"""Read-only bounded capture of separate accounting recovery and its final Slurm row."""
from pathlib import Path
import json,hashlib,datetime,subprocess,tarfile,io,sys
ROOT=Path('/nfs_home/users/poonam/second-20261010');RUN=ROOT/'local_runs/quality-cost-recovery-v72-20261018-a'
def info(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
files={}
for p in sorted(RUN.rglob('*')):
    if p.is_dir():continue
    assert p.is_file() and not p.is_symlink() and p.stat().st_size<8*2**20
    assert '__pycache__' not in p.parts
    files[str(p.relative_to(RUN))]=p.read_bytes()
assert len(files)<60 and sum(map(len,files.values()))<16*2**20
job=json.loads(files['job-binding.json'])['job_id'];assert job=='15421'
command=['sacct','-n','-P','-j',job,'--format=JobIDRaw,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS']
c=dict(schema='v72-bounded-accounting-recovery-observation',captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
       job_id=job,accounting=subprocess.check_output(command,text=True).strip(),files={n:info(b) for n,b in files.items()})
files['collection.json']=json.dumps(c,sort_keys=True,separators=(',',':')).encode()
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as t:
    for n,b in sorted(files.items()):
        m=tarfile.TarInfo(n);m.size=len(b);m.mode=0o600;t.addfile(m,io.BytesIO(b))
