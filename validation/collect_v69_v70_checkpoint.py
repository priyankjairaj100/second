"""Read-only bounded metadata capture of the failed gate or its separate frame audit."""
from pathlib import Path
import tarfile,io,hashlib,json,subprocess,sys,datetime
ROOT=Path('/nfs_home/users/poonam/second-20261010');which=sys.argv[1]
assert which in ['v69','v70']
run=ROOT/'local_runs'/('untouched-quality-v69-20261016-a' if which=='v69' else 'quality-frame-audit-v70-20261018-a')
ids=list(map(str,range(15395,15404))) if which=='v69' else [json.loads((run/'submission-response.json').read_bytes())['stdout'].strip()]
files={}
for p in sorted(run.rglob('*')):
 if p.is_file():
  assert not p.is_symlink() and p.suffix in ['.json','.py','.txt','.sbatch','.log'] and p.stat().st_size<4*2**20
  assert 'worker' not in p.relative_to(run).parts,'Unexpected started numerical worker'
  files[str(p.relative_to(run))]=p.read_bytes()
assert len(files)<180 and sum(map(len,files.values()))<12*2**20
p70=json.loads((ROOT/'local_runs/quality-frame-audit-v70-20261018-a/program.json').read_bytes())
for n,e in p70['frozen_sources'].items():
 b=Path(n).read_bytes();assert dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())==e
c=dict(schema='quality-admission-checkpoint-metadata',phase=which,captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),jobs=ids,files={n:dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest()) for n,b in files.items()},frozen_sources_verified=532,no_numerical_worker_or_loss_output=True,accounting=subprocess.check_output(['sacct','-n','-P','-j',','.join(ids),'--format=JobIDRaw,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS'],text=True).strip(),queue=subprocess.check_output(['squeue','-h','-u','poonam','-o','%i|%j|%T|%R'],text=True).strip())
files['collection.json']=json.dumps(c,sort_keys=True,separators=(',',':')).encode()
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as t:
 for n,b in files.items():m=tarfile.TarInfo(n);m.size=len(b);m.mode=0o600;t.addfile(m,io.BytesIO(b))
