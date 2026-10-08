"""Registered real-feature screen for bounded token and primal certificates."""
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.experiment_inventory import source_hashes
from src.run_store import atomic_write, canonical_json, digest
from src.transaction_timing import verify_command_admission


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    path = Path(sys.argv[1]).absolute()
    raw = path.read_bytes()
    plan = json.loads(raw)
    require(source_hashes(ROOT) == plan['source_sha256'], 'source changed')
    verify_command_admission(plan['protocol_sha256'], 'feasibility',
        [sys.executable, str(Path(__file__).resolve()), str(path)])
    output = Path(plan['output'])
    output.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter_ns()
    result = dict(schema='real-feature-scaling-v30', status='running',
        plan_sha256=digest(raw), phases=[], comparisons=[], artifacts={},
        full_model=False, quality_evaluation=False, confirmation=False,
        scope='real first-stage features and complete weight rows; component diagnostic only',
        target_semantics='fixed nearest-anchor calibration; first stage has no quantized ancestors')

    def save(phase, **details):
        result['phases'].append(dict(phase=phase, elapsed_ns=time.perf_counter_ns()-start, **details))
        result['peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        atomic_write(output/'progress.json', canonical_json(result))
        print(json.dumps(result['phases'][-1]), flush=True)

    try:
        for name, entry in plan['inputs'].items():
            with Path(entry['path']).open('rb') as handle:
                require(hashlib.file_digest(handle, 'sha256').hexdigest() == entry['sha256'], 'input changed: '+name)
        save('inputs_verified')
        import numpy as np
        from src.checkpoint_adapter import load_gpt2_checkpoint
        from src.certified_transformer import CertifiedDecoder
        from src.target_manifest import TargetRecipe
        from src.dyadic_row_target import build_dyadic_row_target
        from src.sequential_finite import sequential_features
        from src.ordered_finite import FiniteWeights
        from src.adaptive_calibration_v30 import AdaptiveBudget, quantize_adaptive_dyadic_rows, assess_routes
        from src.token_box_certificate import TokenBoxUnresolved
        from src.low_rank_certified import LowRankUnresolved
        pool = json.loads(Path(plan['inputs']['pool']['path']).read_bytes())
        by_id = {r['id']:r for r in pool['development']}
        records = tuple(dict(id=rid, tokens=by_id[rid]['tokens'][:plan['tokens_per_record']]) for rid in plan['record_ids'])
        require(all(len(row['tokens']) == plan['tokens_per_record'] for row in records), 'insufficient cached tokens')
        loaded = load_gpt2_checkpoint(plan['checkpoint'], identity_encoding='binary64_tree_v2')
        require(loaded.provenance['files_sha256'] == {name:plan['inputs'][key]['sha256']
            for name,key in (('config.json','config'),('model.safetensors','weights'))}, 'checkpoint binding differs')
        decoder = CertifiedDecoder(loaded.decoder, primitive_backend='mpfr_enclosure')
        token_count = sum(len(row['tokens']) for row in records)
        base = build_dyadic_row_target(decoder, TargetRecipe(original_token_count=2*token_count, group_count=1))
        stage = base.stages[0]
        count = plan['weight_rows']
        require(type(count) is int and 1 <= count <= len(stage.weights), 'invalid complete row count')
        weights = np.ascontiguousarray(FiniteWeights(stage.weights).array()[:count])
        scales = stage.scale_values[:count]
        save('features_started', records=len(records), pooled_tokens=token_count)
        tick = time.perf_counter_ns()
        blocks = []
        for record in records:
            stream = sequential_features(decoder, record['tokens'])
            sid, values = next(stream)
            require(sid == stage.stage_id, 'stage order differs')
            blocks.append(np.asarray(values, dtype=np.float64))
            stream.close()
        features = np.require(np.concatenate(blocks, axis=0).T, requirements=['C','A'])
        result.update(feature_elapsed_ns=time.perf_counter_ns()-tick,
            record_ids=plan['record_ids'], token_lengths=[len(r['tokens']) for r in records],
            pooled_tokens=token_count, width=stage.width, rows=count, stage_id=stage.stage_id,
            base_target_sha256=base.digest, normalization=2*token_count,
            feature_sha256=digest(features.astype('<f8').tobytes()),
            weight_sha256=digest(weights.astype('<f8').tobytes()), neural_stage_record_pairs=len(records))
        budget = AdaptiveBudget(**plan['coefficient_budget'])
        result['admission'] = assess_routes(count, stage.width, token_count, budget=budget)
        save('features_complete')
        outputs = {}
        for route in plan['route_order']:
            save('route_started', route=route)
            tick = time.perf_counter_ns()
            try:
                answer = quantize_adaptive_dyadic_rows(weights, features, scales,
                    bits=stage.bits, ridge=stage.ridge, normalization=stage.normalization,
                    route=route, budget=budget)
                elapsed = time.perf_counter_ns()-tick
                codes = np.asarray(answer.codes, dtype='<f8').tobytes()
                name = route+'.codes.bin'
                atomic_write(output/name, codes)
                result['artifacts'][route] = dict(file=name, sha256=digest(codes), bytes=len(codes))
                outputs[route] = answer.codes
                result['comparisons'].append(dict(route=route, status='accepted', elapsed_ns=elapsed,
                    code_sha256=digest(codes), code_elements=int(answer.codes.size),
                    solver_diagnostics=answer.solver_diagnostics))
            except (TokenBoxUnresolved, LowRankUnresolved, ArithmeticError) as exc:
                result['comparisons'].append(dict(route=route, status='unresolved',
                    elapsed_ns=time.perf_counter_ns()-tick, error_type=type(exc).__name__, reason=str(exc),
                    admission=getattr(exc, 'admission', None)))
            save('route_complete', route=route, outcome=result['comparisons'][-1]['status'])
        both = set(outputs) == {'token','primal'}
        equal = both and bool(np.array_equal(outputs['token'], outputs['primal']))
        require(not both or equal, 'certified primal and token outputs disagree')
        result.update(status='complete', both_routes_accepted=both, exact_route_agreement=equal,
            scaling_gate=equal, original_code_order_preserved=True,
            interpretation='component correctness and feasibility; no full-model or repair speed claim')
        save('complete')
        terminal = canonical_json(result)
        with (output/'completion.json').open('xb') as stream:
            stream.write(terminal); stream.flush(); os.fsync(stream.fileno())
        print(json.dumps(dict(phase='terminal_record_committed', sha256=digest(terminal))), flush=True)
    except BaseException as exc:
        result.update(status='failed', error_type=type(exc).__name__, error=str(exc))
        save('failed')
        raise


if __name__ == '__main__':
    main()
