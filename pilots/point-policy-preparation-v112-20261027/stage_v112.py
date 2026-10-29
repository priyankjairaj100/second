"""One exclusive source-only staging attempt after fresh read-only admission."""
import datetime
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

BASE = Path(__file__).resolve().parent
PACKAGE = BASE / 'v112-prepared'
preparation = json.loads((PACKAGE / 'preparation.json').read_bytes())
archive = PACKAGE / 'matched-complete-recovery-v112-source-only.tar'
blob = archive.read_bytes()
assert len(blob) == preparation['archive']['bytes']
assert hashlib.sha256(blob).hexdigest() == preparation['archive']['sha256']
source = r'''
import datetime,hashlib,io,json,pathlib,subprocess,sys,tarfile
meta=json.loads(METADATA)
root=pathlib.Path('/nfs_home/users/poonam/second-20261010')
old=root/'local_runs/four-cell-recovery-v89-20261023-a'
run=root/'local_runs/matched-complete-recovery-v112-20261026-a'
archive=root/'local_runs/matched-complete-recovery-v112-source-only.tar'
assert not run.exists() and not archive.exists(), 'Existing staging is consumed; inspect instead'
assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()=='f900999fcb200509dfad4fc081ce9c87fd172a16'
assert not subprocess.check_output(['git','-C',str(root),'status','--short'],text=True).strip()
queue=subprocess.check_output(['squeue','-u','poonam','-h','-o','%i|%j|%T'],text=True,timeout=20)
assert not queue.strip(), 'Inspect active jobs before staging'
invraw=(old/'source-inventory.json').read_bytes()
assert hashlib.sha256(invraw).hexdigest()=='9c2df88733a29bedf0591e35157c50af8aabe453f6999e05ec3fc8adb2b484d4'
inventory=json.loads(invraw);assert len(inventory)==934
for name,e in inventory.items():
 b=(old/name).read_bytes();assert len(b)==e['bytes'] and hashlib.sha256(b).hexdigest()==e['sha256']
sys.path.insert(0,str(old))
from research_v88.storage import inspect
from research_v86.admission import EXPECTED,terminal_disposition
old_raw=subprocess.check_output(['sacct','-nP','-j',','.join(EXPECTED),'--format=JobIDRaw,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS,ReqMem,NodeList'],text=True,timeout=20)
old_disposition=terminal_disposition(old_raw)
new_raw=subprocess.check_output(['sacct','-nP','-j',','.join(str(i) for i in range(16004,16017)),'--format=JobIDRaw,State,ExitCode'],text=True,timeout=20)
rows={r.split('|')[0]:r.split('|')[1:3] for r in new_raw.splitlines() if '.' not in r.split('|')[0]}
assert set(rows)==set(str(i) for i in range(16004,16017)) and all(r==['COMPLETED','0:0'] for r in rows.values())
admitted_raw=subprocess.check_output(['sacct','-nP','-j','16302,16303,16304,16305,16306','--format=JobIDRaw,State,ExitCode'],text=True,timeout=20)
admitted_rows={r.split('|')[0]:r.split('|')[1:3] for r in admitted_raw.splitlines() if '.' not in r.split('|')[0]}
assert set(admitted_rows)=={'16302','16303','16304','16305','16306'} and all(r==['COMPLETED','0:0'] for r in admitted_rows.values())
storage=inspect(meta['before_upload_requests'])
payload=sys.stdin.buffer.read(64*2**20+1)
assert len(payload)==meta['archive']['bytes'] and hashlib.sha256(payload).hexdigest()==meta['archive']['sha256']
with tarfile.open(fileobj=io.BytesIO(payload),mode='r:') as tar:
 members=tar.getmembers();assert len(members)==meta['source_count']+1 and all(m.isfile() for m in members)
 assert len({m.name for m in members})==len(members)
 inv=tar.extractfile('inventory.json').read()
 assert len(inv)==meta['inventory']['bytes'] and hashlib.sha256(inv).hexdigest()==meta['inventory']['sha256']
 entries=json.loads(inv);assert len(entries)==meta['source_count'] and set(entries)|{'inventory.json'}=={m.name for m in members}
 assert sum(m.size for m in members)<=64*2**20
 for m in members:
  p=pathlib.PurePosixPath(m.name)
  assert not p.is_absolute() and '..' not in p.parts and str(p)==m.name
  b=tar.extractfile(m).read();e=meta['inventory'] if m.name=='inventory.json' else entries[m.name]
  assert len(b)==e['bytes'] and hashlib.sha256(b).hexdigest()==e['sha256']
 carry=json.loads(tar.extractfile('gates/v99-failed-software-carry.json').read())
 failed=pathlib.Path(carry['directory'])
 assert failed==root/'local_runs/matched-transfer-admission-v99-20261026-a'
 for name,e in carry['files'].items():
  b=(failed/name).read_bytes();assert len(b)==e['bytes'] and hashlib.sha256(b).hexdigest()==e['sha256']
 assert {str(p.relative_to(failed)) for p in failed.rglob('*') if p.is_file()}==set(carry['files'])
 failed_raw=subprocess.check_output(['sacct','-nP','-j','16301','--format=JobIDRaw,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS,ReqMem,NodeList'],text=True,timeout=20)
 assert failed_raw==carry['scheduler_raw']
 assert not any((failed/n).exists() for n in ('checkpoint','budget','chain-chain-intent.json','distilgpt2','gpt2'))
 carry_complete=json.loads(tar.extractfile('gates/v100-failed-software-carry.json').read())
 failed_complete=pathlib.Path(carry_complete['directory'])
 assert failed_complete==root/'local_runs/matched-complete-recovery-v100-20261026-a'
 for n,e in carry_complete['files'].items():
  b=(failed_complete/n).read_bytes();assert len(b)==e['bytes'] and hashlib.sha256(b).hexdigest()==e['sha256']
 assert {str(p.relative_to(failed_complete)) for p in failed_complete.rglob('*') if p.is_file()}==set(carry_complete['files'])
 full_failed_raw=subprocess.check_output(['sacct','-nP','-j','16307','--format=JobIDRaw,JobName%60,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS,ReqMem,NodeList'],text=True,timeout=20)
 assert full_failed_raw==carry_complete['scheduler_raw']
 carry_dispatch=json.loads(tar.extractfile('gates/v103-dispatch-failure-carry.json').read())
 failed_dispatch=pathlib.Path(carry_dispatch['directory'])
 assert failed_dispatch==root/'local_runs/matched-complete-recovery-v103-20261026-a'
 for n,e in carry_dispatch['files'].items():
  b=(failed_dispatch/n).read_bytes();assert len(b)==e['bytes'] and hashlib.sha256(b).hexdigest()==e['sha256']
 assert {str(p.relative_to(failed_dispatch)) for p in failed_dispatch.rglob('*') if p.is_file()}==set(carry_dispatch['files'])
 dispatch_raw=subprocess.check_output(['sacct','-nP','-j',','.join(str(i) for i in range(16309,16332)),'--format=JobIDRaw,JobName%60,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS,ReqMem,NodeList'],text=True,timeout=20)
 assert dispatch_raw==carry_dispatch['scheduler_raw']
 gate=json.loads(tar.extractfile('gates/v104-failed-screen-v110.json').read())
 parent=root/'local_runs/matched-complete-recovery-v104-20261026-a'
 assert hashlib.sha256((parent/'program.json').read_bytes()).hexdigest()==gate['parent_program_sha256']
 parent_raw=subprocess.check_output(['sacct','-nP','-j',','.join(str(i) for i in range(16336,16359)),'--format=JobIDRaw,JobName%60,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS,ReqMem,NodeList'],text=True,timeout=20)
 assert parent_raw==gate['scheduler_raw']
 for n,e in gate['inputs'].items():
  q=pathlib.Path(n);assert q.is_relative_to(parent) and q.is_file() and not q.is_symlink()
  h=hashlib.sha256();count=0
  with q.open('rb') as f:
   while b:=f.read(2**20):h.update(b);count+=len(b)
  assert count==e['bytes'] and h.hexdigest()==e['sha256']
 diagnostic=root/'local_runs/token-stage-diagnostic-v110-20261026-a'
 diagnostic_gate=json.loads(tar.extractfile('gates/v110-selected-stage-closure.json').read())
 assert hashlib.sha256((diagnostic/'program.json').read_bytes()).hexdigest()==diagnostic_gate['program_sha256']
 diagnostic_raw=subprocess.check_output(['sacct','-nP','-j','16366,16367','--format=JobIDRaw,JobName%60,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS,ReqMem,NodeList'],text=True,timeout=20)
 assert diagnostic_raw==diagnostic_gate['scheduler_raw']
 for n,e in diagnostic_gate['inputs'].items():
  q=pathlib.Path(n);assert q.is_relative_to(diagnostic) and not q.is_symlink()
  b=q.read_bytes();assert len(b)==e['bytes'] and hashlib.sha256(b).hexdigest()==e['sha256']
 run.mkdir(exist_ok=False)
 with archive.open('xb') as stream:stream.write(payload)
 for m in members:
  p=run/m.name;p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb') as stream:stream.write(tar.extractfile(m).read())
 for name,e in {**entries,'inventory.json':meta['inventory']}.items():
  b=(run/name).read_bytes();assert len(b)==e['bytes'] and hashlib.sha256(b).hexdigest()==e['sha256']
print(json.dumps(dict(status='source_only_staged_verified',archive=meta['archive'],inventory=meta['inventory'],regular_members=len(members),source_count=len(entries),storage=storage,old_disposition=old_disposition,new_scheduler_raw=new_raw,failed_v99_scheduler_raw=failed_raw,admission_scheduler_raw=admitted_raw,failed_v100_scheduler_raw=full_failed_raw,failed_v103_scheduler_raw=dispatch_raw,parent_v104_scheduler_raw=parent_raw,diagnostic_v110_scheduler_raw=diagnostic_raw,queue=queue,registered=False,launched=False,captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()),sort_keys=True))
'''.replace('METADATA', repr(json.dumps(preparation)))
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
intent = BASE / 'v112-stage-intent.json'
with intent.open('x') as stream:
    json.dump({'archive': preparation['archive'], 'created_utc': stamp, 'one_use': True}, stream)
(BASE / ('v112-stage-source-' + stamp + '.py')).write_text(source)
result = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                         '-o', 'ConnectionAttempts=1', '-o', 'PubkeyAuthentication=no',
                         'csis', 'python3 -B -c ' + shlex.quote(source)],
                        input=blob, capture_output=True, timeout=180)
out = BASE / ('v112-stage-result-' + stamp + '.json')
with out.open('xb') as stream:
    stream.write(result.stdout)
(BASE / ('v112-stage-stderr-' + stamp + '.txt')).write_bytes(result.stderr)
print(json.dumps({'exit': result.returncode, 'receipt': str(out), 'stderr': result.stderr.decode()[:4000]}))
if result.returncode == 0:
    data = json.loads(result.stdout)
    print(json.dumps({k:data[k] for k in ('status','archive','source_count','regular_members','captured_utc')}))
