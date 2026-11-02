"""Held Slurm submission with exclusive intent and no retry path."""
import json,sys,subprocess,hashlib,os
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def save(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
group,h=sys.argv[1:];assert group=='initial'
b=(root/'program.json').read_bytes();assert hashlib.sha256(b).hexdigest()==h;p=json.loads(b);assert p['directory']==str(root)
phases=list(p['controls'])
for name,job in p['producer_jobs'].items():
 q=subprocess.check_output(['sacct','-X','-j',str(job),'-n','-P','--format=State,ExitCode'],text=True).strip();assert q=='FAILED|1:0',q
save(root/('submit-'+group+'-intent.json'),{'registration_sha256':h,'phases':phases,'automatic_retry':False})
result={'registration_sha256':h,'jobs':{},'status':'submitting'}
try:
 for phase in phases:
  c=p['phases'][phase]
  args=['sbatch','--parsable','--hold','--no-requeue','--partition=cpu-short','--qos=cpu-short','--nodelist=csis.mn1','--cpus-per-task=1','--mem=16G','--time='+str((c['wall_seconds']+59)//60),'--job-name=second133-'+phase,'--output='+str(root/(phase+'.out')),'--error='+str(root/(phase+'.err')),str(root/'research_v133/run.sbatch'),phase,h]
  z=subprocess.run(args,capture_output=True,text=True,check=True);job=z.stdout.strip();assert job.isdigit(),job
  result['jobs'][phase]=int(job);save(root/('submitted-'+phase+'.json'),{'job_id':int(job),'args':args,'stdout':z.stdout,'stderr':z.stderr})
 result['status']='bound_held';save(root/('jobs-'+group+'.json'),result)
 for phase,job in result['jobs'].items():subprocess.run(['scontrol','release',str(job)],check=True)
 result['status']='released';save(root/('released-'+group+'.json'),result)
 print(json.dumps(result))
except BaseException:
 save(root/('submission-failure-'+group+'.json'),result)
 raise
