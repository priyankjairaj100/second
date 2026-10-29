"""Package V122 editorial/theory revision with historical evidence unchanged."""
import hashlib,json,zipfile,subprocess,sys,tempfile,datetime
from pathlib import Path
R=Path(__file__).resolve().parents[1]
W=Path('/Users/priyankjairaj/Documents/Codex/2026-10-10/see-i-am-working-on-a-2')
D=W/'work/tacl-review-response-v122';O=W/'outputs'
def identity(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def enc(x):return (json.dumps(x,indent=2,sort_keys=True)+'\n').encode()
def archive(path,prefix,payload):
 assert not path.exists(),path
 with zipfile.ZipFile(path,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for n,b in sorted(payload.items()):
   zi=zipfile.ZipInfo(prefix+'/'+n,(2026,10,29,0,0,0));zi.compress_type=zipfile.ZIP_DEFLATED;zi.external_attr=0o100644<<16;z.writestr(zi,b)
 with zipfile.ZipFile(path) as z:assert {Path(n).name:z.read(n) for n in z.namelist()}==payload
checks=json.loads((R/'validation/v122_manuscript_checks.json').read_bytes())
source=(O/'second-research-draft.tex').read_bytes();pdf=(D/'final/second-research-draft.pdf').read_bytes()
assert identity(source)==checks['manuscript'] and identity(pdf)==checks['pdf']
assert checks['native_compile_success'] and checks['visual_review_status']=='passed_all_11_pages'
assert (checks['content_pages'],checks['reference_pages'],checks['appendices'])==(10,1,0)
checklist=(R/'docs/TACL_SUBMISSION_CHECKLIST_V122.txt').read_bytes()
response=(R/'docs/REVIEW_RESPONSE_V122.txt').read_bytes()
plan=(R/'docs/TACL_REVISION_EVIDENCE_PLAN_V122.txt').read_bytes()
reference=(R/'validation/v122_reference_audit.json').read_bytes()
readme=b'''TACL manuscript build V122, 29 October 2026

main.tex is the same standalone source open in the Codex editor. It embeds the
unmodified official tacl2021v1.sty and all fifteen references. The separate style
copy is identical. Native compilation passes. The delivered PDF is an independent
Tectonic 0.17.0 export: ten content pages, one references page, no appendices.
No font, margin, line-spacing or title-box reduction was used to meet the limit.

This is an editorial/theory revision with generated correctness checks, not a
completed empirical TACL revision. Read REVIEW_RESPONSE_V122.txt and the evidence
plan: matched-target quality, minimal cold baseline and broader operating-range
measurements remain pending. No new experiment has been launched or reported.

This ZIP is an editable author-side build package, not a TACL review supplement.
The full author evidence package is separate. TACL disallows external review
supplements. No upload or submission was performed. Author eligibility/history,
consent, release terms and metadata remain unverified.
'''
source_payload={'main.tex':source,'tacl2021v1.sty':(D/'tacl2021v1.sty').read_bytes(),'README.txt':readme,'TACL_SUBMISSION_CHECKLIST.txt':checklist,'REVIEW_RESPONSE_V122.txt':response,'TACL_REVISION_EVIDENCE_PLAN_V122.txt':plan,'REFERENCE_AUDIT.json':reference}
source_payload['MANIFEST.json']=enc({n:identity(b) for n,b in source_payload.items()})
old_path=O/'second-development-review-v119.zip'
old_report=json.loads((R/'validation/v119_development_bundle.json').read_bytes());assert identity(old_path.read_bytes())==old_report['archive']
with zipfile.ZipFile(old_path) as z:old={Path(n).name:z.read(n) for n in z.namelist()}
for n,h in json.loads(old['MANIFEST.json']).items():assert identity(old[n])==h
payload={n:b for n,b in old.items() if n.endswith('.zip')};assert len(payload)==14
payload.update({'second-research-draft.tex':source,'second-tacl-submission.pdf':pdf,
 'TACL_SUBMISSION_CHECKLIST.txt':checklist,'verify_review_bundle.py':old['verify_review_bundle.py'],
 'REVIEW_RESPONSE_V122.txt':response,'TACL_REVISION_EVIDENCE_PLAN_V122.txt':plan,
 'REFERENCE_AUDIT.json':reference,
 'README.txt':b'''Second author-side evidence and revision checkpoint V122

The revised manuscript has ten content pages and one references page, no appendix.
Native compilation and independent rendered-PDF checks pass. This checkpoint adds
an archive-width coefficient bound, numerical specification and installation
sensitivity, but the substantial empirical revision remains unfinished. Consult
REVIEW_RESPONSE_V122.txt and TACL_REVISION_EVIDENCE_PLAN_V122.txt before submission.

All fourteen historical evidence/source ZIP components, including failures and
negative results, are byte-identical. The unchanged portable verifier covers 1,322
historical source/protocol copies plus the supplied-byte manifest. It is not a
fresh empirical reproduction and does not independently re-audit model binaries.

Extract this archive into a fresh directory. With standard Python 3:
python3 verify_review_bundle.py PATH_TO_EXTRACTED_DIRECTORY

Additional small generated checks are provided as flat files. From that extracted
directory, run check_mathematics_v121.py using Python 3 standard libraries, then
review_response_checks_v122.py with Python 3 and NumPy (validated here with Python
3.9.6 and NumPy 1.26.3). Both emit JSON results beside themselves. The V122 checker
loads only named AST functions from low_rank_certified.py and rational helpers
from check_mathematics_v121.py. It reads E16_comparison_and_costs.json for storage
arithmetic. Input hashes and runtime metadata appear in v122_generated_checks.json.
These are finite generated rational/Python tests, not Linux native qualification,
production transaction abort tests, model experiments or formal verification.

The original inputs/source/runtime acquisition and reuse boundaries remain in the
historical components. A complete clean empirical reproduction is still pending.
The first thirteen primary bibliography checks are inherited from V121; Rump and
Shewchuk were additionally verified for V122, along with all fifteen final links.

This archive is for authors. TACL disallows external review supplements and links
to them. Do not upload this evidence package with the review PDF. Full indirect
anonymity and author eligibility/history/consent are not established. Own-source
release licensing remains an author decision. No raw corpus, weights, runtime
binaries or credentials are added. No submission or new cluster job was made.
'''})
for rel in ['validation/check_mathematics_v121.py','validation/v121_math_audit.json','validation/review_response_checks_v122.py','validation/v122_generated_checks.json','src/low_rank_certified.py','reports/review-service-v70/E16_comparison_and_costs.json']:
 payload[Path(rel).name]=(R/rel).read_bytes()
payload['MANIFEST.json']=enc({n:identity(b) for n,b in sorted(payload.items())})
with tempfile.TemporaryDirectory(prefix='second-v122-check-') as td:
 root=Path(td)
 for n,b in payload.items():(root/n).write_bytes(b)
 p=subprocess.run([sys.executable,'-I','-B',str(root/'verify_review_bundle.py'),str(root)],capture_output=True,text=True,timeout=30)
 assert p.returncode==0,p.stderr;verified=json.loads(p.stdout)
 for name,report in [('check_mathematics_v121.py','v121_math_audit.json'),('review_response_checks_v122.py','v122_generated_checks.json')]:
  p=subprocess.run([sys.executable,'-I','-B',str(root/name)],capture_output=True,text=True,timeout=60)
  assert p.returncode==0,p.stderr
  assert json.loads((root/report).read_bytes())==json.loads(payload[report]),report
# Write deliverables only after successful extracted-only checks.
for dest,b in [(R/'reports/manuscript_v122.tex',source),(R/'reports/second_tacl_v122.pdf',pdf),(O/'second-tacl-submission.pdf',pdf)]:
 if dest==O/'second-tacl-submission.pdf':
  assert identity(dest.read_bytes())['sha256']=='b2c0374eeaa7259696dd4d384c17d35b20365c697d5dfed9575a6f80670778f0'
 else: assert not dest.exists(),dest
 dest.write_bytes(b)
source_zip=O/'second-tacl-source-v122.zip';archive(source_zip,'second-tacl-source-v122',source_payload)
full=O/'second-author-review-v122.zip';archive(full,'second-author-review-v122',payload)
assert all(payload[n]==b for n,b in old.items() if n.endswith('.zip'))
result=dict(schema='second-tacl-packages-v122',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 source_package=dict(path=str(source_zip),archive=identity(source_zip.read_bytes()),members=len(source_payload)),
 author_evidence_package=dict(path=str(full),archive=identity(full.read_bytes()),members=len(payload),unchanged_components=14,verified=verified),
 manuscript=identity(source),pdf=dict(path=str(O/'second-tacl-submission.pdf'),**identity(pdf)),
 generated_checks_reproduced_from_extracted_flat_files=True,clean_empirical_reproduction=False,
 no_new_empirical_result=True,original_sources_changed=False,source_package_is_review_supplement=False,
 author_evidence_is_review_supplement=False,submission_readiness_established=False,submission_performed=False)
(R/'validation/v122_packages.json').write_bytes(enc(result));print(json.dumps(result,indent=2))
