"""Bounded V71 controller; requires separately held and bound Slurm job."""
import sys
from pathlib import Path
if __name__=='__main__':
    root=Path('/nfs_home/users/poonam/second-20261010')
    names=['untouched-quality-v71-20261018-a','quality-data-v68-20261016-a',
        'disjoint-service-v67-20261016-a','complete-service-checks-v66-20261016-a',
        'disjoint-data-v65-20261016-a','modern-service-checks-v64-20261016-a','lossless-control-v63-20261016-a']
    sys.path[:0]=[str(root/'local_runs/lossless-control-v63-20261016-a/deps'),
        *[str(root/'local_runs'/n) for n in names],str(root)]
import platform,resource,time,traceback
from research_v67.io import write,require
from research_v71 import campaign as c,execution_gate as gate
from src.worker_control import run_limited


def main(phase,expected):
    tick=time.perf_counter_ns()
    require(Path(__file__).resolve()==c.RUN/'research_v71/entry.py','Pinned controller entry required')
    p=c.load(expected);j=c.job(p,phase);host=platform.node()
    require(host in p['hosts'][gate.kind(phase)],'Prospectively admitted host required')
    applied=gate.apply_controller_limits(phase,expected_job=j['job_id'],expected_host=host)
    # This exclusive intent precedes every attempted verification/launch. Even a
    # failed preflight cannot be retried by calling this entry again.
    write(c.RUN/phase/'entry-start.json',dict(registration_sha256=expected,phase=phase,job=j,applied=applied))
    r=dict(schema='quality-controller-entry-v71',registration_sha256=expected,phase=phase,job_id=j['job_id'],
        hostname=host,affinity_cpus=applied['affinity_cpus'],status='running',error=None,outputs=None)
    receipt=None
    try:
        x=c.verify(p,phase);c.predecessors(p,phase);gate.imported_sources(x['registered_sources'])
        require(not (c.RUN/phase/'worker').exists() and not (c.RUN/phase/'outputs').exists(),
            'Existing one-use worker/output path; retry forbidden')
        receipt=run_limited(c.command(p,phase),c.RUN/phase/'worker',gate.limits(phase,applied['affinity_cpus'][0]),
            identity=dict(registration_sha256=expected,phase=phase),cwd=c.ROOT,phase_budget=c.budget(p),phase='quality')
        require(receipt['outcome'].get('status')=='complete' and receipt['outcome'].get('returncode')==0,
            'One-use worker failed; preserve all outputs and debit')
        r['outputs']=c.output_census(c.RUN/phase/'outputs');r['status']='complete'
    except BaseException as exc:
        r.update(status='failed',error=dict(type=type(exc).__name__,message=str(exc)));traceback.print_exc()
    child=resource.getrusage(resource.RUSAGE_CHILDREN);own=time.process_time_ns()
    r.update(process_cpu_ns=own,waited_child_cpu_ns=round((child.ru_utime+child.ru_stime)*10**9),
        elapsed_ns=time.perf_counter_ns()-tick,maximum_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        whole_process_cpu_clock=True,all_waited_children_included=True,
        clock_scope='Whole controller Python process including imports and all waited children; final receipt write/shutdown included separately by scheduler')
    measured=receipt['resource_usage']['total_cpu_ns'] if receipt and receipt.get('resource_usage') else 0
    helpers=max(0,r['waited_child_cpu_ns']-measured)
    if r['waited_child_cpu_ns']+2<measured or own+helpers>(gate.CONTROLLER_CPU+1)*10**9:
        r.update(status='failed',error=dict(type='ControllerBudgetExceeded',message='Controller plus helper CPU allowance or child containment failed'))
    write(c.RUN/phase/'entry.json',r)
    require(r['status']=='complete','Registered phase failed; no retry')


if __name__=='__main__':main(*sys.argv[1:])
