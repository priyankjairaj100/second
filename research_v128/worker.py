"""Separately registered matched sequential controls; no old launcher is called."""
import os,sys,json,time,resource,signal,platform,math,hashlib,gc
from pathlib import Path
RUN=Path(__file__).resolve().parents[1];sys.path.insert(0,str(RUN))
from research_v124.worker import enc,ident,read,save

def retained(root,ids):
 assert len(root)==4 and [r['id'] for r in root]==sorted({r['id'] for r in root})
 assert len(ids) in (2,3) and ids==sorted(set(ids))
 by={r['id']:r for r in root};assert set(ids)<=set(by)
 assert all(len(r['tokens'])==128 and all(type(t)is int and 0<=t<50257 for t in r['tokens']) for r in root)
 return [by[i] for i in ids]

def tests(p,out):
 import unittest,numpy,gmpy2,zstandard
 from research_v112.software import SUITES
 assert platform.python_version()=='3.12.14' and numpy.__version__=='2.3.5' and gmpy2.version()=='2.3.2' and zstandard.__version__=='0.25.0'
 suites=dict(SUITES,matched_sequential=(['research_v55.test_sequential'],6),matched_membership=(['research_v128.test_worker'],4))
 result={}
 assert sum(x[1] for x in suites.values())==328
 for name,(mods,count) in suites.items():
  r=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromNames(mods))
  result[name]={'tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'skips':len(r.skipped)}
  save(out/(name+'.json'),result[name]);assert r.wasSuccessful() and not r.skipped and r.testsRun==count,name
 return {'tests':328,'suites':result,'empirical_result':False,'complete_new_transaction_fault_campaign':False}

def construct(p,profile,role,out,h):
 from research_v81.service import MatchedService
 from research_v112.policy import execution,verify_metadata
 from research_v71.model_gate import restore,construct_sequential,matched_codes
 from src.run_store import canonical_json,digest
 from research_v43.dispatcher import ResourcePolicy
 from research_v125.worker import unroll
 import numpy as np
 ck=json.loads((RUN/'checks/completion.json').read_text());assert ck['status']=='complete' and ck['registration_sha256']==h
 x=p['profiles'][profile];end=x['endpoints'][role]
 for e in x['checkpoint'].values():read(e)
 original=json.loads(read(end['completion']));blob=read(end['model']);anchor=read(x['anchor']);cal=read(x['calibration'])
 assert original['status']=='complete' and original['complete_model'] and original['base_target_sha256']==ident(anchor)['sha256'] and original['calibration_target_sha256']==ident(cal)['sha256']
 assert original['artifacts']['model.bin']['sha256']==ident(blob)['sha256']
 root=json.loads(read(p['calibration_records'][profile]))['records'];rows=retained(root,original['request']['retained_ids']);assert len(rows)==int(role[-1])
 marks=[]
 def mark(event):
  save(out/('stage-%03d.json'%len(marks)),event);marks.append(event);print(json.dumps({'phase':'sequential','profile':profile,'role':role,'stage':event['stage_id'],'completed_stages':len(marks)}),flush=True)
 with execution('optimized_compressed') as scope:
  service=MatchedService(str(Path(x['checkpoint']['config.json']['path']).parent),profile,root,allow_proposed_grid_cap=True)
  assert service.bound.anchor_payload==anchor and service.bound.fixed_payload==cal
  assert service.policy==ResourcePolicy()
  candidate=restore(blob,service.base,expected_blob=ident(blob),expected_target_sha256=ident(anchor)['sha256'])
  codes,report=construct_sequential(service.decoder,service.base,rows,candidate,expected_target_sha256=ident(anchor)['sha256'],expected_records_sha256=digest(canonical_json({'records':rows})),policy=service.policy,progress=mark)
  matched_codes(codes,service.base,ident(anchor)['sha256']);saved=b''.join(c.packed_indices for c in codes)
  # Independent nibble expansion and actual code arrays agree for every word.
  expanded=unroll(saved,json.loads(anchor)['stages'])
  for c in codes:assert np.array_equal(c.array(),expanded[c.stage_id])
  assert len(marks)==len(codes)==x['blocks']*4 and report['diagnostics']['stages']==marks
  assert all(r['route']=='token' for r in marks)
  assert all(a['kind']=='point' and a['selected_route']=='token' and a['selection_policy']==p['point_policy'] for a in report['diagnostics']['point_admission'])
  # These inputs are only read; rehash after the complete construction.
  for e in [end['completion'],end['model'],x['anchor'],x['calibration'],p['calibration_records'][profile],*x['checkpoint'].values()]:read(e)
  with (out/'model.bin').open('xb') as f:f.write(saved);f.flush();os.fsync(f.fileno())
  assert ident((out/'model.bin').read_bytes())==ident(saved)
  save(out/'codes.json',{'stages':[c.metadata() for c in codes]});save(out/'construction.json',report)
 verify_metadata(scope['point_route_policy']);assert scope['closed']
 return {'profile':profile,'role':role,'complete_model':True,'model':ident(saved),'anchor':x['anchor'],'calibration':x['calibration'],'retained_ids':[r['id'] for r in rows],'first_stage_equal':report['first_stage_equal'],'stages':len(codes),'code_count':report['code_count'],'scope':scope,'native_calibration_runtime':service.provenance,'quality_evaluation':False,'complete_new_transaction_fault_campaign':False}

def main(phase,h):
 raw=(RUN/'program.json').read_bytes();assert ident(raw)['sha256']==h;p=json.loads(raw);assert p['directory']==str(RUN)
 assert phase in p['phases'] and sys.platform=='linux' and platform.node()=='csis.mn1' and not sys.flags.optimize
 group='initial' if phase=='checks' else 'construct';jobs=json.loads((RUN/('jobs-'+group+'.json')).read_text());assert jobs['registration_sha256']==h and str(jobs['jobs'][phase])==os.environ['SLURM_JOB_ID']
 os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});c=p['phases'][phase]
 resource.setrlimit(resource.RLIMIT_CPU,(c['cpu_seconds'],c['cpu_seconds']+1));resource.setrlimit(resource.RLIMIT_AS,(16*2**30,)*2);resource.setrlimit(resource.RLIMIT_FSIZE,(128*2**20,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 def expire(*a):raise TimeoutError('Registered limit reached')
 signal.signal(signal.SIGALRM,expire);signal.signal(signal.SIGXCPU,expire);signal.alarm(c['wall_seconds']-30)
 out=RUN/phase;out.mkdir(exist_ok=False);save(out/'attempt.json',{'registration_sha256':h,'phase':phase,'job_id':os.environ['SLURM_JOB_ID']});start=time.monotonic()
 r={'schema':'matched-sequential-v128','status':'failed','phase':phase,'registration_sha256':h,'job_id':os.environ['SLURM_JOB_ID'],'error':None,'result':None}
 try:
  assert all(os.environ.get(k)=='1' for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'])
  for n,e in p['sources'].items():read({'path':str(RUN/n),**e})
  r['result']=tests(p,out) if phase=='checks' else construct(p,*phase.split('__'),out,h)
  for n,e in p['sources'].items():read({'path':str(RUN/n),**e})
  r['status']='complete'
 except BaseException as e:
  import traceback;traceback.print_exc();r['error']={'type':type(e).__name__,'message':str(e),'diagnostics':getattr(e,'service_diagnostics',None)}
 finally:
  r.update(process_cpu_seconds=time.process_time(),child_cpu_seconds=sum(resource.getrusage(resource.RUSAGE_CHILDREN)[:2]),elapsed_seconds=time.monotonic()-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,host=platform.node(),python=sys.version)
  r['artifacts']={f.name:ident(f.read_bytes()) for f in out.iterdir() if f.is_file()};save(out/'completion.json',r)
 assert r['status']=='complete',r['error']
if __name__=='__main__':main(*sys.argv[1:])
