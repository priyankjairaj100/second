"""Bounded complete-stage scale workers. No historical attempt is reused."""
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path
import re
import resource
import sys
import time
import traceback

from research_v40.policy import (ROOT, WIDTH, ROWS, STAGE, NORMALIZATION, TOKENS,
    require, read, sha, new, gram_budget, point_budget, verify_sources)
from src.run_store import canonical_json, digest
from src.runtime_contract import capture_runtime_contract
from src.transaction_timing import verify_command_admission


from research_v39.worker import scientific_refusal, load_context, features


def preparation(plan, record, artifact, mark):
    import numpy as np
    from src import fixed_lossless_codec_v29 as lossless
    from src import fixed_factor_codec_v26 as compressed
    from research_v35.exact_gram import accumulate as reference_accumulate, add_grams, dumps
    from research_v40.native_exact_gram import accumulate, prepare_native
    decoder, base, target, stage, weights = load_context(record)
    record['native_integer_build'] = prepare_native()
    records = read(plan['records_path'])['records']
    require(len(records) * TOKENS == NORMALIZATION and all(len(r['tokens']) == TOKENS for r in records),
            'Original calibration extent differs')
    artifact('fixed-target.json', canonical_json(target.payload()))
    artifact('base-target.json', canonical_json(base.payload()))
    artifact('weights.bin', weights.astype('<f8').tobytes())
    metadata, pooled = [], None
    timing = dict(features=0, lossless_encoding=0, gram_preparation=0,
                  compressed_conversion_40=0, native_accumulation=0, python_reference_accumulation=0, archive_comparison=0)
    for index, row in enumerate(records):
        tick = time.perf_counter_ns()
        values = features(decoder, row)
        timing['features'] += time.perf_counter_ns() - tick
        kwargs = dict(target_sha256=target.digest, anchor_target_sha256=base.digest, record_id=row['id'],
                      token_sha256=digest(canonical_json(row['tokens'])), stage_id=STAGE)
        saved = dict(id=row['id'], feature_sha256=digest(values.astype('<f8').tobytes()), descriptors={})
        tick = time.perf_counter_ns()
        descriptor = lossless.encode_factor(values, **kwargs)
        blob = lossless.serialize(descriptor)
        saved['descriptors']['lossless'] = artifact(f'source-{index:02d}-lossless.bin', blob)
        decoded = lossless.parse(blob, expected_sha256=digest(blob)).array()
        require(np.array_equal(values, decoded), 'Lossless roundtrip differs')
        timing['lossless_encoding'] += time.perf_counter_ns() - tick
        for precision in (40,):
            tick = time.perf_counter_ns()
            descriptor = compressed.encode_factor(values, bits=precision, block_size=256, **kwargs)
            blob = compressed.serialize(descriptor)
            saved['descriptors'][str(precision)] = artifact(f'source-{index:02d}-compressed-{precision}.bin', blob)
            box = compressed.parse(blob, expected_sha256=digest(blob)).box()
            require(np.all(box.lower <= values) and np.all(values <= box.upper), 'Compressed containment failed')
            timing[f'compressed_conversion_{precision}'] += time.perf_counter_ns() - tick
        tick = time.perf_counter_ns()
        gram = accumulate(values.T.copy(), source_id=row['id'], normalization=NORMALIZATION, budget=gram_budget())
        timing['native_accumulation'] += time.perf_counter_ns() - tick
        reference_tick = time.perf_counter_ns()
        expected = reference_accumulate(values.T.copy(), source_id=row['id'], normalization=NORMALIZATION, budget=gram_budget())
        timing['python_reference_accumulation'] += time.perf_counter_ns() - reference_tick
        compare_tick = time.perf_counter_ns()
        require(dumps(gram, budget=gram_budget()) == dumps(expected, budget=gram_budget()),
                'Native and Python complete source Gram archives differ')
        timing['archive_comparison'] += time.perf_counter_ns() - compare_tick
        del expected
        pooled = gram if pooled is None else add_grams(pooled, gram, budget=gram_budget())
        timing['gram_preparation'] += time.perf_counter_ns() - tick
        metadata.append(saved)
        mark('source_prepared', record_id=row['id'], count=index + 1)
    tick = time.perf_counter_ns()
    artifact('original-gram.bin', dumps(pooled, budget=gram_budget()))
    timing['gram_preparation'] += time.perf_counter_ns() - tick
    manifest = dict(schema='scale-stage-preparation-v40', native_reference_source_archives_equal=True, target_sha256=target.digest,
        base_target_sha256=base.digest, stage_id=STAGE, rows=ROWS, width=WIDTH,
        normalization=NORMALIZATION, source_records=metadata, gram_sources=[asdict(s) for s in pooled.sources],
        scales_hex=[v.hex() for v in stage.scale_values], timing_ns=timing,
        actual_roundtrips_and_containment_verified=True, neural_stage_record_pairs=len(records),
        original_model_quantization_performed=False, complete_service_state=False)
    artifact('preparation.json', canonical_json(manifest))
    return dict(preparation=manifest, original_record_ids=[r['id'] for r in records],
                neural_stage_record_pairs=len(records), original_model_quantization_performed=False)


