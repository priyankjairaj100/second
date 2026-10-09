"""Explicit native/reference coefficient selection for bounded sparse certificates.

The universal row verifier and requested-coordinate refinement retain V30's
arithmetic and budgets. Only the initial coefficient builder is selectable.
No global function replacement or caller-supplied evidence enables this path.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import hashlib
from pathlib import Path
import time

import numpy as np

from . import ball_box_certificate_v28 as previous
from . import native_ball_quantizer as ball
from . import native_box_certificate as interval
from . import preconditioned_box_certificate as preconditioned
from . import token_box_certificate as boxes
from .ball_box_certificate_v27 import _feature_uncertainty_bounds, _augmented_underflow_bounds
from .dyadic_row_quantizer import dyadic_row_scales, _grid_arrays
from .exact_core import _rational
from .low_rank_certified import LowRankUnresolved, _finite
from .row_scaled_quantizer import _bits
from .token_box_certificate import TokenBoxUnresolved, _finish, _matrix
from .transformer_backend import _check_runtime
from .native_box_coefficients_v31 import NativeBoxCoefficientBudget, native_box_coefficient_enclosures
from .sparse_box_certificate_v30 import (
    SparseCertificateBudget, SparseBoxResult as ReferenceSparseBoxResult,
    _shape, _workspace_allowance, _reserve, _requested_components, _current_failures,
)


@dataclass(frozen=True)
class SparseBoxResult(ReferenceSparseBoxResult):
    backend: str = 'native_ball_budgeted_sparse_box_v31'
    coefficient_backend: str = 'native'
    coefficient_evidence: object = None


def certify_sparse_ball_dyadic_box(
        weights, lower, upper, scale_values=None, *, bits=4,
        significant_bits=24, ridge, normalization=1, candidate_codes=None,
        max_exact_rank=64, max_exact_coordinates=16, max_refinement_coordinates=16,
        allow_python_fallback=False, budget=None, coefficient_backend='native'):
    """Certify all rows or refuse under explicit numerical work limits.

