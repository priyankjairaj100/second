"""Bounded read-only V68 terminal metadata; never copies raw corpus or tokens."""
from pathlib import Path
import datetime,hashlib,io,json,subprocess,sys,tarfile
ROOT=Path('/nfs_home/users/poonam/second-20261010')
RUN=ROOT/'local_runs/quality-data-v68-20261016-a'
REG='ddcf2b686ff0ed4c4401a4defa361bcd956a32d3697dbe1b71485744c513b3cb'
def info(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p,limit=16*2**20):
    assert p.is_file() and not any(x.is_symlink() for x in (p,*p.parents))
    a=p.stat();assert a.st_size<=limit;b=p.read_bytes();c=p.stat()
    assert (a.st_ino,a.st_size,a.st_mtime_ns)==(c.st_ino,c.st_size,c.st_mtime_ns)
    return b
def command(*a):return subprocess.check_output(a,cwd=ROOT,text=True,timeout=30).strip()
p=json.loads(read(RUN/'registration.json'));assert info(read(RUN/'registration.json'))['sha256']==REG
for group in ['frozen_sources','new_sources','administrative_sources','historical_ledgers','tokenizer_runtime_files','prior_dependency_files','host_runtime_files']:
    for path,e in p[group].items():assert info(read(Path(path),128*2**20))==e,path
for name,e in p['history'].items():assert info(read(ROOT/name,2*2**20))==e,name
for e in p['inputs'].values():assert info(read(Path(e['path'])))=={k:e[k] for k in ['bytes','sha256']}
paths=[x for x in RUN.iterdir() if x.is_file() and x.suffix in ['.json','.log','.py']]
paths.extend((RUN/'research_v68').glob('*'))
paths.extend(RUN/'outputs'/n for n in ['selection.json','acquisition.json'] if (RUN/'outputs'/n).is_file())
files={str(x.relative_to(RUN)):read(x) for x in sorted(paths) if x.is_file()}
assert len(files)<100 and sum(map(len,files.values()))<8*2**20
artifacts={}
for x in sorted((RUN/'outputs').iterdir()):
    if x.is_file():artifacts[x.name]=info(read(x))
jobs=json.loads(files['jobs.json']);assert jobs==dict(checks='15390',data='15391',audit='15392')
s=dict(schema='v68-terminal-metadata-snapshot',captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
       registration_sha256=REG,files={n:info(b) for n,b in files.items()},output_commitments=artifacts,
       accounting=command('sacct','-n','-P','-j',','.join(jobs.values()),'--format=JobIDRaw,JobName,State,ExitCode,Elapsed,TotalCPU,MaxRSS,NodeList,Start,End'),
       queue=command('squeue','-h','-u','poonam','-o','%i|%j|%T|%M|%R'),
       frozen_sources_verified=469,v68_sources_verified=9,administrative_sources_verified=1,
       historical_ledgers_verified=len(p['historical_ledgers']),historical_metadata_verified=len(p['history']),
       raw_corpus_or_tokens_copied=False,retokenization_repeated_by_collector=False)
files['collection.json']=json.dumps(s,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as t:
    for n,b in sorted(files.items()):
        m=tarfile.TarInfo(n);m.size=len(b);m.mode=0o600;t.addfile(m,io.BytesIO(b))
