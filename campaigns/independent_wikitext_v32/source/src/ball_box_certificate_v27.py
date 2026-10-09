"""Universal feature-box certificates using the unchanged native ball kernel.

Feature uncertainty augments the proved accumulator bound. All coefficients
are certified for the entire box. Uncertain boxes never use point fallback.
"""
from __future__ import annotations

import ctypes
from dataclasses import dataclass
import hashlib
from pathlib import Path
import time

import numpy as np

from . import native_ball_quantizer as ball
from . import preconditioned_box_certificate as preconditioned
from . import token_box_certificate as boxes
from .dyadic_row_quantizer import dyadic_row_scales, _grid_arrays
from .exact_core import _rational
from .low_rank_certified import LowRankUnresolved, _add, _finite, _norm_squared_upper, _up
from .token_box_certificate import TokenBoxUnresolved, _finish, _matrix
from .transformer_backend import _check_runtime


def _feature_uncertainty_bounds(weights, lower, upper, grid):
    """Return center, entry radii, uniform prefix errors, and code discrepancies.

D[h] covers |w[row,h]-q| for every row and every code in that row's grid.
E[i,k] covers sum_{h<i} D[h]*R[h,k]. The returned prefix is max_k E[i,k].
Every bound encloses exact real arithmetic on the supplied binary64 values.
"""
    with np.errstate(over='ignore', invalid='ignore', under='ignore'):
        center = np.minimum(upper, np.maximum(lower, lower / 2.0 + upper / 2.0))
        radius = np.where(lower == upper, 0.0,
                          _up(np.maximum(center - lower, upper - center)))
        dlo, dhi = _add(weights, weights, -grid[:, :1], -grid[:, :1])
        elo, ehi = _add(weights, weights, -grid[:, -1:], -grid[:, -1:])
        discrepancy = np.max(np.maximum.reduce((np.abs(dlo), np.abs(dhi),
                                                 np.abs(elo), np.abs(ehi))), axis=0)
        _finite(center, radius, discrepancy)
        prefix = np.zeros(lower.shape[1], dtype=np.float64)
        uniform = np.zeros(lower.shape[0], dtype=np.float64)
        for i in range(lower.shape[0]):
            uniform[i] = np.max(prefix) if len(prefix) else 0.0
            term = np.where((discrepancy[i] == 0) | (radius[i] == 0),
                            0.0, _up(discrepancy[i] * radius[i]))
            prefix = np.where(term == 0, prefix, _up(prefix + term))
            _finite(prefix)
    return center, radius, uniform, discrepancy


def _augmented_underflow_bounds(center, proposal, feature_error):
    """Raise the existing uniform accumulator bound by proven feature error."""
    with np.errstate(over='ignore', invalid='ignore', under='ignore'):
        original, proposal_l1 = ball._underflow_bounds(center, proposal)
        augmented = np.where(feature_error == 0, original, _up(original + feature_error))
    _finite(augmented, proposal_l1)
    return augmented, proposal_l1


def _native_pass(weights, center, proposal, rho, umax, proposal_l1, grid, boundaries):
    # A contiguous NumPy array can still have an unaligned buffer offset.
    arrays = [np.require(x, dtype=np.float64, requirements=['C', 'A']) for x in
              (weights, center, proposal, rho, umax, proposal_l1, grid, boundaries)]
    codes = np.empty(weights.shape, dtype=np.float64)
    failed = np.full(len(weights), -1, dtype=np.int64)
    counts = np.zeros(4, dtype=np.uint64)
    ptr = ctypes.POINTER(ctypes.c_double)
    tick = time.perf_counter_ns()
    status = ball._NATIVE.nb_run(len(weights), weights.shape[1], center.shape[1], grid.shape[1],
        *(x.ctypes.data_as(ptr) for x in arrays), None, codes.ctypes.data_as(ptr),
        failed.ctypes.data_as(ctypes.POINTER(ctypes.c_int64)),
        counts.ctypes.data_as(ctypes.POINTER(ctypes.c_uint64)))
    elapsed = time.perf_counter_ns() - tick
    selected = np.flatnonzero(failed >= 0)
    receipt = {
        'native_elapsed_ns': elapsed, 'status': int(status),
        'failed_rows': int(len(selected)),
        'first_unresolved_row': int(selected[0]) if len(selected) else -1,
        'first_unresolved_coordinate': int(failed[selected[0]]) if len(selected) else -1,
        'attempted_decisions': int(counts[2]), 'certified_decisions': int(counts[3]),
    }
    return codes, receipt


