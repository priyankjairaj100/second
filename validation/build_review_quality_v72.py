"""E17 saved-loss and audited-recovery companion; no empirical rerun."""
from pathlib import Path
import json,tarfile,zipfile,tempfile,ast,inspect,copy,hashlib,subprocess,sys
from validation.build_review_receipts_v69 import strings,transform,verify,census,IDENTITY,encoded,commit
from validation.check_v71_completed_losses import arithmetic
R=Path(__file__).resolve().parents[1]
recovery=json.loads((R/'validation/v72_recovery_reconciliation.json').read_bytes())
scalar=json.loads((R/'validation/v72_saved_scalar_reconciliation.json').read_bytes())
assert recovery['recovered_quality_evidence_verified'] and scalar['separate_recovery_verified']
originals={}
with tarfile.open(R/'campaigns/csis_v72_scalar_losses_20261018_a.tar.gz') as t:
 assert commit((R/'campaigns/csis_v72_scalar_losses_20261018_a.tar.gz').read_bytes())==scalar['archive']
 for target,source in [('E17_paired_losses.json','gpu_quality/outputs/losses/paired-losses.json'),('E17_statistics.json','gpu_quality/outputs/losses/statistics.json')]:
  originals[target]=json.load(t.extractfile(source))
 originals['E17_cpu_reference_losses.json']=json.load(t.extractfile('cpu_parity/outputs/losses/completion.json'))['quality']
 originals['E17_terminal_audit.json']=json.load(t.extractfile('terminal/outputs/completion.json'))['result']
 originals['E17_failed_closure_receipt.json']=json.load(t.extractfile('closure/receipt.json'))
with tarfile.open(R/'campaigns/csis_v72_recovery_metadata_20261018_a.tar.gz') as t:
 assert commit((R/'campaigns/csis_v72_recovery_metadata_20261018_a.tar.gz').read_bytes())==recovery['recovery_archive']
 originals['E17_recovery_receipt.json']=json.load(t.extractfile('receipt.json'))
originals['E17_summary.json']=dict(evidence_id='E17',status='untouched_quality_verified_with_separate_accounting_recovery',
 articles=320,predictions_per_article=127,model_roles=6,actual_gpu_losses=1920,actual_cpu_losses=24,
 primary_endpoints=[12,6],sample_frame_complete_records=3801,eligible_records=2778,
 quality_guard_pass=recovery['quality_guard_pass'],bootstrap_draws=20000,pooled_guard=1.05,observed_maximum_guard=1.20,
 one_sided_upper_confidence=.975,nominal_familywise_level=.95,original_campaign_successful=False,
 original_closure_failed=True,original_failed_closure_scheduler_cpu_ns=recovery['failed_closure_scheduler_cpu_ns'],
 separate_recovery_scheduler_cpu_ns=recovery['recovery_scheduler_cpu_ns'],combined_scheduler_cpu_ns=recovery['combined_scheduler_cpu_ns'],
 numerical_worker_charged_cpu_seconds=recovery['numerical_worker_charged_cpu_seconds'],
 controller_charged_cpu_seconds=recovery['controller_charged_cpu_seconds'],
 supplementary_scalar_check=scalar,independent_neural_replication=False,
 scope='Fixed target, one bounded article frame, two dependent retained endpoints. Slightly worse perplexity than sequential calibration; predeclared tolerances pass. No population-tail, transfer, timing reliability or general speedup claim.')
all_strings=set(x for value in originals.values() for x in strings(value));mapping={}
for i,x in enumerate(sorted(x for x in all_strings if IDENTITY.search(x)),1):
 if x.startswith(('/Users/','/nfs_home/')):prefix='REVIEW_PATH_'
 elif x.startswith('c4:'):prefix='REVIEW_ARTICLE_'
 elif x.startswith('csis.'):prefix='REVIEW_HOST_'
 else:raise ValueError('Unreviewed identity category: '+x[:100])
 mapping[x]=prefix+str(i).zfill(4);assert mapping[x] not in all_strings
reverse={v:k for k,v in mapping.items()};files={}
for name,value in originals.items():
 derived=transform(value,mapping);verify(value,derived,reverse);assert census(value)==census(derived)
 files[name]=encoded(derived)
