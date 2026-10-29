"""Read-only saved-host review, also used before releasing admission dependents."""
from research_v80.io import require
from research_v83.terminal import actual_seal
from research_v88.storage import evaluate
from research_v99.config import RUN,PROFILES
from research_v99.host import reconcile_cpu
from research_v99.storage_plan import requests
from research_v99.software import validate


def review(operation,program,expected,inputs,scheduler):
    entry=inputs.json(RUN/(operation+'-entry.json'));host=inputs.json(RUN/(operation+'-host.json'))
    start=inputs.json(RUN/(operation+'-host-start.json'))
    for r in (entry,host,start):
        require(r['program_sha256']==expected and r['job_id']==scheduler['job_id']
            and r['operation']==operation and r['arguments']==[], 'Host/entry/scheduler identity differs')
    require(entry['status']==host['status']=='complete' and entry['error'] is host['error'] is None,
        'Actual successful host and entry required')
    require(type(entry['maximum_rss_kib']) is int and 0<=entry['maximum_rss_kib']*1024<=16*2**30,
        'Entry RSS outside declared memory')
    wanted=requests(program['storage_plan'],program['sources'],program['source_archive']['bytes'],operation)
    snapshot=start['snapshot']
    require(wanted==start['requests']==snapshot['requested'] and start['admission']==evaluate(wanted,
        snapshot['observations'],snapshot['quota_text'],snapshot['group_reports']),'Saved storage admission differs')
    mapping=entry['container_storage_mapping']
    require(mapping['status']=='matched_host_devices_and_new_file_groups' and mapping['paths_redirected'] is False,
        'Actual default container path mapping required')
    for scope,path in [('project',str(RUN)),('temporary','/tmp')]:
        host_observation=snapshot['observations'][scope]
        require(mapping['observations'][scope]==dict(path=path,device=host_observation['device'],write_group=host_observation['write_group']),
            'Container device or new-file group differs')
    outcome=host['outcome'];log=outcome['log']
    require(outcome['exit_code']==0 and outcome['failure'] is None and log['complete'] is True
        and 0<=log['bytes']<=64*2**20 and log['bytes']==log['observed_bytes'], 'Actual complete bootstrap log required')
    inputs.read(RUN/(operation+'-bootstrap.log'),{k:log[k] for k in ('bytes','sha256')},retain=False)
    require(inputs.read(RUN/(operation+'-'+scheduler['job_id']+'.log'),retain=False)['bytes']<=4*2**20,
        'External Slurm log exceeded conservative allowance')
    accounting=reconcile_cpu(operation,host['host_process_cpu_ns'],host['preflight_waited_child_cpu_ns'],outcome['subtree_cpu_ns'],entry)
    require(host['accounting']==accounting,'Actual CPU partition differs')
    worker=None
    if operation in PROFILES:
        worker=actual_seal(inputs,RUN/operation/'worker')
        require(worker['attempt']=='attempt-0001' and worker['outcome']['status']=='complete' and worker['outcome']['returncode']==0,
            'Actual successful one-use target seal required')
        require(worker['resource_usage']['total_cpu_ns']==entry['sealed_worker_cpu_ns']==worker['budget_debit']['observed_cpu_ns']
            and worker['budget_debit']['state']=='settled' and worker['budget_debit']['reserved_cpu_seconds']==602
            and worker['budget_debit']['charged_cpu_seconds']<=602 and worker['budget_reservation_overrun'] is False,
            'Actual settled target debit differs')
    if operation=='checks':
        validate(entry['result']);require(inputs.json(RUN/'software-results.json')==entry['result'],'Actual software result differs')
    require(0<entry['elapsed_ns']<=host['elapsed_ns']<=(scheduler['elapsed_seconds']+1)*10**9,'Wall-clock containment differs')
    upper=scheduler['cpu_ns']+scheduler['quantum_ns']
    require(upper>=accounting['envelope_cpu_ns'],'Scheduler CPU cannot contain full envelope')
    controller=upper-accounting['contained_work_cpu_ns']
    require(0<=controller<=302*10**9,'Complete controller including final writes exceeds allowance')
    if operation=='checks':require(upper<=602*10**9,'Complete scheduler software allowance exceeded')
    return dict(job_id=scheduler['job_id'],scheduler_cpu_ns=scheduler['cpu_ns'],scheduler_quantum_ns=scheduler['quantum_ns'],
        complete_controller_upper_cpu_ns=controller,contained_work_cpu_ns=accounting['contained_work_cpu_ns'],
        contained_kind=accounting['contained_kind'],overlapping_clocks_not_summed=True),worker
