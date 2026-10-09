"""Certified speculative fixed points for the unchanged dyadic row target.

A parallel directed interval scan verifies arbitrary grid-valued proposals.
Certified rows and prefixes bypass ordinary sequential decisions.
Fresh and repair callers may use exactly the same solver and bounds.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction as Q
import time

import numpy as np

from .batched_token_solver import (
    _advance_accumulator, _coefficient_enclosures, _norm_squared_token_major,
)
from .dyadic_row_quantizer import dyadic_row_scales, _grid_arrays, _check_row_cells
from .exact_core import _nearest_index, _rational
from .low_rank_certified import (
    CertifiedTokenResult, LowRankUnresolved, _add, _down, _exact_coefficient,
    _exact_input, _finite, _multiply_point, _refined_coefficient, _up,
)
from .row_scaled_quantizer import _bits
from .transformer_backend import _check_runtime


@dataclass(frozen=True)
class SpeculativeTokenResult(CertifiedTokenResult):
    speculative_sweeps: int = 0
    speculative_decision_checks: int = 0
    speculative_certified_rows: int = 0
    sequential_fallback_rows: int = 0
    prefix_verified_decisions: int = 0
    fallback_decisions: int = 0
    coefficient_elapsed_ns: int = 0
    speculative_elapsed_ns: int = 0
    fallback_elapsed_ns: int = 0
    candidate_source: str = "nearest"
    scan_family: str = "directed_blelloch_v1"


def exclusive_interval_scan(lower, upper):
    """Enclose every exact exclusive prefix along axis zero.

    This work-efficient Blelloch scan uses directed elementary operations.
    Its proof does not depend on NumPy reduction or BLAS summation order.
    Nonfinite intermediates fail closed. Inputs remain unchanged.
    """
    if (type(lower) is not np.ndarray or type(upper) is not np.ndarray
            or lower.dtype != np.float64 or upper.dtype != np.float64
            or lower.shape != upper.shape or lower.ndim < 1):
        raise TypeError("scan endpoints require matching binary64 arrays")
    _finite(lower, upper)
    if np.any(lower > upper):
        raise ValueError("scan lower endpoint exceeds upper endpoint")
    count = len(lower)
    if not count:
        return lower.copy(), upper.copy()
    padded = 1 << (count - 1).bit_length()
    lo = np.zeros((padded,) + lower.shape[1:], dtype=np.float64)
    hi = np.zeros_like(lo)
    lo[:count], hi[:count] = lower, upper
    stride = 2
    while stride <= padded:
        right = np.arange(stride - 1, padded, stride)
        left = right - stride // 2
        a, b = _add(lo[left], hi[left], lo[right], hi[right])
        _finite(a, b)
        lo[right], hi[right] = a, b
        stride *= 2
    lo[-1] = hi[-1] = 0.0
    stride = padded
    while stride >= 2:
        right = np.arange(stride - 1, padded, stride)
        left = right - stride // 2
        # Advanced indexing makes copies before either child is overwritten.
        subtree_lo, subtree_hi = lo[left], hi[left]
        prefix_lo, prefix_hi = lo[right], hi[right]
        a, b = _add(prefix_lo, prefix_hi, subtree_lo, subtree_hi)
        _finite(a, b)
        lo[left], hi[left] = prefix_lo, prefix_hi
        lo[right], hi[right] = a, b
        stride //= 2
    return lo[:count], hi[:count]


def _speculative_inputs(weights, features, candidate, coefficients, errors, boundaries):
    """Return grid indices and certificates for F(candidate), without commits."""
    difference_lo, difference_hi = _add(weights.T, weights.T, -candidate.T, -candidate.T)
    product_lo, product_hi = _multiply_point(
        difference_lo[:, None, :], difference_hi[:, None, :], features[:, :, None])
    _finite(product_lo, product_hi)
    accum_lo, accum_hi = exclusive_interval_scan(product_lo, product_hi)
    term_lo, term_hi = _multiply_point(accum_lo, accum_hi, coefficients[:, :, None])
    value_lo, value_hi = weights.T.copy(), weights.T.copy()
    for token in range(features.shape[1]):
        value_lo, value_hi = _add(value_lo, value_hi, term_lo[:, token], term_hi[:, token])
    norm_squared = _norm_squared_token_major(
        np.moveaxis(accum_lo, 1, 0), np.moveaxis(accum_hi, 1, 0))
    radius_squared = np.where((norm_squared == 0) | (errors[:, None] == 0),
                              0.0, _up(norm_squared * errors[:, None]))
    _finite(value_lo, value_hi, radius_squared)
    midpoint = value_lo / 2.0 + value_hi / 2.0
    indices = np.count_nonzero(midpoint[:, :, None] > boundaries[None, :, :], axis=2)
    row = np.arange(weights.shape[0])[None, :]
    lower = boundaries[row, np.maximum(indices - 1, 0)]
    upper = boundaries[row, np.minimum(indices, boundaries.shape[1] - 1)]
    lower_gap, upper_gap = _down(value_lo - lower), _down(upper - value_hi)
    lower_safe = (lower_gap > 0) & (_down(lower_gap * lower_gap) > radius_squared)
    upper_safe = (upper_gap > 0) & (_down(upper_gap * upper_gap) > radius_squared)
    lower_safe |= (radius_squared == 0) & (value_lo > lower)
    upper_safe |= (radius_squared == 0) & (value_hi <= upper)
    safe = ((indices == 0) | lower_safe) & ((indices == boundaries.shape[1]) | upper_safe)
    return indices.T, safe.T, accum_lo, accum_hi


def speculative_quantize_dyadic_rows(
        weights, features, scale_values=None, *, candidate=None, max_sweeps=2,
        row_batch_size=128, bits=4, significant_bits=24, ridge, normalization=1,
        max_exact_rank=64, max_exact_coordinates=16, max_refinement_coordinates=16):
    """Return exact target codes, or fail without committing any model.

    The candidate is a proposal only. Complete row fixed points require every
    direct-grid cell certificate. Remaining rows use sequential quantization.
    Certified prefixes retain their sound accumulator bounds for fallback.
    Inputs must remain unchanged throughout the call.
    The exact and refinement limits count unique coordinates across all rows.
    Runtime premises match the existing direct dyadic solver.
    """
    _check_runtime()
    half = _bits(bits)
    expected = dyadic_row_scales(weights, bits, significant_bits)
    if scale_values is None:
        supplied = expected
    else:
        supplied = tuple(scale_values)
        if any(type(value) is not float for value in supplied) or supplied != expected:
            raise ValueError("scale_values must equal the canonical base-only dyadic row scales")
    if (type(features) is not np.ndarray or features.dtype != np.float64
            or features.ndim != 2 or weights.shape[1] != features.shape[0]):
        raise TypeError("features must be a matching binary64 matrix")
    if not np.all(np.isfinite(features)):
        raise ValueError("features must contain finite values")
    for name, value in (("max_sweeps", max_sweeps), ("max_exact_rank", max_exact_rank),
                        ("max_exact_coordinates", max_exact_coordinates),
                        ("max_refinement_coordinates", max_refinement_coordinates)):
        if type(value) is not int or value < 0:
            raise ValueError(f"{name} must be a nonnegative built-in integer")
    if type(row_batch_size) is not int or row_batch_size <= 0:
        raise ValueError("row_batch_size must be a positive built-in integer")
    lam, norm = _rational(ridge, "ridge"), _rational(normalization, "normalization")
    if lam <= 0 or norm <= 0:
        raise ValueError("ridge and normalization must be positive")
    tiny = np.float64(np.finfo(np.float64).smallest_subnormal)
    if tiny == 0 or tiny * np.float64(1.) != tiny or np.float64(2.) * tiny != tiny + tiny:
        raise LowRankUnresolved("gradual-underflow runtime check failed")
    grid_codes, boundaries = _grid_arrays(supplied, bits)
    if candidate is not None:
        if (type(candidate) is not np.ndarray or candidate.dtype != np.float64
                or candidate.shape != weights.shape or not np.all(np.isfinite(candidate))):
            raise ValueError("candidate must be a finite binary64 matrix with the weight shape")
        for start in range(0, len(weights), row_batch_size):
            stop = min(start + row_batch_size, len(weights))
            if not np.all(np.any(candidate[start:stop, :, None] == grid_codes[start:stop, None, :], axis=2)):
                raise ValueError("candidate codes must belong to their exact row grids")
    rows, width = weights.shape
    rank = features.shape[1]
    codes = np.empty_like(weights)
    prefix_lengths = np.zeros(rows, dtype=np.int64)
    prefix_lower, prefix_upper = np.zeros((rank, rows)), np.zeros((rank, rows))
    start_time = time.perf_counter_ns()
    coefficients, errors = _coefficient_enclosures(features, lam * norm)
    coefficient_ns = time.perf_counter_ns() - start_time
    exact_cache, refinement_cache, exact_grids = {}, {}, {}
    exact_coordinates, refined_coordinates = [], []
    exact_decisions = certified_rows = fallback_rows = sweeps = decision_checks = 0
    speculative_ns = fallback_ns = 0
    pending = []

    def sequential(selected):
        nonlocal exact_decisions
        w = weights[selected]
        result = codes[selected].copy()
        starts = prefix_lengths[selected]
        accum_lo, accum_hi = prefix_lower[:, selected].copy(), prefix_upper[:, selected].copy()
        for i in range(int(np.min(starts)), width):
            active = np.flatnonzero(starts <= i)
            global_rows = selected[active]
            indices, safe = _check_row_cells(w[active, i], accum_lo[:, active], accum_hi[:, active],
                coefficients[i], errors[i], boundaries[global_rows])
            bad = np.flatnonzero(~safe)
            if len(bad) and (i in refinement_cache or len(refined_coordinates) < max_refinement_coordinates):
                if i not in refinement_cache:
                    refined_coordinates.append(i)
                    try:
                        refinement_cache[i] = _refined_coefficient(features, i, lam * norm)
                    except LowRankUnresolved:
                        refinement_cache[i] = None
                refined = refinement_cache[i]
                if refined is not None:
                    better_indices, better_safe = _check_row_cells(
                        w[active, i], accum_lo[:, active], accum_hi[:, active],
                        refined[0], refined[1], boundaries[global_rows])
                    indices = np.where(safe, indices, better_indices)
                    safe |= better_safe
                bad = np.flatnonzero(~safe)
            if len(bad):
                if rank > max_exact_rank or (i not in exact_cache and len(exact_coordinates) >= max_exact_coordinates):
                    raise LowRankUnresolved(f"exact fallback budget exceeded at coordinate {i}; no codes committed")
                if i not in exact_cache:
                    exact_cache[i] = _exact_coefficient(features, i, lam * norm)
                    exact_coordinates.append(i)
                for row in bad:
                    local_row = int(active[row])
                    global_row = int(selected[local_row])
                    if global_row not in exact_grids:
                        scale = Q.from_float(supplied[global_row])
                        exact_grids[global_row] = tuple(code * scale for code in range(-half, half))
                    value = _exact_input(w, features, result, local_row, i, exact_cache[i])
                    indices[row] = _nearest_index(value, exact_grids[global_row])
                exact_decisions += len(bad)
            result[active, i] = grid_codes[global_rows, indices]
            a, b = _advance_accumulator(
                accum_lo[:, active], accum_hi[:, active], w[active, i], result[active, i], features[i])
            accum_lo[:, active], accum_hi[:, active] = a, b
            _finite(accum_lo, accum_hi)
        codes[selected] = result

    with np.errstate(over="ignore", invalid="ignore", under="ignore", divide="ignore"):
        for start in range(0, rows, row_batch_size):
            selected = np.arange(start, min(start + row_batch_size, rows))
            tick = time.perf_counter_ns()
            if max_sweeps == 0:
                proposal = None
            elif candidate is None:
                indices = np.count_nonzero(weights[selected, :, None] > boundaries[selected, None, :], axis=2)
                proposal = grid_codes[selected[:, None], indices]
            else:
                proposal = candidate[selected].copy()
            for _ in range(max_sweeps):
                if not len(selected):
                    break
                sweeps += 1
                decision_checks += len(selected) * width
                try:
                    indices, safe, scan_lo, scan_hi = _speculative_inputs(
                        weights[selected], features, proposal, coefficients, errors, boundaries[selected])
                except LowRankUnresolved:
                    break
                next_proposal = grid_codes[selected[:, None], indices]
                matches = safe & (next_proposal == proposal)
                lengths = np.where(np.all(matches, axis=1), width, np.argmin(matches, axis=1))
                for local_row, global_row in enumerate(selected):
                    length = int(lengths[local_row])
                    if length > prefix_lengths[global_row]:
                        prefix_lengths[global_row] = length
                        codes[global_row, :length] = proposal[local_row, :length]
                        if length < width:
                            prefix_lower[:, global_row] = scan_lo[length, :, local_row]
                            prefix_upper[:, global_row] = scan_hi[length, :, local_row]
                    known = int(prefix_lengths[global_row])
                    next_proposal[local_row, :known] = codes[global_row, :known]
                accepted = prefix_lengths[selected] == width
                certified_rows += int(np.count_nonzero(accepted))
                selected = selected[~accepted]
                proposal = next_proposal[~accepted]
            speculative_ns += time.perf_counter_ns() - tick
            if len(selected):
                fallback_rows += len(selected)
                pending.append(selected)
        if pending:
            tick = time.perf_counter_ns()
            sequential(np.concatenate(pending))
            fallback_ns += time.perf_counter_ns() - tick
    codes.flags.writeable = False
    prefix_decisions = int(np.sum(prefix_lengths))
    return SpeculativeTokenResult(
        codes, weights.size - exact_decisions, exact_decisions,
        tuple(sorted(exact_coordinates)), tuple(sorted(refined_coordinates)), float(np.max(errors)),
        speculative_sweeps=sweeps, speculative_decision_checks=decision_checks,
        speculative_certified_rows=certified_rows, sequential_fallback_rows=fallback_rows,
        prefix_verified_decisions=prefix_decisions, fallback_decisions=weights.size-prefix_decisions,
        coefficient_elapsed_ns=coefficient_ns, speculative_elapsed_ns=speculative_ns,
        fallback_elapsed_ns=fallback_ns, candidate_source="supplied" if candidate is not None else "nearest")
