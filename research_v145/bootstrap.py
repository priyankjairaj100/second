from pathlib import Path,PurePosixPath
import json,zipfile,hashlib,sys

def ident(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def install(root,program,fresh):
 deps=root/'deps';manifest=root/'environment.json'
 if fresh:
  deps.mkdir(exist_ok=False);files={}
  for e in program['wheels']:
   wheel=root/'wheels'/e['file'];assert ident(wheel.read_bytes())=={k:e[k] for k in ('bytes','sha256')}
   with zipfile.ZipFile(wheel) as z:
    for name in z.namelist():
     q=PurePosixPath(name);assert not q.is_absolute() and '..' not in q.parts
     if name.endswith('/'):continue
     f=deps/name;f.parent.mkdir(parents=True,exist_ok=True)
     data=z.read(name)
     if f.exists():assert f.read_bytes()==data
     else:f.write_bytes(data)
     files[name]=ident(data)
  with manifest.open('x') as f:json.dump(dict(schema='pinned-wheel-payload-install-v145',files=files,wheels=program['wheels'],uses_existing_site_packages=False),f,indent=2)
 obj=json.loads(manifest.read_bytes());assert obj['wheels']==program['wheels'] and not obj['uses_existing_site_packages']
 for name,e in obj['files'].items():assert ident((deps/name).read_bytes())==e,name
 sys.path.insert(0,str(deps))
 return ident(manifest.read_bytes())
