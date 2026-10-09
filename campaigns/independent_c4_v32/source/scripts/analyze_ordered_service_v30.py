"""Read-only audit of the nine registered ordered-service development trials.

This analysis performs no neural inference. All clocks are complete controller
transactions. Repeated-request arithmetic does not establish a changing-state
lifetime benefit or independent corpus/deletion replication.
"""
import argparse
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import analyze_full_service_v30 as common
from scripts.analyze_ordered_feature_identity_v30 import compare as compare_features
from src.experiment_inventory import source_hashes
from src.run_store import canonical_json, digest, strict_json
from src.service_terminal_evidence_v30 import verify_completed

require, hashed, read_json = common.require, common.hashed, common.read_json
SCHEMA = 'ordered-complete-service-transaction-v30'
TRIAL_IDS = ('prepare-256', 'original-model-256', 'repair-001', 'cold-001',
             'indexed-001', 'cold-002', 'repair-002', 'repair-003', 'cold-003')
PREPARER_SOURCES = ('ordered_fixed_service_v30.py', 'ordered_finite_decoder_v30.py',
    'ordered_attention_v30.py', 'fixed_factor_state.py', 'anchor_transformer.py',
    'ordered_finite.py', 'finite_primitives.py', 'certified_intervals.py',
    'certified_transformer.py', 'transformer_backend.py')
DECODER_SOURCES = ('ordered_finite_decoder_v30.py', 'ordered_attention_v30.py',
    'ordered_finite.py', 'finite_primitives.py', 'certified_intervals.py', 'certified_transformer.py')
EXTERNAL_FILES = ('plan.json', 'transaction.json', 'sealed-progress.json',
    'outputs/completion.json', 'outputs/progress.json', 'worker/result.json')


def nested(value, name):
    for part in name.split('.'):
        value = value[part]
    return value


def verify_external_records(program, bind):
    """Check immutable external evidence and its registered artifact bindings."""
    require(set(program['external_attempts']) == {'old_original', 'old_retained'},
            'ordered phase requires both registered scalar references')
    results = {}
    for name, entry in program['external_attempts'].items():
        attempt = Path(entry['attempt'])
        require(attempt.is_absolute(), 'external attempt requires an absolute path')
        result = verify_completed(attempt)
        actual = {}
        for filename in EXTERNAL_FILES:
            path = attempt/filename
            actual[filename] = dict(sha256=hashed(path), bytes=path.stat().st_size)
            bind(path)
        require(actual == entry['evidence'], 'registered external evidence changed: '+name)
        require(entry['completion_sha256'] == actual['outputs/completion.json']['sha256'],
                'external completion digest differs')
        require(result['artifacts'] == entry['verified_artifacts'], 'external artifact mapping differs')
        for key, expected in entry.get('equals', {}).items():
            require(nested(result, key) == expected, 'external prerequisite differs: '+name+'/'+key)
        require(result.get('schema') == 'adaptive-complete-service-transaction-v30'
            and result.get('complete_model') is True, 'external scalar complete-model reference differs')
        results[name] = result
    comparisons = []
    for comparison in program.get('external_equalities', []):
        for artifact in comparison.get('artifacts', ['model']):
            a = results[comparison['left']]['artifacts'][artifact]
            b = results[comparison['right']]['artifacts'][artifact]
            require((a['bytes'], a['sha256']) == (b['bytes'], b['sha256']), 'external equality differs')
            comparisons.append(dict(left=comparison['left'], right=comparison['right'], artifact=artifact, equal=True))
    require(comparisons == program.get('external_equality_checks', []), 'registered external equality receipt differs')
    return results


