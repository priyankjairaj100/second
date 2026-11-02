from pathlib import Path
import json,hashlib,tarfile,io,datetime,sys
R=Path('/Users/priyankjairaj/Downloads/ACL/Second');W=Path('/Users/priyankjairaj/Documents/Codex/2026-10-10/see-i-am-working-on-a-2/work');sys.path.insert(0,str(R))
from research_v136.preflight import validate
D=W/'minimal-cold-v138';s=json.loads((D/'input-snapshot.json').read_bytes());old=json.loads((R/'pilots/matched-sequential-v132-20261029/program.json').read_bytes())
def ident(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
phases={'checks':dict(group='initial',role='checks',cpu_seconds=300,wall_seconds=600)}
for profile in ['distilgpt2','gpt2']:
 phases[profile+'__prepare']=dict(group='prepare',profile=profile,role='prepare',count=4,cpu_seconds=5000,wall_seconds=6300)
 for mode in ['tokens','references']:
  for count in [3,2]:
   phases[profile+'__'+mode+str(count)]=dict(group='measure',profile=profile,role='request',mode=mode,count=count,predecessor=profile+('__prepare' if count==3 else '__'+mode+'3'),cpu_seconds=3600,wall_seconds=4500)
 for count in [3,2]:phases[profile+'__oracle'+str(count)]=dict(group='measure',profile=profile,role='oracle',count=count,cpu_seconds=3600,wall_seconds=4500)
phases['audit']=dict(group='audit',role='audit',cpu_seconds=300,wall_seconds=600)
files={}
for n,e in old['sources'].items():
 b=(R/n).read_bytes();assert ident(b)==e,n;files[n]=b
for directory in ['research_v135','research_v138']:
 for f in (R/directory).glob('*'):
  if f.is_file():files[str(f.relative_to(R))]=f.read_bytes()
f=R/'research_v136/preflight.py';files[str(f.relative_to(R))]=f.read_bytes()
inputs=list(s['inputs'])
for x in old['profiles'].values():
 inputs+=list(x['checkpoint'].values())+[x['anchor'],x['calibration']]
 for e in x['endpoints'].values():inputs += [e['completion'],e['model']]
for v in s['root_models'].values():inputs += [v['completion'],v['model']]
validate(inputs)
p=dict(schema='minimal-source-only-v138',directory='/nfs_home/users/poonam/second-20261010/local_runs/minimal-source-only-v138-20261030-a',registered_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),threads=1,memory_bytes=16*2**30,storage_reserve_bytes=4*2**30,automatic_retry=False,profiles=old['profiles'],root_provenance=s['provenance'],root_ids=s['ids'],root_records_sha256=s['records_sha256'],source_inputs=s['inputs'],root_models={k:{n:v[n] for n in ['completion','model']} for k,v in s['root_models'].items()},bound_inputs=inputs,sources={n:ident(b) for n,b in files.items()},phases=phases,phase_order=list(phases),total_cpu_ceiling=sum(x['cpu_seconds'] for x in phases.values())+60*len(phases),software_tests=335,quality_qualified=['distilgpt2__retained3','distilgpt2__retained2','gpt2__retained2'],quality_failure_boundary='gpt2__retained3',historical_comparison='same_target_codes_only; no paired timing claim',preserved_solver_policy=dict(max_process_bytes=16*2**30,max_array_bytes=8*2**30,max_refinement_coordinates=16,max_stage_work_units=64000000000,max_request_work_units=1000000000000,exact_rational_caps=0),source_availability_probe='resolution_without_neural_evaluation')
assert len(phases)==16 and p['total_cpu_ceiling']==54760
from research_v138.worker import bindings
bindings(p)
raw=json.dumps(p,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
pil=R/'pilots/minimal-source-only-v138-20261030';pil.mkdir(exist_ok=False);(pil/'program.json').write_bytes(raw);(pil/'input-snapshot.json').write_bytes((D/'input-snapshot.json').read_bytes())
archive=D/'source-v138.tar.gz'
with tarfile.open(archive,'x:gz') as t:
 for n,b in [*sorted(files.items()),('program.json',raw)]:
  z=tarfile.TarInfo(n);z.size=len(b);z.mode=0o644;z.mtime=0;t.addfile(z,io.BytesIO(b))
package=dict(archive=dict(path=str(archive),**ident(archive.read_bytes())),registration_sha256=ident(raw)['sha256'],namespace=p['directory'],sources=len(files));(pil/'package.json').write_text(json.dumps(package,indent=2)+'\n');print(json.dumps(package,indent=2))
