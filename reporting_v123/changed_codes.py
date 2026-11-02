"""Read-only posthoc packed-code audit. No model construction or inference."""
from pathlib import Path
import json,hashlib,os,sys,time,resource,datetime,random

def sha(b):return hashlib.sha256(b).hexdigest()
def count(a,b):
 assert len(a)==len(b)
 if not a:return 0
 x=int.from_bytes(a,'little')^int.from_bytes(b,'little')
 m=int.from_bytes(b'\x11'*len(a),'little')
 return bin((x|(x>>1)|(x>>2)|(x>>3))&m).count('1')
def self_test():
 for a in range(256):
  for b in range(256):assert count(bytes([a]),bytes([b]))==int((a&15)!=(b&15))+int((a>>4)!=(b>>4))
 r=random.Random(123)
 for n in [0,1,2,31,128,1024]:
  a=bytes(r.randrange(256) for _ in range(n));b=bytes(r.randrange(256) for _ in range(n))
  assert count(a,b)==sum((x&15)!=(y&15) for x,y in zip(a,b))+sum((x>>4)!=(y>>4) for x,y in zip(a,b))
 return {'byte_pairs':65536,'packed_vectors':6,'failures':0}
if __name__=='__main__':
 if sys.argv[1:] == ['--self-test']:print(json.dumps(self_test()));sys.exit(0)
 assert len(sys.argv)==3 and os.environ.get('SLURM_JOB_ID')
 folder=Path(__file__).resolve().parent;mb=(folder/'manifest.json').read_bytes();assert sha(mb)==sys.argv[1]
 manifest=json.loads(mb);assert sha(Path(__file__).read_bytes())==manifest['script_sha256']
 assert sys.argv[2]==str(folder/'result.json') and not (folder/'result.json').exists()
 resource.setrlimit(resource.RLIMIT_CPU,(300,301));resource.setrlimit(resource.RLIMIT_AS,(16*2**30,16*2**30))
 start=time.perf_counter();cpu=time.process_time()
 out={'schema':'saved-model-changes-v123','status':'running','manifest_sha256':sha(mb),'job_id':os.environ['SLURM_JOB_ID'],'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'new_calibration_or_inference':False,'self_test':self_test(),'models':[],'error':None}
 def read(e):
  p=Path(e['path']);assert p.is_file() and not p.is_symlink();b=p.read_bytes();assert len(b)==e['bytes'] and sha(b)==e['sha256'];return b
 try:
  for profile in manifest['profiles']:
   prep=json.loads(read(profile['preparation']));assert prep['status']=='complete'
   expected=prep['artifacts']['model.bin'];root_entry={'path':str(Path(profile['preparation']['path']).parent/'model.bin'),'bytes':expected['bytes'],'sha256':expected['sha256']}
   root=read(root_entry);prior=root
   for endpoint in profile['endpoints']:
    c=json.loads(read(endpoint['completion']));blob=read(endpoint['model']);assert c['status']=='complete' and c['complete_model'] is True
    assert c['base_target_sha256']==prep['base_target_sha256'] and c['calibration_target_sha256']==prep['calibration_target_sha256']
    assert {k:c['artifacts']['model.bin'][k] for k in ['bytes','sha256']}=={k:endpoint['model'][k] for k in ['bytes','sha256']}
    stages=c['request']['timing']['stages'];offset=0;rows=[]
    for s in stages:
     a=s['admission'];n=a['rows']*a['width'];assert n%2==0;size=n//2
     old=prior[offset:offset+size];new=blob[offset:offset+size];base=root[offset:offset+size]
     assert len(new)==size and isinstance(s['fallback'],bool)
     rows.append({'stage_id':s['stage_id'],'code_count':n,'changed_from_predecessor':count(old,new),'changed_from_root':count(base,new),'source_replay_at_stage':s['fallback']})
     offset+=size
    assert offset==len(blob)==len(prior)==len(root)
    allcodes=sum(x['code_count'] for x in rows);changed=sum(x['changed_from_predecessor'] for x in rows)
    out['models'].append({'profile':profile['profile'],'step':endpoint['step'],'retained_records':len(c['request']['retained_ids']),'code_count':allcodes,'changed_from_predecessor':changed,'changed_fraction':changed/allcodes,'changed_from_root':sum(x['changed_from_root'] for x in rows),'changed_in_nonreplayed_stages':sum(x['changed_from_predecessor'] for x in rows if not x['source_replay_at_stage']),'changed_in_replayed_stages':sum(x['changed_from_predecessor'] for x in rows if x['source_replay_at_stage']),'root_model':root_entry,'model':endpoint['model'],'completion':endpoint['completion'],'stages':rows})
    prior=blob
  out['status']='complete'
 except BaseException as e:
  out['status']='failed';out['error']={'type':type(e).__name__,'message':str(e)};raise
 finally:
  out.update(elapsed_seconds=time.perf_counter()-start,process_cpu_seconds=time.process_time()-cpu,max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,runtime_python=sys.version,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Posthoc counts of saved output codes, not new calibration, quality, precision-success or independent-root evidence. Replay classification applies to whole stages; no claim that every changed code in a replayed stage required replay.')
  with (folder/'result.json').open('x') as f:json.dump(out,f,indent=2);f.write('\n')
