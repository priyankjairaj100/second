"""Package the compiled manuscript revision with unchanged evidence components."""
import datetime
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


def build():
    target = W/'outputs/second-development-review-v117.zip'
    report = R/'validation/v117_development_bundle.json'
    assert not target.exists() and not report.exists()
    prior = json.loads((R/'validation/v116_development_bundle.json').read_bytes())
    old_path = Path(prior['path'])
    assert info(old_path.read_bytes()) == prior['archive']
    with zipfile.ZipFile(old_path) as archive:
        old = {Path(n).name: archive.read(n) for n in archive.namelist()}
        assert len(old) == len(archive.namelist()) == 18
    assert all(info(old[n]) == e for n, e in json.loads(old['MANIFEST.json']).items())
    payload = {n: b for n, b in old.items() if n.endswith('.zip')}
    assert len(payload) == 13
    source = (W/'outputs/second-research-draft.tex').read_bytes()
    checks = json.loads((R/'validation/v117_manuscript_checks.json').read_bytes())
    assert checks['native_compile_success'] and checks['manuscript'] == info(source)
    assert source == (R/'reports/manuscript_v117.tex').read_bytes()
    payload.update({
        'second-research-draft.tex': source,
        'RESPONSIBLE_NLP_CHECKLIST_DRAFT.txt': (R/'reports/RESPONSIBLE_NLP_CHECKLIST_V117.txt').read_bytes(),
        'verify_review_bundle.py': old['verify_review_bundle.py'],
        'README.txt': b'''Second development review checkpoint V117, 27 October 2026

The same manuscript now makes the feature-space certificate explicit in an
appendix: a reverse-LDL suffix identity connects the verified solve residual to
adaptive rounding coefficients, with the two standard ridge/SVD error bounds
used by the frozen implementation. No algorithm, numerical value, completion
guarantee or speed claim changes. Two obsolete directional references were fixed
after the earlier history relocation. Native compilation succeeds. Rendered
layout/PDF export and final venue/cycle/category remain unresolved. This is a
development review package, not a submission-ready artifact.

All thirteen V116 evidence/source/guide components and the portable verifier are
byte-identical. They cover 1322 source/protocol files, with 17 execution-specific
receipts omitted and enumerated. Verified V72/V89 evidence and E19's failed screen
and selected-stage diagnostic keep their original scopes. The new matched V112
experiment is still running. No new complete transfer, speed or quality result is
asserted here. Both fresh reconstructions, both audits and terminal accounting
remain required. Operational progress is recorded in the research repository.

Extract into a new directory and run with standard Python3:
python verify_review_bundle.py PATH_TO_EXTRACTED_BUNDLE_DIRECTORY
The check verifies supplied bytes, source coverage and diagnostic arithmetic.
It neither repeats empirical work nor qualifies path-adapted code for execution.
External-input/runtime acquisition and complete reproduction remain unverified.
Never rerun consumed historical launchers. All failed attempts, exclusions,
resource limits and historical unresolved debits remain preserved.

The checklist preserves its responses and refers to section names so that the
manuscript reorganization does not leave obsolete section numbers. Final policy
fields need review after venue selection; no author attestation is implied.
No model/runtime/corpus binaries, raw tokens, mapping or credentials are added.
Public source and hashes can reveal identity; anonymity is not established.
No project license was assigned and no conference submission occurred.
''',
    })
    payload['MANIFEST.json'] = enc({n: info(b) for n, b in sorted(payload.items())})
    with tempfile.TemporaryDirectory(prefix='second-v117-review-') as temporary:
        root = Path(temporary)
        for n, b in payload.items():
            (root/n).write_bytes(b)
        result = subprocess.run([sys.executable, '-I', '-B', str(root/'verify_review_bundle.py'), str(root)],
            cwd=root, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr
        verified = json.loads(result.stdout)
    zip_payload(target, 'second-development-review-v117', payload)
    with zipfile.ZipFile(target) as archive:
        assert {Path(n).name: archive.read(n) for n in archive.namelist()} == payload
    assert all(payload[n] == old[n] for n in payload if n.endswith('.zip'))
    result = dict(schema='development-review-bundle-v117',
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), path=str(target),
        archive=info(target.read_bytes()), manifest=json.loads(payload['MANIFEST.json']),
        members=len(payload), components=13, unchanged_v116_components=13,
        unchanged_portable_verifier=True, verified=verified, roundtrip_bytes_verified=True,
        manuscript=info(source), native_compile_success=True, rendered_layout_verified=False,
        new_empirical_result=False, original_research_sources_changed=False,
        full_reproduction_verified=False, submission_ready=False)
    report.write_bytes(enc(result))
    print(json.dumps({k: result[k] for k in ('path', 'archive', 'members', 'components', 'verified')}, sort_keys=True))


if __name__ == '__main__':
    build()