The target, tie rule, and canonical scales equal V28. Positive-width boxes never
use a point solver. Singleton inputs also use this bounded certificate path.
Legacy exact limits are validated for API compatibility, but trigger no fallback.
Callers must keep inputs unchanged. No external coefficient evidence is trusted.
"""
    started = time.perf_counter_ns()
    if type(coefficient_backend) is not str or coefficient_backend not in ('native', 'reference'):
        raise ValueError('coefficient backend must be native or reference')
    if budget is None:
        budget = SparseCertificateBudget()
    if type(budget) is not SparseCertificateBudget:
        raise TypeError('budget must be a SparseCertificateBudget')
    if type(allow_python_fallback) is not bool:
        raise ValueError('allow_python_fallback must be a built-in bool')
    if allow_python_fallback:
        raise ValueError('unbudgeted Python fallback is unavailable in this backend')
    diagnostics = {
        'passes': [], 'resource_reservations': [], 'work_units_reserved': 0,
        'coefficient_backend': coefficient_backend, 'coefficient_evidence': None,
        'resource_budget': asdict(budget), 'compile_elapsed_ns': 0,
        'fallback_elapsed_ns': 0, 'preconditioner_rounds': 0,
        'requested_coordinates': [], 'verified_coordinates': [],
        'unresolved_coordinate_rounds': [], 'coefficient_suffix_coordinates_visited': 0,
        'coefficient_policy': 'ridge_then_requested_coordinate_preconditioners',
        'work_scope': 'declared structural proxies, not FLOPs or elapsed time',
        'workspace_scope': 'dense-array engineering allowance, not total process RSS',
    }
    for name, value in (('weights', weights), ('lower', lower), ('upper', upper)):
        _shape(value, name)
    rows, width = weights.shape
    tokens = lower.shape[1]
    if not rows or not width or lower.shape != upper.shape or lower.shape[0] != width:
        raise ValueError('nonempty weights and matching feature box dimensions are required')
    if max(width, tokens) > 2**20:
        raise ValueError('native ball proof requires width and tokens at most 2**20')
    if candidate_codes is not None:
        _shape(candidate_codes, 'candidate_codes')
        if candidate_codes.shape != weights.shape:
            raise ValueError('candidate dimensions differ from weights')
    grid_size = 2 * _bits(bits)
    for value in (max_exact_rank, max_exact_coordinates, max_refinement_coordinates):
        if type(value) is not int or value < 0:
            raise ValueError('fallback limits must be nonnegative built-in integers')
    try:
        allowance = _workspace_allowance(rows, width, tokens, grid_size,
                                         min(width, budget.max_preconditioned_coordinates))
        diagnostics['workspace_array_allowance_bytes'] = allowance
        if allowance > budget.max_workspace_bytes:
            diagnostics['resource_refusal'] = {
                'reason': 'workspace_allowance', 'required_bytes': allowance,
                'limit_bytes': budget.max_workspace_bytes,
            }
            raise TokenBoxUnresolved('workspace allowance exceeds budget; no numerical arrays allocated')
        # Charge validation, grids, feature bounds, coefficient construction, and ball rows first.
        _reserve(diagnostics, budget, 'initial_ball_and_ridge',
                 width*tokens**2 + rows*width*(2*tokens+bits+1)
                 + width*tokens + rows*grid_size)
        _check_runtime()
        for name, value in (('weights', weights), ('lower', lower), ('upper', upper)):
            _matrix(value, name)
        if np.any(lower > upper):
            raise ValueError('reversed feature box')
        if candidate_codes is not None:
            _matrix(candidate_codes, 'candidate_codes')
        lam, norm = _rational(ridge, 'ridge'), _rational(normalization, 'normalization')
        if lam <= 0 or norm <= 0:
            raise ValueError('ridge and normalization must be positive')
        scales = dyadic_row_scales(weights, bits, significant_bits)
        if scale_values is not None:
            supplied = tuple(scale_values)
            if any(type(s) is not float for s in supplied) or supplied != scales:
                raise ValueError('scales must equal the canonical base-only dyadic scales')
        tiny = np.float64(np.finfo(np.float64).smallest_subnormal)
        if tiny == 0 or tiny*np.float64(1.) != tiny or np.float64(2.)*tiny != tiny+tiny:
            raise TokenBoxUnresolved('gradual-underflow runtime check failed')
        uncertain = int(np.count_nonzero(lower != upper))
        wrapper_digest = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        build = ball.prepare_native_ball()
        diagnostics.update(builds={'ball': build}, compile_elapsed_ns=build['call_compile_elapsed_ns'])
        tick = time.perf_counter_ns()
        grid, boundaries = _grid_arrays(scales, bits)
        center, radius, feature_error, _ = _feature_uncertainty_bounds(weights, lower, upper, grid)
        feature_ns = time.perf_counter_ns()-tick
        diagnostics.update(feature_bounds_elapsed_ns=feature_ns,
            max_feature_radius=float(np.max(radius)) if radius.size else 0.,
            max_feature_accumulator_error=float(np.max(feature_error)))
        tick = time.perf_counter_ns()
        coefficient_evidence = None
        try:
            with np.errstate(over='ignore', invalid='ignore', under='ignore', divide='ignore'):
                if coefficient_backend == 'native':
                    coefficient_evidence = native_box_coefficient_enclosures(lower, upper, lam*norm,
                        budget=NativeBoxCoefficientBudget(max_work_units=budget.max_work_units,
                            max_workspace_bytes=budget.max_workspace_bytes))
                    proposal, errors = coefficient_evidence.coefficients, coefficient_evidence.errors
                    metadata = {field.name:getattr(coefficient_evidence, field.name)
                        for field in fields(coefficient_evidence) if field.name not in ('coefficients', 'errors')}
                    diagnostics['coefficient_evidence'] = metadata
                    diagnostics['compile_elapsed_ns'] += coefficient_evidence.compile_elapsed_ns
                else:
                    proposal, errors = boxes._box_coefficients(lower, upper, lam*norm)
                _finite(proposal, errors)
                # Immutable byte-backed evidence need not promise C alignment.
                # Keep the wrapper contract explicit before all legacy row paths.
                proposal = np.require(proposal, dtype=np.float64, requirements=['C', 'A'])
                rho = ball._coefficient_radii(errors)
        finally:
            coefficient_ns = time.perf_counter_ns()-tick
            diagnostics['coefficient_elapsed_ns'] = coefficient_ns
        tick = time.perf_counter_ns()
        umax, proposal_l1 = _augmented_underflow_bounds(center, proposal, feature_error)
        bounds_ns = time.perf_counter_ns()-tick
        diagnostics['ball_bounds_elapsed_ns'] = bounds_ns
        codes, failed, receipt = previous._ball_pass(
            weights, center, proposal, rho, umax, proposal_l1, grid, boundaries)
        diagnostics['passes'].append(receipt)
        if receipt['status']:
            raise TokenBoxUnresolved('native ball runtime or allocation failure; no codes committed')
        selected = np.flatnonzero(failed >= 0)
        first_rows = rows-len(selected)
        ridge_rows = stronger_rows = 0
        interval_build = None
        interval_bounds_ns = 0
        evidence_cache = {}
        checked = set()
        if len(selected):
            _reserve(diagnostics, budget, 'shared_ridge_rows',
                     len(selected)*width*(2*tokens+bits+1))
            interval_build = interval.prepare_native_box()
            diagnostics['builds']['interval'] = interval_build
            diagnostics['compile_elapsed_ns'] += interval_build['call_compile_elapsed_ns']
            tick = time.perf_counter_ns()
            component = np.broadcast_to(rho[:, None], lower.shape).copy()
            valid = np.ones(width, dtype=bool)
            interval_bounds_ns = time.perf_counter_ns()-tick
            diagnostics['interval_bounds_elapsed_ns'] = interval_bounds_ns
            count = len(selected)
            pass_start = len(diagnostics['passes'])
            selected = previous._interval_rows(weights, lower, upper, proposal, component, valid,
                grid, boundaries, selected, codes, diagnostics, 'shared_ridge')
            ridge_rows = count-len(selected)
            current_passes = diagnostics['passes'][pass_start:]
        while len(selected):
            failures = _current_failures(current_passes, selected, width)
            diagnostics['unresolved_coordinate_rounds'].append(tuple(sorted(failures.items())))
            pending = sorted(set(failures.values())-checked)
            if not pending:
                raise TokenBoxUnresolved('requested-coordinate evidence cannot resolve remaining rows')
            if diagnostics['preconditioner_rounds'] >= budget.max_rounds:
                diagnostics['resource_refusal'] = {'reason': 'round_limit', 'pending_coordinates': pending}
                raise TokenBoxUnresolved('preconditioner round budget exhausted')
            if len(checked)+len(pending) > budget.max_preconditioned_coordinates:
                diagnostics['resource_refusal'] = {'reason': 'coordinate_limit', 'pending_coordinates': pending}
                raise TokenBoxUnresolved('preconditioner coordinate budget exhausted')
            sweep_coordinates = width-min(pending)
            _reserve(diagnostics, budget, 'requested_preconditioner_sweep',
                     sweep_coordinates*tokens**2 + len(pending)*tokens**3)
            # Reserve the entire retry before the expensive coefficient construction.
            _reserve(diagnostics, budget, 'mixed_component_rows',
                     len(selected)*width*(2*tokens+bits+1))
            checked.update(pending)
            diagnostics['requested_coordinates'] = sorted(checked)
            diagnostics['preconditioner_rounds'] += 1
            tick = time.perf_counter_ns()
            with np.errstate(over='ignore', invalid='ignore', under='ignore', divide='ignore'):
                evidence, visited = _requested_components(lower, upper, lam*norm, proposal, pending)
            coefficient_ns += time.perf_counter_ns()-tick
            diagnostics['coefficient_elapsed_ns'] = coefficient_ns
            diagnostics['coefficient_suffix_coordinates_visited'] += visited
            for i, certificate in evidence.items():
                if certificate.coordinate != i or not np.array_equal(certificate.proposal, proposal[i]):
                    raise ArithmeticError('coefficient evidence changed its checked proposal')
                evidence_cache[i] = certificate
                # Both enclosures center on the same proposal. Their intersection is valid.
                component[i] = np.minimum(component[i], certificate.radius)
            diagnostics['verified_coordinates'] = sorted(evidence_cache)
            count = len(selected)
            pass_start = len(diagnostics['passes'])
            selected = previous._interval_rows(weights, lower, upper, proposal, component, valid,
                grid, boundaries, selected, codes, diagnostics, 'mixed_requested_preconditioners')
            stronger_rows += count-len(selected)
            current_passes = diagnostics['passes'][pass_start:]
        base = preconditioned._result(_finish(codes, weights.size, 0, uncertain,
            float(np.max(errors)), candidate_codes), len(evidence_cache), len(checked)-len(evidence_cache), 0)
        passes = diagnostics['passes']
        return SparseBoxResult(**base.__dict__,
            coefficient_backend=coefficient_backend,
            coefficient_evidence=diagnostics['coefficient_evidence'],
            native_attempted_decisions=sum(p['attempted_decisions'] for p in passes),
            native_certified_decisions=sum(p['certified_decisions'] for p in passes),
            first_ball_certified_rows=first_rows, ridge_interval_certified_rows=ridge_rows,
            preconditioned_interval_certified_rows=stronger_rows,
            feature_bounds_elapsed_ns=feature_ns, coefficient_elapsed_ns=coefficient_ns,
            ball_bounds_elapsed_ns=bounds_ns, interval_bounds_elapsed_ns=interval_bounds_ns,
            native_elapsed_ns=sum(p['native_elapsed_ns'] for p in passes),
            compile_elapsed_ns=diagnostics['compile_elapsed_ns'], total_elapsed_ns=time.perf_counter_ns()-started,
            max_feature_radius=diagnostics['max_feature_radius'],
            max_feature_accumulator_error=diagnostics['max_feature_accumulator_error'],
            native_source_sha256=build['source_sha256'], native_binary_sha256=build['binary_sha256'],
            native_compiler=build['compiler_version'], wrapper_source_sha256=wrapper_digest,
            interval_source_sha256=interval_build['source_sha256'] if interval_build else '',
            interval_binary_sha256=interval_build['binary_sha256'] if interval_build else '',
            native_passes=tuple(dict(p) for p in passes),
            preconditioner_requested_coordinates=tuple(sorted(checked)),
            preconditioner_verified_coordinates=tuple(sorted(evidence_cache)),
            preconditioner_rounds=diagnostics['preconditioner_rounds'],
            coefficient_suffix_coordinates_visited=diagnostics['coefficient_suffix_coordinates_visited'],
            work_units_reserved=diagnostics['work_units_reserved'],
            workspace_array_allowance_bytes=allowance, resource_budget=tuple(asdict(budget).items()),
            resource_reservations=tuple(diagnostics['resource_reservations']),
            unresolved_coordinate_rounds=tuple(diagnostics['unresolved_coordinate_rounds']))
    except (TokenBoxUnresolved, LowRankUnresolved) as exc:
        for name in ('coefficient_admission', 'coefficient_diagnostics'):
            if hasattr(exc, name):
                diagnostics[name] = getattr(exc, name)
        if diagnostics.get('coefficient_evidence') is None and hasattr(exc, 'coefficient_diagnostics'):
            diagnostics['compile_elapsed_ns'] += exc.coefficient_diagnostics.get('compile_elapsed_ns', 0)
        failure = exc if isinstance(exc, TokenBoxUnresolved) else TokenBoxUnresolved(str(exc))
        diagnostics['total_elapsed_ns'] = time.perf_counter_ns()-started
        failure.native_diagnostics = diagnostics
        if failure is exc:
            raise
        raise failure from exc


# Explicit alias supports a local backend map without modifying historical code.
certify_ball_dyadic_box = certify_sparse_ball_dyadic_box
