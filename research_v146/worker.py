"""One-use fresh-directory reproduction, using existing frozen numerical code."""
import os,sys,json,time,resource,signal,platform,gc,hashlib
from pathlib import Path
RUN=Path(__file__).resolve().parents[1];sys.path.insert(0,str(RUN))
from research_v146.bootstrap import install,ident

def save(path,obj):
 with path.open('x') as f:json.dump(obj,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def read(e):
 path=Path(e['path']);assert path.is_file() and not path.is_symlink();b=path.read_bytes();assert ident(b)=={k:e[k] for k in ('bytes','sha256')};return b
def previous(phase,h):
 c=json.loads((RUN/phase/'completion.json').read_bytes());assert c['status']=='complete' and c['registration_sha256']==h
 return c

def selected_records(rows,ids):
 assert type(rows) is list and len(rows)==13 and len({r['id'] for r in rows})==13
 assert rows==sorted(rows,key=lambda r:r['id'])
 assert len(ids)==4 and ids==sorted(set(ids))
 assert all(set(r)=={'id','tokens'} and type(r['id']) is str and type(r['tokens']) is list and len(r['tokens'])==128 and all(type(t) is int and 0<=t<50257 for t in r['tokens']) for r in rows)
 chosen=[r for r in rows if r['id'] in ids]
 assert [r['id'] for r in chosen]==ids
 return chosen

def target_matches(service,p):
 from src.run_store import canonical_json
 assert ident(service.bound.anchor_payload)['sha256']==p['anchor_sha256']
 assert ident(canonical_json(json.loads(service.bound.fixed_payload)['calibration_target']))['sha256']==p['calibration_sha256']

def setup(p,out):
 from src.run_store import canonical_json
 from research_v143.worker import checks
 from research_v140.campaign import run
 import numpy,gmpy2,zstandard
 for m in (numpy,gmpy2,zstandard):assert Path(m.__file__).is_relative_to(RUN/'deps'),m.__file__
 d=RUN/'inputs';d.mkdir(exist_ok=False);(d/'checkpoint').mkdir()
 artifacts={}
 for name,e in p['checkpoint'].items():
  b=read(e);f=d/'checkpoint'/name
  with f.open('xb') as q:q.write(b)
  assert ident(f.read_bytes())==ident(b);artifacts['checkpoint/'+name]=ident(b);del b
 rows=selected_records(json.loads(read(p['external_records']))['records'],p['root_ids'])
 b=canonical_json(dict(records=rows));assert ident(b)['sha256']==p['root_records_sha256']
 with (d/'records.json').open('xb') as f:f.write(b)
 artifacts['records.json']=ident(b);save(d/'manifest.json',artifacts)
 q=checks(p,out);assert q['tests']==338
 import unittest
 suite=unittest.defaultTestLoader.loadTestsFromName('research_v146.test_bootstrap')
 result=unittest.TextTestRunner(verbosity=1).run(suite)
 assert result.wasSuccessful() and result.testsRun==7 and not result.skipped
 save(out/'bootstrap-tests.json',dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped)))
 a=run();assert len(a['cases'])==406;save(out/'native-arithmetic.json',a)
 from research_v81.service import MatchedService
 service=MatchedService(str(d/'checkpoint'),'distilgpt2',p['root_provenance'],allow_proposed_grid_cap=True)
 target_matches(service,p);del service;gc.collect()
 return dict(inputs=artifacts,software_tests=345,generated_arithmetic_cases=406,fresh_wheel_environment=True,original_checkpoint_and_declared_token_records_only=True,target_identity_verified=True)

