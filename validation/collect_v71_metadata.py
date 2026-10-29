"""Bounded read-only V71 observation; no job submission or empirical execution."""
from pathlib import Path
import datetime, hashlib, io, json, re, subprocess, sys, tarfile

ROOT=Path('/nfs_home/users/poonam/second-20261010')
RUN=ROOT/'local_runs/untouched-quality-v71-20261018-a'
REG='3ec767a20be59ed81330d68a067166bc14a369e967d9d3cbf274166baa32c56c'
PHASES=['cpu_checks','cuda_checks','parameters','sequential_12','sequential_6',
        'cpu_parity','gpu_quality','terminal','closure']
JOBS={phase:str(15405+i) for i,phase in enumerate(PHASES)}
def info(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def command(*a):return subprocess.check_output(a,cwd=ROOT,text=True).strip()
assert command('git','rev-parse','HEAD')=='f900999fcb200509dfad4fc081ce9c87fd172a16'
assert not command('git','status','--porcelain','--untracked-files=no')
p=json.loads((RUN/'program.json').read_bytes());assert info((RUN/'program.json').read_bytes())['sha256']==REG
p70=json.loads((ROOT/'local_runs/quality-frame-audit-v70-20261018-a/program.json').read_bytes())
sources={}
for group in [p70['frozen_sources'],p70['new_sources'],p['new_sources']]:
    for name,e in group.items():
        assert name not in sources or sources[name]==e
        sources[name]=e
assert len(sources)==576 # 575 numerical/protocol files and the separate V70 admin launcher.
for name,e in sources.items():assert info(Path(name).read_bytes())==e
files={}
def capture(relative):
    path=RUN/relative
    if not path.exists():return
    assert path.is_file() and not path.is_symlink() and path.stat().st_size<4*2**20
    b=path.read_bytes();assert len(b)<4*2**20;files[relative]=b
for name in ['program.json','registration.json','frame-scheduler.txt','launch-intent.json',
             'launch-completion.json','chain-ready.json','budget/ledger.json']:
    capture(name)
for phase,job in JOBS.items():
    for name in ['job-binding.json','held-verification.json','submission-intent.json',
                 'submission-response.json','release-intent.json','release-response.json',
                 'entry-start.json','entry.json','worker/identity.json','worker/result.json',
                 'outputs/completion.json','outputs/checks.json','outputs/gpu.json',
                 'start.json','receipt.json','scheduler.txt',f'slurm-{job}.log']:
        capture(phase+'/'+name)
    result=files.get(phase+'/worker/result.json')
    if result is not None:
        worker=json.loads(result)
        if worker.get('status')=='complete':
            attempt=worker['attempt'];assert re.fullmatch(r'attempt-[0-9]{4,}',attempt)
            assert set(worker['artifacts'])=={'request.json','budget-reservation.json',
                'stdout-summary.json','stderr-summary.json','pre-settlement-observation.json','limits-applied.json'}
            for name,e in worker['artifacts'].items():
                rel=phase+'/worker/'+attempt+'/'+name;capture(rel);assert info(files[rel])==e
            capture(phase+'/worker/'+attempt+'/status.json')
    if phase.startswith('sequential_'):
        progress=sorted((RUN/phase/'outputs/construction').glob('progress-*.json'))
        assert len(progress)<=24
        for path in progress:capture(str(path.relative_to(RUN)))
for name in p['new_sources']:capture(str(Path(name).relative_to(RUN)))
assert len(files)<350 and sum(map(len,files.values()))<32*2**20
collection=dict(schema='v71-bounded-metadata-observation',captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    registration_sha256=REG,jobs=JOBS,frozen_numerical_sources_verified=575,auxiliary_sources_verified=1,
    numerical_checkout='f900999fcb200509dfad4fc081ce9c87fd172a16',
    files={n:info(b) for n,b in files.items()},
    queue=command('squeue','-h','-u','poonam','-o','%i|%j|%T|%M|%R'),
    accounting=command('sacct','-n','-P','-j',','.join(JOBS.values()),'--format=JobIDRaw,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS'),
    model_or_corpus_bytes_collected=False,completed_worker_seal_artifacts_included=True,atomic_cross_file_snapshot=False,
    scope='Observed metadata only; verify terminal seals and actual artifact audits before scientific conclusions.')
files['collection.json']=json.dumps(collection,sort_keys=True,separators=(',',':')).encode()
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as t:
    for name,b in sorted(files.items()):
        item=tarfile.TarInfo(name);item.size=len(b);item.mode=0o600;t.addfile(item,io.BytesIO(b))
