"""One-use synthetic profiling under a fresh 602-CPU-second phase."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from research_v43.campaign import read,new,sha,require
from research_v44.campaign import runtime
from research_v45.campaign import sources as frozen_sources
from src.experiment_inventory import source_hashes
from src.phase_budget import PhaseBudget
from src.run_store import canonical_json
from src.transaction_timing import verify_command_admission
from src.worker_control import WorkerLimits,run_limited

ROOT=Path(__file__).resolve().parents[1]
LIMITS=dict(cpu_seconds=600,wall_seconds=900,address_space_bytes=16*2**30,threads=1,file_size_bytes=2**30)


def sources():
    out=frozen_sources()
    for p in sorted((ROOT/'research_v49').iterdir()):
        if p.is_file() and (p.suffix=='.py' or p.name=='PROTOCOL.txt'):out[str(p.relative_to(ROOT))]=sha(p)
    return out


def budget(directory):
    return PhaseBudget(Path(directory)/'budget',identity=dict(protocol_sha256=sha(Path(directory)/'program.json'),
        source_sha256=source_hashes(ROOT)),phase_cpu_seconds={'software_profile':602})


def verify(directory):
    d=Path(directory).resolve();p=read(d/'program.json')
    require(p['directory']==str(d) and read(d/'registration.json')['program_sha256']==sha(d/'program.json')
        and p['sources']==sources() and p['runtime']==runtime() and p['limits']==LIMITS,'Profile registration differs')
    for entry in p['inputs'].values():require(sha(entry['path'])==entry['sha256'],'Failure prerequisite changed')
    return p


def register(directory):
    require(os.environ.get('SLURM_JOB_ID'),'Slurm required');d=Path(directory).resolve()
    require(ROOT in d.parents and not d.exists(),'Fresh profile path required')
    failed=ROOT/'local_runs/c4-full-model-v45-20261010-a'
    tx=read(failed/'prepare/transaction.json');require(tx['worker_outcome']['kind']=='cpu_limit','Preserved failure required')
    require(all(r['state']=='settled' for r in read(failed/'budget/ledger.json')['attempts'].values()),'V45 must be settled')
    inputs={name:dict(path=str(failed/name),sha256=sha(failed/name)) for name in
        ('program.json','budget/ledger.json','prepare/worker/result.json','prepare/transaction.json')}
    from research_v49.profile import WIDTHS,fixture
    import hashlib
    fixtures={str(w):{k:hashlib.sha256(a.astype('<f8').tobytes()).hexdigest()
        for k,a in zip(('weights','features'),fixture(w))} for w in WIDTHS}
    p=dict(schema='synthetic-streamed-profile-program-v49',directory=str(d),sources=sources(),runtime=runtime(),
        inputs=inputs,limits=LIMITS,phase_cpu_seconds=602,fixture_hashes=fixtures,
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        registration_job=os.environ['SLURM_JOB_ID'],empirical_model_inference=False,new_quality_data=False,
        automatic_retry=False,scope='Synthetic software component profiling; not a replacement or retry of V45.')
    d.mkdir(parents=True);new(d/'program.json',p);new(d/'registration.json',dict(program_sha256=sha(d/'program.json')))
    budget(d)


def run(directory):
    p=verify(directory);d=Path(p['directory']);require(not (d/'worker').exists(),'Profile already attempted')
    start=time.perf_counter_ns()
    result=run_limited([sys.executable,'-B','-m','research_v49.campaign','worker',str(d)],d/'worker',
        WorkerLimits(**LIMITS,affinity_cpus=(min(os.sched_getaffinity(0)),)),
        identity=dict(program_sha256=sha(d/'program.json')),cwd=ROOT,phase_budget=budget(d),phase='software_profile')
    new(d/'transaction.json',dict(worker_outcome=result['outcome'],elapsed_ns=time.perf_counter_ns()-start,
        budget=budget(d).snapshot(),slurm_job_id=os.environ['SLURM_JOB_ID']))
    return result['outcome']['status']


def worker(directory):
    p=verify(directory);d=Path(p['directory']);ph=sha(d/'program.json')
    verify_command_admission(ph,'software_profile',[sys.executable,'-B','-m','research_v49.campaign','worker',str(d)])
    out=d/'outputs';out.mkdir();count=0
    def emit(row):
        nonlocal count
        new(out/f'progress-{count:04d}.json',row);count+=1
        print(canonical_json(row).decode(),flush=True)
    result=dict(schema='synthetic-streamed-profile-result-v49',status='running',program_sha256=ph,cases=[],
        empirical_model_inference=False,quality_evaluation=False,confirmation=False,acl_ready=False)
    try:
        from research_v49.profile import run
        result['cases']=run(emit);result['status']='complete'
    except Exception as error:
        result.update(status='failed',error=str(error),traceback=traceback.format_exc());raise
    finally:new(out/'completion.json',result)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('operation',choices=('register','run','worker'))
    parser.add_argument('directory');args=parser.parse_args()
    if args.operation=='register':register(args.directory)
    elif args.operation=='worker':worker(args.directory)
    else:sys.exit(0 if run(args.directory)=='complete' else 1)
