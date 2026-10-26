"""Pinned fresh entry, with separated software-child/target/host CPU clocks."""
import sys
from pathlib import Path
if __name__=='__main__':
    base=Path('/nfs_home/users/poonam/second-20261010');run=Path(__file__).resolve().parents[1]
    sys.path[:0]=[str(run),str(base/'local_runs/lossless-control-v63-20261016-a/deps'),str(base)]
import datetime,os,platform,resource,signal,subprocess,time,traceback
from research_v80.io import json_read,require
from research_v103.config import ROOT,RUN,OPERATIONS as ORDER,TRIALS as PROFILES,cpu,name
from research_v103 import protocol
from research_v103.records import writer
from research_v103.mapping import verify as verify_mapping


def children_ns():
    u=resource.getrusage(resource.RUSAGE_CHILDREN)
    return round((u.ru_utime+u.ru_stime)*10**9)


def main(operation,expected):
    tick=time.perf_counter_ns();before=children_ns()
    require(sys.platform=='linux' and platform.node()=='csis.mn1' and Path(__file__).resolve()==RUN/'research_v103/entry.py'
        and os.environ.get('SLURM_JOB_ID','').isdigit() and operation in ORDER,'Literal pinned Linux operation required')
    resource.setrlimit(resource.RLIMIT_AS,(16*2**30,)*2);resource.setrlimit(resource.RLIMIT_FSIZE,(2*2**30,)*2)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,cpu(operation)[:2])
    def exceeded(*unused):raise RuntimeError('Admission controller CPU limit exceeded')
    signal.signal(signal.SIGXCPU,exceeded);os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
        require(os.environ.get(k)=='1','One thread required')
    key=name(operation);records=writer();records.write(key+'-entry-start.json',dict(operation=operation,arguments=[],program_sha256=expected,
        job_id=os.environ['SLURM_JOB_ID'],started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    error=None;result=None;mapping=None;software_cpu=0;target_cpu=0
    try:
        from research_v103 import campaign
        p=campaign.verify(prerequisite=False)
        require(campaign.sha(RUN/'program.json')==expected,'Exact program identity required')
        protocol.allocation(operation,expected,os.environ['SLURM_JOB_ID'])
        mapping=verify_mapping(json_read(RUN/(key+'-host-start.json')),expected,operation,[])
        from research_v103.prior_run import check_host_binding
        check_host_binding(p,json_read(RUN/(key+'-host-start.json')),expected,operation,os.environ['SLURM_JOB_ID'])
        protocol.earlier(operation,expected);campaign.prerequisites(p)
        if operation=='checks':
            from research_v103.software import validate
            child_before=children_ns()
            # Child writes one bounded result; bootstrap captures its complete diagnostic log.
            env=dict(os.environ,PYTHONPATH=os.pathsep.join(sys.path))
            result_code=subprocess.run([sys.executable,'-B','-m','research_v103.software'],
                cwd=RUN,env=env,timeout=500).returncode
            software_cpu=children_ns()-child_before
            require(result_code==0,'Separate generated software child failed')
            result=json_read(RUN/'software-results.json');validate(result)
            campaign.verify(prerequisite=False)
        elif operation in PROFILES:
            campaign.run(operation,p,expected)
            sealed=json_read(RUN/operation/'worker/result.json')
            require(sealed['outcome']['status']=='complete' and sealed['budget_debit']['state']=='settled','Sealed numerical worker required')
            target_cpu=sealed['resource_usage']['total_cpu_ns']
            require(target_cpu==sealed['budget_debit']['observed_cpu_ns'],'Actual numerical debit differs')
        else:
            from research_v103 import audit
            audit.main(operation)
    except BaseException as exc:
        error=dict(type=type(exc).__name__)
        error['message']=str(exc);traceback.print_exc()
    own=time.process_time_ns();child=children_ns()-before
    if own>(cpu(operation)[0]+1)*10**9 or child<target_cpu+software_cpu:
        error=dict(type='ControllerCPUOrContainmentFailure')
    if operation=='checks' and own+child>598*10**9:error=dict(type='SoftwareAggregateExceeded')
    if operation in ('primary','supplemental') and own+child>cpu(operation)[2]*10**9:error=dict(type='AuditAggregateExceeded')
    receipt=dict(status='complete' if error is None else 'failed',error=error,result=result,
        program_sha256=expected,job_id=os.environ['SLURM_JOB_ID'],operation=operation,arguments=[],
        container_storage_mapping=mapping,process_cpu_ns=own,waited_child_cpu_ns=child,
        sealed_worker_cpu_ns=target_cpu,software_tree_cpu_ns=software_cpu,elapsed_ns=time.perf_counter_ns()-tick,
        maximum_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,empirical_execution=operation in PROFILES,cpu_limits=list(cpu(operation)[:2]),hostname=platform.node(),affinity_cpus=sorted(os.sched_getaffinity(0)))
    records.write(key+'-entry.json',receipt)
    require(error is None,'One-use admission entry failed; no retry')


if __name__=='__main__':main(*sys.argv[1:])
