"""Explicit identity encoding for exactly representable binary64 matrices.

The encoding changes identifiers, never numerical values. Callers must select
it explicitly and declare its version. General rational values are rejected.
"""
from fractions import Fraction
import hashlib
import json
import math


def binary64_matrix_sha256(matrix):
    import numpy as np
    from .compact_exact import CompactDyadicMatrix
    if type(matrix) is CompactDyadicMatrix:
        values=matrix.float_array()
    else:
        rows=[]
        for row in matrix:
            converted=[]
            for x in row:
                if type(x) is not int and not isinstance(x,Fraction):
                    raise TypeError('identity requires exact integers or rationals')
                f=float(x)
                if not math.isfinite(f) or Fraction.from_float(f)!=x:
                    raise ValueError('identity would change an exact parameter value')
                converted.append(0.0 if f==0 else f)
            rows.append(converted)
        values=np.asarray(rows,dtype=np.float64)
    if values.ndim!=2 or not values.size or not np.isfinite(values).all():
        raise ValueError('nonempty finite matrix required')
    h=hashlib.sha256(b'binary64-matrix-little-endian-row-major-v1\0')
    h.update(json.dumps(list(values.shape),separators=(',',':')).encode('ascii'))
    h.update(b'\0')
    # Row chunks bound copies even when the matrix is a transposed source view.
    for start in range(0,values.shape[0],64):
        h.update(values[start:start+64].astype('<f8',copy=False).tobytes(order='C'))
    return h.hexdigest()
