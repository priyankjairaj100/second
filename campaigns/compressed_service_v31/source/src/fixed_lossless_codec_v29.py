"""Source-local exact binary64 compression with bounded canonical decoding.

Encoding selects raw, zlib, or byte-shuffled zlib bytes deterministically.
Every source bit survives, including signed zeros. Content hashes do not
prove that a declared decoder produced the source factor.
"""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import stat
import struct
import sys
import zlib

import numpy as np

from .compact_state import _digest, _name, _json
from .run_store import strict_json

MAGIC = b'VCLF\x01\x00\x00\x00'
SCHEMA = 'source-local-lossless-factor-v1'
MODES = (0, 1, 2)
MODE_NAMES = {0: 'raw', 1: 'zlib', 2: 'byte-shuffled-zlib'}
MAX_DECODED_BYTES = 128*2**20
_RUNTIME_HASH_CACHE = {}
_RUNTIME_CACHE_ENTRIES = 4


def _binary_identity(path):
    metadata = path.stat()
    if not stat.S_ISREG(metadata.st_mode) or not 1 <= metadata.st_size <= 512*2**20:
        raise ValueError('compressor runtime binary must be a bounded regular file')
    return (str(path), metadata.st_dev, metadata.st_ino, metadata.st_size,
            metadata.st_mtime_ns, metadata.st_ctime_ns)


def _runtime_binary_digest(path):
    """Cache a runtime file hash under stable metadata on the trusted filesystem.

    Metadata identity is not hostile-storage authentication. Both cache hits
    and fresh reads require the same before/after identity.
    """
    path = Path(path).resolve(strict=True)
    before = _binary_identity(path)
    cached = _RUNTIME_HASH_CACHE.get(before)
    result = cached if cached is not None else _sha(path.read_bytes())
    if _binary_identity(path) != before:
        raise ValueError('compressor runtime binary changed during validation')
    if cached is None:
        if len(_RUNTIME_HASH_CACHE) >= _RUNTIME_CACHE_ENTRIES:
            _RUNTIME_HASH_CACHE.pop(next(iter(_RUNTIME_HASH_CACHE)))
        _RUNTIME_HASH_CACHE[before] = result
    return result


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def codec_manifest():
    root = Path(__file__).parent
    return dict(source_sha256={name: _sha((root/name).read_bytes()) for name in (
        'fixed_lossless_codec_v29.py', 'compact_state.py', 'run_store.py')},
        zlib_compile_version=zlib.ZLIB_VERSION, zlib_runtime_version=zlib.ZLIB_RUNTIME_VERSION,
        zlib_module_kind='extension' if getattr(zlib, '__file__', None) else 'builtin',
        zlib_runtime_binary_sha256=_runtime_binary_digest(getattr(zlib, '__file__', sys.executable)),
        parameters=dict(level=6, wbits=15, mem_level=8, strategy=0),
        canonical_scope='this bound encoder and compressor runtime')


def codec_binding():
    return _sha(_json(codec_manifest()))


def _shuffle(raw):
    return np.frombuffer(raw, dtype=np.uint8).reshape(-1, 8).T.copy().tobytes()


def _unshuffle(raw):
    return np.frombuffer(raw, dtype=np.uint8).reshape(8, -1).T.copy().tobytes()


def _compress(raw):
    compressor = zlib.compressobj(level=6, method=zlib.DEFLATED, wbits=15,
                                 memLevel=8, strategy=zlib.Z_DEFAULT_STRATEGY)
    return compressor.compress(raw)+compressor.flush(zlib.Z_FINISH)


def _select(raw):
    candidates = (raw, _compress(raw), _compress(_shuffle(raw)))
    # Modes have equal JSON widths. Only payload length and its digit count vary.
    # Ties prefer the lower mode number. Hash strings always have equal lengths.
    mode = min(MODES, key=lambda m: (len(candidates[m])+len(str(len(candidates[m]))), m))
    return mode, candidates[mode]


