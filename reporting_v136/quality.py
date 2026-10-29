from pathlib import Path
import subprocess,json,hashlib,tarfile,io,math,sys
import numpy as np
version=int(sys.argv[1]);r=Path('/Users/priyankjairaj/Downloads/ACL/Second');pil=r/'pilots'/('control-quality-v'+str(version)+'-20261029');p=json.loads((pil/'program.json').read_text());h=hashlib.sha256((pil/'program.json').read_bytes()).hexdigest();w=Path(__file__).parent/('control-quality-v'+str(version));out=w/'collected';out.mkdir(exist_ok=False)
code='''import pathlib,tarfile,sys,json,hashlib
r=pathlib.Path(%r);p=json.loads((r/'program.json').read_text())
for n,e in p['sources'].items():
 b=(r/n).read_bytes();assert len(b)==e['bytes'] and hashlib.sha256(b).hexdigest()==e['sha256']
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as t:
 for n in p['controls']:
  for f in sorted((r/n).iterdir()):
   assert f.is_file() and not f.is_symlink();t.add(f,arcname=n+'/'+f.name,recursive=False)
 for n in ['jobs-evaluate.json','released-evaluate.json']:t.add(r/n,arcname=n,recursive=False)
'''%p['directory']
z=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','csis',"/nfs_home/software/envs/pytorch-12.8/bin/python3.10 - <<'PY'\n"+code+'\nPY'],capture_output=True,check=True);(w/'actual.tar').write_bytes(z.stdout)
with tarfile.open(fileobj=io.BytesIO(z.stdout)) as t:
 for m in t.getmembers():assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
 t.extractall(out,filter='data')
j=json.loads((out/'jobs-evaluate.json').read_text());assert j['registration_sha256']==h
q=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','csis','sacct -j '+','.join(map(str,j['jobs'].values()))+' -P --format=JobIDRaw,State,ExitCode,TotalCPU,ElapsedRaw,MaxRSS'],capture_output=True,text=True,check=True);(out/'sacct.txt').write_text(q.stdout);a={line.split('|')[0]:line.split('|') for line in q.stdout.splitlines()[1:]}
actual={};audit={}
for name,x in p['controls'].items():
 d=out/name;c=json.loads((d/'completion.json').read_text());assert c['status']=='complete' and c['error'] is None and c['registration_sha256']==h and c['job_id']==str(j['jobs'][name]);assert a[c['job_id']][1:3]==['COMPLETED','0:0']
 assert {f.name for f in d.iterdir()}==set(c['artifacts'])|{'completion.json'}
 for n,e in c['artifacts'].items():
  b=(d/n).read_bytes();assert len(b)==e['bytes'] and hashlib.sha256(b).hexdigest()==e['sha256']
 z=c['result'];assert len(z['losses'])==320 and len({v['id'] for v in z['losses']})==320 and z['records_sha256']==p['prepared_data']['records']['sha256']
 assert len(z['likelihood_checks'])==3 and all(v['mean_nll_difference']<=1e-8 for v in z['likelihood_checks'])
 total=0.0
 for i,v in enumerate(z['losses']):
  assert v==json.loads((d/('loss-%04d.json'%i)).read_text()) and v['predictions']==127 and math.isfinite(v['sum_nll']) and v['mean_nll']==v['sum_nll']/127
  total+=v['sum_nll']
 assert abs(math.exp(total/40640)-z['perplexity'])<=2*math.ulp(z['perplexity']);actual[name]=z
 audit[name]={'job':j['jobs'][name],'completion_sha256':hashlib.sha256((d/'completion.json').read_bytes()).hexdigest(),'scheduler':a[c['job_id']],'worker_cpu_seconds':c['process_cpu_seconds'],'peak_rss_kib':c['peak_rss_kib'],'perplexity':z['perplexity']}
prior=json.loads((r/'pilots/matched-quality-v125-20261029/actual-losses.json').read_text());indices=np.random.Generator(np.random.PCG64(124)).integers(0,320,size=(20000,320));comparisons={}
for name,z in actual.items():
 fixed=prior[z['profile']+'__candidate_'+str(z['retained'])];assert [v['id'] for v in fixed]==[v['id'] for v in z['losses']]
 delta=np.array([v['mean_nll'] for v in fixed])-np.array([v['mean_nll'] for v in z['losses']]);boot=delta[indices].mean(axis=1);lo,hi=np.quantile(boot,[.025,.975]);upper=np.quantile(boot,.9875)
 c={'fixed_over_control_perplexity_ratio':math.exp(float(delta.mean())),'paired_95_percentile_ratio':[math.exp(float(lo)),math.exp(float(hi))],'observed_max_article_ratio':math.exp(float(delta.max())),'observed_max_article_id':fixed[int(delta.argmax())]['id']}
 if z['kind']=='sequential':
  c['primary_upper_98_75_percentile_ratio']=math.exp(float(upper));c['primary_guard_pass']=c['fixed_over_control_perplexity_ratio']<=1.05 and c['primary_upper_98_75_percentile_ratio']<=1.05 and c['observed_max_article_ratio']<=1.20
 else:c['primary_quality_guard_evaluated']=False
 comparisons[name]=c
summary={'schema':'control-quality-audit-v'+str(version),'status':'verified','registration_sha256':h,'models':audit,'comparisons':comparisons,'bootstrap_repetitions':20000,'seed':124}
(pil/'actual-audit.json').write_text(json.dumps(summary,indent=2)+'\n');(pil/'actual-losses.json').write_text(json.dumps({n:z['losses'] for n,z in actual.items()},sort_keys=True,separators=(',',':'))+'\n')
import shutil
for name in p['controls']:
 dest=pil/'actual'/name;dest.mkdir(parents=True,exist_ok=True);shutil.copyfile(out/name/'completion.json',dest/'completion.json')
shutil.copyfile(out/'sacct.txt',pil/'actual/sacct.txt');shutil.copyfile(out/'jobs-evaluate.json',pil/'actual/jobs-evaluate.json')
print(json.dumps({'status':'verified','models':{n:z['perplexity'] for n,z in actual.items()},'comparisons':comparisons},indent=2))
