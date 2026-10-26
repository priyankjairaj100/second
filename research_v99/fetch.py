"""Single-attempt bounded public fetch; immutable files, no credential storage.

The URL is an immutable public model revision. Redirect URLs are validated but
never logged. No HTTP credentials or retry loops are supplied.
"""
import hashlib,json,os,time,urllib.request
from research_v90.records import Records, SMALL_BYTES
from research_v80.io import json_read, read, require
from pathlib import Path
from urllib.parse import urlsplit
REVISION='607a30d783dfa663caf39e06633721c8d4cfcd7e'
BASE='https://huggingface.co/openai-community/gpt2/resolve/'+REVISION+'/'
EXPECTED={
 'config.json':dict(bytes=665,sha256='0daed7749b4f02b8f76240d5444551d7b08712dab4d0adb8239c56ba823bb7b4'),
 'model.safetensors':dict(bytes=548105171,sha256='248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707')}

def valid_url(url):
    u=urlsplit(url);h=u.hostname or ''
    return u.scheme=='https' and not u.username and not u.password and u.port in (None,443) and (h=='huggingface.co' or h.endswith('.huggingface.co') or h.endswith('.hf.co'))

class PublicRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if not valid_url(newurl):raise ValueError('Public artifact redirect host refused')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def receive(response,destination,expected,*,deadline,clock=time.monotonic):
    """Exclusive streaming write; any failed partial file remains consumed."""
    path=Path(destination).absolute()
    if any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('Unsafe destination')
    if expected['bytes']<=0 or len(expected['sha256'])!=64:raise ValueError('Bad input commitment')
    h=hashlib.sha256();count=0
    with path.open('xb') as f:
        while True:
            if clock()>deadline:raise TimeoutError('Bounded fetch deadline exceeded')
            chunk=response.read(min(2**20,expected['bytes']-count+1))
            if clock()>deadline:raise TimeoutError('Bounded fetch deadline exceeded')
            if not chunk:break
            count+=len(chunk)
            if count>expected['bytes']:raise ValueError('Public artifact exceeds exact extent')
            f.write(chunk);h.update(chunk)
        f.flush();os.fsync(f.fileno())
    actual=dict(bytes=count,sha256=h.hexdigest())
    if actual!=expected:raise ValueError('Actual public checkpoint commitment differs')
    return actual

def fetch_checkpoint(directory):
    directory=Path(directory).absolute()
    if any(p.is_symlink() for p in (directory,*directory.parents)):raise ValueError('Unsafe fetch directory')
    directory.mkdir(parents=True,exist_ok=False)
    # No proxy credentials are taken from environment variables.
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),PublicRedirect())
    start=time.monotonic();receipt=dict(schema='public-checkpoint-fetch-v99',revision=REVISION,status='running',files={},automatic_retry=False)
    records=Records(directory, {'fetch-intent.json':SMALL_BYTES, 'fetch-receipt.json':SMALL_BYTES})
    records.write('fetch-intent.json',receipt)
    try:
        for name,expected in EXPECTED.items():
            url=BASE+name
            with opener.open(urllib.request.Request(url,headers={'User-Agent':'Second-reproducible-public-model-fetch'}),timeout=30) as response:
                if not valid_url(response.url):raise ValueError('Public response identity refused')
                receipt['files'][name]=receive(response,directory/name,expected,deadline=start+420)
        receipt['status']='complete'
    except BaseException as exc:
        # Do not serialize response objects, signed redirect URLs or raw headers.
        receipt.update(status='failed',error_type=type(exc).__name__)
        raise
    finally:
        receipt['elapsed_seconds']=time.monotonic()-start
        records.write('fetch-receipt.json',receipt)
    return receipt


def verify_fetch(directory):
    directory=Path(directory)
    r=json_read(directory/'fetch-receipt.json'); intent=json_read(directory/'fetch-intent.json')
    require(intent==dict(schema='public-checkpoint-fetch-v99',revision=REVISION,status='running',files={},automatic_retry=False), 'Original exact fetch intent required')
    require(r['schema']=='public-checkpoint-fetch-v99' and r['revision']==REVISION and r['status']=='complete'
        and r['automatic_retry'] is False and r['files']==EXPECTED and 0<=r['elapsed_seconds']<=420,
        'Complete exact public fetch required')
    require({p.name for p in directory.iterdir()}==set(EXPECTED)|{'fetch-intent.json','fetch-receipt.json'},'Exact fetch file census required')
    for name,entry in EXPECTED.items():read(directory/name,entry,retain=False)
    return r
