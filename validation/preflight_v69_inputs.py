"""Read-only file inventory before V69 registration; no numerical imports or inference."""
from pathlib import Path
import hashlib,json,subprocess,datetime
ROOT=Path('/nfs_home/users/poonam/second-20261010');R67=ROOT/'local_runs/disjoint-service-v67-20261016-a';R68=ROOT/'local_runs/quality-data-v68-20261016-a';OBS=ROOT/'local_runs/cuda-runtime-v69-20261018-a'
def read(p):return json.loads(Path(p).read_bytes())
def bind(p):
 p=Path(p);assert p.is_absolute() and p.is_file();a=p.stat();h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 z=p.stat();assert (a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_ino,z.st_size,z.st_mtime_ns)
 return dict(path=str(p),bytes=a.st_size,sha256=h.hexdigest())
def cmd(a):return subprocess.check_output(a,cwd=ROOT,text=True,timeout=30).strip()
p67=read(R67/'program.json');p68=read(R68/'registration.json')
assert cmd(['git','rev-parse','HEAD'])=='f900999fcb200509dfad4fc081ce9c87fd172a16' and not cmd(['git','status','--porcelain'])
service={k:p68['inputs'][k] for k in ['v67_primary','v67_supplemental','v67_primary_entry','v67_supplemental_entry','v67_program']}
service['root_records']=p67['inputs']['data_records']
for i,n in enumerate([12,6],1):service['completion_'+str(n)]=bind(R67/f'compressed-{i}/outputs/completion.json')
quality={k:bind(R68/(k+'.json')) for k in ['checks','data','audit','registration']}
for k,n in dict(selection='selection.json',records='records.json',inventory='candidate-inventory.json',before='exclusions-before.json',after='exclusions-after.json',acquisition='acquisition.json').items():quality[k]=bind(R68/'outputs'/n)
# The scheduler snapshot is returned; the caller saves and binds exact bytes prospectively.
scheduler=cmd(['sacct','-n','-P','-j','15390,15391,15392','--format=JobIDRaw,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS'])
inputs=dict(service=service,candidates={f'candidate_{n}':bind(R67/f'compressed-{i}/outputs/model.bin') for i,n in enumerate([12,6],1)},quality=quality,prefix=bind(R68/'outputs/validation-prefix.gz.part'),checkpoint={Path(p67['inputs'][k]['path']).name:p67['inputs'][k] for k in ['checkpoint_config','checkpoint_weights']},snapshot={k:bind(ROOT/'local_runs/cpu-parameters-v47-20261010-a/outputs'/n) for k,n in [('manifest','manifest.json'),('archive','parameters.npz')]},gpu_registration=bind(ROOT/'local_runs/cuda-parity-v47-20261010-a/program.json'))
# Print target path candidates rather than inventing identities if names differ.
targets={k:v for k,v in p67['inputs'].items() if 'target' in k}
for group in inputs.values():
 for e in ([group] if 'path' in group else group.values()):assert bind(e['path'])==e
receipt=read(OBS/'receipt.json');runtime=read(OBS/'runtime.json');assert receipt['status']=='complete' and receipt['error'] is None and receipt['cuda_initialized'] is False and receipt['job_id']=='15394'
assert hashlib.sha256((OBS/'runtime.json').read_bytes()).hexdigest()==receipt['runtime_sha256']
for e in [runtime['executable'],*[dict(path=n,**e) for x in runtime['packages'].values() for n,e in x.items()]]:assert bind(e['path'])==e
print(json.dumps(dict(schema='v69-pre-registration-input-inventory',captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),inputs=inputs,target_candidates=targets,v68_scheduler=scheduler,cuda_runtime=runtime,cuda_receipt=receipt,observer_scheduler=cmd(['sacct','-n','-P','-j','15394','--format=JobIDRaw,State,ExitCode,ElapsedRaw,TotalCPU,AllocCPUS']),queue=cmd(['squeue','-h','-u','poonam','-o','%i|%j|%T']),partitions={k:cmd(['scontrol','show','partition',n,'-o']) for k,n in [('cpu','cpu-short'),('cuda','gpu-short')]},qos=cmd(['sacctmgr','-n','-P','show','qos','cpu-short','format=Name,MaxWall']),p67_runtime=p67['runtime'],dependencies=p67['dependency_files']),sort_keys=True))
