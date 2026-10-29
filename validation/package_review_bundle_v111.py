"""Preserve prior components; add scoped E19 evidence and corresponding source."""
import datetime,io,json,subprocess,sys,tempfile,zipfile
from pathlib import Path
from validation.build_review_source_v69 import info,enc
from validation.package_review_bundle_v105 import zip_payload
R=Path(__file__).resolve().parents[1]
W=Path('/Users/priyankjairaj/Documents/Codex/2026-10-10/see-i-am-working-on-a-2')


def build():
    target=W/'outputs/second-development-review-v111.zip';report=R/'validation/v111_development_bundle.json'
    assert not target.exists() and not report.exists()
    prior=json.loads((R/'validation/v106_development_bundle.json').read_bytes());old_path=Path(prior['path'])
    assert info(old_path.read_bytes())==prior['archive']
    with zipfile.ZipFile(old_path) as z:old={Path(n).name:z.read(n) for n in z.namelist()}
    old_manifest=json.loads(old['MANIFEST.json']);assert all(info(old[n])==e for n,e in old_manifest.items())
    payload={n:b for n,b in old.items() if n.endswith('.zip')};assert len(payload)==10
    additions=['development-transfer-source-v111.zip','development-diagnostic-evidence-v111.zip']
    for n in additions:payload[n]=(R/'reports'/n).read_bytes()
    source=(W/'outputs/second-research-draft.tex').read_bytes();checks=json.loads((R/'validation/v111_manuscript_checks.json').read_bytes())
    assert checks['native_compile_success'] and checks['manuscript']==info(source)==info((R/'reports/manuscript_v111.tex').read_bytes())
    payload.update({'second-research-draft.tex':source,
        'RESPONSIBLE_NLP_CHECKLIST_DRAFT.txt':(R/'reports/RESPONSIBLE_NLP_CHECKLIST_V111.txt').read_bytes(),
        'verify_review_bundle.py':(R/'validation/verify_review_bundle_v111.py').read_bytes(),
        'README.txt':b'''Second development review checkpoint V111,27 October2026

Verified V72/V89 science remains, including mixed latency. E19 now preserves
the failed first GPT2 matched request and the separate successful token-stage
diagnostic. The latter certifies2359296stage codes but supplies no full-model
comparison, independent fresh stage oracle, speed comparison or quality result.
The manuscript compiles in its existing native editor. Rendered layout and final
venue/cycle/category remain unresolved: this is not submission-ready.

All ten V106 evidence/source/notices/selection/guide components remain byte-identical.
Two additions supply E19 derivatives and296 source copies, extending the prior930
to1226 source/protocol files from the executed V110 archive. Sixteen execution-
specific receipts are omitted and enumerated; originals remain in the public
research repository. Public derivation maps and code/hashes can link identities.
Source adaptation is reversible text substitution, not qualified execution.

The separately prepared V111 point-policy screen is not an empirical result and
is not represented as executed in these components. A connection timeout blocked
its upload. New full-model evidence requires actual qualification,16 requests,
two fresh complete oracles, both audits and terminal accounting under original
remaining caps. No consumed historical job may be repeated.

Extract into a new directory and run with standard Python3:
python verify_review_bundle.py PATH_TO_EXTRACTED_BUNDLE_DIRECTORY
This checks all12 components, safe regular ZIP members,1226-file source coverage,
and scoped E19 arithmetic. It does not repeat certification or model/state/loss
comparisons. The older reproduction guide retains its original scope. External
input/runtime acquisition and complete reproduction remain unverified.

No model/corpus/runtime binaries, raw token bodies, identity mapping or credentials
are added. Project source has no newly assigned license. The checklist preserves
explained No answers and expands evidence/compute/source scope; policy fields
require review when venue/cycle is selected. No author attestation or conference
submission occurred. Existing source, failures, cancellations, exclusions and
unknown debits remain. Do not add overlapping CPU clocks.
'''})
    payload['MANIFEST.json']=enc({n:info(b) for n,b in sorted(payload.items())});assert len(payload)==17
    with tempfile.TemporaryDirectory(prefix='second-v111-bundle-') as temporary:
        root=Path(temporary)
        for n,b in payload.items():(root/n).write_bytes(b)
        def invoke():return subprocess.run([sys.executable,'-I','-B',str(root/'verify_review_bundle.py'),str(root)],cwd=root,capture_output=True,text=True,timeout=30)
        clean=invoke();assert clean.returncode==0,clean.stderr;verified=json.loads(clean.stdout)
        victim=root/additions[0];victim.write_bytes(payload[victim.name]+b'changed');corrupt=invoke().returncode!=0
        victim.unlink();missing=invoke().returncode!=0;victim.write_bytes(payload[victim.name])
        (root/'unexpected.txt').write_text('unexpected');unexpected=invoke().returncode!=0;(root/'unexpected.txt').unlink()
        def changed_inner(component,name,transform):
            with zipfile.ZipFile(io.BytesIO(payload[component])) as z:
                prefix=z.namelist()[0].split('/')[0];inner={'/'.join(Path(n).parts[1:]):z.read(n) for n in z.namelist()}
            inner[name]=transform(inner[name]);manifest=json.loads(inner['MANIFEST.json']);manifest[name]=info(inner[name]);inner['MANIFEST.json']=enc(manifest)
            (root/component).unlink();zip_payload(root/component,prefix,inner)
            outer=json.loads(payload['MANIFEST.json']);outer[component]=info((root/component).read_bytes());(root/'MANIFEST.json').write_bytes(enc(outer))
            rejected=invoke().returncode!=0
            (root/component).write_bytes(payload[component]);(root/'MANIFEST.json').write_bytes(payload['MANIFEST.json']);return rejected
        coverage=changed_inner(additions[0],'research_v110/stage.py',lambda b:b+b'\n# altered copy\n')
        scope=changed_inner(additions[1],'results.json',lambda b:enc(dict(json.loads(b),full_model_transfer=True)))
        assert all((corrupt,missing,unexpected,coverage,scope));assert invoke().returncode==0
    zip_payload(target,'second-development-review-v111',payload)
    with zipfile.ZipFile(target) as z:assert {Path(n).name:z.read(n) for n in z.namelist()}==payload
    assert all(payload[n]==old[n] for n in old if n.endswith('.zip'))
    result=dict(schema='development-review-bundle-v111',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),path=str(target),archive=info(target.read_bytes()),
        manifest=json.loads(payload['MANIFEST.json']),members=17,components=12,unchanged_v106_components=10,verified=verified,
        corruption_rejected=corrupt,missing_rejected=missing,unexpected_rejected=unexpected,inconsistent_source_coverage_rejected=coverage,
        unsupported_full_model_transfer_claim_rejected=scope,roundtrip_bytes_verified=True,native_compile_success=True,source=info(source),
        rendered_layout_verified=False,new_transfer_result=False,source_originals_changed=False,full_reproduction_verified=False,new_pdf_created=False,submission_ready=False)
    report.write_bytes(enc(result));print(json.dumps({k:result[k] for k in ('path','archive','members','components','verified','submission_ready')},sort_keys=True))

if __name__=='__main__':build()
