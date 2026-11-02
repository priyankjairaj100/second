"""Reopen both consumed failures and carry their known cost without a reset."""
import subprocess
from pathlib import Path
from research_v80.io import read, json_read, require, info
from research_v99.prior_setup import verify as verify_v91
from research_v101.config import RUN
from research_v83.accounting import cpu_time
from src.run_store import strict_json
PRIOR = Path('/nfs_home/users/poonam/second-20261010/local_runs/matched-transfer-admission-v99-20261026-a')
SHA = 'df3047fd72654336e8d0791d0acbb0486d7da4c87a8f62798b018cc1f85bb446'


def verify(*, live_scheduler=False):
    old_setup = verify_v91()
    raw = read(RUN/'gates/v99-failed-software-carry.json', maximum=2**20)
    saved = strict_json(raw)
    require(saved['schema']=='failed-software-carry-v99' and saved['status']=='verified_failed_software_only'
            and saved['failed_program_sha256']==SHA and saved['job_id']=='16301'
            and saved['directory']==str(PRIOR), 'Exact failed software provenance required')
    require(saved['conservative_aggregate_charge_seconds']==56 and saved['conservative_controller_charge_seconds']==10
            and saved['remaining_software_aggregate_seconds']==546 and saved['new_checks_controller_seconds']==292
            and saved['new_controller_ceiling_seconds']==1500 and saved['total_controller_ceiling_seconds']==1510,
            'Preserved failed cost and reduced new ceilings required')
    for name, binding in saved['files'].items():
        path=Path(name)
        require(not path.is_absolute() and '..' not in path.parts, 'Unsafe old receipt path')
        read(PRIOR/path,binding,maximum=64*2**20,retain=False)
    require({str(p.relative_to(PRIOR)) for p in PRIOR.rglob('*') if p.is_file()}==set(saved['files']),
            'Consumed V99 attempt changed or was retried')
    read(PRIOR.parent/'matched-transfer-admission-v99-source-only.tar',saved['source_archive'],maximum=64*2**20,retain=False)
    read(PRIOR/'inventory.json',saved['source_inventory'],maximum=2**20,retain=False)
    require(read(PRIOR/'program.json',maximum=2**20,retain=False)['sha256']==SHA
            and json_read(PRIOR/'registration.json')==dict(program_sha256=SHA), 'Failed registry changed')
    require(not any((PRIOR/n).exists() for n in ('budget','checkpoint','chain-chain-intent.json','distilgpt2','gpt2')),
            'Failed software cannot hide fetch or numerical work')
    submission=json_read(PRIOR/'checks-submission.json')
    require(submission['job_id']=='16301' and submission['program_sha256']==SHA
            and submission['name']==submission['operation']=='checks', 'Failed allocation identity differs')
    if live_scheduler:
        actual=subprocess.check_output(['sacct','-nP','-j','16301',
            '--format=JobIDRaw,JobName%60,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS,ReqMem,NodeList'],text=True,timeout=20)
        rows=[line.split('|') for line in actual.splitlines() if '.' not in line.split('|')[0]]
        require(len(rows)==1 and len(rows[0])==9, 'Exact failed scheduler allocation required')
        job,name,state,code,elapsed,cpu,cpus,memory,node=rows[0]
    else:
        # Actual immutable eight-field receipt, verified again live by the host.
        rows=[line.split('|') for line in saved['scheduler_raw'].splitlines() if '.' not in line.split('|')[0]]
        require(len(rows)==1 and len(rows[0])==8, 'Exact saved failed allocation required')
        job,state,code,elapsed,cpu,cpus,memory,node=rows[0]
        require('JobName=second99-checks' in submission['snapshot'], 'Bound failed job name differs')
        name='second99-checks'
    lower,quantum=cpu_time(cpu);upper=lower+quantum
    require((job,name,state,code,cpus,memory,node)==('16301','second99-checks','FAILED','1:0','1','16G','csis.mn1')
            and lower==saved['scheduler_cpu_lower_ns'] and upper==saved['scheduler_cpu_upper_ns'],
            'Failed scheduler identity or CPU differs')
    entry=json_read(PRIOR/'checks-entry.json');host=json_read(PRIOR/'checks-host.json')
    software=json_read(PRIOR/'software-results.json')
    require(entry['status']==host['status']=='failed' and entry['sealed_worker_cpu_ns']==0
            and entry['software_tree_cpu_ns']==saved['contained_software_cpu_ns']==46480290000,
            'Failure scope or contained software cost differs')
    total=host['host_process_cpu_ns']+host['preflight_waited_child_cpu_ns']+host['outcome']['subtree_cpu_ns']
    require(0<=total<=upper<=56*10**9 and 0<=upper-entry['software_tree_cpu_ns']<=10*10**9
            and host['outcome']['log']['complete'] is True, 'Complete failed cost cannot fit carried allowance')
    require(software['suites']['bounded_components']==dict(tests=48,errors=4,failures=0,skipped=0),
            'Preserved four source-binding errors differ')
    return dict(status='preserved_setup_and_software_failures',v91=old_setup,v99_report=info(raw),
                v99_program_sha256=SHA,job_id='16301',scheduler_cpu_lower_ns=lower,scheduler_cpu_upper_ns=upper,
                carried_software_seconds=56,carried_controller_seconds=10,new_software_seconds=546,
                new_checks_controller_seconds=292,new_controller_seconds=1500,
                original_software_seconds=602,original_controller_seconds=1510,no_numerical_work=True)
