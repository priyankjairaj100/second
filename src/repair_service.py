"""Portable exact sequential calibration-deletion service.

This is an executable reference service for oracle V, not a fast GPU kernel.
A trusted deterministic record-local evaluator returns exact rational features
(the dyadic values of a pinned finite neural program are a valid instance).
The target uses exact Grams, a fixed positive ridge, and ``exact_core`` rounding.

The service composes immutable DAG prefixes, independent reference statistics,
absolute group-error bounds, adaptive replay and exact fallback.
Completion requires successful feature evaluation and sufficient resources.
The reference program MUST be corpus independent.  Transport callbacks are a
named, explicit trusted proof boundary: their stated norm bounds must actually
hold.  A typed witness is provenance binding, not a machine-checked proof of an
arbitrary callback.  Unsupported tuples, foreign bindings and malformed bounds
are rejected.  Unknown providers cause replay; they never certify a candidate.

Committed state is a canonical function of retained records.  Audit traces and
work ledgers are returned separately.  The original state is never mutated.
State is assumed to originate from this service or an authenticated store;
content binding assumes a trusted/authenticated source or SHA-256 collision
resistance. Hashes alone do not authenticate attacker-controlled storage.
Logical omission from new state is not secure erasure of Python/caller copies.

Counters are disjoint engine event counts, NOT timings or fixed-bit operation
counts.  Evaluator/provider/factorization calls have opaque internal work and
Fraction bit complexity is not measured.  Neither passing tests nor a reduction
in one counter proves full-model wall-clock speedup.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction
from hashlib import sha256
from math import isqrt
from types import MappingProxyType
from typing import Callable, Iterable, Mapping, Protocol, Sequence, Union
import json

try:
    from .exact_core import certify_relative_enclosure, sequential_oracle
except ImportError:  # Direct import with src/ on sys.path.
    from exact_core import certify_relative_enclosure, sequential_oracle

Rational = Union[int, Fraction]
Matrix = tuple[tuple[Fraction, ...], ...]
ZERO = Fraction(0)
ONE = Fraction(1)


def _q(value: Rational, name: str) -> Fraction:
    if type(value) is int:
        return Fraction(value)
    if isinstance(value, Fraction):
        return value
    raise TypeError(f"{name} must be an int or Fraction")


def _name(value: str, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a nonempty string")
    return value


def _matrix(value: Sequence[Sequence[Rational]], name: str,
            rows: int | None = None, allow_empty_columns: bool = False) -> Matrix:
    result = tuple(tuple(_q(x, name) for x in row) for row in value)
    if not result or (rows is not None and len(result) != rows):
        raise ValueError(f"{name} has the wrong number of rows")
    width = len(result[0])
    if (not width and not allow_empty_columns) or any(len(r) != width for r in result):
        raise ValueError(f"{name} must be rectangular with valid width")
    return result


def _q_json(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _mat_json(value: Matrix) -> list[list[list[int]]]:
    return [[_q_json(x) for x in row] for row in value]


def _json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _digest(value: object) -> str:
    return sha256(_json(value)).hexdigest()


def sqrt_upper(value: Rational, fractional_bits: int = 32) -> Fraction:
    """An exact rational outward bound, not a floating square root."""
    q = _q(value, "square-root argument")
    if q < 0:
        raise ValueError("square-root argument is negative")
    if type(fractional_bits) is not int or fractional_bits < 0:
        raise ValueError("fractional_bits must be a nonnegative integer")
    scale = 1 << fractional_bits
    n = isqrt((q.numerator * scale * scale) // q.denominator)
    if n * n * q.denominator < q.numerator * scale * scale:
        n += 1
    return Fraction(n, scale)


@dataclass(frozen=True)
class Record:
    record_id: str
    payload: bytes

    def __post_init__(self) -> None:
        _name(self.record_id, "record ID")
        if type(self.payload) is not bytes:
            raise TypeError("record payload must be immutable bytes")

    @property
    def content_digest(self) -> str:
        return sha256(self.payload).hexdigest()


@dataclass(frozen=True)
class StageSpec:
    stage_id: str
    dependencies: tuple[str, ...]
    weights: Matrix
    grids: tuple[tuple[Fraction, ...], ...]
    ridge: Fraction
    normalization: Fraction

    def __post_init__(self) -> None:
        _name(self.stage_id, "stage ID")
        deps = tuple(self.dependencies)
        if any(not isinstance(x, str) or not x for x in deps) or len(set(deps)) != len(deps):
            raise ValueError("dependencies must be unique nonempty stage IDs")
        object.__setattr__(self, "dependencies", tuple(sorted(deps)))
        w = _matrix(self.weights, "weights")
        grids = tuple(tuple(_q(x, "grid") for x in g) for g in self.grids)
        if len(grids) != len(w[0]) or any(not g for g in grids):
            raise ValueError("supply one nonempty grid per input coordinate")
        if any(any(a >= b for a, b in zip(g, g[1:])) for g in grids):
            raise ValueError("grids must be strictly increasing")
        ridge, norm = _q(self.ridge, "ridge"), _q(self.normalization, "normalization")
        if ridge <= 0 or norm <= 0:
            raise ValueError("ridge and fixed normalization must be positive")
        object.__setattr__(self, "weights", w)
        object.__setattr__(self, "grids", grids)
        object.__setattr__(self, "ridge", ridge)
        object.__setattr__(self, "normalization", norm)

    @property
    def width(self) -> int:
        return len(self.weights[0])

    def _manifest(self) -> dict[str, object]:
        return {"stage_id": self.stage_id, "dependencies": self.dependencies,
                "weights": _mat_json(self.weights),
                "grids": [[_q_json(x) for x in g] for g in self.grids],
                "ridge": _q_json(self.ridge), "normalization": _q_json(self.normalization)}


@dataclass(frozen=True)
class JobSpec:
    stages: tuple[StageSpec, ...]
    evaluator_id: str
    reference_id: str
    group_count: int = 8
    numerical_contract: str = "V:record-local-finite-features/exact-Gram/reverse-LDL/lower-ties/v1"

    def __post_init__(self) -> None:
        stages = tuple(self.stages)
        if not stages or any(not isinstance(s, StageSpec) for s in stages):
            raise ValueError("a job requires StageSpec entries in dependency order")
        seen: set[str] = set()
        for s in stages:
            if s.stage_id in seen or not set(s.dependencies) <= seen:
                raise ValueError("stage IDs must be unique and dependencies must precede a stage")
            seen.add(s.stage_id)
        for label in ("evaluator_id", "reference_id", "numerical_contract"):
            _name(getattr(self, label), label)
        if type(self.group_count) is not int or self.group_count <= 0:
            raise ValueError("group_count must be a positive integer")
        object.__setattr__(self, "stages", stages)

    @property
    def manifest_bytes(self) -> bytes:
        return _json({"version": "sequential-repair-v1", "stages": [s._manifest() for s in self.stages],
                      "evaluator_id": self.evaluator_id, "reference_id": self.reference_id,
                      "group_count": self.group_count, "numerical_contract": self.numerical_contract,
                      "group_rule": "sha256-utf8-ID-mod-count", "state_schema": "canonical-reference-v1"})

    @property
    def manifest_digest(self) -> str:
        return sha256(self.manifest_bytes).hexdigest()


@dataclass(frozen=True)
class StageOutput:
    stage_id: str
    codes: Matrix

    def __post_init__(self) -> None:
        _name(self.stage_id, "stage ID")
        object.__setattr__(self, "codes", _matrix(self.codes, "codes"))

    def _json(self) -> dict[str, object]:
        return {"stage_id": self.stage_id, "codes": _mat_json(self.codes)}


@dataclass(frozen=True)
class CertifiedPrefix:
    """Only declared ancestors are exposed to a stage evaluator/provider."""
    manifest_digest: str
    outputs: tuple[StageOutput, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "outputs", tuple(self.outputs))
        if len({o.stage_id for o in self.outputs}) != len(self.outputs):
            raise ValueError("prefix contains duplicate stage IDs")

    @property
    def digest(self) -> str:
        return _digest({"manifest": self.manifest_digest,
                        "ancestors": [o._json() for o in self.outputs]})

    def as_mapping(self) -> Mapping[str, Matrix]:
        return MappingProxyType({o.stage_id: o.codes for o in self.outputs})


@dataclass(frozen=True)
class ReferenceSample:
    features: Matrix
    descriptor: bytes = b""

    def __post_init__(self) -> None:
        if type(self.descriptor) is not bytes:
            raise TypeError("reference descriptor must be immutable canonical bytes")
        object.__setattr__(self, "features", _matrix(self.features, "reference features",
                                                   allow_empty_columns=True))


class FeatureEvaluator(Protocol):
    def __call__(self, record: Record, stage: StageSpec,
                 prefix: CertifiedPrefix) -> Sequence[Sequence[Rational]]: ...


class ReferenceEvaluator(Protocol):
    def __call__(self, record: Record, stage: StageSpec) -> ReferenceSample: ...


@dataclass(frozen=True)
class IntrinsicRecord:
    record_id: str
    content_digest: str
    group_id: int
    descriptors: tuple[tuple[str, bytes], ...]

    def descriptor_for(self, stage_id: str) -> bytes:
        return dict(self.descriptors)[stage_id]

    def _json(self) -> dict[str, object]:
        return {"id": self.record_id, "content_sha256": self.content_digest, "group": self.group_id,
                "descriptors": [[s, value.hex()] for s, value in self.descriptors]}


@dataclass(frozen=True)
class ReferenceGroup:
    group_id: int
    record_ids: tuple[str, ...]
    stage_grams: tuple[tuple[str, Matrix], ...]

    def gram_for(self, stage_id: str) -> Matrix:
        return dict(self.stage_grams)[stage_id]

    def _json(self) -> dict[str, object]:
        return {"group": self.group_id, "ids": self.record_ids,
                "grams": [[s, _mat_json(g)] for s, g in self.stage_grams]}


@dataclass(frozen=True)
class CanonicalState:
    manifest_digest: str
    model: tuple[StageOutput, ...]
    records: tuple[IntrinsicRecord, ...]
    reference_groups: tuple[ReferenceGroup, ...]

    def canonical_bytes(self) -> bytes:
        """History-independent logical state; no proof transcripts or raw data."""
        return _json({"schema": "canonical-reference-v1", "manifest": self.manifest_digest,
                      "model": [o._json() for o in self.model],
                      "records": [r._json() for r in self.records],
                      "groups": [g._json() for g in self.reference_groups]})

    @property
    def digest(self) -> str:
        return sha256(self.canonical_bytes()).hexdigest()

    @property
    def retained_ids(self) -> tuple[str, ...]:
        return tuple(r.record_id for r in self.records)


@dataclass(frozen=True)
class GroupBinding:
    manifest_digest: str
    stage_id: str
    prefix_digest: str
    reference_id: str
    group_id: int
    records_digest: str
    reference_gram_digest: str
    surrogate_gram_digest: str


@dataclass(frozen=True)
class GroupContext:
    """The raw Gram is sum XX^T, BEFORE normalization and ridge.

    All records in this context belong to a retained-only fixed group.  A bound
    is valid only for this stage's NEW certified ancestor prefix.  Descriptor
    semantics belong to the pinned corpus-independent reference evaluator.
    """
    binding: GroupBinding
    stage: StageSpec
    prefix: CertifiedPrefix
    reference_gram: Matrix
    records: tuple[IntrinsicRecord, ...]

    def binding_for_surrogate(self, raw_gram: Sequence[Sequence[Rational]]) -> GroupBinding:
        """Bind a prefix-dependent proposal; this does not establish its proof."""
        matrix = _matrix(raw_gram, "surrogate Gram", self.stage.width)
        if any(len(row) != self.stage.width for row in matrix):
            raise ValueError("surrogate Gram must be square")
        return replace(self.binding, surrogate_gram_digest=_digest(_mat_json(matrix)))

    @property
    def reference_frobenius_norm_upper(self) -> Fraction:
        return sqrt_upper(sum((self.reference_gram[i][i] for i in range(self.stage.width)), ZERO))


@dataclass(frozen=True)
class UnknownBound:
    reason: str = "no compatible transport proof"


UNKNOWN = UnknownBound()


@dataclass(frozen=True)
class AbsoluteGramBound:
    """Trusted premise ||true raw Gram - bound proposal raw Gram||_2 <= raw_error_bound."""
    binding: GroupBinding
    provider_id: str
    raw_error_bound: Fraction
    justification: str


@dataclass(frozen=True)
class SignedGramBound:
    """Trusted premise -negative_radius I <= Hraw*-P <= positive_radius I.

    Both radii are nonnegative rational numbers. Unlike a symmetric norm bound,
    this preserves one-sided information for a shifted linear response Gram.
    Normalization and ridge are applied by the service, never by the provider.
    """
    binding: GroupBinding
    provider_id: str
    negative_radius: Fraction
    positive_radius: Fraction
    justification: str


@dataclass(frozen=True)
class FeatureDriftBound:
    """Trusted premise ||concatenated X* - concatenated Z||_F <= error_bound."""
    binding: GroupBinding
    provider_id: str
    error_bound: Fraction
    justification: str


BoundResult = Union[UnknownBound, AbsoluteGramBound, SignedGramBound, FeatureDriftBound]


@dataclass(frozen=True)
class SurrogateProposal:
    """Optional new-prefix proposal computed solely from intrinsic stored state.

    ``origin`` equals the original GroupContext binding. The bound must use
    ``context.binding_for_surrogate(raw_gram)``. The engine validates exact PSD
    before using its ridge lower bound. A FeatureDriftBound additionally asserts
    a common-column realization Z of this Gram and the claimed ||Xtrue-Z||_F.
    An unknown bound permits a proposal but forces replay of its group.
    """
    origin: GroupBinding
    raw_gram: Matrix
    bound: BoundResult


@dataclass(frozen=True)
class TrustedBoundProvider:
    """Explicit trusted theorem implementation, not an unchecked scalar API.

    Provider correctness is a precondition. The engine checks identity/binding,
    exact type/sign and composes its bound rigorously; it cannot prove arbitrary
    callback code. Return UNKNOWN for every unsupported numerical operation.
    """
    provider_id: str
    prove: Callable[[GroupContext], Union[BoundResult, SurrogateProposal]]

    def __post_init__(self) -> None:
        _name(self.provider_id, "provider ID")
        if not callable(self.prove):
            raise TypeError("provider prove must be callable")


class InvalidWitness(ValueError):
    """A claimed certificate was malformed; the transaction did not commit."""


@dataclass(frozen=True)
class WorkLedger:
    counts: tuple[tuple[str, int], ...]

    def count(self, event: str) -> int:
        return dict(self.counts).get(event, 0)

    def as_mapping(self) -> Mapping[str, int]:
        return MappingProxyType(dict(self.counts))


class _Work:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    def add(self, event: str, count: int = 1) -> None:
        if count:
            self.counts[event] = self.counts.get(event, 0) + count

    def freeze(self) -> WorkLedger:
        return WorkLedger(tuple(sorted(self.counts.items())))


@dataclass(frozen=True)
class StageAudit:
    stage_id: str
    prefix_digest: str
    route: str
    certificate_attempts: int
    replayed_groups: tuple[int, ...]
    unknown_groups: tuple[int, ...]
    provider_id: str | None


@dataclass(frozen=True)
class ServiceResult:
    state: CanonicalState
    ledger: WorkLedger
    stages: tuple[StageAudit, ...]


def _zero(d: int) -> Matrix:
    return tuple(tuple(ZERO for _ in range(d)) for _ in range(d))


def _combine(a: Matrix, b: Matrix, sign: int, work: _Work) -> Matrix:
    work.add("moment_entry_additions", len(a) * len(a))
    return tuple(tuple(x + sign * y for x, y in zip(ar, br)) for ar, br in zip(a, b))


def _gram(features: Matrix, work: _Work) -> Matrix:
    d, t = len(features), len(features[0])
    result = [[ZERO for _ in range(d)] for _ in range(d)]
    for i in range(d):
        for j in range(i + 1):
            value = sum((features[i][k] * features[j][k] for k in range(t)), ZERO)
            result[i][j] = result[j][i] = value
    work.add("gram_scalar_products", d * (d + 1) // 2 * t)
    work.add("gram_scalar_accumulations", d * (d + 1) // 2 * t)
    return tuple(tuple(r) for r in result)


def _metric(raw_gram: Matrix, stage: StageSpec, work: _Work) -> Matrix:
    work.add("metric_entry_divisions", stage.width * stage.width)
    work.add("metric_diagonal_additions", stage.width)
    return tuple(tuple(x / stage.normalization + (stage.ridge if i == j else ZERO)
                       for j, x in enumerate(row)) for i, row in enumerate(raw_gram))


def _is_psd(matrix: Matrix) -> bool:
    """Exact semidefinite LDL check; zero pivots require a zero residual row."""
    d = len(matrix)
    if any(matrix[i][j] != matrix[j][i] for i in range(d) for j in range(d)):
        return False
    a = [list(row) for row in matrix]
    for k in range(d):
        pivot = a[k][k]
        if pivot < 0:
            return False
        if pivot == 0:
            if any(a[i][k] != 0 for i in range(k + 1, d)):
                return False
            continue
        for i in range(k + 1, d):
            for j in range(i, d):
                a[j][i] = a[i][j] = a[i][j] - a[i][k] * a[j][k] / pivot
    return True


@dataclass(frozen=True, init=False)
class RepairService:
    """Complete sequential exact model and canonical reference-index service.

    ``fresh`` is an independent direct retained-data constructor, deliberately
    ignoring transport certificates.  It is a correctness oracle, NOT asserted
    to be the fastest fair performance baseline. Both feature callbacks must be
    deterministic under their manifested contracts. Errors propagate without a
    state mutation. Callback failures are target/program errors, not repair wins.
    """

    job: JobSpec
    evaluator: FeatureEvaluator
    reference_evaluator: ReferenceEvaluator
    provider: TrustedBoundProvider | None
    _manifest: str
    _ancestors: Mapping[str, frozenset[str]]

    def __init__(self, job: JobSpec, evaluator: FeatureEvaluator,
                 reference_evaluator: ReferenceEvaluator,
                 provider: TrustedBoundProvider | None = None) -> None:
        if not isinstance(job, JobSpec) or not callable(evaluator) or not callable(reference_evaluator):
            raise TypeError("supply a JobSpec and callable feature/reference evaluators")
        if provider is not None and not isinstance(provider, TrustedBoundProvider):
            raise TypeError("provider must be a TrustedBoundProvider or None")
        object.__setattr__(self, "job", job)
        object.__setattr__(self, "evaluator", evaluator)
        object.__setattr__(self, "reference_evaluator", reference_evaluator)
        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "_manifest", job.manifest_digest)
        ancestors: dict[str, frozenset[str]] = {}
        for stage in job.stages:
            closure = set(stage.dependencies)
            for dep in stage.dependencies:
                closure.update(ancestors[dep])
            ancestors[stage.stage_id] = frozenset(closure)
        object.__setattr__(self, "_ancestors", MappingProxyType(ancestors))

    def _group(self, record_id: str) -> int:
        return int.from_bytes(sha256(record_id.encode("utf-8")).digest(), "big") % self.job.group_count

    def _prefix(self, stage: StageSpec, outputs: Sequence[StageOutput]) -> CertifiedPrefix:
        wanted = self._ancestors[stage.stage_id]
        values = tuple(o for o in outputs if o.stage_id in wanted)
        if {o.stage_id for o in values} != wanted:
            raise ValueError("cannot evaluate a stage before all ancestors are certified")
        return CertifiedPrefix(self._manifest, values)

    def _reference(self, record: Record, stage: StageSpec, work: _Work,
                   event: str) -> ReferenceSample:
        work.add(event)
        sample = self.reference_evaluator(record, stage)
        if not isinstance(sample, ReferenceSample):
            raise TypeError("reference evaluator must return ReferenceSample")
        features = _matrix(sample.features, "reference features", stage.width, True)
        return ReferenceSample(features, sample.descriptor)

    def _target(self, record: Record, stage: StageSpec, prefix: CertifiedPrefix,
                work: _Work, event: str) -> Matrix:
        work.add(event)
        return _matrix(self.evaluator(record, stage, prefix), "target features", stage.width, True)

    def _quantize(self, stage: StageSpec, gram: Matrix, work: _Work) -> StageOutput:
        work.add("exact_factorization_calls")
        work.add("rounding_decisions", len(stage.weights) * stage.width)
        result = sequential_oracle(stage.weights, _metric(gram, stage, work), stage.grids)
        return StageOutput(stage.stage_id, result.codes)

    def _finish(self, records: tuple[IntrinsicRecord, ...], groups: tuple[ReferenceGroup, ...],
                model: tuple[StageOutput, ...], work: _Work,
                audits: tuple[StageAudit, ...]) -> ServiceResult:
        state = CanonicalState(self._manifest, model, records, groups)
        work.add("committed_record_entries", len(records))
        work.add("committed_model_coordinates", sum(len(o.codes) * len(o.codes[0]) for o in model))
        work.add("canonical_serialized_bytes", len(state.canonical_bytes()))
        return ServiceResult(state, work.freeze(), audits)

    def fresh(self, records: Iterable[Record]) -> ServiceResult:
        """Build the reference index and independently run the full exact target."""
        work = _Work()
        data: dict[str, Record] = {}
        for record in records:
            if not isinstance(record, Record) or record.record_id in data:
                raise ValueError("fresh records must be Record objects with unique IDs")
            data[record.record_id] = record
            work.add("fresh_input_records")
            work.add("content_hash_bytes", len(record.payload))
        ordered = tuple(data[k] for k in sorted(data))
        grams: dict[int, dict[str, Matrix]] = {}
        group_ids: dict[int, list[str]] = {}
        metadata = []
        for record in ordered:
            group_id = self._group(record.record_id)
            group_ids.setdefault(group_id, []).append(record.record_id)
            by_stage = grams.setdefault(group_id, {s.stage_id: _zero(s.width) for s in self.job.stages})
            descriptors = []
            for stage in self.job.stages:
                sample = self._reference(record, stage, work, "reference_setup_evaluator_calls")
                by_stage[stage.stage_id] = _combine(by_stage[stage.stage_id], _gram(sample.features, work), 1, work)
                descriptors.append((stage.stage_id, sample.descriptor))
            metadata.append(IntrinsicRecord(record.record_id, record.content_digest, group_id, tuple(descriptors)))
        groups = tuple(ReferenceGroup(gid, tuple(group_ids[gid]),
                                      tuple((s.stage_id, grams[gid][s.stage_id]) for s in self.job.stages))
                       for gid in sorted(grams))
        outputs: list[StageOutput] = []
        audits = []
        for stage in self.job.stages:
            prefix = self._prefix(stage, outputs)
            gram = _zero(stage.width)
            for record in ordered:
                features = self._target(record, stage, prefix, work, "fresh_target_evaluator_calls")
                gram = _combine(gram, _gram(features, work), 1, work)
            outputs.append(self._quantize(stage, gram, work))
            audits.append(StageAudit(stage.stage_id, prefix.digest, "independent_fresh", 0, (), (), None))
        return self._finish(tuple(metadata), groups, tuple(outputs), work, tuple(audits))

    def _validate_state(self, state: CanonicalState, work: _Work) -> None:
        """Structural and manifest validation, not adversarial-store authentication."""
        if not isinstance(state, CanonicalState) or state.manifest_digest != self._manifest:
            raise ValueError("state belongs to a different target/reference manifest")
        if state.retained_ids != tuple(sorted(set(state.retained_ids))):
            raise ValueError("state record map is not canonical")
        stage_ids = tuple(s.stage_id for s in self.job.stages)
        if tuple(o.stage_id for o in state.model) != stage_ids:
            raise ValueError("state model stages do not match the target")
        for output, stage in zip(state.model, self.job.stages):
            if len(output.codes) != len(stage.weights) or any(len(r) != stage.width for r in output.codes):
                raise ValueError("state model has invalid dimensions")
            if any(x not in stage.grids[j] for row in output.codes for j, x in enumerate(row)):
                raise ValueError("state model has a code outside its declared grid")
        by_group: dict[int, list[str]] = {}
        for record in state.records:
            work.add("validated_record_entries")
            if self._group(record.record_id) != record.group_id:
                raise ValueError("state record has a noncanonical group")
            if tuple(s for s, _ in record.descriptors) != stage_ids:
                raise ValueError("record descriptors do not match the target stages")
            if any(type(v) is not bytes for _, v in record.descriptors):
                raise ValueError("record descriptor is not immutable bytes")
            if len(record.content_digest) != 64 or any(c not in "0123456789abcdef" for c in record.content_digest):
                raise ValueError("record content digest is malformed")
            by_group.setdefault(record.group_id, []).append(record.record_id)
        if tuple(g.group_id for g in state.reference_groups) != tuple(sorted(by_group)):
            raise ValueError("reference groups are not the canonical nonempty groups")
        for group in state.reference_groups:
            if group.record_ids != tuple(by_group[group.group_id]) or tuple(s for s, _ in group.stage_grams) != stage_ids:
                raise ValueError("reference group membership or stage order mismatch")
            for stage, (_, gram) in zip(self.job.stages, group.stage_grams):
                checked = _matrix(gram, "stored reference Gram", stage.width)
                if any(len(r) != stage.width for r in checked):
                    raise ValueError("stored reference Gram is not square")
                if any(checked[i][j] != checked[j][i] for i in range(stage.width) for j in range(stage.width)):
                    raise ValueError("stored reference Gram is not symmetric")
                if any(checked[i][i] < 0 for i in range(stage.width)):
                    raise ValueError("stored reference Gram has a negative diagonal")
                work.add("validated_gram_entries", stage.width * stage.width)

    def _delete_index(self, state: CanonicalState, deleted: tuple[Record, ...],
                      work: _Work) -> tuple[tuple[IntrinsicRecord, ...], tuple[ReferenceGroup, ...]]:
        metadata = {r.record_id: r for r in state.records}
        remove = set()
        for record in deleted:
            if not isinstance(record, Record) or record.record_id in remove:
                raise ValueError("deletion records must be unique Record objects")
            old = metadata.get(record.record_id)
            if old is None:
                raise ValueError("deletion ID is not currently retained")
            work.add("content_hash_bytes", len(record.payload))
            if record.content_digest != old.content_digest:
                raise ValueError("deleted-record content does not match the state")
            remove.add(record.record_id)
        grams = {g.group_id: dict(g.stage_grams) for g in state.reference_groups}
        for record in sorted(deleted, key=lambda r: r.record_id):
            old = metadata[record.record_id]
            for stage in self.job.stages:
                sample = self._reference(record, stage, work, "deleted_reference_evaluator_calls")
                if sample.descriptor != old.descriptor_for(stage.stage_id):
                    raise ValueError("reference descriptor changed under a pinned reference program")
                grams[old.group_id][stage.stage_id] = _combine(
                    grams[old.group_id][stage.stage_id], _gram(sample.features, work), -1, work)
        retained = tuple(r for r in state.records if r.record_id not in remove)
        memberships: dict[int, list[str]] = {}
        for record in retained:
            work.add("retained_index_rebuild_entries")
            memberships.setdefault(record.group_id, []).append(record.record_id)
        groups = tuple(ReferenceGroup(gid, tuple(memberships[gid]),
                                      tuple((s.stage_id, grams[gid][s.stage_id]) for s in self.job.stages))
                       for gid in sorted(memberships))
        work.add("logically_removed_record_entries", len(remove))
        return retained, groups

    def _proposal(self, context: GroupContext, work: _Work) -> tuple[Matrix, tuple[Fraction, Fraction] | None]:
        gram = context.reference_gram
        if self.provider is None:
            return gram, None
        work.add("transport_provider_calls")
        work.add("provider_descriptor_records", len(context.records))
        answer = self.provider.prove(context)
        binding = context.binding
        if isinstance(answer, SurrogateProposal):
            if answer.origin != context.binding:
                raise InvalidWitness("surrogate proposal belongs to a different original group/prefix")
            try:
                gram = _matrix(answer.raw_gram, "surrogate Gram", context.stage.width)
            except (TypeError, ValueError) as exc:
                raise InvalidWitness(str(exc)) from exc
            if any(len(row) != context.stage.width for row in gram):
                raise InvalidWitness("surrogate Gram must be square")
            work.add("proposal_psd_validation_calls")
            if not _is_psd(gram):
                raise InvalidWitness("surrogate raw Gram must be exactly symmetric positive semidefinite")
            binding = context.binding_for_surrogate(gram)
            answer = answer.bound
        if isinstance(answer, UnknownBound):
            return gram, None
        if not isinstance(answer, (AbsoluteGramBound, SignedGramBound, FeatureDriftBound)):
            raise InvalidWitness("provider returned an unsupported witness; scalar/spectral tuples are not proofs")
        if answer.binding != binding or answer.provider_id != self.provider.provider_id:
            raise InvalidWitness("transport witness is bound to another prefix, group, target, surrogate, or provider")
        if not isinstance(answer.justification, str) or not answer.justification:
            raise InvalidWitness("transport witness must name its proof obligation")
        def radius(value: Rational) -> Fraction:
            try:
                result = _q(value, "transport bound")
            except TypeError as exc:
                raise InvalidWitness(str(exc)) from exc
            if result < 0:
                raise InvalidWitness("transport bound cannot be negative")
            return result
        if isinstance(answer, SignedGramBound):
            return gram, (radius(answer.negative_radius), radius(answer.positive_radius))
        value = radius(answer.raw_error_bound if isinstance(answer, AbsoluteGramBound) else answer.error_bound)
        if isinstance(answer, FeatureDriftBound):
            work.add("feature_to_gram_bound_conversions")
            norm = sqrt_upper(sum((gram[i][i] for i in range(context.stage.width)), ZERO))
            value = 2 * norm * value + value * value
        return gram, (value, value)

    def repair(self, state: CanonicalState, deleted_records: Iterable[Record],
               retained_source: Callable[[str], Record]) -> ServiceResult:
        """Transactionally remove records and return the complete exact new state.

        Source accesses are retained-only and content checked. Each source record
        is read at most once per request, but feature evaluations are stage local
        and separately charged. The caller provides removed contents before their
        erasure; IDs alone cannot recover missing reference contributions.
        """
        work = _Work()
        self._validate_state(state, work)
        if not callable(retained_source):
            raise TypeError("retained_source must be callable")
        retained, groups = self._delete_index(state, tuple(deleted_records), work)
        metadata = {r.record_id: r for r in retained}
        cached_records: dict[str, Record] = {}

        def read(record_id: str) -> Record:
            if record_id not in metadata:
                raise ValueError("attempted a non-retained source access")
            if record_id not in cached_records:
                work.add("retained_source_record_reads")
                record = retained_source(record_id)
                if not isinstance(record, Record) or record.record_id != record_id:
                    raise ValueError("retained source returned a different record ID")
                work.add("content_hash_bytes", len(record.payload))
                if record.content_digest != metadata[record_id].content_digest:
                    raise ValueError("retained source content does not match the state")
                cached_records[record_id] = record
            return cached_records[record_id]

        outputs: list[StageOutput] = []
        audits: list[StageAudit] = []
        for stage in self.job.stages:
            prefix = self._prefix(stage, outputs)
            raw = _zero(stage.width)
            reference_grams: dict[int, Matrix] = {}
            bounds: dict[int, tuple[Fraction, Fraction] | None] = {}
            by_group = {g.group_id: g for g in groups}
            for group in groups:
                gram = group.gram_for(stage.stage_id)
                members = tuple(metadata[rid] for rid in group.record_ids)
                binding = GroupBinding(self._manifest, stage.stage_id, prefix.digest,
                                       self.job.reference_id, group.group_id,
                                       _digest([r._json() for r in members]), _digest(_mat_json(gram)),
                                       _digest(_mat_json(gram)))
                context = GroupContext(binding, stage, prefix, gram, members)
                proposal, bounds[group.group_id] = self._proposal(context, work)
                reference_grams[group.group_id] = proposal
                raw = _combine(raw, proposal, 1, work)
            unknown = tuple(gid for gid, bound in bounds.items() if bound is None)
            replayed: list[int] = []
            attempts = 0
            while True:
                if not bounds:
                    outputs.append(self._quantize(stage, raw, work))
                    route = "exact_replay"
                    break
                if all(bound is not None for bound in bounds.values()):
                    negative = sum((b[0] for b in bounds.values() if b is not None), ZERO)
                    positive = sum((b[1] for b in bounds.values() if b is not None), ZERO)
                    lo = ONE - negative / stage.normalization / stage.ridge
                    hi = ONE + positive / stage.normalization / stage.ridge
                    work.add("enclosure_scalar_divisions", 4)
                    if lo > 0:
                        attempts += 1
                        work.add("certificate_factorization_calls")
                        work.add("rounding_decisions", len(stage.weights) * stage.width)
                        work.add("cell_predicates", len(stage.weights) * stage.width)
                        certificate = certify_relative_enclosure(
                            stage.weights, _metric(raw, stage, work), stage.grids, lo, hi)
                        if certificate.accepted:
                            outputs.append(StageOutput(stage.stage_id, certificate.candidate.codes))
                            route = "transport_certificate"
                            break
                # Fixed prefix/reference: replay removes a nonnegative ABSOLUTE
                # uncertainty term. Unknown groups take priority. This is a
                # deterministic heuristic, not a minimum-work selector theorem.
                work.add("group_selection_entries", len(bounds))
                unknown_now = [gid for gid, b in bounds.items() if b is None]
                if unknown_now:
                    chosen = min(unknown_now)
                else:
                    chosen = min(bounds, key=lambda gid: (-sum(bounds[gid]), gid))  # type: ignore[arg-type]
                actual = _zero(stage.width)
                for rid in by_group[chosen].record_ids:
                    features = self._target(read(rid), stage, prefix, work, "retained_replay_evaluator_calls")
                    actual = _combine(actual, _gram(features, work), 1, work)
                raw = _combine(_combine(raw, reference_grams[chosen], -1, work), actual, 1, work)
                del bounds[chosen]
                replayed.append(chosen)
            audits.append(StageAudit(stage.stage_id, prefix.digest, route, attempts,
                                     tuple(replayed), unknown,
                                     self.provider.provider_id if self.provider else None))
        return self._finish(retained, groups, tuple(outputs), work, tuple(audits))


__all__ = ["Record", "StageSpec", "JobSpec", "StageOutput", "CertifiedPrefix", "ReferenceSample",
           "IntrinsicRecord", "ReferenceGroup", "CanonicalState", "GroupBinding", "GroupContext",
           "UnknownBound", "UNKNOWN", "AbsoluteGramBound", "SignedGramBound", "FeatureDriftBound", "SurrogateProposal", "TrustedBoundProvider",
           "InvalidWitness", "WorkLedger", "StageAudit", "ServiceResult", "RepairService", "sqrt_upper"]
