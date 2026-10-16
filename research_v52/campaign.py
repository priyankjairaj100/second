"""Fresh one-use 48-bit development probe; never retries V51."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
from research_v43.campaign import read,new,sha,require
from research_v44.campaign import runtime
from research_v45.campaign import bind,bound
from research_v51.campaign import sources as previous_sources
from research_v52.evidence import validate_v51
from src.phase_budget import PhaseBudget
from src.experiment_inventory import source_hashes
from src.worker_control import WorkerLimits,run_limited
from src.run_store import canonical_json

ROOT=Path(__file__).resolve().parents[1]
LIMITS=dict(cpu_seconds=1200,wall_seconds=1800,address_space_bytes=16*2**30,threads=1,file_size_bytes=2**30)
CAPS={'precision48':1202}


def sources():
    result=previous_sources()
    for folder in ('research_v52','research_v51_postrun','research_v48'):
        for p in sorted((ROOT/folder).iterdir()):
            if p.is_file() and (p.suffix=='.py' or p.name=='PROTOCOL.txt'):result[str(p.relative_to(ROOT))]=sha(p)
    return result


def budget(d):
    return PhaseBudget(d/'budget',identity=dict(protocol_sha256=sha(d/'program.json'),
        source_sha256=source_hashes(ROOT)),phase_cpu_seconds=CAPS)


def verify(directory):
    d=Path(directory).resolve();p=read(d/'program.json')
    require(p['schema']=='precision48-stage-program-v52' and p['directory']==str(d) and
        read(d/'registration.json')['program_sha256']==sha(d/'program.json'),'Registration differs')
    require(p['sources']==sources() and p['runtime']==runtime() and p['limits']==LIMITS and
        p['caps']==CAPS and p['precision']==48 and p['block_size']==256,'Frozen design/runtime/source differs')
    for entry in p['inputs'].values():bound(entry)
    return p


def register(directory,checks):
    require(os.environ.get('SLURM_JOB_ID'),'Slurm required');d=Path(directory).resolve()
    require(ROOT in d.parents and not d.exists(),'Fresh one-use path required')
    check=read(checks)
    require(check['status']=='passed' and check['tests']==4 and check['skipped']==0 and
        check['sources']==sources() and check['runtime']==runtime(),'Passing bound software checks required')
    evidence=validate_v51();old=ROOT/'local_runs/real-wide-stage-v51-20261011-a'
    # Bind every consumed/precondition artifact, including prior sealed failures.
    paths=[x for x in old.rglob('*') if x.is_file() and not x.name.endswith('.lock')]
    paths.extend((Path(checks).resolve(),ROOT/'campaigns/csis_wide_stage_v51_terminal/accounting.txt'))
    p=dict(schema='precision48-stage-program-v52',directory=str(d),v51_directory=str(old),
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        sources=sources(),runtime=runtime(),limits=LIMITS,caps=CAPS,precision=48,block_size=256,
        registration_job=os.environ['SLURM_JOB_ID'],inputs={str(x.relative_to(ROOT)):bind(x) for x in paths},
        v51_evidence=evidence,complete_model=False,quality_evaluation=False,confirmation=False,acl_ready=False,
        adaptive_development=True,automatic_retry=False,new_quality_data=False,
        scope='Next already-supported codec precision after V51 box refusal on the same known development stage. Reuses exact prepared inputs; no service timing, new root, holdout or complete-model claim.')
    d.mkdir(parents=True);new(d/'program.json',p);new(d/'registration.json',dict(program_sha256=sha(d/'program.json')))
    budget(d);print(canonical_json(dict(status='registered',program_sha256=sha(d/'program.json'))).decode(),flush=True)


def run(directory):
    require(os.environ.get('SLURM_JOB_ID'),'Slurm required')
    d=Path(directory).resolve();p=verify(d);require(not (d/'worker').exists(),'Attempt already exists')
    tick=time.perf_counter_ns()
    r=run_limited([sys.executable,'-B','-m','research_v52.worker',str(d)],d/'worker',
        WorkerLimits(**LIMITS,affinity_cpus=(min(os.sched_getaffinity(0)),)),
        identity=dict(program_sha256=sha(d/'program.json')),cwd=ROOT,phase_budget=budget(d),phase='precision48')
    new(d/'transaction.json',dict(worker_outcome=r['outcome'],elapsed_ns=time.perf_counter_ns()-tick,
        budget=budget(d).snapshot(),slurm_job_id=os.environ['SLURM_JOB_ID']))
    print(canonical_json(r['outcome']).decode(),flush=True)
    return r['outcome']['status']


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('operation',choices=('execute','run'))
    parser.add_argument('directory');parser.add_argument('--checks');args=parser.parse_args()
    if args.operation=='execute':register(args.directory,args.checks)
    sys.exit(0 if run(args.directory)=='complete' else 1)
