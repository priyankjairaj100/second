"""Integrate checked development components; no new scientific or PDF output."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from validation.check_review_components_v74 import check, NAMES, R

W = Path('/Users/priyankjairaj/Documents/Codex/2026-10-10/see-i-am-working-on-a-2')


def info(raw):
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def enc(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def build():
    target = W / 'outputs/second-development-review-v74.zip'
    report = R / 'validation/v74_development_bundle.json'
    guide_report = R / 'validation/v74_reproduction_guide_check.json'
    assert not any(p.exists() for p in (target, report, guide_report))
    component_report = check()
    with tempfile.TemporaryDirectory(prefix='review-guide-v72-') as temp:
        temp = Path(temp).resolve()
        guide = temp / 'guide'
        companions = temp / 'components'
        guide.mkdir()
        companions.mkdir()
        with zipfile.ZipFile(R / 'reports/development-reproduction-guide-v72.zip') as archive:
            for entry in archive.infolist():
                path = Path(entry.filename)
                assert len(path.parts) == 2 and path.parts[0] == 'reproduction-guide'
                assert stat.S_ISREG(entry.external_attr >> 16)
                (guide / path.name).write_bytes(archive.read(entry))
        for name in NAMES:
            if name != 'development-reproduction-guide-v72.zip':
                shutil.copyfile(R / 'reports' / name, companions / name)
        def invoke():
            return subprocess.run([sys.executable, '-I', '-B', str(guide / 'verify_inputs.py'),
                '--components', str(companions)], text=True, capture_output=True, cwd=guide, timeout=30)
        clean = invoke()
        assert clean.returncode == 0, clean.stderr
        verified = json.loads(clean.stdout)
        assert len(verified['components']) == 7
        victim = companions / 'development-evidence-v69b.zip'
        raw = victim.read_bytes()
        victim.write_bytes(raw + b'changed')
        verified['corruption_rejected'] = invoke().returncode != 0
        victim.unlink()
        verified['missing_rejected'] = invoke().returncode != 0
        victim.write_bytes(raw)
        (guide / 'unexpected.txt').write_text('unexpected')
        verified['unexpected_rejected'] = invoke().returncode != 0
        assert all(verified[k] for k in ('corruption_rejected', 'missing_rejected', 'unexpected_rejected'))
        verified.update(clean_extraction_verified=True,external_input_acquisition=False,
                        archive_sha256=info((R / 'reports/development-reproduction-guide-v72.zip').read_bytes())['sha256'])
    payload = {name: (R / 'reports' / name).read_bytes() for name in NAMES}
    payload['second-research-draft.tex'] = (W / 'outputs/second-research-draft.tex').read_bytes()
    assert payload['second-research-draft.tex'] == (R / 'reports/manuscript_v74.tex').read_bytes()
    payload['README.txt'] = (R / 'reports/REVIEW_PACKAGE_README_V74.txt').read_bytes()
    payload['RESPONSIBLE_NLP_CHECKLIST_DRAFT.txt'] = (R / 'reports/RESPONSIBLE_NLP_CHECKLIST_V74.txt').read_bytes()
    manifest = {n: info(b) for n, b in sorted(payload.items())}
    payload['MANIFEST.json'] = enc(manifest)
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, raw in sorted(payload.items()):
            entry = zipfile.ZipInfo('second-development-review-v74/' + name, (2026, 10, 18, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(entry, raw, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(target) as archive:
        assert len(archive.namelist()) == len(set(archive.namelist())) == len(payload) == 12
        assert {Path(n).name: archive.read(n) for n in archive.namelist()} == payload
    verified['scope'] = 'Component/guide byte checks only; source, data or numerical experiment not executed here.'
    guide_report.write_bytes(enc(verified))
    result = dict(schema='development-review-bundle-v74',created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        archive=dict(path=str(target),**info(target.read_bytes())),members=len(payload),components=len(NAMES),
        manifest=manifest,roundtrip_bytes_verified=True,component_members=component_report['archive_members'],
        open_manuscript_matches_current_snapshot=True,separate_pdf_created=False,original_bundle_preserved=True,
        selection_metadata_integrated=True,expanded_notices_integrated=True,additional_cpu_notices_integrated=True,
        raw_article_or_token_bodies_included=False,model_binaries_included=False,
        private_identity_map_included=False,full_anonymity_verified=False,full_empirical_reproduction=False,
        scientific_quality_result=True,draft_checklist_included=True,author_attestation=False,form_submitted=False,submission_ready=False)
    report.write_bytes(enc(result))
    print(json.dumps({k: result[k] for k in ('archive','members','components','component_members','submission_ready')}))


if __name__ == '__main__':
    build()
