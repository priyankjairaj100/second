"""Explicit optional MPFR enclosures for correctly rounded finite primitives.

The reference rational backend remains the default. The MPFR backend returns
only after directed endpoints round to identical binary64 bit patterns. It
preserves finite values on the common completion domain. It does not assert
identical rejection or resource behavior for both enclosure implementations.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from fractions import Fraction
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import sys
from . import certified_intervals as ci

_BACKEND=ContextVar('calibration_finite_primitives',default='rational')


@contextmanager
def primitive_scope(backend):
    if backend not in ('rational','mpfr_enclosure'):
        raise ValueError('unsupported finite primitive backend')
    token=_BACKEND.set(backend)
    try:yield
    finally:_BACKEND.reset(token)


def _fraction(value):
    numerator,denominator=value.as_integer_ratio()
    return Fraction(int(numerator),int(denominator))


def round_mpfr(name,value,*,initial_bits=96,max_bits=3072):
    import gmpy2 as g
    if name not in ('exp','sqrt','erf','tanh'):raise ValueError('unsupported primitive')
    x=ci._finite_input(value)
    if name=='sqrt' and x<0:raise ValueError('negative square root')
    if not x and name!='exp':return value
    if name=='exp' and x>=1024:return float('inf')
    # Keep exceptional large-argument behavior on the reference path.
    if abs(value)>1024:
        return getattr(ci,'round_'+name)(value,initial_bits=initial_bits,max_bits=max_bits)
    def context(bits, rounding):
        # g.context starts from defaults, not the ambient context. Bind these
        # settings explicitly so exponent limits and traps cannot alter bounds.
        return g.context(precision=max(64,bits+8), round=rounding,
                         emin=-16384, emax=16384, subnormalize=False,
                         trap_underflow=False, trap_overflow=False,
                         trap_inexact=False, trap_invalid=False,
                         trap_erange=False, trap_divzero=False,
                         allow_complex=False)
    def enclose(bits):
        # Every binary64 input has at most 53 significant bits. Conversion
        # is exact at this precision, including binary64 subnormals.
        with context(bits, g.RoundDown):
            lower=getattr(g,name)(g.mpfr(value))
        with context(bits, g.RoundUp):
            upper=getattr(g,name)(g.mpfr(value))
        if not g.is_finite(lower) or not g.is_finite(upper):
            raise ci.ArithmeticLimit('MPFR interval is nonfinite')
        return ci.Interval(_fraction(lower),_fraction(upper),bits).outward()
    return ci.round_interval(enclose,initial_bits=initial_bits,max_bits=max_bits)


def rounded(name,value):
    if _BACKEND.get()=='rational':return getattr(ci,'round_'+name)(value)
    return round_mpfr(name,value)


@lru_cache(maxsize=2)
def _primitive_manifest_bytes(backend):
    if backend not in ('rational','mpfr_enclosure'):raise ValueError('unsupported primitive backend')
    result={'backend':backend,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'rounding':'directed real enclosure; identical RN-even binary64 endpoint encodings',
            'completion_domain_equivalence_claimed':False}
    if backend=='mpfr_enclosure':
        import gmpy2 as g
        result.update(gmpy2=g.version(),mpfr=g.mpfr_version(),gmp=g.mp_version(),
                      mpfr_context={"precision": "max(64, interval_bits+8)",
                                    "emin": -16384, "emax": 16384,
                                    "subnormalize": False, "traps": False,
                                    "rounds": ["toward_negative_infinity", "toward_positive_infinity"]})
        files={Path(module.__file__) for name,module in sys.modules.items()
               if name.startswith('gmpy2') and getattr(module,'__file__',None) and str(module.__file__).endswith('.so')}
        for line in Path('/proc/self/maps').read_text().splitlines():
            field=line.split()[-1]
            if field.startswith('/') and any(word in Path(field).name for word in ('libmpfr','libgmp','libmpc')):
                files.add(Path(field))
        result['binary_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
        if not result['binary_sha256']:raise RuntimeError('MPFR binary identity unavailable')
    return json.dumps(result,sort_keys=True,separators=(",", ":")).encode("utf-8")


def primitive_manifest(backend):
    """Return an independent binding. Callers cannot alter cached identities."""
    return json.loads(_primitive_manifest_bytes(backend))
