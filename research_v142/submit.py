"""Exclusive held submissions; predecessor dependencies never bypassed."""
import json,sys,subprocess,hashlib,os
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def save(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
group,h=sys.argv[1:];assert group in ['initial','prepare','measure','audit']
b=(root/'program.json').read_bytes();assert hashlib.sha256(b).hexdigest()==h;p=json.loads(b)
assert p['directory']==str(root)
phases=[n for n in p['phase_order'] if p['phases'][n]['group']==group]
assert phases
prior=[]
if group=='prepare':prior=['checks']
if group=='measure':prior=[n for n in p['phase_order'] if p['phases'][n]['group']=='prepare']
if group=='audit':prior=[n for n in p['phase_order'] if p['phases'][n]['group']!='audit']
terminal={}
for phase in prior:
 r=json.loads((root/phase/'completion.json').read_bytes());assert r['status']=='complete' and r['registration_sha256']==h
 q=subprocess.run(['sacct','-j',str(r['job_id']),'-n','-X','-P','--format=State,ExitCode'],capture_output=True,text=True,check=True);assert q.stdout.strip()=='COMPLETED|0:0',q.stdout;terminal[phase]=q.stdout
save(root/('submit-'+group+'-intent.json'),{'registration_sha256':h,'phases':phases,'automatic_retry':False,'prior_terminal':terminal})
result={'registration_sha256':h,'jobs':{},'status':'submitting'}
try:
 for phase in phases:
  c=p['phases'][phase]
  args=['sbatch','--parsable','--hold','--no-requeue','--kill-on-invalid-dep=yes','--partition=cpu-short','--qos=cpu-short','--nodelist=csis.mn1','--cpus-per-task=1','--mem=16G','--time='+str((c['wall_seconds']+59)//60),'--job-name=second142-'+phase,'--output='+str(root/(phase+'.out')),'--error='+str(root/(phase+'.err'))]
  args.append('--dependency=afterany:'+':'.join(str(v) for v in p['producer_jobs'].values()))
  parent=c.get('predecessor')
  if parent in result['jobs']:args.append('--dependency=afterok:'+str(result['jobs'][parent]))
  args.extend([str(root/'research_v142/run.sbatch'),phase,h])
  z=subprocess.run(args,capture_output=True,text=True,check=True);job=z.stdout.strip();assert job.isdigit(),job
  result['jobs'][phase]=int(job);save(root/('submitted-'+phase+'.json'),{'job_id':int(job),'args':args,'stdout':z.stdout,'stderr':z.stderr})
 result['status']='bound_held';save(root/('jobs-'+group+'.json'),result)
 for phase,job in result['jobs'].items():subprocess.run(['scontrol','release',str(job)],check=True)
 result['status']='released';save(root/('released-'+group+'.json'),result);print(json.dumps(result))
except BaseException:
 save(root/('submission-failure-'+group+'.json'),result);raise
