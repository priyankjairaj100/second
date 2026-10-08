"""Exact reference semantics for a fixed-grid sequential quantizer.

This module is a small mathematical reference, not a language-model repair
service.  All numerical inputs must be ``int`` or ``fractions.Fraction``;
floats (including accidentally supplied floating-point eigenvalue estimates)
are rejected.  Booleans are also rejected as numerical inputs.  Fraction
arithmetic has growing bit cost: the stated operation counts are not latency
or fixed-word complexity claims.

Contract
--------
* A symmetric positive-definite rational covariance H, rational base weights,
  fixed coordinate order, and one fixed finite rational grid per coordinate.
* Nearest-grid rounding, saturating at the endpoint codes.  An exact midpoint
  is rounded to the LOWER code.  Grids do not change after deletion.
* Reverse LDL: H = L.T diag(t) L, with unit lower-triangular L.  Put
  B = I - L and g_i = 1/t_i.  For a row, process coordinates from left to
  right using v_i = w_i - sum_{h<i} B_ih (w_h-q_h).
* ``certify_relative_enclosure`` takes a CALLER-CERTIFIED enclosure
  a Hbar <= Htrue <= b Hbar in Loewner order.  It verifies arithmetic and
  decision inequalities, NOT the truth of that spectral enclosure.

The certificate proves equality to the mathematical quantizer just defined,
not to an unrelated floating-point Gram/Cholesky program.  The theorem gives
|vtrue_i-vbar_i|^2 <= ((b-a)^2/(4ab)) g_i E_i conditional on identical
earlier codes, where E_i = sum_{h<i}(vbar_h-q_h)^2/g_h.  Induction then
certifies the whole candidate.  Zero displacement, midpoint ties, and the
one-sided cells at saturation are handled explicitly; no square roots or
numerical tolerance tests are used.

Dense factorization costs O(d^3) rational arithmetic operations, and the
quantizer and certificate together cost O(p d^2) for p rows.  The module
does not construct authenticated inputs, bound activation transport, perform
record replay, certify a neural-network evaluator, maintain canonical
multi-request state, or make a full-model or LLVM/PyTorch speedup claim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Iterable, Sequence, Union


Scalar = Union[int, Fraction]
Vector = tuple[Fraction, ...]
Matrix = tuple[Vector, ...]
ZERO = Fraction(0)
ONE = Fraction(1)


def _rational(value: Scalar, name: str) -> Fraction:
    """Accept only exact built-in integers or Fraction values."""
    if type(value) is int:
        return Fraction(value)
    if isinstance(value, Fraction):
        return value
    raise TypeError(f"{name} must be int or Fraction, not {type(value).__name__}")


def _matrix(values: Sequence[Sequence[Scalar]], name: str) -> Matrix:
    rows = tuple(
        tuple(_rational(x, f"{name}[{i}][{j}]") for j, x in enumerate(row))
        for i, row in enumerate(values)
    )
    if not rows or not rows[0]:
        raise ValueError(f"{name} must have at least one row and column")
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError(f"{name} must be rectangular")
    return rows


def _grids(values: Sequence[Sequence[Scalar]], width: int) -> tuple[Vector, ...]:
    grids = tuple(
        tuple(_rational(x, f"grids[{i}][{j}]") for j, x in enumerate(grid))
        for i, grid in enumerate(values)
    )
    if len(grids) != width:
        raise ValueError("supply exactly one grid per weight coordinate")
    for grid in grids:
        if not grid:
            raise ValueError("each grid must contain at least one code")
        if any(left >= right for left, right in zip(grid, grid[1:])):
            raise ValueError("each grid must be strictly increasing")
    return grids


@dataclass(frozen=True)
class ReverseLDL:
    """Exact factors satisfying H = L.T diag(t) L and g = 1/t."""

    L: Matrix
    t: Vector
    B: Matrix
    g: Vector


def reverse_ldl(covariance: Sequence[Sequence[Scalar]]) -> ReverseLDL:
    """Factor a rational SPD matrix by bottom-right Schur elimination.

    A nonpositive exact pivot raises ValueError; no diagonal jitter is added.
    Symmetry is checked exactly.  The factorization itself is an exact SPD
    check for this rational matrix, not a check of another claimed target.
    """
    h = _matrix(covariance, "covariance")
    d = len(h)
    if any(len(row) != d for row in h):
        raise ValueError("covariance must be square")
    if any(h[i][j] != h[j][i] for i in range(d) for j in range(i)):
        raise ValueError("covariance must be exactly symmetric")
    a = [list(row) for row in h]
    lower = [[ONE if i == j else ZERO for j in range(d)] for i in range(d)]
    pivots = [ZERO for _ in range(d)]
    for k in range(d - 1, -1, -1):
        pivot = a[k][k]
        if pivot <= 0:
            raise ValueError("covariance is not positive definite")
        pivots[k] = pivot
        for i in range(k):
            lower[k][i] = a[k][i] / pivot
        for i in range(k):
            for j in range(i + 1):
                entry = a[i][j] - a[k][i] * a[k][j] / pivot
                a[i][j] = entry
                a[j][i] = entry
    lower_tuple = tuple(tuple(row) for row in lower)
    b = tuple(
        tuple(-lower[i][j] if j < i else ZERO for j in range(d))
        for i in range(d)
    )
    t = tuple(pivots)
    return ReverseLDL(lower_tuple, t, b, tuple(ONE / x for x in t))


def _nearest_index(value: Fraction, grid: Vector) -> int:
    """Nearest code; sorted-index secondary key fixes midpoint ties lower."""
    return min(range(len(grid)), key=lambda j: (abs(value - grid[j]), j))


@dataclass(frozen=True)
class RowTrace:
    codes: Vector
    code_indices: tuple[int, ...]
    inputs: Vector
    # Energy BEFORE the decision at this coordinate.
    prefix_energy: Vector


@dataclass(frozen=True)
class OracleResult:
    """The exact surrogate output and its complete decision trace."""

    factors: ReverseLDL
    grids: tuple[Vector, ...]
    rows: tuple[RowTrace, ...]

    @property
    def codes(self) -> Matrix:
        return tuple(row.codes for row in self.rows)


def sequential_oracle(
    weights: Sequence[Sequence[Scalar]],
    covariance: Sequence[Sequence[Scalar]],
    grids: Sequence[Sequence[Scalar]],
) -> OracleResult:
    """Run the declared exact recurrence, with no repair or approximation.

    Grid-search cost is O(p d m) for maximum grid size m, in addition to
    O(d^3+p d^2) arithmetic; for a fixed finite bit grid m is constant.
    No existing candidate is assumed correct.
    """
    w = _matrix(weights, "weights")
    factors = reverse_ldl(covariance)
    d = len(factors.g)
    if len(w[0]) != d:
        raise ValueError("weight width must equal covariance dimension")
    fixed_grids = _grids(grids, d)
    traces = []
    for row in w:
        codes: list[Fraction] = []
        indices: list[int] = []
        inputs: list[Fraction] = []
        energies: list[Fraction] = []
        energy = ZERO
        for i in range(d):
            value = row[i] - sum(
                (factors.B[i][h] * (row[h] - codes[h]) for h in range(i)),
                ZERO,
            )
            index = _nearest_index(value, fixed_grids[i])
            code = fixed_grids[i][index]
            energies.append(energy)
            inputs.append(value)
            codes.append(code)
            indices.append(index)
            energy += (value - code) ** 2 / factors.g[i]
        traces.append(RowTrace(tuple(codes), tuple(indices), tuple(inputs), tuple(energies)))
    return OracleResult(factors, fixed_grids, tuple(traces))


@dataclass(frozen=True)
class CellCheck:
    """One local check, conditional on the earlier candidate codes matching."""

    row: int
    coordinate: int
    accepted: bool
    radius_squared: Fraction
    # None is an infinite endpoint.  The actual cell is (lower, upper].
    lower: Fraction | None
    upper: Fraction | None
    reason: str


@dataclass(frozen=True)
class ConditionalCertificate:
    """Accepted means conditional on the UNVERIFIED caller spectral premise.

    ``candidate`` is always available, including on abstention.  On
    abstention it must not be installed as a certified target.  Never read
    ``accepted=True`` as a verification of the supplied a,b enclosure.
    """

    accepted: bool
    candidate: OracleResult
    lower_scale: Fraction
    upper_scale: Fraction
    kappa_squared: Fraction
    checks: tuple[CellCheck, ...]
    spectral_premise_verified_by_module: bool = field(default=False, init=False)


def certify_relative_enclosure(
    weights: Sequence[Sequence[Scalar]],
    surrogate_covariance: Sequence[Sequence[Scalar]],
    grids: Sequence[Sequence[Scalar]],
    lower_scale: Scalar,
    upper_scale: Scalar,
) -> ConditionalCertificate:
    """Certify the surrogate codes for every Htrue in [a Hbar, b Hbar].

    The caller must independently and rigorously establish the Loewner
    enclosure for the intended target covariance.  This function cannot
    inspect Htrue.  It rejects invalid scalar bounds but cannot detect a
    false spectral assertion with syntactically valid bounds.

    Positive-radius checks use strict inequalities at BOTH finite cell
    boundaries, a conservative rule even at the inclusive upper boundary.
    If the proved radius is zero, the exact old input and its deterministic
    rounding are preserved, including a midpoint tie.  A singleton grid has
    an unbounded cell and always passes.  No square root is computed.
    """
    a = _rational(lower_scale, "lower_scale")
    b = _rational(upper_scale, "upper_scale")
    if not ZERO < a <= b:
        raise ValueError("the caller-certified scales must satisfy 0 < a <= b")
    candidate = sequential_oracle(weights, surrogate_covariance, grids)
    kappa_squared = (b - a) ** 2 / (4 * a * b)
    checks = []
    for row_number, trace in enumerate(candidate.rows):
        for i, value in enumerate(trace.inputs):
            grid = candidate.grids[i]
            index = trace.code_indices[i]
            lower = (grid[index - 1] + grid[index]) / 2 if index else None
            upper = (grid[index] + grid[index + 1]) / 2 if index + 1 < len(grid) else None
            radius_squared = kappa_squared * candidate.factors.g[i] * trace.prefix_energy[i]
            if radius_squared == ZERO:
                accepted = True
                reason = "proved zero displacement (ties preserve lower-code rounding)"
            else:
                lower_safe = lower is None or (
                    value > lower and radius_squared < (value - lower) ** 2
                )
                upper_safe = upper is None or (
                    value < upper and radius_squared < (upper - value) ** 2
                )
                accepted = lower_safe and upper_safe
                reason = "strict cell containment" if accepted else "abstain: cell containment unresolved"
            checks.append(CellCheck(row_number, i, accepted, radius_squared, lower, upper, reason))
    return ConditionalCertificate(
        all(check.accepted for check in checks), candidate, a, b,
        kappa_squared, tuple(checks),
    )


@dataclass(frozen=True)
class DeletionEnclosure:
    """A derived interval, conditional on all supplied Loewner premises."""

    lower_scale: Fraction
    upper_scale: Fraction
    positive_definiteness_proved_conditionally: bool
    kappa_squared: Fraction | None
    spectral_premise_verified_by_module: bool = field(default=False, init=False)


def deletion_spectral_enclosure(
    record_bounds: Iterable[tuple[Scalar, Scalar]],
    *,
    base_lower_scale: Scalar = 1,
    base_upper_scale: Scalar = 1,
) -> DeletionEnclosure:
    """Sum per-deleted-record generalized spectral bounds, not trace bounds.

    Caller premises, all relative to the SAME SPD Hbar:
      base_a Hbar <= Hbase <= base_b Hbar;
      lo_j Hbar <= Delta_j <= hi_j Hbar, with Delta_j PSD.

    Then Hret = Hbase - sum_j Delta_j has enclosure
      a Hbar <= Hret <= b Hbar,
      a = base_a - sum_j hi_j, b = base_b - sum_j lo_j.

    Setting base_a=base_b=1 selects Hbase=Hbar.  Offsetting both spectral
    endpoints can substantially improve the scale-invariant shape bound
    kappa^2=(b-a)^2/(4ab), as compared with ignoring lower PSD bounds.
    This routine validates only rational scalar ordering.  It does NOT
    compute or validate generalized eigenvalue bounds or disjointness of
    record contributions.  Duplicate IDs must be rejected by the caller.

    If a<=0, the routine abstains from proving positive definiteness and
    returns kappa_squared=None.  This does not prove Hret is indefinite.
    """
    base_a = _rational(base_lower_scale, "base_lower_scale")
    base_b = _rational(base_upper_scale, "base_upper_scale")
    if not ZERO < base_a <= base_b:
        raise ValueError("base scales must satisfy 0 < base_lower_scale <= base_upper_scale")
    lower_sum = ZERO
    upper_sum = ZERO
    for j, pair in enumerate(record_bounds):
        if len(pair) != 2:
            raise ValueError("each record bound must be a (lower, upper) pair")
        lo = _rational(pair[0], f"record_bounds[{j}].lower")
        hi = _rational(pair[1], f"record_bounds[{j}].upper")
        if not ZERO <= lo <= hi:
            raise ValueError("record bounds must satisfy 0 <= lower <= upper")
        lower_sum += lo
        upper_sum += hi
    a = base_a - upper_sum
    b = base_b - lower_sum
    positive = a > ZERO
    kappa_squared = (b - a) ** 2 / (4 * a * b) if positive else None
    return DeletionEnclosure(a, b, positive, kappa_squared)


__all__ = [
    "ReverseLDL", "RowTrace", "OracleResult", "CellCheck",
    "ConditionalCertificate", "DeletionEnclosure", "reverse_ldl",
    "sequential_oracle", "certify_relative_enclosure",
    "deletion_spectral_enclosure",
]
