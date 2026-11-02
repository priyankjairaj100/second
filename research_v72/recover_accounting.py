"""One-use artifact/accounting recovery, never a retry of V71 closure.main."""
import sys,os,platform,resource,signal,time,json,hashlib
from pathlib import Path
ROOT=Path('/nfs_home/users/poonam/second-20261010')
RUN=ROOT/'local_runs/quality-cost-recovery-v72-20261018-a'
OLD=ROOT/'local_runs/untouched-quality-v71-20261018-a'
REG71='3ec767a20be59ed81330d68a067166bc14a369e967d9d3cbf274166baa32c56c'
CAPS=dict(cpu_soft=600,cpu_hard=601,cpu_allowance=602,memory=4*2**30,file=128*2**20,process_alarm=900,slurm_wall=1200)
def canonical(o):return json.dumps(o,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def info(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def save(name,value):
    with (RUN/name).open('xb') as f:f.write(canonical(value));f.flush();os.fsync(f.fileno())
def read(e):
    path=Path(e['path']);assert path.is_absolute() and not any(p.is_symlink() for p in (path,*path.parents))
    assert path.is_file() and path.stat().st_size<=64*2**20
    b=path.read_bytes();assert info(b)=={k:e[k] for k in ['bytes','sha256']};return b

def failed_closure(receipt,scheduler):
    from research_v71.cost_accounting import integer
    assert receipt['schema']=='quality-post-exit-closure-v71' and receipt['registration_sha256']==REG71
    assert receipt['job_id']=='15413' and receipt['status']=='failed' and receipt['result'] is None
    assert receipt['error']==dict(type='FileNotFoundError',message="[Errno 2] No such file or directory: 'sacct'")
    assert scheduler['job_id']=='15413' and scheduler['state']=='FAILED' and scheduler['exit_code']=='1:0'
    for k in ['process_cpu_ns','waited_child_cpu_ns','elapsed_ns','maximum_rss_kib']:integer(receipt[k],k)
    total=receipt['process_cpu_ns']+receipt['waited_child_cpu_ns']
    assert receipt['whole_process_and_all_waited_children_included'] is True
    assert total<=302*10**9 and total<=scheduler['total_cpu_ns']+scheduler['reporting_quantum_ns']
    assert scheduler['total_cpu_ns']<=302*10**9 and scheduler['elapsed_seconds']<=900
    assert receipt['elapsed_ns']<=(scheduler['elapsed_seconds']+1)*10**9
    assert receipt['maximum_rss_kib']*1024<=4*2**30
    return dict(status='original_failed_closure_preserved_and_costed',scheduler=scheduler,
        observed_process_and_children_cpu_ns=total,charged_cpu_seconds=max(1,(total+999999999)//10**9),
        original_closure_successful=False)

def main(expected):
    tick=time.perf_counter_ns();raw=(RUN/'program.json').read_bytes();p=json.loads(raw)
    assert canonical(p)==raw and info(raw)['sha256']==expected and p['directory']==str(RUN)
    assert p['schema']=='separate-accounting-recovery-registration-v72' and p['caps']==CAPS
    assert p['automatic_retry'] is False and p['original_registration_sha256']==REG71
    assert sys.platform=='linux' and platform.node()=='csis.mn1' and sys.dont_write_bytecode and sys.flags.optimize==0
    assert sys.executable==str(ROOT/'.venv-container/bin/python') and Path(__file__).resolve()==RUN/'research_v72/recover_accounting.py'
    job=json.loads((RUN/'job-binding.json').read_bytes())
    assert job['registration_sha256']==expected and job['job_id']==os.environ.get('SLURM_JOB_ID')
    assert job['submission_state']=='held-before-release'
    assert not os.environ.get('LD_PRELOAD') and not os.environ.get('LD_AUDIT')
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    def expired(*a):raise TimeoutError('Recovery resource ceiling reached')
    signal.signal(signal.SIGXCPU,expired);signal.signal(signal.SIGALRM,expired);signal.alarm(CAPS['process_alarm'])
    for k,v in [(resource.RLIMIT_CPU,(600,601)),(resource.RLIMIT_AS,(4*2**30,)*2),(resource.RLIMIT_FSIZE,(128*2**20,)*2),(resource.RLIMIT_CORE,(0,0))]:resource.setrlimit(k,v)
    save('attempt.json',dict(job_id=job['job_id'],registration_sha256=expected,affinity_cpus=sorted(os.sched_getaffinity(0)),caps=CAPS))
    receipt=dict(schema='separate-accounting-recovery-v72',status='failed',error=None,result=None,
        registration_sha256=expected,job_id=job['job_id'],original_campaign_successful=False,
        original_closure_retried=False,model_or_likelihood_execution=False)
    try:
        for group in ['frozen_sources','new_sources']:
            for n,e in p[group].items():read(dict(path=n,**e))
        names=['untouched-quality-v71-20261018-a','quality-data-v68-20261016-a','disjoint-service-v67-20261016-a',
               'complete-service-checks-v66-20261016-a','disjoint-data-v65-20261016-a','modern-service-checks-v64-20261016-a','lossless-control-v63-20261016-a']
        sys.path[:0]=[str(ROOT/'local_runs/lossless-control-v63-20261016-a/deps'),*[str(ROOT/'local_runs'/n) for n in names],str(ROOT)]
        from research_v71 import campaign as c, closure, cost_accounting as costs, execution_gate as gate
        from src.worker_control import THREAD_VARIABLES
        assert all(os.environ.get(n)=='1' for n in THREAD_VARIABLES)
        inputs={k:read(e) for k,e in p['inputs'].items()}
        old=c.load(REG71);assert canonical(old)==inputs['old_registration']
        x=c.verify(old,'terminal');registered=dict(p['frozen_sources'],**p['new_sources'])
        gate.imported_sources(registered)
        all_rows=costs.scheduler_rows(inputs['scheduler'].decode(),{**{phase:str(15405+i) for i,phase in enumerate(c.ORDER)},'failed_closure':'15413'})
        failure=failed_closure(json.loads(inputs['failed_receipt']),all_rows['failed_closure'])
        lines='\n'.join(line for line in inputs['scheduler'].decode().splitlines() if line.split('|')[0].split('.')[0]!='15413')
        result=closure.audit(old,lines)
        assert result['accounting']['execution_successful'] is True and result['actual_artifacts_verified'] is True
        assert result['ledger']==info(inputs['ledger'])
        result.update(original_failure=failure,original_nine_allocation_scheduler_cpu_ns=
            result['accounting']['scheduler_cpu_ns']+all_rows['failed_closure']['total_cpu_ns'],
            original_closure_successful=False,actual_original_outputs_rehashed=True,
            original_numerical_audits_not_reexecuted=True,new_recovery_cost_requires_external_terminal_observation=True)
        for k,e in p['inputs'].items():assert read(e)==inputs[k]
        for group in ['frozen_sources','new_sources']:
            for n,e in p[group].items():read(dict(path=n,**e))
        gate.imported_sources(registered);receipt.update(status='complete',result=result)
    except BaseException as e:receipt['error']=dict(type=type(e).__name__,message=str(e))
    child=resource.getrusage(resource.RUSAGE_CHILDREN)
    receipt.update(process_cpu_ns=time.process_time_ns(),waited_child_cpu_ns=round((child.ru_utime+child.ru_stime)*10**9),
        elapsed_ns=time.perf_counter_ns()-tick,max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        final_write_shutdown_and_wrapper_cpu_require_external_scheduler_observation=True)
    if receipt['process_cpu_ns']+receipt['waited_child_cpu_ns']>602*10**9:
        receipt.update(status='failed',error=dict(type='RecoveryBudgetExceeded',message='Whole process/children exceed allowance'))
    save('receipt.json',receipt);assert receipt['status']=='complete',receipt['error']
if __name__=='__main__':main(*sys.argv[1:])
