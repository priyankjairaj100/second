"""One-use prospective Slurm campaign; no old resource allowance is reused."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from src.run_store import canonical_json, digest
from src.phase_budget import PhaseBudget
from src.worker_control import WorkerLimits, run_limited
from src.runtime_contract import capture_runtime_contract

ROOT = Path(__file__).resolve().parents[1]
CAP = 13000
TRIALS = {
    'prepare': dict(cpu_seconds=2400, wall_seconds=3000),
    'cached': dict(cpu_seconds=1800, wall_seconds=2400),
    'compressed': dict(cpu_seconds=1800, wall_seconds=2400),
    'hybrid': dict(cpu_seconds=2400, wall_seconds=3000),
    'cold': dict(cpu_seconds=1800, wall_seconds=2400),
    'oracle': dict(cpu_seconds=2400, wall_seconds=3000),
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def new(path, value, *, raw=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = value if raw else canonical_json(value)
    with path.open('xb') as stream:
        stream.write(blob)
        stream.flush()
        os.fsync(stream.fileno())
    return dict(file=path.name, sha256=digest(blob), bytes=len(blob))


def sources():
    paths = [p for folder in ('src','scripts','research_v35','research_v37','research_v38',
              'research_v39','research_v40','research_v42','research_v43')
              for p in (ROOT/folder).glob('*.py')]
    paths += [ROOT/'research_v43/PROTOCOL.txt', ROOT/'cluster_setup/run_cpu.sbatch']
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}


def register(directory):
    require(os.environ.get('SLURM_JOB_ID'), 'Registration must bind the actual Slurm runtime')
    directory = Path(directory).resolve()
    require(ROOT in directory.parents and not directory.exists(), 'Campaign must be a fresh repository path')
    historical = {str(p.relative_to(ROOT)):sha(p) for folder in ('campaigns','pilots','local_runs')
                  for p in (ROOT/folder).rglob('ledger.json')}
    source_path = ROOT/'campaigns/ci_scale_v39/attempts/data/outputs/records.json'
    selection_path = ROOT/'campaigns/ci_scale_v39/attempts/data/outputs/selection.json'
    selection = read(selection_path)
    selected = selection['sampling_order_ids'][:3]
    metadata = {r['id']:r for r in selection['selected_metadata']}
    all_rows = {r['id']:r for r in read(source_path)['records']}
    rows = sorted([dict(id=rid,tokens=all_rows[rid]['tokens'][:32]) for rid in selected],key=lambda r:r['id'])
    require(len(rows)==3 and all(len(r['tokens'])==32 for r in rows), 'Development source selection differs')
    program = dict(schema='complete-fixed-anchor-development-v43', directory=str(directory),
        registered_source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        sources=sources(), historical_ledgers=historical, runtime=capture_runtime_contract(),
        registration_job=os.environ['SLURM_JOB_ID'], records=rows,
        source_records_sha256=sha(source_path), source_selection_sha256=sha(selection_path),
        record_provenance={rid:dict(dataset_id='Salesforce/wikitext',
            dataset_revision='b08601e04326c79dfdd32d625aee71d232d685c3', split='train',
            source_file_sha256=selection['source_files']['train']['sha256'],
            tokenizer_sha256=selection['source_files']['tokenizer']['sha256'],
            body_sha256=metadata[rid]['body_sha256'],
            normalized_text_sha256=metadata[rid]['normalized_text_sha256'],
            selection_sha256=sha(selection_path)) for rid in selected},
        normalization=96, tokens_per_record=32, record_count=3, retained_counts=[2,1],
        deletion_order=sorted(selected), trials=TRIALS, phase_cpu_seconds=CAP,
        process_address_space_bytes=16*2**30, file_size_bytes=2*2**30,
        state_scope='Complete packed model, fixed/base targets, retained tokens/provenance and representation payloads; common checkpoint separately counted.',
        statistical_scope='One engineering development root; exposed train articles; no population or confirmation inference.',
        representation_rule='hybrid_gram stores native exact Grams at width768 and lossless source factors at width3072.',
        complete_model=True, confirmation=False, quality_evaluation=False, automatic_retry=False,
        paid_compute=False, gpu_numeric_execution=False,
        independent_oracle='Fresh retained-token anchor traversal, fresh point model and fresh encoding of every representation; no prior-state descriptors as inputs.',
        shared_checkpoint_bytes=sum((ROOT/'tmp/models/distilgpt2'/name).stat().st_size for name in ('model.safetensors','config.json')),
        limits_scope='Slurm RSS cap plus worker RLIMIT_AS/CPU/FSIZE, one CPU affinity, bounded admitted CPU ledger; performance observations not confirmation.')
    directory.mkdir(parents=True)
    new(directory/'program.json',program)
    new(directory/'registration.json',dict(program_sha256=sha(directory/'program.json')))
    budget(program)
    print(canonical_json(dict(status='registered',directory=str(directory),program_sha256=sha(directory/'program.json'))).decode())
    return program


def verify(directory):
    directory=Path(directory).resolve()
    p=read(directory/'program.json')
    require(p['directory']==str(directory) and p['trials']==TRIALS and p['phase_cpu_seconds']==CAP, 'Registration design differs')
    require(read(directory/'registration.json')['program_sha256']==sha(directory/'program.json'), 'Registration changed')
    require(p['sources']==sources(), 'Registered implementation changed')
    require(p['runtime']==capture_runtime_contract(), 'Registered runtime changed')
    for name,expected in p['historical_ledgers'].items():
        require(sha(ROOT/name)==expected,'Historical ledger changed')
    return p


def budget(p):
    from src.experiment_inventory import source_hashes
    return PhaseBudget(Path(p['directory'])/'budget',identity=dict(protocol_sha256=sha(Path(p['directory'])/'program.json'),
        source_sha256=source_hashes(ROOT)),
        phase_cpu_seconds={'feasibility':p['phase_cpu_seconds']})


def run(directory,trial):
    require(os.environ.get('SLURM_JOB_ID'), 'Use Slurm for empirical work')
    p=verify(directory)
    require(trial in TRIALS, 'Unknown attempt')
    root=Path(p['directory'])
    if trial!='prepare':
        require(read(root/'prepare/outputs/completion.json')['status']=='complete','Original preparation not complete')
    attempt=root/trial
    require(not attempt.exists(),'Attempt exists; automatic retries prohibited')
    attempt.mkdir()
    plan=dict(trial=trial,program=str(root/'program.json'),program_sha256=sha(root/'program.json'),
        output=str(attempt/'outputs'),slurm_job_id=os.environ['SLURM_JOB_ID'])
    new(attempt/'plan.json',plan)
    limits=WorkerLimits(**TRIALS[trial],address_space_bytes=p['process_address_space_bytes'],
        threads=1,affinity_cpus=(min(os.sched_getaffinity(0)),),file_size_bytes=p['file_size_bytes'])
    tick=time.perf_counter_ns()
    receipt=run_limited([sys.executable,'-B','-m','research_v43.worker',str(attempt/'plan.json')],
        attempt/'worker',limits,identity=dict(campaign_sha256=sha(root/'program.json'),trial=trial),
        cwd=ROOT,phase_budget=budget(p),phase='feasibility')
    new(attempt/'transaction.json',dict(worker_outcome=receipt['outcome'],
        elapsed_ns=time.perf_counter_ns()-tick,budget=budget(p).snapshot(),
        slurm_job_id=os.environ['SLURM_JOB_ID']))
    print(canonical_json(receipt['outcome']).decode(),flush=True)
    return receipt['outcome']['status']


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('operation',choices=('register','run'))
    parser.add_argument('directory')
    parser.add_argument('trial',nargs='?')
    args=parser.parse_args()
    if args.operation=='register':
        register(args.directory)
    elif run(args.directory,args.trial)!='complete':
        raise SystemExit(1)


if __name__=='__main__':
    main()
