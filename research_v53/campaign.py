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
from research_v53.resource_review import review
from src.run_store import canonical_json, digest, read_completed
from src.phase_budget import PhaseBudget, read_budget_snapshot
from src.experiment_inventory import source_hashes
from src.worker_control import WorkerLimits, run_limited

TRIALS={
    'prepare':dict(cpu_seconds=10800,wall_seconds=14400),
    'cached':dict(cpu_seconds=10800,wall_seconds=14400),
    'compressed':dict(cpu_seconds=18000,wall_seconds=21600),
    'hybrid':dict(cpu_seconds=14400,wall_seconds=18000),
    'cold':dict(cpu_seconds=12600,wall_seconds=16200),
    'oracle':dict(cpu_seconds=14400,wall_seconds=18000),
}
CAP=sum(v['cpu_seconds']+2 for v in TRIALS.values())
ARM_ORDER=sorted(('cached','compressed','hybrid','cold'),key=lambda x:digest(('second-v53-arm-order:'+x).encode()))
ORDER=['prepare',*ARM_ORDER,'oracle']


def sources():
    from research_v52.campaign import sources as prior_sources
    result=prior_sources()
    for folder in ('research_v52_postrun','research_v53'):
        for path in sorted((ROOT/folder).iterdir()):
            if path.is_file() and (path.suffix=='.py' or path.name=='PROTOCOL.txt'):
                result[str(path.relative_to(ROOT))]=sha(path)
    result['cluster_setup/v53_pipeline.sh']=sha(ROOT/'cluster_setup/v53_pipeline.sh')
    return result


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
    snapshot=read_budget_snapshot(directory/'budget',identity=dict(protocol_sha256=sha(directory/'program.json'),source_sha256=source_hashes(ROOT)),phase_cpu_seconds={'data':data_phase.CAP})
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


def register(directory,data_directory,checks):
    require(os.environ.get('SLURM_JOB_ID'),'Slurm required')
    directory=Path(directory).resolve();require(ROOT in directory.parents and not directory.exists(),'Fresh campaign path required')
    check=read(checks)
    require(check['status']=='passed' and check['tests']==70 and check['skipped']==0 and
        check['sources']==sources() and check['runtime']==runtime(),'Bound passing Linux checks required')
    require(not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(),'Clean source commit required')
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
    prerequisite.update(software_checks=Path(checks).resolve(),
        v52_audit=ROOT/'validation/v52_terminal_audit.json',
        v51_audit=ROOT/'validation/v52_v51_point_pair_audit.json',
        v45_failure=ROOT/'validation/v49_v45_failure_audit.json')
    require(read(prerequisite['v52_audit'])['status']=='verified_precision48_complete_stage', 'V52 terminal gate absent')
    metadata={r['id']:r for r in selection['selected_metadata']}
    provenance={r['id']:dict(dataset_id='allenai/c4',dataset_revision=DATA_POLICY['revision'],split='train-shard1-prefix',
        source_file_sha256=selection['source_files']['new_c4']['sha256'],tokenizer_sha256=TOKENIZER_SHA,
        body_sha256=metadata[r['id']]['body_sha256'],normalized_text_sha256=metadata[r['id']]['normalized_text_sha256'],
        selection_sha256=sha(prerequisite['data_selection'])) for r in rows}
    historical={str(p.relative_to(ROOT)):sha(p) for folder in ('campaigns','pilots','local_runs') for p in (ROOT/folder).rglob('ledger.json')}
    program=dict(schema='adaptive-compressed48-complete-development-v53',directory=str(directory),
        registered_source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        sources=sources(),runtime=runtime(),historical_ledgers=historical,inputs={k:bind(p) for k,p in prerequisite.items()},
        registration_job=os.environ['SLURM_JOB_ID'],records=rows,record_provenance=provenance,
        normalization=1664,tokens_per_record=128,record_count=13,retained_counts=[12,6],
        deletion_order=[r['id'] for r in rows],trials=TRIALS,trial_order=ORDER,phase_cpu_seconds=CAP,
        prior_failed_charge=4801,data_phase_charged_cpu_seconds=ds['charged_cpu_seconds']['data'],
        process_address_space_bytes=16*2**30,file_size_bytes=2*2**30,shape_admission=review(),
        adaptive_development=True,precision=48,block_size=256,shared_backend='normal_neighbor_primal_v50',
        complete_model=True,confirmation=False,quality_evaluation=False,automatic_retry=False,paid_compute=False,gpu_numeric_execution=False,
        representation_rule='Explicit V53 state schema; compressed48 uses uniform 48-bit block256 factors at every stage. Native exact Grams at eighteen width768 stages, lossless factors at six width3072 stages; max13 sources.',
        independent_oracle='Fresh retained-token traversal and fresh all-representation states; shares solver/codecs, never prior-state descriptors.',
        statistical_scope='One adaptively reused known bounded-frame C4 development root; hash-fixed arm order, one observation per arm/step, no population interval.',
        state_scope='All calibrated code tensors, both targets, retained tokens/provenance and representation payloads; required trust sidecars and common checkpoint counted.',
        shared_checkpoint_bytes=sum((ROOT/'tmp/models/distilgpt2'/name).stat().st_size for name in ('config.json','model.safetensors')),
        limits_scope='One SlurmCPU/thread,16GiB allocation and RLIMIT_AS; fixed process CPU/wall/file ceilings with cumulative admission ledger; no automatic retries.')
    new(directory/'program.json',program);new(directory/'registration.json',dict(program_sha256=sha(directory/'program.json')));budget(program)
    print(canonical_json(dict(status='registered',program_sha256=sha(directory/'program.json'),trial_order=ORDER,phase_cpu_seconds=CAP)).decode())


