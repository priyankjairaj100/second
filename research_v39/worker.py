"""Bounded complete-stage scale workers. No historical attempt is reused."""
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path
import re
import resource
import sys
import time
import traceback

from research_v39.policy import (ROOT, WIDTH, ROWS, STAGE, NORMALIZATION, TOKENS,
    require, read, sha, new, gram_budget, point_budget, verify_sources)
from src.run_store import canonical_json, digest
from src.runtime_contract import capture_runtime_contract
from src.transaction_timing import verify_command_admission


def scientific_refusal(error):
    from src.low_rank_certified import LowRankUnresolved
    from src.token_box_certificate import TokenBoxUnresolved
    if not isinstance(error, (LowRankUnresolved, TokenBoxUnresolved)):
        return False
    return bool(re.fullmatch(
        r'(?:primal native row verification failed: status=3, row=\d+, coordinate=\d+'
        r'|direct Gram coefficient enclosure failed at coordinate \d+: status=2'
        r'|exact fallback budget exceeded at coordinate \d+; no codes committed'
        r'|requested-coordinate evidence cannot resolve remaining rows'
        r'|preconditioner (?:round|coordinate) budget exhausted'
        r'|work budget refuses [A-Za-z0-9_ -]+; no model committed)', str(error)))


def load_context(record):
    from src.checkpoint_adapter import load_gpt2_checkpoint
    from src.ordered_finite_decoder_v30 import OrderedFiniteDecoder
    from src.target_manifest import TargetRecipe
    from src.dyadic_row_target import build_dyadic_row_target
    from src.fixed_anchor_target import build_fixed_anchor_target
    from src.ordered_finite import FiniteWeights
    from research_v38.bootstrap_target import CHECKPOINT_HASHES
    started = time.perf_counter_ns()
    loaded = load_gpt2_checkpoint(ROOT / 'tmp/models/distilgpt2', identity_encoding='binary64_tree_v2')
    require(loaded.provenance['files_sha256'] == CHECKPOINT_HASHES, 'Checkpoint differs')
    decoder = OrderedFiniteDecoder(loaded.decoder, primitive_backend='mpfr_enclosure')
    base = build_dyadic_row_target(decoder, TargetRecipe(original_token_count=NORMALIZATION, group_count=1))
    target = build_fixed_anchor_target(decoder, base)
    stage = target.stages[0]
    require(stage.stage_id == STAGE and stage.width == WIDTH and len(stage.weights) == ROWS, 'Stage extent differs')
    weights = FiniteWeights(stage.weights).array()
    record.update(target_sha256=target.digest, base_target_sha256=base.digest,
        common_checkpoint_and_target_elapsed_ns=time.perf_counter_ns() - started,
        decoder_evaluator_id=decoder.evaluator_id, decoder_implementation_manifest=decoder.implementation_manifest)
    return decoder, base, target, stage, weights


def features(decoder, row):
    import numpy as np
    from src.ordered_finite_decoder_v30 import ordered_sequential_features
    stream = ordered_sequential_features(decoder, row['tokens'])
    try:
        stage, values = next(stream)
        require(stage == STAGE, 'Feature stage differs')
        result = np.ascontiguousarray(values, dtype=np.float64)
        require(result.shape == (TOKENS, WIDTH), 'Real feature shape differs')
        return result
    finally:
        stream.close()


