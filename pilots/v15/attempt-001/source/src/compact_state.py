"""Canonical packed codes and exact current-prefix binary64 factors.

This factor_identity_v1 family stores full factors. It stores no dense Gram,
Taylor witness, feature box, or stale anchor. Hashes bind content, not execution.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import struct

import numpy as np

FAMILY = "factor_identity_v1"
MAGIC = b"VCFI\x01\x00\x00\x00"
_SHA_LENGTH = 64
_BLOCK = 65536


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _digest(value):
    if (type(value) is not str or len(value) != _SHA_LENGTH
            or any(c not in "0123456789abcdef" for c in value)):
        raise ValueError("a lowercase SHA-256 digest is required")
    return value


def _name(value):
    if type(value) is not str or not value or len(value.encode("utf-8")) > 4096:
        raise ValueError("a nonempty bounded UTF-8 identifier is required")
    if any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise ValueError("identifier contains a forbidden character")
    return value


def _positive(value):
    if type(value) is not int or value <= 0:
        raise ValueError("a positive built-in integer is required")
    return value


def token_digest(tokens):
    """Bind the complete ordered token sequence without storing the tokens."""
    tokens = tuple(tokens)
    if not tokens or any(type(t) is not int or not 0 <= t < 2**64 for t in tokens):
        raise ValueError("tokens must be nonempty built-in unsigned integers")
    return _sha(b"factor-identity-token-order-v1\0" + _json(tokens))


def _array(value):
    if type(value) is not np.ndarray or value.dtype != np.float64 or value.ndim != 2:
        raise TypeError("an ordinary binary64 NumPy matrix is required")
    if not all(value.shape) or not np.isfinite(value).all():
        raise ValueError("a nonempty finite matrix is required")
    return value


def _pack(indices, bits):
    flat = np.asarray(indices, dtype=np.uint8).ravel(order="C")
    result = []
    shifts = np.arange(bits, dtype=np.uint8)
    for start in range(0, len(flat), _BLOCK):
        chunk = flat[start:start + _BLOCK]
        binary = ((chunk[:, None] >> shifts) & 1).ravel()
        result.append(np.packbits(binary, bitorder="little").tobytes())
    return b"".join(result)


def _unpack(packed, count, bits):
    # Each full block contains a multiple of eight indices.
    result = np.empty(count, dtype=np.uint8)
    byte_block = _BLOCK * bits // 8
    weights = (1 << np.arange(bits, dtype=np.uint8))
    for start in range(0, count, _BLOCK):
        size = min(_BLOCK, count - start)
        offset = start * bits // 8
        chunk = np.frombuffer(packed[offset:offset + byte_block], dtype=np.uint8)
        binary = np.unpackbits(chunk, bitorder="little")[:size * bits]
        result[start:start + size] = (binary.reshape(size, bits) * weights).sum(axis=1)
    return result


def _dyadic_parts(scale):
    numerator, denominator = scale.as_integer_ratio()
    zeros = (numerator & -numerator).bit_length() - 1
    return numerator >> zeros, zeros - (denominator.bit_length() - 1)


def _dyadic_scales(values, rows, bits):
    values = tuple(values)
    if len(values) != rows or any(type(s) is not float or not math.isfinite(s) or s <= 0 for s in values):
        raise ValueError("dyadic rows require one positive finite Python float scale per row")
    half = 1 << (bits - 1)
    for scale in values:
        odd, exponent = _dyadic_parts(scale)
        # The largest odd midpoint numerator controls precision. The smallest
        # half-step controls underflow. The negative endpoint controls overflow.
        if (exponent < -1073 or (odd * (2 * half - 1)).bit_length() > 53
                or exponent + odd.bit_length() + bits - 2 > 1023):
            raise ValueError("every dyadic grid code and half-step midpoint must be exactly finite binary64")
    return values


def _dyadic_grid_bytes(scale, bits):
    """Construct exact binary64 code encodings using integer operations only."""
    odd, exponent = _dyadic_parts(scale)
    half = 1 << (bits - 1)
    values = []
    for code in range(-half, half):
        if code == 0:
            values.append(struct.pack("<Q", 0))
            continue
        numerator = odd * abs(code)
        zeros = (numerator & -numerator).bit_length() - 1
        numerator >>= zeros
        power = exponent + zeros
        length = numerator.bit_length()
        top = power + length - 1
        if top >= -1022:
            mantissa = numerator << (53 - length)
            encoded = ((top + 1023) << 52) | (mantissa - (1 << 52))
        else:
            encoded = numerator << (power + 1074)
        if code < 0:
            encoded |= 1 << 63
        values.append(struct.pack("<Q", encoded))
    return b"".join(values)


@dataclass(frozen=True)
class StageCodes:
    stage_id: str
    rows: int
    columns: int
    grid_axis: str
    bits: int
    scale_exponents: tuple[int, ...]
    packed_indices: bytes
    scale_values: tuple[float, ...] = ()

    def __post_init__(self):
        _name(self.stage_id)
        _positive(self.rows)
        _positive(self.columns)
        if self.grid_axis not in ("row", "column", "dyadic_row"):
            raise ValueError("grid_axis must be row, column, or dyadic_row")
        if type(self.bits) is not int or not 2 <= self.bits <= 8:
            raise ValueError("bits must be a built-in integer between two and eight")
        scales = tuple(self.scale_exponents)
        if self.grid_axis == "dyadic_row":
            if scales:
                raise ValueError("dyadic rows cannot also declare power-of-two exponents")
            object.__setattr__(self, "scale_values", _dyadic_scales(self.scale_values, self.rows, self.bits))
        else:
            if tuple(self.scale_values):
                raise ValueError("power-of-two grids cannot also declare dyadic row scales")
            object.__setattr__(self, "scale_values", ())
            required = self.rows if self.grid_axis == "row" else self.columns
            if len(scales) != required or any(
                    type(e) is not int or not -1074 <= e <= 1024 - self.bits for e in scales):
                raise ValueError("grid scales do not match the declared finite grid")
        object.__setattr__(self, "scale_exponents", scales)
        if type(self.packed_indices) is not bytes:
            raise TypeError("packed indices must be immutable bytes")
        bit_count = self.rows * self.columns * self.bits
        if len(self.packed_indices) != (bit_count + 7) // 8:
            raise ValueError("packed index length does not match its shape")
        if bit_count % 8 and self.packed_indices[-1] >> (bit_count % 8):
            raise ValueError("unused packed index bits must be zero")

    @classmethod
    def from_array(cls, stage_id, values, *, grid_axis, bits, scale_exponents=(), scale_values=()):
        values = _array(values)
        exponents = tuple(scale_exponents)
        # Validate grid metadata before NumPy shifts or array allocations.
        rows, columns = values.shape
        if grid_axis not in ("row", "column", "dyadic_row"):
            raise ValueError("grid_axis must be row, column, or dyadic_row")
        if type(bits) is not int or not 2 <= bits <= 8:
            raise ValueError("bits must be between two and eight")
        if grid_axis == "dyadic_row":
            if exponents:
                raise ValueError("dyadic rows cannot also declare power-of-two exponents")
            scales = _dyadic_scales(scale_values, rows, bits)
            indices = np.empty(values.shape, dtype=np.uint8)
            value_bits = values.astype("<f8", copy=False).view("<u8")
            for row, scale in enumerate(scales):
                grid_bits = np.frombuffer(_dyadic_grid_bytes(scale, bits), dtype="<u8")
                order = np.argsort(grid_bits)
                ordered = grid_bits[order]
                # Rational zero has one index. Normalize the negative-zero bit
                # pattern without a floating comparison or any target division.
                row_bits = np.where(value_bits[row] == (1 << 63), 0, value_bits[row])
                candidate = np.searchsorted(ordered, row_bits)
                if np.any(candidate >= len(ordered)):
                    raise ValueError("a value is not an exact member of its declared dyadic grid")
                if not np.array_equal(ordered[candidate], row_bits):
                    raise ValueError("a value is not an exact member of its declared dyadic grid")
                indices[row] = order[candidate]
            return cls(stage_id, rows, columns, grid_axis, bits, (), _pack(indices, bits), scales)
        if tuple(scale_values):
            raise ValueError("power-of-two grids cannot also declare dyadic row scales")
        required = rows if grid_axis == "row" else columns
        if len(exponents) != required or any(
                type(e) is not int or not -1074 <= e <= 1024 - bits for e in exponents):
            raise ValueError("invalid grid exponents")
        shifts = np.asarray(exponents, dtype=np.int64)
        shifts = shifts[:, None] if grid_axis == "row" else shifts[None, :]
        with np.errstate(over="ignore", under="ignore", invalid="ignore"):
            normalized = np.ldexp(values, -shifts)
            restored = np.ldexp(normalized, shifts)
        half = 1 << (bits - 1)
        if (not np.isfinite(normalized).all() or not np.array_equal(restored, values)
                or np.any(normalized != np.floor(normalized))
                or np.any(normalized < -half) or np.any(normalized >= half)):
            raise ValueError("a value is not an exact member of its declared grid")
        packed = _pack((normalized + half).astype(np.uint8), bits)
        return cls(stage_id, rows, columns, grid_axis, bits, exponents, packed)

    def metadata(self):
        result = dict(stage_id=self.stage_id, rows=self.rows, columns=self.columns,
                      grid_axis=self.grid_axis, bits=self.bits,
                      nbytes=len(self.packed_indices), sha256=_sha(self.packed_indices))
        if self.grid_axis == "dyadic_row":
            result["scale_values_hex"] = [value.hex() for value in self.scale_values]
        else:
            result["scale_exponents"] = list(self.scale_exponents)
        return result

    @property
    def digest(self):
        return _sha(b"factor-identity-stage-v1\0" + _json(self.metadata()))

    def indices_array(self):
        value = _unpack(self.packed_indices, self.rows * self.columns, self.bits)
        return np.frombuffer(value.tobytes(), dtype=np.uint8).reshape(self.rows, self.columns)

    @property
    def shape(self):
        return (self.rows, self.columns)

    def array(self):
        """Return an immutable token-independent matrix of decoded grid values."""
        return self.values_array()

    def values_array(self):
        if self.grid_axis == "dyadic_row":
            indices = self.indices_array()
            # Integer lookup copies exact encodings, including subnormals.
            values = np.empty(self.shape, dtype="<u8")
            for row, scale in enumerate(self.scale_values):
                grid = np.frombuffer(_dyadic_grid_bytes(scale, self.bits), dtype="<u8")
                values[row] = grid[indices[row]]
            return np.frombuffer(values.tobytes(), dtype="<f8").reshape(self.shape)
        indices = self.indices_array().astype(np.float64)
        indices -= 1 << (self.bits - 1)
        shifts = np.asarray(self.scale_exponents, dtype=np.int64)
        shifts = shifts[:, None] if self.grid_axis == "row" else shifts[None, :]
        values = np.ldexp(indices, shifts)
        return np.frombuffer(values.astype("<f8").tobytes(), dtype="<f8").reshape(self.rows, self.columns)


def prefix_digest(target_sha256, preceding_stages=()):
    """Bind exact ordered ancestor code identities to the quantization target."""
    _digest(target_sha256)
    stages = tuple(preceding_stages)
    if any(type(stage) is not StageCodes for stage in stages):
        raise TypeError("prefix stages must be StageCodes")
    return _sha(b"factor-identity-prefix-v1\0" + _json(dict(
        target_sha256=target_sha256, stages=[stage.digest for stage in stages])))


@dataclass(frozen=True)
class RecordFactor:
    stage_id: str
    record_id: str
    prefix_sha256: str
    token_sha256: str
    token_count: int
    width: int
    binary64: bytes

    def __post_init__(self):
        _name(self.stage_id)
        _name(self.record_id)
        _digest(self.prefix_sha256)
        _digest(self.token_sha256)
        _positive(self.token_count)
        _positive(self.width)
        if type(self.binary64) is not bytes:
            raise TypeError("factor storage must be immutable bytes")
        if len(self.binary64) != self.token_count * self.width * 8:
            raise ValueError("factor byte length does not match its shape")
        values = np.frombuffer(self.binary64, dtype="<f8")
        if not np.isfinite(values).all():
            raise ValueError("factors must be finite binary64 values")
        if np.any((values == 0) & np.signbit(values)):
            raise ValueError("factor zero must use the positive-zero encoding")

    @classmethod
    def from_array(cls, stage_id, record_id, features, *, prefix_sha256, token_sha256):
        features = _array(features)
        copy = features.astype("<f8", copy=True)
        copy[copy == 0] = 0.0
        return cls(stage_id, record_id, prefix_sha256, token_sha256,
                   features.shape[0], features.shape[1], copy.tobytes(order="C"))

    def array(self):
        return np.frombuffer(self.binary64, dtype="<f8").reshape(self.token_count, self.width)

    def metadata(self):
        return dict(stage_id=self.stage_id, record_id=self.record_id,
                    prefix_sha256=self.prefix_sha256, token_sha256=self.token_sha256,
                    token_count=self.token_count, width=self.width,
                    nbytes=len(self.binary64), sha256=_sha(self.binary64))

    @property
    def digest(self):
        return _sha(b"factor-identity-record-factor-v1\0" + _json(self.metadata()))


@dataclass(frozen=True)
class CompactState:
    target_sha256: str
    stages: tuple[StageCodes, ...]
    factors: tuple[RecordFactor, ...]

    def __post_init__(self):
        _digest(self.target_sha256)
        stages, factors = tuple(self.stages), tuple(self.factors)
        if any(type(s) is not StageCodes for s in stages):
            raise TypeError("stages must contain StageCodes")
        if any(type(f) is not RecordFactor for f in factors):
            raise TypeError("factors must contain RecordFactor")
        if not stages or len({s.stage_id for s in stages}) != len(stages):
            raise ValueError("stages must be nonempty with unique identifiers")
        order = {stage.stage_id: i for i, stage in enumerate(stages)}
        expected_prefix = {s.stage_id: prefix_digest(self.target_sha256, stages[:i])
                           for i, s in enumerate(stages)}
        memberships = {}
        keys = set()
        for factor in factors:
            if factor.stage_id not in order:
                raise ValueError("factor refers to an unknown stage")
            key = (factor.stage_id, factor.record_id)
            if key in keys:
                raise ValueError("duplicate stage-record factor")
            keys.add(key)
            stage = stages[order[factor.stage_id]]
            if factor.width != stage.columns:
                raise ValueError("factor width differs from its stage width")
            if factor.prefix_sha256 != expected_prefix[factor.stage_id]:
                raise ValueError("factor does not bind the exact current stage prefix")
            membership = (factor.token_count, factor.token_sha256)
            if factor.record_id in memberships and memberships[factor.record_id] != membership:
                raise ValueError("record token order differs between stages")
            memberships[factor.record_id] = membership
        if len(keys) != len(stages) * len(memberships):
            raise ValueError("every retained record needs one factor for every stage")
        factors = tuple(sorted(factors, key=lambda f: (order[f.stage_id], f.record_id)))
        object.__setattr__(self, "stages", stages)
        object.__setattr__(self, "factors", factors)

    @property
    def record_ids(self):
        return tuple(sorted({factor.record_id for factor in self.factors}))

    @property
    def digest(self):
        return _sha(serialize(self))

    @property
    def factor_bytes(self):
        return sum(len(f.binary64) for f in self.factors)

    @property
    def code_bytes(self):
        return sum(len(s.packed_indices) for s in self.stages)


def _header(state):
    return dict(family=FAMILY, target_sha256=state.target_sha256,
                record_ids=list(state.record_ids), stages=[s.metadata() for s in state.stages],
                factors=[f.metadata() for f in state.factors])


def serialize(state):
    """Return one deterministic binary file. The caller must retain its digest."""
    if type(state) is not CompactState:
        raise TypeError("state must be CompactState")
    header = _json(_header(state))
    return b"".join([MAGIC, struct.pack("<Q", len(header)), header]
                    + [s.packed_indices for s in state.stages]
                    + [f.binary64 for f in state.factors])


@dataclass(frozen=True)
class LoadLimits:
    max_bytes: int = 512 * 1024 * 1024
    max_header_bytes: int = 8 * 1024 * 1024
    max_stages: int = 4096
    max_records: int = 100000
    max_factors: int = 100000
    max_code_elements: int = 268435456
    max_factor_values: int = 67108864

    def __post_init__(self):
        for value in self.__dict__.values():
            _positive(value)


def _keys(value, expected):
    if type(value) is not dict or set(value) != set(expected):
        raise ValueError("unexpected or missing state metadata fields")


def parse(data, *, limits=LoadLimits(), expected_sha256=None):
    """Parse bounded canonical bytes and reject corruption or stale bindings.

    Supply expected_sha256 from a trusted receipt to detect changed metadata.
    Internal hashes alone cannot authenticate an adversary's replacement file.
    """
    if type(data) is not bytes or type(limits) is not LoadLimits:
        raise TypeError("immutable bytes and LoadLimits are required")
    if len(data) > limits.max_bytes or len(data) < 16 or data[:8] != MAGIC:
        raise ValueError("invalid state magic or file size")
    if expected_sha256 is not None and _sha(data) != _digest(expected_sha256):
        raise ValueError("state does not match its trusted digest")
    header_size = struct.unpack("<Q", data[8:16])[0]
    if header_size > limits.max_header_bytes or header_size > len(data) - 16:
        raise ValueError("state header exceeds its bounds")
    raw_header = data[16:16 + header_size]
    try:
        header = json.loads(raw_header)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError("invalid state JSON") from exc
    try:
        canonical = _json(header)
    except (ValueError, TypeError, RecursionError) as exc:
        raise ValueError("invalid canonical state JSON") from exc
    if canonical != raw_header:
        raise ValueError("state JSON is not canonical")
    _keys(header, ("family", "target_sha256", "record_ids", "stages", "factors"))
    if header["family"] != FAMILY:
        raise ValueError("unsupported state family")
    _digest(header["target_sha256"])
    if any(type(header[key]) is not list for key in ("record_ids", "stages", "factors")):
        raise ValueError("state collections must be lists")
    if (len(header["record_ids"]) > limits.max_records
            or len(header["stages"]) > limits.max_stages
            or len(header["factors"]) > limits.max_factors):
        raise ValueError("state collection exceeds its bound")
    cursor = 16 + header_size

    def chunk(metadata, expected_size):
        nonlocal cursor
        if type(metadata["nbytes"]) is not int or metadata["nbytes"] != expected_size:
            raise ValueError("declared payload length is inconsistent")
        if expected_size > len(data) - cursor:
            raise ValueError("truncated state payload")
        value = data[cursor:cursor + expected_size]
        cursor += expected_size
        if _sha(value) != _digest(metadata["sha256"]):
            raise ValueError("state payload hash mismatch")
        return value

    stages, factors = [], []
    code_elements = factor_values = 0
    for entry in header["stages"]:
        dyadic = type(entry) is dict and entry.get("grid_axis") == "dyadic_row"
        scale_key = "scale_values_hex" if dyadic else "scale_exponents"
        _keys(entry, ("stage_id", "rows", "columns", "grid_axis", "bits",
                      scale_key, "nbytes", "sha256"))
        rows, columns = _positive(entry["rows"]), _positive(entry["columns"])
        bits = entry["bits"]
        if type(bits) is not int or not 2 <= bits <= 8:
            raise ValueError("invalid packed code width")
        if type(entry[scale_key]) is not list:
            raise ValueError("scale metadata must be a list")
        scales, exponents = (), ()
        if dyadic:
            decoded = []
            for text in entry[scale_key]:
                if type(text) is not str or len(text) > 64:
                    raise ValueError("dyadic scales require bounded canonical hexadecimal strings")
                try:
                    scale = float.fromhex(text)
                except (ValueError, OverflowError) as exc:
                    raise ValueError("invalid dyadic scale encoding") from exc
                if scale.hex() != text:
                    raise ValueError("dyadic scale encoding is not canonical")
                decoded.append(scale)
            scales = tuple(decoded)
        else:
            exponents = tuple(entry[scale_key])
        code_elements += rows * columns
        if code_elements > limits.max_code_elements:
            raise ValueError("code elements exceed their bound")
        value = chunk(entry, (rows * columns * bits + 7) // 8)
        stages.append(StageCodes(entry["stage_id"], rows, columns, entry["grid_axis"], bits,
                                 exponents, value, scales))
    for entry in header["factors"]:
        _keys(entry, ("stage_id", "record_id", "prefix_sha256", "token_sha256",
                      "token_count", "width", "nbytes", "sha256"))
        count, width = _positive(entry["token_count"]), _positive(entry["width"])
        factor_values += count * width
        if factor_values > limits.max_factor_values:
            raise ValueError("factor values exceed their bound")
        value = chunk(entry, count * width * 8)
        factors.append(RecordFactor(entry["stage_id"], entry["record_id"], entry["prefix_sha256"],
                                    entry["token_sha256"], count, width, value))
    if cursor != len(data):
        raise ValueError("trailing state payload")
    state = CompactState(header["target_sha256"], tuple(stages), tuple(factors))
    if _header(state) != header:
        raise ValueError("state member order or metadata is not canonical")
    return state
