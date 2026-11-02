"""Offline, namespace-local extraction of hash-verified wheel dependencies."""
import json,zipfile,stat,sys
from pathlib import Path
from research_v124.worker import read,save,ident

def prepare(root,p,out):
 dest=root/'deps';dest.mkdir(exist_ok=False)
 for row in p['dependency_wheels']:
  path=root/row['path'];read({'path':str(path),'bytes':row['bytes'],'sha256':row['sha256']})
  with zipfile.ZipFile(path) as z:
   assert z.testzip() is None
   for item in z.infolist():
    name=Path(item.filename);assert not name.is_absolute() and '..' not in name.parts and '.data' not in name.parts and not stat.S_ISLNK(item.external_attr>>16)
    if item.is_dir():continue
    f=dest/name;f.parent.mkdir(parents=True,exist_ok=True)
    with f.open('xb') as stream:stream.write(z.read(item))
 manifest={str(f.relative_to(dest)):ident(f.read_bytes()) for f in sorted(dest.rglob('*')) if f.is_file()}
 save(out/'dependencies.json',manifest);verify(root)

def verify(root):
 dest=root/'deps';manifest=json.loads((root/'checks/dependencies.json').read_text())
 assert {str(f.relative_to(dest)) for f in dest.rglob('*') if f.is_file()}==set(manifest)
 for n,e in manifest.items():read({'path':str(dest/n),**e})
 sys.path.insert(0,str(dest))
 return manifest
