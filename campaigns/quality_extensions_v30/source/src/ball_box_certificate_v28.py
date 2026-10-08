"""Row-selective universal certificates with shared coefficient evidence.

Complete rows certified by the initial ball pass remain reusable. Only its
unresolved rows receive interval verification. No partial row is accepted.
"""
from __future__ import annotations

import ctypes
from dataclasses import dataclass
import hashlib
from pathlib import Path
import time

import numpy as np

from . import native_ball_quantizer as ball
from . import native_box_certificate as interval
from . import preconditioned_box_certificate as preconditioned
from . import token_box_certificate as boxes
from .ball_box_certificate_v27 import _feature_uncertainty_bounds, _augmented_underflow_bounds
from .dyadic_row_quantizer import dyadic_row_scales, _grid_arrays
from .exact_core import _rational
from .low_rank_certified import LowRankUnresolved, _finite
from .token_box_certificate import TokenBoxUnresolved, _finish, _matrix
from .transformer_backend import _check_runtime


def _ball_pass(weights, center, proposal, rho, umax, proposal_l1, grid, boundaries):
    """Return every row's failure coordinate, including discarded partial rows."""
    started = time.perf_counter_ns()
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
    native_ns = time.perf_counter_ns() - tick
    selected = np.flatnonzero(failed >= 0)
    receipt = {
        'backend': 'ball', 'policy': 'ridge', 'status': int(status),
        'native_elapsed_ns': native_ns, 'pass_elapsed_ns': time.perf_counter_ns()-started,
        'rows_evaluated': int(len(weights)), 'failed_rows': int(len(selected)),
        'failed_row_indices': tuple(int(row) for row in selected),
        'failed_coordinates': tuple(int(failed[row]) for row in selected),
        'attempted_decisions': int(counts[2]), 'certified_decisions': int(counts[3]),
    }
    return codes, failed, receipt


def _interval_rows(weights, lower, upper, proposal, component, valid, grid, boundaries,
                   selected, codes, diagnostics, policy):
    """Certify selected complete rows, preserving original row identities."""
    remaining = []
    for row in selected:
        row = int(row)
        started = time.perf_counter_ns()
        status, result, receipt = interval._native_pass(
            weights[row:row+1], lower, upper, proposal, component, valid,
            grid[row:row+1], boundaries[row:row+1])
        receipt = dict(receipt, backend='interval', policy=policy, status=int(status),
            global_row=row, rows_evaluated=1, pass_elapsed_ns=time.perf_counter_ns()-started,
            failed_rows=int(status == 3),
            failed_row_indices=(row,) if status == 3 else (),
            failed_coordinates=(receipt['unresolved_coordinate'],) if status == 3 else ())
        # The kernel sees one local row. Preserve its local failure separately.
        receipt['local_unresolved_row'] = receipt.pop('unresolved_row')
        receipt['unresolved_row'] = row if status == 3 else -1
        diagnostics['passes'].append(receipt)
        if status == 0:
            codes[row] = result[0]
        elif status == 3:
            remaining.append(row)
        else:
            raise TokenBoxUnresolved('native interval runtime or allocation failure; no codes committed')
    return np.asarray(remaining, dtype=np.int64)


@dataclass(frozen=True)
class BallBoxResult(preconditioned.PreconditionedBoxResult):
    backend: str = 'native_ball_sparse_interval_box'
    coefficient_policy: str = 'ridge_ball_then_sparse_intervals'
    native_attempted_decisions: int = 0
    native_certified_decisions: int = 0
    first_ball_certified_rows: int = 0
    ridge_interval_certified_rows: int = 0
    preconditioned_interval_certified_rows: int = 0
    python_universal_rows: int = 0
    python_universal_fallback: bool = False
    feature_bounds_elapsed_ns: int = 0
    coefficient_elapsed_ns: int = 0
    ball_bounds_elapsed_ns: int = 0
    interval_bounds_elapsed_ns: int = 0
    native_elapsed_ns: int = 0
    fallback_elapsed_ns: int = 0
    compile_elapsed_ns: int = 0
    total_elapsed_ns: int = 0
    max_feature_radius: float = 0.0
    max_feature_accumulator_error: float = 0.0
    native_source_sha256: str = ''
    native_binary_sha256: str = ''
    native_compiler: str = ''
    interval_source_sha256: str = ''
    interval_binary_sha256: str = ''
    wrapper_source_sha256: str = ''
    native_passes: tuple = ()
    decisions_requiring_preconditioner_evaluated: bool = False


