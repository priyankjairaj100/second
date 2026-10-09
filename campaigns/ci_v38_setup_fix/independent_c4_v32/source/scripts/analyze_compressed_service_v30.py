"""Audit the registered two-trial compressed phase without neural inference.

Scientific storage or timing losses remain completed numerical observations.
All performance clocks include the complete controller transaction.
"""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import analyze_full_service_v30 as common
from scripts.analyze_ordered_service_v30 import verify_implementation, nested, EXTERNAL_FILES
from src.experiment_inventory import source_hashes
from src.run_store import canonical_json,digest,strict_json
from src.service_terminal_evidence_v30 import verify_completed

require,hashed,read_json = common.require,common.hashed,common.read_json
TRIALS = ('convert-256','repair-128')
COLD_REFERENCES = ('retained_cold','retained_cold_002','retained_cold_003')
EXTERNALS = {'original','quality','retained_lossless',*COLD_REFERENCES}
SCHEMA = 'adaptive-compressed-service-transaction-v30'


def nonnegative(value,name):
    require(type(value) is int and value >= 0,name+' must be a nonnegative integer')
    return value


def verify_archive_source(result,program,trial):
    if result.get('schema') == 'adaptive-quality-followup-v30':
        require(trial['script'] == 'run_followup_quality_v30.py' and 'source_sha256' not in result,
                'quality source contract differs')
        require(result.get('provenance',{}).get('shared_evaluator_sha256')
            == program['source_sha256'].get('scripts/run_quality_v30.py'),
            'quality evaluator source differs')
        # The terminal plan digest, exact command, and frozen plan source map
        # carry this schema's full execution-source binding.
    else:
        require(result.get('source_sha256') == program['source_sha256'],'archive terminal source differs')


def verified_archive(attempt,bind,cache):
    """Verify an archived result and the registration that authorized it."""
    attempt = Path(attempt).absolute()
    if attempt in cache:
        return cache[attempt]
    campaign = attempt.parent.parent
    result = verify_completed(attempt)
    program_raw,protocol_raw = (campaign/'program.json').read_bytes(),(campaign/'protocol.json').read_bytes()
    program,protocol = strict_json(program_raw),strict_json(protocol_raw)
    registration = read_json(campaign/'registration.json')
    program_hash,protocol_hash = digest(program_raw),digest(protocol_raw)
    require(registration['program_sha256'] == program_hash and registration['protocol_sha256'] == protocol_hash
        and protocol['program_sha256'] == program_hash,'archive registration binding differs')
    require(source_hashes(campaign/'source') == program['source_sha256'],'archive frozen source differs')
    matching = [row for row in program['trials'] if row['id'] == attempt.name]
    require(len(matching) == 1,'archive attempt is absent or duplicated in registration')
    trial = matching[0]
    verify_archive_source(result,program,trial)
    parents = {entry['trial']:verify_completed(campaign/'attempts'/entry['trial'])
               for entry in trial.get('inputs_from_trial',{}).values()}
    plan = read_json(attempt/'plan.json')
    common.verify_plan(campaign,trial,plan,program,program_hash,protocol_hash,parents)
    transaction,receipt,identity = (read_json(attempt/path) for path in
        ('transaction.json','worker/result.json','worker/identity.json'))
    common.verify_worker_schedule(campaign,trial,transaction,identity,registration,program)
    require(receipt['budget_debit']['reserved_cpu_seconds'] == trial['cpu_seconds']+2,'archive CPU reservation differs')
    for name in ('program.json','protocol.json','registration.json'):
        bind(campaign/name)
    for name in EXTERNAL_FILES:
        bind(attempt/name)
    bind(attempt/'worker/identity.json')
    value = dict(result=result,program=program,plan=plan,transaction=transaction,receipt=receipt,attempt=attempt)
    cache[attempt] = value
    return value


