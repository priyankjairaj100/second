"""Bounded adaptive backend for the unchanged fixed-feature service.

The request/state path mirrors the V29 exact-factor service. Only the point
solver dispatch differs. Prior state, target, feature, and packing contracts
remain those of the established service. Resource refusal returns no state.
"""
from dataclasses import dataclass, fields
import hashlib
import json
import struct
import time
import numpy as np

from .anchor_state import AnchorState, LoadLimits, serialize as encode_inner, parse as decode_inner
from .anchor_transformer import prepare_context, prepare_anchor
from .compact_state import CompactState, StageCodes, _digest, _json, _name
from .compact_service import _records
from .dyadic_row_quantizer import quantize_dyadic_rows
from .fixed_anchor_target import build_fixed_anchor_target
from .fixed_factor_state import (FixedFactorLeaf, FixedFactorState, STORAGE_SCHEMA as FACTOR_SCHEMA,
    MAGIC as FACTOR_MAGIC, prepare_leaf, from_anchor, preparer_binding,
    serialize as serialize_factors, parse as parse_factors)
from .ordered_finite import FiniteWeights
from .sequential_finite import sequential_features

from .fixed_anchor_service import FixedAnchorState, FixedAnchorResult, FAMILY, METHODS
from .adaptive_calibration_v30 import (AdaptiveBudget, quantize_adaptive_dyadic_rows,
    assess_routes, CalibrationWorkRefused)
from .low_rank_certified import LowRankUnresolved


