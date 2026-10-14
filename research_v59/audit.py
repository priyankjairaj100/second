"""Read-only actual-byte, target, loss, progress and settled-CPU audit.

This verifies artifacts under the trusted frozen implementation. It does not
rerun neural inference or calibration and is not an independent numerical proof.
"""
import os
from pathlib import Path
import sys
import time

from research_v54.postrun import Inputs, bind_ledger_snapshot, verify_kernel
from research_v55.audit import check_prefix
from research_v59.campaign import ROOT, verify, require, new, bound
from research_v59.diagnostic import (
    check_progress, check_result, first_stage_invariant, reconstruct_candidate,
    reconstruct_fixed, reconstruct_sequential,
)
from src.experiment_inventory import source_hashes
from src.phase_budget import read_budget_snapshot
from src.run_store import canonical_json, digest, read_completed


ARTIFACTS = {'sequential-target.json', 'fixed-target.json', 'execution-provenance.json',
    'historical-parity.json', 'candidate-target.json', 'candidate-model.bin',
    'candidate-model-metadata.json', 'candidate-diagnostics.json', 'first-stage-invariant.json'}


def check_candidate_target(target, base, execution, *, constructor_sha256):
    """Reconstruct the target contract from the pinned base, without a decoder."""
    from research_v59.anchor import FEATURE_RULE, ANCHOR_RULE
    from research_v43.dispatcher import StageSpec
    base_hash = digest(canonical_json(base))
    require(base['evaluator_id'] == 'certified-decoder-v1:'+digest(canonical_json(execution['decoder'])),
        'Execution decoder differs from the frozen base evaluator')
    require(len(base['stages']) == 24 and base['recipe']['original_token_count'] == 1664
        and base['recipe']['bits'] == 4 and base['recipe']['ridge'] == [1, 100]
        and base['recipe']['group_count'] == 1 and base['significant_bits'] == 24
        and base['weight_digest_encoding'] == 'binary64_matrix_v1', 'Frozen base recipe or extent differs')
    seen, teachers = [], []
    for entry in base['stages']:
        spec = StageSpec.from_manifest(entry, target_sha256=base_hash)
        require(len(entry['dependencies']) == len(seen) and set(entry['dependencies']) == set(seen)
            and spec.normalization == 1664 and spec.ridge.numerator == 1
            and spec.ridge.denominator == 100, 'Frozen base stage recipe or dependency order differs')
        seen.append(spec.stage_id)
        teachers.append(dict(stage_id=spec.stage_id, shape=[spec.rows, spec.width], weights_sha256=spec.weights_sha256))
    expected = dict(schema='fixed-full-precision-anchor-calibration-target-v59', base_target_sha256=base_hash,
        decoder_sha256=digest(canonical_json(execution['decoder'])),
        implementation_manifest_sha256=digest(canonical_json(execution['implementation'])),
        constructor_source_sha256=constructor_sha256, feature_rule=FEATURE_RULE, anchor_rule=ANCHOR_RULE,
        prefix_rule='calibrated output codes never affect any feature', calibrated_dependencies='empty for every stage',
        original_normalization=1664, normalization_rule='unchanged original normalization from base target',
        grid_rule='unchanged base-only dyadic24 output-row grids; lower midpoint ties',
        record_rule='positions reset per source; causal within source; no cross-source state',
        teacher_weight_digest_encoding='binary64-matrix-little-endian-row-major-v1', teacher_stages=teachers,
        output_rule='complete stage codes only; no canonical repair-state contract declared',
        failure_rule='bounded certified stage solver; unresolved or exhausted resource budget aborts')
    require(target == expected, 'Candidate target does not bind the exact full-precision teacher contract')
    return digest(canonical_json(target))


