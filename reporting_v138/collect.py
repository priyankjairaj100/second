"""One-use final receipt collector. Run only after all sixteen actual jobs close.

No submission, numerical work, retry or remote write is performed here. The
registered independent audit compares actual state/model/trust bytes remotely;
this collector preserves its receipts and reconciles scheduler accounting.
"""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
PILOT=ROOT/'pilots/minimal-source-only-v138-20261030'
def ident(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def seconds(s):
 fields=s.split(':');v=0.
 for x in fields:v=v*60+float(x)
 return v

def validate(report,program,registration):
 assert report['registration_sha256']==registration
 assert set(report['receipts'])==set(program['phases'])
 seen=set();cpu=0.;rows={}
 for line in report['sacct'].splitlines():
  if not line.strip():continue
  c=line.split('|')
  if c[0].isdigit():
   assert c[0] not in rows;rows[c[0]]=c
 for phase,c in report['receipts'].items():
  assert c['status']=='complete' and c['error'] is None and c['phase']==phase and c['registration_sha256']==registration
  job=str(c['job_id']);assert job not in seen;seen.add(job)
  a=rows[job];assert a[1:3]==['COMPLETED','0:0'];cpu+=seconds(a[4])
  assert c['process_cpu_seconds']<=program['phases'][phase]['cpu_seconds']+1
 assert report['receipts']['checks']['result']['tests']==335
 audit=report['receipts']['audit']['result'];assert audit['complete_pairs']==8 and audit['independent_fresh_constructions']==4 and audit['all_exact_same_representation_equal']
 comparisons=[]
 for row in audit['comparisons']:
  phase=row['phase'];c=report['receipts'][phase];r=c['result'];f=report['receipts'][row['oracle']]['result'];mode=r['mode'];n=r['count'];prof=r['profile']
  assert n in (2,3) and r['retained_ids']==program['root_ids'][-n:]
  assert row['quality_qualified']==(not(prof=='gpt2' and n==3))
  for name in ('state.bin','model.bin','trust.json'):
   assert c['artifacts'][mode+'/'+name]==report['receipts'][row['oracle']]['artifacts'][mode+'/'+name]
  assert r['live_state_bytes']==c['artifacts'][mode+'/state.bin']['bytes']+2
  assert r['external_request_reads']==([] if mode=='tokens' else program['root_ids'][-n:])
  assert r['timing']['neural_stage_record_pairs']==program['profiles'][prof]['blocks']*4*n
  assert [x['status'] for x in r['access_probes']]==(['available']*4 if mode=='tokens' else ['available','available','refused','refused'])
  comparisons.append(dict(profile=prof,retained=n,mode=mode,quality_qualified=row['quality_qualified'],live_state_bytes=r['live_state_bytes'],required_external_source_bytes=row['required_external_source_bytes'],request_seconds=r['request_elapsed_ns']/1e9,context_seconds=r['context_and_cleanup_ns']/1e9,worker_seconds=c['elapsed_seconds'],source_stage_record_pairs=r['timing']['neural_stage_record_pairs'],temporary_feature_bytes=r['temporary_feature_array_bytes'],peak_rss_kib=c['peak_rss_kib'],saved_predecessor_bytes=r['predecessor_bytes']))
 assert len(comparisons)==8 and len(seen)==16
 assert cpu<=program['total_cpu_ceiling']
 return dict(schema='minimal-source-only-closure-v138',registration_sha256=registration,actual_jobs=len(seen),all_terminal=True,actual_allocation_cpu_seconds=cpu,launcher_cpu_not_measured=True,ceiling=program['total_cpu_ceiling'],comparisons=comparisons,source_only_fresh_state_model_trust_equality=True,numerical_source_checks_are_not_independent_reproduction=True,clean_external_input_reproduction=False,replicated_timing=False)

def collect():
 p=json.loads((PILOT/'program.json').read_bytes());m=json.loads((PILOT/'package.json').read_bytes());h=m['registration_sha256'];assert ident((PILOT/'program.json').read_bytes())['sha256']==h
 # Exclusive local intent makes this collection a single auditable attempt.
 with (PILOT/'final-collection-intent.json').open('x') as f:json.dump(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),registration_sha256=h),f)
 remote=r'''from pathlib import Path
import json,hashlib,subprocess,datetime
r=Path(NAMESPACE);h=REGISTRATION
raw=(r/'program.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==h;p=json.loads(raw)
receipts={};jobs=[]
for phase in p['phase_order']:
 c=json.loads((r/phase/'completion.json').read_bytes());assert c['status']=='complete' and c['registration_sha256']==h
 receipts[phase]=c;jobs.append(str(c['job_id']))
assert len(jobs)==len(set(jobs))==16
sacct=subprocess.run(['sacct','-n','-P','-j',','.join(jobs),'--format=JobID,State,ExitCode,ElapsedRaw,TotalCPU,MaxRSS'],capture_output=True,text=True,check=True).stdout
rows={s.split('|')[0]:s.split('|') for s in sacct.splitlines() if s.strip()}
assert all(rows[j][1:3]==['COMPLETED','0:0'] for j in jobs)
source_bytes=0
for name,e in p['sources'].items():
 b=(r/name).read_bytes();assert len(b)==e['bytes'] and hashlib.sha256(b).hexdigest()==e['sha256'];source_bytes+=len(b)
print(json.dumps(dict(registration_sha256=h,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),receipts=receipts,sacct=sacct,frozen_sources_verified=len(p['sources']),frozen_source_bytes=source_bytes,submissions={f.name:json.loads(f.read_bytes()) for f in r.glob('jobs-*.json')},stderr={phase:(r/(phase+'.err')).read_text() for phase in p['phase_order']}),sort_keys=True))
'''.replace('NAMESPACE',repr(m['namespace'])).replace('REGISTRATION',repr(h))
 z=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','csis',"/nfs_home/software/envs/pytorch-12.8/bin/python3.10 - <<'PY'\n"+remote+'\nPY'],capture_output=True,text=True)
 (PILOT/'final-collection-transport.json').write_text(json.dumps(dict(returncode=z.returncode,stderr=z.stderr),indent=2)+'\n');assert z.returncode==0,z.stderr
 report=json.loads(z.stdout);result=validate(report,p,h)
 with (PILOT/'actual-final-receipts.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
 with (PILOT/'actual-closure.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps(result,indent=2))
if __name__=='__main__':collect()
