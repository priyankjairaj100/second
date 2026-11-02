from pathlib import Path
import io,json,hashlib,tarfile,sys,datetime
root=Path('/nfs_home/users/poonam/second-20261010')
site=root/'.venv-container/lib/python3.12/site-packages'
bases={name:site/(name+'-'+version+'.dist-info') for name,version in [('numpy','2.3.5'),('gmpy2','2.3.2'),('tokenizers','0.23.2')]}
bases['zstandard']=root/'local_runs/lossless-control-v63-20261016-a/deps/zstandard-0.25.0.dist-info'
files={};inventory={};total=0
for package,base in bases.items():
 assert base.is_dir() and not base.is_symlink(),str(base)
 selected=[]
 for p in sorted(base.rglob('*')):
  if p.is_file() and (any(x.lower() in ('licenses','license') for x in p.relative_to(base).parts[:-1]) or p.name.lower().startswith(('license','copying','notice','authors'))):selected.append(p)
 assert len(selected)<=50
 inventory[package]={'files':{},'notice_files_found':len(selected)}
 for p in selected:
  assert not any(q.is_symlink() for q in (p,*p.parents))
  before=p.stat();assert before.st_size<=2**20
  raw=p.read_bytes();after=p.stat();raw.decode('utf-8')
  assert (before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino)
  total+=len(raw);assert total<=4*2**20
  name=package+'/'+str(p.relative_to(base));files[name]=raw
  inventory[package]['files'][name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
assert files
files['inventory.json']=(json.dumps({'schema':'installed-dependency-notices-v69','captured_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'CPU installed distribution license trees only; no package binaries or model/data','packages':inventory,'all_transitive_notices_complete':False,'gpu_environment_inspected':False,'project_license_assigned':False,'total_notice_bytes':total},sort_keys=True,indent=2)+'\n').encode()
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as t:
 for name,raw in sorted(files.items()):
  entry=tarfile.TarInfo(name);entry.mode=0o644;entry.size=len(raw);t.addfile(entry,io.BytesIO(raw))