def check_candidate_diagnostics(diagnostics, stages, target, base):
    """Re-derive complete admission reports and bind original teacher parents."""
    from research_v43.dispatcher import ResourcePolicy, StageSpec, assess_stage
    from research_v59.anchor import FEATURE_RULE, ANCHOR_RULE
    target_hash = digest(canonical_json(target))
    require(diagnostics['schema'] == 'full-precision-anchor-calibration-v59'
        and diagnostics['target_sha256'] == target_hash and diagnostics['base_target_sha256'] == digest(canonical_json(base))
        and diagnostics['feature_rule'] == FEATURE_RULE and diagnostics['anchor_rule'] == ANCHOR_RULE
        and diagnostics['implementation'] == 'ordered-finite-decoder-v30'
        and diagnostics['implementation_manifest_sha256'] == target['implementation_manifest_sha256']
        and diagnostics['records'] == 6 and diagnostics['retained_tokens'] == 768
        and diagnostics['original_normalization'] == 1664 and diagnostics['neural_stage_record_pairs'] == 144
        and diagnostics['prior_model_access'] is False and diagnostics['prior_factor_access'] is False
        and diagnostics['calibrated_prefix_access'] is False and not diagnostics.get('aborted', False),
        'Candidate execution scope or feature rule differs')
    require(len(stages) == len(diagnostics['stages']) == len(diagnostics['point_admission']) == len(base['stages']) == 24,
        'Candidate complete stage diagnostics required')
    policy, reports = ResourcePolicy(), []
    for index, (stage, entry, row, admission) in enumerate(zip(stages, base['stages'], diagnostics['stages'], diagnostics['point_admission'])):
        spec = StageSpec.from_manifest(entry, target_sha256=target_hash)
        expected = assess_stage(spec, 768, kind='point', block_tokens=128, max_blocks=6,
            policy=policy, resident_bytes=4*2**30)
        require(admission == expected and expected['admitted'] is True, 'Candidate stage admission does not reproduce')
        reports.append(expected)
        require(stage.stage_id == row['stage_id'] == spec.stage_id and stage.shape == (spec.rows, spec.width)
            and stage.scale_values == spec.scale_values and stage.grid_axis == 'dyadic_row' and stage.bits == 4
            and row['feature_tokens'] == 768 and row['input_width'] == spec.width and row['output_rows'] == spec.rows
            and row['route'] == expected['selected_route']
            and row['teacher_parent_stage_id'] == (base['stages'][index-1]['stage_id'] if index else None)
            and row['teacher_parent_weights_sha256'] == (base['stages'][index-1]['weights_sha256'] if index else None)
            and row['output_code_sha256'] == digest(stage.packed_indices),
            'Candidate teacher parent, grid, output bytes or route differs')
        require(type(row['solver_diagnostics']) is dict and bool(row['solver_diagnostics']), 'Missing bounded solver diagnostics')
        for key in ('feature_elapsed_ns', 'solver_elapsed_ns', 'elapsed_ns'):
            require(type(row[key]) is int and row[key] >= 0, 'Invalid candidate stage timing')
        require(row['elapsed_ns'] >= row['feature_elapsed_ns']+row['solver_elapsed_ns'], 'Candidate stage timing is inconsistent')
    require(sum(r['work_units'] for r in reports) <= policy.max_request_work_units, 'Candidate total request admission exceeded')
    require(type(diagnostics['admission_elapsed_ns']) is int and diagnostics['admission_elapsed_ns'] >= 0
        and type(diagnostics['service_elapsed_ns']) is int
        and diagnostics['service_elapsed_ns'] >= diagnostics['admission_elapsed_ns']+sum(r['elapsed_ns'] for r in diagnostics['stages']),
        'Candidate complete-construction timing is inconsistent')
    return dict(complete_stages=24, neural_stage_record_pairs=144,
        total_reserved_work_units=sum(r['work_units'] for r in reports),
        maximum_explicit_array_bytes=max(r['explicit_array_bytes'] for r in reports),
        calibrated_outputs_never_installed=True, complete_admissions_rederived=True)


