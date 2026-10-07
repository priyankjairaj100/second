"""Exact-byte schedule comparisons. These are software fixtures only."""
import math
import struct
import unittest
from fractions import Fraction
from src.certified_transformer import _Finite, _linear, _linear_scalar, Jet
from src.ordered_finite import FiniteWeights, ordered_linear
from src.transformer_backend import FiniteTargetError, _check_runtime


class OrderedFiniteTests(unittest.TestCase):
    def check(self, x, w, b):
        _check_runtime()
        scalar = _linear_scalar(tuple(tuple(_Finite(v) for v in row) for row in x),
                               tuple(tuple(_Finite(v) for v in row) for row in w),b,lambda x:_Finite(float(x)))
        fast = ordered_linear(x,w,b)
        self.assertEqual([[struct.pack('<d',z.value) for z in row] for row in scalar],
                         [[struct.pack('<d',z) for z in row] for row in fast])

    def test_cancellation_and_underflow(self):
        tiny=float.fromhex('0x0.0000000000001p-1022')
        self.check([[1e16,1.,-1e16],[-0.,tiny,-tiny]], [[1.,1.,1.],[-1.,.5,1.]], [0.,-0.])

    def test_nonfinite_intermediate_rejected(self):
        with self.assertRaises(ArithmeticError):
            ordered_linear([[1e308,-1e308]],[[2.,2.]],[0.])

    def test_dispatch_matches(self):
        result=_linear(((_Finite(0.5),_Finite(0.25)),),FiniteWeights(((Fraction(1,2),Fraction(3,4)),)),
                       (Fraction(1,8),),lambda x:_Finite(float(x)))
        self.assertEqual(result[0][0].value,0.5625)

    def test_proof_jets_rejected_by_finite_marker(self):
        with self.assertRaises(TypeError):
            _linear(((Jet.constant(Fraction(1),0,96),),),FiniteWeights(((1.,),)),(0.,),lambda x:_Finite(float(x)))

    def test_dimension_checks(self):
        with self.assertRaises(ValueError):
            ordered_linear([[1.]],[[1.,2.]],[0.])


if __name__=='__main__':unittest.main()
