"""Minimal source-local factors for the existing fixed-anchor model target.

This representation stores exact factor bytes. It stores no scalar tape or
affine summaries. Trusted provenance remains necessary for prepared leaves.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct
import numpy as np

from .anchor_state import LoadLimits
from .compact_state import (CompactState, LoadLimits as ModelLimits, _digest, _name, _json,
    token_digest, serialize as encode_model, parse as decode_model)
from .sequential_finite import sequential_features

FAMILY = 'fixed_anchor_calibration_v1'
STORAGE_SCHEMA = 'source_local_exact_factors_v1'
MAGIC = b'VCFF\x01\x00\x00\x00'


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def preparer_binding():
    root = Path(__file__).parent
    return _sha(_json({name:_sha((root/name).read_bytes())
                      for name in ('fixed_factor_state.py', 'sequential_finite.py')}))


@dataclass(frozen=True)
class FactorBlock:
    stage_id: str
    token_count: int
    width: int
    binary64: bytes

    def __post_init__(self):
        _name(self.stage_id)
        if any(type(v) is not int or v <= 0 for v in (self.token_count, self.width)):
            raise ValueError('factor dimensions must be positive built-in integers')
        if type(self.binary64) is not bytes or len(self.binary64) != self.token_count*self.width*8:
            raise ValueError('factor byte length differs from dimensions')
        if not np.isfinite(np.frombuffer(self.binary64, dtype='<f8')).all():
            raise ValueError('fixed factors must contain finite binary64 values')

    @classmethod
    def from_array(cls, stage_id, values):
        array = np.asarray(values, dtype=np.float64)
        if array.ndim != 2:
            raise ValueError('factor must be a token-major matrix')
        return cls(stage_id, *array.shape, array.astype('<f8', copy=False).tobytes(order='C'))

    def array(self):
        return np.frombuffer(self.binary64, dtype='<f8').reshape(self.token_count, self.width)


@dataclass(frozen=True)
class FixedFactorLeaf:
    record_id: str
    tokens: tuple
    target_sha256: str
    decoder_sha256: str
    provider_sha256: str
    anchor_sha256: str
    preparer_sha256: str
    blocks: tuple

    def __post_init__(self):
        _name(self.record_id)
        tokens, blocks = tuple(self.tokens), tuple(self.blocks)
        token_digest(tokens)
        for value in (self.target_sha256, self.decoder_sha256, self.provider_sha256,
                      self.anchor_sha256, self.preparer_sha256):
            _digest(value)
        if not blocks or any(type(b) is not FactorBlock for b in blocks):
            raise TypeError('fixed factor leaves require complete FactorBlock objects')
        if len({b.stage_id for b in blocks}) != len(blocks):
            raise ValueError('duplicate fixed factor stage')
        if any(b.token_count != len(tokens) for b in blocks):
            raise ValueError('fixed factor token count differs')
        object.__setattr__(self, 'tokens', tokens)
        object.__setattr__(self, 'blocks', blocks)

    @property
    def factors(self):
        # Shared service interface. The integer denotes stage order, not a tape node.
        return tuple((b.stage_id, i, b.array()) for i, b in enumerate(self.blocks))


def from_anchor(anchor):
    from .anchor_transformer import AnchorRecord
    if type(anchor) is not AnchorRecord:
        raise TypeError('conversion requires a trusted AnchorRecord')
    return FixedFactorLeaf(anchor.record_id, anchor.tokens, anchor.target_sha256,
        anchor.decoder_sha256, anchor.provider_sha256, anchor.anchor_sha256, preparer_binding(),
        tuple(FactorBlock.from_array(sid, values) for sid, _, values in anchor.factors))


def prepare_leaf(decoder, target, record, *, context):
    """Run the fixed nearest traversal once, without scalar summaries."""
    from .anchor_transformer import decoder_binding, provider_binding
    if (context.target_sha256 != target.digest or context.decoder_sha256 != decoder_binding(decoder)
            or context.provider_sha256 != provider_binding()):
        raise ValueError('fixed factor context binding differs')
    if type(record) is not dict or set(record) != {'id', 'tokens'}:
        raise ValueError('fixed factor record requires ID and tokens')
    rid, tokens = _name(record['id']), decoder.base._tokens(record['tokens'])
    stream = sequential_features(decoder, tokens)
    blocks = []
    for i, stage in enumerate(target.stages):
        sid, values = next(stream) if i == 0 else stream.send(context.anchor_matrices[i-1])
        if sid != stage.stage_id:
            raise ArithmeticError('fixed factor traversal order differs')
        blocks.append(FactorBlock.from_array(sid, values))
    return FixedFactorLeaf(rid, tuple(tokens), target.digest, context.decoder_sha256,
        context.provider_sha256, context.anchor_sha256, preparer_binding(), tuple(blocks))


@dataclass(frozen=True)
class FixedFactorState:
    target_sha256: str
    anchor_target_sha256: str
    decoder_sha256: str
    provider_sha256: str
    anchor_sha256: str
    preparer_sha256: str
    stages: tuple
    anchors: tuple

    def __post_init__(self):
        for value in (self.target_sha256, self.anchor_target_sha256, self.decoder_sha256,
                      self.provider_sha256, self.anchor_sha256, self.preparer_sha256):
            _digest(value)
        if self.target_sha256 == self.anchor_target_sha256:
            raise ValueError('fixed model target must differ from anchor target')
        model = CompactState(self.target_sha256, tuple(self.stages), ())
        anchors = tuple(self.anchors)
        if any(type(a) is not FixedFactorLeaf for a in anchors):
            raise TypeError('minimal state requires FixedFactorLeaf objects')
        if len({a.record_id for a in anchors}) != len(anchors):
            raise ValueError('duplicate fixed factor record')
        for anchor in anchors:
            if anchor.target_sha256 != self.anchor_target_sha256:
                raise ValueError('leaf anchor target differs')
            for key in ('decoder_sha256', 'provider_sha256', 'anchor_sha256', 'preparer_sha256'):
                if getattr(anchor, key) != getattr(self, key):
                    raise ValueError('leaf provenance differs from state')
            if tuple((b.stage_id, b.width) for b in anchor.blocks) != tuple(
                    (s.stage_id, s.columns) for s in model.stages):
                raise ValueError('leaf must contain every ordered model stage')
        object.__setattr__(self, 'stages', model.stages)
        object.__setattr__(self, 'anchors', tuple(sorted(anchors, key=lambda a:a.record_id)))

    @property
    def record_ids(self):
        return tuple(a.record_id for a in self.anchors)

    @property
    def digest(self):
        return _sha(serialize(self))

    def canonical_bytes(self):
        return serialize(self)


def serialize(state):
    if type(state) is not FixedFactorState:
        raise TypeError('minimal serialization requires FixedFactorState')
    model = encode_model(CompactState(state.target_sha256, state.stages, ()))
    leaves = []
    payloads = []
    for anchor in state.anchors:
        blocks = []
        for block in anchor.blocks:
            blocks.append(dict(stage_id=block.stage_id, token_count=block.token_count,
                width=block.width, nbytes=len(block.binary64), sha256=_sha(block.binary64)))
            payloads.append(block.binary64)
        leaves.append(dict(record_id=anchor.record_id, tokens=list(anchor.tokens),
                           token_sha256=token_digest(anchor.tokens), blocks=blocks))
    header = _json(dict(family=FAMILY, storage_schema=STORAGE_SCHEMA,
        **{key:getattr(state, key) for key in ('target_sha256', 'anchor_target_sha256',
            'decoder_sha256', 'provider_sha256', 'anchor_sha256', 'preparer_sha256')},
        model=dict(nbytes=len(model), sha256=_sha(model)), leaves=leaves))
    return b''.join((MAGIC, struct.pack('<Q', len(header)), header, model, *payloads))


def parse(data, *, limits=LoadLimits(), expected_sha256=None):
    if type(data) is not bytes or type(limits) is not LoadLimits:
        raise TypeError('immutable bytes and LoadLimits are required')
    if len(data) < 16 or len(data) > limits.max_bytes or data[:8] != MAGIC:
        raise ValueError('invalid minimal state magic or size')
    if expected_sha256 is not None and _sha(data) != _digest(expected_sha256):
        raise ValueError('minimal state differs from trusted digest')
    n = struct.unpack('<Q', data[8:16])[0]
    if n > limits.max_header_bytes or n > len(data)-16:
        raise ValueError('minimal state header exceeds its bound')
    raw = data[16:16+n]
    try:
        header = json.loads(raw)
        canonical = _json(header)
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise ValueError('invalid minimal state JSON') from exc
    bindings = ('target_sha256', 'anchor_target_sha256', 'decoder_sha256',
                'provider_sha256', 'anchor_sha256', 'preparer_sha256')
    keys = {'family', 'storage_schema', 'model', 'leaves', *bindings}
    if (canonical != raw or type(header) is not dict or set(header) != keys
            or header['family'] != FAMILY or header['storage_schema'] != STORAGE_SCHEMA):
        raise ValueError('noncanonical or unsupported minimal state schema')
    for key in bindings:
        _digest(header[key])
    if type(header['leaves']) is not list or len(header['leaves']) > limits.max_records:
        raise ValueError('minimal state record count exceeds its bound')
    cursor = 16+n

    def chunk(entry, expected=None):
        nonlocal cursor
        size = entry['nbytes']
        if (type(size) is not int or size < 0 or size > len(data)-cursor
                or (expected is not None and size != expected)):
            raise ValueError('minimal state payload length differs')
        value = data[cursor:cursor+size]
        cursor += size
        if _sha(value) != _digest(entry['sha256']):
            raise ValueError('minimal state payload hash differs')
        return value

    if type(header['model']) is not dict or set(header['model']) != {'nbytes', 'sha256'}:
        raise ValueError('invalid minimal model metadata')
    model = decode_model(chunk(header['model']), limits=ModelLimits(max_bytes=limits.max_bytes,
        max_header_bytes=limits.max_header_bytes, max_stages=limits.max_stages,
        max_code_elements=limits.max_code_elements))
    if model.factors or model.target_sha256 != header['target_sha256']:
        raise ValueError('minimal model binding differs')
    anchors = []
    for leaf in header['leaves']:
        if type(leaf) is not dict or set(leaf) != {'record_id', 'tokens', 'token_sha256', 'blocks'}:
            raise ValueError('invalid minimal leaf metadata')
        _name(leaf['record_id'])
        tokens = leaf['tokens']
        if type(tokens) is not list or not 1 <= len(tokens) <= limits.max_leaf_tokens:
            raise ValueError('minimal leaf tokens exceed their bound')
        if token_digest(tokens) != _digest(leaf['token_sha256']):
            raise ValueError('minimal leaf tokens differ from binding')
        if type(leaf['blocks']) is not list or len(leaf['blocks']) != len(model.stages):
            raise ValueError('minimal leaf must contain every stage')
        blocks, values = [], 0
        for item in leaf['blocks']:
            if type(item) is not dict or set(item) != {'stage_id', 'token_count', 'width', 'nbytes', 'sha256'}:
                raise ValueError('invalid minimal factor metadata')
            if (type(item['token_count']) is not int or item['token_count'] != len(tokens)
                    or type(item['width']) is not int or item['width'] <= 0):
                raise ValueError('invalid minimal factor dimensions')
            count = item['token_count']*item['width']
            values += count
            if values > limits.max_leaf_values or values*8 > limits.max_leaf_bytes:
                raise ValueError('minimal factor values exceed their bound')
            blocks.append(FactorBlock(item['stage_id'], item['token_count'], item['width'], chunk(item, count*8)))
        anchors.append(FixedFactorLeaf(leaf['record_id'], tuple(tokens), header['anchor_target_sha256'],
            *(header[key] for key in ('decoder_sha256', 'provider_sha256', 'anchor_sha256', 'preparer_sha256')),
            tuple(blocks)))
    if cursor != len(data):
        raise ValueError('trailing minimal state payload')
    state = FixedFactorState(*(header[key] for key in bindings), model.stages, tuple(anchors))
    if serialize(state) != data:
        raise ValueError('minimal state order is not canonical')
    return state