def preparation(plan, record, artifact, mark):
    import numpy as np
    from src import fixed_lossless_codec_v29 as lossless
    from src import fixed_factor_codec_v26 as compressed
    from research_v35.exact_gram import accumulate, add_grams, dumps
    decoder, base, target, stage, weights = load_context(record)
    records = read(plan['records_path'])['records']
    require(len(records) * TOKENS == NORMALIZATION and all(len(r['tokens']) == TOKENS for r in records),
            'Original calibration extent differs')
    artifact('fixed-target.json', canonical_json(target.payload()))
    artifact('base-target.json', canonical_json(base.payload()))
    artifact('weights.bin', weights.astype('<f8').tobytes())
    metadata, pooled = [], None
    timing = dict(features=0, lossless_encoding=0, gram_preparation=0,
                  compressed_conversion_32=0, compressed_conversion_40=0, compressed_conversion_48=0)
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
        for precision in (32, 40, 48):
            tick = time.perf_counter_ns()
            descriptor = compressed.encode_factor(values, bits=precision, block_size=256, **kwargs)
            blob = compressed.serialize(descriptor)
            saved['descriptors'][str(precision)] = artifact(f'source-{index:02d}-compressed-{precision}.bin', blob)
            box = compressed.parse(blob, expected_sha256=digest(blob)).box()
            require(np.all(box.lower <= values) and np.all(values <= box.upper), 'Compressed containment failed')
            timing[f'compressed_conversion_{precision}'] += time.perf_counter_ns() - tick
        tick = time.perf_counter_ns()
        gram = accumulate(values.T.copy(), source_id=row['id'], normalization=NORMALIZATION, budget=gram_budget())
        pooled = gram if pooled is None else add_grams(pooled, gram, budget=gram_budget())
        timing['gram_preparation'] += time.perf_counter_ns() - tick
        metadata.append(saved)
        mark('source_prepared', record_id=row['id'], count=index + 1)
    tick = time.perf_counter_ns()
    artifact('original-gram.bin', dumps(pooled, budget=gram_budget()))
    timing['gram_preparation'] += time.perf_counter_ns() - tick
    manifest = dict(schema='scale-stage-preparation-v39', target_sha256=target.digest,
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
    from src.fast_token_quantizer_v30 import native_fast_quantize_dyadic_rows
    from src.native_token_coefficients_v30 import prepare_native_token_coefficients
    from src.native_box_coefficients_v31 import prepare_native_box_coefficients
    from src.native_ball_quantizer import prepare_native_ball
    from src.primal_certificate_v30 import prepare_primal_native
    from src.sparse_box_certificate_v31 import certify_sparse_ball_dyadic_box
    from src.sparse_box_certificate_v30 import SparseCertificateBudget
    from research_v39.feature_primal_ball import certify_feature_primal_ball
    from research_v35.exact_gram import accumulate, add_grams, subtract_gram, dumps, loads, SourceCommitment
    from research_v39.scaled_gram_ball import certify_exact_gram_ball
    from scripts.execute_gram_pilot_v35 import public_result
    decoder, base, target, stage, weights = load_context(record)
    prepared = Path(plan['preparation_path'])
    require(sha(prepared / 'completion.json') == plan['preparation_sha256'], 'Preparation commitment differs')
    completion = read(prepared / 'completion.json')
    require(completion['status'] == 'complete', 'Preparation is incomplete')
    entry = completion['artifacts']['preparation.json']
    require(sha(prepared / entry['file']) == entry['sha256'], 'Preparation manifest changed')
    metadata = read(prepared / entry['file'])
    require(metadata['target_sha256'] == target.digest and metadata['base_target_sha256'] == base.digest,
            'Target changed between preparation and request')
    sources = {row['id']: row for row in metadata['source_records']}
    records = read(plan['records_path'])['records']
    rows = {row['id']: row for row in records}
    retained = plan['retained_ids']
    deleted = sorted(set(rows) - set(retained))
    require(len(retained) == plan['retained_count'] and len(retained) + len(deleted) == 13,
            'Request partition differs')
    artifact('request.json', canonical_json(dict(retained=retained, deleted=deleted, normalization=NORMALIZATION)))
    tick = time.perf_counter_ns()
    record['native_builds'] = dict(row=prepare_native_ball(), primal=prepare_primal_native(),
        token=prepare_native_token_coefficients(), box=prepare_native_box_coefficients())
    record['common_native_build_elapsed_ns'] = time.perf_counter_ns() - tick
    results, code_payloads, gram_payloads = {}, {}, {}

    def read_descriptor(rid, mode):
        descriptor = sources[rid]['descriptors'][mode]
        blob = (prepared / descriptor['file']).read_bytes()
        require(len(blob) == descriptor['bytes'] and digest(blob) == descriptor['sha256'], 'Descriptor changed')
        parsed = (lossless if mode == 'lossless' else compressed).parse(blob, expected_sha256=descriptor['sha256'])
        require(parsed.record_id == rid and parsed.target_sha256 == target.digest
                and parsed.source_sha256 == sources[rid]['feature_sha256'], 'Descriptor provenance differs')
        return parsed, blob

    def regenerate(rid, telemetry):
        values = features(decoder, rows[rid])
        telemetry['neural_stage_record_pairs'] += 1
        require(digest(values.astype('<f8').tobytes()) == sources[rid]['feature_sha256'], 'Replayed features differ')
        return values

    def exact_features(telemetry, *, replay):
        blocks = [regenerate(rid, telemetry) if replay else read_descriptor(rid, 'lossless')[0].array()
                  for rid in retained]
        return np.ascontiguousarray(np.concatenate(blocks).T)

    def point(values):
        if values.shape[1] < WIDTH:
            return native_fast_quantize_dyadic_rows(weights, values, ridge=Fraction(1, 100), normalization=NORMALIZATION)
        return certify_feature_primal_ball(weights, values, values,
            ridge=Fraction(1, 100), normalization=NORMALIZATION, budget=point_budget())

    def form(ids, telemetry):
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
        telemetry = dict(neural_stage_record_pairs=0, certificate_accepted=None, fallback=False,
                         fallback_elapsed_ns=0, fallback_refusal=None)
        try:
            descriptor_payloads, gram_payload = [], None
            if arm in ('gram_delete', 'gram_fresh'):
                if arm == 'gram_delete':
                    desc = completion['artifacts']['original-gram.bin']
                    blob = (prepared / desc['file']).read_bytes()
                    original = loads(blob, trusted_sha256=desc['sha256'],
                        expected_sources=tuple(SourceCommitment(**s) for s in metadata['gram_sources']), budget=gram_budget())
                    removed = form(deleted, telemetry)
                    gram = subtract_gram(original, removed, budget=gram_budget())
                    del original, removed, blob
                else:
                    gram = form(retained, telemetry)
                gram_payload = dumps(gram, budget=gram_budget())
                artifact(arm + '-gram.bin', gram_payload)
                gram_payloads[arm] = gram_payload
                answer = certify_exact_gram_ball(weights, gram, ridge=Fraction(1, 100),
                    budget=point_budget(), gram_budget=gram_budget())
                del gram
            elif arm in ('cached_token', 'cached_primal'):
                values = exact_features(telemetry, replay=False)
                if arm == 'cached_token':
                    answer = native_fast_quantize_dyadic_rows(weights, values,
                        ridge=Fraction(1, 100), normalization=NORMALIZATION)
                else:
                    answer = certify_feature_primal_ball(weights, values, values,
                        ridge=Fraction(1, 100), normalization=NORMALIZATION, budget=point_budget())
                descriptor_payloads = [(rid, 'lossless') for rid in retained]
                del values
            else:
                precision = arm.split('_')[1]
                pairs = [read_descriptor(rid, precision)[0].box() for rid in retained]
                lower = np.ascontiguousarray(np.concatenate([box.lower for box in pairs]).T)
                upper = np.ascontiguousarray(np.concatenate([box.upper for box in pairs]).T)
                del pairs
                try:
                    if len(retained) * TOKENS < WIDTH:
                        answer = certify_sparse_ball_dyadic_box(weights, lower, upper,
                            ridge=Fraction(1, 100), normalization=NORMALIZATION,
                            budget=SparseCertificateBudget(max_work_units=6_000_000_000,
                                max_workspace_bytes=512 * 2**20, max_preconditioned_coordinates=16, max_rounds=4))
                    else:
                        answer = certify_feature_primal_ball(weights, lower, upper,
                            ridge=Fraction(1, 100), normalization=NORMALIZATION, budget=point_budget())
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
                        answer = point(exact_features(telemetry, replay=True))
                    finally:
                        telemetry['fallback_elapsed_ns'] = time.perf_counter_ns() - fallback_start
                descriptor_payloads = [(rid, precision) for rid in retained]
                del lower, upper
            require(answer.codes.shape == (ROWS, WIDTH), 'Incomplete stage output')
            stage_codes = StageCodes.from_array(STAGE, answer.codes, bits=4,
                grid_axis='dyadic_row', scale_values=stage.scale_values)
            code_payload = stage_codes.packed_indices
            artifact(arm + '-codes.bin', code_payload)
            code_payloads[arm] = code_payload
            # Count every retained descriptor, complete stage codes, and explicit
            # stage metadata. This is a component payload, not a full service.
            state_metadata = dict(stage_id=STAGE, target_sha256=target.digest, retained_ids=retained,
                rows=ROWS, width=WIDTH, normalization=NORMALIZATION,
                scales_hex=[v.hex() for v in stage.scale_values], code_sha256=digest(code_payload),
                representation='exact_gram' if gram_payload is not None else descriptor_payloads[0][1],
                retained_payloads=([dict(file=arm + '-gram.bin', sha256=digest(gram_payload), bytes=len(gram_payload))]
                    if gram_payload is not None else [dict(record_id=rid, **sources[rid]['descriptors'][mode])
                        for rid, mode in descriptor_payloads]))
            state_metadata_payload = canonical_json(state_metadata)
            artifact(arm + '-state-metadata.json', state_metadata_payload)
            retained_payload_bytes = len(gram_payload) if gram_payload is not None else sum(
                sources[rid]['descriptors'][mode]['bytes'] for rid, mode in descriptor_payloads)
            diagnostic = public_result(answer)
            results[arm] = dict(status='certified', codes_committed=True, code_count=ROWS * WIDTH,
                code_sha256=digest(code_payload), component_state_bytes=retained_payload_bytes + len(code_payload) + len(state_metadata_payload),
                state_scope='All retained feature descriptors or exact Gram, stage metadata, and stage codes. Base checkpoint, raw token inputs, and audit files excluded. This is not complete persistent service state.',
                solver=diagnostic, **telemetry)
            del answer
        except Exception as error:
            if not scientific_refusal(error):
                raise
            results[arm] = dict(status='scientific_refusal', codes_committed=False,
                error_type=type(error).__name__, error=str(error), **telemetry)
        results[arm]['component_elapsed_ns'] = time.perf_counter_ns() - tick
        record['arms'] = results
        mark('arm_finished', arm=arm, status=results[arm]['status'])
    require(set(gram_payloads) == {'gram_delete', 'gram_fresh'}
            and gram_payloads['gram_delete'] == gram_payloads['gram_fresh'], 'Retained exact Gram bytes differ')
    equal = bool(code_payloads) and len(set(code_payloads.values())) == 1
    require(not code_payloads or equal, 'Certified methods produced unequal actual code bytes')
    return dict(arms=results, retained_ids=retained, deleted_ids=deleted,
        retained_tokens=len(retained) * TOKENS, width=WIDTH, rows=ROWS, code_count=ROWS * WIDTH,
        exact_gram_bytes_equal=True, all_committed_code_bytes_equal=equal,
        all_arms_certified=all(r['status'] == 'certified' for r in results.values()),
        actual_binary_comparison_performed=True, complete_model=False, independent_state_oracle=False,
        primary_clock='Each component arm through descriptor loading, replay, solve, verification, diagnostics, and output.',
        clock_exclusions='Shared checkpoint/target construction and native builds are separately recorded. Post-arm comparisons and receipts are outside arm clocks.',
        statistical_scope='One deterministic-order development observation per arm and size. No population inference.',
        lifetime_benefit_established=False)


def main(plan_path):
    plan_path = Path(plan_path).absolute()
    plan = read(plan_path)
    program = read(plan['program_path'])
    require(sha(plan['program_path']) == plan['program_sha256'], 'Program binding differs')
    from research_v39.controller import expected_plan
    require(plan == expected_plan(program, plan['trial_id']), 'Plan differs from the registered trial')
    verify_sources(program)
    require(capture_runtime_contract() == program['runtime'], 'Runtime changed')
    verify_command_admission(plan['protocol_sha256'], 'feasibility',
                             [sys.executable, '-m', 'research_v39.worker', str(plan_path)])
    output = Path(plan['output'])
    require(not output.exists(), 'Output exists; retries are prohibited')
    output.mkdir(parents=True)
    record = dict(schema='scale-worker-v39', status='running', kind=plan['kind'], plan_sha256=sha(plan_path),
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