def check_worker_receipt(directory, program, inputs, snapshot):
    """Read the single sealed literal command and its settled debit."""
    directory = Path(directory)
    ph = digest(canonical_json(program))
    root, out = directory/'quality', directory/'quality/outputs'
    identity = inputs.json(root/'worker/identity.json')
    tx, plan = inputs.json(root/'transaction.json'), inputs.json(root/'plan.json')
    require(identity['identity'] == dict(program_sha256=ph) and identity['cwd'] == str(ROOT)
        and identity['command'] == [sys.executable, '-B', '-m', 'research_v59.worker', str(root/'plan.json')]
        and identity['phase_budget'] == dict(directory=str(directory/'budget'), phase='development', binding_sha256=snapshot['binding_sha256']),
        'Sealed V59 command or phase binding differs')
    limits = identity['limits']
    require(limits['cpu_seconds'] == program['worker_cpu_seconds'] and limits['wall_seconds'] == program['worker_wall_seconds']
        and limits['address_space_bytes'] == program['process_address_space_bytes'] and limits['file_size_bytes'] == program['file_size_bytes']
        and limits['threads'] == 1 and len(limits['affinity_cpus']) == 1, 'Worker limits differ')
    sealed = read_completed(root/'worker', identity)
    require(sealed is not None and sealed['outcome'] == tx['worker_outcome']
        and sealed['outcome']['status'] == 'complete' and sealed['outcome']['returncode'] == 0, 'Worker did not complete')
    require(inputs.json(root/'worker/result.json') == sealed == inputs.json(root/'worker'/sealed['attempt']/'status.json'),
        'Terminal seal differs')
    for name, entry in sealed['artifacts'].items():
        require(inputs.read(root/'worker'/sealed['attempt']/name, retain=False) == entry, 'Sealed controller artifact differs')
    require(snapshot['attempts'] == {sealed['budget_attempt_id']: sealed['budget_debit']}
        and sealed['budget_debit']['observed_cpu_ns'] == sealed['resource_usage']['total_cpu_ns'], 'Single settled CPU debit differs')
    ledger_keys = {'binding_sha256', 'phase_cpu_seconds', 'charged_cpu_seconds', 'attempts', 'over_cap'}
    require(set(tx['budget']) == ledger_keys and all(tx['budget'][k] == snapshot[k] for k in ledger_keys),
        'Transaction ledger differs')
    require(plan == dict(schema='full-precision-anchor-quality-plan-v59', directory=str(directory),
        program=str(directory/'program.json'), program_sha256=ph, output=str(out), slurm_job_id=tx['slurm_job_id']),
        'Worker plan differs')
    return sealed, plan


