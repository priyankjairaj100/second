"""Exact sparse code-change injection once the TRUE target factor is available.

This implements the recurrence, not a way to obtain the true target metric.
``target_B`` must already be the desired target's strictly lower factor.
The old trace is checked by default. An external provider may bound
``b_i = -sum_h (B'_ih-B_ih)(w_h-q_h)``. Provider bounds are caller premises
unless ``verify_envelopes=True``; the result labels this distinction.

Ignoring grid size, factor acquisition, old-trace validation and envelope
acquisition, arithmetic costs O(p*d + (s+r)*d), for s changed codes and r
ambiguous decisions. Dense factor validation adds O(d^2) reads; default old
trace checking costs O(p*d^2). Verifying every envelope also costs O(p*d^2).
Provider work is not assumed cheap. Fraction bit complexity is unbounded.
No latency claim follows from the operation counters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Callable, Sequence

from .exact_core import (
    Matrix, OracleResult, Scalar, Vector, ZERO, _grids, _matrix,
    _nearest_index, _rational,
)

EnvelopeProvider = Callable[[int, int], tuple[Scalar, Scalar] | None]


@dataclass(frozen=True)
class SparseWork:
    """Exact arithmetic term counts; provider internals are excluded."""

    decisions: int
    changed_codes: int
    accepted_envelopes: int
    exact_fallbacks: int
    old_trace_dot_terms: int
    envelope_verification_terms: int
    exact_fallback_terms: int
    injection_terms: int
    provider_calls: int


@dataclass(frozen=True)
class SparseRepairResult:
    codes: Matrix
    # Closed intervals containing the actual target conditional input,
    # conditional on any accepted unverified envelopes being sound.
    input_intervals: tuple[tuple[tuple[Fraction, Fraction], ...], ...]
    work: SparseWork
    old_trace_verified: bool
    # True means no accepted external interval was left unchecked.
    used_envelopes_verified_by_module: bool
    # This routine cannot prove that a supplied B is a particular model's B.
    target_provenance_verified_by_module: bool = field(default=False, init=False)


def _strict_lower(values: Sequence[Sequence[Scalar]], width: int, name: str) -> Matrix:
    matrix = _matrix(values, name)
    if len(matrix) != width or any(len(row) != width for row in matrix):
        raise ValueError(f"{name} must have shape ({width}, {width})")
    if any(matrix[i][j] != 0 for i in range(width) for j in range(i, width)):
        raise ValueError(f"{name} must be strictly lower triangular")
    return matrix


def _cell_containing_interval(lower: Fraction, upper: Fraction, grid: Vector) -> int | None:
    """Cells are (left midpoint, right midpoint], including saturation."""
    index = _nearest_index(lower, grid)
    if index and lower <= (grid[index - 1] + grid[index]) / 2:
        return None
    if index + 1 < len(grid) and upper > (grid[index] + grid[index + 1]) / 2:
        return None
    return index


def sparse_repair(
    weights: Sequence[Sequence[Scalar]],
    old: OracleResult,
    target_B: Sequence[Sequence[Scalar]],
    envelope_provider: EnvelopeProvider | None = None,
    *,
    validate_old_trace: bool = True,
    verify_envelopes: bool = False,
) -> SparseRepairResult:
    """Repair all rows by injecting changed codes into later decisions.

    A missing or ambiguous interval triggers an exact target dot product.
    An interval can certify a *different* code from the old code. Every
    changed code is propagated through the TRUE B', not through old B.

    ``validate_old_trace=False`` is an explicit trusted-trace contract.
    ``verify_envelopes=False`` avoids dense checking but cannot validate a
    dishonest or mistaken interval. The return value makes both premises
    visible. A checked false envelope raises ValueError before returning.
    Boolean and floating numerical inputs are rejected, including bounds.
    """
    if type(validate_old_trace) is not bool or type(verify_envelopes) is not bool:
        raise TypeError("validation flags must be bool")
    w = _matrix(weights, "weights")
    p, d = len(w), len(w[0])
    old_b = _strict_lower(old.factors.B, d, "old.B")
    new_b = _strict_lower(target_B, d, "target_B")
    grids = _grids(old.grids, d)
    if len(old.rows) != p:
        raise ValueError("old trace row count must match weights")
    prior_codes, prior_inputs = [], []
    trace_terms = 0
    for row_index, trace in enumerate(old.rows):
        q = tuple(_rational(x, "old code") for x in trace.codes)
        v = tuple(_rational(x, "old input") for x in trace.inputs)
        if len(q) != d or len(v) != d:
            raise ValueError("old trace width must match weights")
        if any(q[i] not in grids[i] for i in range(d)):
            raise ValueError("old code must belong to its fixed grid")
        if validate_old_trace:
            for i in range(d):
                actual = w[row_index][i] - sum(
                    (old_b[i][h] * (w[row_index][h] - q[h]) for h in range(i)), ZERO
                )
                trace_terms += i
                if actual != v[i] or grids[i][_nearest_index(actual, grids[i])] != q[i]:
                    raise ValueError("old trace does not satisfy the declared recurrence")
        prior_codes.append(q)
        prior_inputs.append(v)

    output, intervals = [], []
    changed = accepted = fallbacks = verification_terms = fallback_terms = injections = calls = 0
    for row_index, row in enumerate(w):
        old_q, old_v = prior_codes[row_index], prior_inputs[row_index]
        injection = [ZERO] * d
        q_new, row_intervals = [], []
        for i in range(d):
            bound = None
            if envelope_provider is not None:
                calls += 1
                bound = envelope_provider(row_index, i)
            exact_b = None
            index = None
            if bound is not None:
                if len(bound) != 2:
                    raise ValueError("an envelope must have exactly two endpoints")
                low_b = _rational(bound[0], "envelope lower")
                high_b = _rational(bound[1], "envelope upper")
                if low_b > high_b:
                    raise ValueError("envelope lower must not exceed upper")
                if verify_envelopes:
                    exact_b = -sum(
                        ((new_b[i][h] - old_b[i][h]) * (row[h] - old_q[h])
                         for h in range(i)), ZERO
                    )
                    verification_terms += i
                    if not low_b <= exact_b <= high_b:
                        raise ValueError("supplied envelope excludes the exact factor displacement")
                low = old_v[i] + injection[i] + low_b
                high = old_v[i] + injection[i] + high_b
                index = _cell_containing_interval(low, high, grids[i])
            if index is None:
                fallbacks += 1
                if exact_b is None:
                    value = row[i] - sum(
                        (new_b[i][h] * (row[h] - q_new[h]) for h in range(i)), ZERO
                    )
                    fallback_terms += i
                else:
                    value = old_v[i] + injection[i] + exact_b
                low = high = value
                index = _nearest_index(value, grids[i])
            else:
                accepted += 1
            code = grids[i][index]
            q_new.append(code)
            row_intervals.append((low, high))
            difference = code - old_q[i]
            if difference:
                changed += 1
                for j in range(i + 1, d):
                    injection[j] += new_b[j][i] * difference
                    injections += 1
        output.append(tuple(q_new))
        intervals.append(tuple(row_intervals))
    return SparseRepairResult(
        tuple(output), tuple(intervals),
        SparseWork(p * d, changed, accepted, fallbacks, trace_terms,
                   verification_terms, fallback_terms, injections, calls),
        validate_old_trace, verify_envelopes or accepted == 0,
    )
