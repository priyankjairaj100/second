"""Version 29 lossless factors and complete fixed-feature model codes.

Exact decompression preserves every stored source bit. Trusted provenance
still establishes that the declared decoder produced those source features.
"""
from dataclasses import dataclass
import hashlib
import json
import struct

from .anchor_state import LoadLimits
from .compact_state import (
    CompactState, LoadLimits as ModelLimits, _digest, _name, _json,
    token_digest, serialize as encode_model, parse as decode_model,
)
from .fixed_lossless_codec_v29 import (
    LosslessFactorDescriptor, LoadLimits as CodecLimits, codec_binding,
    encode_factor, serialize as encode_descriptor, parse as decode_descriptor,
)
from .fixed_factor_state import FixedFactorState, FixedFactorLeaf, FactorBlock

FAMILY = 'fixed_anchor_calibration_v1'
STORAGE_SCHEMA = 'source_local_lossless_factors_v1'
MAGIC = b'VCLS\x01\x00\x00\x00'
_BINDINGS = ('target_sha256', 'anchor_target_sha256', 'decoder_sha256',
             'provider_sha256', 'anchor_sha256', 'preparer_sha256', 'codec_sha256')


def _sha(data):
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class LosslessFactorLeaf:
    record_id: str
    tokens: tuple
    descriptors: tuple

    def __post_init__(self):
        _name(self.record_id)
        tokens, descriptors = tuple(self.tokens), tuple(self.descriptors)
        token_sha256 = token_digest(tokens)
        if not descriptors or any(type(d) is not LosslessFactorDescriptor for d in descriptors):
            raise TypeError('lossless leaves require complete LosslessFactorDescriptor objects')
        if len({d.stage_id for d in descriptors}) != len(descriptors):
            raise ValueError('duplicate lossless factor stage')
        for descriptor in descriptors:
            if (descriptor.record_id != self.record_id
                    or descriptor.token_sha256 != token_sha256
                    or descriptor.shape[0] != len(tokens)):
                raise ValueError('descriptor record or token binding differs from leaf')
        object.__setattr__(self, 'tokens', tokens)
        object.__setattr__(self, 'descriptors', descriptors)


@dataclass(frozen=True)
class LosslessFactorState:
    target_sha256: str
    anchor_target_sha256: str
    decoder_sha256: str
    provider_sha256: str
    anchor_sha256: str
    preparer_sha256: str
    codec_sha256: str
    stages: tuple
    anchors: tuple

    def __post_init__(self):
        for key in _BINDINGS:
            _digest(getattr(self, key))
        if self.target_sha256 == self.anchor_target_sha256:
            raise ValueError('fixed model target must differ from anchor target')
        model = CompactState(self.target_sha256, tuple(self.stages), ())
        anchors = tuple(self.anchors)
        if any(type(a) is not LosslessFactorLeaf for a in anchors):
            raise TypeError('lossless state requires LosslessFactorLeaf objects')
        if len({a.record_id for a in anchors}) != len(anchors):
            raise ValueError('duplicate lossless factor record')
        expected_stages = tuple((s.stage_id, s.columns) for s in model.stages)
        for anchor in anchors:
            if tuple((d.stage_id, d.shape[1]) for d in anchor.descriptors) != expected_stages:
                raise ValueError('lossless leaf must contain every ordered model stage')
            for descriptor in anchor.descriptors:
                for key in ('target_sha256', 'anchor_target_sha256', 'codec_sha256'):
                    if getattr(descriptor, key) != getattr(self, key):
                        raise ValueError('descriptor target or codec binding differs from state')
        object.__setattr__(self, 'stages', model.stages)
        object.__setattr__(self, 'anchors', tuple(sorted(anchors, key=lambda a: a.record_id)))

    @property
    def record_ids(self):
        return tuple(a.record_id for a in self.anchors)

    @property
    def digest(self):
        return _sha(serialize(self))

    def canonical_bytes(self):
        return serialize(self)