def case(plan, record, artifact, mark):
    import numpy as np
    from src import fixed_lossless_codec_v29 as lossless
    from src import fixed_factor_codec_v26 as compressed
    from src.compact_state import StageCodes
    from src.native_ball_quantizer import prepare_native_ball
    from src.primal_certificate_v30 import prepare_primal_native
    from research_v39.feature_primal_ball import certify_feature_primal_ball
    from research_v39.scaled_gram_ball import certify_exact_gram_ball
    from research_v40.streamed_primal_ball import certify_streamed_primal_ball
    from research_v40.native_exact_gram import accumulate as native_accumulate, prepare_native
    from research_v35.exact_gram import accumulate as python_accumulate, add_grams, subtract_gram, dumps, loads, SourceCommitment
    from scripts.execute_gram_pilot_v35 import public_result
    decoder, base, target, stage, weights = load_context(record)
    prepared = Path(plan['preparation_path'])
    require(sha(prepared / 'completion.json') == plan['preparation_sha256'], 'Preparation commitment differs')
    completion = read(prepared / 'completion.json')
    entry = completion['artifacts']['preparation.json']
    require(completion['status'] == 'complete' and sha(prepared / entry['file']) == entry['sha256'],
            'Preparation manifest differs')
    metadata = read(prepared / entry['file'])
    require(metadata['target_sha256'] == target.digest and metadata['base_target_sha256'] == base.digest,
            'Fixed target changed')
    require(metadata['native_reference_source_archives_equal'], 'Native source archives were not verified')
    sources = {row['id']: row for row in metadata['source_records']}
    rows = {row['id']: row for row in read(plan['records_path'])['records']}
    retained, deleted = plan['retained_ids'], sorted(set(rows) - set(plan['retained_ids']))
    require(len(retained) == plan['retained_count'] and len(retained) + len(deleted) == 13, 'Request partition differs')
    artifact('request.json', canonical_json(dict(retained=retained, deleted=deleted, normalization=NORMALIZATION)))
    tick = time.perf_counter_ns()
    record['native_builds'] = dict(row=prepare_native_ball(), primal=prepare_primal_native(), integer_gram=prepare_native())
    record['common_native_build_elapsed_ns'] = time.perf_counter_ns() - tick
    results, code_payloads, gram_payloads = {}, {}, {}

    def descriptor(rid, mode):
        entry = sources[rid]['descriptors'][mode]
        blob = (prepared / entry['file']).read_bytes()
        require(len(blob) == entry['bytes'] and digest(blob) == entry['sha256'], 'Descriptor changed')
        parsed = (lossless if mode == 'lossless' else compressed).parse(blob, expected_sha256=entry['sha256'])
        require(parsed.record_id == rid and parsed.target_sha256 == target.digest
                and parsed.source_sha256 == sources[rid]['feature_sha256'], 'Descriptor provenance differs')
        return parsed

    def regenerate(rid, telemetry):
        values = features(decoder, rows[rid])
        telemetry['neural_stage_record_pairs'] += 1
        require(digest(values.astype('<f8').tobytes()) == sources[rid]['feature_sha256'], 'Replayed features differ')
        return values

    def blocks(telemetry, mode='lossless', replay=False):
        for rid in retained:
            if replay or mode == 'lossless':
                value = regenerate(rid, telemetry) if replay else descriptor(rid, mode).array()
                value = np.ascontiguousarray(value.T)
                yield value, value
            else:
                box = descriptor(rid, mode).box()
                yield np.ascontiguousarray(box.lower.T), np.ascontiguousarray(box.upper.T)

    def streamed(telemetry, mode='lossless', replay=False):
        return certify_streamed_primal_ball(weights, blocks(telemetry, mode, replay),
            total_tokens=len(retained) * TOKENS, block_tokens=TOKENS, max_blocks=len(retained),
            ridge=Fraction(1, 100), normalization=NORMALIZATION, budget=point_budget())

    def form(ids, telemetry, accumulate):
        pooled = None
        for rid in ids:
            values = regenerate(rid, telemetry)
            item = accumulate(values.T.copy(), source_id=rid, normalization=NORMALIZATION, budget=gram_budget())
            pooled = item if pooled is None else add_grams(pooled, item, budget=gram_budget())
        require(pooled is not None, 'Empty Gram request is not registered')
        return pooled

    for arm in plan['arm_order']:
        mark('arm_started', arm=arm)
        tick = time.perf_counter_ns()
        telemetry = dict(neural_stage_record_pairs=0, certificate_accepted=None, fallback=False, fallback_elapsed_ns=0)
        try:
            gram_payload, mode = None, 'lossless'
            if arm.startswith('gram_'):
                accumulate = python_accumulate if arm.endswith('_python') else native_accumulate
                if arm.startswith('gram_delete_'):
                    desc = completion['artifacts']['original-gram.bin']
                    original = loads((prepared / desc['file']).read_bytes(), trusted_sha256=desc['sha256'],
                        expected_sources=tuple(SourceCommitment(**s) for s in metadata['gram_sources']), budget=gram_budget())
                    removed = form(deleted, telemetry, accumulate)
                    gram = subtract_gram(original, removed, budget=gram_budget())
                    del original, removed
                else:
                    gram = form(retained, telemetry, accumulate)
                gram_payload = dumps(gram, budget=gram_budget())
                artifact(arm + '-gram.bin', gram_payload)
                gram_payloads[arm] = gram_payload
                answer = certify_exact_gram_ball(weights, gram, ridge=Fraction(1, 100),
                    budget=point_budget(), gram_budget=gram_budget())
                del gram
            elif arm == 'cached_primal':
                values = np.ascontiguousarray(np.concatenate([descriptor(rid, 'lossless').array() for rid in retained]).T)
                answer = certify_feature_primal_ball(weights, values, values,
                    ridge=Fraction(1, 100), normalization=NORMALIZATION, budget=point_budget())
                del values
            elif arm == 'streamed_primal':
                answer = streamed(telemetry)
            else:
                require(arm == 'streamed_compressed_40', 'Unregistered arm implementation')
                mode = '40'
                try:
                    answer = streamed(telemetry, mode=mode)
                    telemetry['certificate_accepted'] = True
                except Exception as error:
                    if not scientific_refusal(error):
                        raise
                    telemetry.update(certificate_accepted=False, fallback=True,
                        certificate_refusal=dict(type=type(error).__name__, message=str(error),
                            diagnostics=public_result(getattr(error, 'native_diagnostics', None)
                                or getattr(error, 'native_ball_diagnostics', None) or {})))
                    fallback_start = time.perf_counter_ns()
                    try:
                        answer = streamed(telemetry, replay=True)
                    finally:
                        telemetry['fallback_elapsed_ns'] = time.perf_counter_ns() - fallback_start
            require(answer.codes.shape == (ROWS, WIDTH), 'Incomplete stage')
            codes = StageCodes.from_array(STAGE, answer.codes, bits=4, grid_axis='dyadic_row', scale_values=stage.scale_values)
            payload = codes.packed_indices
            artifact(arm + '-codes.bin', payload)
            code_payloads[arm] = payload
            retained_payloads = ([dict(file=arm + '-gram.bin', sha256=digest(gram_payload), bytes=len(gram_payload))]
                if gram_payload is not None else [dict(record_id=rid, **sources[rid]['descriptors'][mode]) for rid in retained])
            state = canonical_json(dict(stage_id=STAGE, target_sha256=target.digest, retained_ids=retained,
                rows=ROWS, width=WIDTH, normalization=NORMALIZATION, scales_hex=[v.hex() for v in stage.scale_values],
                code_sha256=digest(payload), representation='exact_gram' if gram_payload is not None else mode,
                retained_payloads=retained_payloads))
            artifact(arm + '-state-metadata.json', state)
            results[arm] = dict(status='certified', codes_committed=True, code_count=ROWS * WIDTH,
                code_sha256=digest(payload), component_state_bytes=sum(x['bytes'] for x in retained_payloads) + len(payload) + len(state),
                state_scope='Retained descriptors or exact Gram, stage metadata, and stage codes. Base checkpoint, raw tokens, and audits excluded.',
                solver=public_result(answer), **telemetry)
            del answer
        except Exception as error:
            if not scientific_refusal(error):
                raise
            results[arm] = dict(status='scientific_refusal', codes_committed=False,
                error_type=type(error).__name__, error=str(error), **telemetry)
        results[arm]['component_elapsed_ns'] = time.perf_counter_ns() - tick
        record['arms'] = results
        mark('arm_finished', arm=arm, status=results[arm]['status'])
    require(set(gram_payloads) == {'gram_delete_python', 'gram_delete_native', 'gram_fresh_native'}
            and len(set(gram_payloads.values())) == 1, 'Native, Python, and fresh retained Gram archives differ')
    equal = bool(code_payloads) and len(set(code_payloads.values())) == 1
    require(not code_payloads or equal, 'Certified methods produced unequal actual codes')
    return dict(arms=results, retained_ids=retained, deleted_ids=deleted,
        retained_tokens=len(retained) * TOKENS, width=WIDTH, rows=ROWS, code_count=ROWS * WIDTH,
        exact_gram_bytes_equal=True, all_committed_code_bytes_equal=equal,
        all_arms_certified=all(r['status'] == 'certified' for r in results.values()),
        actual_binary_comparison_performed=True, complete_model=False, independent_state_oracle=False,
        primary_clock='Each complete stage arm through input loading, replay, accumulation, certification, diagnostics, and output.',
        clock_exclusions='Shared checkpoint/target construction and native builds are separately recorded. Cross-arm audits and receipts are outside arm clocks.',
        statistical_scope='One development observation per arm and size. Same exposed articles as V39. No population inference.',
        lifetime_benefit_established=False)

