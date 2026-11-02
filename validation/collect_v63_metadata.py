"""Read-only terminal V63 metadata capture; never reads numerical binaries."""
import argparse,datetime,hashlib,io,json,signal,subprocess,tarfile
from pathlib import Path
ROOT=Path('/nfs_home/users/poonam/second-20261010')
RUN=ROOT/'local_runs/lossless-control-v63-20261016-a'
REG='479f7861b06933994916f1d3a22d94caed104dffdcc807c58a73dbacee5ce9d6'
JOBS={'checks':'15244','measure':'15245','audit':'15246'}
TERMINAL={'COMPLETED','FAILED','TIMEOUT','CANCELLED','OUT_OF_MEMORY','NODE_FAIL','PREEMPTED','DEADLINE','REVOKED','BOOT_FAIL','SPECIAL_EXIT'}
def require(v,m):
    if not v:raise ValueError(m)
def info(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def read(p):
    require(p.is_file() and not any(q.is_symlink() for q in (p,*p.parents)) and p.stat().st_size<=16*2**20,'Unsafe or oversized metadata')
    a=p.stat();b=p.read_bytes();c=p.stat();require((a.st_size,a.st_mtime_ns,a.st_ino)==(c.st_size,c.st_mtime_ns,c.st_ino),'Metadata changed');return b
def command(*a):return subprocess.check_output(a,cwd=ROOT,text=True,timeout=25)
def scheduler():
    ids=','.join(JOBS.values());queue=command('squeue','-h','-j',ids,'-o','%i|%T|%R');require(not queue.strip(),'Jobs are not quiescent')
    raw=command('sacct','-n','-P','-j',ids,'--format=JobIDRaw,JobName%64,State%40,ExitCode,ElapsedRaw,TotalCPU,MaxRSS,Start,End')
    rows={}
    for line in raw.splitlines():
        f=line.split('|')
        if f[0] in JOBS.values():
            require(f[0] not in rows and f[2].split()[0].rstrip('+') in TERMINAL,'Nonterminal/duplicate scheduler row');rows[f[0]]=f
    require(set(rows)==set(JOBS.values()),'Missing scheduler allocation');return dict(queue=queue,accounting=raw,successful=all(f[2:4]==['COMPLETED','0:0'] for f in rows.values()))
def collect(output):
    require(output.is_absolute() and ROOT not in output.parents and not output.exists() and not any(q.is_symlink() for q in (output,*output.parents)),'Fresh archive outside checkout required')
    before=scheduler();require(command('git','rev-parse','HEAD').strip()=='f900999fcb200509dfad4fc081ce9c87fd172a16' and not command('git','status','--porcelain').strip(),'Frozen checkout changed')
    raw=read(RUN/'registration.json');require(info(raw)['sha256']==REG,'Registration changed');p=json.loads(raw)
    files={str(q.relative_to(RUN)):read(q) for q in sorted(RUN.glob('*.json'))+sorted(RUN.glob('*.log'))}
    for n,e in p['new_sources'].items():files[n]=read(RUN/n);require(info(files[n])==e,'Source changed')
    for n,h in p['frozen_sources'].items():require(info(read(ROOT/n))['sha256']==h,'Frozen source changed')
    require(len(files)<=64 and sum(map(len,files.values()))<32*2**20,'Capture bound')
    omitted=dict(p['inputs']);measurement=json.loads(files.get('measure.json',b'{}'))
    if measurement.get('result'):
        for r in measurement['result']['endpoints']:omitted[str(RUN/('endpoint-'+str(r['index'])+'.bin'))]=r['artifact']
    for n,e in omitted.items():
        q=Path(n);require(q.is_file() and not q.is_symlink() and q.stat().st_size==e['bytes'],'Declared input/output extent changed')
    after=scheduler();require(before==after,'Accounting changed during capture')
    require(all(read(RUN/n)==b for n,b in files.items()),'Captured files changed')
    manifest=dict(schema='v63-terminal-metadata-capture',captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),registration_sha256=REG,jobs=JOBS,files={n:info(b) for n,b in files.items()},scheduler=after,omitted_inputs_outputs=omitted,numerical_binary_contents_read=False,frozen_sources_verified=432)
    files['collection-manifest.json']=canonical(manifest)
    with output.open('xb') as f:
        with tarfile.open(fileobj=f,mode='w|gz') as t:
            for n,b in sorted(files.items()):
                ti=tarfile.TarInfo(n);ti.size=len(b);ti.mode=0o600;t.addfile(ti,io.BytesIO(b))
    print(json.dumps(dict(path=str(output),files=len(files),**info(output.read_bytes()),scheduler_success=before['successful'])))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args()
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Capture cap')));signal.alarm(120);collect(a.output)
