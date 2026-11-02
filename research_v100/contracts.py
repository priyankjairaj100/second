"""Shared producer/child command, limits, paths and complete budget identity."""
import sys
from pathlib import Path
from research_v80.io import require
from research_v90.admission import ledger_identity,verify_command_admission
from research_v90.worker_control import WorkerLimits
from research_v90.phase_budget import PhaseBudget,read_budget_snapshot
from research_v100.config import ROOT,RUN,TRIALS,CAP

def contract(trial,expected,job,affinity,*,root=RUN,cwd=ROOT,executable=None):
    require(trial in TRIALS and type(job) is str and job.isdigit(),'Known matched trial and job required')
    require(type(affinity) is int and affinity>=0,'One actual CPU required')
    root=Path(root).absolute();cwd=Path(cwd).absolute();folder=root/trial
    plan=dict(trial=trial,program=str(root/'program.json'),program_sha256=expected,output=str(folder/'outputs'),slurm_job_id=job)
    command=[sys.executable if executable is None else executable,'-B',str(root/'research_v100/worker.py'),str(folder/'plan.json')]
    limits=WorkerLimits(**TRIALS[trial],address_space_bytes=16*2**30,file_size_bytes=2*2**30,threads=1,affinity_cpus=(affinity,))
    return dict(plan=plan,command=command,limits=limits,identity=dict(program_sha256=expected,trial=trial),
        worker_root=folder/'worker',budget_root=root/'budget',cwd=cwd)

def budget(p,expected,*,root=RUN,read_only=False):
    kw=dict(identity=ledger_identity(expected,p['sources']),phase_cpu_seconds={'feasibility':CAP})
    if not read_only:return PhaseBudget(Path(root)/'budget',**kw)
    result=read_budget_snapshot(Path(root)/'budget',**kw)
    require(result['status']=='verified','Actual complete matched ledger required')
    return result

def admit(c,p,expected):
    return verify_command_admission(expected,'feasibility',c['command'],sources=p['sources'],
        phase_cpu_seconds={'feasibility':CAP},budget_root=c['budget_root'],worker_root=c['worker_root'],
        worker_identity=c['identity'],limits=c['limits'],cwd=c['cwd'])
