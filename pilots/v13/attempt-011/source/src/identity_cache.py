"""Exact original-model feature caching for a fixed sequential target.

This optional state interface differs from the aggregate-response interface.
It stores true sequential Grams under its current quantized model. A request
reuses a Gram only when all relevant old and new ancestors agree exactly.
Changed ancestors force retained feature replay. Every result refreshes the
cache to the same bytes produced by a direct retained-data construction.

Cache origins require a trusted digest or authenticated storage. A digest
supplied by an attacker is not authentication. The deterministic evaluator
and its declared dependency graph remain trusted premises.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Callable, Iterable

from .aggregate_response_service import StateParseLimits, _StateParser
from .exact_core import sequential_oracle
from .repair_service import (
    CertifiedPrefix, FeatureEvaluator, JobSpec, Matrix, Record, StageOutput,
    StageSpec, WorkLedger, _Work, _combine, _gram, _is_psd, _json, _mat_json,
    _matrix, _metric, _zero,
)
from .service_telemetry import event, operation, timed


def _digest(value: str) -> str:
    if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('expected a lowercase SHA256 digest')
    return value


@dataclass(frozen=True)
class CacheRecord:
    record_id: str
    content_digest: str

    def __post_init__(self):
        if type(self.record_id) is not str or not self.record_id:
            raise ValueError('cache record ID must be nonempty text')
        _digest(self.content_digest)

    def payload(self):
        return {'id': self.record_id, 'content_sha256': self.content_digest}


@dataclass(frozen=True)
class CachedStage:
    stage_id: str
    prefix_digest: str
    raw_gram: Matrix

    def __post_init__(self):
        if type(self.stage_id) is not str or not self.stage_id:
            raise ValueError('cache stage ID must be nonempty text')
        _digest(self.prefix_digest)
        object.__setattr__(self, 'raw_gram', _matrix(self.raw_gram, 'cached raw Gram'))

    def payload(self):
        return {'stage_id': self.stage_id, 'prefix_sha256': self.prefix_digest,
                'raw_gram': _mat_json(self.raw_gram)}


@dataclass(frozen=True)
class IdentityCacheState:
    manifest_digest: str
    model: tuple[StageOutput, ...]
    records: tuple[CacheRecord, ...]
    stages: tuple[CachedStage, ...]

    def __post_init__(self):
        _digest(self.manifest_digest)
        for name, kind in (('model', StageOutput), ('records', CacheRecord), ('stages', CachedStage)):
            values = tuple(getattr(self, name))
            if any(not isinstance(x, kind) for x in values):
                raise TypeError(f'{name} contains an invalid value')
            object.__setattr__(self, name, values)

    @property
    def retained_ids(self) -> tuple[str, ...]:
        return tuple(r.record_id for r in self.records)

    @timed('cache_serialization')
    def canonical_bytes(self) -> bytes:
        return _json({'schema': 'original-model-gram-cache-v1', 'manifest': self.manifest_digest,
                      'model': [o._json() for o in self.model],
                      'records': [r.payload() for r in self.records],
                      'stages': [s.payload() for s in self.stages]})

    @property
    def digest(self) -> str:
        return sha256(self.canonical_bytes()).hexdigest()

    @property
    def stored_gram_rationals(self) -> int:
        return sum(len(row) for stage in self.stages for row in stage.raw_gram)

    @property
    def stored_aggregate_rational_count(self) -> int:
        """Runner-compatible count for this separate optional cache interface."""
        return self.stored_gram_rationals

    @property
    def stored_model_rationals(self) -> int:
        return sum(len(row) for output in self.model for row in output.codes)

    @property
    def stored_integer_bits(self) -> int:
        values = (value for matrix in (*[s.raw_gram for s in self.stages],
                                      *[o.codes for o in self.model]) for row in matrix for value in row)
        return sum(abs(v.numerator).bit_length() + v.denominator.bit_length() for v in values)

    @classmethod
    def from_canonical_bytes(cls, payload: bytes, *, limits: StateParseLimits | None = None):
        """Bounded syntax parsing. This operation does not authenticate origin."""
        p = _StateParser(StateParseLimits() if limits is None else limits)
        data = p._object(p._load(payload), ('schema', 'manifest', 'model', 'records', 'stages'))
        if data['schema'] != 'original-model-gram-cache-v1':
            raise ValueError('unsupported identity cache schema')
        outputs = []
        for item in p._array(data['model'], p.limits.max_stages):
            item = p._object(item, ('stage_id', 'codes'))
            rows = p._array(item['codes'], p.limits.max_width)
            if not rows:
                raise ValueError('cached model must contain nonempty matrices')
            first = p._array(rows[0], p.limits.max_width)
            outputs.append(StageOutput(p._text(item['stage_id']), p._matrix(rows, len(rows), len(first))))
        records = []
        for item in p._array(data['records'], p.limits.max_records):
            item = p._object(item, ('id', 'content_sha256'))
            records.append(CacheRecord(p._text(item['id']), p._digest(item['content_sha256'])))
        stages = []
        for item in p._array(data['stages'], p.limits.max_stages):
            item = p._object(item, ('stage_id', 'prefix_sha256', 'raw_gram'))
            rows = p._array(item['raw_gram'], p.limits.max_width)
            stages.append(CachedStage(p._text(item['stage_id']), p._digest(item['prefix_sha256']),
                                      p._matrix(rows, len(rows), len(rows))))
        state = cls(p._digest(data['manifest']), tuple(outputs), tuple(records), tuple(stages))
        if state.canonical_bytes() != payload:
            raise ValueError('identity cache bytes are not canonical')
        return state


@dataclass(frozen=True)
class CacheStageAudit:
    stage_id: str
    route: str
    prefix_digest: str
    deleted_evaluations: int
    retained_evaluations: int

    @property
    def certificate_attempts(self):
        return 0

    @property
    def replayed_groups(self):
        # The optional cache has one global Gram per stage.
        return (0,) if self.route in ('changed_ancestor_replay', 'forced_full_replay') else ()

    @property
    def unknown_groups(self):
        return ()


@dataclass(frozen=True)
class IdentityCacheResult:
    state: IdentityCacheState
    ledger: WorkLedger
    stages: tuple[CacheStageAudit, ...]


@dataclass(frozen=True, init=False)
class IdentityCacheService:
    job: JobSpec
    evaluator: FeatureEvaluator
    manifest_digest: str
    _ancestors: object

    def __init__(self, job: JobSpec, evaluator: FeatureEvaluator):
        if not isinstance(job, JobSpec) or not callable(evaluator):
            raise TypeError('supply a JobSpec and a callable feature evaluator')
        ancestors = {}
        for stage in job.stages:
            closure = set(stage.dependencies)
            for dep in stage.dependencies:
                closure.update(ancestors[dep])
            ancestors[stage.stage_id] = frozenset(closure)
        sources = {name: sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                   for name in ('identity_cache.py', 'repair_service.py', 'exact_core.py',
                                'aggregate_response_service.py')}
        manifest = sha256(_json({'schema': 'identity-cache-service-v1', 'job': job.manifest_digest,
                                'sources': sources, 'identity': 'all-transitive-ancestor-exact-code-equality',
                                'state': 'true-sequential-Grams-under-current-quantized-model'})).hexdigest()
        object.__setattr__(self, 'job', job)
        object.__setattr__(self, 'evaluator', evaluator)
        object.__setattr__(self, '_ancestors', MappingProxyType(ancestors))
        object.__setattr__(self, 'manifest_digest', manifest)

    @property
    def target_manifest_digest(self):
        return self.job.manifest_digest

    @operation
    def load_state(self, payload: bytes, *, expected_digest: str,
                   limits: StateParseLimits | None = None) -> IdentityCacheState:
        state = IdentityCacheState.from_canonical_bytes(payload, limits=limits)
        self._validate(state, expected_digest, _Work())
        return state

    def _prefix(self, stage: StageSpec, outputs: Iterable[StageOutput]) -> CertifiedPrefix:
        wanted = self._ancestors[stage.stage_id]
        values = tuple(o for o in outputs if o.stage_id in wanted)
        if {o.stage_id for o in values} != wanted:
            raise ValueError('stage requires all declared transitive ancestors')
        return CertifiedPrefix(self.job.manifest_digest, values)

    @timed('cache_feature_extraction')
    def _contribution(self, record, stage, prefix, work, label):
        work.add(label)
        category = ('cache_replay_feature_evaluation' if label == 'retained_replay_evaluator_calls' else
                    'cache_deleted_feature_evaluation' if label == 'deleted_target_evaluator_calls' else
                    'cache_fresh_feature_evaluation')
        features = _matrix(timed(category)(self.evaluator)(record, stage, prefix), 'target features', stage.width, True)
        work.add('evaluated_feature_entries', sum(len(row) for row in features))
        return self._gram(features, work)

    @staticmethod
    @timed('cache_gram_accumulation')
    def _gram(features, work):
        return _gram(features, work)

    @staticmethod
    @timed('cache_gram_accumulation')
    def _combine(left, right, sign, work):
        return _combine(left, right, sign, work)

    @timed('cache_factor_rounding')
    def _quantize(self, stage, gram, work):
        work.add('exact_factorization_calls')
        work.add('rounding_decisions', len(stage.weights) * stage.width)
        return StageOutput(stage.stage_id, sequential_oracle(stage.weights, _metric(gram, stage, work),
                                                            stage.grids).codes)

    @timed('cache_validation')
    def _validate(self, state, expected_digest, work):
        _digest(expected_digest)
        if not isinstance(state, IdentityCacheState) or state.manifest_digest != self.manifest_digest:
            raise ValueError('cache belongs to a different service manifest')
        payload = state.canonical_bytes()
        work.add('input_cache_serialized_bytes', len(payload))
        work.add('input_cache_hash_bytes', len(payload))
        if sha256(payload).hexdigest() != expected_digest:
            raise ValueError('cache differs from the trusted expected digest')
        if state.retained_ids != tuple(sorted(set(state.retained_ids))):
            raise ValueError('cache record membership is not canonical')
        names = tuple(s.stage_id for s in self.job.stages)
        if tuple(s.stage_id for s in state.stages) != names or tuple(o.stage_id for o in state.model) != names:
            raise ValueError('cache stage order differs from the target')
        for stage, output, cached in zip(self.job.stages, state.model, state.stages):
            if len(output.codes) != len(stage.weights) or any(len(row) != stage.width for row in output.codes):
                raise ValueError('cache model dimensions differ from the target')
            if any(v not in stage.grids[j] for row in output.codes for j, v in enumerate(row)):
                raise ValueError('cache model code falls outside its declared grid')
            if cached.prefix_digest != self._prefix(stage, state.model).digest:
                raise ValueError('cached Gram prefix binding differs from its model')
            if len(cached.raw_gram) != stage.width or any(len(row) != stage.width for row in cached.raw_gram):
                raise ValueError('cached Gram dimensions differ from the target')
            if not _is_psd(cached.raw_gram):
                raise ValueError('cached Gram must be symmetric positive semidefinite')
            work.add('cache_psd_validation_calls')
            work.add('validated_gram_entries', stage.width * stage.width)
        work.add('validated_record_entries', len(state.records))
        work.add('input_cache_gram_rational_slots', state.stored_gram_rationals)
        work.add('input_cache_model_rational_slots', state.stored_model_rationals)
        work.add('input_cache_integer_bits', state.stored_integer_bits)

    def _finish(self, records, outputs, stages, audits, work):
        state = IdentityCacheState(self.manifest_digest, tuple(outputs), tuple(records), tuple(stages))
        work.add('committed_record_entries', len(state.records))
        work.add('committed_cache_gram_rational_slots', state.stored_gram_rationals)
        work.add('committed_model_rational_slots', state.stored_model_rationals)
        work.add('committed_cache_integer_bits', state.stored_integer_bits)
        work.add('canonical_serialized_bytes', len(state.canonical_bytes()))
        return IdentityCacheResult(state, work.freeze(), tuple(audits))

    @operation
    def fresh(self, records: Iterable[Record]) -> IdentityCacheResult:
        """Construct the model and its optional cache through direct sequential replay."""
        work, data = _Work(), {}
        for record in records:
            if not isinstance(record, Record) or record.record_id in data:
                raise ValueError('fresh records must be unique Record objects')
            data[record.record_id] = record
            work.add('fresh_input_records')
            work.add('fresh_input_payload_bytes', len(record.payload))
            work.add('content_hash_bytes', len(record.payload))
        ordered = tuple(data[k] for k in sorted(data))
        metadata = tuple(CacheRecord(r.record_id, r.content_digest) for r in ordered)
        outputs, caches, audits = [], [], []
        for stage in self.job.stages:
            prefix, gram = self._prefix(stage, outputs), _zero(stage.width)
            for record in ordered:
                gram = self._combine(gram, self._contribution(record, stage, prefix, work,
                                                             'fresh_target_evaluator_calls'), 1, work)
            caches.append(CachedStage(stage.stage_id, prefix.digest, gram))
            outputs.append(self._quantize(stage, gram, work))
            audits.append(CacheStageAudit(stage.stage_id, 'direct_fresh', prefix.digest, 0, len(ordered)))
        return self._finish(metadata, outputs, caches, audits, work)

    @operation
    def repair(self, state: IdentityCacheState, deleted: Iterable[Record],
               source: Callable[[str], Record], *, expected_digest: str,
               mode: str = 'certified') -> IdentityCacheResult:
        """Repair the target and refresh the optional cache in one immutable transaction."""
        return self._repair(state, deleted, source, expected_digest, mode)

    @operation
    def indexed_fresh(self, state: IdentityCacheState, deleted: Iterable[Record],
                      source: Callable[[str], Record], *, expected_digest: str,
                      mode: str = 'certified') -> IdentityCacheResult:
        """Give indexed fresh the same valid original cache and the identical solver.

        This comparator exposes shared information. It asserts no deletion-only gain.
        """
        return self._repair(state, deleted, source, expected_digest, mode)

    @staticmethod
    def _mode(mode):
        if type(mode) is not str or mode not in ('certified', 'identity_only', 'full_replay'):
            raise ValueError('identity cache supports certified, identity_only, and full_replay modes')
        return mode

    def _repair(self, state, deleted, source, expected_digest, mode):
        self._mode(mode)
        work = _Work()
        self._validate(state, expected_digest, work)
        if not callable(source):
            raise TypeError('retained source must be callable')
        membership = {r.record_id: r for r in state.records}
        remove = {}
        for record in deleted:
            if not isinstance(record, Record) or record.record_id in remove:
                raise ValueError('deleted records must be unique Record objects')
            if record.record_id not in membership:
                raise ValueError('deleted record is not currently retained')
            work.add('content_hash_bytes', len(record.payload))
            if record.content_digest != membership[record.record_id].content_digest:
                raise ValueError('deleted source content differs from its committed digest')
            remove[record.record_id] = record
            work.add('deleted_input_payload_bytes', len(record.payload))
        work.add('metadata_deletion_filter_entries', len(state.records))
        retained = tuple(r for r in state.records if r.record_id not in remove)
        removed = tuple(remove[k] for k in sorted(remove))
        outputs, caches, audits = [], [], []
        for stage, old in zip(self.job.stages, state.stages):
            prefix, previous = self._prefix(stage, outputs), self._prefix(stage, state.model)
            work.add('ancestor_model_coordinate_comparisons',
                     sum(len(row) for output in previous.outputs for row in output.codes))
            if not retained:
                gram, route, ndel, nret = _zero(stage.width), 'empty_retained', 0, 0
            elif mode != 'full_replay' and prefix.outputs == previous.outputs:
                gram, route, ndel, nret = old.raw_gram, 'old_ancestor_identity', len(removed), 0
                for record in removed:
                    gram = self._combine(gram, self._contribution(record, stage, previous, work,
                                                                 'deleted_target_evaluator_calls'), -1, work)
                if not _is_psd(gram):
                    raise ValueError('deleted contribution exceeds the trusted cached Gram')
                work.add('subtracted_gram_psd_validation_calls')
            else:
                route = 'forced_full_replay' if mode == 'full_replay' else 'changed_ancestor_replay'
                gram, ndel, nret = _zero(stage.width), 0, len(retained)
                for binding in retained:
                    record = self._read(source, binding, work)
                    gram = self._combine(gram, self._contribution(record, stage, prefix, work,
                                                                 'retained_replay_evaluator_calls'), 1, work)
            work.add('cache_stage_refreshes')
            event('cache.stage_route', reason=route)
            caches.append(CachedStage(stage.stage_id, prefix.digest, gram))
            outputs.append(self._quantize(stage, gram, work))
            audits.append(CacheStageAudit(stage.stage_id, route, prefix.digest, ndel, nret))
        work.add('logically_removed_record_entries', len(removed))
        return self._finish(retained, outputs, caches, audits, work)

    @staticmethod
    @timed('cache_retained_source_access')
    def _read(source, binding, work):
        work.add('retained_source_record_reads')
        record = source(binding.record_id)
        if not isinstance(record, Record) or record.record_id != binding.record_id:
            raise ValueError('retained source returned the wrong record')
        work.add('content_hash_bytes', len(record.payload))
        work.add('retained_source_payload_bytes', len(record.payload))
        if record.content_digest != binding.content_digest:
            raise ValueError('retained source content differs from its committed digest')
        return record


@dataclass(frozen=True)
class IdentityPreparedIndex:
    """Transient equal-information input, including old model and deletion payloads.

    This is not committed retained-only state. Discard it after the comparison.
    """
    original: IdentityCacheState
    deleted: tuple[Record, ...]
    expected_digest: str


@dataclass(frozen=True)
class IdentityPreparedResult:
    index: IdentityPreparedIndex
    ledger: WorkLedger


class IdentityCacheRunnerAdapter:
    """Adapt the cache interface to the existing three-method runner.

    Digests established by fresh construction or trusted loading are capabilities
    within this process. They are not persisted model state or hostile-store proof.
    """
    def __init__(self, service: IdentityCacheService, *, max_trusted_states: int = 16):
        if not isinstance(service, IdentityCacheService):
            raise TypeError('adapter requires IdentityCacheService')
        if type(max_trusted_states) is not int or max_trusted_states < 2:
            raise ValueError('adapter requires at least two trusted-origin slots')
        self.service = service
        self.job = service.job
        self.evaluator = service.evaluator
        self.manifest_digest = service.manifest_digest
        self.target_manifest_digest = service.target_manifest_digest
        self.family = 'identity_cache'
        self.service_family = 'identity_cache'
        # These are normalized runner defaults. This family uses neither tier.
        self.response_tier = 'linear'
        self.verifier_policy = 'spectral'
        self._trusted = OrderedDict()
        self.max_trusted_states = max_trusted_states

    def _remember(self, digest):
        self._trusted[digest] = None
        self._trusted.move_to_end(digest)
        while len(self._trusted) > self.max_trusted_states:
            self._trusted.popitem(last=False)

    def _accept(self, result, *, input_bytes=0):
        payload = result.state.canonical_bytes()
        self._remember(sha256(payload).hexdigest())
        work = _Work()
        work.counts.update(dict(result.ledger.counts))
        work.add('adapter_input_serialized_bytes', input_bytes)
        work.add('adapter_input_hash_bytes', input_bytes)
        work.add('adapter_output_serialized_bytes', len(payload))
        work.add('adapter_output_hash_bytes', len(payload))
        work.add('adapter_trusted_digest_entries', len(self._trusted))
        return IdentityCacheResult(result.state, work.freeze(), result.stages)

    def _expected(self, state):
        if not isinstance(state, IdentityCacheState):
            raise TypeError('identity adapter requires its own cache state')
        payload = state.canonical_bytes()
        value = sha256(payload).hexdigest()
        if value not in self._trusted:
            raise ValueError('load cache with a trusted digest before adapter use')
        self._trusted.move_to_end(value)
        return value, len(payload)

    def fresh(self, records, *, telemetry=None):
        return self._accept(self.service.fresh(records, telemetry=telemetry))

    def load_state(self, payload, *, expected_digest, limits=None):
        state = self.service.load_state(payload, expected_digest=expected_digest, limits=limits)
        self._remember(expected_digest)
        return state

    def repair(self, state, deleted, source, *, mode='certified', telemetry=None):
        expected, count = self._expected(state)
        return self._accept(self.service.repair(state, deleted, source, expected_digest=expected,
                                                mode=mode, telemetry=telemetry), input_bytes=count)

    @operation
    def prepare_index(self, state, deleted):
        """Validate shared cache inputs; defer prefix-dependent extraction to solving."""
        work = _Work()
        expected, count = self._expected(state)
        work.add('adapter_input_serialized_bytes', count)
        work.add('adapter_input_hash_bytes', count)
        self.service._validate(state, expected, work)
        deleted = tuple(deleted)
        ids = set()
        membership = {r.record_id: r.content_digest for r in state.records}
        for record in deleted:
            if not isinstance(record, Record) or record.record_id in ids:
                raise ValueError('deleted records must be unique Record objects')
            work.add('content_hash_bytes', len(record.payload))
            if membership.get(record.record_id) != record.content_digest:
                raise ValueError('deleted source differs from trusted cache membership')
            ids.add(record.record_id)
        work.add('prepared_deleted_record_entries', len(deleted))
        work.add('prepared_deleted_payload_bytes', sum(len(r.payload) for r in deleted))
        work.add('prepared_shared_cache_bytes', len(state.canonical_bytes()))
        return IdentityPreparedResult(IdentityPreparedIndex(state, deleted, expected), work.freeze())

    def indexed_fresh(self, index, source, *, mode='certified', telemetry=None):
        if not isinstance(index, IdentityPreparedIndex):
            raise TypeError('indexed fresh requires prepared identity cache inputs')
        expected, count = self._expected(index.original)
        if expected != index.expected_digest:
            raise ValueError('prepared identity cache digest changed')
        return self._accept(self.service.indexed_fresh(index.original, index.deleted, source,
                                                      expected_digest=index.expected_digest,
                                                      mode=mode, telemetry=telemetry), input_bytes=count)
