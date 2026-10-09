"""Finite causal attention with independent entries batched in NumPy.

Every score and value reduction keeps the scalar reference order. Separate
multiply and add operations prevent contraction. No BLAS reduction is used.
Verified MPFR exponentials can share contexts without trusting float casts.
"""
from fractions import Fraction

import numpy as np

from . import certified_intervals as intervals
from . import finite_primitives as primitives
from .certified_transformer import _Finite
from .transformer_backend import FiniteTargetError, _check_runtime


def _mpfr_context(g, rounding):
    return g.context(precision=104, round=rounding,
        emin=-16384, emax=16384, subnormalize=False,
        trap_underflow=False, trap_overflow=False, trap_inexact=False,
        trap_invalid=False, trap_erange=False, trap_divzero=False,
        allow_complex=False)


def _round_mpfr_endpoint(value):
    """Convert the exact public rational representation, without an MPFR cast."""
    numerator,denominator = value.as_integer_ratio()
    return intervals.round_fraction(Fraction(int(numerator),int(denominator)))


def batch_rounded_primitive(name,values, *, chunk_size=4096):
    """Return proved RN-even primitive values under the active backend.

    Directed MPFR endpoints use 104 bits. Equal exact binary64 conversions
    prove the result. Ambiguity and exceptional arguments use rounded(), with
    its unchanged precision limit and extreme-argument behavior. The rational
    primitive backend always uses rounded() directly.
    """
    if name not in ('exp','tanh','erf','sqrt'):
        raise ValueError('unsupported finite primitive')
    if type(values) is not np.ndarray or values.dtype != np.float64:
        raise TypeError('primitive inputs must be an ordinary binary64 NumPy array')
    if not np.all(np.isfinite(values)):
        raise FiniteTargetError('nonfinite certified decoder intermediate')
    if type(chunk_size) is not int or chunk_size < 1:
        raise ValueError('chunk_size must be a positive built-in integer')
    flat = values.ravel(order='C')
    result = np.empty_like(flat)
    if primitives._BACKEND.get() != 'mpfr_enclosure':
        for i,value in enumerate(flat):
            result[i] = primitives.rounded(name,float(value))
        return result.reshape(values.shape)
    import gmpy2 as g
    for start in range(0,len(flat),chunk_size):
        stop = min(start+chunk_size,len(flat))
        indices,arguments = [],[]
        for i in range(start,stop):
            value = float(flat[i])
            if value == 0.0:
                result[i] = 1.0 if name == 'exp' else value
            elif abs(value) > 1024.0 or (name == 'exp' and value >= 1024.0) or (name == 'sqrt' and value < 0.0):
                result[i] = primitives.rounded(name,value)
            else:
                indices.append(i)
                arguments.append(value)
        with _mpfr_context(g,g.RoundDown):
            lower = [getattr(g,name)(g.mpfr(value)) for value in arguments]
        with _mpfr_context(g,g.RoundUp):
            upper = [getattr(g,name)(g.mpfr(value)) for value in arguments]
        for i,value,lo,hi in zip(indices,arguments,lower,upper):
            if g.is_finite(lo) and g.is_finite(hi):
                low = _round_mpfr_endpoint(lo)
                high = _round_mpfr_endpoint(hi)
                if intervals._float_bits(low) == intervals._float_bits(high):
                    result[i] = low
                    continue
            result[i] = primitives.rounded(name,value)
    return result.reshape(values.shape)


def batch_rounded_exp(values, *, chunk_size=4096):
    """Backward-compatible explicit exponential interface."""
    return batch_rounded_primitive('exp',values,chunk_size=chunk_size)


