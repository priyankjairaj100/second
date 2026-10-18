"""Read only: collect already terminal-audited scalar losses after the chain closes.

This is a supplementary reporting observer, not a registered experiment/launcher.
No model, token, checkpoint, or neural evaluator is read or executed.
"""
from pathlib import Path
import datetime, hashlib, io, json, subprocess, sys, tarfile
ROOT = Path('/nfs_home/users/poonam/second-20261010')
RUN = ROOT/'local_runs/untouched-quality-v71-20261018-a'
REG = '3ec767a20be59ed81330d68a067166bc14a369e967d9d3cbf274166baa32c56c'
MODELS = ('original','nearest','candidate_12','sequential_12','candidate_6','sequential_6')
def info(raw): return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
def command(*args): return subprocess.check_output(args, cwd=ROOT, text=True).strip()
def read(path):
    assert path.is_file() and not path.is_symlink() and path.stat().st_size < 8*2**20
    raw=path.read_bytes(); assert len(raw)<8*2**20; return raw

def main():
    assert command('git','rev-parse','HEAD')=='f900999fcb200509dfad4fc081ce9c87fd172a16'
    assert not command('git','status','--porcelain','--untracked-files=no')
    accounting=command('sacct','-n','-P','-j',','.join(str(j) for j in range(15405,15414)),
                       '--format=JobIDRaw,State,ExitCode')
    allocation=[line.split('|') for line in accounting.splitlines() if '.' not in line.split('|')[0]]
    assert len(allocation)==9 and {r[0] for r in allocation}=={str(j) for j in range(15405,15414)}
    assert all(r[1:] == ['COMPLETED','0:0'] for r in allocation), 'Await every original job; do not retry jobs'
    files={name:read(RUN/name) for name in ['program.json','terminal/outputs/completion.json','closure/receipt.json']}
    assert info(files['program.json'])['sha256']==REG
    terminal=json.loads(files['terminal/outputs/completion.json'])
    assert terminal['status']=='complete' and terminal['error'] is None and terminal['registration_sha256']==REG
    audit=terminal['result']['loss_audit']
    assert audit['status']=='verified' and audit['actual_loss_files_compared']==1920
    cpu=audit['actual_cpu_reference_audit']
    assert cpu['status']=='verified' and cpu['actual_loss_files_compared']==24
    for phase,count,pins in [('cpu_parity',4,cpu['artifacts']),('gpu_quality',320,audit['artifacts'])]:
        names=['completion.json']+[f'loss-{m}-{i:04d}.json' for m in MODELS for i in range(count)]
        if phase=='gpu_quality': names+=['paired-losses.json','statistics.json','parity.json']
        for name in names:
            relative=phase+'/outputs/losses/'+name
            raw=read(RUN/relative); assert info(raw)==pins[name], 'Actual bytes differ from terminal audit commitment'
            files[relative]=raw
    assert len(files)<2000 and sum(map(len,files.values()))<32*2**20
    collection=dict(schema='v71-terminal-scalar-loss-observation', captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        registration_sha256=REG, accounting=accounting, files={n:info(b) for n,b in files.items()},
        scalar_loss_files=1944, model_or_token_bodies_read=False, likelihood_reexecuted=False,
        scope='Post-exit reporting copy of previously audited scalar losses; requires separate final metadata/cost reconciliation.')
    files['collection.json']=json.dumps(collection,sort_keys=True,separators=(',',':')).encode()
    with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as archive:
        for name,raw in sorted(files.items()):
            member=tarfile.TarInfo(name);member.size=len(raw);member.mode=0o600
            archive.addfile(member,io.BytesIO(raw))
if __name__=='__main__': main()
