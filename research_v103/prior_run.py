"""Immutable failed V100 evidence; live scheduler access belongs to host only."""
import subprocess
from pathlib import Path
from research_v80.io import read,json_read,require,info
from research_v83.accounting import cpu_time
from research_v103.config import RUN
from research_v103.prior_admission import verify as admission_failures
from src.run_store import strict_json
PRIOR=Path('/nfs_home/users/poonam/second-20261010/local_runs/matched-complete-recovery-v100-20261026-a')
SHA='6be461e20f7e853817f5a610bd7d4705c089b56fd5f57968c64091288d66ea97'
FIELDS='--format=JobIDRaw,JobName%60,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS,ReqMem,NodeList'


def failed_cpu(raw):
    rows=[x.split('|') for x in raw.splitlines() if '.' not in x.split('|')[0]]
    require(len(rows)==1 and len(rows[0])==9,'Exact failed full-screen allocation required')
    job,name,state,code,elapsed,cpu,cpus,memory,node=rows[0];lower,q=cpu_time(cpu)
    require((job,name,state,code,elapsed,cpus,memory,node)==('16307','second100-checks','FAILED','1:0','4','1','16G','csis.mn1')
        and lower==3249000000 and lower+q==3250000000,'Failed full-screen scheduler identity or cost differs')
    return lower,lower+q


def verify(*,live_scheduler=False):
    older=admission_failures(live_scheduler=live_scheduler)
    raw=read(RUN/'gates/v100-failed-software-carry.json',maximum=2**20);r=strict_json(raw)
    require(r['schema']=='failed-fullscreen-software-v100' and r['status']=='verified_pre_software_failure'
        and r['directory']==str(PRIOR) and r['program_sha256']==SHA and r['job_id']=='16307', 'Exact preserved full-screen failure required')
    require(r['conservative_aggregate_charge_seconds']==r['conservative_controller_charge_seconds']==4
        and r['new_software_aggregate_seconds']==598 and r['new_checks_controller_seconds']==298,
        'Failure cost cannot be reset or enlarged')
    for n,e in r['files'].items():
        p=Path(n);require(not p.is_absolute() and '..' not in p.parts,'Unsafe preserved file')
        read(PRIOR/p,e,maximum=64*2**20,retain=False)
    require({str(p.relative_to(PRIOR)) for p in PRIOR.rglob('*') if p.is_file()}==set(r['files']), 'Failed namespace changed or retried')
    read(PRIOR.parent/'matched-complete-recovery-v100-source-only.tar',r['source_archive'],maximum=64*2**20,retain=False)
    read(PRIOR/'inventory.json',r['source_inventory'],maximum=2**20,retain=False)
    require(read(PRIOR/'program.json',maximum=2**20,retain=False)['sha256']==SHA
        and json_read(PRIOR/'registration.json')==dict(program_sha256=SHA), 'Failed program or registration differs')
    require(not any((PRIOR/n).exists() for n in ('budget','distilgpt2','gpt2','chain-chain-intent.json','software-results.json')),
        'Failed pre-software attempt cannot hide numerical work')
    row=json_read(PRIOR/'checks-submission.json')
    require(row['job_id']=='16307' and row['program_sha256']==SHA and row['operation']==row['name']=='checks', 'Failed job identity differs')
    lower,upper=failed_cpu(r['scheduler_raw'])
    if live_scheduler:
        actual=subprocess.check_output(['sacct','-nP','-j','16307',FIELDS],text=True,timeout=20)
        require(failed_cpu(actual)==(lower,upper),'Live failed state differs')
    entry=json_read(PRIOR/'checks-entry.json');host=json_read(PRIOR/'checks-host.json')
    require(entry['status']==host['status']=='failed' and entry['sealed_worker_cpu_ns']==entry['software_tree_cpu_ns']==0
        and entry['error']==dict(type='FileNotFoundError',message="[Errno 2] No such file or directory: 'sacct'"), 'Failure scope changed')
    require(host['outcome']['log']['complete'] is True
        and host['host_process_cpu_ns']+host['preflight_waited_child_cpu_ns']+host['outcome']['subtree_cpu_ns']<=upper<=4*10**9,
        'Complete failed cost omitted')
    return dict(status='preserved_pre_software_failure',v100_report=info(raw),program_sha256=SHA,job_id='16307',
        scheduler_cpu_lower_ns=lower,scheduler_cpu_upper_ns=upper,carried_software_seconds=4,carried_controller_seconds=4,
        new_software_seconds=598,new_checks_controller_seconds=298,original_software_seconds=602,
        original_checks_controller_seconds=302,prior_admission_failures=older,no_numerical_work=True)


def check_host_binding(program,start,expected,operation,job):
    require(start['program_sha256']==expected and start['operation']==operation and start['job_id']==job
        and start['live_failure_scheduler_verified'] is True
        and start['prior_failure_verification']==program['prior_complete_failure'],
        'Current allocation must carry the host live scheduler verification')