def main(plan_path):
    plan_path = Path(plan_path).absolute()
    plan = read(plan_path)
    program = read(plan['program_path'])
    require(sha(plan['program_path']) == plan['program_sha256'], 'Program binding differs')
    from research_v40.controller import expected_plan
    require(plan == expected_plan(program, plan['trial_id']), 'Plan differs from the registered trial')
    verify_sources(program)
    require(capture_runtime_contract() == program['runtime'], 'Runtime changed')
    verify_command_admission(plan['protocol_sha256'], 'feasibility',
                             [sys.executable, '-m', 'research_v40.worker', str(plan_path)])
    output = Path(plan['output'])
    require(not output.exists(), 'Output exists; retries are prohibited')
    output.mkdir(parents=True)
    record = dict(schema='scale-worker-v40', status='running', kind=plan['kind'], plan_sha256=sha(plan_path),
        source_sha256=program['source_sha256'], extra_source_sha256=program['extra_source_sha256'],
        artifacts={}, phases=[], confirmation=False, complete_model=False)
    start = time.perf_counter_ns()

    def artifact(name, payload):
        require(Path(name).name == name, 'Artifact filename is unsafe')
        descriptor = new(output / name, payload, raw=True)
        record['artifacts'][name] = descriptor
        return descriptor

    def mark(phase, **details):
        row = dict(phase=phase, elapsed_ns=time.perf_counter_ns() - start, **details)
        record['phases'].append(row)
        new(output / f'phase-{len(record["phases"]):03d}.json', row)
        print(canonical_json(row).decode(), flush=True)

    try:
        if plan['kind'] == 'data':
            from research_v39.data import select
            details = select(output, artifact)
        else:
            require(sha(plan['records_path']) == plan['records_sha256'], 'Selected tokens changed')
            details = preparation(plan, record, artifact, mark) if plan['kind'] == 'prepare' else case(plan, record, artifact, mark)
        record.update(details, status='complete', worker_elapsed_ns=time.perf_counter_ns() - start,
                      max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        payload = canonical_json(record)
        new(output / 'completion.json', payload, raw=True)
        new(output / 'progress.json', payload, raw=True)
        print(canonical_json({'terminal_sha256': digest(payload)}).decode(), flush=True)
    except BaseException as error:
        record.update(status='failed', error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc())
        new(output / 'failure.json', record)
        raise


if __name__ == '__main__':
    main(sys.argv[1])
