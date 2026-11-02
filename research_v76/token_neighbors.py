"""Extend V50's exact neighbour primitive to both token coefficient libraries.

Dedicated single-thread processes only. Historical files are never edited.
Every compiled source, adapter and original wrapper remains manifest-bound.
"""
from contextlib import contextmanager
import ctypes
import hashlib
from pathlib import Path
import threading

from research_v50.neighbors import HELPER, PROBE
from src import native_token_coefficients_v30 as point
from src import native_box_coefficients_v31 as box
from src.transformer_backend import _check_runtime

_CACHE = {}
_ACTIVE = False

def transformed(raw):
    for name,direction in (('down','-INFINITY'),('up','INFINITY')):
        old=f'static double {name}(double x) {{ return nextafter(x, {direction}); }}'
        if raw.count(old)!=1:
            raise RuntimeError('Historical neighbour primitive changed')
        raw=raw.replace(old,f'static double {name}(double x) {{ return v50_neighbor(x, {int(name=="up")}); }}')
    marker='typedef struct { double lo, hi; } box;'
    if raw.count(marker)!=1:
        raise RuntimeError('Historical interval type changed')
    position=raw.index(marker)
    return raw[:position]+HELPER+raw[position:]+PROBE

def _modules():
    return ((point,point.prepare_native_token_coefficients),
            (box,box.prepare_native_box_coefficients))

@contextmanager
def enabled():
    global _ACTIVE
    if _ACTIVE or threading.active_count()!=1:
        raise RuntimeError('Dedicated single-thread worker required')
    _check_runtime()
    _ACTIVE=True
    saved=[]
    try:
        for module,prepare in _modules():
            old=(module._C_SOURCE,module._NATIVE,module._BUILD,module._DIRECTORY)
            saved.append((module,old))
            raw=transformed(old[0])
            key=(module.__name__,hashlib.sha256(raw.encode()).hexdigest())
            module._C_SOURCE=raw
            cached=_CACHE.get(key)
            if cached is None:
                module._NATIVE=module._BUILD=module._DIRECTORY=None
                prepare()
                native=module._NATIVE
                native.v50_layout.restype=ctypes.c_int
                if native.v50_layout()!=1:
                    raise RuntimeError('Unsupported binary64/runtime layout')
                ptr=ctypes.POINTER(ctypes.c_uint64)
                native.v50_compare.argtypes=[ctypes.c_size_t,ptr,ptr]
                native.v50_compare.restype=ctypes.c_int
                module._BUILD=dict(module._BUILD,
                    adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    original_c_source_sha256=hashlib.sha256(old[0].encode()).hexdigest(),
                    backend='normal_neighbor_token_v76')
                cached=(module._NATIVE,module._BUILD,module._DIRECTORY)
                _CACHE[key]=cached
            module._NATIVE,module._BUILD,module._DIRECTORY=cached
        yield {m.__name__:dict(m._BUILD) for m,_ in _modules()}
    finally:
        for module,old in reversed(saved):
            module._C_SOURCE,module._NATIVE,module._BUILD,module._DIRECTORY=old
        _ACTIVE=False
