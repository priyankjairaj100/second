"""Preserve V103 qualification and failed dispatch; no numerical attempt existed."""
import subprocess
from pathlib import Path
from research_v80.io import read,json_read,require,info
from research_v83.accounting import cpu_time
from research_v104.config import RUN
from research_v104.prior_run import verify as prior_failure,check_host_binding
from src.run_store import strict_json
PRIOR=Path('/nfs_home/users/poonam/second-20261010/local_runs/matched-complete-recovery-v103-20261026-a')
SHA='ac31d8ea5a15de858d4e55c527c9a267106c0fa95ffb54298dc112ed96300733'
FIELDS='--format=JobIDRaw,JobName%60,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS,ReqMem,NodeList'


def verify(*,live_scheduler=False):
    older=prior_failure(live_scheduler=live_scheduler)
    blob=read(RUN/'gates/v103-dispatch-failure-carry.json',maximum=2**20);r=strict_json(blob)
    require(r['schema']=='failed-dispatch-carry-v103' and r['status']=='verified_no_numerical_dispatch'
        and r['directory']==str(PRIOR) and r['program_sha256']==SHA, 'Exact V103 dispatch failure required')
    require(r['carried_v103_software_seconds']==68 and r['carried_v103_software_controller_seconds']==15
        and r['carried_v103_numerical_controller_seconds']==1 and r['total_software_charge_seconds']==72
        and r['total_software_controller_charge_seconds']==19 and r['new_software_seconds']==530
        and r['new_checks_controller_seconds']==283 and r['new_numerical_controller_seconds']==6039,
        'Prior qualification and failed dispatch costs must remain within old ceilings')
    for n,e in r['files'].items():
        q=Path(n);require(not q.is_absolute() and '..' not in q.parts,'Unsafe old path')
        read(PRIOR/q,e,maximum=64*2**20,retain=False)
    require({str(p.relative_to(PRIOR)) for p in PRIOR.rglob('*') if p.is_file()}==set(r['files']), 'Consumed V103 namespace changed')
    read(PRIOR.parent/'matched-complete-recovery-v103-source-only.tar',r['source_archive'],maximum=64*2**20,retain=False)
    read(PRIOR/'inventory.json',r['source_inventory'],maximum=2**20,retain=False)
    require(read(PRIOR/'program.json',maximum=2**20,retain=False)['sha256']==SHA
        and json_read(PRIOR/'registration.json')==dict(program_sha256=SHA), 'V103 registry changed')
    require(not any((PRIOR/n).exists() for n in ('budget','distilgpt2','gpt2','distilgpt2--prepare-host-start.json',
        'distilgpt2--prepare-entry-start.json','distilgpt2--prepare-host.json')), 'Failed preflight cannot hide numerical dispatch')
    raw=r['scheduler_raw']
    if live_scheduler:
        actual=subprocess.check_output(['sacct','-nP','-j',','.join(str(i) for i in range(16309,16332)),FIELDS],text=True,timeout=20)
        require(actual==raw,'Live completed/failed/cancelled V103 state differs')
    rows={x.split('|')[0]:x.split('|') for x in raw.splitlines() if '.' not in x.split('|')[0]}
    require(set(rows)=={str(i) for i in range(16309,16332)} and rows['16309'][2:6]==['COMPLETED','0:0','71','01:07.113']
        and rows['16310'][2:6]==['FAILED','1:0','1','00:00.883'] and
        all(rows[str(i)][2:7]==['CANCELLED','0:0','0','00:00:00','0'] for i in range(16311,16332)), 'Exact consumed chain states required')
    for mode in ('checks','chain'):
        chain=json_read(PRIOR/(mode+'-released-chain.json'))
        require(chain==json_read(PRIOR/(mode+'-held-chain.json')) and chain['program_sha256']==SHA,'Old release chain differs')
        for row in chain['jobs']:
            require(row==json_read(PRIOR/(row['name']+'-submission.json')) and row['job_id'] in rows
                and rows[row['job_id']][1]=='second103-'+row['name'],'Old job identity differs')
    entry=json_read(PRIOR/'checks-entry.json');host=json_read(PRIOR/'checks-host.json')
    lower,q=cpu_time(rows['16309'][5]);upper=lower+q
    require(entry['status']==host['status']=='complete' and entry['software_tree_cpu_ns']==52626715000
        and upper==67114000000 and upper-entry['software_tree_cpu_ns']<=15*10**9,
        'Complete prior software cost differs')
    lower,q=cpu_time(rows['16310'][5]);require(lower+q==884000000,'Dispatch cost differs')
    return dict(status='preserved_qualification_and_pre_dispatch_failure',v103_report=info(blob),program_sha256=SHA,
        checks_job='16309',failed_job='16310',carried_software_seconds=72,carried_controller_seconds=19,
        carried_numerical_controller_seconds=1,new_software_seconds=530,new_checks_controller_seconds=283,
        new_numerical_controller_seconds=6039,original_software_seconds=602,original_checks_controller_seconds=302,
        original_numerical_controller_seconds=6040,prior_complete_failure=older,no_numerical_work=True)
