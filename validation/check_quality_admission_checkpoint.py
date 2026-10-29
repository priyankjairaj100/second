"""Verify actual failed-chain and separate saved-frame audit receipt metadata."""
from pathlib import Path
import json,hashlib,tarfile
from research_v71.campaign import v70_costs
R=Path(__file__).resolve().parents[1]
def info(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def load(name):
 p=R/'campaigns'/name
 with tarfile.open(p) as t:
  m=t.getmembers();assert len(m)<180 and len({x.name for x in m})==len(m) and all(x.isfile() and x.size<4*2**20 and '..' not in Path(x.name).parts and not Path(x.name).is_absolute() for x in m)
  f={x.name:t.extractfile(x).read() for x in m}
 c=json.loads(f['collection.json']);assert c['files']=={n:info(b) for n,b in f.items() if n!='collection.json'}
 assert c['frozen_sources_verified']==532 and c['no_numerical_worker_or_loss_output'] is True
 return f,c,info(p.read_bytes())
f,c,a=load('csis_v69_failed_admission_20261018_a.tar.gz');p=json.loads(f['program.json'])
assert f['program.json']==(R/'handoff/registration_v69_quality.json').read_bytes()
assert set(c['jobs'])=={str(x) for x in range(15395,15404)}
rows={r[0]:r[1:] for line in c['accounting'].splitlines() if (r:=line.split('|'))[0].isdigit()}
assert rows['15395']==['FAILED','1:0','2','00:02.007','1']
assert all(rows[str(x)]==['CANCELLED','0:0','0','00:00:00','0'] for x in range(15396,15404))
e=json.loads(f['cpu_checks/entry.json']);assert e['status']=='failed' and e['outputs'] is None and e['error']['message']=='Entire inspected frame must remain excluded'
assert not any('/worker/' in n or '/outputs/' in n or n.startswith('budget/') for n in f)
assert e['process_cpu_ns']+e['waited_child_cpu_ns']<=2008000000
for n,b in p['new_sources'].items():assert info(f[str(Path(n).relative_to(p['directory']))])==b
f70,c70,a70=load('csis_v70_frame_audit_20261018_a.tar.gz');r=json.loads(f70['receipt.json']);p70=json.loads(f70['program.json'])
assert f70['program.json']==(R/'handoff/registration_v70_frame.json').read_bytes()
assert r['registration_sha256']==info(f70['program.json'])['sha256'] and r['status']=='complete' and r['error'] is None
v=r['result'];assert v['status']=='verified' and v['actual_exact_exclusion_union'] is True and v['retokenized_saved_prefix'] is True
assert v['full_frame_articles']==len(v['complete_token_hashes'])==3801 and v['short_records']==1021
assert v['inputs']=={k:{n:e[n] for n in ['bytes','sha256']} for k,e in p70['inputs'].items()}
assert [x['id'] for x in v['complete_token_hashes']]==[f'c4:en:validation:shard1:line{i}' for i in range(3801)]
assert v['saved_data_audit']['status']=='verified' and v['saved_data_audit']['selected_articles']==320
cost=v70_costs(r,c70['accounting'])
result=dict(status='verified_failed_admission_and_separate_frame_audit_metadata',failed_campaign_archive=a,frame_audit_archive=a70,failed_job='15395',cancelled_jobs=list(map(str,range(15396,15404))),failed_scheduler_cpu_seconds='2.007',failed_controller_cpu_ns=e['process_cpu_ns']+e['waited_child_cpu_ns'],numerical_worker_started=False,quality_losses_evaluated=False,frame_audit_job='15404',frame_audit_costs=cost,full_frame_articles=3801,short_records=1021,actual_retokenization_repeated_locally=False,no_frozen_source_changed=True)
(R/'validation/v70_admission_and_frame_reconciliation.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps(result))
