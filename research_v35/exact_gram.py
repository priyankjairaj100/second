"""Bounded exact pooled Grams for binary64 fixed features.

This module introduces no floating point accumulation.  A finite binary64
matrix is converted to integers sharing a dyadic exponent.  Packed products
are summed exactly, then globally normalized by powers of two.  Deletion is
exact subtraction of committed source contributions.  Original normalization
is metadata; deletion never replaces it with the surviving token count.

``ExactGram`` is a trusted-preparation object, not a cryptographic proof of PSD.
Only accumulation and closed source-set algebra create trusted objects here.
Ordinary deserialization is untrusted.  Restoring trust additionally requires
an externally authenticated expected digest of a previously trusted archive.
Python code with arbitrary process access is outside this trust boundary.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from fractions import Fraction
import hashlib
import json
import math
import struct

import numpy as np


MAGIC = b"EGRAM35\x00"
_SEAL = object()


class GramAdmissionError(ValueError):
    """A requested operation exceeds its declared finite resource envelope."""


@dataclass(frozen=True)
class GramBudget:
    max_width: int = 768
    max_tokens: int = 256
    max_sources: int = 256
    max_product_terms: int = 75_595_776
    max_integer_bits: int = 256
    max_serialized_bytes: int = 64 * 1024 * 1024
    max_memory_bytes: int = 512 * 1024 * 1024

    def __post_init__(self):
        for value in asdict(self).values():
            if type(value) is not int or value <= 0:
                raise ValueError("Gram budget limits must be positive integers")


@dataclass(frozen=True, order=True)
class SourceCommitment:
    source_id: str
    feature_sha256: str
    gram_sha256: str
    tokens: int


@dataclass(frozen=True)
class GramAdmission:
    width: int
    tokens: int
    packed_entries: int
    feature_exponent: int
    feature_integer_bits: int
    accumulator_magnitude_bits: int
    product_terms: int
    payload_bytes_bound: int
    explicit_memory_bound: int


@dataclass(frozen=True, init=False)
class ExactGram:
    width: int
    tokens: int
    normalization: Fraction
    exponent: int
    packed: tuple[int, ...]
    sources: tuple[SourceCommitment, ...]
    trusted: bool
    admission: GramAdmission | None

    def __init__(self, width, tokens, normalization, exponent, packed, sources,
                 *, trusted=False, admission=None, _seal=None):
        if _seal is not _SEAL:
            raise TypeError("Use accumulate, Gram algebra, or loads")
        for key, value in locals().copy().items():
            if key not in {"self", "_seal"}:
                object.__setattr__(self, key, value)

    def to_bytes(self, *, budget=GramBudget()):
        return dumps(self, budget=budget)

    @property
    def source_ids(self):
        return tuple(source.source_id for source in self.sources)


def require_trusted_gram(gram):
    """Reject parsed-only data before any PSD-dependent theorem is invoked."""
    if type(gram) is not ExactGram or gram.trusted is not True:
        raise ValueError("A trusted exact Gram with source lineage is required")
    return gram


def _normalization(value):
    if isinstance(value, bool) or isinstance(value, (float, np.floating)):
        raise ValueError("normalization must be an exact positive rational")
    value = Fraction(value)
    if value <= 0 or max(value.numerator.bit_length(), value.denominator.bit_length()) > 256:
        raise ValueError("normalization must be positive and at most 256 bits")
    return value


def _shape(width, tokens, budget):
    if width < 1 or width > budget.max_width or tokens < 0 or tokens > budget.max_tokens:
        raise GramAdmissionError("width or token count exceeds the Gram budget")
    return width * (width + 1) // 2


def _bound(width, tokens, feature_exp, feature_bits, budget):
    entries = _shape(width, tokens, budget)
    terms = entries * tokens
    # Each product has magnitude < 2**(2*b).  This upper bound is deliberately
    # conservative when the number of tokens is not a power of two.
    bits = 0 if feature_bits == 0 or tokens == 0 else 2 * feature_bits + (tokens - 1).bit_length()
    payload = entries * max(1, (bits + 1 + 7) // 8)
    # CPython integer/list/tuple envelope.  This is an explicit representation
    # bound, not a promise concerning interpreter, allocator, or OS RSS.
    integer_bytes = 64 + 4 * ((max(bits, feature_bits) + 29) // 30)
    memory = (width * tokens + 2 * entries) * (integer_bytes + 16) + payload + width * tokens * 16
    if terms > budget.max_product_terms:
        raise GramAdmissionError("exact product contribution budget exceeded")
    if bits > budget.max_integer_bits:
        raise GramAdmissionError("exact accumulator bit budget exceeded")
    if payload + 65536 > budget.max_serialized_bytes:
        raise GramAdmissionError("Gram serialization budget exceeded")
    if memory > budget.max_memory_bytes:
        raise GramAdmissionError("explicit Gram representation budget exceeded")
    return GramAdmission(width, tokens, entries, feature_exp, feature_bits, bits, terms, payload, memory)


def _parts(word):
    exponent = (word >> 52) & 2047
    fraction = word & ((1 << 52) - 1)
    if exponent == 2047:
        raise ValueError("features must contain only finite binary64 values")
    if exponent == 0:
        sig, exp = fraction, -1074
    else:
        sig, exp = (1 << 52) | fraction, exponent - 1075
    if not sig:
        return 0, 0
    trailing = (sig & -sig).bit_length() - 1
    sig >>= trailing
    exp += trailing
    return (-sig if word >> 63 else sig), exp


def _feature_scan(features, budget):
    if not isinstance(features, np.ndarray) or features.dtype != np.dtype("float64") or features.ndim != 2:
        raise ValueError("features must be a native binary64 ndarray of shape (width,tokens)")
    width, tokens = features.shape
    _shape(width, tokens, budget)
    # Admit copies and a worst case word scan before materializing either.
    if width * tokens * 32 > budget.max_memory_bytes:
        raise GramAdmissionError("feature scan representation budget exceeded")
    # Work on a private snapshot after this copy. The caller must not mutate
    # input storage concurrently with the copy itself.
    array = np.array(features, dtype=np.float64, copy=True, order="C")
    minimum, maximum = None, None
    for word in array.view(np.uint64).flat:
        sig, exp = _parts(int(word))
        if sig:
            minimum = exp if minimum is None else min(minimum, exp)
            high = exp + abs(sig).bit_length()
            maximum = high if maximum is None else max(maximum, high)
    exponent = 0 if minimum is None else minimum
    bits = 0 if minimum is None else maximum - minimum
    return array, _bound(width, tokens, exponent, bits, budget)


def assess_features(features, *, budget=GramBudget()):
    """Scan finite word exponents and admit products before doing any products."""
    return _feature_scan(features, budget)[1]


def _canonical(packed, exponent):
    shift = None
    for entry in packed:
        if entry:
            trailing = (abs(entry) & -abs(entry)).bit_length() - 1
            shift = trailing if shift is None else min(shift, trailing)
            if shift == 0:
                break
    if shift is None:
        return tuple(packed), 0
    if shift:
        packed = [entry >> shift for entry in packed]
    return tuple(packed), exponent + shift


def _numeric_digest(width, exponent, packed):
    h = hashlib.sha256()
    h.update(struct.pack(">Ii", width, exponent))
    for entry in packed:
        raw = entry.to_bytes(max(1, (abs(entry).bit_length() + 8) // 8), "big", signed=True)
        h.update(struct.pack(">I", len(raw)))
        h.update(raw)
    return h.hexdigest()


def _source_id(value):
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > 256 or "\x00" in value:
        raise ValueError("source_id must be nonempty UTF-8 with at most 256 bytes and no NUL")
    return value


def accumulate(features, *, source_id, normalization=256, budget=GramBudget()):
    """Construct exact X X^T, including a commitment to the input word bytes.

    Features have shape (width,tokens). Product counts include the complete
    lower triangle. Source identity is supplied by the registered caller.
    """
    source_id = _source_id(source_id)
    normalization = _normalization(normalization)
    array, admission = _feature_scan(features, budget)
    width, tokens = array.shape
    exponent = admission.feature_exponent
    rows = []
    for row in array.view(np.uint64):
        converted = []
        for word in row:
            sig, exp = _parts(int(word))
            converted.append(0 if not sig else sig << (exp - exponent))
        rows.append(converted)
    packed = []
    for i, left in enumerate(rows):
        for right in rows[:i + 1]:
            total = 0
            for x, y in zip(left, right):
                total += x * y
            packed.append(total)
    packed, exponent = _canonical(packed, 2 * exponent)
    feature_hash = hashlib.sha256()
    feature_hash.update(struct.pack(">II", width, tokens))
    feature_hash.update(array.astype("<f8", copy=False).tobytes(order="C"))
    source = SourceCommitment(source_id, feature_hash.hexdigest(), _numeric_digest(width, exponent, packed), tokens)
    return ExactGram(width, tokens, normalization, exponent, packed, (source,), trusted=True,
                     admission=admission, _seal=_SEAL)


def _algebra(left, right, subtract, budget):
    require_trusted_gram(left)
    require_trusted_gram(right)
    if left.width != right.width or left.normalization != right.normalization:
        raise ValueError("Gram dimensions and original normalization must match")
    lmap, rmap = {s.source_id: s for s in left.sources}, {s.source_id: s for s in right.sources}
    if subtract:
        if not all(lmap.get(key) == value for key, value in rmap.items()):
            raise ValueError("deleted sources must match complete source commitments")
        sources = tuple(s for s in left.sources if s.source_id not in rmap)
        tokens = left.tokens - right.tokens
    else:
        if lmap.keys() & rmap.keys():
            raise ValueError("pooled source identities must be disjoint")
        sources = tuple(sorted(left.sources + right.sources))
        tokens = left.tokens + right.tokens
    entries = _shape(left.width, tokens, budget)
    if len(sources) > budget.max_sources:
        raise GramAdmissionError("source membership budget exceeded")
    left_bits = max((abs(x).bit_length() for x in left.packed), default=0)
    right_bits = max((abs(x).bit_length() for x in right.packed), default=0)
    exponent = min(left.exponent, right.exponent) if left_bits and right_bits else (
        left.exponent if left_bits else right.exponent)
    shifts = left.exponent - exponent, right.exponent - exponent
    # Zero operands need no shift; their canonical exponent is always zero.
    shifts = (shifts[0] if left_bits else 0, shifts[1] if right_bits else 0)
    max_bits = max(left_bits + shifts[0] if left_bits else 0,
                   right_bits + shifts[1] if right_bits else 0) + 1
    if max_bits > budget.max_integer_bits:
        raise GramAdmissionError("exact algebra accumulator bit budget exceeded")
    payload = entries * max(1, (max_bits + 8) // 8)
    memory = entries * (3 * (80 + 4 * ((max_bits + 29) // 30))) + payload
    if payload + 65536 > budget.max_serialized_bytes or memory > budget.max_memory_bytes:
        raise GramAdmissionError("exact algebra representation budget exceeded")
    sign = -1 if subtract else 1
    packed = [(x << shifts[0]) + sign * (y << shifts[1]) for x, y in zip(left.packed, right.packed)]
    packed, exponent = _canonical(packed, exponent)
    return ExactGram(left.width, tokens, left.normalization, exponent, packed, sources,
                     trusted=True, _seal=_SEAL)


def add_grams(left, right, *, budget=GramBudget()):
    return _algebra(left, right, False, budget)


def subtract_gram(pooled, deleted, *, budget=GramBudget()):
    """Delete committed complete sources; an arbitrary Gram difference is forbidden."""
    return _algebra(pooled, deleted, True, budget)


def dumps(gram, *, budget=GramBudget()):
    if type(gram) is not ExactGram:
        raise TypeError("expected ExactGram")
    entries = _shape(gram.width, gram.tokens, budget)
    if len(gram.packed) != entries or len(gram.sources) > budget.max_sources:
        raise ValueError("invalid Gram shape or membership")
    bits = max((abs(x).bit_length() for x in gram.packed), default=0)
    if bits > budget.max_integer_bits:
        raise GramAdmissionError("serialized integer bit budget exceeded")
    entry_bytes = max(1, (bits + 8) // 8)
    representation = entries * (80 + 4 * ((bits + 29) // 30))
    # JSON control characters can expand to six-byte escapes. Admit temporary
    # metadata structures before constructing the header or encoded string.
    header_bound = 512 + sum(256 + 6 * len(source.source_id.encode("utf-8")) for source in gram.sources)
    if representation + 8 * header_bound + 3 * entry_bytes * entries > budget.max_memory_bytes:
        raise GramAdmissionError("serialized Gram buffer budget exceeded")
    header = dict(schema="exact-pooled-binary64-gram-v35", width=gram.width, tokens=gram.tokens,
                  normalization=[str(gram.normalization.numerator), str(gram.normalization.denominator)],
                  exponent=gram.exponent, entry_bytes=entry_bytes,
                  sources=[asdict(source) for source in gram.sources])
    encoded = json.dumps(header, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(encoded) > 65536:
        raise GramAdmissionError("canonical Gram header exceeds 65536 bytes")
    size = len(MAGIC) + 4 + len(encoded) + entry_bytes * entries + 32
    if size > budget.max_serialized_bytes or 3 * size + representation > budget.max_memory_bytes:
        raise GramAdmissionError("serialized Gram buffer budget exceeded")
    # Avoid a join list containing one Python bytes object per matrix entry.
    buffer = bytearray(size - 32)
    prefix = MAGIC + struct.pack(">I", len(encoded)) + encoded
    buffer[:len(prefix)] = prefix
    offset = len(prefix)
    for entry in gram.packed:
        buffer[offset:offset + entry_bytes] = entry.to_bytes(entry_bytes, "big", signed=True)
        offset += entry_bytes
    body = bytes(buffer)
    return body + hashlib.sha256(body).digest()


def loads(data, *, budget=GramBudget(), trusted_sha256=None, expected_sources=None):
    """Parse a canonical archive, untrusted unless its external digest is supplied.

    ``trusted_sha256`` and ``expected_sources`` must both come from authenticated
    trusted preparation. Taking these values from the same untrusted file is
    not an authentication procedure. Ordinary parsing never establishes PSD.
    """
    if type(data) is not bytes or len(data) > budget.max_serialized_bytes or 3 * len(data) > budget.max_memory_bytes:
        raise GramAdmissionError("archive input budget exceeded")
    if len(data) < 44 or data[:8] != MAGIC or hashlib.sha256(data[:-32]).digest() != data[-32:]:
        raise ValueError("invalid Gram archive or checksum")
    if (trusted_sha256 is None) != (expected_sources is None):
        raise ValueError("trusted restore needs both external digest and source commitments")
    trusted = trusted_sha256 is not None
    if trusted and hashlib.sha256(data).hexdigest() != trusted_sha256:
        raise ValueError("trusted archive digest does not match")
    nheader = struct.unpack(">I", data[8:12])[0]
    if nheader > 65536 or 12 + nheader > len(data) - 32:
        raise ValueError("invalid Gram header length")
    # JSON can expand into many small Python objects. Bound that expansion
    # before decoding, including when the caller supplies a very small limit.
    if 64 * nheader + 3 * len(data) > budget.max_memory_bytes:
        raise GramAdmissionError("parsed header representation budget exceeded")
    header = json.loads(data[12:12 + nheader])
    if set(header) != {"schema", "width", "tokens", "normalization", "exponent", "entry_bytes", "sources"}:
        raise ValueError("invalid Gram header fields")
    if header["schema"] != "exact-pooled-binary64-gram-v35":
        raise ValueError("unsupported Gram schema")
    width, tokens, exponent, stride = (header[key] for key in ("width", "tokens", "exponent", "entry_bytes"))
    if any(type(x) is not int for x in (width, tokens, exponent, stride)):
        raise ValueError("Gram dimensions and exponent must be integers")
    entries = _shape(width, tokens, budget)
    if abs(exponent) > 4096 or stride < 1 or stride > (budget.max_integer_bits + 8) // 8:
        raise GramAdmissionError("archive exponent or integer width exceeds budget")
    if len(data) != 12 + nheader + entries * stride + 32:
        raise ValueError("invalid Gram payload length")
    parse_memory = entries * (2 * (80 + 4 * ((stride * 8 + 29) // 30))) + 5 * len(data) + 64 * nheader
    if parse_memory > budget.max_memory_bytes:
        raise GramAdmissionError("parsed integer representation budget exceeded")
    numerator, denominator = header["normalization"]
    if not isinstance(numerator, str) or not isinstance(denominator, str) or max(len(numerator), len(denominator)) > 80:
        raise ValueError("invalid normalization representation")
    normalization = _normalization(Fraction(int(numerator), int(denominator)))
    if type(header["sources"]) is not list or len(header["sources"]) > budget.max_sources:
        raise GramAdmissionError("source membership budget exceeded")
    sources = []
    for source in header["sources"]:
        if set(source) != {"source_id", "feature_sha256", "gram_sha256", "tokens"}:
            raise ValueError("invalid source commitment")
        _source_id(source["source_id"])
        for key in ("feature_sha256", "gram_sha256"):
            digest = source[key]
            if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("invalid source digest")
        if type(source["tokens"]) is not int or not 0 <= source["tokens"] <= tokens:
            raise ValueError("invalid source token count")
        sources.append(SourceCommitment(**source))
    if sources != sorted(sources) or len({s.source_id for s in sources}) != len(sources) or sum(s.tokens for s in sources) != tokens:
        raise ValueError("source membership must be unique, sorted, and token-complete")
    if trusted and tuple(sources) != tuple(expected_sources):
        raise ValueError("external trusted source commitments do not match")
    offset = 12 + nheader
    packed = tuple(int.from_bytes(data[offset + i * stride:offset + (i + 1) * stride], "big", signed=True) for i in range(entries))
    if any(x < 0 for x in (packed[i * (i + 1) // 2 + i] for i in range(width))):
        raise ValueError("negative Gram diagonal")
    canonical, canonical_exp = _canonical(packed, exponent)
    if canonical != packed or canonical_exp != exponent:
        raise ValueError("noncanonical dyadic exponent")
    gram = ExactGram(width, tokens, normalization, exponent, packed, tuple(sources), trusted=trusted, _seal=_SEAL)
    if dumps(gram, budget=budget) != data:
        raise ValueError("noncanonical Gram archive")
    return gram


def to_float64_enclosure(gram, *, budget=GramBudget()):
    """Return outward binary64 bounds on every exact *raw* Gram entry."""
    require_trusted_gram(gram)
    _shape(gram.width, gram.tokens, budget)
    if any(abs(value).bit_length() > budget.max_integer_bits for value in gram.packed):
        raise GramAdmissionError("Gram enclosure integer bit budget exceeded")
    # Finite binary64 squares have exponents at least -2148 and magnitude
    # below 2**2048. Summation adds at most ceil(log2(tokens)) magnitude bits.
    # Exact source-subset subtraction still represents a retained PSD sum.
    maximum_exponent = 2048 + ((gram.tokens - 1).bit_length() if gram.tokens else 0)
    if not -2148 <= gram.exponent <= maximum_exponent or (not gram.tokens and gram.exponent != 0):
        raise GramAdmissionError("Gram enclosure exponent exceeds binary64-source bound")
    if gram.width * gram.width * 16 > budget.max_memory_bytes:
        raise GramAdmissionError("Gram enclosure array budget exceeded")
    lower, upper = np.empty((gram.width, gram.width)), np.empty((gram.width, gram.width))
    scale = Fraction(1 << gram.exponent) if gram.exponent >= 0 else Fraction(1, 1 << -gram.exponent)
    k = 0
    for i in range(gram.width):
        for j in range(i + 1):
            value = gram.packed[k] * scale
            k += 1
            try:
                rounded = float(value)
            except OverflowError:
                rounded = math.inf if value > 0 else -math.inf
            if math.isinf(rounded):
                if rounded > 0:
                    lo, hi = np.finfo(np.float64).max, math.inf
                else:
                    lo, hi = -math.inf, -np.finfo(np.float64).max
            else:
                represented = Fraction.from_float(rounded)
                lo = float(np.nextafter(rounded, -math.inf)) if represented > value else rounded
                hi = float(np.nextafter(rounded, math.inf)) if represented < value else rounded
            lower[i, j] = lower[j, i] = lo
            upper[i, j] = upper[j, i] = hi
    return lower, upper
