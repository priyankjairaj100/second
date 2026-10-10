"""Fresh independent full-model C4 scale registration and one-use workers."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
from research_v43.campaign import ROOT, read, new, sha, require
from research_v44.campaign import runtime
from research_v45 import data_phase
from research_v45.data import POLICY as DATA_POLICY, TOKENIZER_SHA
from research_v45.resource_review import review
from src.run_store import canonical_json, digest, read_completed
from src.phase_budget import PhaseBudget
from src.experiment_inventory import source_hashes
from src.worker_control import WorkerLimits, run_limited

TRIALS={
    'prepare':dict(cpu_seconds=4800,wall_seconds=6000),
    'cached':dict(cpu_seconds=3600,wall_seconds=4800),
    'compressed':dict(cpu_seconds=4800,wall_seconds=6000),
    'hybrid':dict(cpu_seconds=4800,wall_seconds=6000),
    'cold':dict(cpu_seconds=3600,wall_seconds=4800),
    'oracle':dict(cpu_seconds=4800,wall_seconds=6000),
}
CAP=sum(v['cpu_seconds']+2 for v in TRIALS.values())
ARM_ORDER=sorted(('cached','compressed','hybrid','cold'),key=lambda x:digest(('second-v45-arm-order:'+x).encode()))
ORDER=['prepare',*ARM_ORDER,'oracle']


def sources():
    paths=[p for name in ('src','scripts','research_v35','research_v37','research_v38','research_v39','research_v40','research_v42','research_v43','research_v43_postrun','research_v44','research_v45') for p in (ROOT/name).glob('*.py')]
    paths += [ROOT/'research_v45/PROTOCOL.txt',ROOT/'research_v45/DATA_PROTOCOL.txt',ROOT/'cluster_setup/run_cpu.sbatch']
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}


def bind(path):
    path=Path(path).resolve(strict=True)
    require(path.is_file() and not path.is_symlink(),'Bound input must be a regular file')
    return dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size)


def bound(entry):
    path=Path(entry['path']);require(path.is_file() and path.stat().st_size==entry['bytes'] and sha(path)==entry['sha256'],'Bound input changed')
    return path


def validate_data(directory):
    directory=Path(directory).resolve();dp=data_phase.verify(directory)
    require(sha(directory/'program.json')=='4bd64a67eb44151d09d3552231630ab41a937e17e2709b662e93fc542fa994f0' and
        sha(directory/'outputs/records.json')=='1b3dd813dc5deacb35974e28f1fbd47d14364b85202a7ad12c8c1e7fc6a53259' and
        sha(directory/'outputs/selection.json')=='d3c31bb483b6b77587c372b7611ee21d7ac706fcfbb363dbbb0b6b812754bdb9',
        'The prospectively fixed V45 data root differs')
    result=read(directory/'completion.json');tx=read(directory/'transaction.json')
    require(result['status']=='complete' and result['program_sha256']==sha(directory/'program.json') and
        tx['worker_outcome']['status']=='complete','Data phase not complete')
    identity=read(directory/'worker/identity.json');sealed=read_completed(directory/'worker',identity)
    snapshot=data_phase.budget(dp).snapshot()
    require(sealed is not None and sealed['outcome']==tx['worker_outcome'] and
        snapshot['attempts'][sealed['budget_attempt_id']]==sealed['budget_debit'] and
        len(snapshot['attempts'])==1 and all(a['state']=='settled' for a in snapshot['attempts'].values()) and
        not any(snapshot['over_cap'].values()),'Data budget not settled or sealed')
    selection=read(directory/'outputs/selection.json');records=read(directory/'outputs/records.json')['records']
    require(result['selection_sha256']==sha(directory/'outputs/selection.json') and
        result['records_sha256']==selection['selected_records_sha256']==sha(directory/'outputs/records.json'), 'Data outputs changed')
    require(selection['policy']==DATA_POLICY and selection['exact_hash_overlap_checks_passed'] is True and
        selection['all_historical_wiki_pool_hashes_verified'] is True and selection['no_model_inference'] is True,
        'Input selection policy or overlap evidence differs')
    require(len(records)==13 and records==sorted(records,key=lambda r:r['id']) and
        len({r['id'] for r in records})==13 and all(r['id'].startswith('c4:en:shard1:line') and
        len(r['tokens'])==128 and all(type(t) is int and 0<=t<50257 for t in r['tokens']) for r in records), 'Independent root extent differs')
    require(sha(directory/'outputs/exclusions.json')==selection['protected_exclusion_sha256'],'Exclusions changed')
    for shard,key in ((0,'historical_c4'),(1,'new_c4')):
        source=selection['source_files'][key]
        require(sha(directory/f'outputs/shard-{shard}-prefix.gz.part')==source['sha256'],'Acquired prefix changed')
    return selection,records,snapshot


def register(directory,data_directory):
    require(os.environ.get('SLURM_JOB_ID'),'Slurm required')
    directory=Path(directory).resolve();require(ROOT in directory.parents and not directory.exists(),'Fresh campaign path required')
    selection,rows,ds=validate_data(data_directory);data_directory=Path(data_directory).resolve()
    prerequisite={
        'v43_primary':ROOT/'local_runs/full-model-v43-20261010-b/artifact-audit.json',
        'v43_supplemental':ROOT/'local_runs/full-model-v43-20261010-b/postrun-audit.json',
        'v44_quality':ROOT/'local_runs/exposed-quality-v44-20261010-b/quality/outputs/completion.json',
        'v44_ledger':ROOT/'local_runs/exposed-quality-v44-20261010-b/budget/ledger.json',
        'data_program':data_directory/'program.json','data_completion':data_directory/'completion.json',
        'data_selection':data_directory/'outputs/selection.json','data_records':data_directory/'outputs/records.json',
        'data_ledger':data_directory/'budget/ledger.json','data_exclusions':data_directory/'outputs/exclusions.json'}
    require(all(read(prerequisite[k])['status']=='verified' for k in ('v43_primary','v43_supplemental')),'V43 audit prerequisite failed')
    quality=read(prerequisite['v44_quality']);require(quality['status']=='complete' and quality['development_guards_pass'] and quality['valid_diagnostic'],'Exposed quality prerequisite failed')
    require(all(x['state']=='settled' for x in read(prerequisite['v44_ledger'])['attempts'].values()),'Quality phase unsettled')
    metadata={r['id']:r for r in selection['selected_metadata']}
    provenance={r['id']:dict(dataset_id='allenai/c4',dataset_revision=DATA_POLICY['revision'],split='train-shard1-prefix',
        source_file_sha256=selection['source_files']['new_c4']['sha256'],tokenizer_sha256=TOKENIZER_SHA,
        body_sha256=metadata[r['id']]['body_sha256'],normalized_text_sha256=metadata[r['id']]['normalized_text_sha256'],
        selection_sha256=sha(prerequisite['data_selection'])) for r in rows}
    historical={str(p.relative_to(ROOT)):sha(p) for folder in ('campaigns','pilots','local_runs') for p in (ROOT/folder).rglob('ledger.json')}
    program=dict(schema='independent-c4-complete-development-v45',directory=str(directory),
        registered_source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        sources=sources(),runtime=runtime(),historical_ledgers=historical,inputs={k:bind(p) for k,p in prerequisite.items()},
        registration_job=os.environ['SLURM_JOB_ID'],records=rows,record_provenance=provenance,
        normalization=1664,tokens_per_record=128,record_count=13,retained_counts=[12,6],
        deletion_order=[r['id'] for r in rows],trials=TRIALS,trial_order=ORDER,phase_cpu_seconds=CAP,
        prior_failed_charge=0,data_phase_charged_cpu_seconds=ds['charged_cpu_seconds']['data'],
        process_address_space_bytes=16*2**30,file_size_bytes=2*2**30,shape_admission=review(),
        complete_model=True,confirmation=False,quality_evaluation=False,automatic_retry=False,paid_compute=False,gpu_numeric_execution=False,
        representation_rule='Native exact Grams at eighteen width768 stages, lossless factors at six width3072 stages; max13 sources.',
        independent_oracle='Fresh retained-token traversal and fresh all-representation states; shares solver/codecs, never prior-state descriptors.',
        statistical_scope='One outcome-blind disjoint bounded-frame C4 development root; hash-fixed arm order, one observation per arm/step, no population interval.',
        state_scope='All calibrated code tensors, both targets, retained tokens/provenance and representation payloads; required trust sidecars and common checkpoint counted.',
        shared_checkpoint_bytes=sum((ROOT/'tmp/models/distilgpt2'/name).stat().st_size for name in ('config.json','model.safetensors')),
        limits_scope='One SlurmCPU/thread,16GiB allocation and RLIMIT_AS; fixed process CPU/wall/file ceilings with cumulative admission ledger; no automatic retries.')
    new(directory/'program.json',program);new(directory/'registration.json',dict(program_sha256=sha(directory/'program.json')));budget(program)
    print(canonical_json(dict(status='registered',program_sha256=sha(directory/'program.json'),trial_order=ORDER,phase_cpu_seconds=CAP)).decode())


def verify(directory):
    directory=Path(directory).resolve();p=read(directory/'program.json')
    require(p['schema']=='independent-c4-complete-development-v45' and p['directory']==str(directory) and
        p['trials']==TRIALS and p['trial_order']==ORDER and p['phase_cpu_seconds']==CAP and
        p['normalization']==1664 and p['record_count']==13 and p['retained_counts']==[12,6], 'Frozen design differs')
    require(read(directory/'registration.json')['program_sha256']==sha(directory/'program.json'),'Registration changed')
    require(p['sources']==sources() and p['runtime']==runtime(),'Source/runtime changed')
    for name,h in p['historical_ledgers'].items():require(sha(ROOT/name)==h,'Historical ledger changed')
    for entry in p['inputs'].values():bound(entry)
    return p


def budget(p):
    return PhaseBudget(Path(p['directory'])/'budget',identity=dict(protocol_sha256=sha(Path(p['directory'])/'program.json'),source_sha256=source_hashes(ROOT)),phase_cpu_seconds={'feasibility':CAP})


def run(directory,trial):
    require(os.environ.get('SLURM_JOB_ID'),'Slurm required')
    p=verify(directory);require(trial in TRIALS,'Unknown trial');root=Path(p['directory'])
    for previous in ORDER[:ORDER.index(trial)]:
        require(read(root/previous/'transaction.json')['worker_outcome']['status']=='complete' and
            read(root/previous/'outputs/completion.json')['status']=='complete','Earlier trial did not complete')
    attempt=root/trial;require(not attempt.exists(),'One-use attempt exists; retries prohibited');attempt.mkdir()
    plan=dict(trial=trial,program=str(root/'program.json'),program_sha256=sha(root/'program.json'),output=str(attempt/'outputs'),slurm_job_id=os.environ['SLURM_JOB_ID'])
    new(attempt/'plan.json',plan);tick=time.perf_counter_ns()
    r=run_limited([sys.executable,'-B','-m','research_v45.worker',str(attempt/'plan.json')],attempt/'worker',
        WorkerLimits(**TRIALS[trial],address_space_bytes=p['process_address_space_bytes'],threads=1,
            affinity_cpus=(min(os.sched_getaffinity(0)),),file_size_bytes=p['file_size_bytes']),
        identity=dict(campaign_sha256=sha(root/'program.json'),trial=trial),cwd=ROOT,phase_budget=budget(p),phase='feasibility')
    new(attempt/'transaction.json',dict(worker_outcome=r['outcome'],elapsed_ns=time.perf_counter_ns()-tick,
        budget=budget(p).snapshot(),slurm_job_id=os.environ['SLURM_JOB_ID']))
    print(canonical_json(r['outcome']).decode(),flush=True);return r['outcome']['status']

if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='operation',required=True)
    reg=sub.add_parser('register');reg.add_argument('directory');reg.add_argument('data_directory')
    runp=sub.add_parser('run');runp.add_argument('directory');runp.add_argument('trial',choices=tuple(TRIALS));args=parser.parse_args()
    if args.operation=='register':register(args.directory,args.data_directory)
    elif run(args.directory,args.trial)!='complete':raise SystemExit(1)
