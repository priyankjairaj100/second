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
    assert len(components) == 14
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
    matched = components['development-matched-evidence-v119.zip']
    matched_manifest = json.loads(matched['MANIFEST.json'])
    assert set(matched_manifest) == set(matched)-{'MANIFEST.json'}
    assert all(identity(matched[n]) == e for n, e in matched_manifest.items())
    audit = json.loads(matched['audit-summary.json'])
    result = json.loads(matched['results.json'])
    cost = json.loads(matched['costs-and-scope.json'])
    assert audit['schema'] == 'e20-matched-evidence-v119'
    assert audit['program_sha256'] == 'a73ca66d08b50feeccf9601d6d214b00ad21917ae900671cc35d373aef4f4381'
    assert len(audit['jobs']) == 21 and {v['job_id'] for v in audit['jobs'].values()} == {str(i) for i in range(16407,16428)}
    scope = dict(actual_model_state_trust_pairs=16, checkpoints=2, related_gpt_family_only=True,
        single_observation_screen=True, stable_speedup=False, cross_architecture_generality=False,
        quality_evaluation=False)
    assert audit['evidence'] == result['scope'] == scope
    assert audit['independent_binary_audits_executed_on_cluster'] is True
    assert audit['this_package_reexecutes_pipeline'] is audit['this_package_reaudits_binaries'] is False
    assert audit['old_attempts_or_sources_changed'] is audit['numerical_limits_changed'] is False
    assert (audit['original_records'], audit['tokens_per_record'], audit['fixed_normalization']) == (4,128,512)
    assert audit['design'] == dict(stage_counts=dict(distilgpt2=24,gpt2=48),retained_counts=[3,2],
        point_route_policy='all-point-inputs-token-from-start-v112')
    cells = ('reference_compressed','optimized_compressed','reference_modern','optimized_modern')
    expected = {(p,c,s) for p in ('distilgpt2','gpt2') for c in cells for s in (1,2)}
    key = lambda row: (row['profile'],row['cell'],row['step'])
    assert len(audit['comparisons']) == len(result['rows']) == 16
    assert {key(r) for r in audit['comparisons']} == {key(r) for r in result['rows']} == expected
    for pair in audit['comparisons']:
        assert pair['actual_model_bytes_equal'] is pair['actual_state_bytes_equal'] is pair['actual_trust_bytes_equal'] is True
    rows = {key(r):r for r in result['rows']}
    for (p,c,s), row in rows.items():
        assert row['job_id'] == audit['jobs'][f'{p}/{c}-{s}']['job_id']
        assert row['retained_records'] == (3 if s == 1 else 2)
        assert row['host_elapsed_ns'] >= row['request_elapsed_ns'] > 0
        assert row['checkpoint_inclusive_bytes'] >= row['live_state_bytes'] > 0
        assert all(type(v) is int and v >= 0 for v in row['disjoint_host_partition_ns'].values())
        assert sum(row['disjoint_host_partition_ns'].values()) == row['host_elapsed_ns']
        assert row['decoder_only_duration_available'] is False
        assert row['remainder_is_not_a_named_operation'] is True
    from fractions import Fraction
    def ratio(a,b):
        q=Fraction(a,b)
        return dict(numerator=q.numerator,denominator=q.denominator)
    for profile in ('distilgpt2','gpt2'):
        expected_comparisons=[]
        for step in (1,2):
            item=dict(step=step,combined_optimization_speedup={})
            for representation in ('compressed','modern'):
                item['combined_optimization_speedup'][representation]=ratio(
                    rows[profile,'reference_'+representation,step]['host_elapsed_ns'],
                    rows[profile,'optimized_'+representation,step]['host_elapsed_ns'])
            a,b=(rows[profile,'optimized_'+rep,step] for rep in ('compressed','modern'))
            item['optimized_compressed_to_modern']={field:ratio(a[field],b[field]) for field in
                ('host_elapsed_ns','live_state_bytes','checkpoint_inclusive_bytes')}
            expected_comparisons.append(item)
        assert result['comparisons'][profile]==expected_comparisons
    import csv,io
    tabular=list(csv.DictReader(io.StringIO(matched['all-requests.tsv'].decode()),delimiter='\t'))
    assert len(tabular)==16
    assert {(r['profile'],r['cell'],int(r['step'])) for r in tabular}==expected
    for entry in tabular:
        row=rows[entry['profile'],entry['cell'],int(entry['step'])]
        for field,value in entry.items():
            if field in ('fallback_stages','disjoint_host_partition_ns'):
                assert json.loads(value)==row[field]
            else:
                assert value==str(row[field])
    contrasts = json.loads(matched['signed-contrasts.json'])
    assert [(v['profile'],v['step']) for v in contrasts] == [(p,s) for p in ('distilgpt2','gpt2') for s in (1,2)]
    from decimal import Decimal, localcontext
    for item in contrasts:
        p,s = item['profile'],item['step'];comp=rows[p,'optimized_compressed',s];modern=rows[p,'optimized_modern',s]
        for field,source in (('complete_host_change_percent','host_elapsed_ns'),
                             ('live_storage_change_percent','live_state_bytes'),
                             ('checkpoint_inclusive_change_percent','checkpoint_inclusive_bytes')):
            with localcontext() as ctx:
                ctx.prec=40
                assert item[field] == format(Decimal(100*(comp[source]-modern[source]))/Decimal(modern[source]),'.3f')
    assert set(cost['reused_preparation_host_ns']) == {'distilgpt2','gpt2'}
    assert all(type(v) is int and v>0 for v in cost['reused_preparation_host_ns'].values())
    assert cost['old_unknown_v80_cpu_seconds'] == 12602
    budget=cost['numerical_budget'];assert len(budget['attempts'])==18
    assert all(a['state']=='settled' for a in budget['attempts'].values())
    charged=sum(a['charged_cpu_seconds'] for a in budget['attempts'].values())
    assert charged==budget['charged_cpu_seconds']['feasibility']
    assert charged+6304==cost['cumulative_screen_numerical_seconds']<=82840
    assert cost['historical_preparation_cost_is_not_zero'] is cost['preparation_shared_across_cells'] is cost['clocks_overlap'] is True
    assert cost['preparation_reexecuted'] is cost['combine_scheduler_worker_controller_clocks'] is cost['all_experiments_total_established'] is False
    print(json.dumps(dict(status='verified_supplied_bytes_source_coverage_and_scoped_arithmetic',
        components=len(components),source_files=1322,source_component_counts=counts3,
        matched_reported_model_state_trust_pairs=16, matched_reported_requests=16,
        related_checkpoint_evidence_included=True, stable_speedup_established=False,
        cross_architecture_generality=False, new_quality_evaluation=False,
        empirical_pipeline_executed_by_this_verifier=False, binary_reaudit_by_this_verifier=False,
        adapted_code_execution_qualified=False, full_anonymity_verified=False,
        external_inputs_acquired=False),sort_keys=True))


if __name__=='__main__':main(sys.argv[1])
