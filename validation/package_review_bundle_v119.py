"""Package the closed matched evidence and compiled manuscript; retain all prior components."""
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
    target = W/'outputs/second-development-review-v119.zip'
    report = R/'validation/v119_development_bundle.json'
    assert not target.exists() and not report.exists()
    prior = json.loads((R/'validation/v117_development_bundle.json').read_bytes())
    old_path = Path(prior['path'])
    assert info(old_path.read_bytes()) == prior['archive']
    with zipfile.ZipFile(old_path) as archive:
        old = {Path(n).name: archive.read(n) for n in archive.namelist()}
        assert len(old) == len(archive.namelist()) == 18
    assert all(info(old[n]) == e for n, e in json.loads(old['MANIFEST.json']).items())
    payload = {n: b for n, b in old.items() if n.endswith('.zip')}
    assert len(payload) == 13
    evidence = json.loads((R/'validation/v119_matched_evidence.json').read_bytes())
    component = (R/'reports/development-matched-evidence-v119.zip').read_bytes()
    assert evidence['archive'] == info(component) and evidence['requests'] == 16
    assert evidence['status'] == 'packaged_closed_matched_evidence'
    payload['development-matched-evidence-v119.zip'] = component
    source = (W/'outputs/second-research-draft.tex').read_bytes()
    checks = json.loads((R/'validation/v119_manuscript_checks.json').read_bytes())
    assert checks['native_compile_success'] and checks['manuscript'] == info(source)
    assert source == (R/'reports/manuscript_v119.tex').read_bytes()
    payload.update({
        'second-research-draft.tex': source,
        'RESPONSIBLE_NLP_CHECKLIST_DRAFT.txt': (R/'reports/RESPONSIBLE_NLP_CHECKLIST_V119.txt').read_bytes(),
        'verify_review_bundle.py': (R/'validation/verify_review_bundle_v119.py').read_bytes(),
        'README.txt': b'''Second development review checkpoint V119, 27 October 2026

E20 adds the closed matched point-token screen on DistilGPT2 and GPT2. All 16
complete model/state/trust comparisons match fresh reconstruction under both
completed cluster audits and the frozen terminal. Every request row, both
retained endpoints, reference/optimized implementations, complete host timings,
source access, fallback and storage observations remain in the new component.
No endpoint is selected for favorable performance. Each timing is one observation;
related checkpoint correctness is distinct from stable latency, cross-architecture
generality and predictive quality. No new quality evaluation was performed.

The same manuscript integrates that evidence and compiles natively. Its conclusion
must be read with the reported losses and scope limits. Earlier quality and speed
findings, failed matched certification and stage diagnostic remain explicit.
All 13 prior evidence/source components are byte-identical. Their historical scope
flags remain descriptions of those earlier components; E20 separately records the
completed matched evidence. The source components still provide 1,322 source/protocol
copies, with 17 execution-specific receipts omitted and enumerated. No path-adapted
runtime or new independent empirical reproduction is claimed.

Extract into a new directory and run with standard Python3:
python verify_review_bundle.py PATH_TO_EXTRACTED_BUNDLE_DIRECTORY
The updated portable checker verifies supplied bytes, source coverage and scoped
arithmetic across 14 components. It does not execute numerical work or re-audit the
original model binaries. The original source/runtime/input requirements remain
in the reproduction guide and qualified source supplements. Do not rerun consumed
historical launchers. All prior costs and unresolved reservations are preserved.

Rendered layout/PDF export and final venue/cycle/category remain unresolved. The
existing preview-service startup failure is recorded. This development review
package is not a submission-ready artifact. Author-controlled form declarations
and final policy review remain separate; no attestation or submission occurred.
No model/runtime/corpus binaries, raw token bodies or credentials are added.
Hashes and public code can reveal identity; full anonymity is not established.
No general public license was assigned to the project source.
''',
    })
    payload['MANIFEST.json'] = enc({n: info(b) for n, b in sorted(payload.items())})
    with tempfile.TemporaryDirectory(prefix='second-v119-review-') as temporary:
        root = Path(temporary)
        for n, b in payload.items():
            (root/n).write_bytes(b)
        result = subprocess.run([sys.executable, '-I', '-B', str(root/'verify_review_bundle.py'), str(root)],
            cwd=root, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr
        verified = json.loads(result.stdout)
    zip_payload(target, 'second-development-review-v119', payload)
    with zipfile.ZipFile(target) as archive:
        assert {Path(n).name: archive.read(n) for n in archive.namelist()} == payload
    assert all(payload[n] == b for n, b in old.items() if n.endswith('.zip'))
    result = dict(schema='development-review-bundle-v119',
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), path=str(target),
        archive=info(target.read_bytes()), manifest=json.loads(payload['MANIFEST.json']),
        members=len(payload), components=14, unchanged_v117_components=13,
        unchanged_portable_verifier=False, verified=verified, roundtrip_bytes_verified=True,
        manuscript=info(source), native_compile_success=True, rendered_layout_verified=False,
        new_empirical_result=True, actual_matched_comparisons=16, original_research_sources_changed=False,
        full_reproduction_verified=False, submission_ready=False)
    report.write_bytes(enc(result))
    print(json.dumps({k: result[k] for k in ('path', 'archive', 'members', 'components', 'verified')}, sort_keys=True))


if __name__ == '__main__':
    build()
