"""A distinct source-local target with the original full-precision teacher.

Every feature stream installs original checkpoint matrices. Calibrated outputs
are returned but never fed into later features. This is neither the historical
nearest-grid anchor nor sequential calibration. A complete code constructor does
not establish a repair-state contract, quality, or useful costs.
"""
from dataclasses import dataclass, replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from research_v43 import dispatcher as dispatch
from research_v43.campaign import require
from scripts.execute_gram_pilot_v35 import public_result
from src.compact_service import _records
from src.compact_state import StageCodes
from src.dyadic_row_target import DyadicRowTarget
from src.ordered_finite import FiniteWeights
from src.ordered_finite_decoder_v30 import OrderedFiniteDecoder, ordered_sequential_features
from src.run_store import canonical_json, digest


FEATURE_RULE = 'each stage uses source-local features from original full-precision checkpoint weights'
ANCHOR_RULE = 'original pinned binary64 checkpoint stage matrices; no quantized matrix is installed'


@dataclass(frozen=True)
class FullPrecisionAnchorTarget:
    base_target: DyadicRowTarget
    payload_bytes: bytes

    @property
    def stages(self):
        return tuple(replace(stage, dependencies=()) for stage in self.base_target.stages)

    @property
    def recipe(self):
        return self.base_target.recipe

    @property
    def digest(self):
        return digest(self.payload_bytes)

    def payload(self):
        return json.loads(self.payload_bytes)


def build_full_precision_anchor_target(decoder, base_target):
    """Bind an immutable checkpoint teacher, inheriting the exact base recipe.

    Validation scans parameter words but performs no calibration feature work.
    The campaign pins the real checkpoint and original normalization (1664);
    miniature software fixtures can supply a smaller original normalization.
    """
    require(type(decoder) is OrderedFiniteDecoder, 'Explicit ordered decoder required')
    require(type(base_target) is DyadicRowTarget, 'A complete sequential dyadic base target is required')
    stages = tuple(base_target.stages)
    require(tuple(s.stage_id for s in stages) == tuple(decoder.stage_ids),
        'Complete decoder stage order required')
    base_payload = base_target.payload()
    require(base_payload['evaluator_id'] == decoder.evaluator_id,
        'Base target and teacher decoder differ')
    require(base_payload['recipe'] == base_target.recipe.payload()
        and len(base_payload['stages']) == len(stages), 'Base target recipe or extent differs')
    require(base_payload.get('weight_digest_encoding') == 'binary64_matrix_v1',
        'Explicit original binary64 weight identity required')
    teacher_stages = []
    for index, (stage, entry) in enumerate(zip(stages, base_payload['stages'])):
        require(len(stage.dependencies) == index
            and set(stage.dependencies) == set(decoder.stage_ids[:index]) and stage.bits == 4,
            'Complete sequential dependencies and four-bit grids required')
        spec = dispatch.StageSpec.from_stage(stage, target_sha256=base_target.digest)
        require(entry['stage_id'] == stage.stage_id
            and entry['shape'] == [spec.rows, spec.width]
            and entry['weights_sha256'] == spec.weights_sha256
            and entry['dependencies'] == list(stage.dependencies)
            and entry['row_scale_hex'] == [s.hex() for s in stage.scale_values]
            and entry['grid_axis'] == 'output_row' and entry['significant_bits'] == 24
            and Fraction(*entry['normalization']) == stage.normalization == base_target.recipe.original_token_count
            and Fraction(*entry['ridge']) == stage.ridge == base_target.recipe.ridge
            and base_target.recipe.bits == stage.bits,
            'Base target stages do not match their bound manifest')
        teacher = FiniteWeights(decoder.base._float_weights[stage.stage_id]).array()
        require(teacher.shape == (spec.rows, spec.width) and np.isfinite(teacher).all()
            and dispatch._weight_digest(teacher) == spec.weights_sha256,
            'Teacher weights differ from the original base target')
        teacher_stages.append(dict(stage_id=stage.stage_id, shape=[spec.rows, spec.width],
            weights_sha256=spec.weights_sha256))
    payload = dict(schema='fixed-full-precision-anchor-calibration-target-v59',
        base_target_sha256=base_target.digest,
        decoder_sha256=digest(canonical_json(decoder.kernel_manifest)),
        implementation_manifest_sha256=digest(canonical_json(decoder.implementation_manifest)),
        constructor_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        feature_rule=FEATURE_RULE, anchor_rule=ANCHOR_RULE,
        prefix_rule='calibrated output codes never affect any feature',
        calibrated_dependencies='empty for every stage',
        original_normalization=base_target.recipe.original_token_count,
        normalization_rule='unchanged original normalization from base target',
        grid_rule='unchanged base-only dyadic24 output-row grids; lower midpoint ties',
        record_rule='positions reset per source; causal within source; no cross-source state',
        teacher_weight_digest_encoding='binary64-matrix-little-endian-row-major-v1',
        teacher_stages=teacher_stages,
        output_rule='complete stage codes only; no canonical repair-state contract declared',
        failure_rule='bounded certified stage solver; unresolved or exhausted resource budget aborts')
    return FullPrecisionAnchorTarget(base_target, canonical_json(payload))