def from_factor_state(state):
    """Encode trusted exact factors without changing the defining model codes."""
    if type(state) is not FixedFactorState:
        raise TypeError('conversion requires a trusted FixedFactorState')
    anchors = []
    for anchor in state.anchors:
        descriptors = tuple(encode_factor(block.array(),
            target_sha256=state.target_sha256, anchor_target_sha256=state.anchor_target_sha256,
            record_id=anchor.record_id, token_sha256=token_digest(anchor.tokens),
            stage_id=block.stage_id) for block in anchor.blocks)
        anchors.append(LosslessFactorLeaf(anchor.record_id, anchor.tokens, descriptors))
    return LosslessFactorState(*(getattr(state, key) for key in _BINDINGS[:-1]),
        codec_binding(), state.stages, tuple(anchors))


def decode_anchors(state, record_ids=None):
    """Decode selected source leaves once; omit all other source payloads."""
    if type(state) is not LosslessFactorState:
        raise TypeError('decoding requires LosslessFactorState')
    if state.codec_sha256 != codec_binding():
        raise ValueError('lossless codec or compressor runtime binding differs')
    selected = state.record_ids if record_ids is None else tuple(record_ids)
    if len(set(selected)) != len(selected) or not set(selected) <= set(state.record_ids):
        raise ValueError('selected lossless source IDs must be unique and present')
    by_id = {anchor.record_id: anchor for anchor in state.anchors}
    result = []
    for rid in sorted(selected):
        anchor = by_id[rid]
        blocks = tuple(FactorBlock(d.stage_id, *d.shape, d.binary64()) for d in anchor.descriptors)
        result.append(FixedFactorLeaf(anchor.record_id, anchor.tokens, state.anchor_target_sha256,
            state.decoder_sha256, state.provider_sha256, state.anchor_sha256,
            state.preparer_sha256, blocks))
    return tuple(result)


def to_factor_state(state):
    """Reconstruct the complete exact factor state without changing any bit."""
    anchors = decode_anchors(state)
    return FixedFactorState(*(getattr(state, key) for key in _BINDINGS[:-1]), state.stages, anchors)


def serialize(state):
    if type(state) is not LosslessFactorState:
        raise TypeError('lossless serialization requires LosslessFactorState')
    model = encode_model(CompactState(state.target_sha256, state.stages, ()))
    leaves, payloads = [], []
    for anchor in state.anchors:
        descriptors = []
        for descriptor in anchor.descriptors:
            payload = encode_descriptor(descriptor)
            descriptors.append(dict(stage_id=descriptor.stage_id, shape=list(descriptor.shape),
                                    nbytes=len(payload), sha256=_sha(payload)))
            payloads.append(payload)
        leaves.append(dict(record_id=anchor.record_id, tokens=list(anchor.tokens),
                           token_sha256=token_digest(anchor.tokens), descriptors=descriptors))
    header = _json(dict(family=FAMILY, storage_schema=STORAGE_SCHEMA,
        **{key: getattr(state, key) for key in _BINDINGS},
        model=dict(nbytes=len(model), sha256=_sha(model)), leaves=leaves))
    return b''.join((MAGIC, struct.pack('<Q', len(header)), header, model, *payloads))


