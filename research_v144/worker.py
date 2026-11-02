"""Single-use read-only saved-output audit; no model inference."""
from pathlib import Path
import os,sys,json,hashlib,time,resource,platform,signal,traceback,unittest
RUN=Path(__file__).resolve().parents[1];sys.path.insert(0,str(RUN))
def identity(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def save(p,o):
 with p.open('x') as f:json.dump(o,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def main(phase,h):
 start=time.monotonic();raw=(RUN/'program.json').read_bytes();assert identity(raw)['sha256']==h;p=json.loads(raw)
 assert phase=='checks' and p['directory']==str(RUN) and sys.platform=='linux' and platform.node()=='csis.mn1'
 j=json.loads((RUN/'jobs-initial.json').read_bytes());assert str(j['jobs'][phase])==os.environ['SLURM_JOB_ID'] and j['registration_sha256']==h
 c=p['phases'][phase];resource.setrlimit(resource.RLIMIT_CPU,(c['cpu_seconds'],c['cpu_seconds']+1));resource.setrlimit(resource.RLIMIT_AS,(p['memory_bytes'],)*2);resource.setrlimit(resource.RLIMIT_FSIZE,(16*2**20,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
 def expire(*a):raise TimeoutError('Registered software limit reached')
 signal.signal(signal.SIGALRM,expire);signal.signal(signal.SIGXCPU,expire);signal.alarm(c['wall_seconds']-30)
 out=RUN/phase;out.mkdir(exist_ok=False);save(out/'attempt.json',dict(registration_sha256=h,job_id=os.environ['SLURM_JOB_ID']))
 result=dict(status='failed',registration_sha256=h,job_id=os.environ['SLURM_JOB_ID'],error=None,generated_software_only=False,calibration_repeated=False)
 try:
  assert platform.python_version()=='3.12.14' and not sys.flags.optimize
  for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):assert os.environ[k]=='1'
  for n,e in p['sources'].items():assert identity((RUN/n).read_bytes())==e,n
  import numpy as np,gmpy2,zstandard
  assert np.__version__=='2.3.5' and gmpy2.version()=='2.3.2' and zstandard.__version__=='0.25.0'
  tests=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('research_v144.test_audit'));assert tests.wasSuccessful() and tests.testsRun==6 and not tests.skipped
  from research_v144.audit import run
  answer=run(p);save(out/'saved-output-audit.json',answer)
  for n,e in p['sources'].items():assert identity((RUN/n).read_bytes())==e,n
  result.update(status='complete',result=answer)
 except BaseException as e:
  traceback.print_exc();result['error']=dict(type=type(e).__name__,message=str(e))
 finally:
  result.update(elapsed_seconds=time.monotonic()-start,process_cpu_seconds=time.process_time(),child_cpu_seconds=sum(resource.getrusage(resource.RUSAGE_CHILDREN)[:2]),peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,host=platform.node(),python=sys.version)
  result['artifacts']={f.name:identity(f.read_bytes()) for f in out.iterdir() if f.is_file()};save(out/'completion.json',result)
 assert result['status']=='complete',result['error']
if __name__=='__main__':main(*sys.argv[1:])