def model(p,phase,out,h):
 from research_v81.service import MatchedService
 from research_v81.operations import request
 from research_v112.policy import execution,verify_metadata
 from research_v61.service import telemetry,trust_json
 from src.run_store import canonical_json
 from research_v61.state import validate_state
 previous('checks',h);i=json.loads((RUN/'inputs/manifest.json').read_bytes())
 for name,e in i.items():read(dict(path=str(RUN/'inputs'/name),**e))
 rows=json.loads((RUN/'inputs/records.json').read_bytes())['records'];retained=rows[-2:];used=rows if phase=='prepare' else retained;events=[]
 def mark(event,**kw):
  if event in ('source_replayed','stage_certified'):
   entry=dict(event=event,**kw);save(out/('event-%03d.json'%len(events)),entry);events.append(entry)
 def write(name,b):
  with (out/name).open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
  return dict(file=name,**ident(b))
 tick=time.perf_counter_ns()
 with execution('optimized_compressed') as scope:
  service=MatchedService(str(RUN/'inputs/checkpoint'),'distilgpt2',p['root_provenance'],mark,allow_proposed_grid_cap=True)
  target_matches(service,p)
  if phase=='request':
   c=previous('prepare',h)
   def predecessor():
    return tuple(read(dict(path=str(RUN/'prepare'/n),**c['artifacts'][n])) for n in ('state.bin','trust.json'))
   r=request(service,rows,retained,'compressed',predecessor,write)
  else:
   t=telemetry();service.admit(used,'compressed48');values=service.extract(used,t)
   codes,admission=service.solve(used,'lossless',{}, {}, {},t,direct_values=values)
   payloads,grams,trust=service.prepare_payloads(used,values,'compressed48',t)
   blob=service.serialize(used,codes,'compressed48',payloads,grams,trust,t)
   write('state.bin',blob);write('model.bin',b''.join(c.packed_indices for c in codes));write('trust.json',canonical_json(trust_json(trust)))
   r=dict(timing=t,admission=admission,independent_retained_constructor=phase=='oracle',prior_state_read=False)
   del blob,codes,payloads,grams,trust,values;gc.collect()
  c=validate_state((out/'state.bin').read_bytes(),expected_target=service.bound,expected_records=service.records(used))
  assert c.representation=='compressed48'
  r['native_runtime']=json.loads(service.provenance);del service,c;gc.collect()
 verify_metadata(scope['point_route_policy']);assert scope['closed']
 r.update(profile='distilgpt2',phase=phase,retained_ids=[r['id'] for r in used],context_and_cleanup_ns=time.perf_counter_ns()-tick,implementation=scope,complete_model=True)
 assert len([e for e in events if e['event']=='stage_certified'])==24
 expected=p['expected_root_model_sha256'] if phase=='prepare' else p['expected_retained_model_sha256']
 assert ident((out/'model.bin').read_bytes())['sha256']==expected
 return r

def audit(p,out,h):
 for phase in ('checks','prepare','request','oracle'):previous(phase,h)
 result={}
 for name in ('state.bin','model.bin','trust.json'):
  c=previous('request',h);a=read(dict(path=str(RUN/'request'/name),**c['artifacts'][name]))
  c=previous('oracle',h);b=read(dict(path=str(RUN/'oracle'/name),**c['artifacts'][name]));assert a==b,name
  result[name]=ident(a)
 return dict(exact_artifacts=result,full_prepare_delete_oracle_audit_chain=True,original_production_sources_unchanged=True,previous_model_outputs_used_as_inputs=False,new_calibration_root=False,scope='fresh workspace and pinned wheel payload environment from original checkpoint and declared tokenized records; upstream corpus tokenization not repeated')

def main(phase,h):
 start=time.monotonic();raw=(RUN/'program.json').read_bytes();assert ident(raw)['sha256']==h;p=json.loads(raw);assert p['directory']==str(RUN)
 c=p['phases'][phase];jobs=json.loads((RUN/('jobs-'+c['group']+'.json')).read_bytes());assert jobs['registration_sha256']==h and str(jobs['jobs'][phase])==os.environ['SLURM_JOB_ID']
 assert platform.python_version()=='3.12.14' and sys.platform=='linux' and platform.node()=='csis.mn1' and not sys.flags.optimize
 os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_CPU,(c['cpu_seconds'],c['cpu_seconds']+1));resource.setrlimit(resource.RLIMIT_AS,(16*2**30,)*2);resource.setrlimit(resource.RLIMIT_FSIZE,((2**31 if phase=='checks' else 128*2**20),)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 def expire(*args):raise TimeoutError('Registered reproduction cap reached')
 signal.signal(signal.SIGALRM,expire);signal.signal(signal.SIGXCPU,expire);signal.alarm(c['wall_seconds']-30)
 out=RUN/phase;out.mkdir(exist_ok=False);save(out/'attempt.json',dict(registration_sha256=h,job_id=os.environ['SLURM_JOB_ID']))
 r=dict(schema='clean-compressed-reproduction-v146',registration_sha256=h,phase=phase,job_id=os.environ['SLURM_JOB_ID'],status='failed',error=None,result=None)
 try:
  for n,e in p['sources'].items():assert ident((RUN/n).read_bytes())==e,n
  for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):assert os.environ[k]=='1'
  r['environment_manifest']=install(RUN,p,phase=='checks')
  if phase!='checks':assert r['environment_manifest']==previous('checks',h)['environment_manifest']
  r['result']=setup(p,out) if phase=='checks' else audit(p,out,h) if phase=='audit' else model(p,phase,out,h)
  for n,e in p['sources'].items():assert ident((RUN/n).read_bytes())==e,n
  r['status']='complete'
 except BaseException as e:
  import traceback;traceback.print_exc();r['error']=dict(type=type(e).__name__,message=str(e))
 finally:
  r.update(elapsed_seconds=time.monotonic()-start,process_cpu_seconds=time.process_time(),child_cpu_seconds=sum(resource.getrusage(resource.RUSAGE_CHILDREN)[:2]),peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,host=platform.node(),python=sys.version)
  r['artifacts']={f.name:ident(f.read_bytes()) for f in out.iterdir() if f.is_file()};save(out/'completion.json',r)
 assert r['status']=='complete',r['error']
if __name__=='__main__':main(*sys.argv[1:])
