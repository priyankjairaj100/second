"""Actual worker seals plus separate controller and scheduler CPU accounting.

This helper does not inspect model/quality outputs. Incomplete accounting refuses;
fully accounted failed attempts remain failures. No receipt is overwritten.
"""
from pathlib import Path
import re
from research_v67.io import read,json_read,require
from research_v69.execution_gate import CAPS,CONTROLLER_CPU,MEMORY,GPU_ALLOCATOR
from src.run_store import canonical_json,digest,read_completed
from src.worker_control import THREAD_VARIABLES


def integer(x,name):
    require(type(x) is int and x>=0,'Nonnegative integer required: '+name)
    return x


def cpu_time(value):
    """Slurm TotalCPU: [[days-]hours:]minutes:seconds[.fraction]."""
    require(type(value) is str and len(value)<=64,'Bounded scheduler CPU clock required')
    match=re.fullmatch(r'(?:(\d+)-)?(?:(\d+):)?(\d{1,2}):(\d{2})(?:\.(\d{1,9}))?',value)
    require(match is not None,'Unrecognized scheduler CPU clock')
    days,hours,minutes,seconds,fraction=match.groups()
    require(int(minutes)<60 and int(seconds)<60 and (days is None or hours is not None),
        'Noncanonical scheduler CPU clock')
    if days is not None:require(int(hours)<24,'Noncanonical scheduler day/hour clock')
    count=(int(days or 0)*86400+int(hours or 0)*3600+int(minutes)*60+int(seconds))*10**9
    return count+int((fraction or '').ljust(9,'0')),10**(9-len(fraction or ''))


def scheduler_rows(raw,expected_jobs):
    """Only allocation rows count; .batch/.extern rows are not added twice.

Expected command fields: JobIDRaw,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS.
All expected jobs must be terminal. Unknown allocations or step parents refuse.
"""
    require(type(raw) is str and len(raw)<=128*2**10 and type(expected_jobs) is dict
        and expected_jobs and len(set(expected_jobs.values()))==len(expected_jobs),
        'Bounded unique registered scheduler jobs required')
    jobs=set(expected_jobs.values());rows={}
    require(all(type(x) is str and x.isdigit() for x in jobs),'Literal scheduler job IDs required')
    for line in raw.splitlines():
        fields=line.split('|')
        if fields[-1]=='':fields.pop()
        require(len(fields)==6,'Exact scheduler field census required')
        job,state,exitcode,elapsed,cpu,cpus=fields
        if '.' in job:
            require(job.split('.')[0] in jobs,'Unregistered scheduler step');continue
        require(job in jobs and job not in rows,'Unknown or duplicate scheduler allocation')
        require(state in {'COMPLETED','FAILED','TIMEOUT','CANCELLED','OUT_OF_MEMORY','NODE_FAIL','PREEMPTED','BOOT_FAIL','DEADLINE'},
            'Terminal scheduler state required')
        require(re.fullmatch(r'\d+:\d+',exitcode) and elapsed.isdigit() and cpus=='1',
            'Literal exit status, elapsed time and one CPU required')
        observed,quantum=cpu_time(cpu)
        rows[job]=dict(state=state,exit_code=exitcode,elapsed_seconds=int(elapsed),
            total_cpu_ns=observed,reporting_quantum_ns=quantum,allocated_cpus=1)
    require(set(rows)==jobs,'Every registered terminal allocation required')
    return {phase:dict(job_id=job,**rows[job]) for phase,job in expected_jobs.items()}


