"""Exclusive writes and bounded, stable reads for actual experiment artifacts."""
import hashlib,os
from pathlib import Path
from src.run_store import canonical_json,strict_json

def require(x,m):
    if not x:raise ValueError(m)

def regular(path):
    p=Path(path).absolute()
    require(not any(q.is_symlink() for q in (p,*p.parents)) and p.is_file(),'Regular nonsymbolic input required')
    return p

def info(blob):return dict(bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest())

def read(path,expected=None,maximum=2**30,retain=True):
    p=regular(path);a=p.stat();require(a.st_size<=maximum,'Input extent exceeds bound')
    h=hashlib.sha256();count=0;chunks=[]
    with p.open('rb') as stream:
        while chunk:=stream.read(2**20):
            count+=len(chunk);require(count<=maximum,'Growing input exceeds bound');h.update(chunk)
            if retain:chunks.append(chunk)
    b=p.stat();require((a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)==(b.st_dev,b.st_ino,b.st_size,b.st_mtime_ns,b.st_ctime_ns),'Input changed during read')
    observed=dict(bytes=count,sha256=h.hexdigest())
    require(expected is None or observed==expected,'Input commitment differs')
    return b''.join(chunks) if retain else observed

def json_read(path,expected=None):
    raw=read(path,expected,64*2**20);x=strict_json(raw)
    require(type(x) is dict and canonical_json(x)==raw,'Canonical JSON object required')
    return x

def write(path,value,raw=False,maximum=2**30):
    p=Path(path).absolute();blob=value if raw else canonical_json(value)
    require(type(blob) is bytes and len(blob)<=maximum and not any(q.is_symlink() for q in (p,*p.parents)),'Unsafe output')
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(blob);f.flush();os.fsync(f.fileno())
    return dict(file=p.name,**info(blob))
