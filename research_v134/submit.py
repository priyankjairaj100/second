"""One-use held evaluation, gated on every bound constructor's actual closure."""
import json,sys,subprocess,hashlib,os
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def save(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
_,h=sys.argv[1:];b=(root/'program.json').read_bytes();assert hashlib.sha256(b).hexdigest()==h;p=json.loads(b);assert p['directory']==str(root)
for name,x in p['controls'].items():
 f=x['completion'];raw=Path(f['path']).read_bytes();assert len(raw)==f['bytes'] and hashlib.sha256(raw).hexdigest()==f['sha256'];c=json.loads(raw)
 assert c['status']=='complete' and c['registration_sha256']==x['registration_sha256'] and c['result']['complete_model']
 q=subprocess.run(['sacct','-j',c['job_id'],'--noheader','-X','--parsable2','--format=State,ExitCode'],capture_output=True,text=True,check=True);assert q.stdout.strip()=='COMPLETED|0:0',q.stdout
save(root/'submit-evaluate-intent.json',{'registration_sha256':h,'phases':list(p['controls']),'automatic_retry':False})
result={'registration_sha256':h,'jobs':{},'status':'submitting'}
try:
 for phase in p['controls']:
  c=p['phases'][phase];args=['sbatch','--parsable','--hold','--no-requeue','--partition=cpu-short','--qos=cpu-short','--nodelist=csis.mn1','--cpus-per-task=1','--mem=16G','--time='+str((c['wall_seconds']+59)//60),'--job-name=second134-'+phase,'--output='+str(root/(phase+'.out')),'--error='+str(root/(phase+'.err')),str(root/'research_v134/run.sbatch'),phase,h]
  z=subprocess.run(args,capture_output=True,text=True,check=True);job=z.stdout.strip();assert job.isdigit();result['jobs'][phase]=int(job);save(root/('submitted-'+phase+'.json'),{'job_id':int(job),'args':args,'stdout':z.stdout,'stderr':z.stderr})
 result['status']='bound_held';save(root/'jobs-evaluate.json',result)
 for job in result['jobs'].values():subprocess.run(['scontrol','release',str(job)],check=True)
 result['status']='released';save(root/'released-evaluate.json',result);print(json.dumps(result))
except BaseException:
 save(root/'submission-failure.json',result);raise
