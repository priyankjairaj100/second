"""One-use minimal source-only study in the unchanged calibration runtime."""
import os,sys,json,time,resource,signal,platform,gc
from pathlib import Path
RUN=Path(__file__).resolve().parents[1];sys.path.insert(0,str(RUN))
from research_v124.worker import enc,ident,read,save
from src.run_store import canonical_json,digest
from research_v135 import source_state
from research_v138.transaction import reconstruct,repair,publish

def write_raw(path,b):
 with path.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 return ident(b)

def bindings(p):
 from research_v136.preflight import validate
 validate(p['bound_inputs'])
 assert p['threads']==1 and p['memory_bytes']==16*2**30 and p['automatic_retry'] is False
 assert p['total_cpu_ceiling']==sum(c['cpu_seconds'] for c in p['phases'].values())+60*len(p['phases'])
 assert set(p['root_provenance'])==set(p['root_ids']) and len(p['root_ids'])==4

def checks(p,out):
 import unittest,numpy,gmpy2,zstandard
 from research_v112.software import SUITES
 assert platform.python_version()=='3.12.14' and numpy.__version__=='2.3.5' and gmpy2.version()=='2.3.2' and zstandard.__version__=='0.25.0'
 suites=dict(SUITES,source_only=(['research_v135.test_source_state'],10),source_transaction=(['research_v138.test_transaction'],6),native_source_transaction=(['research_v138.test_native'],1))
 result={};assert sum(x[1] for x in suites.values())==335
 for name,(mods,count) in suites.items():
  r=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromNames(mods));result[name]=dict(tests=r.testsRun,failures=len(r.failures),errors=len(r.errors),skips=len(r.skipped))
  save(out/(name+'.json'),result[name]);assert r.wasSuccessful() and not r.skipped and r.testsRun==count,name
 return dict(tests=335,suites=result,empirical_result=False,source_transaction_fault_points=['after_proposal','during_replay','before_seal','before_publish'],global_arithmetic_fault_campaign_complete=False)

def old_rows(p):
 from research_v112.campaign import load_records
 for e in p['source_inputs']:read(e)
 old=json.loads(read(p['source_inputs'][0]));rows,prov=load_records(old)
 assert [r['id'] for r in rows]==p['root_ids'] and prov==p['root_provenance']
 assert digest(canonical_json(dict(records=rows)))==p['root_records_sha256']
 return rows

def completion(phase,h):
 r=json.loads((RUN/phase/'completion.json').read_bytes())
 assert r['status']=='complete' and r['registration_sha256']==h and r['phase']==phase
 return r

def artifact(phase,name,h):
 r=completion(phase,h);e=r['artifacts'][name]
 return read(dict(path=str(RUN/phase/name),**e))

def reference_provider(profile,ids,h,seen,available=True):
 phase=profile+'__prepare';r=completion(phase,h);by=r['result']['providers']
 def provider(rid,metadata):
  assert rid in ids,'Deleted source lookup prohibited'
  if not available:raise PermissionError('Retained source unavailable by registered regime')
  name=by[rid];row=json.loads(artifact(phase,name,h));assert row['id']==rid and row['provenance']==metadata
  seen.append(rid);return row['tokens']
 return provider

def probes(profile,blob,ids,h):
 results=[]
 for retained in (True,False):
  for deleted in (True,False):
   seen=[];provider=reference_provider(profile,ids,h,seen,retained)
   try:
    view=source_state.select_retained(blob,ids,provider);status='available';mode=view.mode
   except PermissionError:status='refused';mode='references'
   assert status==('available' if mode=='tokens' or retained else 'refused')
   assert set(seen)<=set(ids)
   results.append(dict(retained_available=retained,deleted_available=deleted,status=status,external_record_reads=seen))
 return results