function=inspect.getsource(arithmetic)
checker='''"""Offline scalar arithmetic only; no neural or bootstrap reexecution."""\nfrom pathlib import Path\nimport json,math\nMODELS=('original','nearest','candidate_12','sequential_12','candidate_6','sequential_6')\n'''+function+'''\nif __name__=='__main__':
    root=Path(__file__).resolve().parent
    rows=json.loads((root/'E17_paired_losses.json').read_text())['rows']
    stats=json.loads((root/'E17_statistics.json').read_text())
    result=arithmetic(rows,stats)
    print(json.dumps(dict(status='saved_scalar_arithmetic_verified',endpoints=result,bootstrap_reexecuted=False,neural_inference_reexecuted=False),sort_keys=True))
'''
assert ast.dump(ast.parse(function).body[0])==ast.dump(next(n for n in ast.parse(checker).body if isinstance(n,ast.FunctionDef)))
files['verify_statistics.py']=checker.encode()
files['README.txt']=b'''E17: untouched quality and separately recovered accounting

Both retained endpoints pass the predeclared pooled, bootstrap-upper and observed
maximum-article guards on the same320 outcome-blind selected articles. Candidate
perplexity is slightly worse than matched sequential calibration; both paired95%
percentile intervals lie above one. Do not call this a quality gain or equivalence.
The whole inspected bounded frame is excluded from later reuse. Earlier failed
admission, nearest-anchor quality failure and adaptive teacher selection remain.

Seven JSON files are labelled derivatives preserving every typed field. Article,
host and private path strings have reversible labels; the private reverse map is
excluded. The paired-loss file contains all six GPU sums/means for each article;
the CPU file preserves the24 reference sums/means. Raw corpus, tokens, model/state
bodies and per-inference timing files are excluded. Original file commitments in
receipts remain commitments to original bytes, not these renamed derivatives.

The terminal audit checked actual saved codes, original parameters,1920 GPU and
24 CPU losses, ordered parity barrier and bootstrap statistics on the cluster.
The original closure failed because sacct was unavailable in its container. Its
receipt and4.817 scheduler CPU seconds remain. A separately registered artifact/
accounting job passed without rerunning models or inference; its scheduler CPU is
6.312 seconds. Combined scheduler CPU is7588.049 seconds. Nested worker/controller
and scheduler measures overlap and must not be added.

Run python3 verify_statistics.py from any working directory. It recomputes pooled
NLL, paired log ratios, observed maxima and guard decisions from saved paired
losses. It does NOT regenerate bootstrap draws or neural outputs. It reuses the
supplementary root arithmetic implementation. The original statistics function's
actual_loss_artifact_validation_performed=false field describes that function
alone; actual-file validation is in the separate terminal audit. Preserve both.

These results concern one checkpoint, one bounded article frame and two dependent
retained endpoints. No population-tail, transfer, independent model implementation
or reliable latency claim follows. Hashes and public source similarity can remain
indirectly identifying; full anonymity is not established. This is a development
component, not a final submission or complete empirical reproduction archive.
'''
files['MANIFEST.sha256']=''.join(commit(b)['sha256']+'  '+n+'\n' for n,b in sorted(files.items())).encode()
assert len(files)==10
out=R/'reports/review-quality-v72';out.mkdir(exist_ok=False)
for n,b in files.items():assert not IDENTITY.search(b.decode()),n;(out/n).write_bytes(b)
zpath=R/'reports/development-quality-evidence-v72.zip'
with zipfile.ZipFile(zpath,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for n,b in sorted(files.items()):z.writestr('quality-evidence/'+n,b)
with tempfile.TemporaryDirectory() as temp:
 with zipfile.ZipFile(zpath) as z:
  assert len(z.namelist())==10
  for n,b in files.items():assert z.read('quality-evidence/'+n)==b
  z.extractall(temp)
 run=subprocess.run([sys.executable,str(Path(temp)/'quality-evidence/verify_statistics.py')],capture_output=True,text=True,check=True)
 portable=json.loads(run.stdout);assert portable['status']=='saved_scalar_arithmetic_verified'
probes=[]
for n in ['E17_statistics.json','E17_recovery_receipt.json','E17_failed_closure_receipt.json']:
 d=json.loads(files[n]);d.pop(next(iter(d)))
 try:verify(originals[n],d,reverse)
 except ValueError:probes.append(n)
 else:raise AssertionError('Missing field accepted')
(R/'docs/REVIEW_QUALITY_DERIVATION_V72.json').write_bytes(encoded(dict(mapping=mapping,exclude_from_review=True,derivative_files={n:commit(b) for n,b in files.items()})))
result=dict(schema='v72-review-quality-component',status='typed_derivatives_and_saved_scalar_check_verified',archive=commit(zpath.read_bytes()),members=10,
 typed_roundtrips=7,paired_articles=320,model_roles=6,cpu_reference_losses=24,portable_arithmetic_check=portable,
 missing_field_probes_rejected=probes,original_failure_preserved=True,known_identity_scan_passed=True,
 full_anonymity_verified=False,bootstrap_reexecuted=False,model_or_inference_reexecuted=False,submission_ready=False)
(R/'validation/v72_quality_companion.json').write_bytes(encoded(result));print(json.dumps({k:result[k] for k in ['status','archive','members','typed_roundtrips','missing_field_probes_rejected']}))
