"""One administrative release of existing held15394; no sbatch, retry or resource change."""
import json,hashlib,os,subprocess
from pathlib import Path
ROOT=Path('/nfs_home/users/poonam/second-20261010');RUN=ROOT/'local_runs/cuda-runtime-v69-20261018-a';JOB='15394'
def cmd(a):return subprocess.check_output(a,cwd=ROOT,text=True,timeout=30).strip()
def save(n,o):
 with (RUN/n).open('x') as f:json.dump(o,f,sort_keys=True,separators=(',',':'));f.flush();os.fsync(f.fileno())
raw=(RUN/'program.json').read_bytes();assert hashlib.sha256(raw).hexdigest()=='5c9f75e196b822dfe7f0297646b24f50ce3a70164ef4758d59ac85e36d223a0b';p=json.loads(raw)
assert json.loads((RUN/'submission-response.json').read_bytes())==dict(returncode=0,stderr='',stdout=JOB+'\n')
assert not any((RUN/n).exists() for n in ['attempt.json','receipt.json','release-intent.json','release-response.json'])
for n,h in p['new_sources'].items():assert hashlib.sha256((RUN/n).read_bytes()).hexdigest()==h
for n,h in p['sources'].items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h
raw=cmd(['scontrol','show','job',JOB,'-o']);f=dict(x.split('=',1) for x in raw.split())
want=dict(JobId=JOB,JobName='second69-runtime',JobState='PENDING',Reason='JobHeldUser',Requeue='0',Restarts='0',NumCPUs='1',NumNodes='1-1',NumTasks='1',Partition='gpu-short',Account='faculty',QOS='cpu-short',TimeLimit='00:15:00',MinMemoryNode='16G',TresPerNode='gres/gpu:a100-80gb:1',ReqNodeList='(null)',Dependency='(null)',RunTime='00:00:00',ReqTRES='cpu=1,mem=16G,node=1,billing=1,gres/gpu=1',WorkDir=str(ROOT),Command=str(RUN/'capture_v69_cuda_runtime.sbatch'))
assert all(f.get(k)==v for k,v in want.items()) and f['CPUs/Task']=='1'
assert set(cmd(['scontrol','show','hostnames',f['ExcNodeList']]).splitlines())=={'csis.mn1','csis.cn2'}
assert cmd(['squeue','-h','-u','poonam','-o','%i|%j|%T'])==JOB+'|second69-runtime|PENDING'
save('administrative-release-intent.json',dict(job_id=JOB,verified_fields=want,raw=raw,reason='Original launcher refused the equivalent singleton NumNodes=1-1 display before any release or numerical attempt. This separate once-only administrative action releases the existing unchanged allocation; it does not resubmit or alter caps.',script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),automatic_retry=False))
r=subprocess.run(['scontrol','release',JOB],cwd=ROOT,capture_output=True,text=True,timeout=30)
save('administrative-release-response.json',dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0
print('Released existing held runtime inventory job15394 once')