def verify_implementation(result, program):
    """Derive execution provenance from the frozen source inventory."""
    source = program['source_sha256']
    preparer = dict(schema='ordered-fixed-factor-preparer-v30',
        source_sha256={name:source['src/'+name] for name in PREPARER_SOURCES})
    require(result.get('preparer_sha256') == digest(canonical_json(preparer)), 'ordered preparer binding differs')
    manifest = result.get('decoder_implementation_manifest')
    require(type(manifest) is dict and manifest.get('schema') == 'ordered-equivalent-finite-decoder-v30',
            'ordered decoder manifest schema differs')
    require(manifest.get('source_sha256') == {name:source['src/'+name] for name in DECODER_SOURCES},
            'ordered decoder source inventory differs')
    require(manifest.get('global_mutation') is False and manifest.get('same_resource_or_refusal_behavior_claimed') is False,
            'ordered decoder equivalence scope differs')
    require(type(manifest.get('numpy_version')) is str and manifest['numpy_version'], 'decoder runtime version is absent')
    require(result.get('decoder_implementation_sha256') == digest(canonical_json(manifest)),
            'ordered decoder manifest digest differs')
    diagnostics = result.get('diagnostics', {})
    require(diagnostics.get('decoder_implementation_manifest') == manifest
        and diagnostics.get('preparer_sha256') == result['preparer_sha256'], 'service execution binding differs')


def verify_ordered_claims(result, plan, program, attempt):
    require(result.get('schema') == SCHEMA, 'unexpected ordered complete-service schema')
    # Reuse the reviewed common contract after checking the actual new schema.
    common.verify_service_claims(dict(result, schema='adaptive-complete-service-transaction-v30'), plan, program)
    verify_implementation(result, program)
    require(result.get('inputs') == plan['inputs'], 'terminal input access differs')
    expected = plan.get('expected_model_sha256')
    require(type(expected) is str and result.get('expected_model_sha256') == expected
        and result.get('expected_model_agreement') is True
        and result['artifacts']['model']['sha256'] == expected, 'registered complete-model equality gate failed')
    require(plan.get('expected_state_sha256') is None, 'this registered phase has no external state equality gate')
    require(read_json(attempt/'outputs/decoder-implementation.json') == result['decoder_implementation_manifest'],
            'saved decoder implementation manifest differs')
    require(digest(canonical_json(read_json(attempt/'outputs/fixed-target.json'))) == result['fixed_target_sha256'],
            'saved fixed target differs')
    require(digest(canonical_json(read_json(attempt/'outputs/base-target.json'))) == result['base_target_sha256'],
            'saved sequential target differs')
    admission = result.get('resource_admission', {})
    require(admission.get('all_stages_admitted') is True and admission.get('request_admitted') is True
        and admission.get('neural_work_started') is False and admission.get('request_cap') == plan['max_point_work_units'],
        'complete point-route admission is missing')


def verify_registered_comparisons(trial, result, results, external):
    checks = []
    for comparison in trial.get('compare_to', []):
        require(comparison['trial'] in results, 'comparison parent is not an earlier completed trial')
        checks.extend((comparison['trial'], kind, results[comparison['trial']]['artifacts'][kind])
                      for kind in comparison.get('artifacts', ['model']))
    expected_external = 'old_original' if trial['id'] in TRIAL_IDS[:2] else 'old_retained'
    require(trial.get('compare_external') == [dict(external=expected_external, artifacts=['model'])],
            'registered trial lacks its exact scalar complete-model gate')
    for comparison in trial['compare_external']:
        checks.extend((comparison['external'], kind, external[comparison['external']]['artifacts'][kind])
                      for kind in comparison['artifacts'])
    for label, kind, reference in checks:
        current = result['artifacts'][kind]
        require((current['bytes'], current['sha256']) == (reference['bytes'], reference['sha256']),
                'registered artifact comparison failed: '+label+'/'+kind)


