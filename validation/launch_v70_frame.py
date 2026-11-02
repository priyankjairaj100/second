"""Once-only independently registered V70 saved-frame audit launcher."""
import json,hashlib,subprocess,os,sys
from pathlib import Path
ROOT=Path('/nfs_home/users/poonam/second-20261010');RUN=ROOT/'local_runs/quality-frame-audit-v70-20261018-a'
def cmd(a):return subprocess.check_output(a,cwd=ROOT,text=True,timeout=30).strip()
def save(n,o):
 with (RUN/n).open('x') as f:json.dump(o,f,sort_keys=True,separators=(',',':'));f.flush();os.fsync(f.fileno())
def main(h):
 raw=(RUN/'program.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==h;p=json.loads(raw)
 assert cmd(['git','rev-parse','HEAD'])=='f900999fcb200509dfad4fc081ce9c87fd172a16' and not cmd(['git','status','--porcelain'])
 assert not any('second' in x.lower() for x in cmd(['squeue','-h','-u','poonam','-o','%i|%j|%T']).splitlines())
 for group in ['frozen_sources','new_sources','dependencies']:
  for n,e in p[group].items():
   raw=Path(n).read_bytes();assert dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())==e
 accounting=cmd(['sacct','-n','-P','-j',','.join(str(x) for x in range(15395,15404)),'--format=JobIDRaw,State,ExitCode'])
 rows={a[0]:a[1:3] for row in accounting.splitlines() if (a:=row.split('|')) and a[0].isdigit()}
 assert rows['15395']==['FAILED','1:0'] and set(rows)=={str(x) for x in range(15395,15404)} and all(rows[str(x)][0]=='CANCELLED' for x in range(15396,15404))
 args=['sbatch','--parsable','--hold','--no-requeue','--nodes=1','--ntasks=1','--cpus-per-task=1','--partition=cpu-short','--qos=cpu-short','--account=faculty','--nodelist=csis.mn1','--mem=4G','--time=00:20:00','--job-name=second70-frame-audit','--output='+str(RUN/'slurm-%j.log'),'cluster_setup/run_cpu.sbatch',str(ROOT/'local_runs/cluster-setup-20261010/container-13155.sha256'),str(RUN/'research_v70/audit_frame.py'),h]
 save('submission-intent.json',dict(arguments=args,registration_sha256=h,prior_failed_chain_accounting=accounting,automatic_retry=False))
 env={k:v for k,v in os.environ.items() if not k.startswith('SBATCH_')}
 r=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True,timeout=30);save('submission-response.json',dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr));job=r.stdout.strip();assert r.returncode==0 and job.isdigit()
 raw=cmd(['scontrol','show','job',job,'-o']);f=dict(x.split('=',1) for x in raw.split());want=dict(JobId=job,JobState='PENDING',Reason='JobHeldUser',Requeue='0',Restarts='0',NumCPUs='1',NumTasks='1',ReqNodeList='csis.mn1',MinMemoryNode='4G',TimeLimit='00:20:00',Partition='cpu-short',Account='faculty',QOS='cpu-short')
 assert all(f.get(k)==v for k,v in want.items()) and f['NumNodes'] in ['1','1-1'] and f['CPUs/Task']=='1' and f['ReqTRES']=='cpu=1,mem=4G,node=1,billing=1'
 save('held-verification.json',dict(raw=raw,job_id=job,verified=True));save('release-intent.json',dict(job_id=job,automatic_retry=False))
 r=subprocess.run(['scontrol','release',job],cwd=ROOT,capture_output=True,text=True,timeout=30);save('release-response.json',dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0
 print(json.dumps(dict(job_id=job,status='released_once',registration_sha256=h)))
if __name__=='__main__':main(*sys.argv[1:])
