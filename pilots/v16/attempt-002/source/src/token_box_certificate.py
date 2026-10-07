"""Certify constant exact quantizer codes over a box of token factors.

The caller must prove that the new factors lie inside the supplied box.
This module certifies only the quantizer implication of that premise.
It builds token-by-token matrices, never a width-by-width Gram matrix.
An unresolved decision produces no model. Floating solves are proposals.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .exact_core import _grids, _rational
from .low_rank_certified import (
    LowRankUnresolved, _add, _check_cells, _down, _finite,
    _initial_gram, _multiply_point, _norm_squared_upper, _point_bounds,
    _up, certified_token_codes,
)
from .row_scaled_quantizer import _bits, row_scale_exponents
from .transformer_backend import _check_runtime


class TokenBoxUnresolved(LowRankUnresolved):
    """No constant code model was proved for the complete feature box."""


@dataclass(frozen=True)
class TokenBoxResult:
    codes: np.ndarray
    interval_decisions: int
    point_exact_decisions: int
    uncertain_features: int
    max_coefficient_error_squared: float
    candidate_checked: bool
    guarantee: str = "constant exact codes for every factor matrix inside the supplied box"


def _matrix(values, name):
    if type(values) is not np.ndarray or values.dtype != np.float64 or values.ndim != 2:
        raise TypeError(f"{name} must be an ordinary binary64 NumPy matrix")
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{name} must contain only finite values")


def _multiply(alo, ahi, blo, bhi):
    """Enclose interval products using separate elementary operations."""
    products = (alo * blo, alo * bhi, ahi * blo, ahi * bhi)
    lower = _down(np.minimum.reduce(products))
    upper = _up(np.maximum.reduce(products))
    zero = ((alo == 0) & (ahi == 0)) | ((blo == 0) & (bhi == 0))
    return np.where(zero, 0.0, lower), np.where(zero, 0.0, upper)


def _outer_bounds(lower, upper):
    lo, hi = _multiply(lower[:, None], upper[:, None], lower[None, :], upper[None, :])
    # A diagonal product uses the same variable twice. Preserve that fact.
    if len(lower):
        index = np.arange(len(lower))
        square_lo = _down(np.minimum(lower * lower, upper * upper))
        square_hi = _up(np.maximum(lower * lower, upper * upper))
        square_lo = np.where((lower <= 0) & (upper >= 0), 0.0, square_lo)
        square_hi = np.where((lower == 0) & (upper == 0), 0.0, square_hi)
        lo[index, index], hi[index, index] = square_lo, square_hi
    return lo, hi


def _box_residual_squared(gram_lo, gram_hi, rhs_lo, rhs_hi, proposal, beta_squared_lo):
    product_lo, product_hi = np.zeros(len(proposal)), np.zeros(len(proposal))
    for k in range(len(proposal)):
        term_lo, term_hi = _multiply_point(gram_lo[:, k], gram_hi[:, k], proposal[k])
        product_lo, product_hi = _add(product_lo, product_hi, term_lo, term_hi)
    residual_lo, residual_hi = _add(rhs_lo, rhs_hi, -product_hi, -product_lo)
    residual_squared = float(_norm_squared_upper(residual_lo, residual_hi))
    error = 0.0 if residual_squared == 0 else float(_up(residual_squared / beta_squared_lo))
    _finite(residual_lo, residual_hi, error)
    return error


def _box_coefficients(lower, upper, beta):
    """Bound every true coefficient using one common midpoint proposal."""
    width, rank = lower.shape
    proposals, errors = np.zeros_like(lower), np.zeros(width)
    if not rank:
        return proposals, errors
    gram_lo, gram_hi, beta_squared_lo = _initial_gram(rank, beta)
    inverse = np.eye(rank) / float(beta)
    for i in range(width - 1, -1, -1):
        outer_lo, outer_hi = _outer_bounds(lower[i], upper[i])
        gram_lo, gram_hi = _add(gram_lo, gram_hi, outer_lo, outer_hi)
        _finite(gram_lo, gram_hi)
        midpoint = lower[i] / 2.0 + upper[i] / 2.0
        vector = inverse @ midpoint
        denominator = 1.0 + float(midpoint @ vector)
        if np.isfinite(denominator) and denominator > 0 and np.all(np.isfinite(vector)):
            proposal = vector / denominator
            updated = inverse - np.outer(vector, vector) / denominator
            if np.all(np.isfinite(proposal)) and np.all(np.isfinite(updated)):
                inverse = updated
            else:
                inverse, proposal = np.zeros_like(inverse), np.zeros(rank)
        else:
            inverse, proposal = np.zeros_like(inverse), np.zeros(rank)
        proposals[i] = proposal
        errors[i] = _box_residual_squared(
            gram_lo, gram_hi, lower[i], upper[i], proposal, beta_squared_lo)
    return proposals, errors


def _finish(codes, intervals, exacts, uncertain, error, candidate):
    if candidate is not None and not np.array_equal(candidate, codes):
        raise TokenBoxUnresolved("the certified model differs from the supplied candidate")
    # A bytes owner prevents callers from re-enabling write access.
    immutable = np.frombuffer(codes.tobytes(order="C"), dtype=np.float64).reshape(codes.shape)
    return TokenBoxResult(immutable, intervals, exacts, uncertain, error, candidate is not None)


def certify_token_box(weights, feature_lower, feature_upper, grids, *, ridge,
                      normalization=1, candidate_codes=None, max_exact_rank=64,
                      max_exact_coordinates=16):
    """Prove exact codes for all Z with feature_lower <= Z <= feature_upper.

    H = ridge*I + Z*Z.T/normalization defines the exact target.
    Every supplied float denotes its exact dyadic value. Grids must be dyadic.
    Lower-code ties and the fixed coordinate order match the exact oracle.
    Inputs must remain unchanged throughout this call.
    Positive-width boxes have no pointwise or sampling-based fallback.
    Zero-width boxes may use the existing bounded exact point solver.
    """
    _check_runtime()
    for name, values in (("weights", weights), ("feature_lower", feature_lower),
                         ("feature_upper", feature_upper)):
        _matrix(values, name)
    if (not weights.shape[0] or not weights.shape[1]
            or feature_lower.shape != feature_upper.shape
            or feature_lower.shape[0] != weights.shape[1]):
        raise ValueError("nonempty weights and matching feature box dimensions are required")
    if np.any(feature_lower > feature_upper):
        raise ValueError("feature_lower must not exceed feature_upper")
    for name, value in (("max_exact_rank", max_exact_rank),
                        ("max_exact_coordinates", max_exact_coordinates)):
        if type(value) is not int or value < 0:
            raise ValueError(f"{name} must be a nonnegative built-in integer")
    if candidate_codes is not None:
        _matrix(candidate_codes, "candidate_codes")
        if candidate_codes.shape != weights.shape:
            raise ValueError("candidate_codes must match the weights shape")
    lam, norm = _rational(ridge, "ridge"), _rational(normalization, "normalization")
    if lam <= 0 or norm <= 0:
        raise ValueError("ridge and normalization must be positive")
    fixed = _grids(grids, weights.shape[1])
    for grid in fixed:
        for value in grid:
            if _point_bounds(value)[0] != _point_bounds(value)[1]:
                raise ValueError("grid codes must be exactly representable in binary64")
    tiny = np.float64(np.finfo(np.float64).smallest_subnormal)
    if tiny == 0 or tiny * np.float64(1.0) != tiny or np.float64(2.0) * tiny != tiny + tiny:
        raise TokenBoxUnresolved("NumPy gradual-underflow runtime check failed")
    uncertain = int(np.count_nonzero(feature_lower != feature_upper))
    try:
        if not uncertain:
            point = certified_token_codes(
                weights, feature_lower, fixed, ridge=lam, normalization=norm,
                max_exact_rank=max_exact_rank, max_exact_coordinates=max_exact_coordinates)
            return _finish(point.codes, point.interval_decisions, point.exact_decisions, 0,
                           point.max_coefficient_error_squared, candidate_codes)
        with np.errstate(over="ignore", invalid="ignore", under="ignore", divide="ignore"):
            proposals, errors = _box_coefficients(feature_lower, feature_upper, lam * norm)
            rows, width = weights.shape
            rank = feature_lower.shape[1]
            accum_lo, accum_hi = np.zeros((rows, rank)), np.zeros((rows, rank))
            codes = np.empty_like(weights)
            for i in range(width):
                indices, safe = _check_cells(
                    weights[:, i], accum_lo, accum_hi, proposals[i], errors[i], fixed[i])
                if not np.all(safe):
                    raise TokenBoxUnresolved(f"feature box crosses or cannot prove a rounding cell at coordinate {i}")
                codes[:, i] = np.asarray([float(code) for code in fixed[i]])[indices]
                diff_lo, diff_hi = _add(weights[:, i], weights[:, i], -codes[:, i], -codes[:, i])
                for k in range(rank):
                    term_lo, term_hi = _multiply(
                        diff_lo, diff_hi, feature_lower[i, k], feature_upper[i, k])
                    accum_lo[:, k], accum_hi[:, k] = _add(
                        accum_lo[:, k], accum_hi[:, k], term_lo, term_hi)
                _finite(accum_lo, accum_hi)
            return _finish(codes, weights.size, 0, uncertain, float(np.max(errors)), candidate_codes)
    except TokenBoxUnresolved:
        raise
    except LowRankUnresolved as exc:
        raise TokenBoxUnresolved(str(exc)) from exc


def certify_row_scaled_box(weights, feature_lower, feature_upper, exponents, *, bits=4,
                           ridge, normalization=1, candidate_codes=None,
                           max_exact_rank=64, max_exact_coordinates=16):
    """Certify the fixed base-only output-row target over a factor box."""
    _check_runtime()
    half = _bits(bits)
    expected = row_scale_exponents(weights, bits)
    supplied = tuple(exponents)
    if any(type(value) is not int for value in supplied) or supplied != expected:
        raise ValueError("exponents must equal the canonical base-only row exponents")
    shifts = np.asarray(supplied, dtype=np.int64)[:, None]
    if candidate_codes is not None:
        _matrix(candidate_codes, "candidate_codes")
        if candidate_codes.shape != weights.shape:
            raise ValueError("candidate_codes must match the weights shape")
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        normalized = np.ldexp(weights, -shifts)
        recovered = np.ldexp(normalized, shifts)
    if not np.all(np.isfinite(normalized)) or not np.array_equal(recovered, weights):
        raise ValueError("row normalization must be exactly representable in binary64")
    result = certify_token_box(
        normalized, feature_lower, feature_upper, (tuple(range(-half, half)),) * weights.shape[1],
        ridge=ridge, normalization=normalization, max_exact_rank=max_exact_rank,
        max_exact_coordinates=max_exact_coordinates)
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        restored = np.ldexp(result.codes, shifts)
        roundtrip = np.ldexp(restored, -shifts)
    if not np.all(np.isfinite(restored)) or not np.array_equal(roundtrip, result.codes):
        raise TokenBoxUnresolved("scaled codes cannot be represented exactly in binary64")
    return _finish(restored, result.interval_decisions, result.point_exact_decisions,
                   result.uncertain_features, result.max_coefficient_error_squared, candidate_codes)