def verify(directory):
    directory=Path(directory).resolve();p=read(directory/'program.json')
    require(p['schema']=='adaptive-compressed48-complete-development-v53' and p['directory']==str(directory) and
        p['trials']==TRIALS and p['trial_order']==ORDER and p['phase_cpu_seconds']==CAP and
        p['normalization']==1664 and p['record_count']==13 and p['retained_counts']==[12,6], 'Frozen design differs')
    require(read(directory/'registration.json')['program_sha256']==sha(directory/'program.json'),'Registration changed')
    require(p['precision']==48 and p['block_size']==256 and p['shared_backend']=='normal_neighbor_primal_v50' and p['adaptive_development'] is True, 'Representation/backend differs')
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
    r=run_limited([sys.executable,'-B','-m','research_v53.worker',str(attempt/'plan.json')],attempt/'worker',
        WorkerLimits(**TRIALS[trial],address_space_bytes=p['process_address_space_bytes'],threads=1,
            affinity_cpus=(min(os.sched_getaffinity(0)),),file_size_bytes=p['file_size_bytes']),
        identity=dict(campaign_sha256=sha(root/'program.json'),trial=trial),cwd=ROOT,phase_budget=budget(p),phase='feasibility')
    new(attempt/'transaction.json',dict(worker_outcome=r['outcome'],elapsed_ns=time.perf_counter_ns()-tick,
        budget=budget(p).snapshot(),slurm_job_id=os.environ['SLURM_JOB_ID']))
    print(canonical_json(r['outcome']).decode(),flush=True);return r['outcome']['status']

if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='operation',required=True)
    reg=sub.add_parser('register');reg.add_argument('directory');reg.add_argument('data_directory');reg.add_argument('checks')
    runp=sub.add_parser('run');runp.add_argument('directory');runp.add_argument('trial',choices=tuple(TRIALS));args=parser.parse_args()
    if args.operation=='register':register(args.directory,args.data_directory,args.checks)
    elif run(args.directory,args.trial)!='complete':raise SystemExit(1)
