"""Bounded first-stage controls for exact speculative dyadic quantization."""
import argparse
from dataclasses import fields
import hashlib
import json
from pathlib import Path
import resource
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.run_store import atomic_write, canonical_json, digest
from src.experiment_inventory import source_hashes
from src.transaction_timing import verify_command_admission


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_bytes())
    root = Path(__file__).resolve().parents[1]
    if source_hashes(root) != plan['source_sha256']:
        raise ValueError('source binding mismatch')
    verify_command_admission(plan['protocol_sha256'], 'feasibility',
        [sys.executable, str(Path(__file__).resolve()), str(args.plan.absolute())])
    output = Path(plan['output'])
    output.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter_ns()
    result = dict(schema='speculative-first-stage-v16', status='running',
        plan_sha256=digest(args.plan.read_bytes()), scientific_promotion=False,
        complete_model=False, complete_state=False, changed_ancestor_avoidance_claim=False,
        timing_scope='in-process stage solver calls; complete service and prior-state loading excluded',
        phases=[], datasets=[], variant_failures=0)

    def save(phase, **details):
        event = dict(phase=phase, elapsed_ns=time.perf_counter_ns()-start, **details)
        result['phases'].append(event)
        result['peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        atomic_write(output/'progress.json', canonical_json(result))
        print(json.dumps(event), flush=True)

    def diagnostic(outcome):
        return {field.name: getattr(outcome, field.name) for field in fields(outcome) if field.name != 'codes'}

    def code_info(codes):
        raw = codes.astype('<f8', copy=False).tobytes()
        return dict(shape=list(codes.shape), values=int(codes.size), bytes=len(raw), sha256=digest(raw))

    try:
        save('input_validation')
        cp = Path(plan['checkpoint'])
        for name, expected in plan['checkpoint_sha256'].items():
            with (cp/name).open('rb') as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            if actual != expected:
                raise ValueError('checkpoint bytes changed')
        frozen = []
        for entry in plan['datasets']:
            raw = Path(entry['records']).read_bytes()
            if digest(raw) != entry['records_sha256']:
                raise ValueError('record bytes changed')
            payload = json.loads(raw)
            records = sorted(payload['records'], key=lambda row: row['id'])
            if (len(records) != 2 or len({row['id'] for row in records}) != 2
                    or any(len(row['tokens']) != 16 for row in records)):
                raise ValueError('the stage pilot requires two distinct frozen sixteen-token records')
            if entry['deleted_record_id'] != records[0]['id']:
                raise ValueError('the deletion differs from the prospectively fixed first ID')
            frozen.append((entry, payload, records))
        import numpy as np
        from src.checkpoint_adapter import load_gpt2_checkpoint
        from src.certified_transformer import CertifiedDecoder
        from src.target_manifest import TargetRecipe
        from src.dyadic_row_target import build_dyadic_row_target
        from src.dyadic_row_quantizer import quantize_dyadic_rows
        from src.speculative_dyadic_solver import speculative_quantize_dyadic_rows
        from src.ordered_finite import FiniteWeights
        from src.sequential_finite import sequential_features

        tick = time.perf_counter_ns()
        loaded = load_gpt2_checkpoint(cp, identity_encoding='binary64_tree_v2')
        decoder = CertifiedDecoder(loaded.decoder, primitive_backend='mpfr_enclosure')
        target = build_dyadic_row_target(decoder, TargetRecipe(original_token_count=32, group_count=1))
        result['load_and_target_elapsed_ns'] = time.perf_counter_ns()-tick
        atomic_write(output/'target.json', canonical_json(target.payload()))
        atomic_write(output/'evaluator.json', canonical_json(decoder.kernel_manifest))
        stage = target.stages[0]
        if stage.stage_id != 'block.0000.qkv' or stage.dependencies:
            raise ValueError('the registered independent first qkv stage differs')
        weights = FiniteWeights(stage.weights).array()
        options = dict(bits=stage.bits, significant_bits=24, ridge=stage.ridge,
            normalization=stage.normalization, max_exact_rank=64,
            max_exact_coordinates=16, max_refinement_coordinates=64)
        result.update(target_sha256=target.digest, stage_id=stage.stage_id,
            evaluator_id=decoder.evaluator_id, weight_shape=list(weights.shape))
        save('target_constructed')

        def extract(records):
            values = []
            for row in records:
                stream = sequential_features(decoder, row['tokens'])
                sid, factor = next(stream)
                stream.close()
                if sid != stage.stage_id:
                    raise ValueError('the extracted stage differs')
                values.append(np.asarray(factor, dtype=np.float64))
            return np.concatenate(values, axis=0).T.copy()

        for entry, payload, original_records in frozen:
            name = entry['dataset']
            retained_records = original_records[1:]
            row = dict(dataset=name, status='running', provenance=payload.get('provenance'),
                records_sha256=entry['records_sha256'],
                original_record_ids=[item['id'] for item in original_records],
                retained_record_ids=[item['id'] for item in retained_records],
                deleted_record_id=entry['deleted_record_id'], original_tokens=32, retained_tokens=16,
                variants=[], comparison_order=entry['comparison_order'])
            result['datasets'].append(row)
            save('dataset_started', dataset=name)
            tick = time.perf_counter_ns()
            original_features = extract(original_records)
            row['original_features_elapsed_ns'] = time.perf_counter_ns()-tick
            tick = time.perf_counter_ns()
            retained_features = extract(retained_records)
            row['retained_features_elapsed_ns'] = time.perf_counter_ns()-tick
            row['retained_features_match_original_slice'] = bool(np.array_equal(original_features[:, 16:], retained_features))
            if not row['retained_features_match_original_slice']:
                raise ArithmeticError('calibration-independent first-stage factors differ')
            row['original_features'] = code_info(original_features)
            row['retained_features'] = code_info(retained_features)
            save('features_complete', dataset=name)

            tick = time.perf_counter_ns()
            original = quantize_dyadic_rows(weights, original_features, stage.scale_values, **options)
            row['original_reference_solver_elapsed_ns'] = time.perf_counter_ns()-tick
            row['original_reference_diagnostics'] = diagnostic(original)
            row['original_codes'] = code_info(original.codes)
            atomic_write(output/f'{name}.original.codes.bin', original.codes.astype('<f8', copy=False).tobytes())
            save('original_reference_complete', dataset=name)
            tick = time.perf_counter_ns()
            reference = quantize_dyadic_rows(weights, retained_features, stage.scale_values, **options)
            row['retained_reference_solver_elapsed_ns'] = time.perf_counter_ns()-tick
            row['retained_reference_diagnostics'] = diagnostic(reference)
            row['retained_codes'] = code_info(reference.codes)
            row['original_to_retained_changed_codes'] = int(np.count_nonzero(original.codes != reference.codes))
            atomic_write(output/f'{name}.retained.codes.bin', reference.codes.astype('<f8', copy=False).tobytes())
            row['candidate_preparation_elapsed_ns'] = (
                row['original_features_elapsed_ns'] + row['original_reference_solver_elapsed_ns'])
            row['candidate_preparation_scope'] = 'original feature extraction and original sequential quantization; excludes common checkpoint/target setup and artifact writes'
            save('retained_reference_complete', dataset=name)

            for cell in entry['comparison_order']:
                variant = dict(method=cell['method'], max_sweeps=cell['max_sweeps'],
                    row_batch_size=plan['row_batch_size'], status='running')
                row['variants'].append(variant)
                save('variant_started', dataset=name, method=cell['method'], max_sweeps=cell['max_sweeps'])
                tick = time.perf_counter_ns()
                try:
                    outcome = speculative_quantize_dyadic_rows(weights, retained_features, stage.scale_values,
                        candidate=original.codes if cell['method']=='prior_codes' else None,
                        max_sweeps=cell['max_sweeps'], row_batch_size=plan['row_batch_size'], **options)
                except Exception as exc:
                    variant.update(status='failed', solver_elapsed_ns=time.perf_counter_ns()-tick,
                        error_type=type(exc).__name__, error=str(exc))
                    result['variant_failures'] += 1
                    save('variant_failed', dataset=name, method=cell['method'], max_sweeps=cell['max_sweeps'])
                    continue
                variant.update(status='complete', solver_elapsed_ns=time.perf_counter_ns()-tick,
                    diagnostics=diagnostic(outcome), codes=code_info(outcome.codes),
                    unequal_values=int(np.count_nonzero(outcome.codes != reference.codes)))
                if variant['unequal_values']:
                    variant['status'] = 'mismatch'
                    save('variant_mismatch', dataset=name, method=cell['method'], max_sweeps=cell['max_sweeps'])
                    raise ArithmeticError('a speculative variant differs from the sequential reference')
                save('variant_complete', dataset=name, method=cell['method'], max_sweeps=cell['max_sweeps'],
                    solver_elapsed_ns=variant['solver_elapsed_ns'],
                    prefix_verified_decisions=outcome.prefix_verified_decisions,
                    fallback_decisions=outcome.fallback_decisions)
            row['status'] = 'complete' if all(v['status']=='complete' for v in row['variants']) else 'complete_with_failed_variants'
            save('dataset_complete', dataset=name)
        result['status'] = 'complete' if result['variant_failures']==0 else 'complete_with_failed_variants'
        save('complete')
    except Exception as exc:
        result.update(status='failed', error_type=type(exc).__name__, error=str(exc))
        save('failed')
        raise


if __name__ == '__main__':
    main()
