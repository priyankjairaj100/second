"""Compact canonical service for certified sequential calibration deletion.

Committed state keeps group response totals and fixed-size record digests.
It never keeps per-record matrices, jets, error descriptors, or source bytes.
A proposal reads one group's totals; it does not scan retained descriptors.
Metadata validation, membership rebuilding, and canonical serialization still
cost O(N L). This implementation does not claim sublinear complete service.

The exact target is the job's sequential oracle V. The extractor and query
must be fixed, deterministic, corpus-independent theorem implementations.
Unknown extraction or query evidence causes exact retained replay. The target
feature evaluator remains trusted. The service checks identities, arithmetic,
chart radius, signs, and source/contribution digests. It cannot prove arbitrary
callback code. State must originate here or from an authenticated store.

Input state is immutable. Failed transactions never change committed state.
Removed source contents must be supplied before erasure. The caller supplies
retained contents only when replay requires them. Logical state deletion is
not physical erasure of Python objects or caller-held copies.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
from types import MappingProxyType
from typing import Callable, Iterable, Mapping

from .exact_core import certify_relative_enclosure
from .linear_response import LinearRecordMoments, LinearResponseIndex, shifted_linear_response_bound
from .response_moments import RecordMoments, ResponseIndex
from .response_service_adapter import ResponseQuery, ResponseStageContract
from .repair_service import (
    CertifiedPrefix, FeatureEvaluator, GroupBinding, InvalidWitness, JobSpec,
    Matrix, Record, RepairService, StageAudit, StageOutput, StageSpec, UnknownBound,
    WorkLedger, _Work, _combine, _digest, _gram, _is_psd, _json, _mat_json,
    _metric, _q_json, _zero,
)

ZERO = Fraction(0)


def _sha(payload: bytes) -> str:
    return sha256(payload).hexdigest()


def _valid_digest(value: str) -> bool:
    return (type(value) is str and len(value) == 64
            and all(c in "0123456789abcdef" for c in value))


@dataclass(frozen=True)
class ContributionBinding:
    stage_id: str
    available: bool
    contribution_digest: str

    def _json(self) -> list[object]:
        return [self.stage_id, self.available, self.contribution_digest]


@dataclass(frozen=True)
class AggregateRecord:
    record_id: str
    content_digest: str
    group_id: int
    contributions: tuple[ContributionBinding, ...]

    def _json(self) -> dict[str, object]:
        return {"id": self.record_id, "content_sha256": self.content_digest,
                "group": self.group_id, "contributions": [x._json() for x in self.contributions]}


@dataclass(frozen=True)
class AggregateStage:
    stage_id: str
    response: LinearResponseIndex | None
    error: ResponseIndex | None
    unavailable_count: int

    @property
    def stored_rational_count(self) -> int:
        if self.response is None:
            return 0
        return self.response.stored_rational_count + sum(len(x) * len(x[0]) for x in self.error.cross_moments)

    def _json(self) -> dict[str, object]:
        return {"stage": self.stage_id, "unavailable": self.unavailable_count,
                "response": None if self.response is None else self.response.canonical_bytes().decode("ascii"),
                "error": None if self.error is None else self.error.canonical_bytes().decode("ascii")}


@dataclass(frozen=True)
class AggregateGroup:
    group_id: int
    record_ids: tuple[str, ...]
    membership_digest: str
    stages: tuple[AggregateStage, ...]

    def _json(self) -> dict[str, object]:
        return {"group": self.group_id, "ids": self.record_ids,
                "membership_digest": self.membership_digest,
                "stages": [s._json() for s in self.stages]}


@dataclass(frozen=True)
class AggregateState:
    manifest_digest: str
    model: tuple[StageOutput, ...]
    records: tuple[AggregateRecord, ...]
    groups: tuple[AggregateGroup, ...]

    @property
    def retained_ids(self) -> tuple[str, ...]:
        return tuple(r.record_id for r in self.records)

    @property
    def stored_aggregate_rational_count(self) -> int:
        """Matrix scalar slots; excludes model, metadata, and integer bit lengths."""
        return sum(s.stored_rational_count for g in self.groups for s in g.stages)

    def canonical_bytes(self) -> bytes:
        return _json({"schema": "aggregate-linear-service-v1", "manifest": self.manifest_digest,
                      "model": [o._json() for o in self.model],
                      "records": [r._json() for r in self.records],
                      "groups": [g._json() for g in self.groups]})

    @property
    def digest(self) -> str:
        return _sha(self.canonical_bytes())


@dataclass(frozen=True)
class AggregateGroupContext:
    """A proposal receives aggregate statistics and the new certified prefix.

    No retained record list, descriptor, jet, or source payload is exposed.
    Empty ``index.records`` tuples indicate aggregate arithmetic, not an empty
    data group. ``record_count`` and ``unavailable_count`` describe membership.
    The service checked each descriptor's scalar column count at extraction.
    """
    binding: GroupBinding
    stage: StageSpec
    prefix: CertifiedPrefix
    group_id: int
    record_count: int
    unavailable_count: int
    response: LinearResponseIndex | None
    error: ResponseIndex | None


@dataclass(frozen=True)
class AggregateServiceResult:
    state: AggregateState
    ledger: WorkLedger
    stages: tuple[StageAudit, ...]


IntrinsicExtractor = Callable[[Record, StageSpec], tuple[LinearRecordMoments, RecordMoments] | None]
AggregateQuery = Callable[[AggregateGroupContext], ResponseQuery | UnknownBound]


@dataclass(frozen=True, init=False)
class AggregateRepairService:
    """Complete exact model service with group-only response matrices.

    ``job.manifest_digest`` binds target prefixes. ``manifest_digest`` also
    binds this service's distinct canonical-state schema and fixed extractor.
    The independent direct ``fresh`` path is a correctness oracle. It is not
    claimed as the fastest equally indexed baseline. A fresh solver may use
    the same intrinsic response statistics and certificates.
    """
    job: JobSpec
    evaluator: FeatureEvaluator
    intrinsic_moments: IntrinsicExtractor
    contracts: Mapping[str, ResponseStageContract]
    query: AggregateQuery
    provider_id: str
    extractor_id: str
    manifest_digest: str
    _engine: RepairService

    def __init__(self, job: JobSpec, evaluator: FeatureEvaluator,
                 intrinsic_moments: IntrinsicExtractor,
                 contracts: Mapping[str, ResponseStageContract], query: AggregateQuery,
                 *, provider_id: str, extractor_id: str) -> None:
        if not isinstance(job, JobSpec) or not all(callable(x) for x in (evaluator, intrinsic_moments, query)):
            raise TypeError("supply JobSpec and callable evaluator/extractor/query")
        if any(type(x) is not str or not x for x in (provider_id, extractor_id)):
            raise ValueError("provider and extractor identities must be nonempty strings")
        fixed = dict(contracts)
        known = {s.stage_id: s for s in job.stages}
        if not set(fixed) <= set(known):
            raise ValueError("response contract names a stage outside the target")
        for key, contract in fixed.items():
            if not isinstance(contract, ResponseStageContract) or contract.response_basis.rows != known[key].width:
                raise ValueError("response contract dimension differs from the stage")
        payload = {"schema": "aggregate-linear-service-v1", "target_manifest": job.manifest_digest,
                   "extractor_id": extractor_id, "provider_id": provider_id,
                   "contracts": {key: {"response": c.response_basis._payload(), "error": c.error_basis._payload(),
                                       "max_squared_coefficient_norm": None if c.max_squared_coefficient_norm is None
                                       else _q_json(c.max_squared_coefficient_norm)} for key, c in fixed.items()}}
        for key, value in {"job": job, "evaluator": evaluator, "intrinsic_moments": intrinsic_moments,
                           "contracts": MappingProxyType(fixed), "query": query, "provider_id": provider_id,
                           "extractor_id": extractor_id, "manifest_digest": _digest(payload),
                           "_engine": RepairService(job, evaluator, lambda r, s: None)}.items():
            object.__setattr__(self, key, value)

    @property
    def target_manifest_digest(self) -> str:
        return self.job.manifest_digest

    def _empty(self, stage: StageSpec) -> AggregateStage:
        contract = self.contracts.get(stage.stage_id)
        if contract is None:
            return AggregateStage(stage.stage_id, None, None, 0)
        return AggregateStage(stage.stage_id, LinearResponseIndex.from_records(contract.response_basis, ()),
                              ResponseIndex.from_records(contract.error_basis, ()), 0)

    def _extract(self, record: Record, stage: StageSpec, work: _Work,
                 event: str, source_digest: str) -> tuple[ContributionBinding, tuple[LinearRecordMoments, RecordMoments] | None]:
        contract = self.contracts.get(stage.stage_id)
        pair = None
        if contract is not None:
            work.add(event)
            pair = self.intrinsic_moments(record, stage)
        if pair is None:
            digest = _digest({"schema": "aggregate-contribution-unavailable-v1", "id": record.record_id,
                              "content": source_digest, "stage": stage.stage_id,
                              "extractor": self.extractor_id})
            return ContributionBinding(stage.stage_id, False, digest), None
        if (not isinstance(pair, tuple) or len(pair) != 2 or not isinstance(pair[0], LinearRecordMoments)
                or not isinstance(pair[1], RecordMoments)):
            raise TypeError("extractor must return LinearRecordMoments, RecordMoments, or None")
        response, error = pair
        if response.basis != contract.response_basis or error.basis != contract.error_basis:
            raise ValueError("intrinsic contribution uses a different fixed basis")
        if any(x.record_id != record.record_id or x.source_digest != source_digest for x in pair):
            raise ValueError("intrinsic contribution does not bind the source record")
        if error.columns != 1:
            raise ValueError("error descriptor requires one scalar column per record")
        if any(x[0][0] < 0 for x in error.cross_moments):
            raise ValueError("intrinsic error moments must be nonnegative")
        # A digest binds all intrinsic contribution values without storing them.
        encoded = _json({"response": response.canonical_bytes().decode("ascii"),
                         "error": error.canonical_bytes().decode("ascii")})
        work.add("contribution_digest_bytes", len(encoded))
        return ContributionBinding(stage.stage_id, True, _sha(encoded)), pair

    def _add(self, aggregate: AggregateStage,
             pair: tuple[LinearRecordMoments, RecordMoments] | None,
             sign: int, work: _Work) -> AggregateStage:
        if pair is None:
            return AggregateStage(aggregate.stage_id, aggregate.response, aggregate.error,
                                  aggregate.unavailable_count + sign)
        response, error = pair
        current, descriptors = aggregate.response, aggregate.error
        if current is None or descriptors is None:
            raise ValueError("available moments lack an aggregate contract")
        constant = _combine(current.constant_gram, response.constant_gram, sign, work)
        first = tuple(_combine(x, y, sign, work) for x, y in zip(current.first_response, response.first_response))
        tangent = _combine(current.tangent_scalar_gram, response.tangent_scalar_gram, sign, work)
        cross = tuple(_combine(x, y, sign, work) for x, y in zip(descriptors.cross_moments, error.cross_moments))
        return AggregateStage(aggregate.stage_id,
                              LinearResponseIndex(current.basis, constant, first, tangent, ()),
                              ResponseIndex(descriptors.basis, cross, ()), aggregate.unavailable_count)

    def _groups(self, records: tuple[AggregateRecord, ...],
                totals: Mapping[int, Mapping[str, AggregateStage]], work: _Work) -> tuple[AggregateGroup, ...]:
        members: dict[int, list[AggregateRecord]] = {}
        for record in records:
            work.add("metadata_membership_rebuild_entries")
            members.setdefault(record.group_id, []).append(record)
        groups = []
        for gid, items in sorted(members.items()):
            encoded = _json([r._json() for r in items])
            work.add("metadata_membership_hash_bytes", len(encoded))
            groups.append(AggregateGroup(gid, tuple(x.record_id for x in items), _sha(encoded),
                                         tuple(totals[gid][s.stage_id] for s in self.job.stages)))
        return tuple(groups)

    def _finish(self, records: tuple[AggregateRecord, ...], groups: tuple[AggregateGroup, ...],
                outputs: tuple[StageOutput, ...], audits: tuple[StageAudit, ...], work: _Work) -> AggregateServiceResult:
        state = AggregateState(self.manifest_digest, outputs, records, groups)
        work.add("committed_record_entries", len(records))
        work.add("metadata_serialized_entries", len(records))
        work.add("committed_model_coordinates", sum(len(o.codes) * len(o.codes[0]) for o in outputs))
        work.add("canonical_serialized_bytes", len(state.canonical_bytes()))
        work.add("committed_aggregate_rational_entries", state.stored_aggregate_rational_count)
        return AggregateServiceResult(state, work.freeze(), audits)

    def fresh(self, records: Iterable[Record]) -> AggregateServiceResult:
        """Construct canonical aggregates and independently evaluate the target."""
        work = _Work()
        data: dict[str, Record] = {}
        for record in records:
            if not isinstance(record, Record) or record.record_id in data:
                raise ValueError("fresh records must be unique Record values")
            data[record.record_id] = record
            work.add("fresh_input_records")
            work.add("content_hash_bytes", len(record.payload))
        totals: dict[int, dict[str, AggregateStage]] = {}
        metadata = []
        for rid in sorted(data):
            record = data[rid]
            gid = self._engine._group(rid)
            if gid not in totals:
                totals[gid] = {s.stage_id: self._empty(s) for s in self.job.stages}
            by_stage = totals[gid]
            source_digest = record.content_digest
            bindings = []
            for stage in self.job.stages:
                binding, pair = self._extract(record, stage, work, "intrinsic_setup_extractor_calls", source_digest)
                bindings.append(binding)
                by_stage[stage.stage_id] = self._add(by_stage[stage.stage_id], pair, 1, work)
            metadata.append(AggregateRecord(rid, source_digest, gid, tuple(bindings)))
        meta = tuple(metadata)
        groups = self._groups(meta, totals, work)
        outputs, audits = [], []
        for stage in self.job.stages:
            prefix = self._engine._prefix(stage, outputs)
            raw = _zero(stage.width)
            for rid in sorted(data):
                x = self._engine._target(data[rid], stage, prefix, work, "fresh_target_evaluator_calls")
                raw = _combine(raw, _gram(x, work), 1, work)
            outputs.append(self._engine._quantize(stage, raw, work))
            audits.append(StageAudit(stage.stage_id, prefix.digest, "independent_fresh", 0, (), (), None))
        return self._finish(meta, groups, tuple(outputs), tuple(audits), work)

    def _validate(self, state: AggregateState, work: _Work) -> None:
        if not isinstance(state, AggregateState) or state.manifest_digest != self.manifest_digest:
            raise ValueError("aggregate state uses a different service manifest")
        if (type(state.records) is not tuple or type(state.groups) is not tuple or type(state.model) is not tuple
                or state.retained_ids != tuple(sorted(set(state.retained_ids)))):
            raise ValueError("aggregate state must contain canonical immutable tuples")
        stage_ids = tuple(s.stage_id for s in self.job.stages)
        if tuple(o.stage_id for o in state.model) != stage_ids:
            raise ValueError("state model has different stages")
        for output, stage in zip(state.model, self.job.stages):
            if (len(output.codes) != len(stage.weights) or any(len(r) != stage.width for r in output.codes)
                    or any(x not in stage.grids[j] for row in output.codes for j, x in enumerate(row))):
                raise ValueError("state model violates target shapes or grids")
        members: dict[int, list[AggregateRecord]] = {}
        for record in state.records:
            work.add("validated_record_entries")
            if (not isinstance(record, AggregateRecord) or type(record.record_id) is not str or not record.record_id
                    or not _valid_digest(record.content_digest) or record.group_id != self._engine._group(record.record_id)
                    or type(record.contributions) is not tuple
                    or tuple(x.stage_id for x in record.contributions) != stage_ids):
                raise ValueError("invalid aggregate record metadata")
            if any(not isinstance(x, ContributionBinding) or type(x.available) is not bool
                   or not _valid_digest(x.contribution_digest) for x in record.contributions):
                raise ValueError("invalid contribution binding")
            members.setdefault(record.group_id, []).append(record)
        if tuple(g.group_id for g in state.groups) != tuple(sorted(members)):
            raise ValueError("groups must be the canonical nonempty groups")
        for group in state.groups:
            items = members[group.group_id]
            work.add("validated_membership_entries", len(items))
            encoded = _json([r._json() for r in items])
            work.add("metadata_validation_hash_bytes", len(encoded))
            if (type(group.record_ids) is not tuple or type(group.stages) is not tuple
                    or group.record_ids != tuple(r.record_id for r in items)
                    or group.membership_digest != _sha(encoded)
                    or tuple(s.stage_id for s in group.stages) != stage_ids):
                raise ValueError("group membership or aggregate stage order is invalid")
            for index, (aggregate, stage) in enumerate(zip(group.stages, self.job.stages)):
                absent = sum(not r.contributions[index].available for r in items)
                if type(aggregate.unavailable_count) is not int or aggregate.unavailable_count != absent:
                    raise ValueError("unavailable count differs from record metadata")
                contract = self.contracts.get(stage.stage_id)
                if contract is None:
                    if aggregate.response is not None or aggregate.error is not None or absent != len(items):
                        raise ValueError("unsupported stage has claimed response evidence")
                    continue
                response, error = aggregate.response, aggregate.error
                if (not isinstance(response, LinearResponseIndex) or not isinstance(error, ResponseIndex)
                        or response.records or error.records
                        or response.basis != contract.response_basis or error.basis != contract.error_basis):
                    raise ValueError("aggregate basis differs or contains per-record bindings")
                if any(x[0][0] < 0 for x in error.cross_moments):
                    raise ValueError("negative aggregate error moment")
                if not _is_psd(response.constant_gram) or (response.tangent_scalar_gram
                                                         and not _is_psd(response.tangent_scalar_gram)):
                    raise ValueError("aggregate response norm matrices are not PSD")
                work.add("aggregate_psd_validation_calls", 1 + bool(response.tangent_scalar_gram))
                work.add("validated_aggregate_rational_entries", aggregate.stored_rational_count)

    def _delete(self, state: AggregateState, deleted: tuple[Record, ...], work: _Work
                ) -> tuple[tuple[AggregateRecord, ...], tuple[AggregateGroup, ...]]:
        metadata = {r.record_id: r for r in state.records}
        remove = set()
        for record in deleted:
            if not isinstance(record, Record) or record.record_id in remove:
                raise ValueError("deletion records must be unique Record values")
            old = metadata.get(record.record_id)
            if old is None:
                raise ValueError("deletion record is not retained")
            work.add("content_hash_bytes", len(record.payload))
            if record.content_digest != old.content_digest:
                raise ValueError("deleted source content differs from committed content")
            remove.add(record.record_id)
        totals = {g.group_id: {s.stage_id: s for s in g.stages} for g in state.groups}
        for record in sorted(deleted, key=lambda x: x.record_id):
            old = metadata[record.record_id]
            for stage, old_binding in zip(self.job.stages, old.contributions):
                binding, pair = self._extract(record, stage, work, "deleted_intrinsic_extractor_calls", old.content_digest)
                if binding != old_binding:
                    raise ValueError("regenerated contribution differs from committed digest")
                totals[old.group_id][stage.stage_id] = self._add(totals[old.group_id][stage.stage_id], pair, -1, work)
        retained = tuple(x for x in state.records if x.record_id not in remove)
        work.add("metadata_deletion_filter_entries", len(state.records))
        work.add("logically_removed_record_entries", len(remove))
        return retained, self._groups(retained, totals, work)

    def _proposal(self, group: AggregateGroup, aggregate: AggregateStage, stage: StageSpec,
                  prefix: CertifiedPrefix, work: _Work) -> tuple[Matrix, tuple[Fraction, Fraction] | None]:
        raw = _zero(stage.width) if aggregate.response is None else aggregate.response.constant_gram
        if aggregate.unavailable_count or aggregate.response is None:
            work.add("unavailable_aggregate_groups")
            return raw, None
        digest = _digest(_mat_json(raw))
        # This digest reads group matrices, never a retained descriptor list.
        aggregate_payload = _json(aggregate._json())
        work.add("proposal_aggregate_digest_bytes", len(aggregate_payload))
        binding = GroupBinding(self.target_manifest_digest, stage.stage_id, prefix.digest,
                               self.job.reference_id, group.group_id,
                               _digest([group.membership_digest, _sha(aggregate_payload)]), digest, digest)
        context = AggregateGroupContext(binding, stage, prefix, group.group_id, len(group.record_ids),
                                        aggregate.unavailable_count, aggregate.response, aggregate.error)
        work.add("aggregate_query_calls")
        request = self.query(context)
        if isinstance(request, UnknownBound):
            return raw, None
        if not isinstance(request, ResponseQuery) or request.binding != binding:
            raise InvalidWitness("aggregate response query has a stale group, target, or prefix")
        contract = self.contracts[stage.stage_id]
        if len(request.coefficients) != contract.response_basis.terms - 1:
            raise InvalidWitness("aggregate response query has the wrong coefficient count")
        radius = contract.max_squared_coefficient_norm
        if radius is not None and sum((a * a for a in request.coefficients), ZERO) > radius:
            work.add("out_of_chart_aggregate_groups")
            return raw, None
        # Empty record maps avoid O(N) identity loops in the arithmetic module.
        # Source/columns/basis checks occurred at intrinsic extraction above.
        work.add("aggregate_contraction_calls")
        work.add("proposal_aggregate_rational_entries", aggregate.stored_rational_count)
        bound = shifted_linear_response_bound(aggregate.response, aggregate.error, request.coefficients,
                                              stage.ridge, 1, request.unrepresented_parameter_norm)
        raw = bound.raw_surrogate_gram
        work.add("proposal_psd_validation_calls")
        if not _is_psd(raw):
            raise InvalidWitness("aggregate response proposal is not PSD")
        beta, delta = bound.omitted_psd_trace_normalized, bound.response_gram_error_normalized
        return raw, (beta + delta, delta)

    def repair(self, state: AggregateState, deleted_records: Iterable[Record],
               retained_source: Callable[[str], Record]) -> AggregateServiceResult:
        """Return a fresh-identical complete state or fail without a mutation."""
        work = _Work()
        self._validate(state, work)
        if not callable(retained_source):
            raise TypeError("retained source must be callable")
        retained, groups = self._delete(state, tuple(deleted_records), work)
        metadata = {r.record_id: r for r in retained}
        cache: dict[str, Record] = {}
        def read(rid: str) -> Record:
            if rid not in metadata:
                raise ValueError("attempted a non-retained source access")
            if rid not in cache:
                work.add("retained_source_record_reads")
                record = retained_source(rid)
                if not isinstance(record, Record) or record.record_id != rid:
                    raise ValueError("retained source returned a different ID")
                work.add("content_hash_bytes", len(record.payload))
                if record.content_digest != metadata[rid].content_digest:
                    raise ValueError("retained source content differs from committed content")
                cache[rid] = record
            return cache[rid]
        outputs, audits = [], []
        group_map = {g.group_id: g for g in groups}
        for stage_index, stage in enumerate(self.job.stages):
            prefix = self._engine._prefix(stage, outputs)
            raw = _zero(stage.width)
            proposals, bounds = {}, {}
            for group in groups:
                proposal, bound = self._proposal(group, group.stages[stage_index], stage, prefix, work)
                proposals[group.group_id], bounds[group.group_id] = proposal, bound
                raw = _combine(raw, proposal, 1, work)
            unknown = tuple(gid for gid, bound in bounds.items() if bound is None)
            replayed, attempts = [], 0
            while True:
                if not bounds:
                    outputs.append(self._engine._quantize(stage, raw, work))
                    route = "exact_replay"
                    break
                if all(b is not None for b in bounds.values()):
                    negative = sum((b[0] for b in bounds.values()), ZERO)
                    positive = sum((b[1] for b in bounds.values()), ZERO)
                    lo = 1 - negative / stage.normalization / stage.ridge
                    hi = 1 + positive / stage.normalization / stage.ridge
                    work.add("enclosure_scalar_divisions", 4)
                    if lo > 0:
                        attempts += 1
                        work.add("certificate_factorization_calls")
                        work.add("rounding_decisions", len(stage.weights) * stage.width)
                        work.add("cell_predicates", len(stage.weights) * stage.width)
                        certificate = certify_relative_enclosure(stage.weights, _metric(raw, stage, work), stage.grids, lo, hi)
                        if certificate.accepted:
                            outputs.append(StageOutput(stage.stage_id, certificate.candidate.codes))
                            route = "transport_certificate"
                            break
                work.add("group_selection_entries", len(bounds))
                missing = [gid for gid, b in bounds.items() if b is None]
                chosen = min(missing) if missing else min(bounds, key=lambda gid: (-sum(bounds[gid]), gid))
                actual = _zero(stage.width)
                for rid in group_map[chosen].record_ids:
                    x = self._engine._target(read(rid), stage, prefix, work, "retained_replay_evaluator_calls")
                    actual = _combine(actual, _gram(x, work), 1, work)
                raw = _combine(_combine(raw, proposals[chosen], -1, work), actual, 1, work)
                del bounds[chosen]
                replayed.append(chosen)
            audits.append(StageAudit(stage.stage_id, prefix.digest, route, attempts,
                                     tuple(replayed), unknown, self.provider_id))
        return self._finish(retained, groups, tuple(outputs), tuple(audits), work)


__all__ = ["ContributionBinding", "AggregateRecord", "AggregateStage", "AggregateGroup",
           "AggregateState", "AggregateGroupContext", "AggregateServiceResult", "AggregateRepairService"]
