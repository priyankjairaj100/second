"""Offline byte and source-coverage checks; no experiment or external access."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import sys
import zipfile


def identity(blob):
    return dict(bytes=len(blob), sha256=hashlib.sha256(blob).hexdigest())


def archive_files(path):
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        assert len(entries) == len({e.filename for e in entries})
        assert sum(e.file_size for e in entries) <= 512*2**20
        files = {}
        prefixes = set()
        for entry in entries:
            name = PurePosixPath(entry.filename)
            assert not name.is_absolute() and '..' not in name.parts and len(name.parts) >= 2
            # Historical Python writestr archives omit the Unix type bits.
            # Accept their ordinary file entries, but never directories or links.
            assert not entry.is_dir() and stat.S_IFMT(entry.external_attr >> 16) in (0, stat.S_IFREG)
            assert entry.file_size <= 64*2**20
            prefixes.add(name.parts[0])
            relative = str(PurePosixPath(*name.parts[1:]))
            assert relative not in files
            files[relative] = archive.read(entry)
        assert len(prefixes) == 1
        return files


def main(directory):
    directory = Path(directory)
    manifest = json.loads((directory/'MANIFEST.json').read_bytes())
    assert {p.name for p in directory.iterdir()} == set(manifest)|{'MANIFEST.json'}
    for name, expected in manifest.items():
        assert PurePosixPath(name).name == name
        path = directory/name
        assert path.is_file() and not path.is_symlink() and identity(path.read_bytes()) == expected
    components = {n: archive_files(directory/n) for n in manifest if n.endswith('.zip')}
    assert len(components) == 13
    base_name = 'development-source-review-v72.zip'
    extra_name = 'development-optimization-source-v105.zip'
    base, extra = components[base_name], components[extra_name]
    base_hashes = dict((line[66:], line[:64]) for line in base['MANIFEST.sha256'].decode().splitlines())
    assert set(base_hashes) == set(base)-{'MANIFEST.sha256'}
    assert all(hashlib.sha256(base[n]).hexdigest() == h for n, h in base_hashes.items())
    extra_manifest = json.loads(extra['MANIFEST.json'])
    assert set(extra_manifest) == set(extra)-{'MANIFEST.json'}
    assert all(identity(extra[n]) == e for n, e in extra_manifest.items())
    coverage = json.loads(extra['SOURCE_COVERAGE.json'])
    assert coverage['executed_archive_entries'] == 934 and len(coverage['files']) == 930
    assert len(coverage['omitted_execution_receipts']) == 4
    counts = {base_name: 0, extra_name: 0}
    for name, expected in coverage['files'].items():
        component = expected['component']
        assert component in counts and identity(components[component][name]) == expected['derivative']
        counts[component] += 1
    assert counts == {base_name: 583, extra_name: 347}
    further_name='development-transfer-source-v111.zip'
    further=components[further_name]
    manifest2=json.loads(further['MANIFEST.json'])
    assert set(manifest2)==set(further)-{'MANIFEST.json'}
    assert all(identity(further[n])==e for n,e in manifest2.items())
    coverage2=json.loads(further['SOURCE_COVERAGE.json'])
    assert coverage2['executed_archive_entries']==1242 and len(coverage2['files'])==1226
    assert len(coverage2['omitted_execution_receipts'])==16
    counts2={base_name:0,extra_name:0,further_name:0}
    for name,expected in coverage2['files'].items():
        component=expected['component'];assert component in counts2
        assert identity(components[component][name])==expected['derivative'];counts2[component]+=1
    assert counts2=={base_name:583,extra_name:347,further_name:296}
    policy_name = 'development-point-policy-source-v114.zip'
    policy = components[policy_name]
    policy_manifest = json.loads(policy['MANIFEST.json'])
    assert set(policy_manifest) == set(policy)-{'MANIFEST.json'}
    assert all(identity(policy[n]) == e for n, e in policy_manifest.items())
    coverage3 = json.loads(policy['SOURCE_COVERAGE.json'])
    assert coverage3['qualified_archive_entries'] == 1339 and len(coverage3['files']) == 1322
    assert len(coverage3['omitted_execution_receipts']) == 17
    assert coverage3['source_copies_only'] is True
    assert coverage3['empirical_reproduction'] is coverage3['full_model_transfer_result'] is coverage3['general_speedup_result'] is False
    counts3 = {base_name: 0, extra_name: 0, further_name: 0, policy_name: 0}
    for name, expected in coverage3['files'].items():
        component = expected['component']
        assert component in counts3 and identity(components[component][name]) == expected['derivative']
        counts3[component] += 1
    assert counts3 == {base_name: 583, extra_name: 347, further_name: 296, policy_name: 96}
    evidence=components['development-diagnostic-evidence-v111.zip']
    evidence_manifest=json.loads(evidence['MANIFEST.json'])
    assert set(evidence_manifest)==set(evidence)-{'MANIFEST.json'}
    assert all(identity(evidence[n])==e for n,e in evidence_manifest.items())
    e=json.loads(evidence['results.json']);failed=e['matched_screen'];diagnostic=e['diagnostic']
    assert e['full_model_comparisons']==0 and e['full_model_transfer'] is e['speed_comparison'] is e['new_quality_evidence'] is False
    assert failed['completed_requests']==0 and len(failed['cancelled_unstarted_jobs'])==19
    assert diagnostic['independent_stage_oracle_executed'] is diagnostic['full_model_oracle_executed'] is False
    assert diagnostic['rows']*diagnostic['columns']==diagnostic['certified_codes']==2359296
    assert diagnostic['packed_code_bytes']==diagnostic['certified_codes']//2
    assert failed['numerical_cpu_charged_seconds']+diagnostic['numerical_cpu_charged_seconds']==e['costs']['cumulative_numerical_charged_seconds']==6304
    assert failed['failed_request_scheduler_cpu_upper_ns']-failed['failed_request_actual_worker_cpu_ns']==failed['failed_request_complete_controller_upper_cpu_ns']
    for cost in diagnostic['complete_costs'].values():
        assert cost['scheduler_cpu_ns']+cost['scheduler_quantum_ns']-cost['contained_work_cpu_ns']==cost['complete_controller_upper_cpu_ns']
    print(json.dumps(dict(status='verified_supplied_bytes_source_coverage_and_scoped_diagnostic_arithmetic',
        components=len(components),source_files=1322,source_component_counts=counts3,
        empirical_pipeline_executed=False,adapted_code_execution_qualified=False,
        independent_stage_oracle_executed=False,full_model_transfer=False,
        full_anonymity_verified=False,external_inputs_acquired=False),sort_keys=True))


if __name__=='__main__':main(sys.argv[1])
