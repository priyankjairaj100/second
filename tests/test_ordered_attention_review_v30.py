"""Independent endpoint and finite-operation review fixtures, without model runs."""
from fractions import Fraction as Q
import struct
import unittest

import numpy as np

from src.certified_transformer import _Finite,_attention
from src.finite_primitives import primitive_scope
from src.ordered_attention_v30 import _round_mpfr_endpoint,finite_attention


def bits(value):
    return struct.pack('>d',value)


def constant(value):
    return _Finite(float(value))


class OrderedAttentionReviewTests(unittest.TestCase):
    def test_exact_endpoint_halfways_use_binary64_even_rounding(self):
        import gmpy2 as g
        tiny = float.fromhex('0x0.0000000000001p-1022')
        cases = (
            (Q(1)+Q(1,1 << 53),1.),
            (Q(1)+Q(3,1 << 53),float.fromhex('0x1.0000000000002p+0')),
            (Q(1,1 << 1075),0.),
            (Q(3,1 << 1075),2*tiny),
            (Q((1 << 53)-1,1 << 1075),float.fromhex('0x1.0000000000000p-1022')),
            (Q((1 << 1024)-(1 << 970)),float('inf')),
        )
        with g.context(precision=104,emin=-16384,emax=16384,round=g.RoundToNearest):
            endpoints = [g.mpfr(g.mpq(value.numerator,value.denominator)) for value,_ in cases]
        # Hostile ambient settings cannot change exact rational extraction.
        with g.context(precision=2,emin=-3,emax=3,round=g.RoundDown):
            for endpoint,(exact,expected) in zip(endpoints,cases):
                numerator,denominator = endpoint.as_integer_ratio()
                self.assertEqual(Q(int(numerator),int(denominator)),exact)
                self.assertEqual(bits(_round_mpfr_endpoint(endpoint)),bits(expected))

    def test_large_head_width_preserves_subnormal_score_division(self):
        tiny = np.nextafter(0.,1.)
        values = np.zeros((3,27),dtype=np.float64)
        values[:,0] = [1.,-1.,1.]
        values[:,9] = [-tiny,tiny,0.]
        values[:,18:] = [[-0.,tiny,-tiny,1.,-1.,2.,-2.,3.,-3.],
                         [tiny,-tiny,-0.,-1.,1.,-2.,2.,-3.,3.],
                         [-tiny,0.,tiny,2.,-2.,1.,-1.,0.,-0.]]
        qkv = tuple(tuple(_Finite(float(x)) for x in row) for row in values)
        with primitive_scope('mpfr_enclosure'):
            expected = _attention(qkv,9,1,constant)
            actual = finite_attention(qkv,9,1,constant)
        expected_bits = tuple(tuple(bits(value.value) for value in row) for row in expected)
        actual_bits = tuple(tuple(bits(value.value) for value in row) for row in actual)
        self.assertEqual(actual_bits,expected_bits)


if __name__ == '__main__':
    unittest.main()
