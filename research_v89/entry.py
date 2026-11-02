"""Pinned Slurm entry point. Empirical dispatch requires completed software gate."""
import sys
from pathlib import Path
ROOT=Path('/nfs_home/users/poonam/second-20261010');RUN=ROOT/'local_runs/four-cell-recovery-v89-20261023-a'
PRIOR=[ROOT/'local_runs'/n for n in ['complete-service-checks-v66-20261016-a','disjoint-data-v65-20261016-a','modern-service-checks-v64-20261016-a','lossless-control-v63-20261016-a']]
if __name__=='__main__':sys.path[:0]=[str(PRIOR[-1]/'deps'),str(RUN),*map(str,PRIOR),str(ROOT)]
import json,os,resource,signal,time,traceback,unittest,platform,datetime

def main(operation,expected,*arguments):
    start=time.perf_counter_ns();cpu=time.process_time_ns();child=resource.getrusage(resource.RUSAGE_CHILDREN)
    from research_v89.config import design,TRIALS
    from research_v80.io import require,write,json_read,info
    require(sys.platform=='linux' and Path(__file__).resolve()==RUN/'research_v89/entry.py' and os.environ.get('SLURM_JOB_ID','').isdigit(),'Pinned Linux Slurm entry required')
    require(operation in ['checks','run','primary','supplemental'],'Unknown operation')
    require(platform.node()==design()['slurm_host'],'Registered CPU host required')
    require(len(arguments)==(1 if operation=='run' else 0),'Wrong argument count')
    if operation=='run':require(arguments[0] in TRIALS,'Unknown trial')
    resource.setrlimit(resource.RLIMIT_AS,(16*2**30,)*2);resource.setrlimit(resource.RLIMIT_FSIZE,(2*2**30,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    soft,hard=(300,301) if operation=='checks' else (600,16802) if operation=='run' else (7200,7201) if operation=='primary' else (3600,3601)
    resource.setrlimit(resource.RLIMIT_CPU,(soft,hard))
    def cpu_exceeded(*unused):raise RuntimeError('Registered entry/controller CPU allowance exceeded')
    signal.signal(signal.SIGXCPU,cpu_exceeded)
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:require(os.environ.get(k)=='1','One thread required')
    program=RUN/'program.json';p=json_read(program)
    require(info(program.read_bytes())['sha256']==expected and all(p.get(k)==v for k,v in design().items()),'Frozen registered program differs')
    require(json_read(RUN/'registration.json')==dict(program_sha256=expected),'Registration commitment differs')
    name=operation if operation!='run' else arguments[0]
    write(RUN/(name+'-entry-start.json'),dict(program_sha256=expected,job_id=os.environ['SLURM_JOB_ID'],operation=operation,arguments=list(arguments),
        started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),hostname=platform.node(),affinity_cpus=sorted(os.sched_getaffinity(0))))
    result=None;error=None;mapping=None
    try:
        from research_v89.mapping import verify as verify_mapping
        mapping=verify_mapping(json_read(RUN/(name+'-host-start.json')),expected,operation,arguments)
        from research_v89 import campaign
        if operation=='checks':
            campaign.verify(software=False)
            suite=unittest.defaultTestLoader.loadTestsFromNames(p['software_modules'])
            tests=unittest.TextTestRunner(verbosity=2).run(suite)
            result=dict(tests=tests.testsRun,skipped=len(tests.skipped),errors=len(tests.errors),failures=len(tests.failures))
            require(tests.wasSuccessful() and tests.testsRun==p['expected_tests'] and not tests.skipped,'Exact-count Linux software gate failed')
            campaign.verify_bindings(p)
        elif operation=='run':campaign.run(arguments[0])
        else:
            from research_v89 import audit
            audit.main(operation)
    except BaseException as exc:error=dict(type=type(exc).__name__,message=str(exc));traceback.print_exc()
    now=resource.getrusage(resource.RUSAGE_CHILDREN);child_ns=round((now.ru_utime+now.ru_stime-child.ru_utime-child.ru_stime)*1e9);own=time.process_time_ns()-cpu
    if own>(soft+1)*10**9:error=dict(type='ControllerBudgetExceeded',message='Observed entry CPU above registered allowance')
    if operation=='checks' and own+child_ns>602*10**9:error=dict(type='SoftwareBudgetExceeded',message='Observed process and child CPU above software allowance')
    if operation in ('primary','supplemental') and own+child_ns>(soft+1)*10**9:error=dict(type='AuditBudgetExceeded',message='Aggregate audit CPU above registered limit')
    sealed_worker_cpu_ns=None
    if operation=='run' and error is None:
        sealed=json_read(RUN/name/'worker/result.json')
        require(sealed['outcome']['status']=='complete' and sealed['budget_debit']['state']=='settled','Successful sealed debit required')
        sealed_worker_cpu_ns=sealed['resource_usage']['total_cpu_ns']
        require(sealed_worker_cpu_ns==sealed['budget_debit']['observed_cpu_ns'] and sealed_worker_cpu_ns<=child_ns,'Worker CPU containment differs')
    receipt=dict(status='complete' if error is None else 'failed',error=error,program_sha256=expected,
        job_id=os.environ['SLURM_JOB_ID'],operation=operation,arguments=list(arguments),
        container_storage_mapping=mapping,hostname=platform.node(),affinity_cpus=sorted(os.sched_getaffinity(0)),finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        process_cpu_ns=own,waited_child_cpu_ns=child_ns,elapsed_ns=time.perf_counter_ns()-start,
        sealed_worker_cpu_ns=sealed_worker_cpu_ns,
        maximum_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        child_cpu_is_numerical_ledger_work=operation=='run',cpu_limits=[soft,hard])
    if result is not None:receipt.update(result,empirical_execution=False)
    write(RUN/('software-completion.json' if operation=='checks' else name+'-entry.json'),receipt,maximum=64*2**20)
    require(error is None,'One-use entry failed; no automatic retry')

if __name__=='__main__':main(*sys.argv[1:])
