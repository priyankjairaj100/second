"""Replace one inaccurate privacy adjective; preserve all evidence components."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
from validation.build_review_source_v69 import info, enc
from validation.package_review_bundle_v105 import zip_payload

R = Path(__file__).resolve().parents[1]
W = Path('/Users/priyankjairaj/Documents/Codex/2026-10-10/see-i-am-working-on-a-2')


def main():
    prior = json.loads((R/'validation/v105b_development_bundle.json').read_bytes())
    path = Path(prior['path'])
    assert info(path.read_bytes()) == prior['archive']
    target = W/'outputs/second-development-review-v106.zip'
    report = R/'validation/v106_development_bundle.json'
    assert not target.exists() and not report.exists()
    with zipfile.ZipFile(path) as z:
        payload = {Path(n).name: z.read(n) for n in z.namelist()}
        assert len(payload) == len(z.namelist()) == 15
    manifest = json.loads(payload['MANIFEST.json'])
    assert all(info(payload[n]) == e for n, e in manifest.items())
    new = (W/'outputs/second-research-draft.tex').read_bytes()
    checks = json.loads((R/'validation/v106_manuscript_checks.json').read_bytes())
    assert checks['native_compile_success'] and checks['manuscript'] == info(new)
    assert (R/'reports/manuscript_v106.tex').read_bytes() == new
    old = payload['second-research-draft.tex']
    before = b'empirical pipeline. Private source mappings, raw corpus/token bodies and'
    after = b'empirical pipeline. Source derivation maps, raw corpus/token bodies and'
    assert old.count(before) == 1 and old.replace(before, after) == new
    payload['second-research-draft.tex'] = new
    readme = payload['README.txt'].decode().replace('checkpoint V105b,', 'checkpoint V106,')
    before = 'All ten components and the manuscript are unchanged\nfrom V105.'
    after = ('All ten components are unchanged from V105. V106 corrects only the\n'
             'manuscript phrase "Private source mappings" to "Source derivation maps".\n'
             'Scientific statements, numerical results and the checklist are unchanged.')
    assert readme.count(before) == 1
    payload['README.txt'] = readme.replace(before, after).encode()
    changed = {'README.txt', 'second-research-draft.tex'}
    assert all(info(payload[n]) == e for n, e in manifest.items() if n not in changed)
    payload['MANIFEST.json'] = enc({n: info(b) for n, b in sorted(payload.items()) if n != 'MANIFEST.json'})
    zip_payload(target, 'second-development-review-v106', payload)
    with zipfile.ZipFile(target) as z:
        assert {Path(n).name: z.read(n) for n in z.namelist()} == payload
    with tempfile.TemporaryDirectory(prefix='second-v106-') as temporary:
        root = Path(temporary)
        for n, b in payload.items():
            (root/n).write_bytes(b)
        checked = subprocess.run([sys.executable, '-I', '-B', str(root/'verify_review_bundle.py'), str(root)],
            capture_output=True, text=True, timeout=30)
        assert checked.returncode == 0, checked.stderr
        verified = json.loads(checked.stdout)
    result = dict(schema='development-review-bundle-v106', path=str(target), archive=info(target.read_bytes()),
        predecessor_archive=prior['archive'], manifest=json.loads(payload['MANIFEST.json']),
        components=10, members=15, unchanged_evidence_components=10, verifier_unchanged=True,
        verified=verified, roundtrip_bytes_verified=True, source=info(new), native_compile_success=True,
        manuscript_checks='validation/v106_manuscript_checks.json', scientific_content_unchanged=True,
        rendered_layout_verified=False, submission_ready=False, full_anonymity_verified=False,
        repository_public=True, derivation_maps_public=True, disclosure_only=True,
        prior_validation='validation/v105b_development_bundle.json')
    report.write_bytes(enc(result))
    print(json.dumps({k: result[k] for k in ('path', 'archive', 'unchanged_evidence_components', 'verified')}))


if __name__ == '__main__':
    main()
