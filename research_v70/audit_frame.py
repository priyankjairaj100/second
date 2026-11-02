"""One-use saved-frame audit under a separate immutable registration."""
import sys,os,platform,resource,signal,time,json,hashlib
from pathlib import Path
ROOT=Path('/nfs_home/users/poonam/second-20261010');RUN=ROOT/'local_runs/quality-frame-audit-v70-20261018-a'
def canonical(o):return json.dumps(o,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def info(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def save(n,o):
 with (RUN/n).open('xb') as f:f.write(canonical(o));f.flush();os.fsync(f.fileno())
def read(e):
 p=Path(e['path']);assert p.is_file() and not p.is_symlink();b=p.read_bytes();assert info(b)=={k:e[k] for k in ['bytes','sha256']};return b
def main(h):
 tick=time.perf_counter_ns();b=(RUN/'program.json').read_bytes();p=json.loads(b)
 assert canonical(p)==b and info(b)['sha256']==h and p['directory']==str(RUN)
 assert sys.platform=='linux' and platform.node()=='csis.mn1' and sys.dont_write_bytecode and sys.flags.optimize==0 and os.environ.get('SLURM_JOB_ID','').isdigit()
 assert Path(__file__).resolve()==RUN/'research_v70/audit_frame.py'
 os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
 def expired(*a):raise TimeoutError('Frame audit cap reached')
 signal.signal(signal.SIGXCPU,expired);signal.signal(signal.SIGALRM,expired);signal.alarm(900)
 for k,v in [(resource.RLIMIT_CPU,(600,601)),(resource.RLIMIT_AS,(4*2**30,)*2),(resource.RLIMIT_FSIZE,(128*2**20,)*2),(resource.RLIMIT_CORE,(0,0))]:resource.setrlimit(k,v)
 save('attempt.json',dict(job_id=os.environ['SLURM_JOB_ID'],registration_sha256=h,affinity_cpus=sorted(os.sched_getaffinity(0))))
 r=dict(schema='complete-frame-exclusion-audit-v70',status='failed',error=None,registration_sha256=h,job_id=os.environ['SLURM_JOB_ID'],model_inference=False,new_data_acquired=False,result=None)
 try:
  for group in ['frozen_sources','new_sources','dependencies']:
   for n,e in p[group].items():read(dict(path=n,**e))
  names=['quality-data-v68-20261016-a','disjoint-service-v67-20261016-a','complete-service-checks-v66-20261016-a','disjoint-data-v65-20261016-a','modern-service-checks-v64-20261016-a','lossless-control-v63-20261016-a']
  sys.path[:0]=[str(ROOT/'local_runs/lossless-control-v63-20261016-a/deps'),*[str(ROOT/'local_runs'/n) for n in names],str(ROOT)]
  from research_v61.campaign import runtime
  assert runtime()==p['runtime']
  from research_v68 import quality_data as data
  from tokenizers import Tokenizer
  import tokenizers
  assert tokenizers.__version__=='0.23.2'
  inputs={k:read(e) for k,e in p['inputs'].items()}
  tok=Tokenizer.from_file(p['inputs']['tokenizer']['path']);assert tok.get_vocab_size()==50257
  before=json.loads(inputs['before']);protected=data.exclusions_from(before,[])
  directory=Path(p['inputs']['prefix']['path']).parent
  audit=data.audit_saved(directory,tok,protected)
  items,frame=data.decode_frame(inputs['prefix']);records=[data.row(i,item,tok) for i,item in enumerate(items)]
  full=[dict(id=x['id'],token_count=len(x['tokens']),tokens_sha256=info(canonical(x['tokens']))['sha256']) for x in records]
  inv=json.loads(inputs['inventory']);after=json.loads(inputs['after']);expected={k:set(v) for k,v in before.items()}
  assert [x['id'] for x in full]==[x['id'] for x in inv['candidates']]
  for row,f in zip(inv['candidates'],full):
   assert f['token_count']==min(128,row['available_tokens'])
   expected['ids'].add(row['id']);expected['content'].update(row[k] for k in ['body_sha256','normalized_text_sha256','url_sha256']);expected['chunks'].update(row['token_prefixes'].values())
   if f['token_count']:expected['chunks'].add(f['tokens_sha256'])
  assert after=={k:sorted(v) for k,v in expected.items()}
  for k,e in p['inputs'].items():assert read(e)==inputs[k]
  for group in ['frozen_sources','new_sources','dependencies']:
   for n,e in p[group].items():read(dict(path=n,**e))
  r.update(status='complete',result=dict(status='verified',saved_data_audit=audit,inputs={k:info(v) for k,v in inputs.items()},complete_token_hashes=full,full_frame_articles=len(full),short_records=sum(x['token_count']<128 for x in full),actual_exact_exclusion_union=True,retokenized_saved_prefix=True))
 except BaseException as e:r['error']=dict(type=type(e).__name__,message=str(e))
 child=resource.getrusage(resource.RUSAGE_CHILDREN);r.update(process_cpu_ns=time.process_time_ns(),waited_child_cpu_ns=round((child.ru_utime+child.ru_stime)*1e9),elapsed_ns=time.perf_counter_ns()-tick,max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
 save('receipt.json',r);assert r['status']=='complete',r['error']
if __name__=='__main__':main(*sys.argv[1:])