def audit(directory, output):
    require(os.environ.get('SLURM_JOB_ID') and sys.platform == 'linux', 'Audit requires a bounded Linux Slurm allocation')
    directory, output = Path(directory).resolve(), Path(output).resolve()
    require(not output.exists(), 'Fresh audit path required')
    tick, cpu, inputs = time.perf_counter_ns(), time.process_time_ns(), Inputs()
    p = inputs.json(directory/'program.json')
    ph = digest(canonical_json(p))
    verified, registration, previous_program, records, previous_completion = verify(directory)
    require(verified == p and inputs.json(directory/'registration.json') == registration
        and registration['program_sha256'] == ph, 'Frozen registration differs')
    for entry in p['inputs'].values():
        require(inputs.read(bound(entry), retain=False) == dict(bytes=entry['bytes'], sha256=entry['sha256']), 'Bound audit input differs')
    for name, expected in p['sources'].items():
        require(inputs.read(ROOT/name, retain=False)['sha256'] == expected, 'Bound numerical source differs')
    snapshot = read_budget_snapshot(directory/'budget', identity=dict(protocol_sha256=ph, source_sha256=source_hashes(ROOT)),
        phase_cpu_seconds={'development': p['phase_cpu_seconds']})
    require(snapshot['status'] == 'verified' and not snapshot['reserved_unknown_attempts'] and not any(snapshot['over_cap'].values()),
        'CPU ledger unsettled or over cap')
    bind_ledger_snapshot(directory, snapshot, inputs)
    sealed, plan = check_worker_receipt(directory, p, inputs, snapshot)
    out = directory/'quality/outputs'
    c = inputs.json(out/'completion.json')
    require(c['schema'] == 'full-precision-anchor-quality-worker-v59' and c['program_sha256'] == ph
        and c['slurm_job_id'] == plan['slurm_job_id'] and c['original_normalization'] == 1664
        and c['retained_calibration_tokens'] == 768 and c['code_count'] == 42_467_328
        and c['fixed_model_sha256'] == p['inputs']['v54_model']['sha256']
        and c['sequential_model_sha256'] == p['inputs']['v55_sequential_model']['sha256']
        and c['shared_evaluator_sha256'] == p['sources']['scripts/run_quality_v30.py']
        and c['confirmation'] is False and c['acl_ready'] is False and c['intervals'] is False
        and c['certified_inference'] is False and c['approximate_numpy_binary64_likelihood'] is True
        and c['no_new_quality_inputs'] is True and c['repair_service'] is False
        and c['feature_drift_traversals'] is False and c['candidate_count'] == 1,
        'Worker extent or development scope differs')
    from research_v43.dispatcher import ResourcePolicy
    require(c['candidate_resource_policy'] == ResourcePolicy().__dict__, 'Candidate resource policy differs')
    verify_kernel(c['shared_primal_kernel'])
    require(set(c['artifacts']) == ARTIFACTS, 'Complete candidate artifact inventory required')
    for name, entry in c['artifacts'].items():
        require(entry == dict(file=name, **inputs.read(out/name, retain=False)), 'Candidate artifact bytes differ')
    require(inputs.json(bound(p['inputs']['v55_completion'])) == previous_completion
        and inputs.json(bound(p['inputs']['v55_program'])) == previous_program
        and records == p['records'], 'Previous control receipt or exposure differs')
    summary = check_result(c, previous_completion, inputs.json(out/'historical-parity.json'))

    base_blob, fixed_blob = inputs.read(out/'sequential-target.json'), inputs.read(out/'fixed-target.json')
    require(base_blob == inputs.read(bound(p['inputs']['v55_sequential_target']))
        and fixed_blob == inputs.read(bound(p['inputs']['v55_fixed_target']))
        and c['sequential_target_sha256'] == digest(base_blob) and c['fixed_target_sha256'] == digest(fixed_blob),
        'Frozen control target bytes differ')
    # Historical nearest-only state reconstruction is deliberately kept separate
    # from the new full-precision target's manifest and model-code validation.
    from research_v42.resource_plan import BoundTarget
    old_v54 = inputs.json(bound(p['inputs']['v54_program']))
    fixed = reconstruct_fixed(inputs.read(bound(p['inputs']['v54_state'])), inputs.read(bound(p['inputs']['v54_model'])),
        bound_target=BoundTarget(base_blob, fixed_blob), records=p['retained_records'], provenance=old_v54['record_provenance'])
    sequential = reconstruct_sequential(inputs.read(bound(p['inputs']['v55_sequential_model'])),
        inputs.json(bound(p['inputs']['v55_sequential_metadata'])), target_sha256=c['sequential_target_sha256'], fixed=fixed)
    check_prefix(inputs.json(bound(p['inputs']['v55_sequential_diagnostics'])), sequential, c['sequential_target_sha256'])
    base, target = inputs.json(out/'sequential-target.json'), inputs.json(out/'candidate-target.json')
    execution = inputs.json(out/'execution-provenance.json')
    require(inputs.read(out/'execution-provenance.json') == inputs.read(bound(p['inputs']['v55_execution_provenance'])),
        'Candidate execution provenance differs from actual V55 controls')
    from research_v38.bootstrap_target import CHECKPOINT_HASHES
    require(execution['checkpoint']['files_sha256'] == CHECKPOINT_HASHES, 'Actual execution checkpoint differs')
    target_hash = check_candidate_target(target, base, execution, constructor_sha256=p['sources']['research_v59/anchor.py'])
    require(target_hash == c['candidate_target_sha256'] and target_hash not in (c['fixed_target_sha256'], c['sequential_target_sha256']),
        'Candidate must have its own bound target')
    candidate_blob = inputs.read(out/'candidate-model.bin')
    candidate = reconstruct_candidate(candidate_blob, inputs.json(out/'candidate-model-metadata.json'), target_sha256=target_hash, controls=fixed)
    require(len(candidate_blob) == 21_233_664 and sum(s.rows*s.columns for s in candidate) == 42_467_328, 'Incomplete candidate model bytes')
    first = first_stage_invariant(candidate, fixed, sequential, expected_sha256=p['first_stage_packed_sha256'])
    require(first == c['first_stage_invariant'] == inputs.json(out/'first-stage-invariant.json'), 'First-stage invariant receipt differs')
    diagnostics = inputs.json(out/'candidate-diagnostics.json')
    construction = check_candidate_diagnostics(diagnostics, candidate, target, base)
    progress_files = sorted(out.glob('progress-*.json'))
    require([path.name for path in progress_files] == [f'progress-{i:04d}.json' for i in range(c['progress_events'])],
        'Progress files missing, extra or nonconsecutive')
    events = [inputs.json(path) for path in progress_files]
    progress = check_progress(events, c['quality'], diagnostics['stages'], first,
        summary['development_guards_pass'])
    require(events[-1]['worker_elapsed_ns'] <= c['worker_elapsed_ns']
        and c['candidate_construction_elapsed_ns'] >= diagnostics['service_elapsed_ns'], 'Worker timing does not contain reported work')
    require(set(path.name for path in out.iterdir()) == ARTIFACTS | {'completion.json'} | {path.name for path in progress_files},
        'Undeclared candidate output or extra attempt artifact')
    require(c['excluded_from_future_confirmation_ids'] == inputs.json(bound(p['inputs']['historical_exclusions']))['excluded_from_future_confirmation_ids'],
        'Quality exclusion registry differs')
    inputs.unchanged()
    result = dict(schema='full-precision-anchor-quality-artifact-audit-v59', status='verified', campaign=str(directory),
        program_sha256=ph, inputs=inputs.files, summary=summary, development_guards_pass=summary['development_guards_pass'],
        actual_candidate_model_sha256=digest(candidate_blob), actual_model_codes_reconstructed=42_467_328,
        complete_stages=24, candidate_target_sha256=target_hash, first_stage_invariant=first, construction=construction,
        progress=progress, checked_losses=40, historical_control_parity=c['historical_parity'],
        sealed_cpu_receipt_verified=True, budget=snapshot, source_sha256=p['sources'], runtime=p['runtime'],
        slurm_job_id=os.environ['SLURM_JOB_ID'], analysis_cpu_ns=time.process_time_ns()-cpu,
        analysis_elapsed_ns=time.perf_counter_ns()-tick, analysis_outside_empirical_worker_ledger=True,
        confirmation=False, acl_ready=False, repair_service=False,
        scope='Actual fixed, sequential and candidate packed bytes and grids, distinct teacher target, all 40 losses, all 32 parity checks, unchanged guards, ordered progress and settled CPU debit verified. Trusted execution assumed; no independent inference or quantization rerun.')
    new(output, result)
    print(canonical_json(dict(status='verified', development_guards_pass=result['development_guards_pass'], output=str(output))).decode())
    return result


if __name__ == '__main__':
    audit(*sys.argv[1:])
