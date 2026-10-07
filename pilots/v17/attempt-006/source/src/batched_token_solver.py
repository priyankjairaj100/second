"""Optional common batching for the existing exact token-space target.

Batch only independent entries. Keep every directed addition in its original
order. Coefficient solves remain untrusted proposals. Grid cells, fallback
limits, exact fallback, and result semantics match the reference solver.
This module neither changes the target nor claims a measured speedup.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math

import numpy as np

from .exact_core import _grids, _nearest_index, _rational
from .low_rank_certified import (
    CertifiedTokenResult, LowRankUnresolved, _add, _add_outer, _down,
    _exact_coefficient, _exact_input, _finite, _initial_gram,
    _multiply_point, _point_bounds, _refined_coefficient, _up,
)
from .row_scaled_quantizer import _bits, row_scale_exponents
from .transformer_backend import _check_runtime


@dataclass(frozen=True)
class _Grid:
    exact: tuple
    codes: np.ndarray
    boundary_lower: np.ndarray
    boundary_upper: np.ndarray


def _compile_grids(grids, width):
    """Cache identical fixed grids without changing any rational boundary."""
    fixed = _grids(grids, width)
    compiled, cache = [], {}
    for grid in fixed:
        if grid not in cache:
            for value in grid:
                lo, hi = _point_bounds(value)
                if lo != hi:
                    raise ValueError("grid codes must be exactly representable in binary64")
            bounds = [_point_bounds((left + right) / 2)
                      for left, right in zip(grid, grid[1:])]
            cache[grid] = _Grid(
                grid, np.array([float(value) for value in grid]),
                np.array([bound[0] for bound in bounds]),
                np.array([bound[1] for bound in bounds]))
        compiled.append(cache[grid])
    return tuple(compiled)


def _norm_squared_token_major(lower, upper):
    """Batch all squares, then add token terms in the original order."""
    bound = np.maximum(np.abs(lower), np.abs(upper))
    terms = np.where(bound == 0, 0.0, _up(bound * bound))
    result = np.zeros(bound.shape[1:], dtype=np.float64)
    for term in terms:
        result = np.where(term == 0, result, _up(result + term))
    return result


def _residual_error_squared(gram_lower, gram_upper, vector, coefficient, beta_squared_lower):
    # Transposition batches independent products and makes each summed row
    # contiguous. The reduction still visits k=0,...,T-1.
    terms_lower, terms_upper = _multiply_point(
        gram_lower.T, gram_upper.T, coefficient[:, None])
    product_lower, product_upper = np.zeros(len(vector)), np.zeros(len(vector))
    for lower, upper in zip(terms_lower, terms_upper):
        product_lower, product_upper = _add(product_lower, product_upper, lower, upper)
    residual_lower, residual_upper = _add(vector, vector, -product_upper, -product_lower)
    residual_squared = float(_norm_squared_token_major(residual_lower, residual_upper))
    error = 0.0 if residual_squared == 0 else float(_up(residual_squared / beta_squared_lower))
    _finite(residual_lower, residual_upper, error)
    return error


def _coefficient_enclosures(features, beta):
    width, rank = features.shape
    coefficients, errors = np.empty_like(features), np.zeros(width, dtype=np.float64)
    if not rank:
        return coefficients, errors
    gram_lower, gram_upper, beta_squared_lower = _initial_gram(rank, beta)
    inverse = np.eye(rank) / float(beta)
    for i in range(width - 1, -1, -1):
        vector = features[i]
        gram_lower, gram_upper = _add_outer(gram_lower, gram_upper, vector)
        candidate = inverse @ vector
        denominator = 1.0 + float(vector @ candidate)
        if not math.isfinite(denominator) or denominator <= 0:
            raise LowRankUnresolved("candidate inverse update failed")
        coefficient = candidate / denominator
        inverse -= np.outer(candidate, candidate) / denominator
        _finite(gram_lower, gram_upper, inverse, coefficient)
        coefficients[i] = coefficient
        errors[i] = _residual_error_squared(
            gram_lower, gram_upper, vector, coefficient, beta_squared_lower)
    return coefficients, errors


def _check_cells(weights, accum_lower, accum_upper, coefficient, error, grid):
    """Accumulator shape is (token, output row), unlike the reference layout."""
    value_lower, value_upper = weights.copy(), weights.copy()
    term_lower, term_upper = _multiply_point(accum_lower, accum_upper, coefficient[:, None])
    for lower, upper in zip(term_lower, term_upper):
        value_lower, value_upper = _add(value_lower, value_upper, lower, upper)
    norm_squared = _norm_squared_token_major(accum_lower, accum_upper)
    radius_squared = np.where((norm_squared == 0) | (error == 0),
                              0.0, _up(norm_squared * error))
    _finite(value_lower, value_upper, radius_squared)
    midpoint = value_lower / 2.0 + value_upper / 2.0
    indices = np.searchsorted(grid.boundary_upper, midpoint, side="left")
    safe = np.ones(len(weights), dtype=bool)
    if len(grid.boundary_lower):
        lower = grid.boundary_upper[np.maximum(indices - 1, 0)]
        upper = grid.boundary_lower[np.minimum(indices, len(grid.boundary_lower) - 1)]
        lower_gap = _down(value_lower - lower)
        upper_gap = _down(upper - value_upper)
        lower_safe = (lower_gap > 0) & (_down(lower_gap * lower_gap) > radius_squared)
        upper_safe = (upper_gap > 0) & (_down(upper_gap * upper_gap) > radius_squared)
        lower_safe |= (radius_squared == 0) & (value_lower > lower)
        upper_safe |= (radius_squared == 0) & (value_upper <= upper)
        safe = ((indices == 0) | lower_safe) & ((indices == len(grid.exact) - 1) | upper_safe)
    return indices, safe


def _advance_accumulator(lower, upper, weights, codes, features):
    """Update independent token/output entries with the original operations."""
    difference_lower, difference_upper = _add(weights, weights, -codes, -codes)
    term_lower, term_upper = _multiply_point(
        difference_lower[None, :], difference_upper[None, :], features[:, None])
    return _add(lower, upper, term_lower, term_upper)


def batched_token_codes(weights, features, grids, *, ridge, normalization=1,
                        max_exact_rank=64, max_exact_coordinates=16,
                        max_refinement_coordinates=16):
    """Certify the unchanged exact target with independent arithmetic batched.

    The signature and CertifiedTokenResult match certified_token_codes.
    Inputs must remain unchanged throughout the call. Only ordinary finite
    binary64 matrices are accepted. No approximate model is returned.
    Every compatible repair and fresh method may use this common solver.
    """
    _check_runtime()
    for name, value in (("max_refinement_coordinates", max_refinement_coordinates),
                        ("max_exact_rank", max_exact_rank),
                        ("max_exact_coordinates", max_exact_coordinates)):
        if type(value) is not int or value < 0:
            raise ValueError(f"{name} must be a nonnegative integer")
    for name, values in (("weights", weights), ("features", features)):
        if type(values) is not np.ndarray or values.dtype != np.float64 or values.ndim != 2:
            raise TypeError(f"{name} must be a binary64 NumPy matrix")
        if not np.all(np.isfinite(values)):
            raise ValueError(f"{name} must contain finite values")
    if not weights.shape[0] or not weights.shape[1] or weights.shape[1] != features.shape[0]:
        raise ValueError("nonempty weights and matching feature width are required")
    lam, norm = _rational(ridge, "ridge"), _rational(normalization, "normalization")
    if lam <= 0 or norm <= 0:
        raise ValueError("ridge and normalization must be positive")
    tiny = np.float64(np.finfo(np.float64).smallest_subnormal)
    if tiny == 0 or tiny * np.float64(1.0) != tiny or np.float64(2.0) * tiny != tiny + tiny:
        raise LowRankUnresolved("gradual-underflow runtime check failed")
    fixed = _compile_grids(grids, weights.shape[1])
    with np.errstate(over="ignore", invalid="ignore", under="ignore", divide="ignore"):
        coefficients, errors = _coefficient_enclosures(features, lam * norm)
        rows, width = weights.shape
        rank = features.shape[1]
        accum_lower, accum_upper = np.zeros((rank, rows)), np.zeros((rank, rows))
        codes = np.empty_like(weights)
        exact_decisions, exact_coordinates, refined_coordinates = 0, [], []
        for i in range(width):
            indices, safe = _check_cells(
                weights[:, i], accum_lower, accum_upper, coefficients[i], errors[i], fixed[i])
            bad = np.flatnonzero(~safe)
            if len(bad) and len(refined_coordinates) < max_refinement_coordinates:
                refined_coordinates.append(i)
                try:
                    refined, refined_error = _refined_coefficient(features, i, lam * norm)
                    refined_indices, refined_safe = _check_cells(
                        weights[:, i], accum_lower, accum_upper, refined, refined_error, fixed[i])
                    indices = np.where(safe, indices, refined_indices)
                    safe |= refined_safe
                except LowRankUnresolved:
                    pass
                bad = np.flatnonzero(~safe)
            if len(bad):
                if rank > max_exact_rank or len(exact_coordinates) >= max_exact_coordinates:
                    raise LowRankUnresolved(f"exact fallback budget exceeded at coordinate {i}; no codes committed")
                coefficient = _exact_coefficient(features, i, lam * norm)
                exact_coordinates.append(i)
                for row in bad:
                    value = _exact_input(weights, features, codes, row, i, coefficient)
                    indices[row] = _nearest_index(value, fixed[i].exact)
                exact_decisions += len(bad)
            codes[:, i] = fixed[i].codes[indices]
            accum_lower, accum_upper = _advance_accumulator(
                accum_lower, accum_upper, weights[:, i], codes[:, i], features[i])
            _finite(accum_lower, accum_upper)
    codes.flags.writeable = False
    return CertifiedTokenResult(codes, weights.size - exact_decisions, exact_decisions,
                                tuple(exact_coordinates), tuple(refined_coordinates), float(np.max(errors)))


def batched_quantize_row_scaled(weights, features, exponents, *, bits=4, ridge,
                                normalization=1, max_exact_rank=64,
                                max_exact_coordinates=16, max_refinement_coordinates=16):
    """Use the common batched solver for the unchanged fixed output-row target."""
    _check_runtime()
    half = _bits(bits)
    expected = row_scale_exponents(weights, bits)
    try:
        supplied = tuple(exponents)
    except TypeError as exc:
        raise TypeError("exponents must be a sequence of built-in integers") from exc
    if any(type(value) is not int for value in supplied) or supplied != expected:
        raise ValueError("exponents must equal the canonical base-only row exponents")
    shifts = np.array(supplied, dtype=np.int64)[:, None]
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        normalized = np.ldexp(weights, -shifts)
        recovered = np.ldexp(normalized, shifts)
    if not np.all(np.isfinite(normalized)) or not np.array_equal(recovered, weights):
        raise ValueError("row normalization is not exactly representable in binary64")
    if np.any(normalized < -half) or np.any(normalized > half - 1):
        raise ArithmeticError("normalized base weights fall outside the integer grid")
    result = batched_token_codes(
        normalized, features, (tuple(range(-half, half)),) * weights.shape[1],
        ridge=ridge, normalization=normalization, max_exact_rank=max_exact_rank,
        max_exact_coordinates=max_exact_coordinates,
        max_refinement_coordinates=max_refinement_coordinates)
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        restored = np.ldexp(result.codes, shifts)
        roundtrip = np.ldexp(restored, -shifts)
    if not np.all(np.isfinite(restored)) or not np.array_equal(roundtrip, result.codes):
        raise ValueError("scaled quantized codes are not exactly representable in binary64")
    restored.flags.writeable = False
    return replace(result, codes=restored)
