"""Deletion-additive linear Gram response with a certified quadratic tail.

For intrinsic jets Z0,Z1,...,Zr this index keeps only C00=Z0 Z0.T,
A_t=Z0 Zt.T+Zt Z0.T and scalar G_st=<Zs,Zt>_F (s,t>=1).
Queries form Slin=C00+sum a_t A_t. The omitted positive-semidefinite
term P=(sum a_t Zt)(sum a_t Zt).T obeys ||P||_2<=tr(P)=a.T G a.
Storage is O(r*d^2+r^2), instead of O(r^2*d^2) full response matrices.

No response-direction independence or Taylor residual is established here:
the immutable basis and descriptor proof are explicit external contracts.
The index is for a proposal and proof, never a substitution of the linear
Gram quantizer for the original sequential target. Failed enclosures abstain.
The implementation stores full symmetric matrices, not packed triangles.
Construction costs O((r+1)d^2*n+r^2*d*n) rational arithmetic per record;
contraction O(r*d^2+r^2); exact rational bit costs and deletion extraction,
digest checks, O(N) immutable metadata rebuilds and serialization are extra.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
import json
from typing import Iterable, Sequence

from .exact_core import Matrix, Scalar, ZERO, _matrix, _rational
from .response_certificate import dyadic_sqrt_upper, response_error_squared
from .response_moments import (
    RecordBinding, ResponseBasis, ResponseIndex, _dump, _encoded_matrix,
    _nonempty_text, _positive_int,
)


def _square(matrix: Sequence[Sequence[Scalar]], size: int, name: str) -> Matrix:
    if size == 0:
        if tuple(matrix):
            raise ValueError(f"{name} must be empty for a zero-direction basis")
        return ()
    exact = _matrix(matrix, name)
    if len(exact) != size or any(len(row) != size for row in exact):
        raise ValueError(f"{name} has the wrong shape")
    if any(exact[i][j] != exact[j][i] for i in range(size) for j in range(i)):
        raise ValueError(f"{name} must be symmetric")
    return exact


def _checked_parts(basis: ResponseBasis, constant: Matrix, first: tuple[Matrix, ...],
                   tangent: Matrix) -> tuple[Matrix, tuple[Matrix, ...], Matrix]:
    if not isinstance(basis, ResponseBasis):
        raise TypeError("basis must be ResponseBasis")
    zero = _square(constant, basis.rows, "constant Gram")
    linear = tuple(_square(x, basis.rows, "first response") for x in first)
    if len(linear) != basis.terms - 1:
        raise ValueError("one first-response matrix is required per direction")
    scalar = _square(tangent, basis.terms - 1, "tangent scalar Gram")
    return zero, linear, scalar


@dataclass(frozen=True)
class LinearRecordMoments:
    basis: ResponseBasis
    record_id: str
    source_digest: str
    columns: int
    constant_gram: Matrix
    first_response: tuple[Matrix, ...]
    tangent_scalar_gram: Matrix

    def __post_init__(self) -> None:
        _nonempty_text(self.record_id, "record_id")
        _nonempty_text(self.source_digest, "source_digest")
        _positive_int(self.columns, "columns")
        constant, linear, tangent = _checked_parts(
            self.basis, self.constant_gram, self.first_response, self.tangent_scalar_gram)
        object.__setattr__(self, "constant_gram", constant)
        object.__setattr__(self, "first_response", linear)
        object.__setattr__(self, "tangent_scalar_gram", tangent)

    def canonical_bytes(self) -> bytes:
        return _dump({"schema": "linear-record-response-v1", "basis": self.basis._payload(),
                      "record_id": self.record_id, "source_digest": self.source_digest,
                      "columns": self.columns, "constant_gram": _encoded_matrix(self.constant_gram),
                      "first_response": [_encoded_matrix(x) for x in self.first_response],
                      "tangent_scalar_gram": _encoded_matrix(self.tangent_scalar_gram)})

    @property
    def payload_digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

    @classmethod
    def from_canonical_bytes(cls, payload: bytes) -> LinearRecordMoments:
        if type(payload) is not bytes:
            raise TypeError("payload must be bytes")
        data = json.loads(payload)
        if not isinstance(data, dict) or data.get("schema") != "linear-record-response-v1":
            raise ValueError("unsupported linear record schema")
        metadata = data["basis"]
        basis = ResponseBasis(metadata["manifest_id"], metadata["rows"], metadata["terms"],
                              metadata["corpus_independent_by_caller_attestation"])

        def matrix(values: object) -> Matrix:
            result = []
            for row in values:
                exact = []
                for pair in row:
                    if not isinstance(pair, list) or len(pair) != 2 or any(type(x) is not int for x in pair):
                        raise TypeError("encoded rationals must be integer pairs")
                    if pair[1] <= 0:
                        raise ValueError("rational denominator must be positive")
                    exact.append(Fraction(pair[0], pair[1]))
                result.append(tuple(exact))
            return tuple(result)

        result = cls(basis, data["record_id"], data["source_digest"], data["columns"],
                     matrix(data["constant_gram"]), tuple(matrix(x) for x in data["first_response"]),
                     matrix(data["tangent_scalar_gram"]))
        if result.canonical_bytes() != payload:
            raise ValueError("linear record moments require canonical normalized encoding")
        return result


def linear_record_moments(
    basis: ResponseBasis,
    record_id: str,
    source_digest: str,
    features: Sequence[Sequence[Sequence[Scalar]]],
) -> LinearRecordMoments:
    """Extract compact moments directly; never construct quadratic matrices."""
    jets = tuple(_matrix(x, "response feature") for x in features)
    if len(jets) != basis.terms or any(len(x) != basis.rows for x in jets):
        raise ValueError("jets must match basis term count and row count")
    n, d, r = len(jets[0][0]), basis.rows, basis.terms - 1
    if any(len(x[0]) != n for x in jets):
        raise ValueError("a record's feature matrices must have equal column counts")
    constant = tuple(tuple(sum((jets[0][i][k] * jets[0][j][k] for k in range(n)), ZERO)
                           for j in range(d)) for i in range(d))
    linear = tuple(tuple(tuple(sum((jets[0][i][k] * jets[t][j][k] +
                                    jets[t][i][k] * jets[0][j][k] for k in range(n)), ZERO)
                              for j in range(d)) for i in range(d)) for t in range(1, r + 1))
    tangent = tuple(tuple(sum((jets[s][i][k] * jets[t][i][k]
                               for i in range(d) for k in range(n)), ZERO)
                          for t in range(1, r + 1)) for s in range(1, r + 1))
    return LinearRecordMoments(basis, record_id, source_digest, n, constant, linear, tangent)


@dataclass(frozen=True)
class LinearContraction:
    raw_linear_gram: Matrix
    omitted_psd_trace: Fraction
    full_response_squared_frobenius_norm: Fraction


@dataclass(frozen=True)
class LinearResponseIndex:
    basis: ResponseBasis
    constant_gram: Matrix
    first_response: tuple[Matrix, ...]
    tangent_scalar_gram: Matrix
    records: tuple[RecordBinding, ...]

    def __post_init__(self) -> None:
        constant, linear, tangent = _checked_parts(
            self.basis, self.constant_gram, self.first_response, self.tangent_scalar_gram)
        object.__setattr__(self, "constant_gram", constant)
        object.__setattr__(self, "first_response", linear)
        object.__setattr__(self, "tangent_scalar_gram", tangent)
        records = tuple(self.records)
        for record in records:
            if not isinstance(record, RecordBinding):
                raise TypeError("records must contain RecordBinding values")
            _nonempty_text(record.record_id, "record_id")
            _nonempty_text(record.source_digest, "source_digest")
            _nonempty_text(record.payload_digest, "payload_digest")
            _positive_int(record.columns, "columns")
        if len({x.record_id for x in records}) != len(records):
            raise ValueError("record IDs must be unique")
        object.__setattr__(self, "records", tuple(sorted(records)))

    @classmethod
    def from_records(cls, basis: ResponseBasis,
                     records: Iterable[LinearRecordMoments]) -> LinearResponseIndex:
        entries = tuple(records)
        if len({x.record_id for x in entries}) != len(entries):
            raise ValueError("record IDs must be unique")
        if any(x.basis != basis for x in entries):
            raise ValueError("all records must use the same fixed basis")
        d, r = basis.rows, basis.terms - 1
        constant = tuple(tuple(sum((x.constant_gram[i][j] for x in entries), ZERO)
                               for j in range(d)) for i in range(d))
        linear = tuple(tuple(tuple(sum((x.first_response[t][i][j] for x in entries), ZERO)
                                   for j in range(d)) for i in range(d)) for t in range(r))
        tangent = tuple(tuple(sum((x.tangent_scalar_gram[s][t] for x in entries), ZERO)
                              for t in range(r)) for s in range(r))
        bindings = tuple(RecordBinding(x.record_id, x.source_digest, x.columns, x.payload_digest) for x in entries)
        return cls(basis, constant, linear, tangent, bindings)

    @property
    def stored_rational_count(self) -> int:
        """Actual full-matrix scalar slots, excluding IDs/digests/bit lengths."""
        return self.basis.terms * self.basis.rows**2 + (self.basis.terms - 1)**2

    @property
    def retained_ids(self) -> tuple[str, ...]:
        return tuple(x.record_id for x in self.records)

    def remove(self, removed: Iterable[LinearRecordMoments]) -> LinearResponseIndex:
        entries = tuple(removed)
        ids = {x.record_id for x in entries}
        if len(ids) != len(entries):
            raise ValueError("deletion IDs must be unique")
        current = {x.record_id: x for x in self.records}
        for x in entries:
            if x.basis != self.basis:
                raise ValueError("deletion basis does not match")
            if x.record_id not in current:
                raise KeyError(f"record is not retained: {x.record_id}")
            if current[x.record_id] != RecordBinding(x.record_id, x.source_digest, x.columns, x.payload_digest):
                raise ValueError("deletion payload does not match committed contribution")
        subtract = LinearResponseIndex.from_records(self.basis, entries)
        d, r = self.basis.rows, self.basis.terms - 1
        constant = tuple(tuple(self.constant_gram[i][j] - subtract.constant_gram[i][j]
                               for j in range(d)) for i in range(d))
        linear = tuple(tuple(tuple(self.first_response[t][i][j] - subtract.first_response[t][i][j]
                                   for j in range(d)) for i in range(d)) for t in range(r))
        tangent = tuple(tuple(self.tangent_scalar_gram[s][t] - subtract.tangent_scalar_gram[s][t]
                              for t in range(r)) for s in range(r))
        return LinearResponseIndex(self.basis, constant, linear, tangent,
                                   tuple(x for x in self.records if x.record_id not in ids))

    def contract(self, coefficients: Sequence[Scalar]) -> LinearContraction:
        a = tuple(_rational(x, "response coefficient") for x in coefficients)
        if len(a) != self.basis.terms - 1:
            raise ValueError("one coefficient is required per direction")
        d = self.basis.rows
        linear = tuple(tuple(self.constant_gram[i][j] + sum(
            (a[t] * self.first_response[t][i][j] for t in range(len(a))), ZERO)
            for j in range(d)) for i in range(d))
        beta = sum((a[s] * self.tangent_scalar_gram[s][t] * a[t]
                    for s in range(len(a)) for t in range(len(a))), ZERO)
        z2 = sum((linear[i][i] for i in range(d)), ZERO) + beta
        if beta < 0 or z2 < 0:
            raise ValueError("moments do not define nonnegative response squared norms")
        return LinearContraction(linear, beta, z2)

    def canonical_bytes(self) -> bytes:
        return _dump({"schema": "linear-response-index-v1", "basis": self.basis._payload(),
                      "stored_rational_count": self.stored_rational_count,
                      "constant_gram": _encoded_matrix(self.constant_gram),
                      "first_response": [_encoded_matrix(x) for x in self.first_response],
                      "tangent_scalar_gram": _encoded_matrix(self.tangent_scalar_gram),
                      "records": [{"record_id": x.record_id, "source_digest": x.source_digest,
                                   "columns": x.columns, "payload_digest": x.payload_digest}
                                  for x in self.records]})


@dataclass(frozen=True)
class ConditionalLinearEnclosure:
    usable: bool
    reason: str
    linear_covariance: Matrix
    metric_lower_bound: Fraction
    omitted_psd_trace_normalized: Fraction
    response_gram_error_normalized: Fraction
    squared_feature_error_normalized: Fraction
    full_response_squared_norm_normalized: Fraction
    lower_scale: Fraction | None
    upper_scale: Fraction | None
    descriptor_premises_verified_by_module: bool = field(default=False, init=False)


def linear_response_enclosure(
    index: LinearResponseIndex,
    descriptors: ResponseIndex,
    coefficients: Sequence[Scalar],
    ridge: Scalar,
    normalization: Scalar,
    unrepresented_parameter_norm: Scalar = 0,
    *,
    sqrt_precision_bits: int = 32,
) -> ConditionalLinearEnclosure:
    """Prove a two-sided relative enclosure, CONDITIONAL on descriptor proofs.

    Hlin=lambda I+Slin/M0 can be indefinite. A positive exact lower bound mu
    is required; use max(Gershgorin,lambda-beta), where the second bound
    follows from Hlin=lambda I+full_response_Gram-P. Failure safely abstains
    even when a stronger factor proof might succeed. P>=0 is the omitted response Gram,
    tr(P)<=beta. With ||Htrue-(Hlin+P)||<=delta, the scales are
    a=1-delta/mu, b=1+(beta+delta)/mu. a must be positive.
    Unlike discarding all quadratic terms as arbitrary signed error, this
    preserves the omitted tail's PSD sign in the upper scale only.
    """
    lam, m0 = _rational(ridge, "ridge"), _rational(normalization, "normalization")
    if lam <= 0 or m0 <= 0:
        raise ValueError("ridge and normalization must be positive")
    if tuple((x.record_id, x.source_digest) for x in index.records) != tuple(
            (x.record_id, x.source_digest) for x in descriptors.records):
        raise ValueError("response and descriptor retained identities must match")
    a = tuple(_rational(x, "response coefficient") for x in coefficients)
    query = index.contract(a)
    e2 = response_error_squared(descriptors, a, m0, unrepresented_parameter_norm)
    beta, z2 = query.omitted_psd_trace / m0, query.full_response_squared_frobenius_norm / m0
    delta = 2 * dyadic_sqrt_upper(z2 * e2, sqrt_precision_bits) + e2
    d = index.basis.rows
    h = tuple(tuple(query.raw_linear_gram[i][j] / m0 + (lam if i == j else ZERO)
                    for j in range(d)) for i in range(d))
    gershgorin = min(h[i][i] - sum((abs(h[i][j]) for j in range(d) if j != i), ZERO) for i in range(d))
    mu = max(gershgorin, lam - beta)
    if mu <= 0:
        return ConditionalLinearEnclosure(False, "linear covariance lacks a certified positive lower bound",
                                          h, mu, beta, delta, e2, z2, None, None)
    lower, upper = 1 - delta / mu, 1 + (beta + delta) / mu
    return ConditionalLinearEnclosure(
        lower > 0, "relative enclosure available" if lower > 0 else "response error exhausts positive lower scale",
        h, mu, beta, delta, e2, z2, lower, upper,
    )


@dataclass(frozen=True)
class ConditionalShiftedLinearBound:
    raw_surrogate_gram: Matrix
    raw_absolute_gram_error: Fraction
    normalized_absolute_gram_error: Fraction
    omitted_psd_trace_normalized: Fraction
    response_gram_error_normalized: Fraction
    metric_lower_bound: Fraction
    lower_scale: Fraction
    upper_scale: Fraction
    relative_enclosure_usable: bool
    descriptor_premises_verified_by_module: bool = field(default=False, init=False)


def shifted_linear_response_bound(
    index: LinearResponseIndex,
    descriptors: ResponseIndex,
    coefficients: Sequence[Scalar],
    ridge: Scalar,
    normalization: Scalar,
    unrepresented_parameter_norm: Scalar = 0,
    *,
    sqrt_precision_bits: int = 32,
) -> ConditionalShiftedLinearBound:
    """Make the compact proposal PSD without constructing the quadratic Gram.

    Shift by beta=tr(P): Sshift=Slin+beta I is PSD because
    Sshift=Sfull+(beta I-P), with 0<=P<=beta I. Thus Hshift>=lambda I.
    Htrue-Hshift lies between -(beta+delta)I and delta I. The asymmetric
    scales preserve this sign information; a symmetric service hook may use
    the more conservative absolute bound beta+delta. Everything remains
    conditional on true intrinsic jets/descriptors and matching target.
    """
    base = linear_response_enclosure(index, descriptors, coefficients, ridge, normalization,
                                     unrepresented_parameter_norm, sqrt_precision_bits=sqrt_precision_bits)
    lam, m0 = _rational(ridge, "ridge"), _rational(normalization, "normalization")
    beta, delta = base.omitted_psd_trace_normalized, base.response_gram_error_normalized
    d = index.basis.rows
    raw = tuple(tuple(m0 * (base.linear_covariance[i][j] - (lam if i == j else ZERO)
                           + (beta if i == j else ZERO)) for j in range(d)) for i in range(d))
    mu = max(lam, base.metric_lower_bound + beta)
    lower, upper = 1 - (beta + delta) / mu, 1 + delta / mu
    return ConditionalShiftedLinearBound(raw, m0 * (beta + delta), beta + delta,
                                         beta, delta, mu, lower, upper, lower > 0)
