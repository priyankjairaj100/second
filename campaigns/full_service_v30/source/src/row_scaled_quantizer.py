"""A new prospective target: fixed power-of-two grids per output row.

This target differs from the original per-input-coordinate grid target.
Scales depend only on original base weights. They stay fixed after deletion.
No quality improvement follows from this definition alone.

For row scale a>0, write w=a*w' and q=a*q'. Reverse-LDL coefficients
are independent of w. Induction gives v=a*v' at each coordinate. Thus
nearest rounding on a*[-half,...,half-1] equals a times integer-grid rounding.
Positive scaling preserves the lower-code tie rule and endpoint saturation.
This proves the normalization wrapper exactly matches the row-specific target.

The wrapper rejects any normalization or restored code that binary64 cannot
represent exactly. It does not silently underflow, clip, or change a scale.
Inputs must be ordinary binary64 NumPy arrays and remain unchanged during calls.
"""
from __future__ import annotations

from dataclasses import replace
from fractions import Fraction as Q
import math

import numpy as np

from .low_rank_certified import CertifiedTokenResult, certified_token_codes
from .transformer_backend import _check_runtime


def _bits(bits):
    if type(bits) is not int or not 2 <= bits <= 8:
        raise ValueError("bits must be a built-in integer between 2 and 8")
    return 1 << (bits - 1)


def _weights(weights):
    if (type(weights) is not np.ndarray or weights.dtype != np.float64
            or weights.ndim != 2 or not weights.shape[0] or not weights.shape[1]):
        raise TypeError("weights must be a nonempty ordinary binary64 NumPy matrix")
    if not np.all(np.isfinite(weights)):
        raise ValueError("weights must be finite")


def _power(exponent):
    return Q(1 << exponent) if exponent >= 0 else Q(1, 1 << -exponent)


def _ceil_log_two(value):
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    return exponent + (_power(exponent) < value)


def row_scale_exponents(weights: np.ndarray, bits: int = 4) -> tuple[int, ...]:
    """Choose the smallest representable power-of-two grid covering each row.

    The integer grid is [-2**(bits-1), ..., 2**(bits-1)-1].
    A zero row uses exponent zero. Scales cannot be smaller than 2**-1074.
    The complete grid, including unused endpoints, must remain finite.
    """
    half = _bits(bits)
    _weights(weights)
    maxima = np.max(weights, axis=1)
    minima = np.min(weights, axis=1)
    exponents = []
    for maximum, minimum in zip(maxima, minima):
        needed = max(Q.from_float(float(maximum)) / (half - 1),
                     -Q.from_float(float(minimum)) / half, Q(0))
        exponent = max(-1074, _ceil_log_two(needed)) if needed else 0
        # The negative endpoint has magnitude 2**(exponent+bits-1).
        if exponent + bits - 1 > 1023:
            raise ValueError("row grid endpoints exceed the finite binary64 range")
        scale = _power(exponent)
        if Q.from_float(float(minimum)) < -half * scale or Q.from_float(float(maximum)) > (half - 1) * scale:
            raise ArithmeticError("row scale does not cover the base weights")
        exponents.append(exponent)
    return tuple(exponents)


def quantize_row_scaled(weights: np.ndarray, features: np.ndarray, exponents,
                        *, bits: int = 4, ridge, normalization=1,
                        max_exact_rank=64, max_exact_coordinates=16,
                        max_refinement_coordinates=16) -> CertifiedTokenResult:
    """Run the declared row target through exact binary64 normalization.

    Supplied exponents must equal the canonical base-only exponents.
    All calibration-independent scale choices therefore remain reproducible.
    Diagnostics describe the normalized solver; returned codes use original units.
    """
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
    # Scaling upward is exact unless it overflows. Scaling downward can lose
    # bits only at underflow. Its upward inverse then exposes every lost bit.
    if not np.all(np.isfinite(normalized)) or not np.array_equal(recovered, weights):
        raise ValueError("row normalization is not exactly representable in binary64")
    if np.any(normalized < -half) or np.any(normalized > half - 1):
        raise ArithmeticError("normalized base weights fall outside the integer grid")
    grid = tuple(range(-half, half))
    result = certified_token_codes(
        normalized, features, (grid,) * weights.shape[1],
        ridge=ridge, normalization=normalization,
        max_exact_rank=max_exact_rank, max_exact_coordinates=max_exact_coordinates,
        max_refinement_coordinates=max_refinement_coordinates)
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        restored = np.ldexp(result.codes, shifts)
        recovered_codes = np.ldexp(restored, -shifts)
    if not np.all(np.isfinite(restored)) or not np.array_equal(recovered_codes, result.codes):
        raise ValueError("scaled quantized codes are not exactly representable in binary64")
    restored.flags.writeable = False
    return replace(result, codes=restored)
