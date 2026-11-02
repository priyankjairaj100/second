"""Separate bounded post-exit reporting job, after all eight V69 phases.

The external observer must subsequently check this job's own terminal scheduler
row with verify_observer. Transport and the external reporting observer are
outside the registered compute measurement, explicitly rather than recursively
claiming to measure the accounting operation itself.
"""
import sys
from pathlib import Path
if __name__=='__main__':
    root=Path('/nfs_home/users/poonam/second-20261010')
    names=['untouched-quality-v69-20261016-a','quality-data-v68-20261016-a',
        'disjoint-service-v67-20261016-a','complete-service-checks-v66-20261016-a',
        'disjoint-data-v65-20261016-a','modern-service-checks-v64-20261016-a','lossless-control-v63-20261016-a']
    sys.path[:0]=[str(root/'local_runs/lossless-control-v63-20261016-a/deps'),
        *[str(root/'local_runs'/n) for n in names],str(root)]
import os,platform,resource,signal,subprocess,time,traceback
from research_v67.io import read,write,json_read,require,info
from research_v69 import campaign as c,cost_accounting as costs,execution_gate as gate
from src.run_store import canonical_json,digest
from src.worker_control import THREAD_VARIABLES


def audit(p,raw):
    registration=digest(canonical_json(p));jobs={name:c.job(p,name)['job_id'] for name in c.ORDER}
    scheduler=costs.scheduler_rows(raw,jobs);ledger=c.snapshot(p);rows={};outputs={}
    for phase in c.ORDER:
        entry=json_read(c.RUN/phase/'entry.json')
        require(len(entry['affinity_cpus'])==1,'Actual single-CPU controller receipt required')
        identity=c.worker_identity(p,phase,entry['affinity_cpus'][0],ledger)
        worker=costs.worker(c.RUN/phase/'worker',identity,ledger)
        rows[phase]=costs.reconcile(phase,entry,worker,scheduler[phase],registration_sha256=registration)
    accounting=costs.complete(rows,ledger)
    # Fully accounted execution failures stay explicit. No loss/statistic is
    # inferred from them and no missing worker is invented to fill the census.
    result=dict(accounting=accounting,actual_artifacts_verified=False,quality_guard_pass=None,
        ledger=info(read(c.RUN/'budget/ledger.json',maximum=2**20)),phases={})
    if accounting['execution_successful']:
        for phase in c.ORDER:
            outputs[phase]=c.finished(p,phase)
            result['phases'][phase]=info(read(c.RUN/phase/'outputs/completion.json',maximum=64*2**20))
        terminal=outputs['terminal']['result']
        require(terminal['status']=='verified_actual_artifacts'
            and terminal['sequential_actual_saved_codes_reaudited'] is True
            and terminal['actual_checkpoint_parameter_audit']['actual_checkpoint_reference_compared'] is True
            and terminal['loss_audit']['status']=='verified'
            and terminal['loss_audit']['actual_loss_files_compared']==1920
            and terminal['loss_audit']['actual_cpu_reference_audit']['actual_loss_files_compared']==24
            and terminal['loss_audit']['statistics_recomputed'] is True
            and type(terminal['quality_guard_pass']) is bool,'Complete actual terminal artifact evidence required')
        result.update(actual_artifacts_verified=True,quality_guard_pass=terminal['quality_guard_pass'])
    return result


