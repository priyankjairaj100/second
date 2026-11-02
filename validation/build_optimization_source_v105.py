"""Add the missing executed optimization sources as review-only derivatives."""
import ast
import json
from pathlib import Path
import stat
import tarfile
import zipfile
from validation.build_review_source_v69 import MAPPING, Rename, replace, info, enc

R = Path(__file__).resolve().parents[1]
W = Path('/Users/priyankjairaj/Documents/Codex/2026-10-10/see-i-am-working-on-a-2')
S = W/'work/second-speed-campaign'


def build():
    target = R/'reports/development-optimization-source-v105.zip'
    derivation = R/'docs/REVIEW_SOURCE_DERIVATION_V105.json'
    report = R/'validation/v105_optimization_source.json'
    assert not any(p.exists() for p in (target, derivation, report))
    program = json.loads((S/'v89-verified-receipts-20261026/program.json').read_bytes())
    inventory = json.loads((S/'v89-prepared/source-inventory.json').read_bytes())
    assert inventory == program['source_inventory'] == program['sources'] and len(inventory) == 934
    archive = S/'v89-prepared/four-cell-recovery-v89-source-only.tar'
    assert info(archive.read_bytes()) == dict(bytes=program['source_archive_bytes'], sha256=program['source_archive_sha256'])
    with tarfile.open(archive) as tf:
        members = tf.getmembers()
        assert len(members) == len({m.name for m in members})
        assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
        actual = {m.name: tf.extractfile(m).read() for m in members}
    assert all(info(actual[n]) == e for n, e in inventory.items())
    base_name = 'development-source-review-v72.zip'
    extra_name = target.name
    with zipfile.ZipFile(R/'reports'/base_name) as z:
        base = {n.removeprefix('source-review/'): z.read(n) for n in z.namelist()}
    adapted, changed, coverage, omitted = {}, {}, {}, {}
    reverse = {v: k for k, v in MAPPING.items()}
    parsed = 0
    for name, original in sorted(inventory.items()):
        if name.startswith('recovery-evidence/'):
            omitted[name] = dict(identity=original, reason='Run-specific recovery receipt; original retained privately, E18 summarizes outcomes')
            continue
        raw = actual[name]
        assert (R/name).read_bytes() == raw
        text = raw.decode()
        assert not any(value in text for value in MAPPING.values()), name
        derivative = replace(text, MAPPING)
        assert replace(derivative, reverse) == text, name
        if name.endswith('.py'):
            assert ast.dump(Rename().visit(ast.parse(text))) == ast.dump(ast.parse(derivative)), name
            parsed += 1
        blob = derivative.encode()
        component = base_name if name in base else extra_name
        if component == base_name:
            assert base[name] == blob, name
        else:
            adapted[name] = blob
            if raw != blob:
                changed[name] = dict(original=original, derivative=info(blob),
                    replacement_counts={k: text.count(k) for k in MAPPING if k in text})
        coverage[name] = dict(component=component, derivative=info(blob))
    assert len(adapted) == 347 and len(coverage) == 930 and len(omitted) == 4
    assert all(not any(key in blob.decode() for key in MAPPING) for blob in adapted.values())
    adapted['SOURCE_COVERAGE.json'] = enc(dict(schema='optimization-source-coverage-v105',
        executed_archive_entries=934, files=coverage, omitted_execution_receipts=omitted,
        source_copies_only=True, empirical_reproduction=False, private_derivation_mapping_included=False))
    adapted['README.txt'] = b'''Optimization source supplement,26 October2026

This adds347 source/protocol/configuration/test copies to the unchanged583-file
source component V72. Together they cover all930 source/protocol entries from
the executed V89 archive. Four run-specific recovery receipts remain excluded;
E18 supplies their outcome/cost scope. SOURCE_COVERAGE.json maps every supplied
source to its component and derivative hash. It is not a runtime lock.

The supplement includes token-neighbor, native payload decoder and bounded-cache
implementations, integration tests, storage accounting and complete host/audit
wrappers. No active V104 result or source qualification is claimed here.
Declared private path/account/repository/node strings are replaced consistently
with the base component;56 new copies change. All source copies reverse to the
preserved originals under a separate private mapping. Python ASTs were checked
to differ only in those strings; this is not operational equivalence evidence.

Inspect these sources alongside the base component at matching relative paths.
Do not run historical launchers, retry consumed jobs, or pass adapted bytes to
original hash gates. Full empirical reproduction requires separately admitted
external inputs, original-equivalent code/runtime, resources and new registration.
No model/runtime/corpus binaries, raw token arrays, private mapping or credentials
are supplied. Small generated fixtures remain. Project release terms are still
unassigned; dependency notices remain in the unchanged companion. Public code,
hashes and outcomes can provide indirect linkage; anonymity is not established.

The outer verify_review_bundle.py checks all ten component bytes, archive members
and930-file source coverage offline. It does not execute copied research code,
qualify this adapted code, or repeat any scientific or binary-equality result.
'''
    manifest = {n: info(b) for n, b in sorted(adapted.items())}
    adapted['MANIFEST.json'] = enc(manifest)
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, blob in sorted(adapted.items()):
            entry = zipfile.ZipInfo('optimization-source/'+name, (2026, 10, 26, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            z.writestr(entry, blob, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(target) as z:
        assert {n.removeprefix('optimization-source/'): z.read(n) for n in z.namelist()} == adapted
    for name in coverage:
        assert info((R/name).read_bytes()) == inventory[name]
    derivation.write_bytes(enc(dict(schema='private-optimization-source-derivation-v105',
        exclude_from_review_archive=True, mapping=MAPPING, changed_files=changed,
        original_inventory=inventory, original_archive=info(archive.read_bytes()), source_coverage=coverage)))
    result = dict(schema='optimization-source-supplement-v105', source_files_added=347,
        inherited_source_files=583, total_source_files=930, excluded_execution_receipts=4,
        new_copies_adapted=len(changed), python_asts_checked=parsed,
        all_source_originals_unchanged=True, archive_roundtrip_verified=True,
        archive=info(target.read_bytes()), empirical_work_executed=False,
        adapted_code_execution_qualified=False, full_anonymity_verified=False)
    report.write_bytes(enc(result))
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    build()
