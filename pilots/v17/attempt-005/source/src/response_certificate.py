"""Exact contraction of response/error moments into a CONDITIONAL Gram bound.

The companion scalar response index encodes record descriptors
b_j=(nu_j+e_j0,e_j1,...,e_jr,H_j,L_j). Its response query uses
(1,abs(a_1),...,abs(a_r),||a||_2^2/2,upper_bound(||u||)).
The resulting squared sum bounds feature error only when an external proof
establishes every descriptor, chart-domain condition and numerical premise.
This module verifies exact arithmetic, compatible IDs and outward rounding;
it does not prove a Taylor remainder or audit a neural-network evaluator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from math import isqrt
from typing import Sequence

from .exact_core import Matrix, Scalar, ZERO, _rational
from .response_moments import ResponseIndex


def dyadic_sqrt_upper(value: Scalar, precision_bits: int = 32) -> Fraction:
    """Least multiple of 2**(-bits) whose square is >= exact value.

    Uses integer arithmetic only. Result minus sqrt(value) is strictly less
    than one grid unit unless value itself is exactly on the dyadic grid,
    where the result is exact. No floating-point roundoff enters this bound.
    """
    x = _rational(value, "sqrt argument")
    if x < 0:
        raise ValueError("sqrt argument must be nonnegative")
    if type(precision_bits) is not int:
        raise TypeError("precision_bits must be a built-in integer")
    if precision_bits < 0:
        raise ValueError("precision_bits must be nonnegative")
    scaled_numerator = x.numerator << (2 * precision_bits)
    integer = isqrt(scaled_numerator // x.denominator)
    if integer * integer * x.denominator < scaled_numerator:
        integer += 1
    return Fraction(integer, 1 << precision_bits)


@dataclass(frozen=True)
class ConditionalResponseGramBound:
    raw_surrogate_gram: Matrix
    normalization: Fraction
    squared_surrogate_frobenius_norm_normalized: Fraction
    squared_feature_error_bound_normalized: Fraction
    # ||(X X.T-Z Z.T)/M0||_2 <= delta, conditional on descriptor premises.
    normalized_absolute_gram_error: Fraction
    # Same inequality before division by M0; convenient for service hooks.
    raw_absolute_gram_error: Fraction
    response_manifest: str
    descriptor_manifest: str
    retained_ids: tuple[str, ...]
    descriptor_premises_verified_by_module: bool = field(default=False, init=False)


def response_error_squared(
    descriptors: ResponseIndex,
    coefficients: Sequence[Scalar],
    normalization: Scalar,
    unrepresented_parameter_norm: Scalar = 0,
) -> Fraction:
    """Contract nonnegative intrinsic error descriptors, conditional on proof.

    Returns (1/M0) sum_j (b_j dot v)^2. The caller separately binds these
    retained descriptors to the target feature records, domain and prefix.
    """
    m0 = _rational(normalization, "normalization")
    residual = _rational(unrepresented_parameter_norm, "residual norm bound")
    a = tuple(_rational(x, "response coefficient") for x in coefficients)
    if m0 <= 0 or residual < 0:
        raise ValueError("normalization must be positive and residual bound nonnegative")
    if descriptors.basis.rows != 1 or descriptors.basis.terms != len(a) + 3:
        raise ValueError("descriptor index must have one row and r+3 terms")
    if any(record.columns != 1 for record in descriptors.records):
        raise ValueError("descriptor records must each have exactly one scalar column")
    if any(matrix[0][0] < 0 for matrix in descriptors.cross_moments):
        raise ValueError("descriptor moments must be nonnegative")
    query = tuple(abs(x) for x in a) + (sum((x * x for x in a), ZERO) / 2, residual)
    return descriptors.squared_frobenius_norm(query) / m0


def response_gram_enclosure(
    response: ResponseIndex,
    descriptors: ResponseIndex,
    coefficients: Sequence[Scalar],
    normalization: Scalar,
    unrepresented_parameter_norm: Scalar = 0,
    *,
    sqrt_precision_bits: int = 32,
) -> ConditionalResponseGramBound:
    """Contract intrinsic moments and bound the unwhitened Gram difference.

    Each descriptor record must have one scalar column per record and
    nonnegative descriptors with the SAME record/source identities as the
    feature index. All descriptor cross moments must be nonnegative, a
    necessary structural check rather than a proof of their semantics.

    Bound: e2=(1/M0) sum_j (b_j dot v)^2, z2=tr(ZZ.T)/M0,
    delta=2*upper_sqrt(z2*e2)+e2. Given sound feature error descriptors,
    ||(XX.T-ZZ.T)/M0||_2<=delta. Every mixed error term is retained.
    Fixed-ridge metric enclosures may use delta/lambda downstream; damping
    or any data-dependent branch must additionally be accounted for there.
    """
    m0 = _rational(normalization, "normalization")
    residual = _rational(unrepresented_parameter_norm, "residual norm bound")
    if m0 <= 0 or residual < 0:
        raise ValueError("normalization must be positive and residual bound nonnegative")
    a = tuple(_rational(x, "response coefficient") for x in coefficients)
    if len(a) != response.basis.terms - 1:
        raise ValueError("one coefficient is required for each response direction")
    feature_identity = tuple((record.record_id, record.source_digest) for record in response.records)
    descriptor_identity = tuple((record.record_id, record.source_digest) for record in descriptors.records)
    if feature_identity != descriptor_identity:
        raise ValueError("response and descriptor retained identities must match")
    e2 = response_error_squared(descriptors, a, m0, residual)
    z2 = response.squared_frobenius_norm(a) / m0
    if e2 < 0 or z2 < 0:
        raise ValueError("response/descriptor moments do not define nonnegative squared norms")
    delta = 2 * dyadic_sqrt_upper(z2 * e2, sqrt_precision_bits) + e2
    return ConditionalResponseGramBound(
        response.gram(a), m0, z2, e2, delta, m0 * delta,
        response.basis.manifest_id, descriptors.basis.manifest_id, response.retained_ids,
    )
