"""Version 28 exact repair from extended-precision compressed enclosures.

Trusted preparation establishes each descriptor's containment premise.
Repair either proves constant exact codes, or replays retained sources.
Replay scratch never changes the committed source-local descriptors.
"""
from dataclasses import dataclass, fields
import hashlib
import time

import numpy as np

from .anchor_transformer import prepare_context
from .compact_service import _records
from .compact_state import StageCodes, _name
from .dyadic_box_certificate import certify_dyadic_box
from .dyadic_row_quantizer import quantize_dyadic_rows
from .fixed_anchor_service import FixedAnchorService
from .fixed_compressed_state_v26 import (
    CompressedFactorState, FAMILY, STORAGE_SCHEMA, from_factor_state,
)
from .fixed_factor_codec_v26 import PRECISIONS, codec_binding
from .fixed_factor_state import preparer_binding
from .ordered_finite import FiniteWeights
from .preconditioned_box_certificate import certify_preconditioned_dyadic_box
from .native_box_certificate import certify_native_dyadic_box
from .ball_box_certificate_v28 import certify_ball_dyadic_box
from .sequential_finite import sequential_features
from .token_box_certificate import TokenBoxUnresolved


class NeuralBudgetExceeded(RuntimeError):
    """The next required traversal exceeds the declared request budget."""

    def __init__(self, message, diagnostics):
        super().__init__(message)
        self.diagnostics = diagnostics


@dataclass(frozen=True)
class FixedCompressedResult:
    stages: tuple
    state: CompressedFactorState
    diagnostics: dict


def _diagnostics(result):
    return {field.name: getattr(result, field.name)
            for field in fields(result) if field.name != 'codes'}


