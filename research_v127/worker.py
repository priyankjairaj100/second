"""Separately registered matched sequential controls; no old launcher is called."""
import os,sys,json,time,resource,signal,platform,math,hashlib,gc
from pathlib import Path
RUN=Path(__file__).resolve().parents[1];sys.path.insert(0,str(RUN))
from research_v124.worker import enc,ident,read,save

def main(phase,h):
 raw=(RUN/'program.json').read_bytes();assert ident(raw)['sha256']==h;p=json.loads(raw);assert p['directory']==str(RUN)
 assert phase in p['phases'] and sys.platform=='linux' and platform.node()=='csis.mn1' and not sys.flags.optimize
 group='initial' if phase=='checks' else 'construct';jobs=json.loads((RUN/('jobs-'+group+'.json')).read_text());assert jobs['registration_sha256']==h and str(jobs['jobs'][phase])==os.environ['SLURM_JOB_ID']
 os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});c=p['phases'][phase]
 resource.setrlimit(resource.RLIMIT_CPU,(c['cpu_seconds'],c['cpu_seconds']+1));resource.setrlimit(resource.RLIMIT_AS,(16*2**30,)*2);resource.setrlimit(resource.RLIMIT_FSIZE,(128*2**20,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 def expire(*a):raise TimeoutError('Registered limit reached')
 signal.signal(signal.SIGALRM,expire);signal.signal(signal.SIGXCPU,expire);signal.alarm(c['wall_seconds']-30)
 out=RUN/phase;out.mkdir(exist_ok=False);save(out/'attempt.json',{'registration_sha256':h,'phase':phase,'job_id':os.environ['SLURM_JOB_ID']});start=time.monotonic()
 r={'schema':'practical-gptq-v127','status':'failed','phase':phase,'registration_sha256':h,'job_id':os.environ['SLURM_JOB_ID'],'error':None,'result':None}
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


def setup():
 import torch
 torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
 assert torch.__version__=='2.10.0+cu128' and not torch.cuda.is_initialized()
 return torch

def tests(p,out):
 import unittest,numpy as np
 from research_v127 import test_practical
 from research_v127.practical import Float32Decoder,consume_original
 from research_v125.worker import context,audit_parameters
 torch=setup();assert np.__version__=='2.2.6'
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_practical));assert r.wasSuccessful() and r.testsRun==4 and not r.skipped
 results=[]
 for profile in ['distilgpt2','gpt2']:
  reference,base=context(p,profile);audit_parameters(reference,p['profiles'][profile]['checkpoint']['model.safetensors']['path']);d=Float32Decoder(reference,device='cpu')
  for tokens in [[0,1,2,3],[(i*13+7)%50257 for i in range(128)]]:
   with torch.inference_mode():actual,seen=consume_original(d,tokens);expected=d.logits(tokens)
   assert seen==list(reference.weights) and torch.equal(actual,expected)
   results.append({'profile':profile,'tokens':len(tokens),'stages':len(seen),'all_logits_word_equal':True})
  del d,reference,base;gc.collect()
 assert not torch.cuda.is_initialized()
 import transformers
 return {'tests':4,'actual_checkpoint_stream_checks':results,'transformers_version':transformers.__version__,'cuda_initialized':False,'heldout_evaluation':False}

def construct(p,profile,role,out,h):
 import numpy as np
 from research_v125.worker import context,audit_parameters
 from research_v126.worker import retained
 from research_v127.practical import Float32Decoder,features,quantize_matrix
 torch=setup();assert np.__version__=='2.2.6'
 ck=json.loads((RUN/'checks/completion.json').read_text());assert ck['status']=='complete' and ck['registration_sha256']==h
 x=p['profiles'][profile];end=x['endpoints'][role];receipt=json.loads(read(end['completion']))
 assert receipt['status']=='complete' and receipt['complete_model'] and receipt['base_target_sha256']==x['anchor']['sha256'] and receipt['calibration_target_sha256']==x['calibration']['sha256']
 root=json.loads(read(p['calibration_records'][profile]))['records'];rows=retained(root,receipt['request']['retained_ids']);assert len(rows)==int(role[-1])
 ref,base=context(p,profile);audit_parameters(ref,x['checkpoint']['model.safetensors']['path']);d=Float32Decoder(ref,device='cpu')
 streams=[features(d,row['tokens']) for row in rows];previous=None;artifacts={};quantizers={};history=[]
 try:
  with torch.inference_mode():
   for index,(sid,w) in enumerate(d.weights.items()):
    batches=[]
    for stream in streams:
     actual,values=next(stream) if index==0 else stream.send(previous)
     assert actual==sid and values.shape==(128,w.shape[1]) and values.dtype==torch.float32 and torch.isfinite(values).all()
     batches.append(values)
    q,meta=quantize_matrix(w,batches);previous=q
    name='weight-%03d.npy'%index
    with (out/name).open('xb') as f:np.save(f,q.numpy().astype('<f4'),allow_pickle=False)
    check=np.load(out/name,allow_pickle=False);assert check.dtype==np.dtype('<f4') and np.array_equal(check,q.numpy())
    artifacts[sid]={'file':name,**ident((out/name).read_bytes()),'shape':list(q.shape),'word_sha256':meta['grid_words_sha256']};quantizers[sid]=meta
    event={'stage_id':sid,'index':index,'inputs':len(batches),'tokens':128*len(batches),'calibration':'all preceding quantized stages','dtype':'float32','quantizer':meta};save(out/('stage-%03d.json'%index),event);history.append(sid)
    print(json.dumps({'phase':'gptq','profile':profile,'role':role,'stages_complete':index+1}),flush=True)
    del batches,check;gc.collect()
 finally:
  for stream in streams:stream.close()
 assert history==list(ref.weights) and len(history)==x['blocks']*4 and not torch.cuda.is_initialized()
 for e in [end['completion'],x['anchor'],x['calibration'],p['calibration_records'][profile],*x['checkpoint'].values()]:read(e)
 save(out/'model.json',{'weights':artifacts,'quantizers':quantizers,'upstream_commit':p['gptq_commit'],'settings':p['gptq_settings']})
 return {'profile':profile,'role':role,'complete_model':True,'retained_ids':[r['id'] for r in rows],'model':ident((out/'model.json').read_bytes()),'weights':artifacts,'stages':len(history),'quality_evaluation':False,'cuda_initialized':False,'same_target_oracle':False}
if __name__=='__main__':main(*sys.argv[1:])
