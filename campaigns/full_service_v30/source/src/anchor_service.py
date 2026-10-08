"""Exact dyadic output with canonical, calibration-independent anchor leaves.

The transformer provider proves each accepted feature box. Unresolved boxes
trigger exact sequential replay. This module makes no speed claim.
"""
from dataclasses import dataclass, fields
import time

import numpy as np

from .anchor_state import AnchorState, FAMILY
from .compact_state import CompactState, StageCodes, _name
from .compact_service import _records
from .dyadic_box_certificate import certify_dyadic_box
from .dyadic_row_quantizer import quantize_dyadic_rows
from .finite_feature_boxes import FloatBox
from .ordered_finite import FiniteWeights
from .sequential_finite import sequential_features
from .token_box_certificate import TokenBoxUnresolved


METHODS = ('direct_fresh', 'repair', 'indexed_fresh', 'model_only_fresh')


@dataclass(frozen=True)
class AnchorResult:
    stages: tuple
    state: object
    diagnostics: dict


class AnchorService:
    """Complete trusted-state service with explicitly bounded box attempts.

Every method receives the same point solver and exact feature schedule.
Prior code proposals require the explicit use_candidates option.
Model-only reconstruction accepts a factor-free external model seed.
State parsing authenticates no source without a trusted receipt.
"""
    def __init__(self, decoder, target, *, solver_backend='native_ball',
                 use_bounds=True, use_candidates=False, max_box_stage_attempts=4,
                 max_box_tokens=64, max_box_decisions=65536, progress=None):
        if tuple(s.stage_id for s in target.stages) != tuple(decoder.stage_ids):
            raise ValueError('complete target and decoder stage order differ')
        for i, stage in enumerate(target.stages):
            if (len(stage.dependencies) != i or set(stage.dependencies) != set(decoder.stage_ids[:i])
                    or not hasattr(stage, 'scale_values')):
                raise ValueError('anchor service requires a complete dyadic-row target')
        if solver_backend not in ('native_ball', 'reference'):
            raise ValueError('point backend must be native_ball or reference')
        if type(use_bounds) is not bool or type(use_candidates) is not bool:
            raise ValueError('bound and candidate options must be Boolean')
        for value in (max_box_stage_attempts, max_box_tokens, max_box_decisions):
            if type(value) is not int or value < 0:
                raise ValueError('box budgets must be nonnegative built-in integers')
        self.decoder, self.target = decoder, target
        self.solver_backend, self.use_bounds = solver_backend, use_bounds
        self.use_candidates = use_candidates
        self.max_box_stage_attempts = max_box_stage_attempts
        self.max_box_tokens, self.max_box_decisions = max_box_tokens, max_box_decisions
        self.progress = progress

    def _validate_model(self, model):
        if model.target_sha256 != self.target.digest or len(model.stages) != len(self.target.stages):
            raise ValueError('model target or complete stage count differs')
        for codes, stage in zip(model.stages, self.target.stages):
            if (type(codes) is not StageCodes or codes.stage_id != stage.stage_id
                    or codes.grid_axis != 'dyadic_row' or codes.bits != stage.bits
                    or codes.scale_values != stage.scale_values
                    or codes.shape != (len(stage.weights), stage.width)):
                raise ValueError('model stage grid or shape differs')

    def run(self, records, *, method='direct_fresh', prior=None, deleted_ids=(), initial_model=None):
        from .anchor_transformer import prepare_context, prepare_anchor, bound_stage
        started = time.perf_counter_ns()
        if method not in METHODS:
            raise ValueError('unknown anchor comparison method')
        rows = _records(self.decoder, records)
        for rid, _ in rows:
            _name(rid)
        deleted = tuple(deleted_ids)
        if any(type(rid) is not str for rid in deleted) or len(set(deleted)) != len(deleted):
            raise ValueError('deletions must contain unique record IDs')
        stateful = method != 'model_only_fresh'
        indexed = method in ('repair', 'indexed_fresh')
        if not indexed and (prior is not None or deleted):
            raise ValueError('fresh methods accept only retained records')
        if initial_model is not None:
            if method != 'model_only_fresh' or not self.use_candidates:
                raise ValueError('initial_model requires model_only_fresh and use_candidates')
            if type(initial_model) is not CompactState or initial_model.factors:
                raise ValueError('initial_model requires complete stages and no factors')
            self._validate_model(initial_model)
        metrics = dict(
            schema='anchor-service-v20', method=method, state_family=FAMILY,
            target_sha256=self.target.digest, solver_backend=self.solver_backend,
            use_bounds=self.use_bounds, use_candidates=self.use_candidates,
            timing_scope='in-memory service call; includes anchor preparation and context; excludes external loading and output',
            max_box_stage_attempts=self.max_box_stage_attempts,
            max_box_tokens=self.max_box_tokens, max_box_decisions=self.max_box_decisions,
            record_validation_elapsed_ns=time.perf_counter_ns()-started,
            records=len(rows), retained_source_token_reads=sum(len(t) for _, t in rows),
            context_elapsed_ns=0, anchor_preparation_elapsed_ns=0,
            anchor_prepared_records=0, anchor_reused_records=0,
            anchor_preparation_stage_record_pairs=0, prior_validation_elapsed_ns=0,
            bound_elapsed_ns=0, box_certificate_elapsed_ns=0,
            exact_features_elapsed_ns=0, point_solver_elapsed_ns=0,
            weights_elapsed_ns=0, candidate_elapsed_ns=0, code_pack_elapsed_ns=0,
            bound_stage_record_calls=0, box_stage_attempts=0,
            certified_stages=0, certified_stage_record_pairs=0,
            neural_stage_record_pairs=0, changed_prefix_pairs_avoided=0,
            native_build_manifest=None, stages=[])
        context = None
        anchors = ()
        if stateful:
            tick = time.perf_counter_ns()
            context = prepare_context(self.decoder, self.target)
            metrics['context_elapsed_ns'] = time.perf_counter_ns()-tick
            metrics['context_matrix_values'] = context.initial_matrix_values
            metrics['anchor_bindings'] = {k:getattr(context, k) for k in (
                'decoder_sha256', 'provider_sha256', 'anchor_sha256')}
        if indexed:
            tick = time.perf_counter_ns()
            if type(prior) is not AnchorState:
                raise TypeError('repair requires complete AnchorState')
            self._validate_model(prior)
            for key in ('decoder_sha256', 'provider_sha256', 'anchor_sha256'):
                if getattr(prior, key) != getattr(context, key):
                    raise ValueError('prior anchor provenance binding differs')
            by_id = {a.record_id:a for a in prior.anchors}
            if not set(deleted) <= set(by_id) or {rid for rid, _ in rows} != set(by_id)-set(deleted):
                raise ValueError('retained membership differs from declared deletion')
            for rid, tokens in rows:
                if tuple(by_id[rid].tokens) != tuple(tokens):
                    raise ValueError('retained record contents changed')
            anchors = tuple(by_id[rid] for rid, _ in rows)
            metrics['anchor_reused_records'] = len(anchors)
            metrics['prior_validation_elapsed_ns'] = time.perf_counter_ns()-tick
        elif stateful:
            tick = time.perf_counter_ns()
            anchors = tuple(prepare_anchor(self.decoder, self.target, dict(id=rid, tokens=tokens),
                                           context=context) for rid, tokens in rows)
            metrics['anchor_preparation_elapsed_ns'] = time.perf_counter_ns()-tick
            metrics['anchor_prepared_records'] = len(anchors)
            metrics['anchor_preparation_stage_record_pairs'] = len(rows)*len(self.target.stages)
        metrics['stored_anchor_nodes'] = sum(len(a.nodes) for a in anchors)
        metrics['stored_anchor_factor_values'] = sum(v.size for a in anchors for _, _, v in a.factors)
        seed = (prior if indexed else initial_model) if self.use_candidates else None
        metrics['model_seed_source'] = ('prior_state' if indexed else 'external_model_only') if seed else 'none'
        streams, positions, current = {}, {}, {}
        outputs, installed = [], []
        visited, certified_pairs = set(), set()
        changed_pairs = set()

        def evaluate(rid, tokens, index):
            if rid not in streams:
                streams[rid] = sequential_features(self.decoder, tokens)
                current[rid], positions[rid] = next(streams[rid]), 0
                visited.add((rid, 0))
                metrics['neural_stage_record_pairs'] += 1
            while positions[rid] < index:
                current[rid] = streams[rid].send(installed[positions[rid]])
                positions[rid] += 1
                visited.add((rid, positions[rid]))
                metrics['neural_stage_record_pairs'] += 1
            sid, values = current[rid]
            if sid != self.target.stages[index].stage_id:
                raise ArithmeticError('exact stage traversal mismatch')
            return np.asarray(values, dtype=np.float64)

        def point_solve(weights, features, stage, candidate, options):
            if self.solver_backend == 'native_ball':
                from .native_ball_quantizer import native_quantize_dyadic_rows, build_native_kernel
                result = native_quantize_dyadic_rows(weights, features, stage.scale_values,
                                                     candidate=candidate, **options)
                if metrics['native_build_manifest'] is None:
                    metrics['native_build_manifest'] = build_native_kernel()
                return result
            return quantize_dyadic_rows(weights, features, stage.scale_values, **options)

        for i, stage in enumerate(self.target.stages):
            stage_started = time.perf_counter_ns()
            diag = dict(stage_id=stage.stage_id, box_attempted=False, box_accepted=False,
                        bound_diagnostics={}, bound_record_diagnostics=[], fallback_reason=None,
                        singleton_point_solver=False,
                        bound_elapsed_ns=0, box_certificate_elapsed_ns=0,
                        exact_features_elapsed_ns=0, point_solver_elapsed_ns=0,
                        weights_elapsed_ns=0, candidate_elapsed_ns=0, code_pack_elapsed_ns=0)
            tick = time.perf_counter_ns()
            weights = FiniteWeights(stage.weights).array()
            diag['weights_elapsed_ns'] = time.perf_counter_ns()-tick
            tick = time.perf_counter_ns()
            candidate = seed.stages[i].array() if seed else None
            diag['candidate_elapsed_ns'] = time.perf_counter_ns()-tick
            options = dict(bits=stage.bits, ridge=stage.ridge, normalization=stage.normalization,
                           max_exact_rank=64, max_exact_coordinates=16, max_refinement_coordinates=64)
            quantized, boxes = None, {}
            eligible = (stateful and self.use_bounds and bool(rows)
                        and metrics['box_stage_attempts'] < self.max_box_stage_attempts
                        and sum(len(t) for _, t in rows) <= self.max_box_tokens
                        and weights.size <= self.max_box_decisions)
            if eligible:
                diag['box_attempted'] = True
                metrics['box_stage_attempts'] += 1
                tick = time.perf_counter_ns()
                try:
                    for anchor in anchors:
                        metrics['bound_stage_record_calls'] += 1
                        leaf_work = {}
                        try:
                            box = bound_stage(self.decoder, self.target, anchor, tuple(outputs), stage.stage_id,
                                              context=context, diagnostics=leaf_work)
                        finally:
                            diag['bound_record_diagnostics'].append(dict(record_id=anchor.record_id, **leaf_work))
                            for key, value in leaf_work.items():
                                diag['bound_diagnostics'][key] = diag['bound_diagnostics'].get(key, 0)+value
                        if type(box) is not FloatBox or box.shape != (len(anchor.tokens), stage.width):
                            raise ValueError('provider feature box shape differs')
                        boxes[anchor.record_id] = box
                    diag['bound_elapsed_ns'] = time.perf_counter_ns()-tick
                    tick = time.perf_counter_ns()
                    lower = np.concatenate([boxes[rid].lower for rid, _ in rows], axis=0).T.copy()
                    if all(box.singleton for box in boxes.values()):
                        diag['singleton_point_solver'] = True
                        quantized = point_solve(weights, lower, stage, candidate, options)
                    else:
                        upper = np.concatenate([boxes[rid].upper for rid, _ in rows], axis=0).T.copy()
                        quantized = certify_dyadic_box(weights, lower, upper, stage.scale_values,
                                                       candidate_codes=candidate, **options)
                    diag['box_certificate_elapsed_ns'] = time.perf_counter_ns()-tick
                    diag['box_accepted'] = True
                    metrics['certified_stages'] += 1
                    metrics['certified_stage_record_pairs'] += len(rows)
                    certified_pairs.update((rid, i) for rid, _ in rows)
                except (ArithmeticError, TokenBoxUnresolved) as exc:
                    # ValueError indicates an inconsistent binding or box. It must abort.
                    if not diag['bound_elapsed_ns']:
                        diag['bound_elapsed_ns'] = time.perf_counter_ns()-tick
                    else:
                        diag['box_certificate_elapsed_ns'] = time.perf_counter_ns()-tick
                    diag['fallback_reason'] = type(exc).__name__ + ': ' + str(exc)
            else:
                diag['fallback_reason'] = 'boxes disabled, empty input, or deterministic box budget'
            if context is not None and any(
                    outputs[j].digest != context.anchor_codes[j].digest for j in range(i)):
                changed_pairs.update((rid, i) for rid, _ in rows)
            if quantized is None:
                tick = time.perf_counter_ns()
                blocks = []
                for rid, tokens in rows:
                    values = evaluate(rid, tokens, i)
                    if rid in boxes and not boxes[rid].contains(values):
                        raise ValueError('exact factors contradict the provider box')
                    blocks.append(values)
                features = (np.concatenate(blocks, axis=0).T.copy() if blocks
                            else np.empty((stage.width, 0), dtype=np.float64))
                diag['exact_features_elapsed_ns'] = time.perf_counter_ns()-tick
                tick = time.perf_counter_ns()
                quantized = point_solve(weights, features, stage, candidate, options)
                diag['point_solver_elapsed_ns'] = time.perf_counter_ns()-tick
            tick = time.perf_counter_ns()
            codes = StageCodes.from_array(stage.stage_id, quantized.codes, grid_axis='dyadic_row',
                                         bits=stage.bits, scale_values=stage.scale_values)
            outputs.append(codes)
            installed.append(quantized.codes)
            diag['code_pack_elapsed_ns'] = time.perf_counter_ns()-tick
            diag['solver_diagnostics'] = {f.name:getattr(quantized, f.name)
                                          for f in fields(quantized) if f.name != 'codes'}
            diag['elapsed_ns'] = time.perf_counter_ns()-stage_started
            for key in ('bound_elapsed_ns', 'box_certificate_elapsed_ns', 'exact_features_elapsed_ns',
                        'point_solver_elapsed_ns', 'weights_elapsed_ns', 'candidate_elapsed_ns', 'code_pack_elapsed_ns'):
                metrics[key] += diag[key]
            metrics['stages'].append(diag)
            if self.progress:
                self.progress(diag)
        tick = time.perf_counter_ns()
        state = (AnchorState(self.target.digest, context.decoder_sha256, context.provider_sha256,
                             context.anchor_sha256, tuple(outputs), anchors) if stateful else None)
        metrics['state_construct_elapsed_ns'] = time.perf_counter_ns()-tick
        metrics['changed_prefix_pairs_avoided'] = len((certified_pairs & changed_pairs)-visited)
        metrics['retained_replay_stage_record_pairs_avoided'] = len(rows)*len(outputs)-len(visited)
        metrics['service_elapsed_ns'] = time.perf_counter_ns()-started
        return AnchorResult(tuple(outputs), state, metrics)