def verify_external(program,bind,cache):
    require(set(program['external_attempts']) == EXTERNALS,'registered external comparison set differs')
    results = {}
    for name,entry in program['external_attempts'].items():
        archive = verified_archive(entry['attempt'],bind,cache)
        attempt,result = archive['attempt'],archive['result']
        files = {filename:dict(sha256=hashed(attempt/filename),bytes=(attempt/filename).stat().st_size)
                 for filename in EXTERNAL_FILES}
        require(files == entry['evidence'],'registered external evidence changed: '+name)
        require(files['outputs/completion.json']['sha256'] == entry['completion_sha256'],'external completion differs')
        require(result['artifacts'] == entry['verified_artifacts'],'external artifact binding differs')
        for field,expected in entry.get('equals',{}).items():
            require(nested(result,field) == expected,'external prerequisite failed: '+name+'/'+field)
        results[name] = archive
    expected_equalities = [dict(left='retained_lossless',right=name,artifacts=['model']) for name in COLD_REFERENCES]
    require(program.get('external_equalities') == expected_equalities,'registered complete-model comparison policy differs')
    checks = []
    for name in COLD_REFERENCES:
        left,right = results['retained_lossless']['result']['artifacts']['model'],results[name]['result']['artifacts']['model']
        require((left['bytes'],left['sha256']) == (right['bytes'],right['sha256']),'complete external retained models differ')
        checks.append(dict(left='retained_lossless',right=name,artifact='model',equal=True))
    require(checks == program['external_equality_checks'],'registered equality receipt differs')
    quality = results['quality']['result']
    require(all(quality.get(key) is True for key in ('development_safety_gate_pass',
        'historical_control_parity_pass','matched_quality_gate_pass')),'quality prerequisite is incomplete')
    require(quality['provenance']['new_model_sha256'] == results['retained_cold']['result']['model_artifact']['sha256'],
            'quality gate belongs to a different retained model')
    return results


def verify_trial_external_inputs(trial,program):
    for key,binding in trial.get('inputs_from_external',{}).items():
        parent = program['external_attempts'][binding['external']]
        attempt = Path(parent['attempt'])
        if binding.get('completion') is True:
            require(set(binding) == {'external','completion'},'external completion binding fields differ')
            path,sha = attempt/'outputs/completion.json',parent['completion_sha256']
        else:
            require(set(binding) == {'external','artifact'},'external artifact binding fields differ')
            artifact = parent['verified_artifacts'][binding['artifact']]
            path,sha = attempt/'outputs'/artifact['file'],artifact['sha256']
        require(trial['plan']['inputs'][key] == dict(path=str(path),sha256=sha),'resolved external input differs')


def reported_unresolved_pairs(stage):
    diagnostics = (stage.get('certificate_failure_diagnostics') or {}).get('native_diagnostics',{})
    rounds = diagnostics.get('unresolved_coordinate_rounds')
    if not rounds:
        return None
    require(type(rounds) is list,'unresolved coordinate rounds must be a list')
    return rounds[-1]