class FixedCompressedService:
    def __init__(self, decoder, base_target, *, bits=40, block_size=256,
                 solver_backend='native_ball', certificate_backend='ball',
                 max_neural_stage_record_pairs=None,
                 progress=None):
        if type(bits) is not int or bits not in PRECISIONS:
            raise ValueError('codec precision must be sixteen, twenty-four, thirty-two, forty, or forty-eight bits')
        if type(block_size) is not int or not 1 <= block_size <= 4096:
            raise ValueError('codec block size must be between one and 4096')
        if certificate_backend not in ('ball', 'ridge_floor', 'preconditioned', 'native_interval'):
            raise ValueError('certificate backend must be ball, ridge_floor, preconditioned, or native_interval')
        if (max_neural_stage_record_pairs is not None
                and (type(max_neural_stage_record_pairs) is not int
                     or max_neural_stage_record_pairs < 0)):
            raise ValueError('neural budget must be a nonnegative built-in integer or None')
        if progress is not None and not callable(progress):
            raise TypeError('progress must be callable or None')
        self.exact = FixedAnchorService(decoder, base_target,
            solver_backend=solver_backend, state_backend='factors')
        self.decoder, self.base_target, self.target = decoder, base_target, self.exact.target
        self.bits, self.block_size = bits, block_size
        self.solver_backend = solver_backend
        self.certificate_backend = certificate_backend
        self.max_neural_stage_record_pairs = max_neural_stage_record_pairs
        self.progress = progress

    def run(self, records, *, method='direct_fresh', prior=None, deleted_ids=()):
        start = time.perf_counter_ns()
        if method not in ('direct_fresh', 'repair', 'indexed_fresh'):
            raise ValueError('unknown compressed calibration comparison method')
        rows = _records(self.decoder, records)
        for rid, _ in rows:
            _name(rid)
        deleted = tuple(deleted_ids)
        if any(type(rid) is not str for rid in deleted) or len(set(deleted)) != len(deleted):
            raise ValueError('deletions must contain unique record IDs')
        for rid in deleted:
            _name(rid)
        if method == 'direct_fresh' and (prior is not None or deleted):
            raise ValueError('direct_fresh accepts retained records without prior state or deletions')
        metrics = dict(schema='fixed-compressed-service-v28', method=method,
            state_family=FAMILY, storage_schema=STORAGE_SCHEMA,
            target_sha256=self.target.digest, anchor_target_sha256=self.base_target.digest,
            target_semantics='fixed anchor features; not sequential calibration',
            solver_backend=self.solver_backend, certificate_backend=self.certificate_backend,
            bits=self.bits, block_size=self.block_size,
            records=len(rows), retained_source_token_reads=sum(len(t) for _, t in rows),
            record_validation_elapsed_ns=time.perf_counter_ns()-start,
            max_neural_stage_record_pairs=self.max_neural_stage_record_pairs,
            total_possible_neural_stage_record_pairs=len(rows)*len(self.target.stages),
            neural_stage_record_pairs=0, neural_stage_record_pairs_by_source={rid: 0 for rid, _ in rows},
            context_elapsed_ns=0, prior_validation_elapsed_ns=0,
            exact_preparation_elapsed_ns=0, compression_elapsed_ns=0,
            descriptor_decode_elapsed_ns=0, descriptor_decodes=0, descriptor_values_decoded=0,
            box_assembly_elapsed_ns=0, weights_elapsed_ns=0,
            certificate_elapsed_ns=0, certificate_attempted_stages=0,
            certificate_accepted_stages=0, certificate_rejected_stages=0,
            replay_elapsed_ns=0, replay_validation_elapsed_ns=0,
            replay_verified_stage_record_pairs=0, replay_verified_factor_bytes=0,
            fallback_feature_assembly_elapsed_ns=0, point_solver_elapsed_ns=0,
            point_solver_stages=0, singleton_point_stages=0,
            code_pack_elapsed_ns=0, state_construct_elapsed_ns=0,
            native_build_manifest=None,
            native_build_manifest_scope='point solver; certificate receipts appear in stage diagnostics',
            stages=[], pending_stage=None,
            model_seed_source='none', trusted_preparation_required=True,
            timing_scope='in-memory call; includes preparation, verification and fallback; excludes external loading and serialization')

        pending_stage_start_ns = None

        def budget_check(required=1):
            cap = self.max_neural_stage_record_pairs
            if cap is not None and metrics['neural_stage_record_pairs']+required > cap:
                metrics['service_elapsed_ns'] = time.perf_counter_ns()-start
                if metrics['pending_stage'] is not None:
                    metrics['pending_stage']['elapsed_ns'] = time.perf_counter_ns()-pending_stage_start_ns
                metrics['aborted'] = True
                raise NeuralBudgetExceeded('required retained replay exceeds neural stage-record budget', metrics)

        if method == 'direct_fresh':
            # Exact preparation executes every source-stage pair. Reject early
            # when its known complete cost exceeds the supplied work budget.
            budget_check(metrics['total_possible_neural_stage_record_pairs'])
            tick = time.perf_counter_ns()
            exact = FixedAnchorService(self.decoder, self.base_target,
                solver_backend=self.solver_backend, state_backend='factors', progress=self.progress).run(
                    tuple(dict(id=rid, tokens=tokens) for rid, tokens in rows))
            metrics['exact_preparation_elapsed_ns'] = time.perf_counter_ns()-tick
            metrics['exact_service_diagnostics'] = exact.diagnostics
            metrics['neural_stage_record_pairs'] = exact.diagnostics['anchor_preparation_stage_record_pairs']
            metrics['neural_stage_record_pairs_by_source'] = {rid: len(self.target.stages) for rid, _ in rows}
            metrics['point_solver_stages'] = len(exact.stages)
            metrics['native_build_manifest'] = exact.diagnostics['native_build_manifest']
            # These details are included inside exact_preparation_elapsed_ns.
            # They are breakdowns, not additional disjoint elapsed costs.
            for key in ('context_elapsed_ns', 'context_matrix_values',
                        'weights_elapsed_ns', 'code_pack_elapsed_ns'):
                metrics[key] = exact.diagnostics[key]
            metrics['point_solver_elapsed_ns'] = exact.diagnostics['solver_elapsed_ns']
            metrics['preparation_neural_elapsed_ns'] = exact.diagnostics['anchor_preparation_elapsed_ns']
            tick = time.perf_counter_ns()
            state = from_factor_state(exact.state, bits=self.bits, block_size=self.block_size)
            metrics['compression_elapsed_ns'] = time.perf_counter_ns()-tick
            metrics['prepared_records'] = len(rows)
            metrics['reused_records'] = 0
            metrics['stages'] = exact.diagnostics['stages']
            metrics['avoided_neural_stage_record_pairs'] = 0
            metrics['service_elapsed_ns'] = time.perf_counter_ns()-start
            return FixedCompressedResult(exact.stages, state, metrics)

        tick = time.perf_counter_ns()
        if type(prior) is not CompressedFactorState:
            raise TypeError('compressed repair requires CompressedFactorState')
        self.exact._validate_model(prior)
        if prior.anchor_target_sha256 != self.base_target.digest:
            raise ValueError('prior anchor target differs')
        if prior.bits != self.bits or prior.block_size != self.block_size:
            raise ValueError('prior codec settings differ')
        if prior.codec_sha256 != codec_binding():
            raise ValueError('prior codec binding differs')
        if prior.preparer_sha256 != preparer_binding():
            raise ValueError('prior fixed factor preparer binding differs')
        by_id = {a.record_id: a for a in prior.anchors}
        if not set(deleted) <= set(by_id) or {rid for rid, _ in rows} != set(by_id)-set(deleted):
            raise ValueError('retained membership differs from declared deletion')
        for rid, tokens in rows:
            if tuple(tokens) != by_id[rid].tokens:
                raise ValueError('retained record contents changed')
        anchors = tuple(by_id[rid] for rid, _ in rows)
        metrics['prepared_records'], metrics['reused_records'] = 0, len(anchors)
        metrics['prior_validation_elapsed_ns'] = time.perf_counter_ns()-tick
        tick = time.perf_counter_ns()
        context = prepare_context(self.decoder, self.base_target)
        metrics['context_elapsed_ns'] = time.perf_counter_ns()-tick
        metrics['context_matrix_values'] = context.initial_matrix_values
        tick = time.perf_counter_ns()
        for key in ('decoder_sha256', 'provider_sha256', 'anchor_sha256'):
            if getattr(prior, key) != getattr(context, key):
                raise ValueError('prior fixed anchor provenance differs')
        metrics['prior_validation_elapsed_ns'] += time.perf_counter_ns()-tick

        streams, positions, outputs = {}, {rid: -1 for rid, _ in rows}, []

        def decode(descriptor):
            tick = time.perf_counter_ns()
            box = descriptor.box()
            metrics['descriptor_decode_elapsed_ns'] += time.perf_counter_ns()-tick
            metrics['descriptor_decodes'] += 1
            metrics['descriptor_values_decoded'] += box.lower.size
            return box

        def replay(anchor, requested, requested_box):
            values = None
            for j in range(positions[anchor.record_id]+1, requested+1):
                budget_check()
                tick = time.perf_counter_ns()
                if j == 0:
                    streams[anchor.record_id] = sequential_features(self.decoder, anchor.tokens)
                    sid, produced = next(streams[anchor.record_id])
                else:
                    sid, produced = streams[anchor.record_id].send(context.anchor_matrices[j-1])
                metrics['replay_elapsed_ns'] += time.perf_counter_ns()-tick
                metrics['neural_stage_record_pairs'] += 1
                metrics['neural_stage_record_pairs_by_source'][anchor.record_id] += 1
                metrics['pending_stage']['neural_stage_record_pairs'] += 1
                positions[anchor.record_id] = j
                descriptor = anchor.descriptors[j]
                box = requested_box if j == requested else decode(descriptor)
                tick = time.perf_counter_ns()
                values = np.asarray(produced, dtype=np.float64)
                if sid != descriptor.stage_id or values.shape != descriptor.shape:
                    raise ArithmeticError('retained replay stage or factor shape differs')
                raw = values.astype('<f8', copy=False).tobytes(order='C')
                if hashlib.sha256(raw).hexdigest() != descriptor.source_sha256:
                    raise ArithmeticError('retained replay contradicts descriptor source hash')
                if not box.contains(values):
                    raise ArithmeticError('retained replay contradicts descriptor enclosure')
                metrics['replay_validation_elapsed_ns'] += time.perf_counter_ns()-tick
                metrics['replay_verified_stage_record_pairs'] += 1
                metrics['replay_verified_factor_bytes'] += len(raw)
            return values

        def point_solve(weights, features, stage, options):
            tick = time.perf_counter_ns()
            if self.solver_backend == 'native_ball':
                from .native_ball_quantizer import native_quantize_dyadic_rows, build_native_kernel
                quantized = native_quantize_dyadic_rows(weights, features, stage.scale_values, **options)
                if metrics['native_build_manifest'] is None:
                    metrics['native_build_manifest'] = build_native_kernel()
            else:
                quantized = quantize_dyadic_rows(weights, features, stage.scale_values, **options)
            metrics['point_solver_elapsed_ns'] += time.perf_counter_ns()-tick
            metrics['point_solver_stages'] += 1
            return quantized

        for i, stage in enumerate(self.target.stages):
            stage_start = time.perf_counter_ns()
            pending_stage_start_ns = stage_start
            metrics['pending_stage'] = dict(stage_id=stage.stage_id,
                certificate_backend=self.certificate_backend, route='checking_box',
                neural_stage_record_pairs=0)
            before_pairs = metrics['neural_stage_record_pairs']
            boxes = tuple(decode(anchor.descriptors[i]) for anchor in anchors)
            tick = time.perf_counter_ns()
            lower = (np.concatenate([b.lower for b in boxes], axis=0).T.copy() if boxes
                     else np.empty((stage.width, 0), dtype=np.float64))
            upper = (np.concatenate([b.upper for b in boxes], axis=0).T.copy() if boxes
                     else np.empty((stage.width, 0), dtype=np.float64))
            singleton = bool(np.array_equal(lower, upper))
            metrics['box_assembly_elapsed_ns'] += time.perf_counter_ns()-tick
            tick = time.perf_counter_ns()
            weights = FiniteWeights(stage.weights).array()
            metrics['weights_elapsed_ns'] += time.perf_counter_ns()-tick
            options = dict(bits=stage.bits, ridge=stage.ridge, normalization=stage.normalization,
                max_exact_rank=64, max_exact_coordinates=16, max_refinement_coordinates=64)
            rejection = None
            failure_diagnostics = None
            if singleton:
                # A singleton's defining feature matrix is known exactly.
                # Use the same selected point backend as ordinary reconstruction.
                quantized = point_solve(weights, lower, stage, options)
                metrics['singleton_point_stages'] += 1
            else:
                verifier = {'ball': certify_ball_dyadic_box,
                            'ridge_floor': certify_dyadic_box,
                            'preconditioned': certify_preconditioned_dyadic_box,
                            'native_interval': certify_native_dyadic_box}[self.certificate_backend]
                tick = time.perf_counter_ns()
                metrics['certificate_attempted_stages'] += 1
                try:
                    quantized = verifier(weights, lower, upper, stage.scale_values, **options)
                except TokenBoxUnresolved as exc:
                    rejection = str(exc)
                    failure_diagnostics = {key: getattr(exc, key)
                        for key in ('native_diagnostics', 'ball_diagnostics') if hasattr(exc, key)}
                metrics['certificate_elapsed_ns'] += time.perf_counter_ns()-tick
            accepted = rejection is None
            route = ('singleton_exact_point' if singleton
                     else 'box_certificate' if accepted else 'exact_retained_replay')
            metrics['pending_stage'].update(certificate_accepted=None if singleton else accepted,
                singleton_box=singleton, certificate_rejection=rejection,
                certificate_failure_diagnostics=failure_diagnostics, route=route)
            if accepted:
                if not singleton:
                    metrics['certificate_accepted_stages'] += 1
            else:
                metrics['certificate_rejected_stages'] += 1
                blocks = [replay(anchor, i, box) for anchor, box in zip(anchors, boxes)]
                tick = time.perf_counter_ns()
                features = (np.concatenate(blocks, axis=0).T.copy() if blocks
                            else np.empty((stage.width, 0), dtype=np.float64))
                metrics['fallback_feature_assembly_elapsed_ns'] += time.perf_counter_ns()-tick
                quantized = point_solve(weights, features, stage, options)
            tick = time.perf_counter_ns()
            outputs.append(StageCodes.from_array(stage.stage_id, quantized.codes,
                grid_axis='dyadic_row', bits=stage.bits, scale_values=stage.scale_values))
            metrics['code_pack_elapsed_ns'] += time.perf_counter_ns()-tick
            diag = dict(stage_id=stage.stage_id, certificate_accepted=None if singleton else accepted,
                certificate_backend=self.certificate_backend, singleton_box=singleton,
                certificate_rejection=rejection, certificate_failure_diagnostics=failure_diagnostics, route=route,
                neural_stage_record_pairs=metrics['neural_stage_record_pairs']-before_pairs,
                solver_diagnostics=_diagnostics(quantized), elapsed_ns=time.perf_counter_ns()-stage_start)
            metrics['stages'].append(diag)
            metrics['pending_stage'] = None
            pending_stage_start_ns = None
            if self.progress:
                self.progress(diag)
        tick = time.perf_counter_ns()
        state = CompressedFactorState(prior.target_sha256, prior.anchor_target_sha256,
            prior.decoder_sha256, prior.provider_sha256, prior.anchor_sha256,
            prior.preparer_sha256, prior.codec_sha256, prior.bits, prior.block_size,
            tuple(outputs), anchors)
        metrics['state_construct_elapsed_ns'] = time.perf_counter_ns()-tick
        metrics['avoided_neural_stage_record_pairs'] = (
            metrics['total_possible_neural_stage_record_pairs']-metrics['neural_stage_record_pairs'])
        metrics['service_elapsed_ns'] = time.perf_counter_ns()-start
        return FixedCompressedResult(tuple(outputs), state, metrics)
