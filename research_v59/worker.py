"""One bounded teacher-anchor constructor after all 32 frozen control losses.

Only one expanded likelihood prefix is live at a time. All control prefixes are
released before calibration; candidate features perform exactly the anchor
constructor's single ordered traversal per retained source, without drift probes.
"""
import gc
from pathlib import Path
import resource
import sys
import time
import traceback

from research_v59.campaign import ROOT, new, read, sha, verify, bound
from research_v59.diagnostic import (
    CANDIDATE_LABEL, CONTROL_LABELS, first_stage_invariant, parity, reconstruct_candidate,
    reconstruct_fixed, reconstruct_sequential, require, summarize,
)
from src.run_store import canonical_json
from src.transaction_timing import verify_command_admission


def _main(plan_path, kernel):
    plan_path = Path(plan_path).resolve()
    plan = read(plan_path)
    directory = Path(plan['directory']).resolve()
    p, registration, previous_program, records, previous_completion = verify(directory)
    require(plan_path == directory/'quality/plan.json'
        and plan == dict(schema='full-precision-anchor-quality-plan-v59', directory=str(directory),
            program=str(directory/'program.json'), program_sha256=sha(directory/'program.json'),
            output=str(directory/'quality/outputs'), slurm_job_id=plan['slurm_job_id'])
        and registration['program_sha256'] == plan['program_sha256'], 'Candidate worker plan differs')
    verify_command_admission(plan['program_sha256'], 'development',
        [sys.executable, '-B', '-m', 'research_v59.worker', str(plan_path)])
    out = Path(plan['output'])
    out.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter_ns()
    result = dict(schema='full-precision-anchor-quality-worker-v59', status='running',
        shared_primal_kernel=kernel, program_sha256=plan['program_sha256'], slurm_job_id=plan['slurm_job_id'],
        quality={}, artifacts={}, confirmation=False, acl_ready=False, intervals=False,
        approximate_numpy_binary64_likelihood=True, certified_inference=False, no_new_quality_inputs=True,
        repair_service=False, feature_drift_traversals=False, candidate_count=1,
        model_target='one full-precision teacher anchor on retained768/original1664; matched frozen V55 controls',
        shared_evaluator_sha256=sha(ROOT/'scripts/run_quality_v30.py'))

    def artifact(name, blob):
        result['artifacts'][name] = new(out/name, blob, raw=True)

    def mark(phase, **details):
        event = dict(phase=phase, worker_elapsed_ns=time.perf_counter_ns()-start, **details)
        new(out/f'progress-{mark.count:04d}.json', event)
        mark.count += 1
        print(canonical_json(event).decode(), flush=True)
    mark.count = 0

    def evaluate(evaluator, record, label, prefix):
        from scripts.run_quality_v30 import nll_from_logits
        tick = time.perf_counter_ns()
        nll = nll_from_logits(evaluator.logits(record['tokens'], prefix), record['tokens'])
        result['quality'].setdefault(label, []).append(dict(id=record['id'], nll_sum=nll,
            predictions=127, mean_nll=nll/127, elapsed_ns=time.perf_counter_ns()-tick))
        mark('quality_article', model=label, record_id=record['id'], nll_sum=nll)

    try:
        from research_v38.bootstrap_target import CHECKPOINT_HASHES
        from research_v42.resource_plan import BoundTarget
        from research_v43.dispatcher import ResourcePolicy
        from research_v55.audit import check_prefix
        from research_v59.anchor import build_full_precision_anchor_target, calibrate
        from scripts.run_quality_v30 import NumpyQualityDecoder, nearest_prefix
        from scripts.execute_gram_pilot_v35 import public_result
        from src.checkpoint_adapter import load_gpt2_checkpoint
        from src.dyadic_row_target import build_dyadic_row_target
        from src.fixed_anchor_target import build_fixed_anchor_target
        from src.ordered_finite_decoder_v30 import OrderedFiniteDecoder
        from src.target_manifest import TargetRecipe

        checkpoint = bound(p['inputs']['checkpoint_config']).parent
        require(bound(p['inputs']['checkpoint_weights']).parent == checkpoint, 'Checkpoint components must share a directory')
        tick = time.perf_counter_ns()
        loaded = load_gpt2_checkpoint(checkpoint, identity_encoding='binary64_tree_v2')
        require(loaded.provenance['files_sha256'] == CHECKPOINT_HASHES, 'Frozen checkpoint identity changed')
        decoder = OrderedFiniteDecoder(loaded.decoder, primitive_backend='mpfr_enclosure')
        base = build_dyadic_row_target(decoder, TargetRecipe(original_token_count=1664, group_count=1))
        fixed_target = build_fixed_anchor_target(decoder, base)
        base_blob, fixed_blob = canonical_json(base.payload()), canonical_json(fixed_target.payload())
        require(base_blob == bound(p['inputs']['v55_sequential_target']).read_bytes()
            and fixed_blob == bound(p['inputs']['v55_fixed_target']).read_bytes(), 'Actual controls target bytes differ')
        # BoundTarget is used only for the historical nearest-anchor state.
        historical_target = BoundTarget(base_blob, fixed_blob)
        old_v54 = read(bound(p['inputs']['v54_program']))
        fixed = reconstruct_fixed(bound(p['inputs']['v54_state']).read_bytes(),
            bound(p['inputs']['v54_model']).read_bytes(), bound_target=historical_target,
            records=p['retained_records'], provenance=old_v54['record_provenance'])
        sequential = reconstruct_sequential(bound(p['inputs']['v55_sequential_model']).read_bytes(),
            read(bound(p['inputs']['v55_sequential_metadata'])), target_sha256=base.digest, fixed=fixed)
        check_prefix(read(bound(p['inputs']['v55_sequential_diagnostics'])), sequential, base.digest)
        require(tuple(s.stage_id for s in fixed) == tuple(decoder.stage_ids), 'Complete control stage order differs')
        require(p['retained_records'] == previous_program['retained_records']
            and len(p['retained_records']) == 6 and all(len(row['tokens']) == 128 for row in p['retained_records']),
            'Frozen retained calibration sources differ')
        require(records == p['records'], 'Exposed evaluation records differ')
        evaluator = NumpyQualityDecoder(loaded.decoder)
        require(set(evaluator.weights) == {s.stage_id for s in fixed}, 'Evaluator/model stage extent differs')
        policy = ResourcePolicy()
        result.update(context_elapsed_ns=time.perf_counter_ns()-tick, candidate_resource_policy=policy.__dict__,
            fixed_target_sha256=fixed_target.digest, sequential_target_sha256=base.digest,
            fixed_model_sha256=p['inputs']['v54_model']['sha256'],
            sequential_model_sha256=p['inputs']['v55_sequential_model']['sha256'], code_count=42_467_328,
            original_normalization=1664, retained_calibration_tokens=768,
            excluded_from_future_confirmation_ids=read(bound(p['inputs']['historical_exclusions']))['excluded_from_future_confirmation_ids'])
        artifact('sequential-target.json', base_blob)
        artifact('fixed-target.json', fixed_blob)
        execution_blob = canonical_json(dict(decoder=decoder.kernel_manifest,
            implementation=decoder.implementation_manifest, checkpoint=loaded.provenance))
        require(execution_blob == bound(p['inputs']['v55_execution_provenance']).read_bytes(),
            'Actual execution provenance differs from frozen V55 controls')
        artifact('execution-provenance.json', execution_blob)
        del historical_target
        gc.collect()
        mark('targets_and_actual_models_validated')

        for label in CONTROL_LABELS:
            if label == 'full_precision':
                prefix = None
            elif label == 'nearest_rounding':
                prefix = nearest_prefix(loaded.decoder, base.stages)
            else:
                codes = fixed if label == 'fixed_feature' else sequential
                prefix = {s.stage_id: s.array() for s in codes}
            for record in records:
                evaluate(evaluator, record, label, prefix)
            del prefix
            gc.collect()
        result['historical_parity'] = parity(result['quality'], previous_completion)
        artifact('historical-parity.json', canonical_json(result['historical_parity']))
        require(result['historical_parity']['passed'], 'A frozen V55 control changed; candidate construction refused')
        mark('all_historical_controls_passed', checked_losses=32)

        tick = time.perf_counter_ns()
        candidate_target = build_full_precision_anchor_target(decoder, base)
        result['candidate_target_sha256'] = candidate_target.digest
        artifact('candidate-target.json', canonical_json(candidate_target.payload()))
        mark('candidate_construction_started')
        candidate, diagnostics = calibrate(decoder, base, p['retained_records'], policy=policy,
            progress=lambda row: mark('candidate_stage', stage_id=row['stage_id'], elapsed_ns=row['elapsed_ns'],
                output_code_sha256=row['output_code_sha256']))
        artifact('candidate-diagnostics.json', canonical_json(public_result(diagnostics)))
        require(diagnostics['target_sha256'] == candidate_target.digest and len(candidate) == 24
            and sum(s.rows*s.columns for s in candidate) == 42_467_328, 'Candidate construction extent or target differs')
        blob = b''.join(s.packed_indices for s in candidate)
        metadata = dict(target_sha256=candidate_target.digest, stages=[s.metadata() for s in candidate])
        # This consumes actual packed bytes, without expanding a numerical prefix.
        require(reconstruct_candidate(blob, metadata, target_sha256=candidate_target.digest, controls=fixed) == candidate,
            'Candidate export did not reconstruct its codes')
        artifact('candidate-model.bin', blob)
        artifact('candidate-model-metadata.json', canonical_json(metadata))
        del blob
        result['first_stage_invariant'] = first_stage_invariant(candidate, fixed, sequential,
            expected_sha256=p['first_stage_packed_sha256'])
        artifact('first-stage-invariant.json', canonical_json(result['first_stage_invariant']))
        result['candidate_construction_elapsed_ns'] = time.perf_counter_ns()-tick
        mark('candidate_model_validated', first_stage_packed_sha256=result['first_stage_invariant']['packed_sha256'])
        prefix = {s.stage_id: s.array() for s in candidate}
        for record in records:
            evaluate(evaluator, record, CANDIDATE_LABEL, prefix)
        del prefix
        result['summary'] = summarize(result['quality'])
        result.update(status='complete', valid_diagnostic=True,
            development_guards_pass=result['summary']['development_guards_pass'])
        tick = time.perf_counter_ns()
        del candidate, fixed, sequential, codes, evaluator, decoder, loaded, base, fixed_target, candidate_target
        gc.collect()
        result['disposal_elapsed_ns'] = time.perf_counter_ns()-tick
        mark('diagnostic_complete', development_guards_pass=result['development_guards_pass'])
    except Exception as error:
        result.update(status='failed', valid_diagnostic=False, error_type=type(error).__name__,
            error=str(error), traceback=traceback.format_exc())
        diagnostics = getattr(error, 'service_diagnostics', None)
        if diagnostics is not None and 'candidate-diagnostics.json' not in result['artifacts']:
            from scripts.execute_gram_pilot_v35 import public_result
            artifact('candidate-diagnostics.json', canonical_json(public_result(diagnostics)))
        raise
    finally:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        result.update(worker_elapsed_ns=time.perf_counter_ns()-start, max_rss_kib=usage.ru_maxrss,
            cpu_self_seconds=usage.ru_utime+usage.ru_stime, progress_events=mark.count,
            timing_scope='Checkpoint/context, all 32 control losses and parity, one candidate constructor, eight candidate losses, writes and disposal; controller also charges pre-clock verification, terminal commit and exit')
        new(out/'completion.json', result)


def main(plan_path):
    from research_v50.neighbors import enabled
    with enabled() as kernel:
        return _main(plan_path, kernel)


if __name__ == '__main__':
    main(sys.argv[1])