def verify_diagnostics(result,plan):
    """Cross-check complete stage routes, replay counts, and reserved work."""
    d = result['diagnostics']
    if plan['method'] == 'convert_lossless':
        require(d.get('schema') == 'verified-lossless-to-compressed-conversion-v30','conversion diagnostic schema differs')
        for key in ('every_source_hash_verified','every_enclosure_contains_source','complete_original_model_preserved',
                    'conversion_uses_no_quantizer'):
            require(d.get(key) is True,'conversion verification missing: '+key)
        expected = len(plan['record_ids'])*result['stage_count']
        require(d.get('checked_enclosures') == d.get('decoded_exact_factors') == expected,'conversion omits exact source enclosures')
        require(d.get('neural_stage_record_pairs') == d.get('point_solver_stages') == 0,'conversion performs undeclared numerical work')
        require(result.get('containment_verified_for_all_factors') is True,'conversion containment is missing')
        return dict(kind='conversion',checked_enclosures=expected,neural_stage_record_pairs=0,
                    decoded_source_bytes=d['decoded_source_bytes'],complete_original_model_preserved=True)
    stages = d.get('stages')
    require(type(stages) is list and [r['stage_id'] for r in stages] == result['stage_ids'],'repair stage diagnostics incomplete')
    require(d.get('pending_stage') is None and not d.get('aborted',False),'repair diagnostic remains pending or aborted')
    counts = {'box_certificate':0,'singleton_exact_point':0,'exact_retained_replay':0}
    neural = refused = 0
    expected_reservations = {}
    for row in stages:
        route = row['route'];require(route in counts,'unknown compressed route')
        counts[route] += 1
        neural += nonnegative(row['neural_stage_record_pairs'],'stage replay count')
        require(route == 'exact_retained_replay' or row['neural_stage_record_pairs'] == 0,
                'accepted or singleton stage performs undeclared replay')
        require((row['certificate_accepted'] is True) == (route == 'box_certificate'),'certificate acceptance and route disagree')
        require((row['singleton_box'] is True) == (route == 'singleton_exact_point'),'singleton and route disagree')
        if route == 'box_certificate':
            require(row['certificate_route'] in ('sparse','primal') and row['certificate_rejection'] is None,
                    'accepted box certificate lacks a valid route or records a rejection')
        if route == 'singleton_exact_point':
            require(row['certificate_accepted'] is None and row['certificate_rejection'] is None,
                    'singleton is not a rejected box certificate')
        if route == 'exact_retained_replay':
            require(row['certificate_accepted'] is False and bool(row['certificate_rejection']),'fallback rejection is missing')
            refused += int(row['certificate_route'] is None)
        nonnegative(row['elapsed_ns'],'stage elapsed time')
        if route != 'singleton_exact_point' and row['certificate_route'] is not None:
            chosen = row['certificate_route']
            require(chosen in ('sparse','primal'),'unknown admitted certificate route')
            admission = row['certificate_admission']['routes'][chosen]
            require(admission['admitted'] is True,'attempted certificate was not admitted')
            expected_reservations[('certificate',row['stage_id'])] = (chosen,
                nonnegative(admission['work_units_reserved'],'certificate reservation'))
        if route != 'box_certificate':
            solver = row['solver_diagnostics'];chosen = solver['backend']
            require(chosen in ('token','primal') and solver['admission']['selected'] == chosen,
                    'point backend and admission differ')
            admission = solver['admission']['routes'][chosen]
            require(admission['admitted'] is True,'point solver was not admitted')
            expected_reservations[('point',row['stage_id'])] = (chosen,
                nonnegative(admission['work_units'],'point reservation'))
    accepted,singleton,replayed = (counts[k] for k in ('box_certificate','singleton_exact_point','exact_retained_replay'))
    require(d['certificate_accepted_stages'] == accepted and d['certificate_rejected_stages'] == replayed
        and d['singleton_point_stages'] == singleton,'aggregate route counts differ')
    require(d['certificate_admission_refused_stages'] == refused
        and d['certificate_attempted_stages'] == accepted+replayed-refused,'certificate attempt accounting differs')
    require(d['point_solver_stages'] == d['point_solver_attempted_stages'] == singleton+replayed,'point solver stage accounting differs')
    maximum = len(plan['record_ids'])*result['stage_count']
    require(d['neural_stage_record_pairs'] == d['replay_verified_stage_record_pairs'] == neural
        and neural <= plan['max_neural_stage_record_pairs'] <= maximum,'replay count or policy differs')
    require(sum(nonnegative(v,'source replay count') for v in d['neural_stage_record_pairs_by_source'].values()) == neural
        and set(d['neural_stage_record_pairs_by_source']) == set(plan['record_ids']),'per-source replay counts differ')
    require(d['total_possible_neural_stage_record_pairs'] == maximum
        and d['avoided_neural_stage_record_pairs'] == maximum-neural,'avoided replay accounting differs')
    reservations = d['coefficient_reservations']
    actual_reservations = {}
    for row in reservations:
        key = (row['kind'],row['stage_id'])
        require(key not in actual_reservations,'duplicate stage work reservation')
        actual_reservations[key] = (row['route'],nonnegative(row['work_units'],'reserved work'))
    require(actual_reservations == expected_reservations,'missing, extra, or mismatched stage work reservation')
    for kind in ('point','certificate'):
        units = sum(nonnegative(row['work_units'],'reserved work') for row in reservations if row['kind'] == kind)
        require(units == d[kind+'_work_units_reserved'] and units <= plan['max_'+kind+'_work_units'],
                'cumulative '+kind+' work differs or exceeds policy')
    require(all(row['kind'] in ('point','certificate') and row['stage_id'] in result['stage_ids']
                for row in reservations),'unknown coefficient reservation')
    require(d['model_seed_source'] == 'none' and d['trusted_preparation_required'] is True,'hidden model proposals or untrusted factors')
    return dict(kind='repair',certificate_accepted_stages=accepted,certificate_rejected_stages=replayed,
        certificate_attempted_stages=d['certificate_attempted_stages'],certificate_admission_refused_stages=refused,
        singleton_point_stages=singleton,point_solver_stages=singleton+replayed,neural_stage_record_pairs=neural,
        avoided_neural_stage_record_pairs=maximum-neural,total_possible_neural_stage_record_pairs=maximum,
        certificate_work_units_reserved=d['certificate_work_units_reserved'],point_work_units_reserved=d['point_work_units_reserved'],
        certificate_seconds=d['certificate_elapsed_ns']/1e9,replay_seconds=d['replay_elapsed_ns']/1e9,
        point_solver_seconds=d['point_solver_elapsed_ns']/1e9,service_seconds=d['service_elapsed_ns']/1e9,
        timing_scope='nested diagnostics; never added to complete transaction time',
        certificate_scope='accepted stages can still be traversed as ancestors during later replay',
        unresolved_coordinates_by_stage=[dict(stage_id=row['stage_id'],
            final_reported_row_coordinate_pairs=reported_unresolved_pairs(row))
            for row in stages if row['route'] == 'exact_retained_replay'],
        stages=[{k:row[k] for k in ('stage_id','route','certificate_accepted','certificate_route',
                'certificate_rejection','neural_stage_record_pairs','elapsed_ns')} for row in stages])


