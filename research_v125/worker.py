"""One-use CPU quality worker for saved exact models. No calibration or retry."""
import os,sys,json,hashlib,time,resource,platform,signal,math,gc,struct
from pathlib import Path
RUN=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(RUN))
def enc(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def ident(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def read(e):
 p=Path(e['path']);assert p.is_file() and not p.is_symlink() and p.stat().st_size==e['bytes'];b=p.read_bytes();assert ident(b)=={k:e[k] for k in ['bytes','sha256']};return b
def save(p,v):
 b=enc(v)
 with p.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 return ident(b)
def weight_hash(a):
 h=hashlib.sha256(b'binary64-matrix-little-endian-row-major-v1\0');h.update(enc(list(a.shape)));h.update(b'\0');h.update(a.astype('<f8',copy=False).tobytes());return h.hexdigest()
def unroll(blob,entries):
 import numpy as np
 out={};offset=0
 for e in entries:
  rows,cols=e['shape'];n=rows*cols;assert n%2==0
  b=blob[offset:offset+n//2];assert len(b)==n//2;offset+=n//2
  raw=np.frombuffer(b,dtype=np.uint8);idx=np.empty(n,dtype=np.uint8);idx[0::2]=raw&15;idx[1::2]=raw>>4
  a=(idx.reshape(rows,cols).astype(np.float64)-8)*np.asarray([float.fromhex(s) for s in e['row_scale_hex']])[:,None]
  assert np.isfinite(a).all();out[e['stage_id']]=a
 assert offset==len(blob)
 return out

def audit_parameters(reference,path):
 """Second direct safetensors reader, independent of the project importer."""
 import numpy as np
 with open(path,'rb') as f:
  n=struct.unpack('<Q',f.read(8))[0];assert 2<=n<=2**24;header=json.loads(f.read(n));origin=8+n
  prefix='transformer.' if 'transformer.wte.weight' in header else ''
  mapping={'embeddings':prefix+'wte.weight','positions':prefix+'wpe.weight','head':('lm_head.weight' if 'lm_head.weight' in header else prefix+'wte.weight'),'final_scale':prefix+'ln_f.weight','final_bias':prefix+'ln_f.bias'}
  arrays={name:getattr(reference,name) for name in mapping};arrays['head_bias']=reference.head_bias
  for i,block in enumerate(reference.blocks):
   q=prefix+'h.'+str(i)+'.'
   for dest,src in [('norm1_scale','ln_1.weight'),('norm1_bias','ln_1.bias'),('norm2_scale','ln_2.weight'),('norm2_bias','ln_2.bias'),('qkv_bias','attn.c_attn.bias'),('attn_out_bias','attn.c_proj.bias'),('mlp_up_bias','mlp.c_fc.bias'),('mlp_down_bias','mlp.c_proj.bias')]:
    name='blocks/'+str(i)+'/'+dest;arrays[name]=block[dest];mapping[name]=q+src
   for dest,src in [('qkv','attn.c_attn'),('attn_out','attn.c_proj'),('mlp_up','mlp.c_fc'),('mlp_down','mlp.c_proj')]:
    name='weights/block.%04d.'%i+dest;arrays[name]=reference.weights[name.split('/',1)[1]];mapping[name]=q+src+'.weight'
  checked={}
  for name,a in arrays.items():
   assert a.dtype==np.float64 and np.isfinite(a).all()
   if name=='head_bias':assert np.all(a==0)
   else:
    e=header[mapping[name]];assert e['dtype']=='F32';lo,hi=e['data_offsets'];assert hi-lo==math.prod(e['shape'])*4
    f.seek(origin+lo);b=f.read(hi-lo);assert len(b)==hi-lo
    direct=np.frombuffer(b,dtype='<f4').astype(np.float64).reshape(e['shape'])
    if name.startswith('weights/'):direct=direct.T
    assert a.shape==direct.shape and a.astype('<f8').tobytes()==direct.astype('<f8').tobytes(),name
   checked[name]={'shape':list(a.shape),'sha256':hashlib.sha256(a.astype('<f8').tobytes()).hexdigest()}
 return checked

def context(p,profile):
 import numpy as np
 from src.checkpoint_adapter import load_gpt2_checkpoint
 from scripts.run_quality_v30 import NumpyQualityDecoder
 x=p['profiles'][profile]
 for e in x['checkpoint'].values():read(e)
 from research_v125.runtime import likelihood_manifest_scope
 with likelihood_manifest_scope():
  loaded=load_gpt2_checkpoint(str(Path(x['checkpoint']['config.json']['path']).parent),identity_encoding='binary64_tree_v2')
 assert loaded.provenance['files_sha256']=={n:e['sha256'] for n,e in x['checkpoint'].items()}
 r=NumpyQualityDecoder(loaded.decoder);base=json.loads(read(x['anchor']))
 assert r.config.block_count==x['blocks'] and r.config.model_width==768 and r.config.vocabulary_size==50257
 assert base['recipe']['original_token_count']==512 and base['recipe']['bits']==4
 assert [e['stage_id'] for e in base['stages']]==list(r.weights)
 for e in base['stages']:
  assert list(r.weights[e['stage_id']].shape)==e['shape'] and weight_hash(r.weights[e['stage_id']])==e['weights_sha256']
  assert e['normalization']==[512,1] and e['ridge']==[1,100]
 return r,base

def prefix(p,profile,role,base):
 if role=='original':return None,None
 x=p['profiles'][profile]['endpoints'][role];c=json.loads(read(x['completion']));b=read(x['model'])
 assert c['status']=='complete' and c['complete_model'] and c['base_target_sha256']==p['profiles'][profile]['anchor']['sha256']
 assert c['calibration_target_sha256']==p['profiles'][profile]['calibration']['sha256']
 assert c['artifacts']['model.bin']['sha256']==ident(b)['sha256']
 assert len(c['request']['retained_ids'])==int(role[-1])
 stages=c['request']['timing']['stages'];assert len(stages)==len(base['stages']);offset=0
 for e,s in zip(base['stages'],stages):
  assert e['stage_id']==s['stage_id'];n=math.prod(e['shape'])//2;assert hashlib.sha256(b[offset:offset+n]).hexdigest()==s['code_sha256'];offset+=n
 assert offset==len(b)
 return unroll(b,base['stages']),{'model':x['model'],'completion':x['completion'],'retained_ids':c['request']['retained_ids']}

def qualify(p,profile,out):
 import numpy as np,torch
 import unittest
 from research_v125 import test_worker
 tests=unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromModule(test_worker));assert tests.wasSuccessful() and tests.testsRun==7
 assert np.__version__==p['runtime_versions']['numpy'] and torch.__version__==p['runtime_versions']['torch']
 from scripts.run_quality_v30 import nll_from_logits
 from research_v46.evaluator import TorchQualityDecoder
 from src.compact_state import StageCodes
 torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
 assert not torch.cuda.is_initialized()
 r,base=context(p,profile);words=audit_parameters(r,p['profiles'][profile]['checkpoint']['model.safetensors']['path'])
 t=TorchQualityDecoder(r,device='cpu');results=[]
 cases=[[0,1,2,3],[1]*8,[(i*13+7)%50257 for i in range(128)]]
 for role in ['original','candidate_3','candidate_2']:
  a,binding=prefix(p,profile,role,base);ta=None if a is None else t.prefix(a)
  if a is not None:
   blob=read(p['profiles'][profile]['endpoints'][role]['model']);offset=0
   for e in base['stages']:
    rows,cols=e['shape'];n=rows*cols//2
    s=StageCodes(e['stage_id'],rows,cols,'dyadic_row',4,(),blob[offset:offset+n],tuple(float.fromhex(v) for v in e['row_scale_hex']))
    assert np.array_equal(s.array(),a[e['stage_id']]);offset+=n
   assert offset==len(blob)
  for toks in cases:
   v=nll_from_logits(r.logits(toks,a),toks)
   with torch.inference_mode():other=t.nll(toks,ta)
   delta=abs(v-other)/(len(toks)-1);assert math.isfinite(delta) and delta<=1e-8
   results.append({'role':role,'tokens':len(toks),'mean_nll_difference':delta,'passed':True})
  del a,ta;gc.collect()
 assert not torch.cuda.is_initialized()
 return {'status':'verified','all_parameter_words':words,'cases':results,'heldout_records_evaluated':False,'native_calibration_requalified':False,'torch_cpu':True,'cuda_initialized':False}

def evaluation(p,profile,role,out):
 import numpy as np
 assert np.__version__==p['runtime_versions']['numpy']
 from scripts.run_quality_v30 import nll_from_logits
 data_receipt=json.loads(read(p['prepared_data']['completion']));check=json.loads((RUN/('checks_'+profile)/'completion.json').read_text())
 assert data_receipt['status']==check['status']=='complete' and data_receipt['registration_sha256']==p['prepared_data']['registration_sha256'] and check['registration_sha256']==p['_hash']
 records_raw=read(p['prepared_data']['records']);assert ident(records_raw)==data_receipt['result']['records']
 rows=json.loads(records_raw)['records'];assert len(rows)==320 and len({r['id'] for r in rows})==320 and all(len(r['tokens'])==128 for r in rows)
 r,base=context(p,profile);words=audit_parameters(r,p['profiles'][profile]['checkpoint']['model.safetensors']['path'])
 assert words==check['result']['all_parameter_words']
 a,binding=prefix(p,profile,role,base);results=[]
 for i,row in enumerate(rows):
  value=nll_from_logits(r.logits(row['tokens'],a),row['tokens']);assert math.isfinite(value) and value>=0
  loss={'id':row['id'],'predictions':127,'sum_nll':value,'mean_nll':value/127}
  save(out/('loss-%04d.json'%i),loss);results.append(loss)
  if i%32==31:print(json.dumps({'phase':'quality','profile':profile,'role':role,'articles_complete':i+1}),flush=True)
 return {'profile':profile,'role':role,'binding':binding,'records_sha256':ident(records_raw)['sha256'],'losses':results,'predictions':320*127,'perplexity':math.exp(sum(x['sum_nll'] for x in results)/(320*127)),'comparative_quality_guard_evaluated':False,'control_comparators_pending':True}

def main(phase,h):
 start=time.monotonic();raw=(RUN/'program.json').read_bytes();assert ident(raw)['sha256']==h;p=json.loads(raw);assert p['directory']==str(RUN)
 assert sys.platform=='linux' and os.environ.get('SLURM_JOB_ID','').isdigit() and not sys.flags.optimize
 group='initial' if phase=='data' or phase.startswith('checks_') else 'evaluate'
 jobs=json.loads((RUN/('jobs-'+group+'.json')).read_text());assert jobs['registration_sha256']==h and str(jobs['jobs'][phase])==os.environ['SLURM_JOB_ID']
 cap=p['phases'][phase];os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
 resource.setrlimit(resource.RLIMIT_CPU,(cap['cpu_seconds'],cap['cpu_seconds']+1));resource.setrlimit(resource.RLIMIT_AS,(16*2**30,)*2);resource.setrlimit(resource.RLIMIT_FSIZE,(128*2**20,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 def expire(*a):raise TimeoutError('Registered wall/CPU cap reached')
 signal.signal(signal.SIGXCPU,expire);signal.signal(signal.SIGALRM,expire);signal.alarm(cap['wall_seconds']-30)
 out=RUN/phase;out.mkdir(exist_ok=False)
 save(out/'attempt.json',{'registration_sha256':h,'phase':phase,'job_id':os.environ['SLURM_JOB_ID']})
 report={'schema':'matched-quality-v125','phase':phase,'job_id':os.environ['SLURM_JOB_ID'],'registration_sha256':h,'status':'failed','error':None,'result':None}
 try:
  for name,e in p['sources'].items():read({'path':str(RUN/name),**e})
  assert platform.node()=='csis.mn1'
  assert all(os.environ.get(n)=='1' for n in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'])
  if phase.startswith('checks_'):report['result']=qualify(p,phase[len('checks_'):],out)
  else:
   profile,role=phase.split('__');p['_hash']=h;report['result']=evaluation(p,profile,role,out)
  for name,e in p['sources'].items():read({'path':str(RUN/name),**e})
  report['status']='complete'
 except BaseException as e:
  report['error']={'type':type(e).__name__,'message':str(e)}
  import traceback;traceback.print_exc()
 finally:
  from research_v125.runtime import manifest
  report['likelihood_runtime_manifest']=manifest()
  report.update(elapsed_seconds=time.monotonic()-start,process_cpu_seconds=time.process_time(),peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,host=platform.node(),runtime={'python':sys.version,'numpy':getattr(sys.modules.get('numpy'),'__version__',None),'torch':getattr(sys.modules.get('torch'),'__version__',None)},affinity=sorted(os.sched_getaffinity(0)))
  report['artifacts']={f.name:ident(f.read_bytes()) for f in out.iterdir() if f.is_file()}
  save(out/'completion.json',report)
 assert report['status']=='complete',report['error']
if __name__=='__main__':main(*sys.argv[1:])
