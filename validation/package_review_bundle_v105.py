"""Preserve historical components and close the E18 source-coverage gap."""
import datetime
import io
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import zipfile
from validation.build_review_source_v69 import info, enc

R = Path(__file__).resolve().parents[1]
W = Path('/Users/priyankjairaj/Documents/Codex/2026-10-10/see-i-am-working-on-a-2')


def zip_payload(path, prefix, payload):
    with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, blob in sorted(payload.items()):
            entry = zipfile.ZipInfo(prefix+'/'+name, (2026, 10, 26, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            z.writestr(entry, blob, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def build():
    target = W/'outputs/second-development-review-v105.zip'
    report = R/'validation/v105_development_bundle.json'
    assert not target.exists() and not report.exists()
    old_report = json.loads((R/'validation/v98_development_bundle.json').read_bytes())
    old_path = Path(old_report['path'])
    assert info(old_path.read_bytes()) == old_report['archive']
    with zipfile.ZipFile(old_path) as z:
        old = {Path(n).name: z.read(n) for n in z.namelist()}
        assert len(old) == len(z.namelist()) == 13
    old_manifest = json.loads(old['MANIFEST.json'])
    assert all(info(old[n]) == e for n, e in old_manifest.items())
    payload = {n: b for n, b in old.items() if n.endswith('.zip')}
    assert len(payload) == 9
    extra = 'development-optimization-source-v105.zip'
    payload[extra] = (R/'reports'/extra).read_bytes()
    source = (W/'outputs/second-research-draft.tex').read_bytes()
    compile_report = json.loads((R/'validation/v105_manuscript_checks.json').read_bytes())
    assert compile_report['native_compile_success'] and compile_report['manuscript'] == info(source)
    assert source == (R/'reports/manuscript_v105.tex').read_bytes()
    payload['second-research-draft.tex'] = source
    payload['RESPONSIBLE_NLP_CHECKLIST_DRAFT.txt'] = (R/'reports/RESPONSIBLE_NLP_CHECKLIST_V105.txt').read_bytes()
    payload['verify_review_bundle.py'] = (R/'validation/verify_review_bundle_v105.py').read_bytes()
    payload['README.txt'] = b'''Second development review checkpoint V105,26 October2026

The manuscript retains the verified V72/V89 scientific findings, including mixed
optimization latency. The matched-model study is running; no new model-transfer,
speed or quality result is included. Native compilation succeeds; rendered
layout remains unverified after a preview-service startup failure. Venue/cycle
and final category remain unset. This is not a submission-ready package.

All nine V98 evidence/source/notices/selection/guide components are byte-identical.
The new optimization source supplement adds347 review copies to the unchanged583
base copies, covering930 source/protocol files from the executed V89 archive.
Four run-specific recovery receipts remain excluded and are identified in the
coverage manifest. E18 retains every outcome and the historical unknown debit.
Private strings are adapted in source copies only; original research bytes and
all one-use attempts remain immutable. Do not execute historical launchers.

Extract this ZIP into a new directory and run, with a standard Python3:
python verify_review_bundle.py PATH_TO_EXTRACTED_BUNDLE_DIRECTORY
This verifies all ten components, regular safe ZIP members and930-file source
coverage. The older reproduction guide retains its original scope. Neither check
repeats the empirical pipeline or qualifies adapted code as an executable copy.
External input/runtime acquisition and full reproduction remain unverified.

The checklist preserves its answers and updates compute/source scope. Its policy
fields require review after the final venue/cycle is chosen; it is not an author
attestation. No model/runtime/corpus binaries, raw token bodies, private mapping
or credentials are added. Known direct-identity markers were checked, but hashes,
job IDs and code can permit indirect linkage. Full anonymity is not established.
Project-source release terms remain unassigned. No conference submission occurred.
'''
    payload['MANIFEST.json'] = enc({n: info(b) for n, b in sorted(payload.items())})
    assert len(payload) == 15
    with tempfile.TemporaryDirectory(prefix='second-v105-review-') as temporary:
        root = Path(temporary)
        for n, b in payload.items():
            (root/n).write_bytes(b)
        def invoke():
            return subprocess.run([sys.executable, '-I', '-B', str(root/'verify_review_bundle.py'), str(root)],
                cwd=root, capture_output=True, text=True, timeout=30)
        clean = invoke()
        assert clean.returncode == 0, clean.stderr
        verified = json.loads(clean.stdout)
        victim = root/extra
        victim.write_bytes(payload[extra]+b'changed')
        corrupt = invoke().returncode != 0
        victim.unlink()
        missing = invoke().returncode != 0
        victim.write_bytes(payload[extra])
        (root/'unexpected.txt').write_text('unexpected')
        unexpected = invoke().returncode != 0
        (root/'unexpected.txt').unlink()
        # Simulate an internally rehashed source edit while leaving the independently
        # declared source-coverage commitment unchanged. It must still be rejected.
        with zipfile.ZipFile(io.BytesIO(payload[extra])) as z:
            inner = {n: z.read(n) for n in z.namelist()}
        changed_name = 'optimization-source/research_v76/token_neighbors.py'
        inner[changed_name] += b'\n# changed review copy\n'
        inner_manifest = json.loads(inner['optimization-source/MANIFEST.json'])
        inner_manifest[changed_name.removeprefix('optimization-source/')] = info(inner[changed_name])
        inner['optimization-source/MANIFEST.json'] = enc(inner_manifest)
        victim.unlink()
        zip_payload(victim, 'optimization-source', {n.removeprefix('optimization-source/'): b for n, b in inner.items()})
        changed_manifest = json.loads(payload['MANIFEST.json'])
        changed_manifest[extra] = info(victim.read_bytes())
        (root/'MANIFEST.json').write_bytes(enc(changed_manifest))
        inconsistent_coverage = invoke().returncode != 0
        assert corrupt and missing and unexpected and inconsistent_coverage
    zip_payload(target, 'second-development-review-v105', payload)
    with zipfile.ZipFile(target) as z:
        assert {Path(n).name: z.read(n) for n in z.namelist()} == payload
    result = dict(schema='development-review-bundle-v105', created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        path=str(target), archive=info(target.read_bytes()), manifest=json.loads(payload['MANIFEST.json']),
        members=15, components=10, unchanged_v98_components=9, verified=verified,
        corruption_rejected=corrupt, missing_rejected=missing, unexpected_rejected=unexpected,
        inconsistent_source_coverage_rejected=inconsistent_coverage, roundtrip_bytes_verified=True,
        native_compile_success=True, source=info(source), rendered_layout_verified=False,
        new_transfer_result=False, source_originals_changed=False, full_reproduction_verified=False,
        new_pdf_created=False, submission_ready=False)
    report.write_bytes(enc(result))
    print(json.dumps({k: result[k] for k in ('archive', 'members', 'components', 'unchanged_v98_components', 'verified', 'submission_ready')}, sort_keys=True))


if __name__ == '__main__':
    build()