def verify_observer(receipt,raw,*,registration_sha256,closure_job):
    """Cheap saved-receipt check after closure exit, without rerunning any phase."""
    require(receipt['schema']=='quality-post-exit-closure-v69' and receipt['registration_sha256']==registration_sha256
        and receipt['job_id']==closure_job and receipt['status']=='complete' and receipt['error'] is None,
        'Complete bound post-exit closure required')
    row=costs.scheduler_rows(raw,{'closure':closure_job})['closure'];policy=gate.design()['post_exit_closure']
    require(row['state']=='COMPLETED' and row['exit_code']=='0:0','Successful terminal closure allocation required')
    for key in ['process_cpu_ns','waited_child_cpu_ns','elapsed_ns','maximum_rss_kib']:
        costs.integer(receipt[key],key)
    total=receipt['process_cpu_ns']+receipt['waited_child_cpu_ns']
    require(total<=policy['cpu_allowance_seconds']*10**9
        and total<=row['total_cpu_ns']+row['reporting_quantum_ns']
        and row['total_cpu_ns']<=policy['cpu_allowance_seconds']*10**9
        and receipt['elapsed_ns']<=(row['elapsed_seconds']+1)*10**9
        and row['elapsed_seconds']<=policy['wall_seconds']
        and receipt['maximum_rss_kib']*1024<=policy['address_space_bytes']
        and receipt['whole_process_and_all_waited_children_included'] is True,
        'Complete bounded closure CPU, scheduler, wall and memory evidence required')
    a=receipt['result']['accounting']
    require(a['status']=='verified_complete_cost_accounting' and set(a['phases'])==set(c.ORDER)
        and closure_job not in {r['job_id'] for r in a['phases'].values()},
        'Separate closure cannot duplicate an experimental allocation')
    return dict(status='verified_complete_registered_campaign',
        all_registered_execution_succeeded=a['execution_successful'],
        actual_artifacts_verified=receipt['result']['actual_artifacts_verified'],
        quality_guard_pass=receipt['result']['quality_guard_pass'],
        eight_phase_scheduler_cpu_ns=a['scheduler_cpu_ns'],closure_scheduler_cpu_ns=row['total_cpu_ns'],
        total_registered_scheduler_cpu_ns=a['scheduler_cpu_ns']+row['total_cpu_ns'],
        eight_worker_charged_cpu_seconds=a['worker_charged_cpu_seconds'],
        eight_controller_charged_cpu_seconds=a['controller_charged_cpu_seconds'],
        closure_charged_cpu_seconds=max(1,(total+999999999)//10**9),
        total_registered_cpu_allowance_seconds=44424+policy['cpu_allowance_seconds'],
        scope='Eight registered workers/controllers plus separate bounded closure allocation; transport and external reporting observer excluded',
        negative_quality_is_completed_evidence=True)


def main(expected):
    tick=time.perf_counter_ns();p=c.load(expected);j=c.job(p,'closure');policy=gate.design()['post_exit_closure']
    require(sys.platform=='linux' and platform.node()=='csis.mn1' and sys.dont_write_bytecode
        and sys.flags.optimize==0 and Path(__file__).resolve()==c.RUN/'research_v69/closure.py'
        and os.environ.get('SLURM_JOB_ID')==j['job_id'] and all(os.environ.get(n)=='1' for n in THREAD_VARIABLES)
        and not os.environ.get('LD_PRELOAD') and not os.environ.get('LD_AUDIT'),
        'Pinned one-thread Linux closure job required')
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    def expired(*unused):raise TimeoutError('Post-exit closure CPU ceiling reached')
    signal.signal(signal.SIGXCPU,expired)
    for key,pair in [(resource.RLIMIT_CPU,(policy['cpu_soft_seconds'],policy['cpu_hard_seconds'])),
        (resource.RLIMIT_AS,(policy['address_space_bytes'],)*2),(resource.RLIMIT_FSIZE,(policy['file_size_bytes'],)*2),
        (resource.RLIMIT_CORE,(0,0))]:resource.setrlimit(key,pair)
    directory=c.RUN/'closure';write(directory/'start.json',dict(registration_sha256=expected,job=j,policy=policy))
    r=dict(schema='quality-post-exit-closure-v69',registration_sha256=expected,job_id=j['job_id'],status='running',error=None,result=None)
    try:
        x=c.verify(p,'terminal');gate.imported_sources(x['registered_sources'])
        jobs=[c.job(p,name)['job_id'] for name in c.ORDER]
        raw=subprocess.check_output(['sacct','-n','-P','-j',','.join(jobs),
            '--format=JobIDRaw,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS'],text=True,timeout=30)
        require(len(raw)<=128*2**10,'Bounded actual scheduler response required')
        write(directory/'scheduler.txt',raw.encode('ascii'),raw=True,maximum=128*2**10)
        r['result']=audit(p,raw);gate.imported_sources(x['registered_sources']);r['status']='complete'
    except BaseException as exc:
        r.update(status='failed',error=dict(type=type(exc).__name__,message=str(exc)));traceback.print_exc()
    child=resource.getrusage(resource.RUSAGE_CHILDREN);own=time.process_time_ns()
    r.update(process_cpu_ns=own,waited_child_cpu_ns=round((child.ru_utime+child.ru_stime)*10**9),
        elapsed_ns=time.perf_counter_ns()-tick,maximum_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        whole_process_and_all_waited_children_included=True,
        own_final_write_shutdown_and_terminal_scheduler_row_still_require_external_observation=True)
    if own+r['waited_child_cpu_ns']>policy['cpu_allowance_seconds']*10**9:
        r.update(status='failed',error=dict(type='ClosureBudgetExceeded',message='Closure plus child CPU exceeded allowance'))
    write(directory/'receipt.json',r);require(r['status']=='complete','Post-exit closure failed; preserve without retry')


if __name__=='__main__':main(*sys.argv[1:])
