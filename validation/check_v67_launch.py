"""Portable launch/qualification evidence only; no scientific result inference."""
from pathlib import Path
import io,tarfile,json,hashlib,math
R=Path(__file__).resolve().parents[1];A=R/'campaigns/csis_v67_launch_metadata_20261016.tar.gz'
SHA='11e0db146e79330852f550a1cc3b2dd7568a66cdfe8006b004dca3840149cc30'
def info(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
raw=A.read_bytes();assert info(raw)==dict(bytes=145359,sha256='bb5d05edede86264f03a3cd9912495ad4f2ab433a2ef53a29c900ee819c1c5f0')
files={}
with tarfile.open(fileobj=io.BytesIO(raw)) as t:
 for m in t.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts and m.size<8*2**20 and m.name not in files
  files[m.name]=t.extractfile(m).read()
def obj(n):
 x=json.loads(files[n]);assert canonical(x)==files[n];return x
collection=obj('collection.json');assert len(files)==65 and set(files)==set(collection['files'])|{'collection.json'}
for n,e in collection['files'].items():assert info(files[n])==e
p=obj('program.json');assert info(files['program.json'])['sha256']==SHA and files['program.json']==(R/'handoff/registration_v67.json').read_bytes()
assert obj('registration.json')==dict(program_sha256=SHA)
run=Path(p['directory']);root=run.parents[1]
assert len(p['prior_sources'])==456 and len(p['new_sources'])==13
for name,e in p['prior_sources'].items():
 parts=Path(name).relative_to(root).parts;local=R/Path(*(parts if parts[0]!='local_runs' else parts[2:]));assert info(local.read_bytes())==e
for name,e in p['new_sources'].items():
 n=str(Path(name).relative_to(run));assert info(files[n])==e==info((R/n).read_bytes())
c=obj('software-completion.json');assert c['program_sha256']==SHA and c['status']=='complete' and c['tests']==64 and c['errors']==c['failures']==c['skipped']==0 and c['empirical_execution'] is False
assert '15261|second67-checks|COMPLETED|0:0|' in collection['accounting']
assert c['process_cpu_ns']+c['waited_child_cpu_ns']<602*10**9
jobs=obj('chain-submission.json')['jobs'];assert [j['name'] for j in jobs]==p['trial_order']+['primary','supplemental'] and len({j['job_id'] for j in jobs})==14
previous='15261'
for j in jobs:
 name=j['name'];a=j['arguments'];assert obj(name+'-submission.json')==j and obj(name+'-submission-intent.json')['arguments']==a
 assert '--dependency=afterok:'+previous in a and '--no-requeue' in a and '--kill-on-invalid-dep=yes' in a and '--nodelist=csis.mn1' in a and '--mem=16G' in a
 wall=p['trials'][name]['wall_seconds']+600 if name in p['trials'] else p[name+'_audit_caps']['wall'];minutes=math.ceil(wall/60)
 assert f'--time={minutes//60:02d}:{minutes%60:02d}:00' in a
 assert a[-3:]==['run',SHA,name] if name in p['trials'] else a[-2:]==[name,SHA]
 previous=j['job_id']
ledger=obj('budget/ledger.json');assert ledger['binding']['identity']['protocol_sha256']==SHA and len(ledger['attempts'])==1
attempt=next(iter(ledger['attempts'].values()));assert attempt['state']=='reserved' and attempt['observed_cpu_ns'] is None and attempt['reserved_cpu_seconds']==12602
assert not collection['terminal_receipts_present'] and 'primary-audit.json' not in files and 'supplemental-audit.json' not in files
result=dict(status='verified_launch_and_software_metadata_only',archive=info(raw),copied_files=len(files),frozen_sources_verified=469,program_sha256=SHA,
 software=dict(job_id='15261',tests=64,skips=0,failures=0,errors=0,process_and_waited_child_cpu_ns=c['process_cpu_ns']+c['waited_child_cpu_ns'],scheduler_allocation_cpu_seconds=9.977),
 jobs=[dict(name=j['name'],job_id=j['job_id']) for j in jobs],captured_at_utc=collection['captured_at_utc'],
 preparation_at_capture='RUNNING',numerical_worker_ledger_at_capture='one_reserved_attempt_no_observed_CPU_yet',
 numerical_result_verified=False,actual_model_state_comparison_repeated_locally=False,all_empirical_and_audit_outcomes_pending=True)
print(json.dumps(result,sort_keys=True,indent=2))
