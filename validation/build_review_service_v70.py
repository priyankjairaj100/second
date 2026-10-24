"""E16 reporting supplement: typed receipts and descriptive arithmetic, no inference."""
from pathlib import Path
from decimal import Decimal
import json,hashlib,tarfile,zipfile,tempfile,copy
from validation.build_review_receipts_v69 import strings,transform,verify,census,IDENTITY,encoded,commit
R=Path(__file__).resolve().parents[1]
def build():
 archive=R/'campaigns/csis_v67_terminal_metadata_20261018_a.tar.gz';report=json.loads((R/'validation/v67_terminal_reconciliation_20261018_a.json').read_bytes())
 assert commit(archive.read_bytes())==report['snapshot'] and report['status']=='verified_terminal_receipt_metadata'
 assert report['cluster_terminal_audit_claims_reconciled'] and not report['actual_model_state_bytes_checked_locally']
 originals={}
 with tarfile.open(archive) as t:
  for role in ['primary','supplemental']:
   b=t.extractfile(role+'-audit.json').read();assert commit(b)==report['audit_receipt_commitments'][role]
   originals['E16_'+role+'_receipt.json']=json.loads(b)
 rows=report['comparison_rows'];ratios=[]
 for step in [1,2]:
  arms={r['arm']:r for r in rows if r['step']==step};c=arms['compressed']
  for name in ['cached','modern','hybrid','cold']:
   a=arms[name]
   ratios.append(dict(step=step,reference=name,live_saving_percent=str(100*(1-Decimal(c['live_state_bytes'])/a['live_state_bytes'])),request_slowdown_percent=str(100*(Decimal(c['request_elapsed_ns'])/a['request_elapsed_ns']-1)),checkpoint_inclusive_saving_percent=str(100*(1-Decimal(c['checkpoint_inclusive_bytes'])/a['checkpoint_inclusive_bytes']))))
 summary=dict(evidence_id='E16',status='completed_development_service',rows=rows,ratios=ratios,
   attributed_timings=report['costs']['timings'],preparation_transaction_elapsed_ns=report['costs']['preparation_transaction_elapsed_ns'],oracle_transaction_elapsed_ns=report['costs']['oracle_transaction_elapsed_ns'],
   numerical_worker_charged_cpu_seconds=report['numerical_worker_charged_cpu_seconds'],scheduler_allocation_cpu_seconds=report['scheduler_allocation_cpu_seconds'],controller_own_cpu_ns=report['controller_own_cpu_ns'],added_codec_installation_bytes=report['added_codec_installation_bytes'],audit_entries=report['audit_entries'],
   full_model_state_comparisons=10,quality_evaluated=False,confirmation=False,independent_implementation=False,
   timing_replicates_per_arm_endpoint=1,nested_clocks_must_not_be_added=True,
   scope='Five complete service arms, two endpoints, one disjoint development root. Saved cluster audits compare actual model/state bytes against fresh retained-input reconstruction using a shared solver. Local checks reconcile metadata only. No quality, timing uncertainty, population reliability, or general acceleration result.')
 originals['E16_comparison_and_costs.json']=summary
 all_s=set(x for o in originals.values() for x in strings(o));mapping={}
 for i,x in enumerate(sorted(x for x in all_s if IDENTITY.search(x)),1):
  if x.startswith(('/Users/','/nfs_home/')):label='REVIEW_PATH_'
  elif x.startswith('c4:'):label='REVIEW_ARTICLE_'
  elif x in ['csis.mn1','csis.cn1','csis.cn2','csis.cn3','csis.cn4']:label='REVIEW_HOST_'
  else:raise ValueError('Unreviewed identity category: '+x[:100])
  n=label+str(i).zfill(4);assert n not in all_s;mapping[x]=n
 reverse={v:k for k,v in mapping.items()};derived={}
 for n,o in originals.items():
  d=transform(o,mapping);verify(o,d,reverse);assert census(o)==census(d);derived[n]=d
 out=R/'reports/review-service-v70';out.mkdir(exist_ok=False)
 files={n:encoded(d) for n,d in derived.items()}
 files['README.txt']=b'''E16: disjoint-root complete-service development result\n\nFive arms and two deletion endpoints; all ten model/state comparisons passed the\ncluster's fresh reconstruction and saved-artifact checks. The numerical solver is\nshared; this is not independent implementation replication. The comparison JSON\npreserves all ten storage, request/transaction, source-traversal, numerical fallback\nand cost rows. Percentages are descriptive single-trajectory arithmetic.\nCompression remains smaller than both caches, but its measured requests are slower.\nHybrid is faster and smaller at the first endpoint with a different source-access\nrequirement. Numerical row fallback is not source replay. No untouched quality or\ntiming uncertainty is established. Checkpoint-inclusive storage excludes separately\nreported codec installation bytes. Nested worker/controller/scheduler clocks must\nnot be added. Attributed preparation is not a measured deployment lifetime.\n\nThe two receipt JSON files are labelled derivatives of actual completed cluster\naudits. Every typed field is preserved, with reversible labels for paths, hosts\nand article identifiers. Embedded hashes refer to original objects. These copies\nare not executable registrations and do not re-audit model/state binaries locally.\nNo raw corpus, tokens, model/state binaries or private identity map is distributed.\nThe private reverse mapping is kept outside this component. Known identifier checks\ndo not resolve indirect linkage through hashes, version/job IDs or public sources.\n\nRead alongside the five preserved historical components. E01--E15 and the failed\nnearest-anchor quality guard remain unchanged. The historical source component\npredates the scheduler-presentation adjustments in the newly frozen quality phase;\nit is not the final current-source reproduction bundle. Final quality, timing,\nreproduction, notices, anonymity, author details and rendered layout remain open.\n'''
 files['MANIFEST.sha256']=''.join(commit(b)['sha256']+'  '+n+'\n' for n,b in sorted(files.items())).encode()
 for n,b in files.items():assert not IDENTITY.search(b.decode());(out/n).write_bytes(b)
 zpath=R/'reports/development-service-evidence-v70.zip'
 with zipfile.ZipFile(zpath,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for n,b in sorted(files.items()):z.writestr('service-evidence/'+n,b)
 with tempfile.TemporaryDirectory() as tmp:
  with zipfile.ZipFile(zpath) as z:
   assert len(z.namelist())==5
   for n,b in files.items():assert z.read('service-evidence/'+n)==b
   for n,o in originals.items():verify(o,json.loads(z.read('service-evidence/'+n)),reverse)
 # Changing a numerical result or omitting an audit field must fail typed roundtrip.
 probes=[]
 for name in ['E16_comparison_and_costs.json','E16_primary_receipt.json']:
  d=copy.deepcopy(derived[name]);d.pop(next(iter(d)))
  try:verify(originals[name],d,reverse)
  except ValueError:probes.append(name)
  else:raise AssertionError('Dropped field not detected')
 private=dict(mapping=mapping,original_archive=commit(archive.read_bytes()),derivative_files={n:commit(b) for n,b in files.items()},exclude_from_anonymous_archive=True)
 (R/'docs/REVIEW_SERVICE_DERIVATION_V70.json').write_bytes(encoded(private))
 result=dict(status='typed_receipts_arithmetic_and_archive_verified',archive=commit(zpath.read_bytes()),members=5,typed_roundtrips=3,discarded_field_probes_rejected=probes,comparison_rows=10,known_identity_scan_passed=True,full_anonymity_verified=False,empirical_audits_rerun=False,submission_ready=False)
 (R/'validation/v70_service_companion.json').write_bytes(encoded(result));print(json.dumps(result))
if __name__=='__main__':build()
