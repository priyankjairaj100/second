"""Package V123 editorial/theory revision with historical evidence unchanged."""
import hashlib,json,zipfile,subprocess,sys,tempfile,datetime
from pathlib import Path
R=Path(__file__).resolve().parents[1]
W=Path('/Users/priyankjairaj/Documents/Codex/2026-10-10/see-i-am-working-on-a-2')
D=W/'work/tacl-review-followup-v123';O=W/'outputs'
def identity(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def enc(x):return (json.dumps(x,indent=2,sort_keys=True)+'\n').encode()
def archive(path,prefix,payload):
 assert not path.exists(),path
 with zipfile.ZipFile(path,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for n,b in sorted(payload.items()):
   zi=zipfile.ZipInfo(prefix+'/'+n,(2026,10,29,0,0,0));zi.compress_type=zipfile.ZIP_DEFLATED;zi.external_attr=0o100644<<16;z.writestr(zi,b)
 with zipfile.ZipFile(path) as z:assert {Path(n).name:z.read(n) for n in z.namelist()}==payload
checks=json.loads((R/'validation/v123_manuscript_checks.json').read_bytes())
source=(O/'second-research-draft.tex').read_bytes();pdf=(D/'final/second-research-draft.pdf').read_bytes()
assert identity(source)==checks['manuscript'] and identity(pdf)==checks['pdf']
assert checks['native_compile_success'] and checks['visual_review_status']=='passed_all_11_pages'
assert (checks['content_pages'],checks['reference_pages'],checks['appendices'])==(10,1,0)
checklist=(R/'docs/TACL_SUBMISSION_CHECKLIST_V123.txt').read_bytes()
response=(R/'docs/REVIEW_FOLLOWUP_V123.txt').read_bytes()
plan=(R/'docs/TACL_REVISION_EVIDENCE_PLAN_V122.txt').read_bytes()
reference=(R/'validation/v123_reference_audit.json').read_bytes()
readme=b'''TACL manuscript build V123, 29 October 2026

main.tex is the same standalone source open in the Codex editor. It embeds the
unmodified official tacl2021v1.sty and all fifteen references. The separate style
copy is identical. Native compilation passes. The delivered PDF is an independent
Tectonic 0.17.0 export: ten content pages, one references page, no appendices.
No font, margin, line-spacing or title-box reduction was used to meet the limit.

V123 resolves four technical ambiguities, reports generated-test coverage, and
adds measured changed-code counts from four already-saved model transitions.
No new calibration or likelihood experiment was run. Read REVIEW_FOLLOWUP_V123.txt
and the prospective V122 evidence plan. Matched-target quality, minimal cold
baseline and broader operating-range measurements remain pending. The entire
previously inspected quality/calibration frames remain excluded from new samples.

This ZIP is an editable author-side build package, not a TACL review supplement.
The full author evidence package is separate. TACL disallows external review
supplements. No upload or submission was performed. Author eligibility/history,
consent, release terms and metadata remain unverified.
'''
source_payload={'main.tex':source,'tacl2021v1.sty':(D/'tacl2021v1.sty').read_bytes(),'README.txt':readme,'TACL_SUBMISSION_CHECKLIST.txt':checklist,'REVIEW_FOLLOWUP_V123.txt':response,'TACL_REVISION_EVIDENCE_PLAN_V122.txt':plan,'REFERENCE_AUDIT.json':reference}
source_payload['MANIFEST.json']=enc({n:identity(b) for n,b in source_payload.items()})
old_path=O/'second-development-review-v119.zip'
old_report=json.loads((R/'validation/v119_development_bundle.json').read_bytes());assert identity(old_path.read_bytes())==old_report['archive']
with zipfile.ZipFile(old_path) as z:old={Path(n).name:z.read(n) for n in z.namelist()}
for n,h in json.loads(old['MANIFEST.json']).items():assert identity(old[n])==h
payload={n:b for n,b in old.items() if n.endswith('.zip')};assert len(payload)==14
payload.update({'second-research-draft.tex':source,'second-tacl-submission.pdf':pdf,
 'TACL_SUBMISSION_CHECKLIST.txt':checklist,'verify_review_bundle.py':old['verify_review_bundle.py'],
 'REVIEW_FOLLOWUP_V123.txt':response,'TACL_REVISION_EVIDENCE_PLAN_V122.txt':plan,
 'REFERENCE_AUDIT.json':reference,
 'README.txt':b'''Second author-side evidence and revision checkpoint V123

The revised manuscript has ten content pages and one reference page, no appendix.
Native compilation and independent all-page rendered-PDF checks pass. V123 fixes
four technical ambiguities, adds generated-test coverage, and reports actual
changed-code counts for the four saved headline model transitions. It does not
complete the empirical TACL revision. Consult REVIEW_FOLLOWUP_V123.txt and the
V122 prospective evidence plan. QUALITY_INPUT_READINESS_V123.json binds the exact
models and records the remaining quality prerequisites and frame exclusions.

All fourteen historical evidence/source ZIP components, including failures and
negative results, are byte-identical. From a fresh extraction, standard Python 3:
python3 verify_review_bundle.py PATH_TO_EXTRACTED_DIRECTORY
This unchanged verifier checks 1,322 historical source/protocol copies and the
supplied-byte manifest. It is not an independent re-audit of remote model binaries.

Two inherited small generated checkers remain in flat files. Run
check_mathematics_v121.py using standard Python 3, then
review_response_checks_v122.py with Python 3 and NumPy (validated with Python
3.9.6 and NumPy 1.26.3). They emit JSON beside themselves. The latter loads named
AST functions from low_rank_certified.py and rational helpers from the former.
It also reads E16_comparison_and_costs.json. These are generated algebra/Python
checks, not production C qualification or complete repair-transaction tests.

The additional saved-code audit is a separately registered, completed posthoc
measurement (job 16651). Its source, manifest, raw result, closure and scheduler
receipt are flat V123 files. Run changed_codes_v123.py --self-test for the portable
integer counter checks only. Recomputing the original counts requires the named
remote saved models and bound completion metadata; those binaries are not in this
archive. The one-use registered audit must not be rerun. No model calibration or
likelihood evaluation occurred. Whole-stage replay classification does not identify
which individual changed codes required replay. See AUDIT_PROTOCOL_V123.txt.

Complete external-input reproduction, matched-target quality, the minimal-storage
source-only cold comparison and operating-range evidence remain pending. All
fifteen reference identities retain the V121/V122 primary checks, with unchanged
claims and verified final destinations. Author declarations are unverified.

This archive is for authors. TACL disallows external review supplements and links
to them. Do not upload it with the review PDF. Own-code release licensing remains
an author decision. No corpus, weights, runtime binaries or credentials are added.
No submission, scheduler restart or historical-job retry occurred.
'''})
for rel in ['validation/check_mathematics_v121.py','validation/v121_math_audit.json','validation/review_response_checks_v122.py','validation/v122_generated_checks.json','src/low_rank_certified.py','reports/review-service-v70/E16_comparison_and_costs.json']:
 payload[Path(rel).name]=(R/rel).read_bytes()
for dest,rel in {
 'changed_codes_v123.py':'reporting_v123/changed_codes.py',
 'AUDIT_MANIFEST_V123.json':'reporting_v123/manifest.json',
 'AUDIT_PROTOCOL_V123.txt':'reporting_v123/PROTOCOL.txt',
 'SAVED_CODE_CHANGES_V123.json':'pilots/saved-code-audit-v123-20261029/result.json',
 'SAVED_CODE_AUDIT_CLOSURE_V123.json':'validation/v123_changed_codes_audit.json',
 'SAVED_CODE_AUDIT_SACCT_V123.txt':'pilots/saved-code-audit-v123-20261029/sacct.txt',
 'QUALITY_INPUT_READINESS_V123.json':'validation/v123_quality_input_readiness.json',
}.items():payload[dest]=(R/rel).read_bytes()
payload['MANIFEST.json']=enc({n:identity(b) for n,b in sorted(payload.items())})
with tempfile.TemporaryDirectory(prefix='second-v123-check-') as td:
 root=Path(td)
 for n,b in payload.items():(root/n).write_bytes(b)
 p=subprocess.run([sys.executable,'-I','-B',str(root/'verify_review_bundle.py'),str(root)],capture_output=True,text=True,timeout=30)
 assert p.returncode==0,p.stderr;verified=json.loads(p.stdout)
 for name,report in [('check_mathematics_v121.py','v121_math_audit.json'),('review_response_checks_v122.py','v122_generated_checks.json')]:
  p=subprocess.run([sys.executable,'-I','-B',str(root/name)],capture_output=True,text=True,timeout=60)
  assert p.returncode==0,p.stderr
  assert json.loads((root/report).read_bytes())==json.loads(payload[report]),report
 p=subprocess.run([sys.executable,'-I','-B',str(root/'changed_codes_v123.py'),'--self-test'],capture_output=True,text=True,timeout=30)
 assert p.returncode==0,p.stderr
 counter_self_test=p.stdout.strip()
# Write deliverables only after successful extracted-only checks.
for dest,b in [(R/'reports/manuscript_v123.tex',source),(R/'reports/second_tacl_v123.pdf',pdf),(O/'second-tacl-submission.pdf',pdf)]:
 if dest==O/'second-tacl-submission.pdf':
  assert identity(dest.read_bytes())['sha256']=='424679733e47dba403ee8f008f966a73600fde56ceb8a3cacf9ebcd6033c6cf6'
 else: assert not dest.exists(),dest
 dest.write_bytes(b)
source_zip=O/'second-tacl-source-v123.zip';archive(source_zip,'second-tacl-source-v123',source_payload)
full=O/'second-author-review-v123.zip';archive(full,'second-author-review-v123',payload)
assert all(payload[n]==b for n,b in old.items() if n.endswith('.zip'))
result=dict(schema='second-tacl-packages-v123',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 source_package=dict(path=str(source_zip),archive=identity(source_zip.read_bytes()),members=len(source_payload)),
 author_evidence_package=dict(path=str(full),archive=identity(full.read_bytes()),members=len(payload),unchanged_components=14,verified=verified),
 manuscript=identity(source),pdf=dict(path=str(O/'second-tacl-submission.pdf'),**identity(pdf)),
 generated_checks_reproduced_from_extracted_flat_files=True,clean_empirical_reproduction=False,
 new_saved_output_measurement=True,no_new_model_calibration_or_inference=True,changed_code_self_test=counter_self_test,original_sources_changed=False,source_package_is_review_supplement=False,
 author_evidence_is_review_supplement=False,submission_readiness_established=False,submission_performed=False)
(R/'validation/v123_packages.json').write_bytes(enc(result));print(json.dumps(result,indent=2))
