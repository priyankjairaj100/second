from pathlib import Path
import subprocess,json,tarfile,io,hashlib
r=Path('/Users/priyankjairaj/Downloads/ACL/Second');pil=r/'pilots/sequential-output-audit-v133-20261029';p=json.loads((pil/'program.json').read_bytes());h=hashlib.sha256((pil/'program.json').read_bytes()).hexdigest();w=Path(__file__).parent/'sequential-output-audit-v133';out=w/'collected';out.mkdir(exist_ok=False)
code='''import pathlib,sys,tarfile,json,subprocess
r=pathlib.Path(%r);p=json.loads((r/'program.json').read_text());j=json.loads((r/'jobs-initial.json').read_text())
q=subprocess.check_output(['sacct','-j',','.join(map(str,j['jobs'].values())),'-P','--format=JobIDRaw,State,ExitCode,TotalCPU,ElapsedRaw,MaxRSS'],text=True)
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as t:
 import io
 b=q.encode();a=tarfile.TarInfo('sacct.txt');a.size=len(b);t.addfile(a,io.BytesIO(b))
 for n in p['controls']:
  for f in (r/n).iterdir():t.add(f,arcname=n+'/'+f.name,recursive=False)
  for ext in ['out','err']:t.add(r/(n+'.'+ext),arcname=n+'.'+ext,recursive=False)
 for n in ['jobs-initial.json','released-initial.json']:t.add(r/n,arcname=n,recursive=False)
 # Preserve original failure logs/reports/stage files, without copying model weights.
 old=pathlib.Path(p['producer']['path']).parent
 for n in p['controls']:
  for f in (old/n).glob('*.json'):t.add(f,arcname='producer/'+n+'/'+f.name,recursive=False)
  for ext in ['out','err']:t.add(old/(n+'.'+ext),arcname='producer/'+n+'.'+ext,recursive=False)
'''%p['directory']
z=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','csis',"/nfs_home/software/envs/pytorch-12.8/bin/python3.10 - <<'PY'\n"+code+'\nPY'],capture_output=True,check=True);(w/'actual.tar').write_bytes(z.stdout)
with tarfile.open(fileobj=io.BytesIO(z.stdout)) as t:
 for m in t.getmembers():assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
 t.extractall(out,filter='data')
j=json.loads((out/'jobs-initial.json').read_text());a={v.split('|')[0]:v.split('|') for v in (out/'sacct.txt').read_text().splitlines()[1:]};summary={}
for n in p['controls']:
 c=json.loads((out/n/'completion.json').read_text());assert c['status']=='complete' and c['error'] is None and c['registration_sha256']==h and str(j['jobs'][n])==c['job_id'];assert a[c['job_id']][1:3]==['COMPLETED','0:0'];assert c['result']['producer_state']=='FAILED' and c['result']['model']=={k:p['controls'][n]['files']['model.bin'][k] for k in ('bytes','sha256')}
 for f in (out/'producer'/n).glob('*.json'):
  e=p['controls'][n]['files'][f.name];b=f.read_bytes();assert len(b)==e['bytes'] and hashlib.sha256(b).hexdigest()==e['sha256']
 summary[n]=dict(job=c['job_id'],result=c['result'],process_cpu_seconds=c['process_cpu_seconds'],scheduler=a[c['job_id']])
import shutil
shutil.copytree(out,pil/'actual')
(pil/'actual-audit.json').write_text(json.dumps(dict(schema='sequential-closure-v133',status='verified',registration_sha256=h,models=summary),indent=2)+'\n');print('V133 actual closure verified for',len(summary),'models')