def summarize_comparison(repair_ns,conversion_ns,prepared_ns,original_model_ns,cold_times,compressed_bytes,lossless_bytes,lossless_repair_ns):
    require(set(cold_times) == set(COLD_REFERENCES),'all three registered cold times are required')
    for value in (repair_ns,conversion_ns,prepared_ns,original_model_ns,*cold_times.values(),compressed_bytes,lossless_bytes,lossless_repair_ns):
        require(type(value) is int and value > 0,'comparison costs and sizes require positive integers')
    fastest = min(cold_times.values())
    preparation = prepared_ns+conversion_ns
    overhead = preparation-original_model_ns
    return dict(cold_comparators=[dict(external=name,controller_seconds=cold_times[name]/1e9,
            cold_over_compressed_repair=cold_times[name]/repair_ns) for name in COLD_REFERENCES],
        minimum_cold_seconds=fastest/1e9,minimum_cold_over_compressed_repair=fastest/repair_ns,
        repair_seconds=repair_ns/1e9,conversion_seconds=conversion_ns/1e9,
        lossless_repair_seconds=lossless_repair_ns/1e9,lossless_over_compressed_repair=lossless_repair_ns/repair_ns,
        lossless_preparation_seconds=prepared_ns/1e9,complete_compressed_preparation_seconds=preparation/1e9,
        original_model_only_seconds=original_model_ns/1e9,preparation_incremental_overhead_seconds=overhead/1e9,
        one_request_prepared_total_seconds=(preparation+repair_ns)/1e9,
        one_request_cold_totals_seconds={name:(original_model_ns+value)/1e9 for name,value in cold_times.items()},
        storage=dict(compressed_complete_state_bytes=compressed_bytes,lossless_complete_state_bytes=lossless_bytes,
            saved_bytes=lossless_bytes-compressed_bytes,relative_reduction=(lossless_bytes-compressed_bytes)/lossless_bytes,
            scope='complete successor state, including model; common base checkpoint and audit archive excluded'),
        latency_gate_passed=repair_ns<fastest,storage_gate_passed=compressed_bytes<lossless_bytes,
        combined_pilot_gate_passed=repair_ns<fastest and compressed_bytes<lossless_bytes,
        replication_scope='one compressed repair; three earlier matched cold observations; no repair replication',
        changing_state_lifetime_benefit_established=False,population_superiority_established=False)


