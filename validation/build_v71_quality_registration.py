"""Separate corrected quality campaign; preserve failed V69 and all old inputs."""
from pathlib import Path
import json,copy,tarfile,io,datetime
from research_v71 import submission as s
R=Path(__file__).resolve().parents[1];W=Path('/Users/priyankjairaj/Documents/Codex/2026-10-10/see-i-am-working-on-a-2/work')
old=json.loads((R/'handoff/registration_v69_quality.json').read_bytes());p=copy.deepcopy(old)
for n,e in old['new_sources'].items():assert s.info((R/'research_v69'/Path(n).name).read_bytes())==e
assert (R/'validation/v71_local_checks_20261018_b.txt').read_text().endswith('OK\n')
assert json.loads((R/'validation/v70_admission_and_frame_reconciliation.json').read_bytes())['status']=='verified_failed_admission_and_separate_frame_audit_metadata'
with tarfile.open(R/'campaigns/csis_v70_frame_audit_20261018_a.tar.gz') as t:
 receipt=t.extractfile('receipt.json').read();c=json.load(t.extractfile('collection.json'))
r=json.loads(receipt);assert r['status']=='complete' and r['job_id']=='15404'
p.update(schema='untouched-quality-campaign-v71',directory=str(s.RUN),resources=s.resources(),expected_tests=103)
files={str(q.relative_to(R)):q.read_bytes() for q in (R/'research_v71').iterdir() if q.is_file()};assert len(files)==40
p['new_sources']={str(s.RUN/n):s.info(b) for n,b in files.items()}
p['software_modules']=sorted(['research_v55.test_sequential',*['research_v71.'+Path(n).stem for n in files if Path(n).name.startswith('test_') and Path(n).suffix=='.py']])
p['launch']['schema']='held-slurm-launch-policy-v71'
p['inputs']['quality']['frame_audit']=dict(path='/nfs_home/users/poonam/second-20261010/local_runs/quality-frame-audit-v70-20261018-a/receipt.json',**s.info(receipt))
scheduler=(c['accounting']+'\n').encode();p['inputs']['frame_scheduler']=dict(path=str(s.RUN/'frame-scheduler.txt'),**s.info(scheduler))
# Original V68 scheduler bytes remain bound at the failed V69 directory; immutable.
s.policy(p);raw=s.canonical(p);h=s.sha(raw)
with (R/'handoff/registration_v71_quality.json').open('xb') as f:f.write(raw)
files.update({'program.json':raw,'registration.json':s.canonical(dict(program_sha256=h)),'frame-scheduler.txt':scheduler})
with tarfile.open(W/'v71-quality-stage.tar.gz','w:gz') as t:
 for n,b in sorted(files.items()):m=tarfile.TarInfo(n);m.size=len(b);m.mode=0o644;t.addfile(m,io.BytesIO(b))
result=dict(schema='v71-quality-registration-observation',created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),registration_sha256=h,registration_bytes=len(raw),source_files=40,local_tests=97,expected_linux_tests=103,allowance_cpu_seconds=44726,prior_failed_registration=s.sha((R/'handoff/registration_v69_quality.json').read_bytes()),prior_failed_jobs_preserved=True,same_320_selected_articles=True,same_v67_models_and_target=True,same_guards_and_caps=True,new_job_chain_not_a_v69_retry=True,frame_audit_job='15404',staging_archive=s.info((W/'v71-quality-stage.tar.gz').read_bytes()))
with (R/'validation/v71_quality_registration_20261018.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True)
print(json.dumps(result))
