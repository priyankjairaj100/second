"""Shared native point acceleration with unchanged certified model outputs.

This wrapper preserves the established native decision loop. Its new directed
coefficient kernel removes Python residual loops. Reconstruction receives the
same optimization. The legacy bounded row fallback remains charged.
"""
import ctypes
from dataclasses import dataclass, fields
import time
import numpy as np
from . import native_ball_quantizer as ball
from .native_ball_quantizer import (NativeBallTokenResult, prepare_native_ball,
    _coefficient_radii, _underflow_bounds)
from .native_token_coefficients_v30 import (NativeCoefficientBudget,
    native_token_coefficient_enclosures)
from .dyadic_row_quantizer import dyadic_row_scales, _grid_arrays, quantize_dyadic_rows
from .exact_core import _rational
from .low_rank_certified import LowRankUnresolved
from .transformer_backend import _check_runtime

@dataclass(frozen=True)
class FastNativeTokenResult(NativeBallTokenResult):
    coefficient_verification: object = None


def native_fast_quantize_dyadic_rows(
        weights, features, scale_values=None, *, candidate=None, bits=4,
        significant_bits=24, ridge, normalization=1, max_exact_rank=64,
        max_exact_coordinates=16, max_refinement_coordinates=16,
        coefficient_budget=NativeCoefficientBudget()):
    """Certify the unchanged target with shared native arithmetic.

    A candidate only changes the first cell tested. Fresh uses the same kernel.
    Whole-row fallback repeats work and remains part of the total cost.
    All exact/refinement budgets apply jointly to all unresolved rows.
    No result is returned when the fallback cannot certify the target.
    """
    started = time.perf_counter_ns()
    _check_runtime()
    expected = dyadic_row_scales(weights, bits, significant_bits)
    if scale_values is None:
        supplied = expected
    else:
        supplied = tuple(scale_values)
        if any(type(x) is not float for x in supplied) or supplied != expected:
            raise ValueError('scale_values must equal canonical base-only dyadic scales')
    if (type(features) is not np.ndarray or features.dtype != np.float64 or features.ndim != 2
            or weights.shape[1] != features.shape[0] or not np.all(np.isfinite(features))):
        raise TypeError('features must be a finite matching binary64 matrix')
    if max(weights.shape[1], features.shape[1]) > 2 ** 20:
        raise ValueError('native error bounds require width and rank at most 2**20')
    for name, value in (('max_exact_rank', max_exact_rank),
                        ('max_exact_coordinates', max_exact_coordinates),
                        ('max_refinement_coordinates', max_refinement_coordinates)):
        if type(value) is not int or value < 0:
            raise ValueError(name + ' must be a nonnegative built-in integer')
    lam, norm = _rational(ridge, 'ridge'), _rational(normalization, 'normalization')
    if lam <= 0 or norm <= 0:
        raise ValueError('ridge and normalization must be positive')
    grid, boundaries = _grid_arrays(supplied, bits)
    candidate_indices = None
    if candidate is not None:
        if (type(candidate) is not np.ndarray or candidate.dtype != np.float64
                or candidate.shape != weights.shape or not np.all(np.isfinite(candidate))):
            raise ValueError('candidate must be a finite binary64 array with the weight shape')
        candidate_indices = np.empty(weights.shape, dtype=np.int16)
        for row in range(len(weights)):
            indices = np.searchsorted(grid[row], candidate[row])
            if np.any(indices >= len(grid[row])) or not np.array_equal(grid[row, indices], candidate[row]):
                raise ValueError('candidate values must belong to the exact row grid')
            candidate_indices[row] = indices
    build = prepare_native_ball()
    weights = np.require(weights, requirements=['C', 'A'])
    features = np.require(features, requirements=['C', 'A'])
    tick = time.perf_counter_ns()
    evidence = native_token_coefficient_enclosures(features, lam * norm, budget=coefficient_budget)
    coefficients = np.require(evidence.coefficients, requirements=['C', 'A'])
    errors = evidence.errors
    coefficient_ns = time.perf_counter_ns() - tick
    tick = time.perf_counter_ns()
    rho = _coefficient_radii(errors)
    with np.errstate(over='ignore', invalid='ignore', under='ignore'):
        umax, u_l1 = _underflow_bounds(features, coefficients)
    bounds_ns = time.perf_counter_ns() - tick
    codes = np.empty_like(weights)
    failed = np.empty(len(weights), dtype=np.int64)
    counts = np.zeros(4, dtype=np.uint64)
    ptr = ctypes.POINTER(ctypes.c_double)
    arrays = (weights, features, coefficients, rho, umax, u_l1, grid, boundaries)
    tick = time.perf_counter_ns()
    status = ball._NATIVE.nb_run(len(weights), weights.shape[1], features.shape[1], grid.shape[1],
        *(array.ctypes.data_as(ptr) for array in arrays),
        None if candidate_indices is None else candidate_indices.ctypes.data_as(ctypes.POINTER(ctypes.c_int16)),
        codes.ctypes.data_as(ptr), failed.ctypes.data_as(ctypes.POINTER(ctypes.c_int64)),
        counts.ctypes.data_as(ctypes.POINTER(ctypes.c_uint64)))
    native_ns = time.perf_counter_ns() - tick
    if status:
        raise LowRankUnresolved('native runtime or allocation failure; no codes committed')
    selected = np.flatnonzero(failed >= 0)
    exact_decisions, exact_coordinates, refined_coordinates, fallback_ns = 0, (), (), 0
    if len(selected):
        tick = time.perf_counter_ns()
        fallback = quantize_dyadic_rows(weights[selected], features,
            tuple(supplied[int(row)] for row in selected), bits=bits, significant_bits=significant_bits,
            ridge=ridge, normalization=normalization, max_exact_rank=max_exact_rank,
            max_exact_coordinates=max_exact_coordinates,
            max_refinement_coordinates=max_refinement_coordinates)
        codes[selected] = fallback.codes
        fallback_ns = time.perf_counter_ns() - tick
        exact_decisions = fallback.exact_decisions
        exact_coordinates, refined_coordinates = fallback.exact_coordinates, fallback.refined_coordinates
    codes.flags.writeable = False
    return FastNativeTokenResult(
        codes, weights.size - exact_decisions, exact_decisions, exact_coordinates,
        refined_coordinates, float(np.max(errors)), native_certified_rows=len(weights)-len(selected),
        fallback_rows=len(selected), native_attempted_decisions=int(counts[2]),
        native_prefix_certified_decisions=int(counts[3]),
        candidate_checks=int(counts[0]), candidate_hits=int(counts[1]),
        coefficient_elapsed_ns=coefficient_ns, bounds_elapsed_ns=bounds_ns,
        native_elapsed_ns=native_ns, fallback_elapsed_ns=fallback_ns,
        compile_elapsed_ns=build['call_compile_elapsed_ns']+evidence.compile_elapsed_ns,
        quantizer_elapsed_ns=time.perf_counter_ns()-started,
        candidate_source='supplied' if candidate is not None else 'none',
        native_source_sha256=build['source_sha256'], native_binary_sha256=build['binary_sha256'],
        native_compiler=build['compiler_version'],
        coefficient_verification={field.name:getattr(evidence,field.name) for field in fields(evidence)
            if field.name not in ('coefficients','errors')})

