"""Canonical source-local anchor leaves plus the exact complete output model.

This is a separate state family from current-prefix factor_identity_v1.
Content hashes detect corruption. Trusted provenance remains required.
"""
from dataclasses import dataclass
import hashlib
import json
import struct

from .compact_state import (
    CompactState, StageCodes, LoadLimits as ModelLimits,
    serialize as serialize_model, parse as parse_model, _digest, _name, _json,
)

FAMILY = 'source_local_anchor_v1'
MAGIC = b'VCAN\x01\x00\x00\x00'


def _sha(data):
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class AnchorState:
    target_sha256: str
    decoder_sha256: str
    provider_sha256: str
    anchor_sha256: str
    stages: tuple
    anchors: tuple

    def __post_init__(self):
        from .anchor_transformer import AnchorRecord
        for value in (self.target_sha256, self.decoder_sha256,
                      self.provider_sha256, self.anchor_sha256):
            _digest(value)
        stages, anchors = tuple(self.stages), tuple(self.anchors)
        # Reuse all grid, packed-code, and ordered-model invariants.
        CompactState(self.target_sha256, stages, ())
        if any(type(a) is not AnchorRecord for a in anchors):
            raise TypeError('anchors must contain trusted AnchorRecord objects')
        ids = []
        for anchor in anchors:
            _name(anchor.record_id)
            ids.append(anchor.record_id)
            for key in ('target_sha256', 'decoder_sha256', 'provider_sha256', 'anchor_sha256'):
                if getattr(anchor, key) != getattr(self, key):
                    raise ValueError('anchor leaf binding differs from state binding')
        if len(set(ids)) != len(ids):
            raise ValueError('duplicate anchor record ID')
        object.__setattr__(self, 'stages', stages)
        object.__setattr__(self, 'anchors', tuple(sorted(anchors, key=lambda a: a.record_id)))

    @property
    def record_ids(self):
        return tuple(a.record_id for a in self.anchors)

    @property
    def digest(self):
        return _sha(serialize(self))

    def canonical_bytes(self):
        return serialize(self)


@dataclass(frozen=True)
class LoadLimits:
    max_bytes: int = 512 * 1024 * 1024
    max_header_bytes: int = 8 * 1024 * 1024
    max_records: int = 100000
    max_leaf_bytes: int = 128 * 1024 * 1024
    max_stages: int = 4096
    max_code_elements: int = 268435456
    max_leaf_nodes: int = 2000000
    max_leaf_values: int = 32000000
    max_leaf_tokens: int = 4096

    def __post_init__(self):
        if any(type(v) is not int or v <= 0 for v in self.__dict__.values()):
            raise ValueError('load limits must be positive built-in integers')


def serialize(state):
    from .anchor_transformer import encode_anchor
    if type(state) is not AnchorState:
        raise TypeError('state must be AnchorState')
    model = serialize_model(CompactState(state.target_sha256, state.stages, ()))
    leaves = tuple(encode_anchor(a) for a in state.anchors)
    header = _json(dict(
        family=FAMILY, target_sha256=state.target_sha256,
        decoder_sha256=state.decoder_sha256, provider_sha256=state.provider_sha256,
        anchor_sha256=state.anchor_sha256,
        model=dict(nbytes=len(model), sha256=_sha(model)),
        leaves=[dict(record_id=a.record_id, nbytes=len(b), sha256=_sha(b))
                for a, b in zip(state.anchors, leaves)]))
    return b''.join((MAGIC, struct.pack('<Q', len(header)), header, model, *leaves))


def parse(data, *, limits=LoadLimits(), expected_sha256=None):
    """Read bounded canonical bytes. A trusted external digest authenticates bindings."""
    from .anchor_transformer import decode_anchor
    if type(data) is not bytes or type(limits) is not LoadLimits:
        raise TypeError('immutable bytes and LoadLimits are required')
    if len(data) < 16 or len(data) > limits.max_bytes or data[:8] != MAGIC:
        raise ValueError('invalid anchor state magic or size')
    if expected_sha256 is not None and _sha(data) != _digest(expected_sha256):
        raise ValueError('anchor state does not match trusted digest')
    size = struct.unpack('<Q', data[8:16])[0]
    if size > limits.max_header_bytes or size > len(data) - 16:
        raise ValueError('anchor state header exceeds its bound')
    raw = data[16:16 + size]
    try:
        header = json.loads(raw)
        if _json(header) != raw:
            raise ValueError('anchor state JSON is not canonical')
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise ValueError('invalid canonical anchor state JSON') from exc
    keys = {'family', 'target_sha256', 'decoder_sha256', 'provider_sha256',
            'anchor_sha256', 'model', 'leaves'}
    if type(header) is not dict or set(header) != keys or header['family'] != FAMILY:
        raise ValueError('unsupported anchor state metadata')
    for key in ('target_sha256', 'decoder_sha256', 'provider_sha256', 'anchor_sha256'):
        _digest(header[key])
    if type(header['leaves']) is not list or len(header['leaves']) > limits.max_records:
        raise ValueError('anchor leaf count exceeds its bound')
    cursor = 16 + size

    def chunk(metadata, max_bytes, leaf=False):
        nonlocal cursor
        expected = {'nbytes', 'sha256', 'record_id'} if leaf else {'nbytes', 'sha256'}
        if type(metadata) is not dict or set(metadata) != expected:
            raise ValueError('invalid anchor payload metadata')
        n = metadata['nbytes']
        if type(n) is not int or n <= 0 or n > max_bytes or n > len(data) - cursor:
            raise ValueError('anchor payload exceeds its bound')
        if leaf:
            _name(metadata['record_id'])
        value = data[cursor:cursor + n]
        cursor += n
        if _sha(value) != _digest(metadata['sha256']):
            raise ValueError('anchor payload hash mismatch')
        return value

    model = parse_model(chunk(header['model'], limits.max_bytes), limits=ModelLimits(
        max_bytes=limits.max_bytes, max_header_bytes=limits.max_header_bytes,
        max_stages=limits.max_stages, max_code_elements=limits.max_code_elements))
    if model.factors or model.target_sha256 != header['target_sha256']:
        raise ValueError('anchor state model binding differs')
    anchors = []
    for entry in header['leaves']:
        anchor = decode_anchor(chunk(entry, limits.max_leaf_bytes, True),
            max_bytes=limits.max_leaf_bytes, max_nodes=limits.max_leaf_nodes,
            max_values=limits.max_leaf_values, max_tokens=limits.max_leaf_tokens)
        if anchor.record_id != entry['record_id']:
            raise ValueError('anchor record ID differs from metadata')
        anchors.append(anchor)
    if cursor != len(data):
        raise ValueError('trailing anchor state payload')
    state = AnchorState(*(header[key] for key in (
        'target_sha256', 'decoder_sha256', 'provider_sha256', 'anchor_sha256')),
        model.stages, tuple(anchors))
    if serialize(state) != data:
        raise ValueError('anchor state member order is not canonical')
    return state
