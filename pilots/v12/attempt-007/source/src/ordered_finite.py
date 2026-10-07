"""Binary64 linear map with the scalar multiply/add order preserved.

Only independent token/output coordinates are batched. Each input coordinate
has a separate NumPy multiply and add. There is no dot, BLAS, or fused call.
Certified nonlinear primitives and all proof-jet operations remain separate.
"""
from __future__ import annotations
import math


def ordered_linear(x, weights, bias):
    import numpy as np
    a = np.asarray(x, dtype=np.float64)
    w = np.asarray(weights, dtype=np.float64)
    b = np.asarray(bias, dtype=np.float64)
    if a.ndim != 2 or w.ndim != 2 or b.ndim != 1 or not a.size or not w.size:
        raise ValueError('nonempty matrices and a bias vector required')
    if a.shape[1] != w.shape[1] or b.shape != (w.shape[0],):
        raise ValueError('linear dimensions differ')
    if not all(np.isfinite(v).all() for v in (a, w, b)):
        raise ValueError('nonfinite linear input')
    tiny = np.array([float.fromhex('0x0.0000000000001p-1022')], dtype=np.float64)
    with np.errstate(under='ignore', over='raise', invalid='raise'):
        if np.multiply(tiny, 1.0)[0] != tiny[0] or np.add(tiny, 0.0)[0] != tiny[0]:
            raise ArithmeticError('vector subnormal behavior differs')
        result = np.zeros((a.shape[0], w.shape[0]), dtype=np.float64)
        product = np.empty_like(result)
        for coordinate in range(a.shape[1]):
            np.multiply(a[:, coordinate, None], w[None, :, coordinate], out=product)
            np.add(result, product, out=result)
        np.add(result, b[None, :], out=result)
    if not np.isfinite(result).all():
        raise ArithmeticError('nonfinite linear output')
    return tuple(tuple(float(v) for v in row) for row in result)


class FiniteWeights:
    """Internal marker for unwrapped weights in finite execution only."""
    def __init__(self, values):
        self.values = values

    def array(self):
        import numpy as np
        if type(self.values) is np.ndarray and self.values.dtype == np.float64:
            return self.values
        # Compact storage can expose an exact binary64 view without Fractions.
        if hasattr(self.values, 'float_array'):
            return self.values.float_array()
        return np.asarray([[float(x) for x in row] for row in self.values], dtype=np.float64)
