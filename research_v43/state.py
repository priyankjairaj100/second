"""Canonical complete successor state with actual payload validation.

This module serializes and compares supplied numerical results. It never
recomputes neural features, proves compressed containment, or calibrates codes.
The caller must build the fresh oracle from retained inputs independently of
the predecessor/repair state. Equality here verifies all actual canonical
bytes, not a caller-supplied equality flag or a list of matching hashes.

Records and descriptor payloads contain retained sources only. This is logical
live-state deletion, not deletion of external corpora, checkpoints, archives,
process memory, or filesystem history. Both target manifests and the retained
tokens/provenance are included in the byte count. The pretrained checkpoint
and executable dependencies remain external and must be charged separately.

Representations: lossless uses canonical V29 source-local descriptors;
compressed40 uses V26 40-bit, block-size-256 descriptors; exact_gram uses V35
pooled exact Grams; hybrid_gram uses exact Grams at widths <=768 and lossless
descriptors otherwise. Equality is within one representation and codec runtime.
Gram trust must come from trusted preparation or independent reconstruction,
never by copying a digest and source list out of the archive being checked.

Binary framing avoids base64. Serialization still retains inputs and creates
one complete output allocation; parsing copies artifact slices and invokes
bounded codec/Gram parsers. These limits are not a whole-process memory proof.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import math
import struct

from research_v42.resource_plan import BoundTarget
from research_v35.exact_gram import GramBudget, SourceCommitment, loads as load_gram
from src.compact_state import StageCodes
from src.run_store import canonical_json, strict_json

MAGIC = b'VCST43\x00\x01'
SCHEMA = 'complete-fixed-anchor-successor-v43'
REPRESENTATIONS = ('lossless', 'compressed40', 'exact_gram', 'hybrid_gram')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _digest(value):
    if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('invalid lowercase SHA-256 digest')
    return value


def _name(value):
    if type(value) is not str or not value or len(value.encode('utf-8')) > 512 or '\x00' in value:
        raise ValueError('invalid identifier')
    return value


def _object(data):
    if type(data) is not bytes:
        raise TypeError('canonical JSON must be immutable bytes')
    value = strict_json(data)
    if type(value) is not dict or canonical_json(value) != data:
        raise ValueError('canonical JSON object required')
    return value


@dataclass(frozen=True)
class StateLimits:
    max_bytes: int = 2 * 2**30
    max_header_bytes: int = 32 * 2**20
    max_records: int = 4096
    max_tokens: int = 2**20
    max_stages: int = 256
    max_descriptor_bytes: int = 128 * 2**20
    max_descriptor_values: int = 16_000_000

    def __post_init__(self):
        if any(type(v) is not int or v <= 0 for v in self.__dict__.values()):
            raise ValueError('state limits must be positive built-in integers')


@dataclass(frozen=True)
class Record:
    record_id: str
    tokens: tuple[int, ...]
    provenance: bytes

    def __post_init__(self):
        _name(self.record_id)
        if (type(self.tokens) is not tuple or not self.tokens
                or any(type(t) is not int or not 0 <= t < 2**32 for t in self.tokens)):
            raise ValueError('record tokens must be a nonempty immutable unsigned sequence')
        provenance = _object(self.provenance)
        required = {'dataset_id', 'dataset_revision', 'source_file_sha256',
                    'body_sha256', 'tokenizer_sha256'}
        allowed = required | {'split', 'normalized_text_sha256', 'selection_sha256'}
        if not required <= set(provenance) <= allowed:
            raise ValueError('record provenance fields are missing or unsupported')
        for key, value in provenance.items():
            _digest(value) if key.endswith('_sha256') else _name(value)

    @property
    def token_sha256(self):
        return sha(canonical_json(self.tokens))

    def metadata(self):
        return dict(record_id=self.record_id, tokens=list(self.tokens),
                    token_sha256=self.token_sha256, provenance=_object(self.provenance))


@dataclass(frozen=True)
class GramTrust:
    """Caller-provided authenticated preparation/rebuild commitment."""
    sha256: str
    sources: tuple[SourceCommitment, ...]

    def __post_init__(self):
        _digest(self.sha256)
        if type(self.sources) is not tuple or any(type(s) is not SourceCommitment for s in self.sources):
            raise TypeError('external Gram trust requires immutable SourceCommitment objects')


@dataclass(frozen=True)
class StateView:
    target: BoundTarget
    records: tuple[Record, ...]
    stage_codes: tuple[StageCodes, ...]
    representation: str
    source_payloads: tuple[tuple[str, str, bytes], ...]
    stage_grams: tuple[tuple[str, bytes], ...]

    def source_map(self):
        return {(sid, rid): data for sid, rid, data in self.source_payloads}

    def gram_map(self):
        return dict(self.stage_grams)


def _mode(representation, width):
    if representation not in REPRESENTATIONS:
        raise ValueError('unsupported state representation')
    if representation == 'hybrid_gram':
        return 'exact_gram' if width <= 768 else 'lossless'
    return representation


def _records(records, target, limits):
    records = tuple(records)
    if len(records) > limits.max_records or any(type(r) is not Record for r in records):
        raise ValueError('record type or count exceeds contract')
    result = tuple(sorted(records, key=lambda r: r.record_id))
    if len({r.record_id for r in result}) != len(result):
        raise ValueError('duplicate source membership')
    tokens = sum(len(r.tokens) for r in result)
    if tokens > min(target.original_tokens, limits.max_tokens):
        raise ValueError('retained tokens exceed original normalization or state limit')
    return result


def _validate_descriptor(blob, mode, binding, record, target, limits):
    if mode == 'lossless':
        from src import fixed_lossless_codec_v29 as codec
    else:
        from src import fixed_factor_codec_v26 as codec
    descriptor = codec.parse(blob, limits=codec.LoadLimits(
        max_bytes=limits.max_descriptor_bytes, max_values=limits.max_descriptor_values,
        max_tokens=limits.max_tokens))
    if (descriptor.target_sha256 != sha(target.fixed_payload)
            or descriptor.anchor_target_sha256 != sha(target.anchor_payload)
            or descriptor.record_id != record.record_id or descriptor.stage_id != binding.stage_id
            or descriptor.token_sha256 != record.token_sha256
            or descriptor.shape != (len(record.tokens), binding.width)
            or descriptor.codec_sha256 != codec.codec_binding()):
        raise ValueError('source descriptor identity, provenance, dimensions, or codec differs')
    if mode == 'compressed40':
        if descriptor.bits != 40 or descriptor.block_size != 256:
            raise ValueError('compressed40 state requires 40-bit block-size-256 descriptors')
    else:
        # The V29 parser checks canonical decoding/source identity but does
        # not reject nonfinite words created outside its trusted encoder.
        if any(not math.isfinite(x[0]) for x in struct.iter_unpack('<d', descriptor.binary64())):
            raise ValueError('source descriptor contains nonfinite feature values')


def _prepare(target, records, stage_codes, representation, source_payloads,
             stage_grams, gram_trust, gram_budget, limits):
    if type(target) is not BoundTarget or type(limits) is not StateLimits:
        raise TypeError('BoundTarget and StateLimits required')
    records = _records(records, target, limits)
    stages = target.stages
    if len(stages) > limits.max_stages:
        raise ValueError('stage count exceeds state limit')
    codes = tuple(stage_codes)
    if len(codes) != len(stages):
        raise ValueError('complete target stage codes required')
    source_payloads, stage_grams, gram_trust = dict(source_payloads or {}), dict(stage_grams or {}), dict(gram_trust or {})
    modes = [_mode(representation, stage.width) for stage in stages]
    expected_sources = {(stage.stage_id, r.record_id) for stage, mode in zip(stages, modes)
                        if mode != 'exact_gram' for r in records}
    expected_grams = {stage.stage_id for stage, mode in zip(stages, modes) if mode == 'exact_gram'}
    if set(source_payloads) != expected_sources or set(stage_grams) != expected_grams:
        raise ValueError('missing, extra, or deleted source/stage payloads')
    if set(gram_trust) != expected_grams or any(type(t) is not GramTrust for t in gram_trust.values()):
        raise ValueError('every exact Gram needs separate external preparation/rebuild trust')
    if expected_grams and type(gram_budget) is not GramBudget:
        raise TypeError('explicit GramBudget is required for exact Gram parsing')
    if any(type(blob) is not bytes for blob in (*source_payloads.values(), *stage_grams.values())):
        raise TypeError('artifact payloads must be immutable bytes')
    if sum(map(len, source_payloads.values())) + sum(map(len, stage_grams.values())) > limits.max_bytes:
        raise ValueError('artifact bytes exceed state limit')
    anchor = _object(target.anchor_payload)
    ordered_sources, ordered_grams = [], []
    for binding, code, entry, mode in zip(stages, codes, anchor['stages'], modes):
        if (type(code) is not StageCodes or code.stage_id != binding.stage_id
                or code.shape != (binding.rows, binding.width) or code.bits != binding.bits
                or code.grid_axis != 'dyadic_row' or code.scale_exponents
                or tuple(x.hex() for x in code.scale_values) != tuple(entry['row_scale_hex'])):
            raise ValueError('model stage order, shape, bits, or bound row scales differ')
        # Reconstruct to revalidate actual packed extent/padding, not metadata
        # returned by a possibly altered object.
        StageCodes(code.stage_id, code.rows, code.columns, code.grid_axis,
                   code.bits, code.scale_exponents, code.packed_indices, code.scale_values)
        if mode == 'exact_gram':
            blob, trust = stage_grams[binding.stage_id], gram_trust[binding.stage_id]
            gram = load_gram(blob, budget=gram_budget, trusted_sha256=trust.sha256,
                             expected_sources=trust.sources)
            if (gram.width != binding.width or gram.normalization != Fraction(*binding.normalization)
                    or tuple((s.source_id, s.tokens) for s in gram.sources)
                       != tuple((r.record_id, len(r.tokens)) for r in records)):
                raise ValueError('Gram source membership, tokens, width, or original normalization differs')
            ordered_grams.append((binding.stage_id, blob))
            del gram
        else:
            for record in records:
                blob = source_payloads[binding.stage_id, record.record_id]
                _validate_descriptor(blob, mode, binding, record, target, limits)
                ordered_sources.append((binding.stage_id, record.record_id, blob))
    return StateView(target, records, codes, representation, tuple(ordered_sources), tuple(ordered_grams))


def _blob(data):
    return dict(nbytes=len(data), sha256=sha(data))


def _serialize(view, limits):
    payloads = [view.target.anchor_payload, view.target.fixed_payload]
    source_map, gram_map = view.source_map(), view.gram_map()
    stages = []
    for binding, code in zip(view.target.stages, view.stage_codes):
        mode = _mode(view.representation, binding.width)
        row = dict(code=code.metadata(), representation=mode, sources=[], gram=None)
        payloads.append(code.packed_indices)
        if mode == 'exact_gram':
            blob = gram_map[binding.stage_id]
            row['gram'] = _blob(blob)
            payloads.append(blob)
        else:
            for record in view.records:
                blob = source_map[binding.stage_id, record.record_id]
                row['sources'].append(dict(record_id=record.record_id, **_blob(blob)))
                payloads.append(blob)
        stages.append(row)
    header = canonical_json(dict(schema=SCHEMA, representation=view.representation,
        anchor_target=_blob(view.target.anchor_payload), fixed_target=_blob(view.target.fixed_payload),
        records=[r.metadata() for r in view.records], stages=stages))
    if len(header) > limits.max_header_bytes or 16 + len(header) + sum(map(len, payloads)) > limits.max_bytes:
        raise ValueError('serialized state exceeds declared byte limits')
    return b''.join((MAGIC, struct.pack('<Q', len(header)), header, *payloads))


def build_state(target, records, stage_codes, representation, *, source_payloads=None,
                stage_grams=None, gram_trust=None, gram_budget=None, limits=StateLimits()):
    """Validate explicit numerical artifacts and serialize once; no regeneration."""
    view = _prepare(target, records, stage_codes, representation, source_payloads,
                    stage_grams, gram_trust, gram_budget, limits)
    return _serialize(view, limits)


def validate_state(data, *, expected_target=None, expected_records=None,
                   gram_trust=None, gram_budget=None, limits=StateLimits()):
    """Validate framing, every embedded artifact, and external Gram trust."""
    if type(data) is not bytes or type(limits) is not StateLimits:
        raise TypeError('immutable state bytes and StateLimits required')
    if not 16 <= len(data) <= limits.max_bytes or data[:8] != MAGIC:
        raise ValueError('invalid state magic or byte extent')
    length = struct.unpack_from('<Q', data, 8)[0]
    if length > limits.max_header_bytes or length > len(data) - 16:
        raise ValueError('invalid state header length')
    header = _object(data[16:16+length])
    if set(header) != {'schema', 'representation', 'anchor_target', 'fixed_target', 'records', 'stages'} or header['schema'] != SCHEMA:
        raise ValueError('unsupported state schema or header fields')
    offset = 16 + length
    def chunk(entry):
        nonlocal offset
        if type(entry) is not dict or set(entry) != {'nbytes', 'sha256'}:
            raise ValueError('invalid artifact byte descriptor')
        nbytes = entry['nbytes']
        if type(nbytes) is not int or nbytes < 0 or nbytes > len(data)-offset:
            raise ValueError('artifact length exceeds state')
        blob = data[offset:offset+nbytes]
        offset += nbytes
        if sha(blob) != _digest(entry['sha256']):
            raise ValueError('actual artifact bytes differ from commitment')
        return blob
    target = BoundTarget(chunk(header['anchor_target']), chunk(header['fixed_target']))
    if expected_target is not None and target != expected_target:
        raise ValueError('state target manifests differ from expected target')
    if type(header['records']) is not list or len(header['records']) > limits.max_records:
        raise ValueError('record metadata exceeds state limit')
    records = []
    for entry in header['records']:
        if type(entry) is not dict or set(entry) != {'record_id', 'tokens', 'token_sha256', 'provenance'} or type(entry['tokens']) is not list:
            raise ValueError('invalid record metadata')
        record = Record(entry['record_id'], tuple(entry['tokens']), canonical_json(entry['provenance']))
        if record.metadata() != entry:
            raise ValueError('record token commitment differs')
        records.append(record)
    records = tuple(records)
    if records != _records(records, target, limits):
        raise ValueError('record membership must use canonical source order')
    if expected_records is not None and records != _records(expected_records, target, limits):
        raise ValueError('state source membership or record provenance differs')
    if type(header['stages']) is not list or len(header['stages']) != len(target.stages):
        raise ValueError('complete target stage list required')
    codes, source_payloads, stage_grams = [], {}, {}
    for binding, row in zip(target.stages, header['stages']):
        if type(row) is not dict or set(row) != {'code', 'representation', 'sources', 'gram'}:
            raise ValueError('invalid state stage fields')
        mode = _mode(header['representation'], binding.width)
        if row['representation'] != mode:
            raise ValueError('stage representation violates declared policy')
        meta = row['code']
        expected_keys = {'stage_id', 'rows', 'columns', 'grid_axis', 'bits', 'nbytes', 'sha256', 'scale_values_hex'}
        if type(meta) is not dict or set(meta) != expected_keys or type(meta['scale_values_hex']) is not list:
            raise ValueError('invalid complete-stage code metadata')
        packed = chunk({k: meta[k] for k in ('nbytes', 'sha256')})
        code = StageCodes(meta['stage_id'], meta['rows'], meta['columns'], meta['grid_axis'],
            meta['bits'], (), packed, tuple(float.fromhex(x) for x in meta['scale_values_hex']))
        if code.metadata() != meta:
            raise ValueError('noncanonical stage code metadata')
        codes.append(code)
        if mode == 'exact_gram':
            if row['sources'] != []:
                raise ValueError('Gram stage must not retain descriptor payloads')
            stage_grams[binding.stage_id] = chunk(row['gram'])
        else:
            if row['gram'] is not None or type(row['sources']) is not list or len(row['sources']) != len(records):
                raise ValueError('descriptor source extent differs')
            for record, entry in zip(records, row['sources']):
                if type(entry) is not dict or set(entry) != {'record_id', 'nbytes', 'sha256'} or entry['record_id'] != record.record_id:
                    raise ValueError('descriptor source membership/order differs')
                source_payloads[binding.stage_id, record.record_id] = chunk({k: entry[k] for k in ('nbytes', 'sha256')})
    if offset != len(data):
        raise ValueError('trailing or unaccounted state payloads')
    return _prepare(target, records, codes, header['representation'], source_payloads,
                    stage_grams, gram_trust, gram_budget, limits)


def _retained(previous, deleted_ids):
    deleted = tuple(deleted_ids)
    if any(type(r) is not str for r in deleted) or len(set(deleted)) != len(deleted):
        raise ValueError('deletion IDs must be unique strings')
    if not set(deleted) <= {r.record_id for r in previous.records}:
        raise ValueError('deletion request contains an absent source')
    return tuple(r for r in previous.records if r.record_id not in set(deleted))


def delete_state(previous, deleted_ids, new_stage_codes, *, stage_grams=None,
                 previous_gram_trust=None, gram_trust=None, gram_budget=None, limits=StateLimits()):
    """Keep retained descriptors; accept supplied recalibrated codes/new Grams.

    This performs no numerical repair. Updated pooled Grams must have external
    trust from checked exact subtraction or independent fresh reconstruction.
    """
    old = validate_state(previous, gram_trust=previous_gram_trust, gram_budget=gram_budget, limits=limits)
    records = _retained(old, deleted_ids)
    kept = {r.record_id for r in records}
    sources = {key: value for key, value in old.source_map().items() if key[1] in kept}
    return build_state(old.target, records, new_stage_codes, old.representation,
        source_payloads=sources, stage_grams=stage_grams, gram_trust=gram_trust,
        gram_budget=gram_budget, limits=limits)


def compare_fresh(candidate, fresh, *, candidate_gram_trust=None, fresh_gram_trust=None,
                  gram_budget=None, limits=StateLimits()):
    """Compare validated actual complete bytes within one representation."""
    left = validate_state(candidate, gram_trust=candidate_gram_trust, gram_budget=gram_budget, limits=limits)
    right = validate_state(fresh, expected_target=left.target, expected_records=left.records,
        gram_trust=fresh_gram_trust, gram_budget=gram_budget, limits=limits)
    if left.representation != right.representation:
        raise ValueError('canonical state equality requires the same representation')
    if candidate != fresh:
        raise ValueError('complete canonical successor bytes differ from fresh reconstruction')
    return dict(schema='complete-state-equality-v43', actual_bytes_equal=True,
        state_sha256=sha(candidate), state_bytes=len(candidate), stages=len(left.stage_codes),
        code_count=sum(c.rows*c.columns for c in left.stage_codes),
        retained_records=len(left.records), retained_tokens=sum(len(r.tokens) for r in left.records),
        representation=left.representation, independently_regenerated_features_verified_here=False,
        scope='All supplied artifact bytes validated and compared. Caller owns independent numerical reconstruction.')


def verify_successor(previous, candidate, fresh, deleted_ids, *, previous_gram_trust=None,
                     candidate_gram_trust=None, fresh_gram_trust=None,
                     gram_budget=None, limits=StateLimits()):
    """Check precise deletion semantics, unchanged provenance, and fresh bytes."""
    deleted_ids = tuple(deleted_ids)
    old = validate_state(previous, gram_trust=previous_gram_trust, gram_budget=gram_budget, limits=limits)
    kept = _retained(old, deleted_ids)
    new = validate_state(candidate, expected_target=old.target, expected_records=kept,
        gram_trust=candidate_gram_trust, gram_budget=gram_budget, limits=limits)
    if new.representation != old.representation:
        raise ValueError('deletion cannot silently change representation')
    old_sources = old.source_map()
    if any(old_sources.get(key) != blob for key, blob in new.source_map().items()):
        raise ValueError('source-local retained descriptors changed during deletion')
    result = compare_fresh(candidate, fresh, candidate_gram_trust=candidate_gram_trust,
        fresh_gram_trust=fresh_gram_trust, gram_budget=gram_budget, limits=limits)
    return dict(result, exact_retained_membership_verified=True, deleted_count=len(deleted_ids))