def worker(directory,expected_identity,snapshot):
    """Validate the actual persisted seal and artifacts, then its exact debit."""
    directory=Path(directory)
    require(json_read(directory/'identity.json')==expected_identity,'Actual worker identity differs')
    declared=json_read(directory/'result.json')
    require(type(declared.get('attempt')) is str and re.fullmatch(r'attempt-[0-9]{4,}',declared['attempt'])
        and set(declared['artifacts'])=={'request.json','budget-reservation.json','stdout-summary.json',
            'stderr-summary.json','pre-settlement-observation.json','limits-applied.json'},
        'Exact bounded worker seal artifact census required')
    for name,e in declared['artifacts'].items():
        read(directory/declared['attempt']/name,e,maximum=2**20,retain=False)
    sealed=read_completed(directory,expected_identity)
    require(sealed is not None and json_read(directory/'result.json')==sealed,
        'Complete actual worker seal required, including failed outcomes')
    require(json_read(directory/sealed['attempt']/'status.json')==sealed,'Terminal worker status differs')
    for name,e in sealed['artifacts'].items():
        require(Path(name).name==name,'Literal sealed artifact name required')
        read(directory/sealed['attempt']/name,e,maximum=2*2**30,retain=False)
    limits=expected_identity['limits'];actual=sealed['limits_applied']
    request=json_read(directory/sealed['attempt']/'request.json')
    require(sealed['limits']==limits and request['limits']==limits
        and request['command']==expected_identity['command'] and request['cwd']==expected_identity['cwd']
        and actual==json_read(directory/sealed['attempt']/'limits-applied.json')
        and actual['request_sha256']==digest(canonical_json(request))
        and actual['cpu_seconds']==[limits['cpu_seconds'],limits['cpu_seconds']+1]
        and actual['address_space']==[limits['address_space_bytes']]*2
        and actual['file_size']==[limits['file_size_bytes']]*2
        and actual['affinity_cpus']==limits['affinity_cpus']
        and actual['thread_environment']=={n:'1' for n in THREAD_VARIABLES}
        and limits['threads']==1 and len(limits['affinity_cpus'])==1,
        'Actual worker command or applied resource limit differs')
    require(snapshot['status']=='verified' and not snapshot['reserved_unknown_attempts']
        and not snapshot['reservation_overrun_attempts'] and not any(snapshot['over_cap'].values()),
        'Settled complete within-cap ledger required')
    debit=sealed['budget_debit'];identifier=sealed['budget_attempt_id'];usage=sealed['resource_usage']
    require(expected_identity['phase_budget']['binding_sha256']==snapshot['binding_sha256']
        and expected_identity['phase_budget']['phase']==debit['phase'],
        'Sealed identity and actual ledger binding differ')
    require(snapshot['attempts'].get(identifier)==debit and debit['state']=='settled'
        and sealed['budget_reservation_overrun'] is False,'Actual worker debit differs')
    cpu=integer(usage['total_cpu_ns'],'worker CPU')
    require(cpu==integer(usage['user_cpu_ns'],'user CPU')+integer(usage['system_cpu_ns'],'system CPU')
        and debit['observed_cpu_ns']==cpu and debit['charged_cpu_seconds']==max(1,(cpu+999999999)//10**9),
        'Worker CPU components or rounded debit differ')
    require(debit['reserved_cpu_seconds']==sealed['limits']['cpu_seconds']+2,
        'Worker reservation differs from applied CPU allowance')
    return dict(debit_id=identifier,worker_cpu_ns=cpu,charged_cpu_seconds=debit['charged_cpu_seconds'],
        worker_outcome=sealed['outcome'],maximum_rss_kib=integer(usage['max_rss_kib'],'worker RSS'),
        actual_seal_and_artifacts_checked=True)


def reconcile(phase,entry,worker_row,scheduler,*,registration_sha256):
    require(phase in CAPS and entry['schema']=='quality-controller-entry-v69'
        and entry['registration_sha256']==registration_sha256 and entry['phase']==phase
        and entry['job_id']==scheduler['job_id'],'Bound actual phase/controller/job required')
    require(entry['status'] in {'complete','failed'} and
        ((entry['status']=='complete')==(entry['error'] is None)),'Consistent terminal controller status required')
    require(entry['whole_process_cpu_clock'] is True and entry['all_waited_children_included'] is True
        and worker_row['actual_seal_and_artifacts_checked'] is True,'Whole process and actual sealed accounting required')
    own=integer(entry['process_cpu_ns'],'controller CPU');child=integer(entry['waited_child_cpu_ns'],'waited children')
    measured=integer(worker_row['worker_cpu_ns'],'worker CPU')
    # wait4 components are rounded up independently; getrusage has a different
    # conversion to nanoseconds. Only the two-nanosecond rounding envelope is
    # permitted, not a broad accounting tolerance.
    require(child+2>=measured,'Controller child clock does not include the sealed worker')
    helpers=max(0,child-measured);controller=own+helpers
    require(controller<=(CONTROLLER_CPU+1)*10**9,'Controller plus nonworker children exceed allowance')
    require(worker_row['charged_cpu_seconds']<=CAPS[phase]['cpu_seconds']+2,
        'Worker debit exceeds separate reservation')
    total=own+child
    require(scheduler['total_cpu_ns']+scheduler['reporting_quantum_ns']+2>=total,
        'Scheduler CPU is smaller than observed process tree outside reporting precision')
    require(scheduler['total_cpu_ns']<=(CAPS[phase]['cpu_seconds']+2+CONTROLLER_CPU+1)*10**9,
        'Scheduler CPU exceeds the complete phase reservation')
    require(integer(entry['elapsed_ns'],'entry elapsed')<=(scheduler['elapsed_seconds']+1)*10**9,
        'Scheduler duration cannot contain controller clock')
    require(integer(worker_row['maximum_rss_kib'],'worker RSS')*1024<=MEMORY
        and integer(entry['maximum_rss_kib'],'controller RSS')*1024<=MEMORY,
        'Observed physical RSS exceeds admitted host memory')
    successful=entry['status']=='complete' and worker_row['worker_outcome'].get('status')=='complete'\
        and worker_row['worker_outcome'].get('returncode')==0\
        and scheduler['state']=='COMPLETED' and scheduler['exit_code']=='0:0'
    return dict(phase=phase,job_id=scheduler['job_id'],debit_id=worker_row['debit_id'],accounting_status='verified',
        execution_successful=successful,worker_cpu_ns=measured,controller_own_cpu_ns=own,
        nonworker_waited_child_cpu_ns=helpers,observed_process_tree_cpu_ns=total,
        scheduler_cpu_ns=scheduler['total_cpu_ns'],scheduler_reporting_quantum_ns=scheduler['reporting_quantum_ns'],
        scheduler_minus_observed_cpu_ns=scheduler['total_cpu_ns']-total,
        worker_charged_cpu_seconds=worker_row['charged_cpu_seconds'],
        controller_charged_cpu_seconds=max(1,(controller+999999999)//10**9),
        waited_worker_cpu_counted_once=True,quality_gate_outcome_not_used_for_accounting=True)


def complete(rows,snapshot):
    """Reject missing/duplicated debits; preserve fully accounted phase failures."""
    require(type(rows) is dict and set(rows)==set(CAPS),'All eight declared phase costs required')
    require(all(r['phase']==phase and r['accounting_status']=='verified' for phase,r in rows.items())
        and len({r['job_id'] for r in rows.values()})==len(rows),'Unique bound phase/job costs required')
    require(snapshot['status']=='verified' and not snapshot['reserved_unknown_attempts']
        and not snapshot['reservation_overrun_attempts'] and not any(snapshot['over_cap'].values()),
        'Complete settled ledger required')
    require(all(type(r.get('debit_id')) is str for r in rows.values())
        and len({r['debit_id'] for r in rows.values()})==len(rows)
        and {r['debit_id'] for r in rows.values()}==set(snapshot['attempts']),
        'Every actual ledger attempt must appear exactly once')
    for phase,r in rows.items():
        debit=snapshot['attempts'][r['debit_id']]
        require(debit['state']=='settled' and debit['observed_cpu_ns']==r['worker_cpu_ns']
            and debit['charged_cpu_seconds']==r['worker_charged_cpu_seconds']
            and debit['reserved_cpu_seconds']==CAPS[phase]['cpu_seconds']+2,
            'Phase cost and actual ledger debit differ')
    return dict(status='verified_complete_cost_accounting',execution_successful=all(r['execution_successful'] for r in rows.values()),
        worker_charged_cpu_seconds=sum(r['worker_charged_cpu_seconds'] for r in rows.values()),
        controller_charged_cpu_seconds=sum(r['controller_charged_cpu_seconds'] for r in rows.values()),
        observed_process_tree_cpu_ns=sum(r['observed_process_tree_cpu_ns'] for r in rows.values()),
        scheduler_cpu_ns=sum(r['scheduler_cpu_ns'] for r in rows.values()),phases=rows,
        includes_terminal_entry_after_exit=True,actual_quality_and_model_audits_required_separately=True)


def gpu_memory(report):
    require(report['dtype']=='float64' and report['tf32'] is False and report['amp'] is False
        and report['deterministic_algorithms'] is True and report['allocator_limit_bytes']==GPU_ALLOCATOR,
        'Admitted deterministic binary64 device report required')
    allocated=integer(report['peak_cuda_allocated_bytes'],'allocated GPU bytes')
    reserved=integer(report['peak_cuda_reserved_bytes'],'reserved GPU bytes')
    require(0<allocated<=reserved<=GPU_ALLOCATOR and
        integer(report['copied_arrays_with_bitwise_roundtrip'],'roundtrip arrays')>=78,
        'Actual allocator or complete original parameter transfer report differs')
    return dict(peak_allocated_bytes=allocated,peak_reserved_bytes=reserved,
        allocator_limit_bytes=GPU_ALLOCATOR,all_original_parameter_roundtrips_reported=True,
        allocator_is_not_total_device_memory=True)