class AdaptiveFixedAnchorService:
    def __init__(self, decoder, base_target, *, solver_backend='auto', use_candidates=False,
                 state_backend='factors', progress=None, coefficient_budget=AdaptiveBudget(),
                 max_point_work_units=48_000_000_000):
        if solver_backend not in ('auto', 'token', 'primal'):
            raise ValueError('point backend must be auto, token, or primal')
        if type(coefficient_budget) is not AdaptiveBudget:
            raise TypeError('coefficient_budget must be AdaptiveBudget')
        if use_candidates:
            raise ValueError('adaptive service does not use prior model proposals')
        self.coefficient_budget = coefficient_budget
        if type(max_point_work_units) is not int or max_point_work_units < 0:
            raise ValueError('max_point_work_units must be a nonnegative integer')
        self.max_point_work_units = max_point_work_units
        if type(use_candidates) is not bool:
            raise ValueError('use_candidates must be Boolean')
        if progress is not None and not callable(progress):
            raise TypeError('progress must be callable or None')
        if state_backend not in ('anchors', 'factors'):
            raise ValueError('state_backend must be anchors or factors')
        self.decoder, self.base_target = decoder, base_target
        self.target = build_fixed_anchor_target(decoder, base_target)
        if any(stage.bits != 4 for stage in self.target.stages):
            raise ValueError('adaptive service requires registered four-bit target grids')
        self.solver_backend, self.use_candidates, self.progress = solver_backend, use_candidates, progress
        self.state_backend = state_backend

    def admit_records(self, rows):
        """Reserve every stage before context, source decoding, or neural work."""
        tokens = sum(len(token_ids) for _, token_ids in rows)
        reports = []
        total = 0
        for stage in self.target.stages:
            report = assess_routes(len(stage.weights), stage.width, tokens, budget=self.coefficient_budget)
            selected = report['selected'] if self.solver_backend == 'auto' else self.solver_backend
            report = dict(report, stage_id=stage.stage_id, selected=selected)
            reports.append(report)
            if selected is None or not report['routes'][selected]['admitted']:
                raise CalibrationWorkRefused('complete request has an inadmissible point stage',
                    dict(stages=reports, reserved_work_units=total, request_cap=self.max_point_work_units))
            total += report['routes'][selected]['work_units']
        admission = dict(stages=reports, reserved_work_units=total, request_cap=self.max_point_work_units,
            scope='structural allowance; not measured CPU or whole-process memory')
        if total > self.max_point_work_units:
            raise CalibrationWorkRefused('complete request exceeds cumulative point-work cap', admission)
        return admission

    def _validate_model(self, model):
        if model.target_sha256 != self.target.digest or len(model.stages) != len(self.target.stages):
            raise ValueError('fixed-feature target or complete model differs')
        for code, stage in zip(model.stages, self.target.stages):
            if (type(code) is not StageCodes or code.stage_id != stage.stage_id
                    or code.grid_axis != 'dyadic_row' or code.bits != stage.bits
                    or code.scale_values != stage.scale_values
                    or code.shape != (len(stage.weights), stage.width)):
                raise ValueError('fixed-feature model grid differs')

    def run_prepared(self, records, anchors, *, preparation_receipt):
        """Use trusted existing leaves and retain their external preparation cost.

        This route measures neither ordinary fresh preparation nor repair.
        The caller supplies a preparation receipt from the previous worker.
        Its elapsed value is recorded provenance, not a verified timer here.
        """
        return self.run(records, prepared_anchors=anchors, preparation_receipt=preparation_receipt)

    def run(self, records, *, method='direct_fresh', prior=None, deleted_ids=(), initial_model=None,
            prepared_anchors=None, preparation_receipt=None):
        start = time.perf_counter_ns()
        if method not in METHODS:
            raise ValueError('unknown fixed calibration comparison method')
        rows = _records(self.decoder, records)
        point_admission = self.admit_records(rows)
        for rid, _ in rows:
            _name(rid)
        deleted = tuple(deleted_ids)
        if any(type(rid) is not str for rid in deleted) or len(set(deleted)) != len(deleted):
            raise ValueError('deletions must contain unique record IDs')
        indexed = method in ('repair', 'indexed_fresh')
        stateful = method != 'model_only_fresh'
        if not indexed and (prior is not None or deleted):
            raise ValueError('fresh methods accept retained records only')
        if prepared_anchors is not None:
            if method != 'direct_fresh' or initial_model is not None:
                raise ValueError('prepared leaves require direct_fresh without a model seed')
            if (type(preparation_receipt) is not dict
                    or set(preparation_receipt) != {'source', 'artifact_sha256', 'elapsed_ns'}
                    or type(preparation_receipt['source']) is not str or not preparation_receipt['source']
                    or type(preparation_receipt['elapsed_ns']) is not int
                    or preparation_receipt['elapsed_ns'] < 0):
                raise ValueError('prepared leaves require explicit preparation provenance')
            _digest(preparation_receipt['artifact_sha256'])
        elif preparation_receipt is not None:
            raise ValueError('preparation receipt requires prepared leaves')
        if initial_model is not None:
            if method != 'model_only_fresh' or not self.use_candidates:
                raise ValueError('initial_model requires model_only_fresh and use_candidates')
            if type(initial_model) is not CompactState or initial_model.factors:
                raise ValueError('initial_model requires complete stages and no factors')
            self._validate_model(initial_model)
        metrics = dict(schema='adaptive-fixed-anchor-service-v30', state_family=FAMILY, method=method,
            point_admission=point_admission,
            target_sha256=self.target.digest, anchor_target_sha256=self.base_target.digest,
            target_semantics='fixed anchor features; not sequential calibration',
            solver_backend=self.solver_backend, use_candidates=self.use_candidates,
            state_backend=self.state_backend,
            storage_schema=FACTOR_SCHEMA if self.state_backend == 'factors' else 'complete_anchor_summary_envelope_v1',
            execution_route='prepared_leaf_construction' if prepared_anchors is not None else method,
            external_preparation_receipt=dict(preparation_receipt) if preparation_receipt is not None else None,
            external_preparation_elapsed_ns=preparation_receipt['elapsed_ns'] if preparation_receipt is not None else 0,
            preparation_receipt_verified_by_service=False,
            records=len(rows), retained_source_token_reads=sum(len(tokens) for _, tokens in rows),
            record_validation_elapsed_ns=time.perf_counter_ns()-start,
            context_elapsed_ns=0, prior_validation_elapsed_ns=0, anchor_preparation_elapsed_ns=0,
            anchor_prepared_records=0, anchor_reused_records=0, anchor_preparation_stage_record_pairs=0,
            anchor_conversion_elapsed_ns=0, anchor_converted_records=0,
            anchor_leaf_factor_reads=0, fixed_feature_values_read=0, neural_stage_record_pairs=0,
            feature_elapsed_ns=0, weights_elapsed_ns=0, candidate_elapsed_ns=0,
            solver_elapsed_ns=0, code_pack_elapsed_ns=0, native_build_manifest=None, stages=[],
            timing_scope='in-memory call; includes context and anchor preparation; excludes external loading and serialized output')
        tick = time.perf_counter_ns()
        context = prepare_context(self.decoder, self.base_target)
        metrics['context_elapsed_ns'] = time.perf_counter_ns()-tick
        metrics['context_matrix_values'] = context.initial_matrix_values
        anchors = ()
        if indexed:
            tick = time.perf_counter_ns()
            required_state = FixedFactorState if self.state_backend == 'factors' else FixedAnchorState
            if type(prior) is not required_state:
                raise TypeError('fixed calibration repair requires the selected state backend')
            self._validate_model(prior)
            if prior.anchor_target_sha256 != self.base_target.digest:
                raise ValueError('prior anchor target differs')
            for key in ('decoder_sha256', 'provider_sha256', 'anchor_sha256'):
                if getattr(prior, key) != getattr(context, key):
                    raise ValueError('prior fixed anchor provenance differs')
            if self.state_backend == 'factors' and prior.preparer_sha256 != preparer_binding():
                raise ValueError('prior fixed factor preparer binding differs')
            by_id = {a.record_id:a for a in prior.anchors}
            if not set(deleted) <= set(by_id) or {rid for rid, _ in rows} != set(by_id)-set(deleted):
                raise ValueError('retained membership differs from declared deletion')
            for rid, tokens in rows:
                if tuple(by_id[rid].tokens) != tuple(tokens):
                    raise ValueError('retained record contents changed')
            anchors = tuple(by_id[rid] for rid, _ in rows)
            metrics['anchor_reused_records'] = len(anchors)
            metrics['prior_validation_elapsed_ns'] = time.perf_counter_ns()-tick
        elif prepared_anchors is not None:
            tick = time.perf_counter_ns()
            supplied = tuple(prepared_anchors)
            if self.state_backend == 'factors':
                convert_start = time.perf_counter_ns()
                anchors = tuple(a if type(a) is FixedFactorLeaf else from_anchor(a) for a in supplied)
                metrics['anchor_conversion_elapsed_ns'] = time.perf_counter_ns()-convert_start
                metrics['anchor_converted_records'] = sum(type(a) is not FixedFactorLeaf for a in supplied)
                envelope = FixedFactorState(self.target.digest, self.base_target.digest, context.decoder_sha256,
                    context.provider_sha256, context.anchor_sha256, preparer_binding(), context.anchor_codes, anchors)
            else:
                # Reuse leaf validation, never a falsely labelled previous model.
                envelope = AnchorState(self.base_target.digest, context.decoder_sha256,
                    context.provider_sha256, context.anchor_sha256, context.anchor_codes, supplied)
            anchors = envelope.anchors
            if tuple((a.record_id, tuple(a.tokens)) for a in anchors) != tuple((rid, tuple(tokens)) for rid, tokens in rows):
                raise ValueError('prepared leaves differ from retained records')
            metrics['anchor_reused_records'] = len(anchors)
            metrics['prior_validation_elapsed_ns'] = time.perf_counter_ns()-tick
        elif stateful:
            tick = time.perf_counter_ns()
            prepare = prepare_leaf if self.state_backend == 'factors' else prepare_anchor
            anchors = tuple(prepare(self.decoder, self.base_target, dict(id=rid, tokens=tokens),
                                    context=context) for rid, tokens in rows)
            metrics['anchor_preparation_elapsed_ns'] = time.perf_counter_ns()-tick
            metrics['anchor_prepared_records'] = len(anchors)
            metrics['anchor_preparation_stage_record_pairs'] = len(anchors)*len(self.target.stages)
        metrics['stored_anchor_nodes'] = sum(len(getattr(a, 'nodes', ())) for a in anchors)
        metrics['stored_anchor_factor_values'] = sum(v.size for a in anchors for _, _, v in a.factors)
        seed = (prior if indexed else initial_model) if self.use_candidates else None
        metrics['model_seed_source'] = ('prior_state' if indexed else 'external_model_only') if seed else 'none'
        streams, outputs = {}, []
        for i, stage in enumerate(self.target.stages):
            stage_start = time.perf_counter_ns()
            tick = time.perf_counter_ns()
            blocks = []
            if stateful:
                for anchor in anchors:
                    sid, _, values = anchor.factors[i]
                    if sid != stage.stage_id or values.shape != (len(anchor.tokens), stage.width):
                        raise ValueError('fixed anchor factor order or dimensions differ')
                    blocks.append(values)
                    metrics['anchor_leaf_factor_reads'] += 1
            else:
                for rid, tokens in rows:
                    if i == 0:
                        streams[rid] = sequential_features(self.decoder, tokens)
                        sid, values = next(streams[rid])
                    else:
                        sid, values = streams[rid].send(context.anchor_matrices[i-1])
                    if sid != stage.stage_id:
                        raise ArithmeticError('fixed anchor traversal stage differs')
                    blocks.append(np.asarray(values, dtype=np.float64))
                    metrics['neural_stage_record_pairs'] += 1
            features = (np.concatenate(blocks, axis=0).T.copy() if blocks
                        else np.empty((stage.width, 0), dtype=np.float64))
            metrics['fixed_feature_values_read'] += features.size
            feature_ns = time.perf_counter_ns()-tick
            tick = time.perf_counter_ns()
            weights = FiniteWeights(stage.weights).array()
            weights_ns = time.perf_counter_ns()-tick
            tick = time.perf_counter_ns()
            candidate = seed.stages[i].array() if seed else None
            candidate_ns = time.perf_counter_ns()-tick
            options = dict(bits=stage.bits, ridge=stage.ridge, normalization=stage.normalization,
                           max_exact_rank=64, max_exact_coordinates=16, max_refinement_coordinates=64)
            tick = time.perf_counter_ns()
            try:
                quantized = quantize_adaptive_dyadic_rows(weights, features, stage.scale_values,
                    candidate=candidate, route=self.solver_backend, budget=self.coefficient_budget, **options)
            except LowRankUnresolved as exc:
                metrics.update(aborted=True, unresolved_stage_id=stage.stage_id,
                    failed_solver_elapsed_ns=time.perf_counter_ns()-tick,
                    service_elapsed_ns=time.perf_counter_ns()-start)
                exc.service_diagnostics = metrics
                exc.diagnostics = metrics
                raise
            solver_ns = time.perf_counter_ns()-tick
            tick = time.perf_counter_ns()
            outputs.append(StageCodes.from_array(stage.stage_id, quantized.codes,
                grid_axis='dyadic_row', bits=stage.bits, scale_values=stage.scale_values))
            pack_ns = time.perf_counter_ns()-tick
            diag = dict(stage_id=stage.stage_id, feature_elapsed_ns=feature_ns,
                weights_elapsed_ns=weights_ns, candidate_elapsed_ns=candidate_ns,
                solver_elapsed_ns=solver_ns, code_pack_elapsed_ns=pack_ns,
                elapsed_ns=time.perf_counter_ns()-stage_start,
                solver_diagnostics={f.name:getattr(quantized, f.name)
                    for f in fields(quantized) if f.name != 'codes'})
            for key in ('feature_elapsed_ns', 'weights_elapsed_ns', 'candidate_elapsed_ns',
                        'solver_elapsed_ns', 'code_pack_elapsed_ns'):
                metrics[key] += diag[key]
            metrics['stages'].append(diag)
            if self.progress:
                self.progress(diag)
        tick = time.perf_counter_ns()
        state = None
        if stateful:
            if self.state_backend == 'factors':
                state = FixedFactorState(self.target.digest, self.base_target.digest, context.decoder_sha256,
                    context.provider_sha256, context.anchor_sha256, preparer_binding(), tuple(outputs), anchors)
            else:
                state = FixedAnchorState(self.target.digest, self.base_target.digest, context.decoder_sha256,
                    context.provider_sha256, context.anchor_sha256, tuple(outputs), anchors)
        metrics['state_construct_elapsed_ns'] = time.perf_counter_ns()-tick
        metrics['service_elapsed_ns'] = time.perf_counter_ns()-start
        return FixedAnchorResult(tuple(outputs), state, metrics)
