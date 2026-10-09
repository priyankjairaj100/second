"""Lossless storage with explicit ordered preparation and bounded point solving.

The state format stays unchanged. The preparation identity changes truthfully.
Old preparation states are rejected, including after full deletion.
"""
from dataclasses import dataclass
import hashlib
import time

from .compact_service import _records
from .compact_state import _json, _name
from .ordered_fixed_service_v30 import OrderedFixedAnchorService, ordered_preparer_binding
from .adaptive_calibration_v30 import AdaptiveBudget
from .low_rank_certified import LowRankUnresolved
from .fixed_lossless_codec_v29 import codec_binding, MODE_NAMES
from .fixed_lossless_state_v29 import (
    FAMILY, STORAGE_SCHEMA, LosslessFactorState, decode_anchors, from_factor_state,
)


@dataclass(frozen=True)
class FixedLosslessResult:
    stages: tuple
    state: object
    diagnostics: dict


class OrderedLosslessService:
    def __init__(self, decoder, base_target, *, solver_backend='auto', progress=None,
                 coefficient_budget=AdaptiveBudget(), max_point_work_units=48_000_000_000):
        if progress is not None and not callable(progress):
            raise TypeError('progress must be callable or None')
        self.exact = OrderedFixedAnchorService(decoder, base_target, solver_backend=solver_backend,
            state_backend='factors', use_candidates=False, progress=progress,
            coefficient_budget=coefficient_budget, max_point_work_units=max_point_work_units)
        self.decoder, self.base_target, self.target = decoder, base_target, self.exact.target
        self.solver_backend = solver_backend

    @staticmethod
    def _deletions(deleted_ids):
        deleted = tuple(deleted_ids)
        if any(type(rid) is not str for rid in deleted) or len(set(deleted)) != len(deleted):
            raise ValueError('deletions must contain unique record IDs')
        for rid in deleted:
            _name(rid)
        return deleted

    def repair(self, prior, deleted_ids=()):
        if type(prior) is not LosslessFactorState:
            raise TypeError('lossless repair requires LosslessFactorState')
        deleted = self._deletions(deleted_ids)
        records = tuple(dict(id=a.record_id, tokens=a.tokens) for a in prior.anchors
                        if a.record_id not in set(deleted))
        return self.run(records, method='repair', prior=prior, deleted_ids=deleted)

    def indexed_fresh(self, prior, deleted_ids=()):
        if type(prior) is not LosslessFactorState:
            raise TypeError('lossless indexed reconstruction requires LosslessFactorState')
        deleted = self._deletions(deleted_ids)
        records = tuple(dict(id=a.record_id, tokens=a.tokens) for a in prior.anchors
                        if a.record_id not in set(deleted))
        return self.run(records, method='indexed_fresh', prior=prior, deleted_ids=deleted)

    def run(self, records, *, method='direct_fresh', prior=None, deleted_ids=()):
        start = time.perf_counter_ns()
        if method not in ('direct_fresh', 'repair', 'indexed_fresh', 'model_only_fresh'):
            raise ValueError('unknown lossless comparison method')
        rows = _records(self.decoder, records)
        admission_started = time.perf_counter_ns()
        point_admission = self.exact.admit_records(rows)
        admission_ns = time.perf_counter_ns()-admission_started
        for rid, _ in rows:
            _name(rid)
        deleted = self._deletions(deleted_ids)
        indexed = method in ('repair', 'indexed_fresh')
        if not indexed and (prior is not None or deleted):
            raise ValueError('fresh methods accept retained records without prior state or deletions')
        metrics = dict(schema='ordered-lossless-service-v30', method=method,
            decoder_implementation_manifest=self.decoder.implementation_manifest,
            preparer_sha256=ordered_preparer_binding(), early_point_admission=point_admission,
            early_admission_elapsed_ns=admission_ns,
            state_family=FAMILY, storage_schema=STORAGE_SCHEMA,
            target_sha256=self.target.digest, anchor_target_sha256=self.base_target.digest,
            target_semantics='fixed anchor features; not sequential calibration',
            solver_backend=self.solver_backend, model_seed_source='none',
            records=len(rows), retained_source_token_reads=sum(len(tokens) for _, tokens in rows),
            record_validation_elapsed_ns=time.perf_counter_ns()-start,
            prior_validation_elapsed_ns=0, lossless_decode_elapsed_ns=0,
            decode_receipt_elapsed_ns=0, exact_service_elapsed_ns=0,
            lossless_encode_elapsed_ns=0, state_assemble_elapsed_ns=0,
            decoded_descriptors=0, decoded_source_bytes=0, decoded_deleted_descriptors=0,
            decoded_payload_bytes=0, encoded_descriptors=0, encoded_source_bytes=0,
            reused_descriptors=0, reused_payload_bytes=0,
            original_feature_preparation_scope='external lifetime cost for indexed methods; not repeated or credited as request work',
            in_request_decode_scope='retained descriptors only; validation, decoding and receipt hashing are included',
            input_parser_decode_scope='external loading; canonical parsing decodes and recompresses all supplied descriptors, including deleted leaves',
            timing_scope='in-memory call; includes decoding and output-state assembly; excludes constructor, input parsing and serialized output')
        def exact_call(operation):
            tick = time.perf_counter_ns()
            try:
                return operation()
            except LowRankUnresolved as exc:
                nested = getattr(exc, 'service_diagnostics', getattr(exc, 'diagnostics', None))
                metrics.update(aborted=True, exact_service_diagnostics=nested,
                    exact_service_rejection=str(exc), service_elapsed_ns=time.perf_counter_ns()-start)
                exc.diagnostics = metrics
                raise
            finally:
                metrics['exact_service_elapsed_ns'] = time.perf_counter_ns()-tick

        record_dicts = tuple(dict(id=rid, tokens=tokens) for rid, tokens in rows)
        anchors = ()
        if indexed:
            tick = time.perf_counter_ns()
            if type(prior) is not LosslessFactorState:
                raise TypeError('lossless repair requires LosslessFactorState')
            self.exact._validate_model(prior)
            if prior.anchor_target_sha256 != self.base_target.digest:
                raise ValueError('prior anchor target differs')
            if prior.codec_sha256 != codec_binding():
                raise ValueError('prior lossless codec or compressor runtime binding differs')
            if prior.preparer_sha256 != ordered_preparer_binding():
                raise ValueError('prior fixed factor preparer binding differs')
            by_id = {a.record_id: a for a in prior.anchors}
            if not set(deleted) <= set(by_id) or {rid for rid, _ in rows} != set(by_id)-set(deleted):
                raise ValueError('retained membership differs from declared deletion')
            for rid, tokens in rows:
                if tuple(tokens) != by_id[rid].tokens:
                    raise ValueError('retained record contents changed')
            anchors = tuple(by_id[rid] for rid, _ in rows)
            metrics['prior_validation_elapsed_ns'] = time.perf_counter_ns()-tick
            tick = time.perf_counter_ns()
            decoded = decode_anchors(prior, tuple(rid for rid, _ in rows))
            metrics['lossless_decode_elapsed_ns'] = time.perf_counter_ns()-tick
            metrics['decoded_descriptors'] = sum(len(a.descriptors) for a in anchors)
            metrics['decoded_source_bytes'] = sum(len(b.binary64) for a in decoded for b in a.blocks)
            metrics['decoded_payload_bytes'] = sum(len(d.payload) for a in anchors for d in a.descriptors)
            tick = time.perf_counter_ns()
            # This is an actual, reproducible decoded-source manifest. It does
            # not pretend that a prior model was trained on a different corpus.
            manifest = dict(schema='lossless-decoded-source-manifest-v29',
                **{key: getattr(prior, key) for key in ('target_sha256', 'anchor_target_sha256',
                    'decoder_sha256', 'provider_sha256', 'anchor_sha256', 'preparer_sha256', 'codec_sha256')},
                records=[dict(record_id=a.record_id, tokens=list(a.tokens),
                    factors=[dict(stage_id=d.stage_id, shape=list(d.shape), source_sha256=d.source_sha256)
                             for d in a.descriptors]) for a in anchors])
            manifest_bytes = _json(manifest)
            receipt = dict(source='current-request retained lossless decode',
                artifact_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
                elapsed_ns=metrics['lossless_decode_elapsed_ns'])
            metrics['decode_receipt_elapsed_ns'] = time.perf_counter_ns()-tick
            metrics['decoded_source_manifest'] = manifest
            metrics['decoded_source_receipt'] = receipt
            tick = time.perf_counter_ns()
            exact = exact_call(lambda: self.exact.run_prepared(record_dicts, decoded, preparation_receipt=receipt))
        else:
            tick = time.perf_counter_ns()
            exact = exact_call(lambda: self.exact.run(record_dicts, method=method))
        metrics['exact_service_elapsed_ns'] = time.perf_counter_ns()-tick
        metrics['exact_service_diagnostics'] = exact.diagnostics
        metrics['neural_stage_record_pairs'] = (exact.diagnostics['neural_stage_record_pairs']
            + exact.diagnostics['anchor_preparation_stage_record_pairs'])
        metrics['total_possible_neural_stage_record_pairs'] = len(rows)*len(self.target.stages)
        metrics['avoided_neural_stage_record_pairs'] = (
            metrics['total_possible_neural_stage_record_pairs']-metrics['neural_stage_record_pairs'])
        for key in ('solver_elapsed_ns', 'weights_elapsed_ns', 'feature_elapsed_ns',
                    'context_elapsed_ns', 'context_matrix_values', 'code_pack_elapsed_ns',
                    'native_build_manifest', 'anchor_leaf_factor_reads', 'fixed_feature_values_read'):
            metrics[key] = exact.diagnostics[key]
        metrics['point_solver_stages'] = len(exact.stages)
        metrics['stages'] = exact.diagnostics['stages']
        if indexed:
            tick = time.perf_counter_ns()
            # Empty retained sets have no leaves for run_prepared's envelope
            # to compare. Check current bindings independently of membership.
            for key in ('decoder_sha256', 'provider_sha256', 'anchor_sha256'):
                if getattr(prior, key) != getattr(exact.state, key):
                    raise ValueError('prior fixed anchor provenance differs from current exact state')
            state = LosslessFactorState(*(getattr(prior, key) for key in ('target_sha256',
                'anchor_target_sha256', 'decoder_sha256', 'provider_sha256', 'anchor_sha256',
                'preparer_sha256', 'codec_sha256')), exact.stages, anchors)
            metrics['state_assemble_elapsed_ns'] = time.perf_counter_ns()-tick
            metrics['reused_descriptors'] = metrics['decoded_descriptors']
            metrics['reused_payload_bytes'] = metrics['decoded_payload_bytes']
        elif method == 'direct_fresh':
            tick = time.perf_counter_ns()
            state = from_factor_state(exact.state)
            metrics['lossless_encode_elapsed_ns'] = time.perf_counter_ns()-tick
            metrics['encoded_descriptors'] = sum(len(a.blocks) for a in exact.state.anchors)
            metrics['encoded_source_bytes'] = sum(len(b.binary64) for a in exact.state.anchors for b in a.blocks)
        else:
            state = None
        metrics['output_descriptor_modes'] = {name: sum(d.mode == mode for a in state.anchors
            for d in a.descriptors) if state is not None else 0 for mode, name in MODE_NAMES.items()}
        metrics['service_elapsed_ns'] = time.perf_counter_ns()-start
        return FixedLosslessResult(exact.stages, state, metrics)
