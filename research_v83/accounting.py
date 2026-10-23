"""Read-only terminal reconciliation with separate overlapping CPU clocks.

The integer Slurm clock parser follows the preserved V69 accounting contract.
No successful receipt is inferred from generated tests or an active allocation.
"""
import re

def require(ok,message):
    if not ok:raise ValueError(message)

def integer(x,name):
    require(type(x) is int and x>=0,'Nonnegative integer required: '+name);return x

def cpu_time(value):
    require(type(value) is str and len(value)<=64,'Bounded CPU time required')
    m=re.fullmatch(r'(?:(\d+)-)?(?:(\d+):)?(\d{1,2}):(\d{2})(?:\.(\d{1,9}))?',value)
    require(m is not None,'Unrecognized scheduler clock')
    d,h,minutes,seconds,f=m.groups()
    require(int(minutes)<60 and int(seconds)<60 and (d is None or h is not None and int(h)<24),'Noncanonical scheduler clock')
    return (int(d or 0)*86400+int(h or 0)*3600+int(minutes)*60+int(seconds))*10**9+int((f or '').ljust(9,'0')),10**(9-len(f or ''))

def scheduler_rows(raw,jobs):
    # JobIDRaw,JobName,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS,ReqMem,NodeList
    require(type(raw) is str and len(raw)<128*2**10 and jobs and len({r['job_id'] for r in jobs.values()})==len(jobs),'Bounded unique job registry required')
    ids={r['job_id'] for r in jobs.values()};found={}
    for line in raw.splitlines():
        fields=line.split('|')
        require(len(fields)==9,'Exact nine scheduler fields required')
        ident,name,state,exitcode,elapsed,cpu,cpus,mem,node=fields
        if '.' in ident:
            require(ident.split('.')[0] in ids,'Unknown scheduler step');continue
        require(ident in ids and ident not in found,'Unknown or duplicate allocation')
        require(state=='COMPLETED' and exitcode=='0:0','Successful terminal allocation required; preserve failure separately')
        require(cpus=='1' and mem=='16G' and node=='csis.mn1' and elapsed.isdigit(),'Allocation host/resource identity differs')
        observed,quantum=cpu_time(cpu)
        found[ident]=dict(name=name,job_id=ident,cpu_ns=observed,quantum_ns=quantum,elapsed_seconds=int(elapsed),state=state,exit_code=exitcode)
    require(set(found)==ids,'Every registered allocation required')
    result={}
    for key,e in jobs.items():
        row=found[e['job_id']];require(row['name']==e['name'],'Job name differs from registration');result[key]=row
    return result

def reconcile(entry,scheduler,*,program_sha,operation,own_cap,aggregate_cap,worker=None,rss_key='maximum_rss_kib'):
    require(entry['status']=='complete' and entry['error'] is None and entry['job_id']==scheduler['job_id']
        and entry['program_sha256']==program_sha and entry['operation']==operation,'Actual successful entry identity differs')
    own=integer(entry['process_cpu_ns'],'own CPU');child=integer(entry['waited_child_cpu_ns'],'child CPU');total=own+child
    require(own<=own_cap*10**9 and total<=aggregate_cap*10**9,'Observed entry CPU exceeds reservation')
    require(scheduler['cpu_ns']+scheduler['quantum_ns']+2>=total and scheduler['cpu_ns']<=aggregate_cap*10**9,'Scheduler CPU cannot contain entry or exceeds reservation')
    require(integer(entry['elapsed_ns'],'entry duration')<=(scheduler['elapsed_seconds']+1)*10**9,'Scheduler duration cannot contain entry')
    require(integer(entry[rss_key],'entry RSS')*1024<=16*2**30,'Observed RSS exceeds memory allowance')
    measured=helpers=0
    if worker is not None:
        usage=worker['resource_usage'];debit=worker['budget_debit'];limits=worker['limits']
        measured=integer(usage['total_cpu_ns'],'sealed CPU')
        require(measured==integer(usage['user_cpu_ns'],'user CPU')+integer(usage['system_cpu_ns'],'system CPU')
            and child+2>=measured,'Waited children omit sealed worker CPU')
        require(worker['outcome']==dict(status='complete',returncode=0) or
            worker['outcome'].get('status')=='complete' and worker['outcome'].get('returncode')==0,'Successful sealed worker required')
        require(debit['state']=='settled' and debit['observed_cpu_ns']==measured
            and debit['reserved_cpu_seconds']==limits['cpu_seconds']+2
            and debit['charged_cpu_seconds']==max(1,(measured+10**9-1)//10**9)<=debit['reserved_cpu_seconds']
            and worker['budget_reservation_overrun'] is False,'Actual sealed debit differs')
        helpers=max(0,child-measured)
        require(own+helpers<=own_cap*10**9,'Controller plus helper children exceed separate allowance')
        require(integer(usage['max_rss_kib'],'worker RSS')*1024<=16*2**30,'Worker RSS exceeds allowance')
    return dict(job_id=scheduler['job_id'],observed_process_tree_cpu_ns=total,own_cpu_ns=own,
        waited_child_cpu_ns=child,sealed_worker_cpu_ns=measured,nonworker_child_cpu_ns=helpers,
        scheduler_cpu_ns=scheduler['cpu_ns'],scheduler_reporting_quantum_ns=scheduler['quantum_ns'],
        overlapping_clocks_not_summed=True)