def _decode(payload, mode, expected_bytes):
    if type(expected_bytes) is not int or not 1 <= expected_bytes <= MAX_DECODED_BYTES:
        raise ValueError('decoded lossless factor exceeds its hard byte bound')
    if mode == 0:
        raw = payload
    else:
        decoder = zlib.decompressobj(wbits=15)
        try:
            raw = decoder.decompress(payload, expected_bytes+1)
        except zlib.error as exc:
            raise ValueError('invalid lossless zlib stream') from exc
        if (len(raw) != expected_bytes or not decoder.eof
                or decoder.unused_data or decoder.unconsumed_tail):
            raise ValueError('lossless stream exceeds its bound, is incomplete, or has trailing data')
        if mode == 2:
            raw = _unshuffle(raw)
    if len(raw) != expected_bytes:
        raise ValueError('lossless factor length differs from its shape')
    if not np.isfinite(np.frombuffer(raw, dtype='<f8')).all():
        raise ValueError('lossless factors require finite binary64 values')
    return raw


@dataclass(frozen=True)
class LoadLimits:
    max_bytes: int = 128*2**20
    max_header_bytes: int = 65536
    max_values: int = 16000000
    max_tokens: int = 4096
    max_width: int = 1048576

    def __post_init__(self):
        if any(type(value) is not int or value <= 0 for value in self.__dict__.values()):
            raise ValueError('lossless limits must be positive built-in integers')


@dataclass(frozen=True)
class LosslessFactorDescriptor:
    target_sha256: str
    anchor_target_sha256: str
    record_id: str
    token_sha256: str
    stage_id: str
    shape: tuple
    source_sha256: str
    codec_sha256: str
    mode: int
    payload: bytes

    def __post_init__(self):
        self._validate_metadata()
        raw = self.binary64()
        if _select(raw) != (self.mode, self.payload):
            raise ValueError('lossless encoder choice or compressed stream is not canonical')

    def _validate_metadata(self):
        for value in (self.target_sha256, self.anchor_target_sha256, self.token_sha256,
                      self.source_sha256, self.codec_sha256):
            _digest(value)
        _name(self.record_id)
        _name(self.stage_id)
        shape = tuple(self.shape)
        if len(shape) != 2 or any(type(n) is not int or n <= 0 for n in shape):
            raise ValueError('lossless descriptor requires a positive token-major shape')
        if shape[0]*shape[1]*8 > MAX_DECODED_BYTES:
            raise ValueError('decoded lossless factor exceeds its hard byte bound')
        if type(self.mode) is not int or self.mode not in MODES:
            raise ValueError('unsupported lossless mode')
        if type(self.payload) is not bytes:
            raise TypeError('lossless payload must be immutable bytes')
        if self.codec_sha256 != codec_binding():
            raise ValueError('lossless codec or compressor runtime binding differs')
        object.__setattr__(self, 'shape', shape)

    def binary64(self):
        """Decode exact immutable source bytes without recompressing them."""
        raw = _decode(self.payload, self.mode, self.shape[0]*self.shape[1]*8)
        if _sha(raw) != self.source_sha256:
            raise ValueError('decoded lossless factor differs from source hash')
        return raw

    def array(self):
        return np.frombuffer(self.binary64(), dtype='<f8').reshape(self.shape)

    @property
    def digest(self):
        return _sha(serialize(self))


def encode_factor(values, *, target_sha256, anchor_target_sha256, record_id, token_sha256, stage_id):
    """Encode one trusted source factor. No other record affects the choice."""
    if type(values) is not np.ndarray or values.dtype != np.float64 or values.ndim != 2 or not all(values.shape):
        raise TypeError('an ordinary nonempty binary64 matrix is required')
    if not np.isfinite(values).all():
        raise ValueError('lossless factors require finite binary64 values')
    if values.size*8 > MAX_DECODED_BYTES:
        raise ValueError('decoded lossless factor exceeds its hard byte bound')
    raw = values.astype('<f8', copy=False).tobytes(order='C')
    mode, payload = _select(raw)
    # This path just produced exact source bytes and the canonical choice.
    # Reuse that evidence instead of repeating decompression and recompression.
    descriptor = object.__new__(LosslessFactorDescriptor)
    names = ('target_sha256', 'anchor_target_sha256', 'record_id', 'token_sha256', 'stage_id',
             'shape', 'source_sha256', 'codec_sha256', 'mode', 'payload')
    contents = (target_sha256, anchor_target_sha256, record_id, token_sha256, stage_id,
                tuple(values.shape), _sha(raw), codec_binding(), mode, payload)
    for name, value in zip(names, contents):
        object.__setattr__(descriptor, name, value)
    descriptor._validate_metadata()
    return descriptor


