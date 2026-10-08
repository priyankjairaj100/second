"""Residual-certified token-space rounding for the exact rational target.

NumPy supplies untrusted candidate solves. Directed elementary binary64
operations enclose their residuals and each rounding decision. Unresolved
cells use bounded exact rational solves, or abort without an output model.

Runtime premise: IEEE binary64 elementary +,-,*,/ operations round to nearest
with gradual underflow. No BLAS result is accepted without residual checks.
This module does not certify neural features, canonical state, or full costs.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction as Q
import math

import numpy as np

from .exact_core import _grids, _nearest_index, _rational
from .transformer_backend import _check_runtime


class LowRankUnresolved(ArithmeticError):
    """The bounded exact fallback could not complete an unresolved decision."""


@dataclass(frozen=True)
class CertifiedTokenResult:
    codes: np.ndarray
    interval_decisions: int
    exact_decisions: int
    exact_coordinates: tuple[int, ...]
    refined_coordinates: tuple[int, ...]
    max_coefficient_error_squared: float
    runtime_premise: str = "IEEE binary64 RN elementary operations; gradual underflow"


def _down(x):
    return np.nextafter(x, -np.inf)


def _up(x):
    return np.nextafter(x, np.inf)


def _finite(*values):
    if any(not np.all(np.isfinite(value)) for value in values):
        raise LowRankUnresolved("nonfinite intermediate; no codes committed")


def _point_bounds(value):
    value = _rational(value, "exact scalar")
    try:
        midpoint = float(value)
    except OverflowError as exc:
        raise LowRankUnresolved("exact scalar exceeds binary64 range") from exc
    if not math.isfinite(midpoint):
        raise LowRankUnresolved("exact scalar exceeds binary64 range")
    converted = Q.from_float(midpoint)
    return (midpoint if converted <= value else float(_down(midpoint)),
            midpoint if converted >= value else float(_up(midpoint)))


def _add(alo, ahi, blo, bhi):
    lo, hi = _down(alo + blo), _up(ahi + bhi)
    # An exact zero addend needs no rounding enclosure.
    zero_b = (blo == 0) & (bhi == 0)
    lo, hi = np.where(zero_b, alo, lo), np.where(zero_b, ahi, hi)
    zero_a = (alo == 0) & (ahi == 0)
    return np.where(zero_a, blo, lo), np.where(zero_a, bhi, hi)


def _multiply_point(lo, hi, point):
    a, b = lo * point, hi * point
    lower, upper = _down(np.minimum(a, b)), _up(np.maximum(a, b))
    zero = (point == 0) | ((lo == 0) & (hi == 0))
    return np.where(zero, 0.0, lower), np.where(zero, 0.0, upper)


def _norm_squared_upper(lo, hi):
    bound = np.maximum(np.abs(lo), np.abs(hi))
    result = np.zeros(bound.shape[:-1], dtype=np.float64)
    for k in range(bound.shape[-1]):
        term = _up(bound[..., k] * bound[..., k])
        term = np.where(bound[..., k] == 0, 0.0, term)
        result = np.where(term == 0, result, _up(result + term))
    return result


def _exact_solve(a, b):
    """Exact elimination with positive pivots for a positive-definite matrix."""
    n = len(b)
    rows = [list(row) + [rhs] for row, rhs in zip(a, b)]
    for k in range(n):
        pivot = rows[k][k]
        if pivot <= 0:
            raise ArithmeticError("exact SPD pivot failed")
        for i in range(k + 1, n):
            multiplier = rows[i][k] / pivot
            for j in range(k + 1, n + 1):
                rows[i][j] -= multiplier * rows[k][j]
            rows[i][k] = Q(0)
    solution = [Q(0)] * n
    for i in range(n - 1, -1, -1):
        solution[i] = (rows[i][n] - sum((rows[i][j] * solution[j]
                                      for j in range(i + 1, n)), Q(0))) / rows[i][i]
    return solution


def _exact_coefficient(z, coordinate, beta):
    rank = z.shape[1]
    gram = [[beta if j == k else Q(0) for k in range(rank)] for j in range(rank)]
    for row in z[coordinate:]:
        values = [Q.from_float(float(x)) for x in row]
        for j in range(rank):
            for k in range(j + 1):
                gram[j][k] += values[j] * values[k]
                gram[k][j] = gram[j][k]
    rhs = [Q.from_float(float(x)) for x in z[coordinate]]
    return _exact_solve(gram, rhs)


def _exact_input(weights, z, codes, row, coordinate, coefficient):
    accumulator = [Q(0)] * z.shape[1]
    for h in range(coordinate):
        residual = Q.from_float(float(weights[row, h])) - Q.from_float(float(codes[row, h]))
        for k in range(z.shape[1]):
            accumulator[k] += Q.from_float(float(z[h, k])) * residual
    return Q.from_float(float(weights[row, coordinate])) + sum(
        (x * y for x, y in zip(accumulator, coefficient)), Q(0))


def _residual_error_squared(gram_lo, gram_hi, vector, coefficient, beta_squared_lo):
    rank = len(vector)
    product_lo = np.zeros(rank)
    product_hi = np.zeros(rank)
    for k in range(rank):
        term_lo, term_hi = _multiply_point(gram_lo[:, k], gram_hi[:, k], coefficient[k])
        product_lo, product_hi = _add(product_lo, product_hi, term_lo, term_hi)
    residual_lo, residual_hi = _add(vector, vector, -product_hi, -product_lo)
    residual_squared = float(_norm_squared_upper(residual_lo, residual_hi))
    error = 0.0 if residual_squared == 0 else float(_up(residual_squared / beta_squared_lo))
    _finite(residual_lo, residual_hi, error)
    return error


def _initial_gram(rank, beta):
    beta_lo, beta_hi = _point_bounds(beta)
    if beta_lo <= 0:
        raise LowRankUnresolved("positive ridge-normalization product underflows")
    beta_squared_lo = float(_down(beta_lo * beta_lo))
    if beta_squared_lo <= 0:
        raise LowRankUnresolved("squared ridge-normalization product underflows")
    return np.eye(rank) * beta_lo, np.eye(rank) * beta_hi, beta_squared_lo


def _add_outer(gram_lo, gram_hi, vector):
    outer = vector[:, None] * vector[None, :]
    zero = (vector[:, None] == 0) | (vector[None, :] == 0)
    product_lo = np.where(zero, 0.0, _down(outer))
    product_hi = np.where(zero, 0.0, _up(outer))
    return _add(gram_lo, gram_hi, product_lo, product_hi)


def _coefficient_enclosures(z, beta):
    """Return candidate u_i and proved squared Euclidean error bounds."""
    d, rank = z.shape
    coefficients = np.empty_like(z)
    errors = np.zeros(d, dtype=np.float64)
    if rank == 0:
        return coefficients, errors
    gram_lo, gram_hi, beta_squared_lo = _initial_gram(rank, beta)
    inverse = np.eye(rank) / float(beta)
    for i in range(d - 1, -1, -1):
        vector = z[i]
        gram_lo, gram_hi = _add_outer(gram_lo, gram_hi, vector)
        candidate = inverse @ vector
        denominator = 1.0 + float(vector @ candidate)
        if not math.isfinite(denominator) or denominator <= 0:
            raise LowRankUnresolved("candidate inverse update failed")
        coefficient = candidate / denominator
        inverse -= np.outer(candidate, candidate) / denominator
        _finite(gram_lo, gram_hi, inverse, coefficient)
        coefficients[i] = coefficient
        errors[i] = _residual_error_squared(gram_lo, gram_hi, vector, coefficient, beta_squared_lo)
    return coefficients, errors


def _refined_coefficient(z, coordinate, beta):
    """Propose a fresh direct solve, then independently bound its residual."""
    rank = z.shape[1]
    if rank == 0:
        return np.empty(0), 0.0
    gram_lo, gram_hi, beta_squared_lo = _initial_gram(rank, beta)
    for vector in z[coordinate:][::-1]:
        gram_lo, gram_hi = _add_outer(gram_lo, gram_hi, vector)
    _finite(gram_lo, gram_hi)
    midpoint = gram_lo / 2.0 + gram_hi / 2.0
    try:
        coefficient = np.linalg.solve(midpoint, z[coordinate])
    except np.linalg.LinAlgError as exc:
        raise LowRankUnresolved("candidate direct solve failed") from exc
    _finite(coefficient)
    error = _residual_error_squared(gram_lo, gram_hi, z[coordinate], coefficient, beta_squared_lo)
    return coefficient, error


def _check_cells(weights, accum_lo, accum_hi, coefficient, error, grid):
    rank = len(coefficient)
    value_lo, value_hi = weights.copy(), weights.copy()
    for k in range(rank):
        term_lo, term_hi = _multiply_point(accum_lo[:, k], accum_hi[:, k], coefficient[k])
        value_lo, value_hi = _add(value_lo, value_hi, term_lo, term_hi)
    norm_squared = _norm_squared_upper(accum_lo, accum_hi)
    radius_squared = np.where((norm_squared == 0) | (error == 0),
                              0.0, _up(norm_squared * error))
    _finite(value_lo, value_hi, radius_squared)
    boundaries = [_point_bounds((left + right) / 2)
                  for left, right in zip(grid, grid[1:])]
    midpoint = value_lo / 2.0 + value_hi / 2.0
    indices = np.searchsorted([b[1] for b in boundaries], midpoint, side="left")
    safe = np.ones(len(weights), dtype=bool)
    if boundaries:
        boundary_lo = np.array([b[0] for b in boundaries])
        boundary_hi = np.array([b[1] for b in boundaries])
        lower = boundary_hi[np.maximum(indices - 1, 0)]
        upper = boundary_lo[np.minimum(indices, len(boundaries) - 1)]
        lower_gap = _down(value_lo - lower)
        upper_gap = _down(upper - value_hi)
        lower_safe = (lower_gap > 0) & (_down(lower_gap * lower_gap) > radius_squared)
        upper_safe = (upper_gap > 0) & (_down(upper_gap * upper_gap) > radius_squared)
        # A zero error permits the exact inclusive upper cell endpoint.
        lower_safe |= (radius_squared == 0) & (value_lo > lower)
        upper_safe |= (radius_squared == 0) & (value_hi <= upper)
        safe = ((indices == 0) | lower_safe) & ((indices == len(grid) - 1) | upper_safe)
    return indices, safe


def certified_token_codes(weights, features, grids, *, ridge, normalization=1,
                          max_exact_rank=64, max_exact_coordinates=16, max_refinement_coordinates=16):
    """Certify codes for H=ridge I+features features.T/normalization.

    ``weights`` and ``features`` must be finite NumPy binary64 matrices.
    Their represented dyadic values define the exact rational inputs.
    This explicit interface never silently converts an exact rational input.
    Each grid code must also be exactly representable in binary64.
    All approximate inverse operations are proposals, not trusted solves.
    Inputs must remain unchanged throughout the call. Array subclasses are rejected.
    """
    _check_runtime()
    if type(max_refinement_coordinates) is not int or max_refinement_coordinates < 0:
        raise ValueError("max_refinement_coordinates must be a nonnegative integer")
    if type(max_exact_rank) is not int or max_exact_rank < 0:
        raise ValueError("max_exact_rank must be a nonnegative integer")
    if type(max_exact_coordinates) is not int or max_exact_coordinates < 0:
        raise ValueError("max_exact_coordinates must be a nonnegative integer")
    for name, values in (("weights", weights), ("features", features)):
        if type(values) is not np.ndarray or values.dtype != np.float64 or values.ndim != 2:
            raise TypeError(f"{name} must be a binary64 NumPy matrix")
        if not np.all(np.isfinite(values)):
            raise ValueError(f"{name} must contain finite values")
    if weights.shape[0] == 0 or weights.shape[1] == 0 or weights.shape[1] != features.shape[0]:
        raise ValueError("nonempty weights and matching feature width are required")
    lam, norm = _rational(ridge, "ridge"), _rational(normalization, "normalization")
    if lam <= 0 or norm <= 0:
        raise ValueError("ridge and normalization must be positive")
    # Check the declared finite arithmetic premise for basic underflow behavior.
    tiny = np.float64(np.finfo(np.float64).smallest_subnormal)
    if tiny == 0 or tiny * np.float64(1.0) != tiny or np.float64(2.0) * tiny != tiny + tiny:
        raise LowRankUnresolved("gradual-underflow runtime check failed")
    fixed = _grids(grids, weights.shape[1])
    for grid in fixed:
        for value in grid:
            lo, hi = _point_bounds(value)
            if lo != hi:
                raise ValueError("grid codes must be exactly representable in binary64")
    z, w = features, weights
    with np.errstate(over="ignore", invalid="ignore", under="ignore", divide="ignore"):
        coefficients, errors = _coefficient_enclosures(z, lam * norm)
        p, d = w.shape
        rank = z.shape[1]
        accum_lo = np.zeros((p, rank))
        accum_hi = np.zeros((p, rank))
        codes = np.empty_like(w)
        exact_decisions = 0
        exact_coordinates = []
        refined_coordinates = []
        for i in range(d):
            indices, safe = _check_cells(w[:, i], accum_lo, accum_hi, coefficients[i], errors[i], fixed[i])
            bad = np.flatnonzero(~safe)
            if len(bad) and len(refined_coordinates) < max_refinement_coordinates:
                refined_coordinates.append(i)
                try:
                    refined, refined_error = _refined_coefficient(z, i, lam * norm)
                    refined_indices, refined_safe = _check_cells(
                        w[:, i], accum_lo, accum_hi, refined, refined_error, fixed[i])
                    # Keep every earlier verified decision. Add new verified decisions.
                    indices = np.where(safe, indices, refined_indices)
                    safe |= refined_safe
                except LowRankUnresolved:
                    pass
                bad = np.flatnonzero(~safe)
            if len(bad):
                if rank > max_exact_rank or len(exact_coordinates) >= max_exact_coordinates:
                    raise LowRankUnresolved(f"exact fallback budget exceeded at coordinate {i}; no codes committed")
                coefficient = _exact_coefficient(z, i, lam * norm)
                exact_coordinates.append(i)
                for row in bad:
                    value = _exact_input(w, z, codes, row, i, coefficient)
                    indices[row] = _nearest_index(value, fixed[i])
                exact_decisions += len(bad)
            codes[:, i] = np.array([float(value) for value in fixed[i]])[indices]
            difference_lo, difference_hi = _add(w[:, i], w[:, i], -codes[:, i], -codes[:, i])
            for k in range(rank):
                term_lo, term_hi = _multiply_point(difference_lo, difference_hi, z[i, k])
                accum_lo[:, k], accum_hi[:, k] = _add(accum_lo[:, k], accum_hi[:, k], term_lo, term_hi)
            _finite(accum_lo, accum_hi)
    codes.flags.writeable = False
    return CertifiedTokenResult(codes, p * d - exact_decisions, exact_decisions,
                                tuple(exact_coordinates), tuple(refined_coordinates), float(np.max(errors)))
