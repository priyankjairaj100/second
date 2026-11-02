import datetime,hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
hist=json.loads((R/'validation/v74_frozen_source_check.json').read_text())
sources=dict(hist['numerical_sources']);aux=hist['auxiliary_sources'];programs={}
for v in (76,78):
 p=R/f'research_v{v}/program.json';raw=p.read_bytes();j=json.loads(raw);programs[str(v)]=hashlib.sha256(raw).hexdigest()
 for n,e in j['sources'].items():
  if n in sources:assert sources[n]==e,n
  sources[n]=e
for n,e in dict(sources,**aux).items():
 b=(R/n).read_bytes();assert len(b)==e['bytes'] and hashlib.sha256(b).hexdigest()==e['sha256'],n
man=(R/'reports/manuscript_v74.tex').read_bytes()
assert hashlib.sha256(man).hexdigest()=='bf3b7a73cda7b4c62fb7fe6fc7df08a36e949cb15f4c0d9e361fc25a732cc8eb'
receipts={}
for v,folder,job,count in [(76,'speed-software-v76-20261022-a','15897',311),(78,'control-software-v78-20261023-a','15898',620)]:
 d=R/'pilots'/folder;s=json.loads((d/'terminal-snapshot.json').read_text());c=json.loads((d/'completion.json').read_text())
 assert c['status']=='complete' and c['error'] is None and c['job_id']==job and c['program_sha256']==programs[str(v)]
 assert c['aggregate_cpu_ns']<=602*10**9 and c['aggregate_cpu_ns']==c['process_cpu_ns']+c['waited_child_cpu_ns']
 assert s['sources_verified']==count
 lines=[line.split('|') for line in s['accounting'].splitlines()];fields=lines[0];actual=[dict(zip(fields,row)) for row in lines[1:] if row[0]==job]
 assert len(actual)==1 and actual[0]['State']=='COMPLETED' and actual[0]['ExitCode']=='0:0'
 textchecked=0
 for name,e in c['outputs'].items():
  if (d/name).is_file():
   b=(d/name).read_bytes();assert len(b)==e['bytes'] and hashlib.sha256(b).hexdigest()==e['sha256'];textchecked+=1
 assert s['outputs_verified']==len(c['outputs'])
 receipts[str(v)]=dict(job_id=job,status='verified_software_qualification',source_count=count,aggregate_cpu_ns=c['aggregate_cpu_ns'],elapsed_ns=c['elapsed_ns'],scheduler=actual[0],remote_verified_outputs=s['outputs_verified'],local_verified_text_outputs=textchecked,independent_review=False)
 if v==76:
  codec=json.loads((d/'outputs/codec/software-results.json').read_text());tok=json.loads((d/'outputs/token-results.json').read_text())
  assert codec['differential_cases']==dict(valid=40,mutated=6810,boundary=1600,accepted_mutations=2710,rejected_mutations=4100)
  assert all(x['tests']==8 and x['passed'] for x in codec['legacy_tests'].values())
  assert tok['coefficient_parity_cases']==16 and tok['primitive']['words_per_library']==1016385
  assert all(x==dict(count=21,errors=0,failures=0,skips=0) for x in tok['legacy_tests'].values())
 else:
  j=json.loads((d/'outputs/control-results.json').read_text())
  assert j['suites']=={k:dict(tests=n,errors=0,failures=0,skipped=0) for k,n in [('reference',17),('optimized',17),('cache_mechanics',9),('cache_parser',8)]}
  assert s['dependencies_verified']==11
validation=dict(status='verified',checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),historical_numerical_source_count=581,auxiliary_source_count=len(aux),frozen_source_union_count=len(sources),numerical_and_qualified_software_sources=sources,auxiliary_sources=aux,receipts=receipts,manuscript_sha256=hashlib.sha256(man).hexdigest(),scientific_claim_changed=False)
(R/'validation/v79_checkpoint_check.json').write_text(json.dumps(validation,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:v for k,v in validation.items() if k not in ('numerical_and_qualified_software_sources','auxiliary_sources')},indent=2))