def verify_compressed_claims(result,plan,program,reference):
    require(result.get('schema') == SCHEMA and result.get('status') == 'complete','compressed terminal kind differs')
    require(result.get('method') == plan['method'] and result.get('source_sha256') == program['source_sha256'],
            'compressed terminal policy source differs')
    for key in ('complete_model','complete_state','model_roundtrip_exact','state_roundtrip_canonical','trusted_preparation_required'):
        require(result.get(key) is True,'compressed output verification missing: '+key)
    for key in ('confirmation','scientific_promotion','use_candidates'):
        require(result.get(key) is False,'compressed scientific policy differs: '+key)
    for key in ('inputs','decoder_backend','codec_bits','block_size','certificate_backend','solver_backend','solver_budget',
                'sparse_budget','max_point_work_units','max_certificate_work_units','max_certificate_workspace_bytes',
                'max_neural_stage_record_pairs','original_token_count'):
        require(result.get(key) == plan[key],'compressed policy differs: '+key)
    require(result['fixed_target_sha256'] == plan['expected_target'],'compressed target differs')
    require(result['retained_record_ids'] == result['committed_record_ids'] == plan['record_ids']
        and result['deleted_record_ids'] == plan['deleted_ids'],'compressed membership differs')
    for key in ('fixed_target_sha256','base_target_sha256','checkpoint_files_sha256','target_recipe','evaluator_id',
                'original_token_count','original_record_ids','original_records_sha256','records_input_sha256',
                'stage_count','stage_ids','model_code_elements','retained_record_ids','retained_token_count','deleted_record_ids',
                'preparer_sha256','decoder_implementation_manifest','decoder_implementation_sha256'):
        require(result.get(key) == reference.get(key),'compressed/reference science differs: '+key)
    require(result['stage_count'] == 24 and len(set(result['stage_ids'])) == 24,'compressed model incomplete')
    require(set(result['artifacts']) == {'model','state'}
        and all(result['artifacts'][kind] == result[kind+'_artifact'] for kind in ('model','state')),'artifact mappings differ')
    actual,expected = result['model_artifact'],reference['model_artifact']
    require((actual['bytes'],actual['sha256']) == (expected['bytes'],expected['sha256']),'compressed complete model differs')
    # Conversion has no neural service; bind its copied implementation explicitly.
    adapted = dict(result,diagnostics=dict(result['diagnostics'],
        preparer_sha256=result['preparer_sha256'],decoder_implementation_manifest=result['decoder_implementation_manifest']))
    verify_implementation(adapted,program)
    if plan['method'] == 'repair':
        require(result.get('retained_reference_model_byte_equal') is True,'full retained byte comparison is missing')
        require(result['diagnostics'].get('decoder_implementation_manifest') == result['decoder_implementation_manifest']
            and result['diagnostics'].get('preparer_sha256') == result['preparer_sha256'],'actual repair implementation differs')
    return verify_diagnostics(result,plan)


