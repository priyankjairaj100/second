"""Qualified evaluation of completed sequential/GPTQ controls on V124 articles."""
import os,sys,json,math,time,resource,signal,platform,gc
from pathlib import Path
RUN=Path(__file__).resolve().parents[1];sys.path.insert(0,str(RUN))
from research_v124.worker import read,save,ident,unroll,audit_parameters
from research_v125.worker import context

def load_control(p,name,base,reference):
 import numpy as np
 x=p['controls'][name];c=json.loads(read(x['completion']));assert c['status']=='complete' and c['registration_sha256']==x['registration_sha256'] and c['result']['complete_model']
 result=c['result'];assert result['profile']==x['profile'] and result['role']=='candidate_'+str(x['retained']) and len(result['retained_ids'])==x['retained']
 endpoint=p['profiles'][x['profile']]['endpoints']['candidate_'+str(x['retained'])];original=json.loads(read(endpoint['completion']))
 assert result['retained_ids']==original['request']['retained_ids']
 if x['kind']=='sequential':
  blob=read(x['model']);assert result['model']==ident(blob) and c['artifacts']['model.bin']==ident(blob)
  arrays=unroll(blob,base['stages']);assert result['first_stage_equal']
  first=base['stages'][0];n=math.prod(first['shape'])//2;assert blob[:n]==read(endpoint['model'])[:n]
 else:
  manifest=json.loads(read(x['model']));assert result['model']==ident(read(x['model']))
  assert manifest['upstream_commit']=='2d65066eeb06a5c9ff5184d8cebdf33662c67faf' and manifest['settings']==p['gptq_settings']
  assert manifest['weights']==result['weights'];arrays={}
  for sid,e in manifest['weights'].items():
   entry=x['weights'][sid];assert entry['sha256']==e['sha256'] and entry['bytes']==e['bytes']
   raw=read(entry)
   import io,hashlib
   a=np.load(io.BytesIO(raw),allow_pickle=False);assert a.dtype==np.dtype('<f4') and list(a.shape)==e['shape'] and np.isfinite(a).all()
   assert hashlib.sha256(a.astype('<f4').tobytes()).hexdigest()==e['word_sha256'];arrays[sid]=a.astype(np.float64)
 assert set(arrays)==set(reference.weights) and all(arrays[k].shape==reference.weights[k].shape for k in arrays)
 return arrays

def evaluate(p,name,out):
 import numpy as np,torch
 from scripts.run_quality_v30 import nll_from_logits
 from research_v46.evaluator import TorchQualityDecoder
 assert np.__version__=='2.2.6' and torch.__version__=='2.10.0+cu128'
 torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True);assert not torch.cuda.is_initialized()
 x=p['controls'][name];reference,base=context(p,x['profile']);words=audit_parameters(reference,p['profiles'][x['profile']]['checkpoint']['model.safetensors']['path'])
 qualified=json.loads(read(p['qualification'][x['profile']]));assert qualified['status']=='complete' and words==qualified['result']['all_parameter_words']
 arrays=load_control(p,name,base,reference);other=TorchQualityDecoder(reference,device='cpu');ta=other.prefix(arrays);checks=[]
 for tokens in [[0,1,2,3],[1]*8,[(i*13+7)%50257 for i in range(128)]]:
  nll=nll_from_logits(reference.logits(tokens,arrays),tokens)
  with torch.inference_mode():nll2=other.nll(tokens,ta)
  delta=abs(nll-nll2)/(len(tokens)-1);assert math.isfinite(delta) and delta<=1e-8;checks.append({'tokens':len(tokens),'mean_nll_difference':delta})
 save(out/'likelihood-checks.json',{'cases':checks,'heldout_evaluation':False});del other,ta;gc.collect()
 data=json.loads(read(p['prepared_data']['completion']));raw=read(p['prepared_data']['records']);assert data['status']=='complete' and data['result']['records']==ident(raw)
 rows=json.loads(raw)['records'];assert len(rows)==320 and len({r['id'] for r in rows})==320 and all(len(r['tokens'])==128 for r in rows)
 losses=[]
 for i,row in enumerate(rows):
  value=nll_from_logits(reference.logits(row['tokens'],arrays),row['tokens']);assert math.isfinite(value) and value>=0
  loss={'id':row['id'],'predictions':127,'sum_nll':value,'mean_nll':value/127};save(out/('loss-%04d.json'%i),loss);losses.append(loss)
  if i%32==31:print(json.dumps({'name':name,'articles_complete':i+1}),flush=True)
 assert not torch.cuda.is_initialized()
 return {'name':name,'profile':x['profile'],'kind':x['kind'],'retained':x['retained'],'records_sha256':ident(raw)['sha256'],'losses':losses,'predictions':40640,'perplexity':math.exp(sum(v['sum_nll'] for v in losses)/40640),'likelihood_checks':checks,'comparative_quality_guard_evaluated':False}

def main(phase,h):
 raw=(RUN/'program.json').read_bytes();assert ident(raw)['sha256']==h;p=json.loads(raw);assert p['directory']==str(RUN)
 assert phase in p['controls'] and sys.platform=='linux' and platform.node()=='csis.mn1' and not sys.flags.optimize
 jobs=json.loads((RUN/'jobs-evaluate.json').read_text());assert jobs['registration_sha256']==h and str(jobs['jobs'][phase])==os.environ['SLURM_JOB_ID']
 os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});c=p['phases'][phase]
 resource.setrlimit(resource.RLIMIT_CPU,(c['cpu_seconds'],c['cpu_seconds']+1));resource.setrlimit(resource.RLIMIT_AS,(16*2**30,)*2);resource.setrlimit(resource.RLIMIT_FSIZE,(128*2**20,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 def expire(*a):raise TimeoutError('Registered limit reached')
 signal.signal(signal.SIGALRM,expire);signal.signal(signal.SIGXCPU,expire);signal.alarm(c['wall_seconds']-30)
 out=RUN/phase;out.mkdir(exist_ok=False);save(out/'attempt.json',{'registration_sha256':h,'phase':phase,'job_id':os.environ['SLURM_JOB_ID']});start=time.monotonic()
 r={'schema':'control-quality-v131','status':'failed','phase':phase,'registration_sha256':h,'job_id':os.environ['SLURM_JOB_ID'],'error':None,'result':None}
 try:
  assert all(os.environ.get(k)=='1' for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'])
  for n,e in p['sources'].items():read({'path':str(RUN/n),**e})
  r['result']=evaluate(p,phase,out)
  for n,e in p['sources'].items():read({'path':str(RUN/n),**e})
  for e in p['bound_inputs']:read(e)
  r['status']='complete'
 except BaseException as e:
  import traceback;traceback.print_exc();r['error']={'type':type(e).__name__,'message':str(e)}
 finally:
  r.update(process_cpu_seconds=time.process_time(),elapsed_seconds=time.monotonic()-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,host=platform.node(),python=sys.version)
  r['artifacts']={f.name:ident(f.read_bytes()) for f in out.iterdir() if f.is_file()};save(out/'completion.json',r)
 assert r['status']=='complete',r['error']
if __name__=='__main__':main(*sys.argv[1:])