def measure(p,c,out,h):
 from research_v81.service import MatchedService
 from research_v112.policy import execution,verify_metadata
 from research_v132.worker import verify_target
 from research_v43.dispatcher import ResourcePolicy
 from research_v61.state import Record
 profile=c['profile'];role=c['role'];x=p['profiles'][profile];ids=tuple(p['root_ids'][-c['count']:]);external=[]
 for e in x['checkpoint'].values():read(e)
 anchor=read(x['anchor']);cal=read(x['calibration'])
 events=[]
 def mark(event,**kw):
  if event in ('stage_certified','source_replayed'):
   item=dict(event=event,**kw);save(out/('event-%03d.json'%len(events)),item);events.append(item)
   print(json.dumps(dict(event=event,profile=profile,phase=out.name,stage=kw.get('stage_id'),record=kw.get('record_id'))),flush=True)
 tick=time.perf_counter_ns();before=None
 with execution('optimized_modern') as scope:
  service=MatchedService(str(Path(x['checkpoint']['config.json']['path']).parent),profile,p['root_provenance'],mark,allow_proposed_grid_cap=True)
  verify_target(service.bound,anchor,cal);assert service.policy==ResourcePolicy()
  if role=='request':
   parent=c['predecessor'];filename=c['mode']+'/state.bin'
   before=artifact(parent,filename,h);provider=reference_provider(profile,ids,h,external)
   r=repair(service,before,ids,out/c['mode'],provider)
   assert external==([] if c['mode']=='tokens' else list(ids))
   # Extra availability checks are separately timed, with no neural traversal.
   t=time.perf_counter_ns();r['access_probes']=probes(profile,before,ids,h);r['access_probe_ns']=time.perf_counter_ns()-t
   assert artifact(parent,filename,h)==before
   modes=[c['mode']]
  else:
   rows=[r for r in old_rows(p) if r['id'] in ids]
   records=service.records(rows);codes,r=reconstruct(service,records)
   modes=['tokens','references'];r['states']={};model=b''.join(z.packed_indices for z in codes)
   for mode in modes:
    t=time.perf_counter_ns();blob=source_state.pack(service.bound,records,codes,mode)
    r['states'][mode]={'serialization_and_publication_ns':None,'artifacts':publish(out/mode,{'state.bin':blob,'model.bin':model,'trust.json':b'{}'}),'live_state_bytes':len(blob)+2,'canonical_state_bytes':len(blob),'trust_bytes':2}
    r['states'][mode]['serialization_and_publication_ns']=time.perf_counter_ns()-t
   if role=='prepare':
    providers={};(out/'source-provider').mkdir()
    for rec in records:
     name='source-provider/'+digest(rec.record_id.encode())+'.json';save(out/name,dict(id=rec.record_id,tokens=list(rec.tokens),provenance=json.loads(rec.provenance)));providers[rec.record_id]=name
    r['providers']=providers
   del codes,records,model;gc.collect()
  native=json.loads(service.provenance)
  assert len([e for e in events if e['event']=='stage_certified'])==4*x['blocks']
  assert [e['record_id'] for e in events if e['event']=='source_replayed']==list(ids)
  for mode in modes:
   state=(out/mode/'state.bin').read_bytes();target,head,codes=source_state._decode(state)
   assert target==service.bound and [q['record_id'] for q in head['records']]==list(ids)
   assert b''.join(z.packed_indices for z in codes)==(out/mode/'model.bin').read_bytes()
  del service,codes,state;gc.collect()
 verify_metadata(scope['point_route_policy']);assert scope['closed']
 r['context_and_cleanup_ns']=time.perf_counter_ns()-tick
 # Compare against an immutable historical output only after the new constructor.
 prior=p['root_models'][profile] if c['count']==4 else x['endpoints']['retained'+str(c['count'])]
 original=json.loads(read(prior['completion']));assert original['status']=='complete'
 for mode in modes:assert (out/mode/'model.bin').read_bytes()==read(prior['model'])
 if role=='prepare':
  required=sum((out/r['providers'][rid]).stat().st_size for rid in ids)
 else:
  parent=completion(profile+'__prepare',h)
  required=sum(parent['artifacts'][parent['result']['providers'][rid]]['bytes'] for rid in ids)
 r.update(profile=profile,role=role,count=c['count'],retained_ids=list(ids),external_request_reads=external,implementation=scope,native_calibration_runtime=native,historical_packed_model_equal=True,checkpoint_shared_bytes=sum(e['bytes'] for e in x['checkpoint'].values()),reference_mode_required_external_retained_source_bytes=required,token_mode_external_source_bytes=0,model_bin_is_audit_copy_of_embedded_deployed_codes=True,availability_probe_scope='state resolution only; no extra calibration',no_deleted_feature_traversal=True,cache_policy='natural OS cache; fresh process, not a cold-cache claim',timing_comparison_to_historical_is_exploratory=True)
 return r

