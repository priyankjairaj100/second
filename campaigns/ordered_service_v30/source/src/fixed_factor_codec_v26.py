"""Version 26 packed dyadic enclosures with sixteen through forty-eight bits.

This codec stores evidence about the existing fixed-feature target. It does
not quantize that target's defining features or implement a repair service.
Trusted preparation establishes containment. Hashes only bind content.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct
import numpy as np

from .compact_state import _digest, _name, _json
from .finite_feature_boxes import FloatBox

MAGIC = b'VCFC\x02\x00\x00\x00'
SCHEMA = 'source-local-dyadic-factor-enclosure-v2'
PRECISIONS = (16, 24, 32, 40, 48)
# Every precision uses the same guard. Otherwise a coarse exact escape could
# become a wider regular cell at finer precision, violating nestedness.
_GUARD_BITS = 0x7FEFFFC000000000
_SIGN = 1 << 63
_ABS = _SIGN-1
_FRACTION = (1 << 52)-1


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def codec_dependencies():
    """Bind copied arithmetic and both directly imported project helpers."""
    root = Path(__file__).parent
    return {name: _sha((root/name).read_bytes()) for name in (
        'fixed_factor_codec_v26.py', 'compact_state.py', 'finite_feature_boxes.py')}


def codec_binding():
    return _sha(_json(codec_dependencies()))


def _word_float(word):
    return struct.unpack('<d', struct.pack('<Q', word))[0]


def _top(word):
    """Return the exact floor(log2(abs(x))) from finite binary64 bits."""
    word &= _ABS
    exponent, fraction = word >> 52, word & _FRACTION
    if exponent == 0:
        return fraction.bit_length()-1-1074 if fraction else -1074
    if exponent == 2047:
        raise ValueError('factor entries must be finite')
    return exponent-1023


def _parts(word):
    exponent, fraction = (word & _ABS) >> 52, word & _FRACTION
    if exponent == 2047:
        raise ValueError('factor entries must be finite')
    return (fraction, -1074) if exponent == 0 else ((1 << 52)|fraction, exponent-1075)


def _cell(word, step_exponent):
    """Exact integer floor(x / 2**step_exponent), plus grid membership."""
    mantissa, power = _parts(word)
    if not mantissa:
        return 0, True
    shift = step_exponent-power
    if shift <= 0:
        floor, remainder = mantissa << (-shift), 0
    elif shift >= mantissa.bit_length():
        floor, remainder = 0, mantissa
    else:
        floor, remainder = mantissa >> shift, mantissa & ((1 << shift)-1)
    if word & _SIGN:
        floor = -floor-int(remainder != 0)
    return floor, remainder == 0


def _dyadic_word(integer, power):
    """Encode an exactly representable finite integer*2**power, without rounding."""
    if type(integer) is not int or type(power) is not int:
        raise TypeError('dyadic coordinates require built-in integers')
    if not integer:
        return 0
    sign = _SIGN if integer < 0 else 0
    magnitude = abs(integer)
    zeros = (magnitude & -magnitude).bit_length()-1
    magnitude >>= zeros
    power += zeros
    length = magnitude.bit_length()
    top = power+length-1
    if power < -1074 or top > 1023 or length > 53:
        raise ValueError('dyadic endpoint is not exactly finite binary64')
    if top < -1022:
        return sign | (magnitude << (power+1074))
    significand = magnitude << (53-length)
    return sign | ((top+1023) << 52) | (significand-(1 << 52))


def _step(top, bits):
    return max(top-(bits-2), -1074)


def _flags_pack(flags):
    packed = bytearray((len(flags)+3)//4)
    for i, flag in enumerate(flags):
        packed[i//4] |= flag << (2*(i%4))
    return bytes(packed)


def _encode_payload(words, bits, block_size):
    chunks = []
    byte_width = bits//8
    for start in range(0, len(words), block_size):
        block = [int(w) for w in words[start:start+block_size]]
        top = max(_top(w) for w in block)
        step = _step(top, bits)
        flags, indices, escapes = [], bytearray(), bytearray()
        for word in block:
            if (word & _ABS) > _GUARD_BITS:
                flag, integer = 2, 0
                escapes += struct.pack('<Q', word)
            else:
                integer, exact = _cell(word, step)
                flag = int(exact)
                _dyadic_word(integer, step)
                if not exact:
                    _dyadic_word(integer+1, step)
            if not -(1 << (bits-1)) <= integer < (1 << (bits-1)):
                raise ArithmeticError('block cell exceeds its packed integer range')
            flags.append(flag)
            indices += integer.to_bytes(byte_width, 'little', signed=True)
        chunks.extend((struct.pack('<h', top), _flags_pack(flags), bytes(indices), bytes(escapes)))
    return b''.join(chunks)


def _decode_payload(payload, shape, bits, block_size, *, with_radius=False):
    total = shape[0]*shape[1]
    lower = np.empty(total, dtype='<u8')
    upper = np.empty(total, dtype='<u8')
    radius = np.zeros(total, dtype='<u8') if with_radius else None
    center = np.empty(total, dtype='<u8') if with_radius else None
    cursor, byte_width, escapes = 0, bits//8, 0
    for start in range(0, total, block_size):
        count = min(block_size, total-start)
        flag_bytes = (count+3)//4
        fixed_size = 2+flag_bytes+count*byte_width
        if fixed_size > len(payload)-cursor:
            raise ValueError('truncated compressed factor block')
        top = struct.unpack_from('<h', payload, cursor)[0]
        cursor += 2
        if not -1074 <= top <= 1023:
            raise ValueError('invalid local block exponent')
        step = _step(top, bits)
        flags = payload[cursor:cursor+flag_bytes]
        cursor += flag_bytes
        if count % 4 and flags[-1] >> (2*(count%4)):
            raise ValueError('unused flag bits must be zero')
        integers = payload[cursor:cursor+count*byte_width]
        cursor += count*byte_width
        for j in range(count):
            flag = (flags[j//4] >> (2*(j%4))) & 3
            integer = int.from_bytes(integers[j*byte_width:(j+1)*byte_width], 'little', signed=True)
            if flag == 3:
                raise ValueError('reserved compressed factor flag')
            if flag == 2:
                if integer != 0 or len(payload)-cursor < 8:
                    raise ValueError('invalid exact escape encoding')
                word = struct.unpack_from('<Q', payload, cursor)[0]
                cursor += 8
                _top(word)
                if (word & _ABS) <= _GUARD_BITS:
                    raise ValueError('unnecessary exact escape is not canonical')
                lo = hi = word
                escapes += 1
            else:
                lo = _dyadic_word(integer, step)
                hi = lo if flag == 1 else _dyadic_word(integer+1, step)
            lower[start+j], upper[start+j] = lo, hi
            if radius is not None:
                center[start+j] = lo
                if flag == 0:
                    half_step = step-1 if step > -1074 else step
                    radius[start+j] = _dyadic_word(1, half_step)
                    if step > -1074:
                        center[start+j] = _dyadic_word(2*integer+1, step-1)
    if cursor != len(payload):
        raise ValueError('trailing compressed factor payload')
    result = (lower.view('<f8').reshape(shape), upper.view('<f8').reshape(shape), escapes)
    return (*result, center.view('<f8').reshape(shape), radius.view('<f8').reshape(shape)) if radius is not None else result


@dataclass(frozen=True)
class LoadLimits:
    max_bytes: int = 128*2**20
    max_header_bytes: int = 65536
    max_values: int = 16000000
    max_tokens: int = 4096
    max_width: int = 1048576
    max_block_size: int = 4096

    def __post_init__(self):
        if any(type(v) is not int or v <= 0 for v in self.__dict__.values()):
            raise ValueError('codec limits must be positive built-in integers')


@dataclass(frozen=True)
class FactorDescriptor:
    target_sha256: str
    anchor_target_sha256: str
    record_id: str
    token_sha256: str
    stage_id: str
    shape: tuple
    bits: int
    block_size: int
    source_sha256: str
    codec_sha256: str
    payload: bytes

    def __post_init__(self):
        for value in (self.target_sha256, self.anchor_target_sha256, self.token_sha256,
                      self.source_sha256, self.codec_sha256):
            _digest(value)
        _name(self.record_id)
        _name(self.stage_id)
        shape = tuple(self.shape)
        if len(shape) != 2 or any(type(n) is not int or n <= 0 for n in shape):
            raise ValueError('descriptor requires a positive token-major shape')
        if type(self.bits) is not int or self.bits not in PRECISIONS:
            raise ValueError('codec precision must be 16, 24, 32, 40, or 48 bits')
        if type(self.block_size) is not int or not 1 <= self.block_size <= 4096:
            raise ValueError('codec block size must be between one and 4096')
        if type(self.payload) is not bytes:
            raise TypeError('codec payload must be immutable bytes')
        # Establish a payload lower bound before any decoded-array allocation.
        minimum = shape[0]*shape[1]*(self.bits//8)
        if minimum > len(self.payload):
            raise ValueError('descriptor shape exceeds available payload')
        object.__setattr__(self, 'shape', shape)
        _decode_payload(self.payload, shape, self.bits, self.block_size)

    def box(self):
        """Return exact finite token-major endpoints, suitable for transposition."""
        lo, hi, _ = _decode_payload(self.payload, self.shape, self.bits, self.block_size)
        return FloatBox(lo, hi)

    def center_radius(self):
        """Return exact dyadic centers and nonnegative radii.

        Midpoints use half-cell radii when exactly representable. At the
        smallest subnormal step, lower centers use a full-cell radius.
        Escape and exact-grid radii are zero. box() always remains tighter
        than, or equal to, this symmetric enclosure.
        """
        _, _, _, center, radius = _decode_payload(self.payload, self.shape, self.bits, self.block_size, with_radius=True)
        def freeze(x):
            return np.frombuffer(x.astype('<f8', copy=False).tobytes(), dtype='<f8').reshape(self.shape)
        return freeze(center), freeze(radius)

    @property
    def escape_count(self):
        return _decode_payload(self.payload, self.shape, self.bits, self.block_size)[2]

    @property
    def digest(self):
        return _sha(serialize(self))


def encode_factor(values, *, target_sha256, anchor_target_sha256, record_id,
                  token_sha256, stage_id, bits=16, block_size=256):
    """Encode one trusted exact factor without consulting another record."""
    if type(values) is not np.ndarray or values.dtype != np.float64 or values.ndim != 2 or not all(values.shape):
        raise TypeError('an ordinary nonempty binary64 matrix is required')
    if not np.isfinite(values).all():
        raise ValueError('factor entries must be finite')
    if type(bits) is not int or bits not in PRECISIONS:
        raise ValueError('codec precision must be 16, 24, 32, 40, or 48 bits')
    if type(block_size) is not int or not 1 <= block_size <= 4096:
        raise ValueError('codec block size must be between one and 4096')
    raw = values.astype('<f8', copy=False).tobytes(order='C')
    words = np.frombuffer(raw, dtype='<u8')
    return FactorDescriptor(target_sha256, anchor_target_sha256, record_id, token_sha256,
        stage_id, tuple(values.shape), bits, block_size, _sha(raw), codec_binding(),
        _encode_payload(words, bits, block_size))


def _header(descriptor):
    return dict(schema=SCHEMA, target_sha256=descriptor.target_sha256,
        anchor_target_sha256=descriptor.anchor_target_sha256, record_id=descriptor.record_id,
        token_sha256=descriptor.token_sha256, stage_id=descriptor.stage_id, shape=list(descriptor.shape),
        bits=descriptor.bits, block_size=descriptor.block_size, source_sha256=descriptor.source_sha256,
        codec_sha256=descriptor.codec_sha256, payload_bytes=len(descriptor.payload),
        payload_sha256=_sha(descriptor.payload), zero_rule='numeric zero endpoints use positive zero; source hash preserves original bytes')


def serialize(descriptor):
    if type(descriptor) is not FactorDescriptor:
        raise TypeError('serialization requires FactorDescriptor')
    header = _json(_header(descriptor))
    return MAGIC+struct.pack('<Q', len(header))+header+descriptor.payload


def parse(data, *, limits=LoadLimits(), expected_sha256=None):
    if type(data) is not bytes or type(limits) is not LoadLimits:
        raise TypeError('immutable bytes and codec LoadLimits are required')
    if len(data) < 16 or len(data) > limits.max_bytes or data[:8] != MAGIC:
        raise ValueError('invalid codec magic or file size')
    if expected_sha256 is not None and _sha(data) != _digest(expected_sha256):
        raise ValueError('descriptor differs from trusted digest')
    size = struct.unpack_from('<Q', data, 8)[0]
    if size > limits.max_header_bytes or size > len(data)-16:
        raise ValueError('codec header exceeds its bound')
    raw = data[16:16+size]
    try:
        header = json.loads(raw)
        canonical = _json(header)
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise ValueError('invalid codec JSON') from exc
    keys = {'schema', 'target_sha256', 'anchor_target_sha256', 'record_id', 'token_sha256', 'stage_id',
            'shape', 'bits', 'block_size', 'source_sha256', 'codec_sha256', 'payload_bytes', 'payload_sha256', 'zero_rule'}
    if canonical != raw or type(header) is not dict or set(header) != keys or header['schema'] != SCHEMA:
        raise ValueError('unsupported or noncanonical codec header')
    shape = header['shape']
    if (type(shape) is not list or len(shape) != 2 or any(type(n) is not int or n <= 0 for n in shape)
            or shape[0] > limits.max_tokens or shape[1] > limits.max_width
            or shape[0]*shape[1] > limits.max_values):
        raise ValueError('codec dimensions exceed their bound')
    if type(header['block_size']) is not int or not 1 <= header['block_size'] <= limits.max_block_size:
        raise ValueError('codec block size exceeds its bound')
    payload = data[16+size:]
    if (type(header['payload_bytes']) is not int or len(payload) != header['payload_bytes']
            or _sha(payload) != _digest(header['payload_sha256'])):
        raise ValueError('codec payload binding differs')
    descriptor = FactorDescriptor(*(header[k] for k in ('target_sha256', 'anchor_target_sha256', 'record_id',
        'token_sha256', 'stage_id')), tuple(shape), header['bits'], header['block_size'],
        header['source_sha256'], header['codec_sha256'], payload)
    if serialize(descriptor) != data:
        raise ValueError('descriptor encoding is not canonical')
    return descriptor