def analyze(campaign):
    started = time.process_time_ns();campaign = Path(campaign).absolute()
    program_raw,protocol_raw = (campaign/'program.json').read_bytes(),(campaign/'protocol.json').read_bytes()
    program,protocol = strict_json(program_raw),strict_json(protocol_raw)
    program_hash,protocol_hash = digest(program_raw),digest(protocol_raw)
    registration = read_json(campaign/'registration.json')
    require(registration['program_sha256'] == program_hash and registration['protocol_sha256'] == protocol_hash
        and protocol['program_sha256'] == program_hash,'registration binding differs')
    require(protocol['phase_cpu_seconds'] == {'feasibility':program['phase_cpu_cap_seconds']},'phase CPU cap differs')
    require(tuple(row['id'] for row in program['trials']) == TRIALS,'compressed trial registration differs')
    require({p.name for p in (campaign/'attempts').iterdir() if p.is_dir()} == set(TRIALS),'complete two-trial evidence is required')
    require(source_hashes(campaign/'source') == program['source_sha256'],'frozen compressed source differs')
    evidence = {};cache = {}
    def bind(path):
        path = Path(path).absolute();key = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        evidence[key] = hashed(path)
    for name in ('program.json','protocol.json','registration.json','registered-launcher.py'):
        bind(campaign/name)
    for name,sha in program['controller_sha256'].items():
        require(hashed(campaign/'source'/name) == sha,'frozen controller differs: '+name);bind(campaign/'source'/name)
        if name.startswith('scripts/launch_'):
            require(hashed(campaign/'registered-launcher.py') == sha,'registered launcher differs')
    for name,sha in program['historical_frozen_ledgers'].items():
        require(hashed(ROOT/name) == sha,'historical ledger changed: '+name);bind(ROOT/name)
    external = verify_external(program,bind,cache)
    rows,results,receipts,times = [],{},[],{}
    for trial in program['trials']:
        name = trial['id'];attempt = campaign/'attempts'/name
        require(trial['script'] == 'run_compressed_service_v30.py'
            and trial['plan']['method'] == ('convert_lossless' if name == 'convert-256' else 'repair'),'trial method differs')
        verify_trial_external_inputs(trial,program)
        archive = verified_archive(attempt,bind,cache)
        result,plan,transaction,receipt = (archive[k] for k in ('result','plan','transaction','receipt'))
        common.verify_plan(campaign,trial,plan,program,program_hash,protocol_hash,results)
        reference_name = 'original' if name == 'convert-256' else 'retained_cold'
        require(trial['compare_external'] == [dict(external=reference_name,artifacts=['model'])],'registered model gate differs')
        diagnostics = verify_compressed_claims(result,plan,program,external[reference_name]['result'])
        for dependency in trial.get('depends',[]):
            require(dependency['trial'] in results,'compressed dependency did not complete earlier')
            for key,value in dependency.get('equals',{}).items():
                require(nested(results[dependency['trial']],key) == value,'compressed dependency gate failed')
        times[name] = transaction['controller_elapsed_ns']
        rows.append(dict(trial=name,method=result['method'],controller_seconds=times[name]/1e9,
            observed_cpu_seconds=receipt['resource_usage']['total_cpu_ns']/1e9,
            charged_cpu_seconds=receipt['budget_debit']['charged_cpu_seconds'],artifacts=result['artifacts'],
            diagnostics=diagnostics,worker_seconds=result['worker_transaction_elapsed_ns']/1e9))
        results[name] = result;receipts.append(receipt)
        for path in sorted(attempt.rglob('*')):
            if path.is_file() and path.suffix in ('.json','.txt','.log'):bind(path)
    budget = common.verify_final_budget(campaign,program,protocol_hash,receipts);bind(campaign/'phase-cpu-budget/ledger.json')
    original = external['original'];ordered_campaign = original['attempt'].parent.parent
    baseline = verified_archive(ordered_campaign/'attempts/original-model-256',bind,cache)
    for key in ('model_artifact','fixed_target_sha256','base_target_sha256','target_recipe','retained_record_ids',
                'solver_backend','solver_budget','decoder_implementation_manifest','preparer_sha256'):
        require(baseline['result'][key] == original['result'][key],'matched original model-only baseline differs: '+key)
    require(baseline['result']['method'] == 'model_only_fresh','original model-only cost has the wrong output contract')
    cold_times = {key:external[key]['transaction']['controller_elapsed_ns'] for key in COLD_REFERENCES}
    summary = summarize_comparison(times['repair-128'],times['convert-256'],original['transaction']['controller_elapsed_ns'],
        baseline['transaction']['controller_elapsed_ns'],cold_times,results['repair-128']['state_artifact']['bytes'],
        external['retained_lossless']['result']['state_artifact']['bytes'],
        external['retained_lossless']['transaction']['controller_elapsed_ns'])
    repair_trial = program['trials'][1]
    require(repair_trial['storage_gate'] == dict(artifact='state',external='retained_lossless',strictly_smaller=True)
        and repair_trial['latency_gate'] == dict(aggregation='minimum_recorded_controller_elapsed_ns',
            externals=list(COLD_REFERENCES),strictly_faster=True),'registered scientific gate policy differs')
    # Recompute the controller sidecar using the exact frozen gate function.
    import importlib.util
    spec = importlib.util.spec_from_file_location('_compressed_frozen_controller',campaign/'registered-launcher.py')
    controller = importlib.util.module_from_spec(spec);spec.loader.exec_module(controller)
    gates = controller.scientific_gates(repair_trial,results['repair-128'],program['external_attempts'],
        read_json(campaign/'attempts/repair-128/transaction.json'))
    require(gates['checks']['storage']['passed'] == summary['storage_gate_passed']
        and gates['checks']['latency']['passed'] == summary['latency_gate_passed'],'controller scientific gates disagree')
    sidecar = campaign/'attempts/repair-128/scientific-gates.json'
    require(read_json(sidecar) == gates,'saved scientific gate receipt differs');bind(sidecar)
    source_files = ('scripts/analyze_compressed_service_v30.py','scripts/analyze_full_service_v30.py',
        'scripts/analyze_ordered_service_v30.py','src/service_terminal_evidence_v30.py','src/phase_budget.py',
        'src/run_store.py','src/experiment_inventory.py')
    checkpoint_bytes = sum(Path(external['retained_cold']['plan']['inputs'][name]['path']).stat().st_size
                           for name in ('config','weights'))
    return dict(schema='compressed-complete-service-audit-v30',status='complete',confirmation=False,
        scientific_promotion=False,program_sha256=program_hash,protocol_sha256=protocol_hash,trials=rows,
        exact_complete_model_agreement=True,registered_scientific_gates=gates,quality_prerequisite_passed=True,
        phase_budget=budget,phase_accounting=dict(cap_seconds=program['phase_cpu_cap_seconds'],
            charged_seconds=budget['charged_cpu_seconds']['feasibility'],settled_receipts=2,unresolved_reservations=0,
            remaining_seconds=program['phase_cpu_cap_seconds']-budget['charged_cpu_seconds']['feasibility'],
            historical_ledgers_unchanged=True,analysis_cpu_excluded_from_worker_ledger=True),
        complete_storage_context=dict(common_base_checkpoint_bytes=checkpoint_bytes,base_checkpoint_still_required=True,
            exported_model_bytes=results['repair-128']['model_artifact']['bytes'],
            original_lossless_state_bytes=original['result']['state_artifact']['bytes'],
            original_compressed_state_bytes=results['convert-256']['state_artifact']['bytes'],
            retained_compressed_state_plus_base_bytes=checkpoint_bytes+results['repair-128']['state_artifact']['bytes'],
            retained_lossless_state_plus_base_bytes=checkpoint_bytes+external['retained_lossless']['result']['state_artifact']['bytes'],
            state_already_contains_calibrated_model=True,audit_archive_excluded=True),
        supplemental_lifetime_baseline=dict(attempt=str(baseline['attempt']),
            completion_sha256=hashed(baseline['attempt']/'outputs/completion.json'),
            scope='matched original model-only trial from the registered ordered phase; no new measurement'),
        timing_scope='complete controller transactions; evidence closure verification and oracle artifact reads remain included',
        target_scope='fixed nearest-anchor features; distinct from sequential calibration',
        evidence_sha256=evidence,analysis_source_sha256={name:hashed(ROOT/name) for name in source_files},
        analysis_cpu_ns=time.process_time_ns()-started,**summary)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign',type=Path,default=ROOT/'campaigns/compressed_service_v30')
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args();report = analyze(args.campaign)
    with args.output.open('xb') as stream:stream.write(canonical_json(report))
    print(json.dumps({key:report[key] for key in ('status','combined_pilot_gate_passed',
        'minimum_cold_over_compressed_repair','preparation_incremental_overhead_seconds','analysis_cpu_ns')}))
