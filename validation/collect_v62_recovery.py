"""Collect a quiescent V62 audit recovery, preserving V61's original failure.
Reads bounded metadata; numerical inputs are only statted. Never launches jobs.
"""
import argparse
import datetime
import hashlib
import io
import json
from pathlib import Path
import signal
import subprocess
import tarfile
import time

ROOT=Path('/nfs_home/users/poonam/second-20261010')
RUN=ROOT/'local_runs/audit-recovery-v62-20261015-a'
CAMPAIGN=ROOT/'local_runs/full-precision-service-v61-20261014-a'
REGISTRATION_SHA='531d530feb42feca040dab0f5f288136152f80463611a391d8404dfd82b8192b'
JOBS={'15150','15151'}
TERMINAL={'COMPLETED','FAILED','TIMEOUT','CANCELLED','OUT_OF_MEMORY','NODE_FAIL','PREEMPTED','DEADLINE','REVOKED','BOOT_FAIL','SPECIAL_EXIT'}


def require(v,m):
    if not v:raise ValueError(m)


def info(raw):return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def read(path):
    path=Path(path);require(path.is_file() and not any(p.is_symlink() for p in (path,*path.parents)),'Unsafe input')
    a=path.stat();require(a.st_size<=64*2**20,'Metadata exceeds bound')
    data=path.read_bytes();b=path.stat()
    require((a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)==(b.st_dev,b.st_ino,b.st_size,b.st_mtime_ns,b.st_ctime_ns),'Changed input')
    return data


def command(*args):
    r=subprocess.run(args,cwd=ROOT,text=True,capture_output=True,timeout=25,check=True)
    require(len(r.stdout)<2**20,'Command output exceeds bound');return r.stdout


def scheduler():
    ids=','.join(sorted(JOBS));queue=command('squeue','-h','-j',ids,'-o','%i|%T|%R')
    require(not queue.strip(),'Recovery still queued/running')
    raw=command('sacct','-X','-n','-P','-j',ids,'--format=JobIDRaw,JobName%64,State%40,ExitCode,ElapsedRaw,TotalCPU,Start,End')
    rows={}
    for line in raw.splitlines():
        if not line.strip():continue
        f=line.split('|');f=f[:-1] if f[-1]=='' else f
        require(len(f)==8 and f[0] in JOBS and f[0] not in rows,'Scheduler census')
        require(f[2].split()[0].rstrip('+') in TERMINAL,'Nonterminal recovery state')
        rows[f[0]]=f
    require(set(rows)==JOBS,'Both recovery scheduler rows required')
    steps=command('sacct','-n','-P','-j',ids,'--format=JobIDRaw,JobName%64,State%40,ExitCode,ElapsedRaw,TotalCPU,MaxRSS,Start,End')
    return dict(scheduler=raw,scheduler_steps=steps,scheduler_queue=queue,successful=all(v[2:4]==['COMPLETED','0:0'] for v in rows.values()))


def old_bindings(p):
    for n,e in p['metadata_inputs'].items():require(info(read(n))==e,'Original metadata changed: '+n)
    for n in ('artifact-audit.json','postrun-audit.json'):
        q=CAMPAIGN/n;require(not q.exists() and not q.is_symlink(),'Original failed audit path was filled')
    for n,e in p['binary_inputs'].items():
        q=Path(n);require(q.is_file() and not any(f.is_symlink() for f in (q,*q.parents)) and q.stat().st_size==e['bytes'],'Declared binary missing/size changed')


def collect(output):
    start=time.monotonic();output=Path(output)
    require(output.is_absolute() and output.name.endswith('.tar.gz') and ROOT not in output.parents
        and not output.exists() and not output.is_symlink(),'Fresh archive outside checkout required')
    require(not any(p.is_symlink() for p in output.parents),'Unsafe archive parent')
    before=scheduler()
    require(command('git','rev-parse','HEAD').strip()=='f900999fcb200509dfad4fc081ce9c87fd172a16' and not command('git','status','--porcelain').strip(),'Frozen numerical checkout changed')
    raw=read(RUN/'registration.json');require(info(raw)['sha256']==REGISTRATION_SHA,'Recovery registration changed')
    p=json.loads(raw);old_bindings(p)
    paths=sorted(RUN.rglob('*'));require(len(paths)<=128 and all(f.is_file() and not f.is_symlink() for f in paths),'Unexpected recovery directory entry')
    data={f.name:read(f) for f in paths};require(len(data)==len(paths) and sum(map(len,data.values()))<=64*2**20,'Recovery inventory bound')
    for n,e in p['wrapper_sources'].items():require(info(data[n])==e,'Recovery source changed')
    require(info(data['failure-manifest.json'])==p['failure_manifest'],'Failure manifest changed')
    a=json.loads(data.get('primary.json',b'{}'));b=json.loads(data.get('postrun.json',b'{}'))
    verified=before['successful'] and a.get('status')==b.get('status')=='verified'
    inventories={}
    for label,value in (('primary',a),('postrun',b)):
        if value.get('inputs'):inventories[label]=dict(audit_file=label+'.json',inputs=value['inputs'])
    if verified:
        for remote,entry in b['inputs'].items():
            q=Path(remote)
            require(ROOT in q.parents,'Foreign audit input')
            if remote in p['binary_inputs']:require(entry==p['binary_inputs'][remote],'Binary commitment changed')
            else:require(info(read(q))==entry,'Actual audit metadata changed')
    old_bindings(p)
    require(sorted(RUN.rglob('*'))==paths and all(read(RUN/n)==blob for n,blob in data.items()),'Recovery files changed during collection')
    after=scheduler();require(before==after,'Recovery accounting changed during capture')
    manifest=dict(schema='second-audit-recovery-capture-v62',captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        registered_program_sha256=REGISTRATION_SHA,old_failure_manifest_sha256=p['failure_manifest']['sha256'],
        terminal_success=verified,old_campaign_unmodified=True,binary_contents_read=False,
        files={n:info(blob) for n,blob in data.items()},audit_input_inventories=inventories,
        expected_input_commitments=b.get('inputs',{}),binary_inputs_not_revalidated=p['binary_inputs'],
        capture_elapsed_seconds=time.monotonic()-start,**after)
    data['collection-manifest.json']=canonical(manifest)
    with output.open('xb') as f:
        with tarfile.open(fileobj=f,mode='w|gz') as t:
            for n,blob in sorted(data.items()):
                member=tarfile.TarInfo(n);member.size=len(blob);member.mode=0o600;t.addfile(member,io.BytesIO(blob))
    print(json.dumps(dict(path=str(output),**info(output.read_bytes()),files=len(data),terminal_success=verified)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('archive');a=p.parse_args()
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Capture wall cap')));signal.alarm(180)
    collect(a.archive)