@dataclass(frozen=True)
class BallBoxResult(preconditioned.PreconditionedBoxResult):
    backend: str = 'native_ball_universal_box'
    coefficient_policy: str = 'ridge_then_preconditioned'
    native_attempted_decisions: int = 0
    native_certified_decisions: int = 0
    python_universal_fallback: bool = False
    feature_bounds_elapsed_ns: int = 0
    coefficient_elapsed_ns: int = 0
    ball_bounds_elapsed_ns: int = 0
    native_elapsed_ns: int = 0
    fallback_elapsed_ns: int = 0
    compile_elapsed_ns: int = 0
    total_elapsed_ns: int = 0
    max_feature_radius: float = 0.0
    max_feature_accumulator_error: float = 0.0
    native_source_sha256: str = ''
    native_binary_sha256: str = ''
    native_compiler: str = ''
    wrapper_source_sha256: str = ''
    native_passes: tuple = ()
    decisions_requiring_preconditioner_evaluated: bool = False


def certify_ball_dyadic_box(
        weights, lower, upper, scale_values=None, *, bits=4,
        significant_bits=24, ridge, normalization=1, candidate_codes=None,
        max_exact_rank=64, max_exact_coordinates=16, max_refinement_coordinates=16,
        allow_python_fallback=True):
    """Certify constant exact dyadic codes over the supplied inclusive box.

The first pass uses ridge coefficient bounds. A rejected pass tries verified
preconditioning. Optional fallback uses the Python universal verifier only.
Singletons dispatch to the common native point solver. Inputs remain caller
owned and must not change during the call. Every repeated pass is charged.
"""
    started = time.perf_counter_ns()
    diagnostics = {'passes': [], 'fallback_elapsed_ns': 0, 'compile_elapsed_ns': 0,
                   'coefficient_policy': 'ridge_then_preconditioned'}
    _check_runtime()
    for name, value in (('weights', weights), ('lower', lower), ('upper', upper)):
        _matrix(value, name)
    scales = dyadic_row_scales(weights, bits, significant_bits)
    if scale_values is not None:
        supplied = tuple(scale_values)
        if any(type(s) is not float for s in supplied) or supplied != scales:
            raise ValueError('scales must equal the canonical base-only dyadic scales')
    if lower.shape != upper.shape or lower.shape[0] != weights.shape[1]:
        raise ValueError('feature box dimensions differ from weight width')
    if np.any(lower > upper):
        raise ValueError('reversed feature box')
    if max(weights.shape[1], lower.shape[1]) > 2**20:
        raise ValueError('native ball proof requires width and rank at most 2**20')
    if candidate_codes is not None:
        _matrix(candidate_codes, 'candidate_codes')
        if candidate_codes.shape != weights.shape:
            raise ValueError('candidate dimensions differ from weights')
    for value in (max_exact_rank, max_exact_coordinates, max_refinement_coordinates):
        if type(value) is not int or value < 0:
            raise ValueError('fallback limits must be nonnegative built-in integers')
    if type(allow_python_fallback) is not bool:
        raise ValueError('allow_python_fallback must be a built-in bool')
    lam, norm = _rational(ridge, 'ridge'), _rational(normalization, 'normalization')
    if lam <= 0 or norm <= 0:
        raise ValueError('ridge and normalization must be positive')
    tiny = np.float64(np.finfo(np.float64).smallest_subnormal)
    if tiny == 0 or tiny * np.float64(1.) != tiny or np.float64(2.) * tiny != tiny + tiny:
        raise TokenBoxUnresolved('gradual-underflow runtime check failed')
    uncertain = int(np.count_nonzero(lower != upper))
    wrapper_digest = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    common = dict(bits=bits, significant_bits=significant_bits, ridge=lam, normalization=norm,
        max_exact_rank=max_exact_rank, max_exact_coordinates=max_exact_coordinates,
        max_refinement_coordinates=max_refinement_coordinates)
    try:
        if not uncertain:
            tick = time.perf_counter_ns()
            point = ball.native_ball_quantize_dyadic_rows(
                np.require(weights, dtype=np.float64, requirements=['C', 'A']),
                np.require(lower, dtype=np.float64, requirements=['C', 'A']), scales, **common)
            base = preconditioned._result(_finish(point.codes, point.interval_decisions,
                point.exact_decisions, 0, point.max_coefficient_error_squared, candidate_codes))
            return BallBoxResult(**base.__dict__, backend='native_singleton_point',
                fallback_elapsed_ns=time.perf_counter_ns()-tick, compile_elapsed_ns=point.compile_elapsed_ns,
                total_elapsed_ns=time.perf_counter_ns()-started,
                native_source_sha256=point.native_source_sha256, native_binary_sha256=point.native_binary_sha256,
                native_compiler=point.native_compiler,
                wrapper_source_sha256=wrapper_digest)
        build = ball.prepare_native_ball()
        diagnostics.update(build=build, compile_elapsed_ns=build['call_compile_elapsed_ns'])
        tick = time.perf_counter_ns()
        grid, boundaries = _grid_arrays(scales, bits)
        center, radius, feature_error, discrepancy = _feature_uncertainty_bounds(weights, lower, upper, grid)
        feature_ns = time.perf_counter_ns() - tick
        diagnostics.update(feature_bounds_elapsed_ns=feature_ns,
            max_feature_radius=float(np.max(radius)) if radius.size else 0.,
            max_feature_accumulator_error=float(np.max(feature_error)))
        used_preconditioner = False
        valid_count = 0
        for policy in ('ridge', 'preconditioned'):
            tick = time.perf_counter_ns()
            with np.errstate(over='ignore', invalid='ignore', under='ignore', divide='ignore'):
                if policy == 'ridge':
                    proposal, errors = boxes._box_coefficients(lower, upper, lam * norm)
                else:
                    proposal, errors, component, valid = preconditioned._coefficient_bounds(lower, upper, lam * norm)
                    component_squared = _norm_squared_upper(-component, component)
                    errors = np.where(valid, np.minimum(errors, component_squared), errors)
                    used_preconditioner = True
                    valid_count = int(np.count_nonzero(valid))
                _finite(proposal, errors)
                rho = ball._coefficient_radii(errors)
            coefficient_ns = time.perf_counter_ns() - tick
            tick = time.perf_counter_ns()
            umax, proposal_l1 = _augmented_underflow_bounds(center, proposal, feature_error)
            bounds_ns = time.perf_counter_ns() - tick
            codes, receipt = _native_pass(weights, center, proposal, rho, umax, proposal_l1, grid, boundaries)
            receipt.update(policy=policy, coefficient_elapsed_ns=coefficient_ns, bounds_elapsed_ns=bounds_ns)
            diagnostics['passes'].append(receipt)
            if receipt['status']:
                raise TokenBoxUnresolved('native runtime or allocation failure; no codes committed')
            if not receipt['failed_rows']:
                break
        fallback_ns = 0
        fallback = receipt['failed_rows'] > 0
        if fallback:
            if not allow_python_fallback:
                raise TokenBoxUnresolved(f"ball box unresolved at row {receipt['first_unresolved_row']}, "
                                         f"coordinate {receipt['first_unresolved_coordinate']}")
            tick = time.perf_counter_ns()
            try:
                base = preconditioned.certify_preconditioned_dyadic_box(
                    weights, lower, upper, scales, candidate_codes=candidate_codes, **common)
            finally:
                fallback_ns = time.perf_counter_ns() - tick
                diagnostics['fallback_elapsed_ns'] = fallback_ns
        else:
            base = preconditioned._result(_finish(codes, weights.size, 0, uncertain,
                float(np.max(errors)), candidate_codes), valid_count,
                weights.shape[1]-valid_count if used_preconditioner else 0, 0)
        passes = diagnostics['passes']
        return BallBoxResult(**base.__dict__,
            native_attempted_decisions=sum(p['attempted_decisions'] for p in passes),
            native_certified_decisions=sum(p['certified_decisions'] for p in passes),
            python_universal_fallback=fallback, feature_bounds_elapsed_ns=feature_ns,
            coefficient_elapsed_ns=sum(p['coefficient_elapsed_ns'] for p in passes),
            ball_bounds_elapsed_ns=sum(p['bounds_elapsed_ns'] for p in passes),
            native_elapsed_ns=sum(p['native_elapsed_ns'] for p in passes),
            fallback_elapsed_ns=fallback_ns, compile_elapsed_ns=build['call_compile_elapsed_ns'],
            total_elapsed_ns=time.perf_counter_ns()-started,
            max_feature_radius=diagnostics['max_feature_radius'],
            max_feature_accumulator_error=diagnostics['max_feature_accumulator_error'],
            native_source_sha256=build['source_sha256'], native_binary_sha256=build['binary_sha256'],
            native_compiler=build['compiler_version'],
            wrapper_source_sha256=wrapper_digest,
            native_passes=tuple(dict(p) for p in passes),
            decisions_requiring_preconditioner_evaluated=fallback)
    except TokenBoxUnresolved as exc:
        diagnostics['total_elapsed_ns'] = time.perf_counter_ns() - started
        exc.native_diagnostics = diagnostics
        raise
    except LowRankUnresolved as exc:
        failure = TokenBoxUnresolved(str(exc))
        diagnostics['total_elapsed_ns'] = time.perf_counter_ns() - started
        failure.native_diagnostics = diagnostics
        raise failure from exc
