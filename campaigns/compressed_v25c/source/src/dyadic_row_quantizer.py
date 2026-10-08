"""A separate base-only row target with finer exact dyadic scales.

Weights remain in their original units. No division by a non-power-of-two
scale enters the solver. Each row has its own exact grid and exact fallback.
This module defines a new target and makes no empirical quality claim.
"""
from __future__ import annotations

from fractions import Fraction as Q
import math

import numpy as np

from .batched_token_solver import (
    _advance_accumulator, _coefficient_enclosures, _norm_squared_token_major,
)
from .exact_core import _nearest_index, _rational
from .low_rank_certified import (
    CertifiedTokenResult, LowRankUnresolved, _add, _down, _exact_coefficient,
    _exact_input, _finite, _multiply_point, _refined_coefficient, _up,
)
from .row_scaled_quantizer import _bits, _weights
from .transformer_backend import _check_runtime


def _power(exponent):
    return Q(1 << exponent) if exponent >= 0 else Q(1, 1 << -exponent)


def _floor_log_two(value):
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    return exponent - (_power(exponent) > value)


def _precision(value):
    if type(value) is not int or not 1 <= value <= 24:
        raise ValueError("significant_bits must be a built-in integer between 1 and 24")
    return value


def _scale_parts(weights, bits, significant_bits):
    half = _bits(bits)
    precision = _precision(significant_bits)
    _weights(weights)
    result = []
    for maximum, minimum in zip(np.max(weights, axis=1), np.min(weights, axis=1)):
        needed = max(Q.from_float(float(maximum)) / (half - 1),
                     -Q.from_float(float(minimum)) / half, Q(0))
        # Half-step boundaries require a representable s/2. Therefore the
        # least admissible positive scale is 2**-1073, including a zero row.
        exponent = max(-1073, _floor_log_two(needed) - precision + 1) if needed else -1073
        ratio = needed / _power(exponent)
        significand = max(1, -(-ratio.numerator // ratio.denominator))
        while significand % 2 == 0:
            significand //= 2
            exponent += 1
        if significand.bit_length() > precision:
            raise ArithmeticError("dyadic scale exceeded its significant-bit bound")
        scale = significand * _power(exponent)
        if scale < needed:
            raise ArithmeticError("dyadic row scale does not cover its base weights")
        try:
            # These extrema cover every grid code and midpoint in magnitude.
            # All products have at most precision+bits significant bits.
            for value in (scale, scale / 2, -half * scale, (half - 1) * scale,
                          Q(1 - 2 * half, 2) * scale, Q(2 * half - 3, 2) * scale):
                converted = float(value)
                if not math.isfinite(converted) or Q.from_float(converted) != value:
                    raise ValueError("dyadic row grids and midpoints must be finite exact binary64 values")
        except OverflowError as exc:
            raise ValueError("dyadic row grid exceeds the finite binary64 range") from exc
        result.append((significand, exponent))
    return tuple(result)


def dyadic_row_scales(weights, bits=4, significant_bits=24):
    """Return the smallest admissible base-only scale for each output row.

    Scales have at most significant_bits significant binary digits.
    Every code and half-step boundary must be exactly representable.
    The returned tuple contains ordinary Python binary64 floats.
    """
    return tuple(float(significand * _power(exponent))
                 for significand, exponent in _scale_parts(weights, bits, significant_bits))


def dyadic_row_scale_metadata(weights, bits=4, significant_bits=24):
    """Return JSON-compatible exact scale metadata without calibration access."""
    return tuple({"significand": significand, "exponent": exponent,
                  "binary64_hex": float(significand * _power(exponent)).hex(),
                  "significant_bits": significand.bit_length()}
                 for significand, exponent in _scale_parts(weights, bits, significant_bits))


def _grid_arrays(scale_values, bits):
    half = _bits(bits)
    scales = np.asarray(scale_values, dtype=np.float64)
    with np.errstate(over="raise", invalid="raise", under="ignore"):
        codes = scales[:, None] * np.arange(-half, half, dtype=np.float64)[None, :]
        boundaries = scales[:, None] * (np.arange(-half, half - 1, dtype=np.float64) + .5)[None, :]
    _finite(codes, boundaries)
    return codes, boundaries


def _check_row_cells(weights, accum_lower, accum_upper, coefficient, error, boundaries):
    value_lower, value_upper = weights.copy(), weights.copy()
    term_lower, term_upper = _multiply_point(accum_lower, accum_upper, coefficient[:, None])
    for lower, upper in zip(term_lower, term_upper):
        value_lower, value_upper = _add(value_lower, value_upper, lower, upper)
    norm_squared = _norm_squared_token_major(accum_lower, accum_upper)
    radius_squared = np.where((norm_squared == 0) | (error == 0),
                              0.0, _up(norm_squared * error))
    _finite(value_lower, value_upper, radius_squared)
    midpoint = value_lower / 2.0 + value_upper / 2.0
    # Each row has distinct exact boundaries. Strict comparison retains the
    # lower-code tie rule. Candidate selection itself is not the certificate.
    indices = np.count_nonzero(midpoint[:, None] > boundaries, axis=1)
    row = np.arange(len(weights))
    lower = boundaries[row, np.maximum(indices - 1, 0)]
    upper = boundaries[row, np.minimum(indices, boundaries.shape[1] - 1)]
    lower_gap, upper_gap = _down(value_lower - lower), _down(upper - value_upper)
    lower_safe = (lower_gap > 0) & (_down(lower_gap * lower_gap) > radius_squared)
    upper_safe = (upper_gap > 0) & (_down(upper_gap * upper_gap) > radius_squared)
    lower_safe |= (radius_squared == 0) & (value_lower > lower)
    upper_safe |= (radius_squared == 0) & (value_upper <= upper)
    return indices, ((indices == 0) | lower_safe) & ((indices == boundaries.shape[1]) | upper_safe)


def quantize_dyadic_rows(weights, features, scale_values=None, *, bits=4, significant_bits=24,
                         ridge, normalization=1, max_exact_rank=64,
                         max_exact_coordinates=16, max_refinement_coordinates=16):
    """Certify row-specific direct grids without normalizing the weights.

    This is a separate target from power-of-two row quantization.
    Supplied scale_values must exactly equal the canonical base-only scales.
    Only finite ordinary binary64 matrices are accepted.
    Inputs must remain unchanged throughout the call.
    """
    _check_runtime()
    half = _bits(bits)
    expected = dyadic_row_scales(weights, bits, significant_bits)
    if scale_values is None:
        supplied = expected
    else:
        try:
            supplied = tuple(scale_values)
        except TypeError as exc:
            raise TypeError("scale_values must be a sequence of Python floats") from exc
        if any(type(value) is not float for value in supplied) or supplied != expected:
            raise ValueError("scale_values must equal the canonical base-only dyadic row scales")
    if type(features) is not np.ndarray or features.dtype != np.float64 or features.ndim != 2:
        raise TypeError("features must be a binary64 NumPy matrix")
    if not np.all(np.isfinite(features)):
        raise ValueError("features must contain finite values")
    if weights.shape[1] != features.shape[0]:
        raise ValueError("weight width and feature width must agree")
    for name, value in (("max_exact_rank", max_exact_rank),
                        ("max_exact_coordinates", max_exact_coordinates),
                        ("max_refinement_coordinates", max_refinement_coordinates)):
        if type(value) is not int or value < 0:
            raise ValueError(f"{name} must be a nonnegative built-in integer")
    lam, norm = _rational(ridge, "ridge"), _rational(normalization, "normalization")
    if lam <= 0 or norm <= 0:
        raise ValueError("ridge and normalization must be positive")
    tiny = np.float64(np.finfo(np.float64).smallest_subnormal)
    if tiny == 0 or tiny * np.float64(1.) != tiny or np.float64(2.) * tiny != tiny + tiny:
        raise LowRankUnresolved("gradual-underflow runtime check failed")
    grid_codes, boundaries = _grid_arrays(supplied, bits)
    row_indices = np.arange(weights.shape[0])
    exact_grids = {}
    with np.errstate(over="ignore", invalid="ignore", under="ignore", divide="ignore"):
        coefficients, errors = _coefficient_enclosures(features, lam * norm)
        rows, width = weights.shape
        rank = features.shape[1]
        accum_lower, accum_upper = np.zeros((rank, rows)), np.zeros((rank, rows))
        codes = np.empty_like(weights)
        exact_decisions, exact_coordinates, refined_coordinates = 0, [], []
        for i in range(width):
            indices, safe = _check_row_cells(
                weights[:, i], accum_lower, accum_upper, coefficients[i], errors[i], boundaries)
            bad = np.flatnonzero(~safe)
            if len(bad) and len(refined_coordinates) < max_refinement_coordinates:
                refined_coordinates.append(i)
                try:
                    refined, refined_error = _refined_coefficient(features, i, lam * norm)
                    refined_indices, refined_safe = _check_row_cells(
                        weights[:, i], accum_lower, accum_upper, refined, refined_error, boundaries)
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
                    if row not in exact_grids:
                        scale = Q.from_float(supplied[row])
                        exact_grids[row] = tuple(code * scale for code in range(-half, half))
                    value = _exact_input(weights, features, codes, row, i, coefficient)
                    indices[row] = _nearest_index(value, exact_grids[row])
                exact_decisions += len(bad)
            codes[:, i] = grid_codes[row_indices, indices]
            accum_lower, accum_upper = _advance_accumulator(
                accum_lower, accum_upper, weights[:, i], codes[:, i], features[i])
            _finite(accum_lower, accum_upper)
    codes.flags.writeable = False
    return CertifiedTokenResult(codes, weights.size - exact_decisions, exact_decisions,
                                tuple(exact_coordinates), tuple(refined_coordinates), float(np.max(errors)))
