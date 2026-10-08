"""Exact deletion service for an explicitly different, fixed-feature target.

This service preserves fixed-anchor calibration, not sequential calibration.
Fresh and repair share all point solvers. Indexed reconstruction has the same
retained anchor access as repair and therefore uses the same numerical path.
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
from .ordered_finite import FiniteWeights
from .sequential_finite import sequential_features

FAMILY = 'fixed_anchor_calibration_v1'
MAGIC = b'VCFA\x01\x00\x00\x00'
METHODS = ('direct_fresh', 'repair', 'indexed_fresh', 'model_only_fresh')


def _sha(value):
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class FixedAnchorState:
    target_sha256: str
    anchor_target_sha256: str
    decoder_sha256: str
    provider_sha256: str
    anchor_sha256: str
    stages: tuple
    anchors: tuple

    def __post_init__(self):
        _digest(self.target_sha256)
        if self.target_sha256 == self.anchor_target_sha256:
            raise ValueError('fixed-feature target must differ from its anchor target')
        inner = self._inner()
        object.__setattr__(self, 'stages', inner.stages)
        object.__setattr__(self, 'anchors', inner.anchors)

    def _inner(self):
        # This private envelope reuses structural encoding only.
        # Its model carries the OUTER fixed-feature target semantics.
        return AnchorState(self.anchor_target_sha256, self.decoder_sha256, self.provider_sha256,
                           self.anchor_sha256, self.stages, self.anchors)

    @property
    def record_ids(self):
        return tuple(a.record_id for a in self.anchors)

    @property
    def digest(self):
        return _sha(serialize(self))

    def canonical_bytes(self):
        return serialize(self)


def serialize(state):
    if type(state) is not FixedAnchorState:
        raise TypeError('fixed calibration state requires FixedAnchorState')
    inner = encode_inner(state._inner())
    header = _json(dict(family=FAMILY, target_sha256=state.target_sha256,
        anchor_target_sha256=state.anchor_target_sha256,
        inner_nbytes=len(inner), inner_sha256=_sha(inner)))
    return MAGIC+struct.pack('<Q', len(header))+header+inner


def parse(data, *, limits=LoadLimits(), expected_sha256=None):
    if type(data) is not bytes or type(limits) is not LoadLimits:
        raise TypeError('immutable bytes and LoadLimits are required')
    if len(data) < 16 or len(data) > limits.max_bytes or data[:8] != MAGIC:
        raise ValueError('invalid fixed calibration state magic or size')
    if expected_sha256 is not None and _sha(data) != _digest(expected_sha256):
        raise ValueError('fixed calibration state does not match trusted digest')
    n = struct.unpack('<Q', data[8:16])[0]
    if n > limits.max_header_bytes or n > len(data)-16:
        raise ValueError('fixed calibration header exceeds its bound')
    raw = data[16:16+n]
    try:
        header = json.loads(raw)
        canonical = _json(header)
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise ValueError('invalid fixed calibration JSON') from exc
    if canonical != raw:
        raise ValueError('fixed calibration JSON is not canonical')
    required = {'family', 'target_sha256', 'anchor_target_sha256', 'inner_nbytes', 'inner_sha256'}
    if type(header) is not dict or set(header) != required or header['family'] != FAMILY:
        raise ValueError('invalid fixed calibration schema')
    _digest(header['target_sha256'])
    _digest(header['anchor_target_sha256'])
    payload = data[16+n:]
    if (type(header['inner_nbytes']) is not int or header['inner_nbytes'] != len(payload)
            or _sha(payload) != _digest(header['inner_sha256'])):
        raise ValueError('fixed calibration payload differs from metadata')
    inner = decode_inner(payload, limits=limits)
    if inner.target_sha256 != header['anchor_target_sha256']:
        raise ValueError('fixed calibration anchor target differs')
    state = FixedAnchorState(header['target_sha256'], inner.target_sha256, inner.decoder_sha256,
                             inner.provider_sha256, inner.anchor_sha256, inner.stages, inner.anchors)
    if serialize(state) != data:
        raise ValueError('noncanonical fixed calibration state')
    return state


@dataclass(frozen=True)
class FixedAnchorResult:
    stages: tuple
    state: object
    diagnostics: dict


class FixedAnchorService:
    def __init__(self, decoder, base_target, *, solver_backend='native_ball', use_candidates=False, progress=None):
        if solver_backend not in ('native_ball', 'reference'):
            raise ValueError('point backend must be native_ball or reference')
        if type(use_candidates) is not bool:
            raise ValueError('use_candidates must be Boolean')
        self.decoder, self.base_target = decoder, base_target
        self.target = build_fixed_anchor_target(decoder, base_target)
        self.solver_backend, self.use_candidates, self.progress = solver_backend, use_candidates, progress

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
        metrics = dict(schema='fixed-anchor-service-v21', state_family=FAMILY, method=method,
            target_sha256=self.target.digest, anchor_target_sha256=self.base_target.digest,
            target_semantics='fixed anchor features; not sequential calibration',
            solver_backend=self.solver_backend, use_candidates=self.use_candidates,
            execution_route='prepared_leaf_construction' if prepared_anchors is not None else method,
            external_preparation_receipt=dict(preparation_receipt) if preparation_receipt is not None else None,
            external_preparation_elapsed_ns=preparation_receipt['elapsed_ns'] if preparation_receipt is not None else 0,
            preparation_receipt_verified_by_service=False,
            records=len(rows), retained_source_token_reads=sum(len(tokens) for _, tokens in rows),
            record_validation_elapsed_ns=time.perf_counter_ns()-start,
            context_elapsed_ns=0, prior_validation_elapsed_ns=0, anchor_preparation_elapsed_ns=0,
            anchor_prepared_records=0, anchor_reused_records=0, anchor_preparation_stage_record_pairs=0,
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
            if type(prior) is not FixedAnchorState:
                raise TypeError('fixed calibration repair requires FixedAnchorState')
            self._validate_model(prior)
            if prior.anchor_target_sha256 != self.base_target.digest:
                raise ValueError('prior anchor target differs')
            for key in ('decoder_sha256', 'provider_sha256', 'anchor_sha256'):
                if getattr(prior, key) != getattr(context, key):
                    raise ValueError('prior fixed anchor provenance differs')
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
            # Reuse the canonical leaf validation, never a falsely labelled model.
            envelope = AnchorState(self.base_target.digest, context.decoder_sha256,
                context.provider_sha256, context.anchor_sha256, context.anchor_codes, tuple(prepared_anchors))
            anchors = envelope.anchors
            if tuple((a.record_id, tuple(a.tokens)) for a in anchors) != tuple((rid, tuple(tokens)) for rid, tokens in rows):
                raise ValueError('prepared leaves differ from retained records')
            metrics['anchor_reused_records'] = len(anchors)
            metrics['prior_validation_elapsed_ns'] = time.perf_counter_ns()-tick
        elif stateful:
            tick = time.perf_counter_ns()
            anchors = tuple(prepare_anchor(self.decoder, self.base_target, dict(id=rid, tokens=tokens),
                                           context=context) for rid, tokens in rows)
            metrics['anchor_preparation_elapsed_ns'] = time.perf_counter_ns()-tick
            metrics['anchor_prepared_records'] = len(anchors)
            metrics['anchor_preparation_stage_record_pairs'] = len(anchors)*len(self.target.stages)
        metrics['stored_anchor_nodes'] = sum(len(a.nodes) for a in anchors)
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
            if self.solver_backend == 'native_ball':
                from .native_ball_quantizer import native_quantize_dyadic_rows, build_native_kernel
                quantized = native_quantize_dyadic_rows(weights, features, stage.scale_values,
                                                       candidate=candidate, **options)
                if metrics['native_build_manifest'] is None:
                    metrics['native_build_manifest'] = build_native_kernel()
            else:
                quantized = quantize_dyadic_rows(weights, features, stage.scale_values, **options)
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
        state = (FixedAnchorState(self.target.digest, self.base_target.digest, context.decoder_sha256,
            context.provider_sha256, context.anchor_sha256, tuple(outputs), anchors) if stateful else None)
        metrics['state_construct_elapsed_ns'] = time.perf_counter_ns()-tick
        metrics['service_elapsed_ns'] = time.perf_counter_ns()-start
        return FixedAnchorResult(tuple(outputs), state, metrics)
