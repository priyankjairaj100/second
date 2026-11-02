"""Review-only copies from the exact qualified V112 package; no result claim."""
import ast
import json
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from validation.build_review_source_v69 import MAPPING, Rename, replace, info, enc
from validation.package_review_bundle_v105 import zip_payload

R = Path(__file__).resolve().parents[1]
S = Path('/Users/priyankjairaj/Documents/Codex/2026-10-10/see-i-am-working-on-a-2/work/second-speed-campaign')


def build():
    target = R/'reports/development-point-policy-source-v114.zip'
    report = R/'validation/v114_point_policy_source.json'
    derivation = R/'docs/REVIEW_SOURCE_DERIVATION_V114.json'
    assert not any(p.exists() for p in (target, report, derivation))
    archive = S/'v112-prepared/matched-complete-recovery-v112-source-only.tar'
    expected = dict(bytes=14131200, sha256='051c490a449120fabd7ddd839afb1287b5ea8ceef15a39fcd86a8823258ac2bd')
    assert info(archive.read_bytes()) == expected
    program_raw = (S/'v112-program.json').read_bytes()
    assert info(program_raw)['sha256'] == 'a73ca66d08b50feeccf9601d6d214b00ad21917ae900671cc35d373aef4f4381'
    program = json.loads(program_raw)
    with tarfile.open(archive) as tf:
        members = tf.getmembers()
        assert len(members) == len({m.name for m in members}) == 1340
        assert all(m.isfile() and not PurePosixPath(m.name).is_absolute()
                   and '..' not in PurePosixPath(m.name).parts for m in members)
        actual = {m.name: tf.extractfile(m).read() for m in members}
    inventory_raw = actual.pop('inventory.json')
    inventory = json.loads(inventory_raw)
    assert len(inventory) == 1339 and set(inventory) == set(actual)
    assert inventory == program['sources']
    assert info(inventory_raw) == program['source_inventory']
    assert expected == program['source_archive']
    assert all(info(actual[n]) == e for n, e in inventory.items())
    prior = {}
    for component in ('development-source-review-v72.zip',
                      'development-optimization-source-v105.zip',
                      'development-transfer-source-v111.zip'):
        with zipfile.ZipFile(R/'reports'/component) as z:
            for n in z.namelist():
                relative = str(PurePosixPath(*PurePosixPath(n).parts[1:]))
                if relative in inventory:
                    assert relative not in prior
                    prior[relative] = component, z.read(n)
    assert len(prior) == 1226
    adapted, coverage, omitted, changes = {}, {}, {}, {}
    parsed = 0
    reverse = {v: k for k, v in MAPPING.items()}
    for name, expected_file in sorted(inventory.items()):
        if name.startswith(('gates/', 'recovery-evidence/')):
            omitted[name] = dict(identity=expected_file,
                reason='Execution receipt omitted; original preserved in the public research repository')
            continue
        raw = actual[name]
        assert (R/name).read_bytes() == raw
        text = raw.decode()
        assert not any(v in text for v in MAPPING.values())
        edited = replace(text, MAPPING)
        assert replace(edited, reverse) == text
        if name.endswith('.py'):
            assert ast.dump(Rename().visit(ast.parse(text))) == ast.dump(ast.parse(edited))
            parsed += 1
        blob = edited.encode()
        component = prior[name][0] if name in prior else target.name
        if name in prior:
            assert blob == prior[name][1]
        else:
            adapted[name] = blob
            if raw != blob:
                changes[name] = dict(original=expected_file, derivative=info(blob))
        coverage[name] = dict(component=component, derivative=info(blob))
    assert len(coverage) == 1322 and len(adapted) == 96 and len(omitted) == 17
    adapted['SOURCE_COVERAGE.json'] = enc(dict(schema='point-policy-source-coverage-v114',
        qualified_archive_entries=1339, files=coverage, omitted_execution_receipts=omitted,
        source_copies_only=True, empirical_reproduction=False,
        full_model_transfer_result=False, general_speedup_result=False))
    adapted['README.txt'] = b'''Point-policy source inspection supplement,27 October2026

This adds96 source/protocol/test copies to the unchanged1226 earlier copies.
Together they cover all1322 source entries in the exact qualified V112 package.
Seventeen execution-specific receipts are omitted and enumerated. Their original
versions and the derivation map remain in the public research repository.

The original V112 package passed318 pinned Linux software checks and its matched
numerical chain was released once. At this package checkpoint that chain was
running; no completed full-model transfer or general speedup result is supplied.
The new policy chooses the existing token route for point solves in all cells
and fresh oracles. The binary audit reader repair preserves the original caps.
All older failed sources and existing-token diagnostic sources remain included.

Declared path/account/node/repository strings are reversibly adapted. Python ASTs
are checked to differ only in those strings; adapted execution is not qualified.
These copies are for inspection. Do not run historical launchers, retry consumed
jobs, or pass adapted bytes to original hash gates. No model/corpus/token-body/
runtime binaries or credentials are added. Small generated fixtures remain.
No project license is newly assigned. Public originals can reveal identity;
anonymity is not established. Offline source coverage is not empirical replication.
'''
    adapted['MANIFEST.json'] = enc({n: info(b) for n, b in sorted(adapted.items())})
    zip_payload(target, 'point-policy-source', adapted)
    with zipfile.ZipFile(target) as z:
        assert {n.removeprefix('point-policy-source/'): z.read(n) for n in z.namelist()} == adapted
    assert all(info((R/n).read_bytes()) == inventory[n] for n in coverage)
    derivation.write_bytes(enc(dict(schema='point-policy-source-derivation-v114',
        exclude_from_review_archive=True, mapping=MAPPING, changed_files=changes,
        original_inventory=inventory, original_archive=expected, source_coverage=coverage)))
    result = dict(schema='point-policy-source-supplement-v114', archive=info(target.read_bytes()),
        source_files_added=96, inherited_source_files=1226, total_source_files=1322,
        excluded_execution_receipts=17, new_copies_adapted=len(changes), python_asts_checked=parsed,
        all_source_originals_unchanged=True, archive_roundtrip_verified=True,
        empirical_work_executed=False, adapted_code_execution_qualified=False,
        full_model_transfer_result=False, general_speedup_result=False, full_anonymity_verified=False)
    report.write_bytes(enc(result))
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    build()
