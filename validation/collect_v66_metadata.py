from pathlib import Path
import hashlib,json,subprocess,tarfile,io,datetime
R=Path('/nfs_home/users/poonam/second-20261010');D=R/'local_runs/complete-service-checks-v66-20261016-a';PRIOR=R/'local_runs/lossless-control-v63-20261016-a';V64=R/'local_runs/modern-service-checks-v64-20261016-a';V65=R/'local_runs/disjoint-data-v65-20261016-a';OUT=Path('/tmp/second-v66-checks-terminal-20261016-a.tar.gz');REG='5727138fa7739700e5d14b10a015e33b42765da19dad80b6723a3bdf29e5ada3'
def info(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def cmd(*a):return subprocess.check_output(a,cwd=R,text=True,timeout=20)
def scheduler():
 q=cmd('squeue','-h','-j','15259','-o','%i|%T');assert not q.strip()
 a=cmd('sacct','-n','-P','-j','15259','--format=JobIDRaw,State,ExitCode,ElapsedRaw,TotalCPU,MaxRSS,Start,End')
 rows={f[0]:f for f in [s.split('|') for s in a.splitlines()]};assert all(rows[n][1:3]==['COMPLETED','0:0'] for n in ['15259','15259.batch']);return a
assert not OUT.exists();first=scheduler();assert cmd('git','rev-parse','HEAD').strip()=='f900999fcb200509dfad4fc081ce9c87fd172a16' and not cmd('git','status','--porcelain').strip()
raw=(D/'registration.json').read_bytes();assert info(raw)['sha256']==REG;p=json.loads(raw)
for n,h in p['historical_sources'].items():assert info((R/n).read_bytes())['sha256']==h
for group,root in [('new_sources',D),('v63_sources',PRIOR),('v64_sources',V64),('v65_sources',V65),('dependency_files',PRIOR/'deps')]:
 for n,e in p[group].items():assert info((root/n).read_bytes())==e
for n,e in p['prior_software_data_receipts'].items():assert info(Path(n).read_bytes())==e
paths=sorted(D.glob('*.json'))+sorted(D.glob('*.log'))+[D/n for n in p['new_sources']];files={}
for path in paths:
 assert path.is_file() and not any(q.is_symlink() for q in (path,*path.parents)) and path.stat().st_size<2**20
 n=str(path.relative_to(D));assert n not in files;files[n]=path.read_bytes()
assert len(files)==13 and sum(map(len,files.values()))<2**20
c=json.loads(files['completion.json']);assert c['status']=='complete' and c['registration_sha256']==REG and c['result']['tests']==44 and c['result']['skipped']==0
last=scheduler();assert first==last and all((D/n).read_bytes()==b for n,b in files.items())
files['collection-manifest.json']=canonical(dict(schema='v66-software-terminal-capture',captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),registration_sha256=REG,files={n:info(b) for n,b in files.items()},scheduler=last,historical_sources_verified=432,v63_sources_verified=7,v64_sources_verified=6,v65_sources_verified=5,dependency_files_verified=11,empirical_inputs_read=False))
with OUT.open('xb') as f:
 with tarfile.open(fileobj=f,mode='w|gz') as t:
  for n,b in sorted(files.items()):
   ti=tarfile.TarInfo(n);ti.size=len(b);ti.mode=0o600;t.addfile(ti,io.BytesIO(b))
print(json.dumps(dict(path=str(OUT),files=len(files),**info(OUT.read_bytes()))))
