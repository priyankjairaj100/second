"""Exclusive bounded runtime-inventory launch; never repeats an uncertain call."""
import sys,os,json,hashlib,subprocess
from pathlib import Path
ROOT=Path('/nfs_home/users/poonam/second-20261010');RUN=ROOT/'local_runs/cuda-runtime-v69-20261018-a'
def save(n,o):
 with (RUN/n).open('x') as f:json.dump(o,f,sort_keys=True,separators=(',',':'));f.flush();os.fsync(f.fileno())
def cmd(a):return subprocess.check_output(a,cwd=ROOT,text=True,timeout=30).strip()
def main(h):
 raw=(RUN/'program.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==h;p=json.loads(raw)
 assert cmd(['git','rev-parse','HEAD'])=='f900999fcb200509dfad4fc081ce9c87fd172a16' and not cmd(['git','status','--porcelain'])
 assert not any('second' in r.lower() for r in cmd(['squeue','-h','-u','poonam','-o','%i|%j|%T']).splitlines())
 for n,s in p['sources'].items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==s
 for n,s in p['new_sources'].items():assert hashlib.sha256((RUN/n).read_bytes()).hexdigest()==s
 args=['sbatch','--parsable','--hold','--no-requeue','--nodes=1','--ntasks=1','--cpus-per-task=1','--partition=gpu-short','--qos=cpu-short','--account=faculty','--mem=16G','--time=00:15:00','--gres=gpu:a100-80gb:1','--exclude=csis.mn1,csis.cn2','--job-name=second69-runtime','--chdir='+str(ROOT),'--output='+str(RUN/'slurm-%j.log'),str(RUN/'capture_v69_cuda_runtime.sbatch'),h]
 save('submission-intent.json',dict(arguments=args,registration_sha256=h,automatic_retry=False))
 env={k:v for k,v in os.environ.items() if not k.startswith('SBATCH_')}
 r=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
 save('submission-response.json',dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr));job=r.stdout.strip()
 assert r.returncode==0 and job.isdigit()
 raw=cmd(['scontrol','show','job',job,'-o']);f=dict(x.split('=',1) for x in raw.split())
 want=dict(JobId=job,JobName='second69-runtime',JobState='PENDING',Reason='JobHeldUser',Requeue='0',Restarts='0',NumCPUs='1',NumNodes='1',NumTasks='1',Partition='gpu-short',Account='faculty',QOS='cpu-short',TimeLimit='00:15:00',MinMemoryNode='16G',TresPerNode='gres/gpu:a100-80gb:1',ReqNodeList='(null)')
 assert all(f.get(k)==v for k,v in want.items()),{k:f.get(k) for k in want}
 assert set(cmd(['scontrol','show','hostnames',f['ExcNodeList']]).splitlines())=={'csis.mn1','csis.cn2'}
 save('held-verification.json',dict(raw=raw,job_id=job,verified=True))
 save('release-intent.json',dict(job_id=job,automatic_retry=False))
 r=subprocess.run(['scontrol','release',job],cwd=ROOT,capture_output=True,text=True,timeout=30)
 save('release-response.json',dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0
 print(json.dumps(dict(job_id=job,status='released_once',registration_sha256=h)))
if __name__=='__main__':main(*sys.argv[1:])
