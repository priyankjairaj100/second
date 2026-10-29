"""Package the TACL rewrite; do not alter or execute any research component."""
import hashlib,json,zipfile,subprocess,sys,tempfile,datetime
from pathlib import Path
R=Path(__file__).resolve().parents[1]
W=Path('/Users/priyankjairaj/Documents/Codex/2026-10-10/see-i-am-working-on-a-2')
D=W/'work/tacl-rewrite-v120';O=W/'outputs'
def identity(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def enc(x):return (json.dumps(x,indent=2,sort_keys=True)+'\n').encode()
def archive(path,prefix,payload):
 assert not path.exists(),path
 with zipfile.ZipFile(path,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for n,b in sorted(payload.items()):
   zi=zipfile.ZipInfo(prefix+'/'+n,(2026,10,28,0,0,0));zi.compress_type=zipfile.ZIP_DEFLATED;zi.external_attr=0o100644<<16;z.writestr(zi,b)
 with zipfile.ZipFile(path) as z:assert {Path(n).name:z.read(n) for n in z.namelist()}==payload
checks=json.loads((R/'validation/v120_manuscript_checks.json').read_bytes())
source=(O/'second-research-draft.tex').read_bytes();pdf=(D/'final/second-research-draft.pdf').read_bytes()
assert identity(source)==checks['manuscript'] and identity(pdf)==checks['pdf']
assert checks['native_compile_success'] and checks['visual_review_status']=='passed_all_11_pages'
assert (checks['content_pages'],checks['reference_pages'],checks['appendices'])==(10,1,0)
for dest,b in [(R/'reports/manuscript_v120.tex',source),(R/'reports/second_tacl_v120.pdf',pdf),(O/'second-tacl-submission.pdf',pdf)]:
 assert not dest.exists(),dest;dest.write_bytes(b)
checklist=(R/'docs/TACL_SUBMISSION_CHECKLIST_V120.txt').read_bytes()
readme=b'''TACL manuscript build, V120, 28 October 2026

main.tex is the same standalone source open in the Codex editor. It embeds the
unmodified official tacl2021v1.sty and all references. The separate style copy is
identical. Compile main.tex using the native Codex compiler or an existing TeX
installation with the declared packages. The delivered PDF is an independent
Tectonic 0.17.0 export of this source: 10 content pages, 1 references page, no appendix.
No font, margin, line-spacing or title-box reduction was used to meet the limit.

This ZIP is an editable author-side build package, not a TACL review supplement.
The separately delivered second-tacl-submission.pdf is the review-format artifact.
Consult TACL_SUBMISSION_CHECKLIST.txt for pending author eligibility/history facts
and upload naming after a submission number is assigned. No upload was performed.
The frozen experimental source/evidence archive is maintained separately.
'''
source_payload={'main.tex':source,'tacl2021v1.sty':(D/'tacl2021v1.sty').read_bytes(),'README.txt':readme,'TACL_SUBMISSION_CHECKLIST.txt':checklist}
source_payload['MANIFEST.json']=enc({n:identity(b) for n,b in source_payload.items()})
source_zip=O/'second-tacl-source-v120.zip';archive(source_zip,'second-tacl-source-v120',source_payload)
old_path=O/'second-development-review-v119.zip'
old_report=json.loads((R/'validation/v119_development_bundle.json').read_bytes());assert identity(old_path.read_bytes())==old_report['archive']
with zipfile.ZipFile(old_path) as z:old={Path(n).name:z.read(n) for n in z.namelist()}
for n,h in json.loads(old['MANIFEST.json']).items():assert identity(old[n])==h
payload={n:b for n,b in old.items() if n.endswith('.zip')};assert len(payload)==14
payload.update({'second-research-draft.tex':source,'second-tacl-submission.pdf':pdf,
 'TACL_SUBMISSION_CHECKLIST.txt':checklist,'verify_review_bundle.py':old['verify_review_bundle.py'],
 'README.txt':b'''Second author-side reproducibility checkpoint V120

The manuscript has been rewritten for TACL and rendered: 10 content pages plus
1 reference page, no appendices. All core proofs are in the main paper. Native
compilation and independent PDF export pass. The original 14 evidence/source
components, including every prior failure and negative result, are byte-identical.
The 1,322 source/protocol copies remain covered by the unchanged portable verifier.
No new experiment, audit replay or consumed registration was run.

Extract into a fresh directory, then use standard Python3:
python verify_review_bundle.py PATH_TO_EXTRACTED_DIRECTORY
The checker verifies supplied bytes, source coverage and scoped arithmetic.
It does not rerun numerical work, re-audit original model binaries or establish
full external-input reproduction. Source/input/runtime acquisition and reuse
boundaries remain in the original components. Their historical scope flags and
README checkpoints retain their original meanings.

TACL does not allow external review supplements. This complete archive is for the
authors; do not upload it or link it as a review supplement. Use the standalone
PDF for review, after author eligibility, history, consent and metadata checks.
Hashes and historical public code may reveal identity; full indirect anonymity
is not established. Source release licensing remains unassigned. No raw corpus,
model/runtime payload or credential is added. No submission was made.
'''})
payload['MANIFEST.json']=enc({n:identity(b) for n,b in sorted(payload.items())})
with tempfile.TemporaryDirectory(prefix='second-v120-check-') as td:
 root=Path(td)
 for n,b in payload.items():(root/n).write_bytes(b)
 p=subprocess.run([sys.executable,'-I','-B',str(root/'verify_review_bundle.py'),str(root)],capture_output=True,text=True,timeout=30)
 assert p.returncode==0,p.stderr;verified=json.loads(p.stdout)
full=O/'second-author-review-v120.zip';archive(full,'second-author-review-v120',payload)
assert all(payload[n]==b for n,b in old.items() if n.endswith('.zip'))
result=dict(schema='second-tacl-packages-v120',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 source_package=dict(path=str(source_zip),archive=identity(source_zip.read_bytes()),members=len(source_payload)),
 author_evidence_package=dict(path=str(full),archive=identity(full.read_bytes()),members=len(payload),unchanged_components=14,verified=verified),
 manuscript=identity(source),pdf=dict(path=str(O/'second-tacl-submission.pdf'),**identity(pdf)),
 no_new_empirical_result=True,original_sources_changed=False,source_package_is_review_supplement=False,
 author_evidence_is_review_supplement=False,submission_performed=False)
(R/'validation/v120_packages.json').write_bytes(enc(result));print(json.dumps(result,indent=2))
