"""Bound separate diagnostic producer; no original operation can be dispatched."""
import os,sys,time
from pathlib import Path
from research_v80.io import require,read,json_read,info
from research_v110.config import ROOT,RUN,PARENT,PARENT_SHA,TRIALS,design
from research_v110.contracts import contract,budget
from research_v110.records import transaction_writer
from research_v90.worker_control import run_limited
from src.run_store import canonical_json


def sha(path):return read(path,retain=False)['sha256']
def bound(e,retain=True):return read(e['path'],{k:e[k] for k in ('bytes','sha256')},retain=retain)


def prerequisites(p):
    from research_v110.dispatch_failure import verify as prior
    require(prior()==p['prior_complete_failure'],'Actual original failure changed')
    from research_v104 import campaign as parent
    old=parent.verify(prerequisite=True)
    require(sha(PARENT/'program.json')==PARENT_SHA and old['admitted_targets']['gpt2']==p['admitted_target']
        and old['checkpoint_paths']['gpt2']==p['checkpoint_path'],'Fixed original target/checkpoint required')
    return old


def verify(program=RUN/'program.json',*,prerequisite=True,registered=True):
    require(Path(program).absolute()==RUN/'program.json','Literal diagnostic program required')
    p=json_read(program);expected=info(canonical_json(p))['sha256']
    require(all(p.get(k)==v for k,v in design().items()),'Exact diagnostic design required')
    if registered:require(json_read(RUN/'registration.json')==dict(program_sha256=expected),'New diagnostic registration required')
    require(json_read(RUN/'inventory.json')==p['sources'] and p['source_count']==len(p['sources'])
        and p['source_inventory']==info(canonical_json(p['sources'])),'Exact source census required')
    for name,e in p['sources'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts,'Relative source required')
        read(RUN/name,e,maximum=64*2**20,retain=False)
    from research_v110.software import SUITES
    require(p['software_suites']=={k:dict(modules=v[0],tests=v[1]) for k,v in SUITES.items()},'Exact test census required')
    if prerequisite:prerequisites(p)
    return p


def run(trial,p,expected):
    require(trial=='diagnostic','Only the new token stage can run')
    c=contract(trial,expected,os.environ['SLURM_JOB_ID'],min(os.sched_getaffinity(0)))
    folder=RUN/trial;folder.mkdir(parents=True,exist_ok=False);records=transaction_writer(folder)
    records.write('plan.json',c['plan']);ledger=budget(p,expected);tick=time.perf_counter_ns()
    receipt=run_limited(c['command'],c['worker_root'],c['limits'],identity=c['identity'],cwd=ROOT,
        phase_budget=ledger,phase='diagnostic')
    records.write('transaction.json',dict(worker_outcome=receipt['outcome'],budget=ledger.snapshot(),
        elapsed_ns=time.perf_counter_ns()-tick,slurm_job_id=os.environ['SLURM_JOB_ID']))
    # Entry always opens this sealed outcome, including failure, before testing success.
    return receipt