def certify_ball_dyadic_box(
        weights, lower, upper, scale_values=None, *, bits=4,
        significant_bits=24, ridge, normalization=1, candidate_codes=None,
        max_exact_rank=64, max_exact_coordinates=16, max_refinement_coordinates=16,
        allow_python_fallback=True):
    """Certify every row universally, sharing evidence across sparse repairs.

All passes use the full feature box, full coordinate order, and unchanged
row grids. Only complete certified rows enter the immutable returned model.
Uncertain boxes never use point fallback. Caller inputs must remain unchanged.
"""
    started = time.perf_counter_ns()
    diagnostics = {'passes': [], 'fallback_elapsed_ns': 0, 'compile_elapsed_ns': 0,
                   'coefficient_policy': 'ridge_ball_then_sparse_intervals'}
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
                native_compiler=point.native_compiler, wrapper_source_sha256=wrapper_digest)
        build = ball.prepare_native_ball()
        diagnostics.update(builds={'ball': build}, compile_elapsed_ns=build['call_compile_elapsed_ns'])
        tick = time.perf_counter_ns()
        grid, boundaries = _grid_arrays(scales, bits)
        center, radius, feature_error, _ = _feature_uncertainty_bounds(weights, lower, upper, grid)
        feature_ns = time.perf_counter_ns() - tick
        diagnostics.update(feature_bounds_elapsed_ns=feature_ns,
            max_feature_radius=float(np.max(radius)) if radius.size else 0.,
            max_feature_accumulator_error=float(np.max(feature_error)))
        tick = time.perf_counter_ns()
        with np.errstate(over='ignore', invalid='ignore', under='ignore', divide='ignore'):
            proposal, errors = boxes._box_coefficients(lower, upper, lam * norm)
            _finite(proposal, errors)
            rho = ball._coefficient_radii(errors)
        coefficient_ns = time.perf_counter_ns() - tick
        maximum_error = float(np.max(errors))
        diagnostics['coefficient_elapsed_ns'] = coefficient_ns
        tick = time.perf_counter_ns()
        umax, proposal_l1 = _augmented_underflow_bounds(center, proposal, feature_error)
        bounds_ns = time.perf_counter_ns() - tick
        diagnostics['ball_bounds_elapsed_ns'] = bounds_ns
        codes, failed, receipt = _ball_pass(weights, center, proposal, rho, umax, proposal_l1, grid, boundaries)
        diagnostics['passes'].append(receipt)
        if receipt['status']:
            raise TokenBoxUnresolved('native ball runtime or allocation failure; no codes committed')
        selected = np.flatnonzero(failed >= 0)
        first_rows = len(weights) - len(selected)
        ridge_rows = preconditioned_rows = valid_count = 0
        preconditioned_used = False
        interval_build = None
        interval_bounds_ns = 0
        if len(selected):
            interval_build = interval.prepare_native_box()
            diagnostics['builds']['interval'] = interval_build
            diagnostics['compile_elapsed_ns'] += interval_build['call_compile_elapsed_ns']
            tick = time.perf_counter_ns()
            # The existing l2 radius bounds each component for the same proposal.
            component = np.broadcast_to(rho[:, None], lower.shape).copy()
            valid = np.ones(weights.shape[1], dtype=bool)
            interval_bounds_ns = time.perf_counter_ns() - tick
            diagnostics['interval_bounds_elapsed_ns'] = interval_bounds_ns
            count = len(selected)
            selected = _interval_rows(weights, lower, upper, proposal, component, valid,
                grid, boundaries, selected, codes, diagnostics, 'shared_ridge')
            ridge_rows = count - len(selected)
        if len(selected):
            tick = time.perf_counter_ns()
            with np.errstate(over='ignore', invalid='ignore', under='ignore', divide='ignore'):
                stronger_proposal, stronger_errors, component, valid = preconditioned._coefficient_bounds(lower, upper, lam * norm)
            preconditioned_ns = time.perf_counter_ns() - tick
            coefficient_ns += preconditioned_ns
            diagnostics['coefficient_elapsed_ns'] = coefficient_ns
            diagnostics['preconditioned_elapsed_ns'] = preconditioned_ns
            _finite(stronger_proposal, stronger_errors, component)
            if np.any(component < 0) or np.any(stronger_errors < 0):
                raise TokenBoxUnresolved('invalid preconditioned coefficient radius')
            maximum_error = max(maximum_error, float(np.max(stronger_errors)))
            valid_count = int(np.count_nonzero(valid))
            preconditioned_used = True
            count = len(selected)
            selected = _interval_rows(weights, lower, upper, stronger_proposal, component, valid,
                grid, boundaries, selected, codes, diagnostics, 'shared_preconditioned')
            preconditioned_rows = count - len(selected)
        fallback_ns = 0
        python_rows = len(selected)
        if python_rows:
            diagnostics['python_universal_row_indices'] = tuple(int(row) for row in selected)
            if not allow_python_fallback:
                raise TokenBoxUnresolved(f'universal box has unresolved original rows {tuple(int(row) for row in selected)}')
            tick = time.perf_counter_ns()
            try:
                # Row-local scales remain canonical under row selection.
                fallback = preconditioned.certify_preconditioned_dyadic_box(
                    weights[selected], lower, upper, tuple(scales[int(row)] for row in selected), **common)
                codes[selected] = fallback.codes
                maximum_error = max(maximum_error, fallback.max_coefficient_error_squared)
            finally:
                fallback_ns = time.perf_counter_ns() - tick
                diagnostics['fallback_elapsed_ns'] = fallback_ns
        base = preconditioned._result(_finish(codes, weights.size, 0, uncertain,
            maximum_error, candidate_codes), valid_count,
            weights.shape[1]-valid_count if preconditioned_used else 0, 0)
        passes = diagnostics['passes']
        return BallBoxResult(**base.__dict__,
            native_attempted_decisions=sum(p['attempted_decisions'] for p in passes),
            native_certified_decisions=sum(p['certified_decisions'] for p in passes),
            first_ball_certified_rows=first_rows, ridge_interval_certified_rows=ridge_rows,
            preconditioned_interval_certified_rows=preconditioned_rows, python_universal_rows=python_rows,
            python_universal_fallback=bool(python_rows), feature_bounds_elapsed_ns=feature_ns,
            coefficient_elapsed_ns=coefficient_ns, ball_bounds_elapsed_ns=bounds_ns,
            interval_bounds_elapsed_ns=interval_bounds_ns,
            native_elapsed_ns=sum(p['native_elapsed_ns'] for p in passes),
            fallback_elapsed_ns=fallback_ns, compile_elapsed_ns=diagnostics['compile_elapsed_ns'],
            total_elapsed_ns=time.perf_counter_ns()-started,
            max_feature_radius=diagnostics['max_feature_radius'],
            max_feature_accumulator_error=diagnostics['max_feature_accumulator_error'],
            native_source_sha256=build['source_sha256'], native_binary_sha256=build['binary_sha256'],
            native_compiler=build['compiler_version'], wrapper_source_sha256=wrapper_digest,
            interval_source_sha256=interval_build['source_sha256'] if interval_build else '',
            interval_binary_sha256=interval_build['binary_sha256'] if interval_build else '',
            native_passes=tuple(dict(p) for p in passes))
    except TokenBoxUnresolved as exc:
        diagnostics['total_elapsed_ns'] = time.perf_counter_ns() - started
        exc.native_diagnostics = diagnostics
        raise
    except LowRankUnresolved as exc:
        failure = TokenBoxUnresolved(str(exc))
        diagnostics['total_elapsed_ns'] = time.perf_counter_ns() - started
        failure.native_diagnostics = diagnostics
        raise failure from exc
