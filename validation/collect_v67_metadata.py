"""Read-only bounded metadata collection; active snapshots are not terminal results.
Run remotely with Python3 and capture binary stdout to a new local file.
Never includes raw records, model/state/factor binaries or checkpoint weights.
"""
from pathlib import Path
import io,tarfile,json,hashlib,subprocess,datetime,sys
ROOT=Path('/nfs_home/users/poonam/second-20261010');RUN=ROOT/'local_runs/disjoint-service-v67-20261016-a'
SHA='11e0db146e79330852f550a1cc3b2dd7568a66cdfe8006b004dca3840149cc30'
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def info(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p,limit=8*2**20):
 assert p.is_file() and not any(q.is_symlink() for q in (p,*p.parents))
 before=p.stat();assert before.st_size<=limit
 raw=p.read_bytes();after=p.stat();assert len(raw)<=limit
 assert (before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_ino,after.st_size,after.st_mtime_ns)
 return raw
def cmd(*a):return subprocess.check_output(a,cwd=ROOT,text=True,timeout=30).strip()
p=json.loads(read(RUN/'program.json'));assert info(read(RUN/'program.json'))['sha256']==SHA
for group in ['prior_sources','new_sources','dependency_files','historical_ledgers']:
 for name,e in p[group].items():assert info(read(Path(name),128*2**20))==e,name
files={};volatile=[]
paths=[q for q in RUN.rglob('*') if q.is_file() and q.suffix in ['.json','.log','.py','.txt'] and 'outputs' not in q.relative_to(RUN).parts]
for trial in p['trial_order']:
 out=RUN/trial/'outputs'
 if out.is_dir():
  paths.extend(out.glob('progress-*.json'))
  for name in ['completion.json','execution-provenance.json','admission.json']:
   if (out/name).exists():paths.append(out/name)
for q in sorted(set(paths)):
 name=str(q.relative_to(RUN))
 try:files[name]=read(q)
 except AssertionError:volatile.append(name)
assert len(files)<1000 and sum(map(len,files.values()))<64*2**20
ids=['15261']+[r['job_id'] for r in json.loads(read(RUN/'chain-submission.json'))['jobs']]
accounting=cmd('sacct','-n','-P','-j',','.join(ids),'--format=JobIDRaw,JobName,State,ExitCode,Elapsed,TotalCPU,MaxRSS,NodeList,Start,End')
status=dict(schema='v67-metadata-snapshot',captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 program_sha256=SHA,accounting=accounting,queue=cmd('squeue','-h','-j',','.join(ids),'-o','%i|%j|%T|%M|%R'),
 frozen_sources_verified=469,volatile_files_omitted=volatile,
 numerical_binaries_copied=False,actual_model_state_audit_repeated_locally=False,
 terminal_receipts_present=all((RUN/(n+'-audit.json')).is_file() for n in ['primary','supplemental']),
 files={n:info(b) for n,b in files.items()})
files['collection.json']=canonical(status)
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as archive:
 for n,b in sorted(files.items()):
  entry=tarfile.TarInfo(n);entry.size=len(b);entry.mode=0o600;archive.addfile(entry,io.BytesIO(b))