def finite_attention(qkv,width,heads,constant):
    """Return _Finite rows with the reference causal scalar arithmetic order.

    Only ordinary finite binary64 values are supported, not proof jets.
    The constant function must return the declared _Finite constants.
    Caller inputs must remain unchanged during this call.
    """
    _check_runtime()
    if type(width) is not int or type(heads) is not int or width < 1 or heads < 1 or width % heads:
        raise ValueError('width must be positive and divisible by the positive head count')
    if not isinstance(qkv,(tuple,list)):
        raise TypeError('qkv must contain finite rows')
    for row in qkv:
        if not isinstance(row,(tuple,list)) or len(row) != 3*width:
            raise ValueError('each qkv row must have three times the model width')
        if any(type(value) is not _Finite or not isinstance(value.value,(float,np.float64)) for value in row):
            raise TypeError('ordered finite attention cannot evaluate proof jets or non-binary64 values')
    zero = constant(0)
    divisor = constant(width//heads).sqrt()
    if type(zero) is not _Finite or type(divisor) is not _Finite:
        raise TypeError('constant must return finite scalar values')
    if zero.value != 0.0:
        raise ValueError('constant zero must equal binary64 zero')
    tokens = len(qkv)
    if tokens > 2**53:
        raise ValueError('softmax length exceeds the exact integer summation bound')
    if not tokens:
        return ()
    values = np.asarray([[float(value.value) for value in row] for row in qkv],dtype=np.float64)
    if not np.all(np.isfinite(values)):
        raise FiniteTargetError('nonfinite certified decoder intermediate')
    tiny = np.array([np.finfo(np.float64).smallest_subnormal],dtype=np.float64)
    if np.multiply(tiny,1.0)[0] != tiny[0] or np.add(tiny,0.0)[0] != tiny[0]:
        raise FiniteTargetError('vector subnormal behavior differs')
    head_width = width//heads
    query = values[:,:width].reshape(tokens,heads,head_width)
    key = values[:,width:2*width].reshape(tokens,heads,head_width)
    value = values[:,2*width:].reshape(tokens,heads,head_width)
    # Only actual causal pairs exist. Unused future scores are never evaluated.
    query_ids,key_ids = np.tril_indices(tokens)
    starts = np.arange(tokens,dtype=np.int64)
    starts = starts*(starts+1)//2
    scores = np.full((len(query_ids),heads),zero.value,dtype=np.float64)
    product = np.empty_like(scores)
    try:
        with np.errstate(over='raise',invalid='raise',divide='raise',under='ignore'):
            for coordinate in range(head_width):
                np.multiply(query[query_ids,:,coordinate],key[key_ids,:,coordinate],out=product)
                np.add(scores,product,out=scores)
            np.divide(scores,divisor.value,out=scores)
            # Strict > preserves the first maximum, including signed-zero ties.
            maximum = scores[starts].copy()
            for k in range(1,tokens):
                candidate = scores[starts[k:]+k]
                np.copyto(maximum[k:],candidate,where=candidate > maximum[k:])
            shifted = np.empty_like(scores)
            np.add(scores,np.negative(maximum[query_ids]),out=shifted)
            terms = batch_rounded_exp(shifted)
            if not np.all(np.isfinite(terms)):
                raise FiniteTargetError('nonfinite certified decoder intermediate')
            denominator = np.full((tokens,heads),zero.value,dtype=np.float64)
            for k in range(tokens):
                np.add(denominator[k:],terms[starts[k:]+k],out=denominator[k:])
            probabilities = np.empty_like(terms)
            np.divide(terms,denominator[query_ids],out=probabilities)
            output = np.full((tokens,heads,head_width),zero.value,dtype=np.float64)
            weighted = np.empty_like(output)
            for k in range(tokens):
                np.multiply(probabilities[starts[k:]+k,:,None],value[k],out=weighted[k:])
                np.add(output[k:],weighted[k:],out=output[k:])
    except FloatingPointError as exc:
        raise FiniteTargetError('nonfinite certified decoder intermediate') from exc
    if not np.all(np.isfinite(output)):
        raise FiniteTargetError('nonfinite certified decoder intermediate')
    return tuple(tuple(_Finite(float(x)) for x in row) for row in output.reshape(tokens,width))
