from pathlib import Path
import json,subprocess,datetime,hashlib,collections
root=Path('/nfs_home/users/poonam/second-20261010');run=root/'local_runs/matched-complete-recovery-v112-20261026-a'
def cmd(args):return subprocess.check_output(args,text=True,timeout=20)
program=(run/'program.json').read_bytes();assert hashlib.sha256(program).hexdigest()=='a73ca66d08b50feeccf9601d6d214b00ad21917ae900671cc35d373aef4f4381'
queue=cmd(['squeue','-u','poonam','-h','-o','%i|%j|%T|%M|%R'])
raw=cmd(['sacct','-nP','-j',','.join(str(i) for i in range(16407,16428)),'--format=JobIDRaw,JobName%60,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS,ReqMem,NodeList'])
counts=collections.Counter();out=run/'gpt2/reference_compressed-1/outputs'
for p in sorted(out.glob('progress-*.json')):
 assert p.stat().st_size<1024*1024
 d=json.loads(p.read_bytes());counts[d.get('phase','unknown')]+=1
completion=out/'completion.json'
result=dict(captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),program_sha256=hashlib.sha256(program).hexdigest(),queue=queue,scheduler_raw=raw,numerical_checkout=cmd(['git','-C',str(root),'rev-parse','HEAD']).strip(),numerical_status=cmd(['git','-C',str(root),'status','--porcelain']),first_request_progress_counts=dict(counts),first_request_completion=None if not completion.exists() else dict(bytes=completion.stat().st_size,sha256=hashlib.sha256(completion.read_bytes()).hexdigest()))
active={}
for line in queue.splitlines():
 row=line.split('|')
 if len(row)>2 and row[2]=='RUNNING' and row[1].startswith('second112-'):
  operation=row[1].removeprefix('second112-').replace('--','/')
  directory=run/operation/'outputs';phases=collections.Counter()
  for item in directory.glob('progress-*.json'):
   assert item.stat().st_size<1024*1024
   phases[json.loads(item.read_bytes()).get('phase','unknown')]+=1
  active[row[0]]=dict(operation=operation,progress_counts=dict(phases),completion_exists=(directory/'completion.json').exists())
result['active_worker_progress']=active
print(json.dumps(result,sort_keys=True))
