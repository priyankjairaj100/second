"""Held Slurm submission with exclusive intent and no retry path."""
import json,sys,subprocess,hashlib,os
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def save(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
group,h=sys.argv[1:];assert group in ['initial','evaluate']
b=(root/'program.json').read_bytes();assert hashlib.sha256(b).hexdigest()==h;p=json.loads(b)
assert p['directory']==str(root)
phases=['checks_distilgpt2','checks_gpt2'] if group=='initial' else [n for n in p['phases'] if '__' in n]
if group=='evaluate':
 j=json.loads((root/'jobs-initial.json').read_text())
 for phase in ['checks_distilgpt2','checks_gpt2']:
  r=json.loads((root/phase/'completion.json').read_text());assert r['status']=='complete' and r['registration_sha256']==h
  q=subprocess.run(['sacct','-j',str(j['jobs'][phase]),'--noheader','-X','--parsable2','--format=State,ExitCode'],capture_output=True,text=True,check=True)
  assert q.stdout.strip()=='COMPLETED|0:0',q.stdout
save(root/('submit-'+group+'-intent.json'),{'registration_sha256':h,'phases':phases,'automatic_retry':False})
result={'registration_sha256':h,'jobs':{},'status':'submitting'}
try:
 for phase in phases:
  c=p['phases'][phase]
  args=['sbatch','--parsable','--hold','--no-requeue','--partition=cpu-short','--qos=cpu-short','--nodelist=csis.mn1','--cpus-per-task=1','--mem=16G','--time='+str((c['wall_seconds']+59)//60),'--job-name=second125-'+phase,'--output='+str(root/(phase+'.out')),'--error='+str(root/(phase+'.err')),str(root/'research_v125/run.sbatch'),phase,h]
  z=subprocess.run(args,capture_output=True,text=True,check=True);job=z.stdout.strip();assert job.isdigit(),job
  result['jobs'][phase]=int(job);save(root/('submitted-'+phase+'.json'),{'job_id':int(job),'args':args,'stdout':z.stdout,'stderr':z.stderr})
 result['status']='bound_held';save(root/('jobs-'+group+'.json'),result)
 for phase,job in result['jobs'].items():subprocess.run(['scontrol','release',str(job)],check=True)
 result['status']='released';save(root/('released-'+group+'.json'),result)
 print(json.dumps(result))
except BaseException:
 save(root/('submission-failure-'+group+'.json'),result)
 raise
