"""Reporting-only source/receipt check; does not execute model experiments."""
import datetime,hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def load(p):return json.loads((R/p).read_text())
def info(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def terminal(snapshot,job):
 rows=[x.split('|') for x in snapshot['accounting'].splitlines()];found=[dict(zip(rows[0],x)) for x in rows[1:] if x[0]==job]
 assert len(found)==1 and found[0]['State']=='COMPLETED' and found[0]['ExitCode']=='0:0';return found[0]
p79=load('research_v79/program.json');p80=load('research_v80/program.json');p81=load('research_v81/program.json')
programs={str(v):info((R/f'research_v{v}/program.json').read_bytes())['sha256'] for v in (79,80,81)}
sources=p81['sources'];aux=p81['protected_auxiliary_sources']
for name,e in dict(sources,**aux).items():assert info((R/name).read_bytes())==e,name
for path,e in p80['new_sources'].items():assert sources[str(Path(path).relative_to(p80['directory']))]==e
for name,e in p79['sources'].items():assert sources[name]==e
assert len(sources)==851 and len(aux)==5
man=(R/'reports/manuscript_v74.tex').read_bytes();assert info(man)['sha256']=='bf3b7a73cda7b4c62fb7fe6fc7df08a36e949cb15f4c0d9e361fc25a732cc8eb'
d79=Path('pilots/service-integration-v79-20261023-a');s79=load(d79/'terminal-snapshot.json');c79=load(d79/'completion.json')
assert c79['status']=='complete' and c79['error'] is None and c79['job_id']=='15903' and c79['program_sha256']==programs['79']
assert c79['aggregate_cpu_ns']==c79['process_cpu_ns']+c79['waited_child_cpu_ns']<=602*10**9
assert (s79['sources_verified'],s79['dependencies_verified'],s79['outputs_verified'])==(777,11,2)
for name,e in c79['outputs'].items():assert info((R/d79/name).read_bytes())==e
assert load(d79/'outputs/integration-results.json')['suites']=={n:dict(tests=t,failures=0,errors=0,skipped=0) for n,t in [('legacy',44),('four_cell_integration',5)]}
d80=Path('pilots/four-cell-service-v80-20261023-a');s80=load(d80/'active-snapshot.json');c80=load(d80/'software-completion.json')
assert c80['status']=='complete' and c80['error'] is None and c80['job_id']=='15904' and c80['program_sha256']==programs['80']
assert (c80['tests'],c80['failures'],c80['errors'],c80['skipped'])==(73,0,0,0)
assert c80['process_cpu_ns']+c80['waited_child_cpu_ns']<=602*10**9
assert [s80[k+'_verified'] for k in ('prior_sources','new_sources','dependency_files','historical_ledgers')]==[456,834,11,102]
order=p80['trial_order']+['primary','supplemental'];ids={t:load(d80/(t+'-submission.json'))['job_id'] for t in order}
assert [ids[t] for t in order]==[str(n) for n in range(15905,15917)]
assert p80['phase_cpu_seconds']==108020<=p80['preserved_phase_ceiling']==120624
assert p80['controller_allowance_cpu_seconds']==6020<=p80['preserved_controller_ceiling']==7224
d81=Path('pilots/transfer-software-v81-20261023-a');release=load(d81/'release.json');held=load(d81/'held-job.json')
assert release==dict(job_id='15917',program_sha256=programs['81'],released=True)
assert 'afterany:15916' in held['snapshot'] and 'JobState=PENDING' in held['snapshot']
assert p81['transfer_grid_allowance']['entries']==1327104 and p81['transfer_grid_allowance']['user_approval']=='Approve the transfer-only grid allowance'
assert sum(p81['expected']['suite_counts'].values())==62
v=dict(status='verified_reporting_checkpoint',checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),observation_utc=s80['captured_utc'],programs=programs,
 frozen_source_count=len(sources),auxiliary_source_count=len(aux),frozen_sources=sources,auxiliary_sources=aux,
 v79=dict(tests=49,job_id='15903',terminal=terminal(s79,'15903'),aggregate_cpu_ns=c79['aggregate_cpu_ns']),
 v80=dict(tests=73,software_job='15904',software_terminal=terminal(s80,'15904'),jobs=ids,status='running; no numerical result yet',aggregate_software_cpu_ns=c80['process_cpu_ns']+c80['waited_child_cpu_ns']),
 v81=dict(job_id='15917',status='dependency pending; not qualified',tests_expected=62,transfer_grid_user_approved=1327104),
 scientific_claim_changed=False,independent_review=False,manuscript_sha256=info(man)['sha256'])
(R/'validation/v81_checkpoint_check.json').write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:x for k,x in v.items() if k not in ('frozen_sources','auxiliary_sources')},indent=2))