def _header(descriptor):
    return dict(schema=SCHEMA, target_sha256=descriptor.target_sha256,
        anchor_target_sha256=descriptor.anchor_target_sha256, record_id=descriptor.record_id,
        token_sha256=descriptor.token_sha256, stage_id=descriptor.stage_id, shape=list(descriptor.shape),
        source_sha256=descriptor.source_sha256, codec_sha256=descriptor.codec_sha256,
        mode=descriptor.mode, raw_bytes=descriptor.shape[0]*descriptor.shape[1]*8,
        payload_bytes=len(descriptor.payload), payload_sha256=_sha(descriptor.payload))


def serialize(descriptor):
    if type(descriptor) is not LosslessFactorDescriptor:
        raise TypeError('serialization requires LosslessFactorDescriptor')
    header = _json(_header(descriptor))
    return MAGIC+struct.pack('<Q', len(header))+header+descriptor.payload


def parse(data, *, limits=LoadLimits(), expected_sha256=None):
    if type(data) is not bytes or type(limits) is not LoadLimits:
        raise TypeError('immutable bytes and lossless LoadLimits are required')
    if len(data) < 16 or len(data) > limits.max_bytes or data[:8] != MAGIC:
        raise ValueError('invalid lossless magic or file size')
    if expected_sha256 is not None and _sha(data) != _digest(expected_sha256):
        raise ValueError('lossless descriptor differs from trusted digest')
    size = struct.unpack_from('<Q', data, 8)[0]
    if size > limits.max_header_bytes or size > len(data)-16:
        raise ValueError('lossless header exceeds its bound')
    raw_header = data[16:16+size]
    try:
        header = strict_json(raw_header)
        canonical = _json(header)
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise ValueError('invalid lossless JSON') from exc
    keys = {'schema', 'target_sha256', 'anchor_target_sha256', 'record_id', 'token_sha256',
            'stage_id', 'shape', 'source_sha256', 'codec_sha256', 'mode', 'raw_bytes',
            'payload_bytes', 'payload_sha256'}
    if type(header) is not dict or set(header) != keys or canonical != raw_header or header['schema'] != SCHEMA:
        raise ValueError('unsupported or noncanonical lossless header')
    shape = header['shape']
    if (type(shape) is not list or len(shape) != 2 or any(type(n) is not int or n <= 0 for n in shape)
            or shape[0] > limits.max_tokens or shape[1] > limits.max_width
            or shape[0]*shape[1] > limits.max_values):
        raise ValueError('lossless dimensions exceed their bound')
    if type(header['raw_bytes']) is not int or header['raw_bytes'] != shape[0]*shape[1]*8:
        raise ValueError('lossless decoded byte length differs from dimensions')
    payload = data[16+size:]
    if (type(header['payload_bytes']) is not int or header['payload_bytes'] != len(payload)
            or _sha(payload) != _digest(header['payload_sha256'])):
        raise ValueError('lossless payload binding differs')
    descriptor = LosslessFactorDescriptor(*(header[key] for key in ('target_sha256', 'anchor_target_sha256',
        'record_id', 'token_sha256', 'stage_id')), tuple(shape), header['source_sha256'],
        header['codec_sha256'], header['mode'], payload)
    if serialize(descriptor) != data:
        raise ValueError('lossless descriptor encoding is not canonical')
    return descriptor
