"""No calibration: validate frozen producer, actual files and stage certificates."""
from pathlib import Path
import json,hashlib,subprocess
from research_v135.source_state import _decode,select_retained
from src.run_store import canonical_json

def ident(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def bound(e):
 p=Path(e['path']);assert p.is_file() and not p.is_symlink();b=p.read_bytes();assert ident(b)=={k:e[k] for k in ('bytes','sha256')};return b

def saved_model_checks(blob,model,trust,anchor,fixed,ids,mode,events):
 target,head,codes=_decode(blob)
 assert target.anchor_payload==anchor
 assert canonical_json(json.loads(target.fixed_payload)['calibration_target'])==fixed
 assert head['mode']==mode and [r['record_id'] for r in head['records']]==ids
 assert b''.join(c.packed_indices for c in codes)==model and trust==b'{}'
 stages=[e for e in events if e['event']=='stage_certified']
 assert len(stages)==len(codes)
 for c,e in zip(codes,stages):
  assert e['stage_id']==c.stage_id and e['code_sha256']==ident(c.packed_indices)['sha256']
  assert e['route']=='token' and not e['fallback'] and e['admission']['kind']=='point'
  assert e['admission']['admitted'] and e['admission']['selected_route']=='token'
 assert [e['record_id'] for e in events if e['event']=='source_replayed']==ids
 return dict(stages=len(stages),model=ident(model),state=ident(blob),trust=ident(trust))

def run(p):
 prior=Path(p['producer']['path']).parent;raw=bound(p['producer']);old=json.loads(raw);h=ident(raw)['sha256']
 for n,e in old['sources'].items():bound(dict(path=str(prior/n),**e))
 jobs=p['producer_jobs'];account=bound(p['scheduler_snapshot']).decode()
 rows={x.split('|')[0]:x.split('|') for x in account.splitlines() if x.strip()};results={};oracles={}
 for phase,job in jobs.items():
  cfg=old['phases'][phase];r=prior/phase
  if cfg.get('predecessor','').endswith('3'):
   assert rows[str(job)][1].startswith('CANCELLED'),(phase,rows[str(job)])
   assert not r.exists();results[phase]=dict(job_id=job,producer_state=rows[str(job)][1],unexecuted=True);continue
  assert rows[str(job)][1:3]==['FAILED','1:0'],(phase,rows[str(job)])
  c=json.loads((r/'completion.json').read_bytes());assert c['status']=='failed' and c['registration_sha256']==h and c['job_id']==str(job) and c['result'] is None
  n=cfg['count'];profile=cfg['profile'];x=old['profiles'][profile]
  assert c['error']['type']=='KeyError' and c['error']['message']==repr('retained'+str(n))
  stderr=(prior/(phase+'.err')).read_text();assert "KeyError: 'retained"+str(n)+"'" in stderr
  for name,e in c['artifacts'].items():bound(dict(path=str(r/name),**e))
  events=[json.loads((r/name).read_bytes()) for name in sorted(c['artifacts']) if name.startswith('event-')]
  modes=['tokens','references'] if cfg['role']=='oracle' else [cfg['mode']]
  model=bound(x['endpoints']['candidate_'+str(n)]['model']);anchor=bound(x['anchor']);fixed=bound(x['calibration']);ids=old['root_ids'][-n:]
  checked={}
  for mode in modes:
   b={name:(r/mode/name).read_bytes() for name in ('state.bin','model.bin','trust.json')}
   assert b['model.bin']==model
   checked[mode]=saved_model_checks(b['state.bin'],b['model.bin'],b['trust.json'],anchor,fixed,ids,mode,events)
   def provider(rid,metadata):
    assert rid in ids
    prep=json.loads((prior/(profile+'__prepare')/'completion.json').read_bytes());fname=prep['result']['providers'][rid]
    q=json.loads(bound(dict(path=str(prior/(profile+'__prepare')/fname),**prep['artifacts'][fname])))
    assert q['id']==rid and q['provenance']==metadata;return q['tokens']
   view=select_retained(b['state.bin'],tuple(ids),provider)
   assert [z.record_id for z in view.records]==ids
  results[phase]=dict(producer_completion=dict(path=str(r/'completion.json'),**ident((r/'completion.json').read_bytes())),producer_stderr=dict(path=str(prior/(phase+'.err')),**ident((prior/(phase+'.err')).read_bytes())),job_id=job,producer_state='FAILED',producer_exit='1:0',reporting_error=c['error'],checked=checked,successful_service_timing_available=False,actual_failed_worker_elapsed=c['elapsed_seconds'],actual_failed_worker_cpu=c['process_cpu_seconds'],result_sidecar_missing=True)
  if cfg['role']=='oracle':
   oracles[phase]=dict(producer_job=job,producer_state='FAILED',artifacts={mode+'/'+name:dict(path=str(r/mode/name),**c['artifacts'][mode+'/'+name]) for mode in modes for name in ('state.bin','model.bin','trust.json')})
 assert len(oracles)==4 and len(results)==12
 return dict(producer_registration_sha256=h,producer_sources_verified=len(old['sources']),results=results,oracles=oracles,sacct=account,calibration_repeated=False,old_status_modified=False,first_endpoint_outputs_audited=4,independently_constructed_oracles_audited=4,blocked_second_endpoints=4)
