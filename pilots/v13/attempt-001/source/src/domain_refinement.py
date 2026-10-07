"""Conditional exact certificates from intersected covariance enclosures.

The caller must prove each enclosure, its common binding, and H >= ridge I.
This module checks exact interval arithmetic and target rounding only. It does
not authenticate the bounds, construct a corpus-independent domain bank, or
alter the canonical deletion state. Keep existing spectral checks first and
OR-compose this route with them; replacing them loses their coverage.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Sequence

from .exact_core import Matrix, Scalar, ZERO, ONE, _matrix, _grids, _rational


@dataclass(frozen=True)
class RationalInterval:
    lo: Fraction
    hi: Fraction

    def __post_init__(self):
        lo = _rational(self.lo, 'interval lower')
        hi = _rational(self.hi, 'interval upper')
        if lo > hi:
            raise ValueError('interval is empty')
        object.__setattr__(self, 'lo', lo)
        object.__setattr__(self, 'hi', hi)

    @classmethod
    def point(cls, value):
        value = _rational(value, 'interval point')
        return cls(value, value)

    def __add__(self, other):
        return RationalInterval(self.lo + other.lo, self.hi + other.hi)

    def __sub__(self, other):
        return RationalInterval(self.lo - other.hi, self.hi - other.lo)

    def __mul__(self, other):
        values = (self.lo * other.lo, self.lo * other.hi,
                  self.hi * other.lo, self.hi * other.hi)
        return RationalInterval(min(values), max(values))

    def square(self):
        upper = max(self.lo * self.lo, self.hi * self.hi)
        lower = ZERO if self.lo <= ZERO <= self.hi else min(self.lo * self.lo, self.hi * self.hi)
        return RationalInterval(lower, upper)

    def divide_positive(self, other):
        if other.lo <= ZERO:
            raise ValueError('interval divisor must be strictly positive')
        return self * RationalInterval(ONE / other.hi, ONE / other.lo)

    def intersect(self, other):
        return RationalInterval(max(self.lo, other.lo), min(self.hi, other.hi))

    def subset_of(self, other):
        return other.lo <= self.lo and self.hi <= other.hi


@dataclass(frozen=True)
class GramBinding:
    """Common identity; caller validates hashes against actual target inputs."""
    target_id: str
    stage_id: str
    prefix_digest: str
    retained_digest: str
    normalization: Fraction

    def __post_init__(self):
        for name in ('target_id', 'stage_id', 'prefix_digest', 'retained_digest'):
            if type(getattr(self, name)) is not str or not getattr(self, name):
                raise ValueError(f'{name} must be a nonempty string')
        for name in ('prefix_digest', 'retained_digest'):
            value = getattr(self, name)
            if len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
                raise ValueError(f'{name} must be a lowercase SHA256 digest')
        value = _rational(self.normalization, 'normalization')
        if value <= ZERO:
            raise ValueError('normalization must be positive')
        object.__setattr__(self, 'normalization', value)


@dataclass(frozen=True)
class GramBox:
    """Entrywise enclosure of the complete normalized covariance, with ridge."""
    binding: GramBinding
    lower: Matrix
    upper: Matrix
    evidence_ids: tuple[str, ...]

    def __post_init__(self):
        if not isinstance(self.binding, GramBinding):
            raise TypeError('a GramBinding is required')
        lower, upper = _matrix(self.lower, 'lower'), _matrix(self.upper, 'upper')
        d = len(lower)
        if len(upper) != d or any(len(row) != d for row in lower + upper):
            raise ValueError('enclosure matrices must be square with equal dimensions')
        for i in range(d):
            for j in range(d):
                if lower[i][j] > upper[i][j]:
                    raise ValueError('covariance enclosure is empty')
                if lower[i][j] != lower[j][i] or upper[i][j] != upper[j][i]:
                    raise ValueError('covariance bounds must be symmetric')
        ids = tuple(self.evidence_ids)
        if not ids or any(type(x) is not str or not x for x in ids):
            raise ValueError('nonempty evidence identities are required')
        object.__setattr__(self, 'lower', lower)
        object.__setattr__(self, 'upper', upper)
        object.__setattr__(self, 'evidence_ids', tuple(sorted(set(ids))))

    @property
    def dimension(self):
        return len(self.lower)

    def intervals(self):
        return tuple(tuple(RationalInterval(lo, hi) for lo, hi in zip(left, right))
                     for left, right in zip(self.lower, self.upper))

    def subset_of(self, other):
        if self.binding != other.binding or self.dimension != other.dimension:
            return False
        return all(other.lower[i][j] <= self.lower[i][j] <= self.upper[i][j] <= other.upper[i][j]
                   for i in range(self.dimension) for j in range(self.dimension))


def spectral_ball_box(binding: GramBinding, center, radius: Scalar, evidence_id: str) -> GramBox:
    """Use |H_ij - center_ij| <= ||H-center||_2 <= radius.

    The center need not be SPD. The actual target must separately satisfy the
    declared ridge floor. No supplied spectral premise is verified here.
    """
    center = _matrix(center, 'center')
    radius = _rational(radius, 'radius')
    if radius < ZERO:
        raise ValueError('radius must be nonnegative')
    return GramBox(binding,
                   tuple(tuple(x - radius for x in row) for row in center),
                   tuple(tuple(x + radius for x in row) for row in center),
                   (evidence_id,))


def signed_loewner_box(binding: GramBinding, center, negative: Scalar,
                       positive: Scalar, evidence_id: str) -> GramBox:
    """Convert -negative I <= H-center <= positive I without lost asymmetry.

    Diagonal bounds retain their separate endpoints. Off-diagonal errors
    have magnitude at most (negative + positive)/2, since shifting the error
    by (positive-negative)I/2 gives that operator-norm radius.
    All quantities use the normalized complete covariance units.
    """
    center = _matrix(center, 'center')
    negative = _rational(negative, 'negative error')
    positive = _rational(positive, 'positive error')
    if negative < ZERO or positive < ZERO:
        raise ValueError('signed error magnitudes must be nonnegative')
    radius = (negative + positive) / 2
    return GramBox(binding,
                   tuple(tuple(x - (negative if i == j else radius) for j, x in enumerate(row))
                         for i, row in enumerate(center)),
                   tuple(tuple(x + (positive if i == j else radius) for j, x in enumerate(row))
                         for i, row in enumerate(center)), (evidence_id,))


def intersect_gram_boxes(boxes: Sequence[GramBox]) -> GramBox:
    """Intersect sound enclosures of ONE target covariance.

    Empty intersections indicate incompatible premises. Never treat them as
    vacuous successful certificates. The caller must abort or discard invalid
    evidence through an independently justified policy.
    """
    boxes = tuple(boxes)
    if not boxes or any(not isinstance(box, GramBox) for box in boxes):
        raise ValueError('at least one GramBox is required')
    first = boxes[0]
    if any(box.binding != first.binding or box.dimension != first.dimension for box in boxes[1:]):
        raise ValueError('all enclosures must bind the same covariance and dimension')
    d = first.dimension
    return GramBox(first.binding,
                   tuple(tuple(max(box.lower[i][j] for box in boxes) for j in range(d)) for i in range(d)),
                   tuple(tuple(min(box.upper[i][j] for box in boxes) for j in range(d)) for i in range(d)),
                   tuple(identity for box in boxes for identity in box.evidence_ids))


@dataclass(frozen=True)
class IntervalCellCheck:
    row: int
    coordinate: int
    input_interval: RationalInterval
    lower_cell: Fraction | None
    upper_cell: Fraction | None
    accepted: bool


@dataclass(frozen=True)
class ConditionalBoxCertificate:
    accepted: bool
    candidate: Matrix
    covariance_box: GramBox
    ridge: Fraction
    lower_factors: tuple[tuple[RationalInterval, ...], ...]
    pivots: tuple[RationalInterval, ...]
    checks: tuple[IntervalCellCheck, ...]
    enclosure_and_ridge_premises_verified_by_module: bool = field(default=False, init=False)


def interval_reverse_ldl(box: GramBox, ridge: Scalar):
    """Enclose reverse LDL for H in box AND H >= ridge I.

    Each true Schur complement has the same ridge floor. Intersect each pivot
    interval with [ridge,infinity) before division. A resulting empty interval
    raises ValueError, never acceptance. This is not an SPD proof for every
    matrix in the entrywise box. Dependency overestimation can remain large.
    """
    if not isinstance(box, GramBox):
        raise TypeError('a GramBox is required')
    ridge = _rational(ridge, 'ridge')
    if ridge <= ZERO:
        raise ValueError('ridge must be strictly positive')
    d = box.dimension
    a = [list(row) for row in box.intervals()]
    point = RationalInterval.point
    lower = [[point(ONE if i == j else ZERO) for j in range(d)] for i in range(d)]
    pivots = [None] * d
    for k in range(d - 1, -1, -1):
        pivot = RationalInterval(max(ridge, a[k][k].lo), a[k][k].hi)
        pivots[k] = pivot
        for i in range(k):
            lower[k][i] = a[k][i].divide_positive(pivot)
        for i in range(k):
            for j in range(i + 1):
                product = a[k][i].square() if i == j else a[k][i] * a[k][j]
                value = a[i][j] - product.divide_positive(pivot)
                a[i][j] = value
                a[j][i] = value
    return tuple(tuple(row) for row in lower), tuple(pivots)


def certify_gram_box(weights, candidate, grids, box: GramBox, ridge: Scalar) -> ConditionalBoxCertificate:
    """Certify a fixed candidate under exact lower-tie rounding.

    Cells are (lower,upper], with missing infinite endpoints at saturation.
    Candidate decisions may come from any source; every row and coordinate
    is checked. On abstention the candidate must not be installed.
    """
    if not isinstance(box, GramBox):
        raise TypeError('a GramBox is required')
    weights, candidate = _matrix(weights, 'weights'), _matrix(candidate, 'candidate')
    if len(weights) != len(candidate) or len(weights[0]) != box.dimension or len(candidate[0]) != box.dimension:
        raise ValueError('weight and candidate dimensions must match covariance')
    fixed_grids = _grids(grids, box.dimension)
    indices = []
    for row in candidate:
        try:
            indices.append(tuple(grid.index(code) for grid, code in zip(fixed_grids, row)))
        except ValueError as exc:
            raise ValueError('each candidate code must belong to its frozen grid') from exc
    ridge = _rational(ridge, 'ridge')
    lower, pivots = interval_reverse_ldl(box, ridge)
    point = RationalInterval.point
    checks = []
    for row_number, (row, codes, selected) in enumerate(zip(weights, candidate, indices)):
        for i, (grid, index) in enumerate(zip(fixed_grids, selected)):
            value = point(row[i])
            for h in range(i):
                value = value + lower[i][h] * point(row[h] - codes[h])
            cell_lo = (grid[index - 1] + grid[index]) / 2 if index else None
            cell_hi = (grid[index] + grid[index + 1]) / 2 if index + 1 < len(grid) else None
            accepted = (cell_lo is None or value.lo > cell_lo) and (cell_hi is None or value.hi <= cell_hi)
            checks.append(IntervalCellCheck(row_number, i, value, cell_lo, cell_hi, accepted))
    return ConditionalBoxCertificate(all(check.accepted for check in checks), candidate, box, ridge,
                                     lower, pivots, tuple(checks))


__all__ = ['RationalInterval', 'GramBinding', 'GramBox', 'spectral_ball_box', 'signed_loewner_box',
           'intersect_gram_boxes', 'interval_reverse_ldl', 'certify_gram_box',
           'ConditionalBoxCertificate', 'IntervalCellCheck']