def parse(data, *, limits=LoadLimits(), expected_sha256=None):
    """Read bounded canonical state. An external digest must come from trusted preparation."""
    if type(data) is not bytes or type(limits) is not LoadLimits:
        raise TypeError('immutable bytes and LoadLimits are required')
    if len(data) < 16 or len(data) > limits.max_bytes or data[:8] != MAGIC:
        raise ValueError('invalid lossless state magic or size')
    if expected_sha256 is not None and _sha(data) != _digest(expected_sha256):
        raise ValueError('lossless state differs from trusted digest')
    size = struct.unpack_from('<Q', data, 8)[0]
    if size > limits.max_header_bytes or size > len(data)-16:
        raise ValueError('lossless state header exceeds its bound')
    raw = data[16:16+size]
    try:
        header = json.loads(raw)
        canonical = _json(header)
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise ValueError('invalid lossless state JSON') from exc
    keys = {'family', 'storage_schema', 'model', 'leaves', *_BINDINGS}
    if (type(header) is not dict or set(header) != keys or canonical != raw
            or header['family'] != FAMILY or header['storage_schema'] != STORAGE_SCHEMA):
        raise ValueError('noncanonical or unsupported lossless state schema')
    for key in _BINDINGS:
        _digest(header[key])
    if type(header['leaves']) is not list or len(header['leaves']) > limits.max_records:
        raise ValueError('lossless state record count exceeds its bound')
    cursor = 16+size

    def chunk(entry, maximum):
        nonlocal cursor
        length = entry['nbytes']
        if type(length) is not int or not 1 <= length <= maximum or length > len(data)-cursor:
            raise ValueError('lossless state payload exceeds its bound')
        value = data[cursor:cursor+length]
        cursor += length
        if _sha(value) != _digest(entry['sha256']):
            raise ValueError('lossless state payload hash differs')
        return value

    if type(header['model']) is not dict or set(header['model']) != {'nbytes', 'sha256'}:
        raise ValueError('invalid lossless model metadata')
    model = decode_model(chunk(header['model'], limits.max_bytes), limits=ModelLimits(
        max_bytes=limits.max_bytes, max_header_bytes=limits.max_header_bytes,
        max_stages=limits.max_stages, max_code_elements=limits.max_code_elements))
    if model.factors or model.target_sha256 != header['target_sha256']:
        raise ValueError('lossless model binding differs')
    anchors = []
    for leaf in header['leaves']:
        if type(leaf) is not dict or set(leaf) != {'record_id', 'tokens', 'token_sha256', 'descriptors'}:
            raise ValueError('invalid lossless leaf metadata')
        _name(leaf['record_id'])
        tokens = leaf['tokens']
        if type(tokens) is not list or not 1 <= len(tokens) <= limits.max_leaf_tokens:
            raise ValueError('lossless leaf tokens exceed their bound')
        if token_digest(tokens) != _digest(leaf['token_sha256']):
            raise ValueError('lossless leaf tokens differ from binding')
        entries = leaf['descriptors']
        if type(entries) is not list or len(entries) != len(model.stages):
            raise ValueError('lossless leaf must contain every stage')
        # Check total decoded values and encoded bytes before decoding any descriptor.
        values, encoded_bytes = 0, 0
        for item, stage in zip(entries, model.stages):
            if type(item) is not dict or set(item) != {'stage_id', 'shape', 'nbytes', 'sha256'}:
                raise ValueError('invalid lossless descriptor metadata')
            shape = item['shape']
            if (type(shape) is not list or len(shape) != 2
                    or any(type(n) is not int or n <= 0 for n in shape)
                    or shape != [len(tokens), stage.columns] or item['stage_id'] != stage.stage_id):
                raise ValueError('lossless descriptor dimensions or stage differ')
            values += shape[0]*shape[1]
            if type(item['nbytes']) is not int or item['nbytes'] <= 0:
                raise ValueError('invalid lossless descriptor size')
            encoded_bytes += item['nbytes']
        if values > limits.max_leaf_values or encoded_bytes > limits.max_leaf_bytes:
            raise ValueError('lossless leaf values or bytes exceed their bound')
        descriptors = []
        for item, stage in zip(entries, model.stages):
            descriptor = decode_descriptor(chunk(item, limits.max_leaf_bytes), limits=CodecLimits(
                max_bytes=limits.max_leaf_bytes, max_header_bytes=limits.max_header_bytes,
                max_values=len(tokens)*stage.columns, max_tokens=len(tokens), max_width=stage.columns), expected_sha256=item['sha256'])
            if descriptor.shape != tuple(item['shape']) or descriptor.stage_id != item['stage_id']:
                raise ValueError('descriptor differs from lossless index')
            descriptors.append(descriptor)
        anchors.append(LosslessFactorLeaf(leaf['record_id'], tuple(tokens), tuple(descriptors)))
    if cursor != len(data):
        raise ValueError('trailing lossless state payload')
    state = LosslessFactorState(*(header[key] for key in _BINDINGS), model.stages, tuple(anchors))
    if serialize(state) != data:
        raise ValueError('lossless state order is not canonical')
    return state
