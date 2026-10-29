"""Isolated V26-compatible payload-decoder prototype, not a campaign worker.

Does not alter repository files, codec bindings or scientific runtime guards.
The caller must still use the legacy framing/hash/identity checks. Integration
into any service requires a NEW implementation manifest and registration.
"""
import ctypes
import hashlib
from pathlib import Path
import subprocess
import sys
import numpy as np

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'decode.c'
_library = None
ERRORS = {
    1: 'truncated compressed factor block', 2: 'invalid local block exponent',
    3: 'unused flag bits must be zero', 4: 'reserved compressed factor flag',
    5: 'invalid exact escape encoding', 6: 'factor entries must be finite',
    7: 'dyadic endpoint is not exactly finite binary64',
    8: 'unnecessary exact escape is not canonical',
    9: 'trailing compressed factor payload', 10: 'prototype admission failed',
}

def library():
    global _library
    if _library is None:
        if sys.byteorder != 'little':
            raise RuntimeError('prototype has only little-endian qualification')
        key = hashlib.sha256(SOURCE.read_bytes()).hexdigest()[:16]
        target = ROOT / ('decode-' + key + '.so')
        if not target.exists():
            subprocess.run(['cc', '-std=c11', '-O3', '-Wall', '-Wextra', '-Werror',
                            '-shared', '-fPIC', str(SOURCE), '-o', str(target)], check=True)
        _library = ctypes.CDLL(str(target))
        _library.decode.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_size_t,
            ctypes.c_uint, ctypes.c_size_t] + [ctypes.c_void_p]*5
        _library.decode.restype = ctypes.c_int
    return _library

def decode_payload(payload, shape, bits, block_size, *, with_radius=False):
    if type(payload) is not bytes:
        raise TypeError('immutable payload required')
    if (len(shape) != 2 or any(type(n) is not int or n <= 0 for n in shape)
        or type(bits) is not int or bits not in (16, 24, 32, 40, 48)
        or type(block_size) is not int or not 1 <= block_size <= 4096):
        raise ValueError('prototype admission failed')
    total = shape[0]*shape[1]
    if total > 16000000 or len(payload) > 128*2**20 or total*(bits//8) > len(payload):
        raise ValueError('prototype admission failed')
    lower = np.empty(total, dtype='<u8')
    upper = np.empty(total, dtype='<u8')
    center = np.empty(total, dtype='<u8') if with_radius else None
    radius = np.empty(total, dtype='<u8') if with_radius else None
    escapes = ctypes.c_size_t()
    code = library().decode(payload, len(payload), total, bits, block_size,
        lower.ctypes.data, upper.ctypes.data,
        center.ctypes.data if with_radius else None,
        radius.ctypes.data if with_radius else None, ctypes.byref(escapes))
    if code:
        raise ValueError(ERRORS[code])
    result = (lower.view('<f8').reshape(shape), upper.view('<f8').reshape(shape), escapes.value)
    if with_radius:
        result += (center.view('<f8').reshape(shape), radius.view('<f8').reshape(shape))
    return result