def summarize_timings(times):
    """Use integer nanoseconds for strict break-even arithmetic."""
    require(set(times) == set(TRIAL_IDS), 'all nine timings are required')
    require(all(type(v) is int and v > 0 for v in times.values()), 'timings require positive integer nanoseconds')
    pairs = []
    for index in range(1, 4):
        cold, repair = times[f'cold-{index:03}'], times[f'repair-{index:03}']
        pairs.append(dict(pair=index, cold_seconds=cold/1e9, repair_seconds=repair/1e9,
            cold_over_repair=cold/repair, cold_minus_repair_seconds=(cold-repair)/1e9))
    ratios = [row['cold_over_repair'] for row in pairs]
    cold_sum = sum(times[f'cold-{i:03}'] for i in range(1, 4))
    repair_sum = sum(times[f'repair-{i:03}'] for i in range(1, 4))
    overhead = times['prepare-256']-times['original-model-256']
    savings_sum = cold_sum-repair_sum
    # Initial preparation can already win, even without positive request savings.
    # This is the first nonnegative k satisfying the displayed strict inequality,
    # not a claim that the advantage persists for every later request count.
    crossing = 0 if overhead < 0 else ((3*overhead)//savings_sum+1 if savings_sum > 0 else None)
    cumulative = []
    for count in range(1, 4):
        prepared = times['prepare-256']+sum(times[f'repair-{i:03}'] for i in range(1, count+1))
        replay = times['original-model-256']+sum(times[f'cold-{i:03}'] for i in range(1, count+1))
        cumulative.append(dict(repetitions=count,prepared_seconds=prepared/1e9,replay_seconds=replay/1e9,
            replay_minus_prepared_seconds=(replay-prepared)/1e9,replay_over_prepared=replay/prepared))
    return dict(pairs=pairs, observed_pair_count=3, geometric_mean_cold_over_repair=math.exp(sum(map(math.log,ratios))/3),
        minimum_cold_over_repair=min(ratios), maximum_cold_over_repair=max(ratios),
        aggregate_cold_over_repair=cold_sum/repair_sum,mean_cold_seconds=cold_sum/3e9,
        mean_repair_seconds=repair_sum/3e9,all_observed_pairs_favor_repair=all(x>1 for x in ratios),
        indexed_seconds=times['indexed-001']/1e9,indexed_over_mean_repair=3*times['indexed-001']/repair_sum,
        preparation_seconds=times['prepare-256']/1e9,original_model_only_seconds=times['original-model-256']/1e9,
        preparation_incremental_overhead_seconds=overhead/1e9,
        illustrative_repeated_same_request=dict(
            scope='same original state and same deletion replayed; no changing-state request sequence was measured',
            changing_state_lifetime_benefit_established=False,
            mean_request_saving_seconds=savings_sum/3e9,strict_break_even_repetitions=crossing,
            break_even_exists_for_positive_savings=savings_sum>0,
            formula='prepare + k*mean(repair) < original_model_only + k*mean(cold)',
            fixed_observed_mean_assumption=True,storage_carrying_cost_included=False,
            first_three_observed_repetition_totals=cumulative))


def verify_feature_identity(campaign, external, results, bind):
    """Recompute saved feature equality; never invoke a neural evaluator."""
    report_path = campaign/'feature-identity.json'
    saved = read_json(report_path)
    left = Path(external['old_original']['attempt'])
    right = campaign/'attempts/prepare-256'
    require(saved.get('schema') == 'ordered-real-feature-identity-v30'
        and saved.get('status') == 'complete' and saved.get('neural_evaluation_performed') is False,
        'saved feature identity report differs')
    regenerated = compare_features(left, right)
    require({k:v for k,v in regenerated.items() if k != 'analysis_cpu_ns'}
        == {k:v for k,v in saved.items() if k != 'analysis_cpu_ns'}, 'saved feature identity differs from archive reconstruction')
    require(saved['descriptor_count'] == 48 and len(saved['descriptors']) == 48,
            'feature identity does not cover both complete 24-stage records')
    require(saved['preparation_identities'][1] == results['prepare-256']['preparer_sha256'],
            'feature identity new preparer differs')
    bind(report_path)
    return dict(report_sha256=hashed(report_path),descriptor_count=48,total_binary64_bytes=saved['total_binary64_bytes'],
        all_feature_words_equal=True,all_canonical_descriptors_equal=True,neural_evaluation_performed=False,
        original_analysis_cpu_ns=saved['analysis_cpu_ns'],current_revalidation_cpu_ns=regenerated['analysis_cpu_ns'],
        original_analysis_source_binding='not recorded in the historical report; current recomputation source is bound below',
        input_evidence=saved['input_evidence'],preparation_identities=saved['preparation_identities'])


def analyze(campaign):
    started = time.process_time_ns()
    campaign = Path(campaign).absolute()
    program_raw, protocol_raw = (campaign/'program.json').read_bytes(), (campaign/'protocol.json').read_bytes()
    program, protocol = strict_json(program_raw), strict_json(protocol_raw)
    program_hash, protocol_hash = digest(program_raw), digest(protocol_raw)
    registration = read_json(campaign/'registration.json')
    require(registration['program_sha256'] == program_hash and registration['protocol_sha256'] == protocol_hash
        and protocol['program_sha256'] == program_hash, 'registration bindings differ')
    require(protocol['phase_cpu_seconds'] == {'feasibility':program['phase_cpu_cap_seconds']}, 'phase cap differs')
    require(tuple(row['id'] for row in program['trials']) == TRIAL_IDS, 'registered ordered trial schedule differs')
    for trial in program['trials']:
        method = ('direct_fresh' if trial['id'] == 'prepare-256' else 'indexed_fresh'
                  if trial['id'] == 'indexed-001' else 'repair' if trial['id'].startswith('repair-')
                  else 'model_only_fresh')
        require(trial['script'] == 'run_ordered_service_v30.py' and trial['plan']['method'] == method,
                'trial name does not represent its declared timing method')
    require({p.name for p in (campaign/'attempts').iterdir() if p.is_dir()} == set(TRIAL_IDS),
            'all nine registered attempts must be present; extra attempts cannot be omitted')
    require(not (campaign/'supersession.json').exists() and not (campaign/'continuation-v1.json').exists(),
            'this analyzer requires the unchanged nine-trial registration')
    require(source_hashes(campaign/'source') == program['source_sha256'], 'frozen source changed')
    evidence = {}
    def bind(path):
        path = Path(path).absolute()
        key = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        evidence[key] = hashed(path)
    for name in ('program.json','protocol.json','registration.json','registered-launcher.py'):
        bind(campaign/name)
    for name, expected in program['controller_sha256'].items():
        require(hashed(campaign/'source'/name) == expected, 'frozen controller changed: '+name)
        bind(campaign/'source'/name)
        if name.startswith('scripts/launch_'):
            require(hashed(campaign/'registered-launcher.py') == expected, 'registered launcher snapshot differs')
    for name, expected in program['historical_frozen_ledgers'].items():
        require(hashed(ROOT/name) == expected, 'historical ledger changed: '+name)
        bind(ROOT/name)
    external = verify_external_records(program, bind)
    rows, results, receipts, times = [], {}, [], {}
    reference = None
    state_groups, model_groups = {}, {}
    for trial in program['trials']:
        name = trial['id']; attempt = campaign/'attempts'/name
        result = verify_completed(attempt)
        plan = read_json(attempt/'plan.json')
        common.verify_plan(campaign,trial,plan,program,program_hash,protocol_hash,results)
        transaction,receipt,identity = (read_json(attempt/path) for path in
            ('transaction.json','worker/result.json','worker/identity.json'))
        common.verify_worker_schedule(campaign,trial,transaction,identity,registration,program)
        require(receipt['budget_debit']['reserved_cpu_seconds'] == trial['cpu_seconds']+2, 'reservation differs')
        verify_ordered_claims(result,plan,program,attempt)
        current = {key:result[key] for key in ('fixed_target_sha256','base_target_sha256','target_recipe',
            'evaluator_id','stage_ids','model_code_elements','original_records_sha256','checkpoint_files_sha256',
            'decoder_implementation_manifest','decoder_implementation_sha256','preparer_sha256','solver_backend',
            'solver_budget','max_point_work_units')}
        if reference is None:
            reference = current
        require(current == reference, 'ordered methods differ in mathematical or implementation policy')
        for dependency in trial.get('depends',[]):
            require(dependency['trial'] in results,'dependency did not precede this trial')
            for key, expected in dependency.get('equals',{}).items():
                require(nested(results[dependency['trial']],key) == expected,'registered dependency failed')
        verify_registered_comparisons(trial,result,results,external)
        old = external['old_original' if name in TRIAL_IDS[:2] else 'old_retained']
        for key in ('fixed_target_sha256','base_target_sha256','target_recipe','stage_ids','model_code_elements',
                    'original_records_sha256','checkpoint_files_sha256','retained_record_ids','deleted_record_ids',
                    'evaluator_id','original_token_count','retained_token_count'):
            require(result[key] == old[key], 'scalar/ordered scientific scope differs: '+key)
        membership = tuple(result['retained_record_ids'])
        for kind, groups in (('model',model_groups),('state',state_groups)):
            if kind in result['artifacts']:
                value = {k:result['artifacts'][kind][k] for k in ('bytes','sha256')}
                require(membership not in groups or groups[membership] == value,
                        'same-membership complete '+kind+' outputs differ within ordered phase')
                groups[membership] = value
        diagnostics = result['diagnostics']; times[name] = transaction['controller_elapsed_ns']
        rows.append(dict(trial=name,method=result['method'],controller_seconds=times[name]/1e9,
            observed_cpu_seconds=receipt['resource_usage']['total_cpu_ns']/1e9,
            charged_cpu_seconds=receipt['budget_debit']['charged_cpu_seconds'],artifacts=result['artifacts'],
            neural_stage_record_pairs=diagnostics['neural_stage_record_pairs'],stage_count=result['stage_count'],
            code_elements=result['model_code_elements'],retained_token_count=result['retained_token_count']))
        results[name] = result;receipts.append(receipt)
        for path in sorted(attempt.rglob('*')):
            if path.is_file() and path.suffix in ('.json','.txt','.log'):
                bind(path)
    budget = common.verify_final_budget(campaign,program,protocol_hash,receipts)
    bind(campaign/'phase-cpu-budget/ledger.json')
    feature = verify_feature_identity(campaign,program['external_attempts'],results,bind)
    timing = summarize_timings(times)
    analysis_sources = ('scripts/analyze_ordered_service_v30.py','scripts/analyze_full_service_v30.py',
        'scripts/analyze_ordered_feature_identity_v30.py','src/service_terminal_evidence_v30.py','src/run_store.py',
        'src/phase_budget.py','src/fixed_lossless_state_v29.py','src/fixed_lossless_codec_v29.py','src/compact_state.py')
    for name in analysis_sources:
        bind(ROOT/name)
    return dict(schema='ordered-complete-service-audit-v30',status='complete',confirmation=False,
        scientific_promotion=False,program_sha256=program_hash,protocol_sha256=protocol_hash,
        trials=rows,complete_cross_method_agreement=True,old_scalar_complete_models_equal=True,
        new_preparer_sha256=reference['preparer_sha256'],decoder_implementation_sha256=reference['decoder_implementation_sha256'],
        feature_identity=feature,phase_budget=budget,phase_accounting=dict(
            cap_seconds=program['phase_cpu_cap_seconds'],charged_seconds=budget['charged_cpu_seconds']['feasibility'],
            remaining_seconds=program['phase_cpu_cap_seconds']-budget['charged_cpu_seconds']['feasibility'],
            settled_receipts=len(receipts),unresolved_reservations=0,historical_ledgers_unchanged=True,
            external_reference_costs_added_to_new_phase=False,analysis_cpu_excluded_from_worker_ledger=True),
        replication_scope='three timing pairs; one shared model, corpus, original state, and deletion request',
        target_scope='fixed nearest-anchor features; distinct from sequential calibration',
        order_policy=program['method_order_policy'],os_cache=program['os_cache'],other_activity=program['other_activity'],
        population_superiority_established=False,quality_promotion_established=False,
        evidence_sha256=evidence,analysis_source_sha256={name:hashed(ROOT/name) for name in analysis_sources},
        analysis_cpu_ns=time.process_time_ns()-started,**timing)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign',type=Path,default=ROOT/'campaigns/ordered_service_v30')
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    report = analyze(args.campaign)
    with args.output.open('xb') as stream:
        stream.write(canonical_json(report))
    print(json.dumps({key:report[key] for key in ('status','geometric_mean_cold_over_repair',
        'preparation_incremental_overhead_seconds','analysis_cpu_ns')}))
