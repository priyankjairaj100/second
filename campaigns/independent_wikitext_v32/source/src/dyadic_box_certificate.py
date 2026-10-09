"""Constant-code certificates on uncertain factors, in original weight units.

This implication needs a separate proof that actual factors lie in the box.
It does not compute transformer bounds or promise feature avoidance.
"""
import numpy as np

from .dyadic_row_quantizer import (
    dyadic_row_scales, quantize_dyadic_rows, _grid_arrays, _check_row_cells,
)
from .exact_core import _rational
from .low_rank_certified import LowRankUnresolved, _add, _finite
from .token_box_certificate import (
    TokenBoxUnresolved, _matrix, _box_coefficients, _multiply, _finish,
)
from .transformer_backend import _check_runtime


def certify_dyadic_box(weights, lower, upper, scale_values=None, *, bits=4,
                       significant_bits=24, ridge, normalization=1,
                       candidate_codes=None, max_exact_rank=64,
                       max_exact_coordinates=16, max_refinement_coordinates=16):
    """Certify one exact model for every finite factor matrix in [lower, upper].

    Nonzero-width boxes cannot use a pointwise exact fallback.
    Singleton boxes share the point solver and its global coordinate budgets.
    Caller-owned inputs must remain unchanged throughout the call.
    """
    _check_runtime()
    for name, value in (("weights", weights), ("lower", lower), ("upper", upper)):
        _matrix(value, name)
    scales = dyadic_row_scales(weights, bits, significant_bits)
    if scale_values is not None:
        supplied = tuple(scale_values)
        if any(type(s) is not float for s in supplied) or supplied != scales:
            raise ValueError("scales must equal the canonical base-only dyadic scales")
    if lower.shape != upper.shape or lower.shape[0] != weights.shape[1]:
        raise ValueError("feature box dimensions differ from weight width")
    if np.any(lower > upper):
        raise ValueError("reversed feature box")
    if candidate_codes is not None:
        _matrix(candidate_codes, "candidate_codes")
        if candidate_codes.shape != weights.shape:
            raise ValueError("candidate dimensions differ from weights")
    for value in (max_exact_rank, max_exact_coordinates, max_refinement_coordinates):
        if type(value) is not int or value < 0:
            raise ValueError("fallback limits must be nonnegative built-in integers")
    lam, norm = _rational(ridge, "ridge"), _rational(normalization, "normalization")
    if lam <= 0 or norm <= 0:
        raise ValueError("ridge and normalization must be positive")
    tiny = np.float64(np.finfo(np.float64).smallest_subnormal)
    if tiny == 0 or tiny * np.float64(1.) != tiny or np.float64(2.) * tiny != tiny + tiny:
        raise TokenBoxUnresolved("gradual-underflow runtime check failed")
    uncertain = int(np.count_nonzero(lower != upper))
    try:
        if not uncertain:
            point = quantize_dyadic_rows(
                weights, lower, scales, bits=bits, significant_bits=significant_bits,
                ridge=lam, normalization=norm, max_exact_rank=max_exact_rank,
                max_exact_coordinates=max_exact_coordinates,
                max_refinement_coordinates=max_refinement_coordinates)
            return _finish(point.codes, point.interval_decisions, point.exact_decisions,
                           0, point.max_coefficient_error_squared, candidate_codes)
        with np.errstate(over="ignore", invalid="ignore", under="ignore", divide="ignore"):
            proposals, errors = _box_coefficients(lower, upper, lam * norm)
            grid, boundaries = _grid_arrays(scales, bits)
            rows, width = weights.shape
            rank = lower.shape[1]
            accum_lo, accum_hi = np.zeros((rank, rows)), np.zeros((rank, rows))
            codes = np.empty_like(weights)
            for i in range(width):
                indices, safe = _check_row_cells(
                    weights[:, i], accum_lo, accum_hi, proposals[i], errors[i], boundaries)
                if not np.all(safe):
                    raise TokenBoxUnresolved(f"box does not certify every row at coordinate {i}")
                codes[:, i] = grid[np.arange(rows), indices]
                dlo, dhi = _add(weights[:, i], weights[:, i], -codes[:, i], -codes[:, i])
                for k in range(rank):
                    tlo, thi = _multiply(dlo, dhi, lower[i, k], upper[i, k])
                    accum_lo[k], accum_hi[k] = _add(accum_lo[k], accum_hi[k], tlo, thi)
                _finite(accum_lo, accum_hi)
            return _finish(codes, weights.size, 0, uncertain, float(np.max(errors)), candidate_codes)
    except TokenBoxUnresolved:
        raise
    except LowRankUnresolved as exc:
        raise TokenBoxUnresolved(str(exc)) from exc
