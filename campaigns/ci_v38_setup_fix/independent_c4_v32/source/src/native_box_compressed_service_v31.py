"""Bounded compressed repair with native universal box coefficients.

The mathematical target, codec, and point budgets remain unchanged.
Only ordered preparation states are accepted. Fallback shares ordered neural
execution with the exact and lossless controls, without global mutation.
"""
from dataclasses import asdict, replace
import hashlib
import time

import numpy as np

from .anchor_transformer import prepare_context
from .compact_service import _records
from .compact_state import StageCodes, _name
from .ordered_fixed_service_v30 import OrderedFixedAnchorService, ordered_preparer_binding
from .ordered_finite_decoder_v30 import OrderedFiniteDecoder, ordered_sequential_features
from .adaptive_calibration_v30 import (AdaptiveBudget, CalibrationWorkRefused,
    assess_routes, quantize_adaptive_dyadic_rows)
from .adaptive_compressed_service_v30 import (
    FixedCompressedResult, NeuralBudgetExceeded,
    assess_compressed_routes as _assess_shared_compressed_routes, _diagnostics,
)
from .fixed_compressed_state_v26 import (
    CompressedFactorState, FAMILY, STORAGE_SCHEMA, from_factor_state,
)
from .fixed_factor_codec_v26 import PRECISIONS, codec_binding
from .ordered_finite import FiniteWeights
from .sparse_box_certificate_v31 import SparseCertificateBudget, certify_sparse_ball_dyadic_box
from .primal_certificate_v30 import PrimalBudget, certify_primal_dyadic_box
from .token_box_certificate import TokenBoxUnresolved
from .low_rank_certified import LowRankUnresolved


def assess_compressed_routes(rows, width, tokens, *, bits=4,
        coefficient_budget=AdaptiveBudget(), sparse_budget=SparseCertificateBudget(),
        remaining_work=6_000_000_000, max_certificate_workspace_bytes=512 * 2**20):
    """Assess certificate arrays separately from the unchanged point budget.

The coefficient work ceiling still applies. Sparse checks also retain their
own workspace ceiling. This is an engineering allowance, not process RSS.
"""
    if type(coefficient_budget) is not AdaptiveBudget:
        raise TypeError('coefficient_budget must be AdaptiveBudget')
    if type(max_certificate_workspace_bytes) is not int or max_certificate_workspace_bytes < 1:
        raise ValueError('max_certificate_workspace_bytes must be a positive built-in integer')
    certificate_budget = replace(coefficient_budget, max_workspace_bytes=max_certificate_workspace_bytes)
    report = _assess_shared_compressed_routes(rows, width, tokens, bits=bits,
        coefficient_budget=certificate_budget, sparse_budget=sparse_budget, remaining_work=remaining_work)
    return dict(report, max_certificate_workspace_bytes=max_certificate_workspace_bytes,
        point_max_workspace_bytes=coefficient_budget.max_workspace_bytes,
        workspace_scope='independent certificate array allowance; point budget remains unchanged')


