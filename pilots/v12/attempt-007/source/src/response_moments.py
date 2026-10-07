"""Deletion-additive exact quadratic moments of an intrinsic affine response.

Fix an extractor BEFORE the deletable corpus: each record j yields feature
matrices Z_0j,...,Z_rj of shape d by n_j. For request coefficients a, set
Z_j(a)=Z_0j+sum_t a_t Z_tj. Store C_st=sum_j Z_sj Z_tj.T for s<=t.
Then the exact Gram of Z(a) is a quadratic polynomial in a. Its trace is
the exact squared Frobenius norm. This is a surrogate construction, not a
proof that the target transformer's features equal this response.

The extractor's corpus independence and feature fidelity remain explicit
caller premises. No automatic differentiation, Taylor remainder, numerical
neural bound, authentication of raw source bytes, or speedup is supplied.
The manifest binds the intended extractor; it does not audit that extractor.

With m=r+1 terms, totals use m(m+1)d^2/2 rational entries. Record bindings
use O(N) IDs/digests; individual moment matrices need not be stored. Deletion
requires regenerating/providing their exact intrinsic contributions. Given
those contributions, k deletions cost O(k*m^2*d^2) arithmetic, plus copying
and canonical-state costs. Gram evaluation costs O(m^2*d^2), independent of
record count; building record moments costs O(m^2*d^2*n_j). Extractor costs,
index reads, digest serialization and arbitrary-precision bitcost are extra.
The simple immutable implementation rebuilds O(N) record tuples at deletion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
import json
from typing import Callable, Iterable, Sequence, TypeVar

from .exact_core import Matrix, Scalar, ZERO, _matrix, _rational


def _positive_int(value: int, name: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{name} must be a built-in integer")
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _nonempty_text(value: str, name: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{name} must be str")
    if not value:
        raise ValueError(f"{name} must be nonempty")
    return value


def _dump(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("ascii")


def _encoded_matrix(matrix: Matrix) -> list[list[list[int]]]:
    return [[[x.numerator, x.denominator] for x in row] for row in matrix]


@dataclass(frozen=True)
class ResponseBasis:
    """Manifest for a fixed corpus-independent affine feature extractor.

    ``terms`` includes the constant term. ``manifest_id`` should be a stable
    content digest or identifier covering the reference, directions,
    extractor program, numerical semantics and stage. Corpus independence
    must be explicitly attested; this class cannot establish its truth.
    """

    manifest_id: str
    rows: int
    terms: int
    corpus_independent_by_caller_attestation: bool
    corpus_independence_verified_by_module: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        _nonempty_text(self.manifest_id, "manifest_id")
        _positive_int(self.rows, "rows")
        _positive_int(self.terms, "terms")
        if self.corpus_independent_by_caller_attestation is not True:
            raise ValueError("a pre-data corpus-independent extractor must be explicitly attested")

    def _payload(self) -> dict[str, object]:
        return {"manifest_id": self.manifest_id, "rows": self.rows,
                "terms": self.terms, "corpus_independent_by_caller_attestation": True}


def _pairs(basis: ResponseBasis) -> tuple[tuple[int, int], ...]:
    return tuple((s, t) for s in range(basis.terms) for t in range(s, basis.terms))


def _normalize_moments(values: Sequence[Sequence[Sequence[Scalar]]], basis: ResponseBasis) -> tuple[Matrix, ...]:
    matrices = tuple(_matrix(value, "cross moment") for value in values)
    if len(matrices) != basis.terms * (basis.terms + 1) // 2:
        raise ValueError("wrong number of triangular cross moments")
    for (s, t), matrix in zip(_pairs(basis), matrices):
        if len(matrix) != basis.rows or any(len(row) != basis.rows for row in matrix):
            raise ValueError("every cross moment must be d by d")
        if s == t and any(matrix[i][j] != matrix[j][i]
                          for i in range(basis.rows) for j in range(i)):
            raise ValueError("diagonal cross moments must be symmetric")
    return matrices


@dataclass(frozen=True)
class RecordMoments:
    """Intrinsic contribution; use ``record_moments`` to construct from jets.

    Arbitrary directly constructed moments are only caller-claimed moments;
    aggregate source provenance is not validated by this arithmetic module.
    Source identity must be bound by the surrounding data/transaction layer.
    """

    basis: ResponseBasis
    record_id: str
    source_digest: str
    columns: int
    cross_moments: tuple[Matrix, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.basis, ResponseBasis):
            raise TypeError("basis must be ResponseBasis")
        _nonempty_text(self.record_id, "record_id")
        _nonempty_text(self.source_digest, "source_digest")
        _positive_int(self.columns, "columns")
        object.__setattr__(self, "cross_moments", _normalize_moments(self.cross_moments, self.basis))

    def canonical_bytes(self) -> bytes:
        return _dump({"schema": "record-response-moments-v1", "basis": self.basis._payload(),
                      "record_id": self.record_id, "source_digest": self.source_digest,
                      "columns": self.columns,
                      "cross_moments": [_encoded_matrix(x) for x in self.cross_moments]})

    @classmethod
    def from_canonical_bytes(cls, payload: bytes) -> RecordMoments:
        """Decode the exact schema and reject noncanonical byte encodings.

        This is parsing, not authentication; callers must bind the bytes to
        the intended intrinsic extractor/source and bound resource sizes.
        """
        if type(payload) is not bytes:
            raise TypeError("payload must be bytes")
        data = json.loads(payload)
        if not isinstance(data, dict) or data.get("schema") != "record-response-moments-v1":
            raise ValueError("unsupported record-moment schema")
        metadata = data["basis"]
        basis = ResponseBasis(metadata["manifest_id"], metadata["rows"], metadata["terms"],
                              metadata["corpus_independent_by_caller_attestation"])

        def scalar(pair: object) -> Fraction:
            if not isinstance(pair, list) or len(pair) != 2 or any(type(x) is not int for x in pair):
                raise TypeError("encoded rationals must be pairs of built-in integers")
            if pair[1] <= 0:
                raise ValueError("encoded rational denominator must be positive")
            return Fraction(pair[0], pair[1])

        cross = tuple(tuple(tuple(scalar(pair) for pair in row) for row in matrix)
                      for matrix in data["cross_moments"])
        result = cls(basis, data["record_id"], data["source_digest"], data["columns"], cross)
        if result.canonical_bytes() != payload:
            raise ValueError("record moments must use canonical normalized encoding")
        return result

    @property
    def payload_digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


def record_moments(
    basis: ResponseBasis,
    record_id: str,
    source_digest: str,
    features: Sequence[Sequence[Sequence[Scalar]]],
) -> RecordMoments:
    """Build exact oriented C_st from the supplied Z_0,...,Z_r matrices."""
    jets = tuple(_matrix(value, "response feature") for value in features)
    if len(jets) != basis.terms:
        raise ValueError("feature count must equal basis.terms")
    if any(len(matrix) != basis.rows for matrix in jets):
        raise ValueError("response features must all have basis.rows rows")
    columns = len(jets[0][0])
    if any(len(matrix[0]) != columns for matrix in jets):
        raise ValueError("a record's response features must have identical column counts")
    moments = tuple(
        tuple(tuple(sum((jets[s][i][k] * jets[t][j][k] for k in range(columns)), ZERO)
                    for j in range(basis.rows)) for i in range(basis.rows))
        for s, t in _pairs(basis)
    )
    return RecordMoments(basis, record_id, source_digest, columns, moments)


Record = TypeVar("Record")


def extract_record_moments(
    basis: ResponseBasis,
    record_id: str,
    source_digest: str,
    record: Record,
    trusted_extractor: Callable[[Record], Sequence[Sequence[Sequence[Scalar]]]],
) -> RecordMoments:
    """Call an explicitly trusted intrinsic extractor, then compute moments."""
    return record_moments(basis, record_id, source_digest, trusted_extractor(record))


@dataclass(frozen=True, order=True)
class RecordBinding:
    record_id: str
    source_digest: str
    columns: int
    payload_digest: str


@dataclass(frozen=True)
class ResponseIndex:
    """Canonical retained-only totals plus intrinsic record-payload bindings.

    Supplied deletions are checked against the committed payload digests.
    This prevents accidental wrong-contribution subtraction. It is hash
    binding, not a proof against collision or unauthenticated original input.
    Byte equality of fresh/repaired indexes is exact for the same moments.
    """

    basis: ResponseBasis
    cross_moments: tuple[Matrix, ...]
    records: tuple[RecordBinding, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.basis, ResponseBasis):
            raise TypeError("basis must be ResponseBasis")
        object.__setattr__(self, "cross_moments", _normalize_moments(self.cross_moments, self.basis))
        records = tuple(self.records)
        for record in records:
            if not isinstance(record, RecordBinding):
                raise TypeError("records must contain RecordBinding values")
            _nonempty_text(record.record_id, "record_id")
            _nonempty_text(record.source_digest, "source_digest")
            _nonempty_text(record.payload_digest, "payload_digest")
            _positive_int(record.columns, "columns")
        if len({record.record_id for record in records}) != len(records):
            raise ValueError("record IDs must be unique")
        object.__setattr__(self, "records", tuple(sorted(records)))

    @classmethod
    def from_records(cls, basis: ResponseBasis, records: Iterable[RecordMoments]) -> ResponseIndex:
        moments = tuple(records)
        ids = [record.record_id for record in moments]
        if len(set(ids)) != len(ids):
            raise ValueError("record IDs must be unique")
        if any(record.basis != basis for record in moments):
            raise ValueError("all contributions must use the same fixed response basis")
        totals = tuple(
            tuple(tuple(sum((record.cross_moments[p][i][j] for record in moments), ZERO)
                        for j in range(basis.rows)) for i in range(basis.rows))
            for p in range(len(_pairs(basis)))
        )
        bindings = tuple(RecordBinding(record.record_id, record.source_digest,
                                       record.columns, record.payload_digest) for record in moments)
        return cls(basis, totals, bindings)

    @property
    def retained_ids(self) -> tuple[str, ...]:
        return tuple(record.record_id for record in self.records)

    @property
    def total_columns(self) -> int:
        return sum(record.columns for record in self.records)

    def remove(self, removed: Iterable[RecordMoments]) -> ResponseIndex:
        """Return fresh-identical retained state after authenticated subtraction.

        No mutation occurs before/after validation failure. Removed features
        must be available as supplied intrinsic contributions before erasure.
        """
        contributions = tuple(removed)
        if len({record.record_id for record in contributions}) != len(contributions):
            raise ValueError("deletion IDs must be unique")
        current = {record.record_id: record for record in self.records}
        for record in contributions:
            if record.basis != self.basis:
                raise ValueError("deletion contribution uses a different basis")
            stored = current.get(record.record_id)
            if stored is None:
                raise KeyError(f"record is not retained: {record.record_id}")
            binding = RecordBinding(record.record_id, record.source_digest,
                                    record.columns, record.payload_digest)
            if binding != stored:
                raise ValueError("deletion contribution does not match its committed payload")
        totals = tuple(
            tuple(tuple(self.cross_moments[p][i][j] - sum(
                (record.cross_moments[p][i][j] for record in contributions), ZERO)
                for j in range(self.basis.rows)) for i in range(self.basis.rows))
            for p in range(len(_pairs(self.basis)))
        )
        removed_ids = {record.record_id for record in contributions}
        return ResponseIndex(self.basis, totals,
                             tuple(record for record in self.records if record.record_id not in removed_ids))

    def gram(self, coefficients: Sequence[Scalar]) -> Matrix:
        """Evaluate sum_j Z_j(a) Z_j(a).T exactly; excludes any ridge/scaling."""
        a = (Fraction(1),) + tuple(_rational(x, "response coefficient") for x in coefficients)
        if len(a) != self.basis.terms:
            raise ValueError("supply one coefficient per nonconstant response term")
        gram = [[ZERO for _ in range(self.basis.rows)] for _ in range(self.basis.rows)]
        for (s, t), cross in zip(_pairs(self.basis), self.cross_moments):
            coefficient = a[s] * a[t]
            for i in range(self.basis.rows):
                for j in range(self.basis.rows):
                    gram[i][j] += coefficient * (cross[i][j] if s == t else cross[i][j] + cross[j][i])
        return tuple(tuple(row) for row in gram)

    def squared_frobenius_norm(self, coefficients: Sequence[Scalar]) -> Fraction:
        """Exact ||Z(a)||_F^2, computed directly in O(m^2*d) operations."""
        a = (Fraction(1),) + tuple(_rational(x, "response coefficient") for x in coefficients)
        if len(a) != self.basis.terms:
            raise ValueError("supply one coefficient per nonconstant response term")
        return sum((a[s] * a[t] * (1 if s == t else 2) * sum(
            (cross[i][i] for i in range(self.basis.rows)), ZERO)
            for (s, t), cross in zip(_pairs(self.basis), self.cross_moments)), ZERO)

    def canonical_bytes(self) -> bytes:
        return _dump({"schema": "response-index-v1", "basis": self.basis._payload(),
                      "cross_moments": [_encoded_matrix(x) for x in self.cross_moments],
                      "records": [{"record_id": r.record_id, "source_digest": r.source_digest,
                                   "columns": r.columns, "payload_digest": r.payload_digest}
                                  for r in self.records]})
