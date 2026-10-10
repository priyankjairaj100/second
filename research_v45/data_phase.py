"""One-use, independently budgeted data preparation under Slurm."""
import argparse
import os
from pathlib import Path
import sys
import time
import traceback
from research_v43.campaign import ROOT, read, new, sha, require
from research_v44.campaign import runtime
from research_v45.data import POLICY, inventory, prepare
from src.phase_budget import PhaseBudget
from src.worker_control import WorkerLimits, run_limited
from src.run_store import canonical_json
from src.transaction_timing import verify_command_admission

CAP=602
FILES=('research_v45/data.py','research_v45/data_phase.py','research_v45/DATA_PROTOCOL.txt',
       'research_v43/campaign.py','research_v44/campaign.py','scripts/prepare_wikitext_pilot.py',
       'src/phase_budget.py','src/worker_control.py','src/run_store.py','src/transaction_timing.py')

def sources():return {name:sha(ROOT/name) for name in FILES}

def budget(p):
    return PhaseBudget(Path(p['directory'])/'budget',identity=dict(protocol_sha256=sha(Path(p['directory'])/'program.json'),sources=p['sources']),phase_cpu_seconds={'data':CAP})

def verify(directory):
    p=read(Path(directory)/'program.json')
    require(read(Path(directory)/'registration.json')['program_sha256']==sha(Path(directory)/'program.json'),'Data registration changed')
    require(p['directory']==str(Path(directory).resolve()) and p['policy']==POLICY and p['sources']==sources(), 'Data design/source changed')
    require(p['runtime']==runtime() and p['history']==inventory(),'Data runtime/history changed')
    return p

def register(directory):
    require(os.environ.get('SLURM_JOB_ID'),'Slurm required')
    path=Path(directory).resolve();require(ROOT in path.parents and not path.exists(),'Fresh repository directory required')
    p=dict(schema='c4-data-registration-v45',directory=str(path),policy=POLICY,sources=sources(),runtime=runtime(),
        history=inventory(),cpu_seconds=600,wall_seconds=900,phase_cpu_seconds=CAP,memory_bytes=4*2**30,
        registration_job=os.environ['SLURM_JOB_ID'],automatic_retry=False,model_inference=False)
    new(path/'program.json',p);new(path/'registration.json',dict(program_sha256=sha(path/'program.json')));budget(p)
    print(canonical_json(dict(status='registered',program_sha256=sha(path/'program.json'))).decode())

def run(directory):
    require(os.environ.get('SLURM_JOB_ID'),'Slurm required')
    p=verify(directory);path=Path(p['directory']);require(not (path/'worker').exists(),'One-use data attempt already exists')
    tick=time.perf_counter_ns()
    r=run_limited([sys.executable,'-B','-m','research_v45.data_phase','worker',str(path)],path/'worker',
        WorkerLimits(cpu_seconds=600,wall_seconds=900,address_space_bytes=4*2**30,threads=1,
            affinity_cpus=(min(os.sched_getaffinity(0)),),file_size_bytes=128*2**20),
        identity=dict(program_sha256=sha(path/'program.json')),cwd=ROOT,phase_budget=budget(p),phase='data')
    new(path/'transaction.json',dict(worker_outcome=r['outcome'],elapsed_ns=time.perf_counter_ns()-tick,
        budget=budget(p).snapshot(),slurm_job_id=os.environ['SLURM_JOB_ID']))
    print(canonical_json(r['outcome']).decode());return r['outcome']['status']

def worker(directory):
    p=verify(directory);path=Path(p['directory'])
    verify_command_admission(sha(path/'program.json'),'data',
        [sys.executable,'-B','-m','research_v45.data_phase','worker',str(path)])
    start=time.perf_counter_ns();result=dict(status='running',program_sha256=sha(path/'program.json'))
    try:result.update(prepare(path/'outputs',p['history']))
    except Exception as error:
        result.update(status='failed',error_type=type(error).__name__,error=str(error),traceback=traceback.format_exc());raise
    finally:
        result['elapsed_ns']=time.perf_counter_ns()-start
        new(path/'completion.json',result)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('operation',choices=('register','run','worker'));parser.add_argument('directory');args=parser.parse_args()
    if args.operation=='register':register(args.directory)
    elif args.operation=='worker':worker(args.directory)
    elif run(args.directory)!='complete':raise SystemExit(1)