class NativeBoxCompressedService:
    def __init__(self, decoder, base_target, *, bits=48, block_size=256,
                 solver_backend='auto', certificate_backend='auto',
                 max_neural_stage_record_pairs=None, progress=None,
                 coefficient_budget=AdaptiveBudget(), sparse_budget=SparseCertificateBudget(),
                 max_certificate_work_units=6_000_000_000,
                 max_certificate_workspace_bytes=512 * 2**20,
                 max_point_work_units=48_000_000_000):
        if type(decoder) is not OrderedFiniteDecoder:
            raise TypeError('ordered compressed service requires OrderedFiniteDecoder')
        if type(bits) is not int or bits not in PRECISIONS:
            raise ValueError('codec precision must be sixteen, twenty-four, thirty-two, forty, or forty-eight bits')
        if type(block_size) is not int or not 1 <= block_size <= 4096:
            raise ValueError('codec block size must be between one and 4096')
        if certificate_backend not in ('auto', 'sparse', 'primal'):
            raise ValueError('certificate backend must be auto, sparse, or primal')
        if solver_backend not in ('auto', 'token', 'primal'):
            raise ValueError('point backend must be auto, token, or primal')
        if type(coefficient_budget) is not AdaptiveBudget or type(sparse_budget) is not SparseCertificateBudget:
            raise TypeError('coefficient_budget and sparse_budget must have their declared budget types')
        if type(max_certificate_workspace_bytes) is not int or max_certificate_workspace_bytes < 1:
            raise ValueError('max_certificate_workspace_bytes must be a positive built-in integer')
        for name, value in (('max_certificate_work_units', max_certificate_work_units),
                            ('max_point_work_units', max_point_work_units)):
            if type(value) is not int or value < 0:
                raise ValueError(name+' must be a nonnegative built-in integer')
        self.coefficient_budget, self.sparse_budget = coefficient_budget, sparse_budget
        self.max_certificate_work_units = max_certificate_work_units
        self.max_certificate_workspace_bytes = max_certificate_workspace_bytes
        self.max_point_work_units = max_point_work_units
        if (max_neural_stage_record_pairs is not None
                and (type(max_neural_stage_record_pairs) is not int
                     or max_neural_stage_record_pairs < 0)):
            raise ValueError('neural budget must be a nonnegative built-in integer or None')
        if progress is not None and not callable(progress):
            raise TypeError('progress must be callable or None')
        self.exact = OrderedFixedAnchorService(decoder, base_target,
            solver_backend=solver_backend, state_backend='factors', coefficient_budget=coefficient_budget,
            max_point_work_units=max_point_work_units)
        self.decoder, self.base_target, self.target = decoder, base_target, self.exact.target
        if any(stage.bits != 4 for stage in self.target.stages):
            raise ValueError('the adaptive point policy currently requires four-bit model grids')
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
        metrics = dict(schema='native-box-compressed-service-v31', method=method,
            decoder_implementation_manifest=self.decoder.implementation_manifest,
            preparer_sha256=ordered_preparer_binding(),
            state_family=FAMILY, storage_schema=STORAGE_SCHEMA,
            target_sha256=self.target.digest, anchor_target_sha256=self.base_target.digest,
            target_semantics='fixed anchor features; not sequential calibration',
            solver_backend=self.solver_backend, certificate_backend=self.certificate_backend,
            bits=self.bits, block_size=self.block_size,
            coefficient_budget=asdict(self.coefficient_budget), sparse_budget=asdict(self.sparse_budget),
            max_certificate_work_units=self.max_certificate_work_units,
            max_certificate_workspace_bytes=self.max_certificate_workspace_bytes,
            max_point_work_units=self.max_point_work_units,
            certificate_work_units_reserved=0, point_work_units_reserved=0,
            coefficient_reservations=[], certificate_admission_refused_stages=0,
            resource_scope='structural work ceilings and engineering array allowances; not CPU time or process RSS',
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
            point_solver_stages=0, point_solver_attempted_stages=0, singleton_point_stages=0,
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

        def refuse(message, admission):
            metrics['service_elapsed_ns'] = time.perf_counter_ns()-start
            metrics['aborted'] = True
            if metrics['pending_stage'] is not None:
                metrics['pending_stage']['elapsed_ns'] = time.perf_counter_ns()-pending_stage_start_ns
            error = CalibrationWorkRefused(message, admission)
            error.diagnostics = metrics
            raise error

        def reserve_units(kind, stage_id, route, units):
            used_key = kind+'_work_units_reserved'
            limit = getattr(self, 'max_'+kind+'_work_units')
            if type(units) is not int or units < 0:
                raise ArithmeticError('invalid service work reservation')
            if metrics[used_key]+units > limit:
                refuse(kind+' work exceeds the cumulative request budget',
                       dict(kind=kind, stage_id=stage_id, route=route, required_units=units,
                            used_units=metrics[used_key], limit_units=limit))
            metrics[used_key] += units
            metrics['coefficient_reservations'].append(
                dict(kind=kind, stage_id=stage_id, route=route, work_units=units))

        def reserve_point(stage):
            report = assess_routes(len(stage.weights), stage.width,
                metrics['retained_source_token_reads'], budget=self.coefficient_budget)
            selected = report['selected'] if self.solver_backend == 'auto' else self.solver_backend
            if selected is None or not report['routes'][selected]['admitted']:
                refuse('point route exceeds the declared stage resource policy', report)
            report = dict(report, selected=selected)
            reserve_units('point', stage.stage_id, selected, report['routes'][selected]['work_units'])
            return report

        if method == 'direct_fresh':
            # Exact preparation executes every source-stage pair. Reject early
            # when its known complete cost exceeds the supplied work budget.
            budget_check(metrics['total_possible_neural_stage_record_pairs'])
            tick = time.perf_counter_ns()
            # Preflight every point stage before exact preparation reads any retained feature.
            for stage in self.target.stages:
                reserve_point(stage)
            try:
                exact = OrderedFixedAnchorService(self.decoder, self.base_target,
                    solver_backend=self.solver_backend, state_backend='factors', progress=self.progress,
                    coefficient_budget=self.coefficient_budget,
                    max_point_work_units=self.max_point_work_units).run(
                        tuple(dict(id=rid, tokens=tokens) for rid, tokens in rows))
            except LowRankUnresolved as exc:
                nested = getattr(exc, 'service_diagnostics', getattr(exc, 'diagnostics', None))
                metrics['aborted'] = True
                metrics['exact_preparation_rejection'] = str(exc)
                metrics['exact_service_diagnostics'] = nested
                metrics['service_elapsed_ns'] = time.perf_counter_ns()-start
                # Missing nested receipts remain unknown. They never become zero observed work.
                metrics['neural_stage_record_pairs'] = None
                metrics['neural_stage_record_pairs_by_source'] = {rid: None for rid, _ in rows}
                metrics['point_solver_stages'] = None
                metrics['point_solver_attempted_stages'] = None
                metrics['point_solver_elapsed_ns'] = None
                if type(nested) is dict:
                    prepared = nested.get('anchor_preparation_stage_record_pairs')
                    if type(prepared) is int and prepared >= 0:
                        metrics['neural_stage_record_pairs'] = prepared
                        if prepared == metrics['total_possible_neural_stage_record_pairs']:
                            metrics['neural_stage_record_pairs_by_source'] = {
                                rid: len(self.target.stages) for rid, _ in rows}
                    completed = nested.get('stages')
                    if type(completed) is list:
                        metrics['point_solver_stages'] = len(completed)
                        metrics['point_solver_attempted_stages'] = (
                            len(completed)+int('unresolved_stage_id' in nested))
                    solver_ns, failed_ns = nested.get('solver_elapsed_ns'), nested.get('failed_solver_elapsed_ns')
                    if type(solver_ns) is int and type(failed_ns) is int:
                        metrics['point_solver_elapsed_ns'] = solver_ns+failed_ns
                exc.diagnostics = metrics
                raise
            finally:
                metrics['exact_preparation_elapsed_ns'] = time.perf_counter_ns()-tick
            metrics['exact_service_diagnostics'] = exact.diagnostics
            metrics['neural_stage_record_pairs'] = exact.diagnostics['anchor_preparation_stage_record_pairs']
            metrics['neural_stage_record_pairs_by_source'] = {rid: len(self.target.stages) for rid, _ in rows}
            metrics['point_solver_stages'] = len(exact.stages)
            metrics['point_solver_attempted_stages'] = len(exact.stages)
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
        if prior.preparer_sha256 != ordered_preparer_binding():
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
                    streams[anchor.record_id] = ordered_sequential_features(self.decoder, anchor.tokens)
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

        def point_solve(weights, features, stage, options, admission):
            tick = time.perf_counter_ns()
            metrics['point_solver_attempted_stages'] += 1
            try:
                quantized = quantize_adaptive_dyadic_rows(weights, features, stage.scale_values,
                    route=admission['selected'], budget=self.coefficient_budget, **options)
            except LowRankUnresolved as exc:
                metrics['aborted'] = True
                metrics['service_elapsed_ns'] = time.perf_counter_ns()-start
                metrics['pending_stage']['point_rejection'] = str(exc)
                metrics['pending_stage']['point_failure_diagnostics'] = getattr(exc, 'diagnostics', None)
                metrics['pending_stage']['elapsed_ns'] = time.perf_counter_ns()-pending_stage_start_ns
                exc.diagnostics = metrics
                raise
            finally:
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
            # Resource plans use public dimensions before descriptor decoding or matrix assembly.
            certificate_plan = assess_compressed_routes(len(stage.weights), stage.width,
                metrics['retained_source_token_reads'], bits=stage.bits,
                coefficient_budget=self.coefficient_budget, sparse_budget=self.sparse_budget,
                remaining_work=self.max_certificate_work_units-metrics['certificate_work_units_reserved'],
                max_certificate_workspace_bytes=self.max_certificate_workspace_bytes)
            selected_certificate = (certificate_plan['selected'] if self.certificate_backend == 'auto'
                                    else self.certificate_backend)
            if (selected_certificate is not None
                    and not certificate_plan['routes'][selected_certificate]['admitted']):
                selected_certificate = None
            metrics['pending_stage']['certificate_admission'] = certificate_plan
            assembly_bytes = 8*(12*stage.width*metrics['retained_source_token_reads']
                                +4*len(stage.weights)*stage.width)
            if assembly_bytes > self.max_certificate_workspace_bytes:
                refuse('stage box assembly exceeds the declared array allowance',
                       dict(stage_id=stage.stage_id, assembly_array_bytes=assembly_bytes,
                            max_workspace_bytes=self.max_certificate_workspace_bytes,
                            workspace_policy='certificate'))
            # If no certificate route can start, reject before decoding when fallback is also impossible.
            early_point_plan = reserve_point(stage) if selected_certificate is None else None
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
                point_plan = early_point_plan if early_point_plan is not None else reserve_point(stage)
                quantized = point_solve(weights, lower, stage, options, point_plan)
                metrics['singleton_point_stages'] += 1
            else:
                if selected_certificate is None:
                    rejection = 'no certificate route admitted under the declared resource policy'
                    failure_diagnostics = {'admission': certificate_plan}
                    metrics['certificate_admission_refused_stages'] += 1
                else:
                    route_plan = certificate_plan['routes'][selected_certificate]
                    reserve_units('certificate', stage.stage_id, selected_certificate,
                                  route_plan['work_units_reserved'])
                    tick = time.perf_counter_ns()
                    metrics['certificate_attempted_stages'] += 1
                    try:
                        if selected_certificate == 'sparse':
                            bounded = replace(self.sparse_budget,
                                max_work_units=route_plan['work_units_reserved'],
                                max_workspace_bytes=min(self.sparse_budget.max_workspace_bytes,
                                                        self.max_certificate_workspace_bytes))
                            quantized = certify_sparse_ball_dyadic_box(weights, lower, upper,
                                stage.scale_values, budget=bounded, **options)
                        else:
                            bounded = PrimalBudget(max_work_units=route_plan['work_units_reserved'],
                                max_workspace_bytes=self.max_certificate_workspace_bytes)
                            quantized = certify_primal_dyadic_box(weights, lower, upper,
                                stage.scale_values, bits=stage.bits, ridge=stage.ridge,
                                normalization=stage.normalization, budget=bounded)
                    except TokenBoxUnresolved as exc:
                        rejection = str(exc)
                        failure_diagnostics = {key: getattr(exc, key)
                            for key in ('native_diagnostics', 'ball_diagnostics', 'admission') if hasattr(exc, key)}
                    finally:
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
                # Admit and reserve point work before the first fallback neural traversal.
                point_plan = early_point_plan if early_point_plan is not None else reserve_point(stage)
                blocks = [replay(anchor, i, box) for anchor, box in zip(anchors, boxes)]
                tick = time.perf_counter_ns()
                features = (np.concatenate(blocks, axis=0).T.copy() if blocks
                            else np.empty((stage.width, 0), dtype=np.float64))
                metrics['fallback_feature_assembly_elapsed_ns'] += time.perf_counter_ns()-tick
                quantized = point_solve(weights, features, stage, options, point_plan)
            tick = time.perf_counter_ns()
            outputs.append(StageCodes.from_array(stage.stage_id, quantized.codes,
                grid_axis='dyadic_row', bits=stage.bits, scale_values=stage.scale_values))
            metrics['code_pack_elapsed_ns'] += time.perf_counter_ns()-tick
            diag = dict(stage_id=stage.stage_id, certificate_accepted=None if singleton else accepted,
                certificate_backend=self.certificate_backend, certificate_route=selected_certificate,
                certificate_admission=certificate_plan, singleton_box=singleton,
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