def _immutable_teacher(decoder, stage_id, expected_sha256):
    values = FiniteWeights(decoder.base._float_weights[stage_id]).array()
    require(dispatch._weight_digest(values) == expected_sha256, 'Teacher checkpoint words changed')
    # Own immutable bytes prevent solver outputs or writable views from becoming
    # the next parent matrix. Only one teacher stage is retained at a time.
    return np.frombuffer(values.tobytes(order='C'), dtype=np.float64).reshape(values.shape)


def calibrate(decoder, base_target, records, *, policy=dispatch.ResourcePolicy(), progress=None):
    """Certify complete output codes while keeping every feature teacher fixed."""
    start = time.perf_counter_ns()
    require(progress is None or callable(progress), 'Progress must be callable')
    target = build_full_precision_anchor_target(decoder, base_target)
    stages = target.stages
    rows = _records(decoder, records)
    require(bool(rows), 'Nonempty retained record set required')
    tokens = sum(len(ids) for _, ids in rows)
    block_tokens = max(len(ids) for _, ids in rows)
    specs, admission = [], []
    for stage in stages:
        spec = dispatch.StageSpec.from_stage(stage, target_sha256=target.digest)
        report = dispatch.assess_stage(spec, tokens, kind='point', block_tokens=block_tokens,
            max_blocks=len(rows), policy=policy, resident_bytes=4*2**30)
        require(report['admitted'], 'Full-precision-anchor stage admission refused: '+stage.stage_id)
        specs.append(spec)
        admission.append(report)
    require(sum(r['work_units'] for r in admission) <= policy.max_request_work_units,
        'Full-precision-anchor request work admission refused')
    metrics = dict(schema='full-precision-anchor-calibration-v59', target_sha256=target.digest,
        base_target_sha256=base_target.digest, feature_rule=FEATURE_RULE, anchor_rule=ANCHOR_RULE,
        implementation='ordered-finite-decoder-v30',
        implementation_manifest_sha256=digest(canonical_json(decoder.implementation_manifest)),
        records=len(rows), retained_tokens=tokens, original_normalization=target.recipe.original_token_count,
        neural_stage_record_pairs=0, prior_model_access=False, prior_factor_access=False,
        calibrated_prefix_access=False, point_admission=admission,
        admission_elapsed_ns=time.perf_counter_ns()-start, stages=[])
    streams, outputs = {}, []
    teacher_parent = None
    try:
        for index, (stage, spec) in enumerate(zip(stages, specs)):
            tick = time.perf_counter_ns()
            if index:
                teacher_parent = _immutable_teacher(decoder, stages[index-1].stage_id,
                    specs[index-1].weights_sha256)
            blocks = []
            for rid, ids in rows:
                if index == 0:
                    streams[rid] = ordered_sequential_features(decoder, ids)
                    sid, values = next(streams[rid])
                else:
                    sid, values = streams[rid].send(teacher_parent)
                require(sid == stage.stage_id, 'Full-precision feature stream stage differs')
                point = np.ascontiguousarray(np.asarray(values, dtype=np.float64).T)
                require(point.shape == (stage.width, len(ids)) and np.isfinite(point).all(),
                    'Full-precision feature shape or words invalid')
                blocks.append((point, point))
                metrics['neural_stage_record_pairs'] += 1
            teacher_parent = None
            feature_ns = time.perf_counter_ns()-tick
            weights = FiniteWeights(stage.weights).array()
            solve_tick = time.perf_counter_ns()
            solved = dispatch.solve_blocks(spec, weights, blocks, total_tokens=tokens, kind='point',
                block_tokens=block_tokens, max_blocks=len(rows), policy=policy, resident_bytes=4*2**30)
            solve_ns = time.perf_counter_ns()-solve_tick
            code = StageCodes.from_array(stage.stage_id, solved.codes, grid_axis='dyadic_row',
                bits=stage.bits, scale_values=stage.scale_values)
            outputs.append(code)
            row = dict(stage_id=stage.stage_id, feature_tokens=tokens, input_width=stage.width,
                output_rows=spec.rows, route=solved.route,
                teacher_parent_stage_id=stages[index-1].stage_id if index else None,
                teacher_parent_weights_sha256=specs[index-1].weights_sha256 if index else None,
                output_code_sha256=digest(code.packed_indices),
                feature_elapsed_ns=feature_ns, solver_elapsed_ns=solve_ns,
                elapsed_ns=time.perf_counter_ns()-tick, solver_diagnostics=public_result(solved.solver_result))
            metrics['stages'].append(row)
            if progress is not None:
                progress(row)
            del blocks, weights, solved, point, values
        metrics['service_elapsed_ns'] = time.perf_counter_ns()-start
        return tuple(outputs), metrics
    except Exception as error:
        metrics.update(aborted=True, completed_stages=len(outputs), service_elapsed_ns=time.perf_counter_ns()-start)
        error.service_diagnostics = metrics
        error.diagnostics = metrics
        raise
    finally:
        for stream in streams.values():
            stream.close()
