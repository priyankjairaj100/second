"""Clarify public provenance without changing any supplied scientific component."""
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
    prior = json.loads((R/'validation/v105_development_bundle.json').read_bytes())
    source = Path(prior['path'])
    assert info(source.read_bytes()) == prior['archive']
    target = W/'outputs/second-development-review-v105b.zip'
    report = R/'validation/v105b_development_bundle.json'
    assert not target.exists() and not report.exists()
    with zipfile.ZipFile(source) as z:
        payload = {Path(n).name: z.read(n) for n in z.namelist()}
        assert len(payload) == len(z.namelist()) == 15
    manifest = json.loads(payload['MANIFEST.json'])
    assert all(info(payload[n]) == e for n, e in manifest.items())
    old_readme = payload['README.txt'].decode()
    assert 'private mapping' in old_readme
    new_readme = old_readme.replace('checkpoint V105,', 'checkpoint V105b,').replace('private mapping', 'derivation map')
    new_readme += '''
Provenance clarification, V105b:
The reporting repository is public and contains the source derivation maps.
Those maps are excluded from these review components, but are not private.
Earlier component text calling a mapping "private" refers to its exclusion
from that component; it must not be read as a repository-access guarantee.
Source text, hashes and public history may identify the project. This bundle
is not verified anonymous. All ten components and the manuscript are unchanged
from V105. This clarification neither removes public history nor changes access.
'''
    payload['README.txt'] = new_readme.encode()
    assert all(info(payload[n]) == e for n, e in manifest.items() if n != 'README.txt')
    payload['MANIFEST.json'] = enc({n: info(b) for n, b in sorted(payload.items()) if n != 'MANIFEST.json'})
    zip_payload(target, 'second-development-review-v105b', payload)
    with zipfile.ZipFile(target) as z:
        assert {Path(n).name: z.read(n) for n in z.namelist()} == payload
    with tempfile.TemporaryDirectory(prefix='second-v105b-') as temporary:
        root = Path(temporary)
        for n, b in payload.items():
            (root/n).write_bytes(b)
        checked = subprocess.run([sys.executable, '-I', '-B', str(root/'verify_review_bundle.py'), str(root)],
            capture_output=True, text=True, timeout=30)
        assert checked.returncode == 0, checked.stderr
        verified = json.loads(checked.stdout)
    result = dict(schema='development-review-bundle-v105b', path=str(target), archive=info(target.read_bytes()),
        predecessor_archive=prior['archive'], manifest=json.loads(payload['MANIFEST.json']),
        components=10, members=15, unchanged_v105_components=10, unchanged_manuscript=True,
        verifier_unchanged=True, verified=verified, roundtrip_bytes_verified=True,
        source=info(payload['second-research-draft.tex']), native_compile_success=prior['native_compile_success'],
        rendered_layout_verified=False, submission_ready=False, full_anonymity_verified=False,
        repository_public=True, derivation_maps_public=True, disclosure_only=True,
        prior_validation='validation/v105_development_bundle.json')
    report.write_bytes(enc(result))
    print(json.dumps({k: result[k] for k in ('path', 'archive', 'unchanged_v105_components', 'verified')}))


if __name__ == '__main__':
    main()
