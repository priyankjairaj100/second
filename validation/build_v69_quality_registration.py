"""Freeze the reviewed V69 sources and observed inputs; no numerical execution."""
from pathlib import Path
import json,hashlib,tarfile,io,datetime
from research_v69 import submission as s
R=Path(__file__).resolve().parents[1];W=Path('/Users/priyankjairaj/Documents/Codex/2026-10-10/see-i-am-working-on-a-2/work')
x=json.loads((R/'validation/v69_input_preflight_20261018_a.json').read_bytes());p68=json.loads((R/'handoff/registration_v68.json').read_bytes())
assert x['queue']=='' and x['cuda_receipt']['host']=='csis.cn4' and x['cuda_receipt']['status']=='complete'
assert x['cuda_receipt']['cuda_initialized'] is False and x['p67_runtime']==p68['base_runtime']
assert '15394|COMPLETED|0:0|18|00:04.331|1' in x['observer_scheduler']
assert (R/'validation/v69_local_checks_20261018_c.txt').read_text().endswith('OK\n')
paths=sorted(p for p in (R/'research_v69').iterdir() if p.is_file());assert len(paths)==40
new={str(s.RUN/'research_v69'/p.name):s.info(p.read_bytes()) for p in paths}
scheduler=(x['v68_scheduler']+'\n').encode();inputs=x['inputs']
inputs['targets']={k:x['target_candidates'][k+'_target'] for k in ['base','calibration']}
inputs['v68_scheduler']=dict(path=str(s.RUN/'v68-scheduler.txt'),**s.info(scheduler))
deps=dict(x['dependencies'])
for n,e in p68['tokenizer_runtime_files'].items():assert n not in deps or deps[n]==e;deps[n]=e
p=dict(schema='untouched-quality-campaign-v69',directory=str(s.RUN),resources=s.resources(),inputs=inputs,
    new_sources=new,dependency_files=deps,historical_ledgers=p68['historical_ledgers'],
    runtimes=dict(cpu={'csis.mn1':x['p67_runtime']},cuda={'csis.cn4':x['cuda_runtime']}),
    hosts=dict(cpu=['csis.mn1'],cuda=['csis.cn4']),interpreters=dict(cpu=str(s.CPU),cuda=str(s.CUDA)),
    software_modules=sorted(['research_v55.test_sequential',*['research_v69.'+q.stem for q in paths if q.name.startswith('test_') and q.suffix=='.py']]),
    expected_tests=100,v68_sha256=hashlib.sha256((R/'handoff/registration_v68.json').read_bytes()).hexdigest(),
    automatic_retry=False,registered=True,submission_policy='hold-bind-release-once-sequential-afterok',
    launch=dict(schema='held-slurm-launch-policy-v69',partitions={k:s.partition(v,'cpu-short' if k=='cpu' else 'gpu-short') for k,v in x['partitions'].items()},partition_hosts={k:sorted(s.NODES) for k in ['cpu','cuda']},qos_max_wall=x['qos'].split('|')[1],account='faculty',qos='cpu-short'))
s.policy(p);raw=s.canonical(p);h=s.sha(raw)
with (R/'handoff/registration_v69_quality.json').open('xb') as f:f.write(raw)
files={'program.json':raw,'registration.json':s.canonical(dict(program_sha256=h)),'v68-scheduler.txt':scheduler}
files.update({'research_v69/'+q.name:q.read_bytes() for q in paths})
with tarfile.open(W/'v69-quality-stage.tar.gz','w:gz') as t:
 for n,b in sorted(files.items()):
  m=tarfile.TarInfo(n);m.size=len(b);m.mode=0o644;t.addfile(m,io.BytesIO(b))
report=dict(schema='v69-quality-registration-observation',created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),registration_sha256=h,registration_bytes=len(raw),new_sources=40,total_numerical_source_bindings=532,local_v69_tests=94,expected_linux_tests=100,cuda_inventory_job='15394',cuda_inventory_host='csis.cn4',cuda_inventory_charged_cpu_seconds=4,cuda_inventory_scheduler_cpu_seconds='4.331',allowance_cpu_seconds=44726,staged_files=len(files),staging_archive=s.info((W/'v69-quality-stage.tar.gz').read_bytes()),numerical_work_started=False,automatic_retry=False)
with (R/'validation/v69_quality_registration_20261018.json').open('x') as f:json.dump(report,f,indent=2,sort_keys=True)
print(json.dumps(report))
