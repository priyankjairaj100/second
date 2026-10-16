"""One-use V69 worker. Absent registration/admission fails before dispatch."""
import sys
from pathlib import Path
if __name__=='__main__':
    root=Path('/nfs_home/users/poonam/second-20261010')
    names=['untouched-quality-v69-20261016-a','quality-data-v68-20261016-a',
        'disjoint-service-v67-20261016-a','complete-service-checks-v66-20261016-a',
        'disjoint-data-v65-20261016-a','modern-service-checks-v64-20261016-a','lossless-control-v63-20261016-a']
    sys.path[:0]=[str(root/'local_runs/lossless-control-v63-20261016-a/deps'),
        *[str(root/'local_runs'/n) for n in names],str(root)]
import os,platform,time,traceback
from research_v67.io import write,require
from research_v69 import campaign as c,execution_gate as gate
from src.transaction_timing import verify_command_admission


def main(phase,expected):
    require(sys.platform=='linux' and Path(__file__).resolve()==c.RUN/'research_v69/worker.py'
        and sys.dont_write_bytecode and sys.flags.optimize==0,'Pinned unoptimized Linux worker required')
    p=c.load(expected);binding=c.job(p,phase)
    require(os.environ.get('SLURM_JOB_ID')==binding['job_id'],'Actual held/bound job differs')
    admission=verify_command_admission(expected,'quality',c.command(p,phase))
    require(Path(admission['phase_budget_root'])==c.RUN/'budget' and admission['cwd']==str(c.ROOT),
        'Exact campaign allowance required')
    live=c.snapshot(p)['attempts'][admission['attempt_id']]
    require(live['reserved_cpu_seconds']==gate.CAPS[phase]['cpu_seconds']+2,
        'Exact phase reservation must precede execution')
    out=c.RUN/phase/'outputs';out.mkdir(exist_ok=False);tick=time.perf_counter_ns()
    r=dict(schema='quality-phase-worker-v69',phase=phase,registration_sha256=expected,
        job_id=binding['job_id'],hostname=platform.node(),status='running',error=None,result=None)
    try:
        x=c.verify(p,phase);r['runtime']=x['runtime']
        previous=c.predecessors(p,phase,active_attempt_id=admission['attempt_id'])
        from research_v69.phase_flow import run
        gate.imported_sources(x['registered_sources'])
        r['result']=run(phase,p,x,previous,out,c.RUN,expected)
        # Do not recapture a fresh-CUDA runtime after device initialization.
        # Rehash the immutable admitted files and all actually imported sources.
        for path,e in x['registered_sources'].items():c.read(path,e,maximum=128*2**20,retain=False)
        r['imports']=gate.imported_sources(x['registered_sources'])
        c.inputs(p)
        r['status']='complete'
    except BaseException as exc:
        r.update(status='failed',error=dict(type=type(exc).__name__,message=str(exc)))
        traceback.print_exc();raise
    finally:
        r.update(elapsed_ns=time.perf_counter_ns()-tick,partial_outputs_preserved=r['status']!='complete',
            clock_scope='Phase body; complete worker CPU includes startup, verification, final writes and shutdown in sealed wait4 receipt')
        write(out/'completion.json',r)


if __name__=='__main__':main(*sys.argv[1:])
