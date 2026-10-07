"""Exact token-space form of the declared reverse-LDL quantizer.

This module stores no width-by-width matrix. It remains a rational reference.
Arithmetic counts do not bound growing integer sizes or wall time.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction as Q
from typing import Sequence

from .exact_core import RowTrace, _grids, _matrix, _nearest_index, _rational


@dataclass(frozen=True)
class TokenFactors:
    """L[i,h] = dot(coefficients[i], features[h]) for h < i."""

    features: tuple[tuple[Q, ...], ...]
    coefficients: tuple[tuple[Q, ...], ...]
    pivots: tuple[Q, ...]
    ridge: Q
    normalization: Q

    @property
    def g(self):
        return tuple(1 / value for value in self.pivots)


@dataclass(frozen=True)
class TokenOracleResult:
    factors: TokenFactors
    grids: tuple[tuple[Q, ...], ...]
    rows: tuple[RowTrace, ...]

    @property
    def codes(self):
        return tuple(row.codes for row in self.rows)


def token_reverse_ldl(features, *, ridge, normalization=1):
    """Factor H = ridge I + features features.T / normalization exactly.

    Rows represent weight coordinates. Columns represent calibration tokens.
    Empty columns represent complete calibration deletion. Ridge must be positive.
    Work is O(d T²); stored factors require O(d T + T²) rational entries.
    """
    lam = _rational(ridge, "ridge")
    norm = _rational(normalization, "normalization")
    if lam <= 0 or norm <= 0:
        raise ValueError("ridge and normalization must be positive")
    z = tuple(tuple(_rational(x, "features") for x in row) for row in features)
    if not z or any(len(row) != len(z[0]) for row in z):
        raise ValueError("features must have positive width and equal token counts")
    d, rank = len(z), len(z[0])
    c = [[Q(i == j) / norm for j in range(rank)] for i in range(rank)]
    coeff = [()] * d
    pivots = [Q(0)] * d
    for i in range(d - 1, -1, -1):
        v = tuple(sum((c[j][k] * z[i][k] for k in range(rank)), Q(0))
                  for j in range(rank))
        pivot = lam + sum((z[i][j] * v[j] for j in range(rank)), Q(0))
        if pivot <= 0:
            raise ArithmeticError("positive ridge failed exact pivot invariant")
        coeff[i] = tuple(x / pivot for x in v)
        pivots[i] = pivot
        for j in range(rank):
            for k in range(j + 1):
                value = c[j][k] - v[j] * v[k] / pivot
                c[j][k] = c[k][j] = value
    return TokenFactors(z, tuple(coeff), tuple(pivots), lam, norm)


def token_sequential_oracle(weights, features, grids, *, ridge, normalization=1):
    """Return exactly the dense oracle's codes, inputs, and prefix energies."""
    w = _matrix(weights, "weights")
    factors = token_reverse_ldl(features, ridge=ridge, normalization=normalization)
    d = len(factors.features)
    if len(w[0]) != d:
        raise ValueError("weight width and feature width differ")
    fixed = _grids(grids, d)
    rank = len(factors.features[0])
    rows = []
    for row in w:
        accumulator = [Q(0)] * rank
        codes, indices, inputs, energies = [], [], [], []
        energy = Q(0)
        for i in range(d):
            value = row[i] + sum((factors.coefficients[i][k] * accumulator[k]
                                 for k in range(rank)), Q(0))
            index = _nearest_index(value, fixed[i])
            code = fixed[i][index]
            energies.append(energy)
            inputs.append(value)
            indices.append(index)
            codes.append(code)
            energy += (value - code) ** 2 * factors.pivots[i]
            for k in range(rank):
                accumulator[k] += factors.features[i][k] * (row[i] - code)
        rows.append(RowTrace(tuple(codes), tuple(indices), tuple(inputs), tuple(energies)))
    return TokenOracleResult(factors, fixed, tuple(rows))
