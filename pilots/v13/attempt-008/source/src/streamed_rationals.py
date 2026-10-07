"""Stream the existing integer-pair JSON encoding of exact rational state."""
from fractions import Fraction
from collections.abc import Mapping, Sequence
import hashlib
import json
from .compact_exact import CompactDyadicVector


def iter_rational_json(value):
    if isinstance(value, Fraction):
        yield b'[' + str(value.numerator).encode() + b',' + str(value.denominator).encode() + b']'
    elif isinstance(value, CompactDyadicVector):
        yield b'['
        for i, number in enumerate(value.floats()):
            if i:yield b','
            numerator, denominator = number.as_integer_ratio()
            yield b'[' + str(numerator).encode() + b',' + str(denominator).encode() + b']'
        yield b']'
    elif isinstance(value, Mapping):
        yield b'{'
        for i, key in enumerate(sorted(value)):
            if i:yield b','
            yield json.dumps(key,ensure_ascii=False,separators=(',',':')).encode('utf-8')
            yield b':'
            yield from iter_rational_json(value[key])
        yield b'}'
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        yield b'['
        for i, child in enumerate(value):
            if i:yield b','
            yield from iter_rational_json(child)
        yield b']'
    else:
        yield json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')


def rational_json_sha256(value):
    digest = hashlib.sha256()
    buffer = bytearray()
    for chunk in iter_rational_json(value):
        buffer.extend(chunk)
        if len(buffer) >= 65536:
            digest.update(buffer)
            buffer.clear()
    if buffer:digest.update(buffer)
    return digest.hexdigest()
