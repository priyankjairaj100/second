"""Preserve V111 science; add qualified point-policy source inspection copies."""
import datetime
import io
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from validation.build_review_source_v69 import info, enc
from validation.package_review_bundle_v105 import zip_payload

R = Path(__file__).resolve().parents[1]
W = Path('/Users/priyankjairaj/Documents/Codex/2026-10-10/see-i-am-working-on-a-2')


def build():
    target = W/'outputs/second-development-review-v114.zip'
    report = R/'validation/v114_development_bundle.json'
    assert not target.exists() and not report.exists()
    prior = json.loads((R/'validation/v111_development_bundle.json').read_bytes())
    old_path = Path(prior['path'])
    assert info(old_path.read_bytes()) == prior['archive']
    with zipfile.ZipFile(old_path) as z:
        old = {Path(n).name: z.read(n) for n in z.namelist()}
        assert len(old) == len(z.namelist())
    old_manifest = json.loads(old['MANIFEST.json'])
    assert all(info(old[n]) == e for n, e in old_manifest.items())
    payload = {n: b for n, b in old.items() if n.endswith('.zip')}
    assert len(payload) == 12
    extra = 'development-point-policy-source-v114.zip'
    payload[extra] = (R/'reports'/extra).read_bytes()
    source = (W/'outputs/second-research-draft.tex').read_bytes()
    checks = json.loads((R/'validation/v111_manuscript_checks.json').read_bytes())
    assert checks['native_compile_success'] and checks['manuscript'] == info(source)
    assert source == old['second-research-draft.tex'] == (R/'reports/manuscript_v111.tex').read_bytes()
    payload.update({'second-research-draft.tex': source,
        'RESPONSIBLE_NLP_CHECKLIST_DRAFT.txt': (R/'reports/RESPONSIBLE_NLP_CHECKLIST_V114.txt').read_bytes(),
        'verify_review_bundle.py': (R/'validation/verify_review_bundle_v114.py').read_bytes(),
        'README.txt': b'''Second development review checkpoint V114,27 October2026

The V111 manuscript and all twelve previous components remain byte-identical.
They preserve verified V72/V89 findings, mixed latency, and E19's failed matched
screen and selected-stage diagnostic. The same manuscript previously compiled
in the native editor. Rendered layout and final venue/cycle/category remain
unresolved. This is not a submission-ready package.

One additional component supplies96 source/protocol/test copies from the exact
qualified V112 archive. Together with the unchanged1226 copies, source coverage
now reaches1322 files. Seventeen execution receipts are excluded and enumerated;
their originals and derivation maps remain in the public research repository.
The original source passed318 Linux checks. Its matched numerical chain is running
at this checkpoint; no new complete model-transfer, speed or quality result is
supplied. Source coverage and tests alone do not imply scientific success.

Extract into a new directory and run with standard Python3:
python verify_review_bundle.py PATH_TO_EXTRACTED_BUNDLE_DIRECTORY
This verifies all13 components, regular safe ZIP members,1322-file source
coverage, preserved E19 arithmetic and the pending-result scope. It does not
repeat the numerical pipeline or qualify path-adapted copies for execution.
The older reproduction guide retains its scope; external input/runtime acquisition
and complete reproduction remain unverified. Do not run historical launchers or
retry consumed jobs. Both fresh oracles, both audits and terminal accounting of
the active screen remain required before any new model claim.

No model/corpus/runtime binaries, raw token bodies, identity mapping or credentials
are added. Small generated fixtures remain. Public code and hashes can reveal
identity; anonymity is not established. No project license is newly assigned.
The checklist retains its answers and updates source coverage only. Venue policy
fields require review after selection; no author attestation or submission occurred.
All failures, exclusions, unknown debits and earlier evidence remain preserved.
'''})
    payload['MANIFEST.json'] = enc({n: info(b) for n, b in sorted(payload.items())})
    assert len(payload) == 18
    with tempfile.TemporaryDirectory(prefix='second-v114-bundle-') as temporary:
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

        def changed_inner(name, transform):
            with zipfile.ZipFile(io.BytesIO(payload[extra])) as z:
                prefix = z.namelist()[0].split('/')[0]
                inner = {'/'.join(Path(n).parts[1:]): z.read(n) for n in z.namelist()}
            inner[name] = transform(inner[name])
            manifest = json.loads(inner['MANIFEST.json'])
            manifest[name] = info(inner[name])
            inner['MANIFEST.json'] = enc(manifest)
            (root/extra).unlink()
            zip_payload(root/extra, prefix, inner)
            outer = json.loads(payload['MANIFEST.json'])
            outer[extra] = info((root/extra).read_bytes())
            (root/'MANIFEST.json').write_bytes(enc(outer))
            rejected = invoke().returncode != 0
            (root/extra).write_bytes(payload[extra])
            (root/'MANIFEST.json').write_bytes(payload['MANIFEST.json'])
            return rejected

        coverage = changed_inner('research_v112/closure.py', lambda b: b+b'\n# altered copy\n')
        transfer = changed_inner('SOURCE_COVERAGE.json', lambda b: enc(dict(json.loads(b), full_model_transfer_result=True)))
        speed = changed_inner('SOURCE_COVERAGE.json', lambda b: enc(dict(json.loads(b), general_speedup_result=True)))
        assert all((corrupt, missing, unexpected, coverage, transfer, speed))
        assert invoke().returncode == 0
    zip_payload(target, 'second-development-review-v114', payload)
    with zipfile.ZipFile(target) as z:
        assert {Path(n).name: z.read(n) for n in z.namelist()} == payload
    assert all(payload[n] == old[n] for n in old if n.endswith('.zip'))
    result = dict(schema='development-review-bundle-v114',
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), path=str(target),
        archive=info(target.read_bytes()), manifest=json.loads(payload['MANIFEST.json']),
        members=18, components=13, unchanged_v111_components=12, verified=verified,
        corruption_rejected=corrupt, missing_rejected=missing, unexpected_rejected=unexpected,
        inconsistent_source_coverage_rejected=coverage, unsupported_full_model_transfer_claim_rejected=transfer,
        unsupported_general_speedup_claim_rejected=speed, roundtrip_bytes_verified=True,
        manuscript_unchanged=True, prior_native_compile_success=True, source=info(source),
        prior_manuscript_validation='validation/v111_manuscript_checks.json',
        rendered_layout_verified=False, new_transfer_result=False, source_originals_changed=False,
        full_reproduction_verified=False, new_pdf_created=False, submission_ready=False)
    report.write_bytes(enc(result))
    print(json.dumps({k: result[k] for k in ('path', 'archive', 'members', 'components', 'verified', 'submission_ready')}, sort_keys=True))


if __name__ == '__main__':
    build()
