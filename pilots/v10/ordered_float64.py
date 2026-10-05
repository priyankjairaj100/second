"""Diagnostic prototype for the same multiply-then-add binary64 schedule.

Batch independent output entries. Never reduce the coordinate axis in NumPy.
This prototype does not change the production decoder or its certificate.
"""
import math
import numpy as np


def ordered_linear(x, weight, bias):
    a=np.asarray(x,dtype=np.float64)
    w=np.asarray(weight,dtype=np.float64)
    b=np.asarray(bias,dtype=np.float64)
    if a.ndim!=2 or w.ndim!=2 or b.ndim!=1 or not a.size or not w.size:
        raise ValueError('nonempty matrices and a bias vector required')
    if a.shape[1]!=w.shape[1] or b.shape!=(w.shape[0],):
        raise ValueError('linear dimensions differ')
    if not all(np.isfinite(v).all() for v in (a,w,b)):
        raise ValueError('nonfinite linear input')
    # Verify subnormal handling on the selected ufunc path.
    tiny=np.array([float.fromhex('0x0.0000000000001p-1022')],dtype=np.float64)
    with np.errstate(under='ignore',over='raise',invalid='raise'):
        if np.multiply(tiny,1.0)[0]!=tiny[0] or np.add(tiny,0.0)[0]!=tiny[0]:
            raise ArithmeticError('vector subnormal behavior differs')
        out=np.zeros((a.shape[0],w.shape[0]),dtype=np.float64)
        product=np.empty_like(out)
        for coordinate in range(a.shape[1]):
            np.multiply(a[:,coordinate,None],w[None,:,coordinate],out=product)
            np.add(out,product,out=out)
        np.add(out,b[None,:],out=out)
    if not np.isfinite(out).all():
        raise ArithmeticError('nonfinite linear output')
    return tuple(tuple(float(v) for v in row) for row in out)


def finite_linear(x, weights, bias, constant):
    from src.certified_transformer import _Finite
    if any(type(z) is not _Finite for row in x for z in row):
        raise TypeError('prototype accepts finite evaluation only, never proof jets')
    if any(type(z) is not _Finite for row in weights for z in row):
        raise TypeError('prototype requires finite weights')
    values=ordered_linear([[z.value for z in row] for row in x],
        [[z.value for z in row] for row in weights], [float(z) for z in bias])
    return tuple(tuple(_Finite(z) for z in row) for row in values)