def audit(p,out,h):
 results=[]
 for profile in p['profiles']:
  for count in (3,2):
   oracle=profile+'__oracle'+str(count)
   fresh=completion(oracle,h)
   assert fresh['result']['role']=='oracle' and fresh['result']['historical_packed_model_equal']
   for mode in ('tokens','references'):
    phase=profile+'__'+mode+str(count);r=completion(phase,h);q=r['result']
    assert q['role']=='request' and q['mode']==mode and q['historical_packed_model_equal']
    names=('state.bin','model.bin','trust.json')
    for name in names:
     assert artifact(phase,mode+'/'+name,h)==artifact(oracle,mode+'/'+name,h),phase+'/'+name
    state=artifact(phase,mode+'/state.bin',h);target,header,codes=source_state._decode(state)
    assert [v['record_id'] for v in header['records']]==p['root_ids'][-count:]
    assert all(('tokens' in v)==(mode=='tokens') for v in header['records'])
    assert q['timing']['neural_stage_record_pairs']==4*p['profiles'][profile]['blocks']*count
    assert all(e['route']=='token' and e['admission']['kind']=='point' for e in q['timing']['stages'])
    assert q['external_request_reads']==([] if mode=='tokens' else p['root_ids'][-count:])
    assert len(q['access_probes'])==4
    assert [v['status'] for v in q['access_probes']]==(['available']*4 if mode=='tokens' else ['available','available','refused','refused'])
    results.append(dict(phase=phase,oracle=oracle,exact_artifacts_equal=list(names),live_state_bytes=q['live_state_bytes'],context_and_cleanup_ns=q['context_and_cleanup_ns'],request_elapsed_ns=q['request_elapsed_ns'],required_external_source_bytes=q['reference_mode_required_external_retained_source_bytes'] if mode=='references' else 0,quality_qualified=not(profile=='gpt2' and count==3)))
 save(out/'comparisons.json',results)
 return dict(comparisons=results,complete_pairs=8,all_exact_same_representation_equal=True,
             independent_fresh_constructions=4,new_quality=False,replicated_speed_claim=False)

def main(phase,h):
 start=time.monotonic();raw=(RUN/'program.json').read_bytes();assert ident(raw)['sha256']==h;p=json.loads(raw);bindings(p)
 assert p['directory']==str(RUN) and phase in p['phases'] and sys.platform=='linux' and platform.node()=='csis.mn1' and not sys.flags.optimize
 group=p['phases'][phase]['group']
 j=json.loads((RUN/('jobs-'+group+'.json')).read_bytes());assert j['registration_sha256']==h and str(j['jobs'][phase])==os.environ['SLURM_JOB_ID']
 os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});c=p['phases'][phase]
 resource.setrlimit(resource.RLIMIT_CPU,(c['cpu_seconds'],c['cpu_seconds']+1));resource.setrlimit(resource.RLIMIT_AS,(p['memory_bytes'],)*2);resource.setrlimit(resource.RLIMIT_FSIZE,((2**31 if phase=='checks' else 128*2**20),)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 def expire(*a):raise TimeoutError('Registered limit reached')
 signal.signal(signal.SIGALRM,expire);signal.signal(signal.SIGXCPU,expire);signal.alarm(c['wall_seconds']-30)
 out=RUN/phase;out.mkdir(exist_ok=False);save(out/'attempt.json',dict(registration_sha256=h,job_id=os.environ['SLURM_JOB_ID'],phase=phase))
 r=dict(schema='minimal-source-only-v138',status='failed',phase=phase,registration_sha256=h,job_id=os.environ['SLURM_JOB_ID'],error=None,result=None)
 try:
  assert all(os.environ.get(k)=='1' for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'])
  for n,e in p['sources'].items():read(dict(path=str(RUN/n),**e))
  if phase=='checks':r['result']=checks(p,out)
  else:
   ck=completion('checks',h);assert ck['result']['tests']==335
   r['result']=audit(p,out,h) if phase=='audit' else measure(p,c,out,h)
  for n,e in p['sources'].items():read(dict(path=str(RUN/n),**e))
  r['status']='complete'
 except BaseException as e:
  import traceback;traceback.print_exc();r['error']=dict(type=type(e).__name__,message=str(e),diagnostics=getattr(e,'service_diagnostics',None))
 finally:
  r.update(process_cpu_seconds=time.process_time(),child_cpu_seconds=sum(resource.getrusage(resource.RUSAGE_CHILDREN)[:2]),elapsed_seconds=time.monotonic()-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,host=platform.node(),python=sys.version)
  r['artifacts']={str(f.relative_to(out)):ident(f.read_bytes()) for f in out.rglob('*') if f.is_file()};save(out/'completion.json',r)
 assert r['status']=='complete',r['error']
if __name__=='__main__':main(*sys.argv[1:])
