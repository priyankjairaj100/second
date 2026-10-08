"""Finite-program equivalence fixtures, not empirical research datasets."""
import struct
import unittest
from unittest.mock import patch

import numpy as np

from src.certified_transformer import _Finite, _attention
from src.finite_primitives import primitive_scope, rounded
from src.ordered_attention_v30 import batch_rounded_exp, finite_attention
from src.transformer_backend import FiniteTargetError


def constant(value):
    return _Finite(float(value))


def rows(values):
    return tuple(tuple(_Finite(float(value)) for value in row) for row in values)


def encodings(values):
    return tuple(tuple(struct.pack('>d',float(value.value)) for value in row) for row in values)


class OrderedAttentionTests(unittest.TestCase):
    def compare(self,values,width,heads,backend='mpfr_enclosure'):
        inputs = rows(values)
        before = encodings(inputs)
        with primitive_scope(backend):
            expected = _attention(inputs,width,heads,constant)
            actual = finite_attention(inputs,width,heads,constant)
        self.assertEqual(encodings(actual),encodings(expected))
        self.assertEqual(encodings(inputs),before)
        return actual

    def test_independent_head_query_and_key_batches_match_scalar_bits(self):
        generator = np.random.default_rng(3107)
        for tokens,width,heads in ((1,1,1),(2,4,2),(3,6,3),(7,8,2),(5,4,1)):
            self.compare(generator.uniform(-2.,2.,size=(tokens,3*width)),width,heads)

    def test_rational_primitive_backend_keeps_reference_values(self):
        values = np.array([[.25,-.5,.5,.25,1.,-.5],[-.125,.75,-.5,.25,2.,.125]])
        self.compare(values,2,1,backend='rational')

    def test_signed_zeros_subnormals_and_cancellation_match_bits(self):
        tiny = np.nextafter(0.,1.)
        values = np.array([[0.,-0.,-0.,0.,-0.,-tiny],
                           [-0.,tiny,0.,-tiny,tiny,-0.],
                           [tiny,-tiny,-tiny,tiny,-tiny,tiny]])
        self.compare(values,2,1)
        cancellation = np.array([[2.**50,1.,2.**-50,-1.,1e100,-1e100],
                                  [-2.**50,1.,-2.**-50,-1.,-1e100,1e100],
                                  [1.,-1.,1.,1.,1.,-1.]])
        self.compare(cancellation,2,1)

    def test_future_rows_cannot_change_any_earlier_output(self):
        generator = np.random.default_rng(731)
        values = generator.uniform(-1.,1.,size=(5,12))
        changed = values.copy(); changed[3:] = generator.uniform(-4.,4.,size=(2,12))
        first = self.compare(values,4,2)
        second = self.compare(changed,4,2)
        self.assertEqual(encodings(first[:3]),encodings(second[:3]))

    def test_unused_future_score_can_overflow_without_affecting_execution(self):
        # q0*k1 would overflow, but that future pair is absent from causal attention.
        values = np.array([[1e308,0.,.25],[0.,1e308,-.5]])
        self.compare(values,1,1)

    def test_nonfinite_used_score_or_shift_refuses_like_scalar_reference(self):
        fixtures = (np.array([[1e308,1e308,1.]]),
                    np.array([[0.,1e308,1.],[1.,-1e308,1.]]))
        for values in fixtures:
            for function in (_attention,finite_attention):
                with primitive_scope('mpfr_enclosure'):
                    with self.assertRaises(FiniteTargetError):
                        function(rows(values),1,1,constant)

    def test_batched_mpfr_exp_matches_exact_existing_rounding(self):
        tiny = np.nextafter(0.,1.)
        values = np.array([0.,-0.,tiny,-tiny,1.,-1.,-.1,-20.,-96.,-700.,-744.,-745.,-1000.,709.,1024.])
        with primitive_scope('mpfr_enclosure'):
            expected = np.array([rounded('exp',float(value)) for value in values])
            for chunk in (1,4,4096):
                actual = batch_rounded_exp(values,chunk_size=chunk)
                np.testing.assert_array_equal(actual.view(np.uint64),expected.view(np.uint64))

    def test_ambiguous_mpfr_endpoint_conversion_uses_unchanged_fallback(self):
        with primitive_scope('mpfr_enclosure'):
            with patch('src.ordered_attention_v30._round_mpfr_endpoint',side_effect=[1.,2.]), \
                 patch('src.ordered_attention_v30.primitives.rounded',wraps=rounded) as fallback:
                actual = batch_rounded_exp(np.array([.1]))
            self.assertEqual(fallback.call_count,1)
            self.assertEqual(actual[0],rounded('exp',.1))

    def test_mpfr_context_is_explicit_and_restored(self):
        import gmpy2 as g
        with g.context(precision=7,round=g.RoundUp,emin=-7,emax=7):
            before = repr(g.get_context())
            with primitive_scope('mpfr_enclosure'):
                actual = batch_rounded_exp(np.array([.1,-20.,1.]))
                expected = np.array([rounded('exp',value) for value in (.1,-20.,1.)])
            np.testing.assert_array_equal(actual.view(np.uint64),expected.view(np.uint64))
            # Status flags can change in user computations, so compare settings explicitly.
            self.assertEqual(g.get_context().precision,7)
            self.assertEqual(g.get_context().round,g.RoundUp)
            self.assertEqual(g.get_context().emin,-7)
            self.assertEqual(g.get_context().emax,7)

    def test_empty_input_shape_contract_and_runtime_guards(self):
        with primitive_scope('mpfr_enclosure'):
            self.assertEqual(finite_attention((),4,2,constant),())
        for width,heads in ((0,1),(2,0),(3,2),(True,1)):
            with self.assertRaises(ValueError):
                finite_attention((),width,heads,constant)
        with self.assertRaises(ValueError):
            finite_attention(rows([[0.]]),2,1,constant)
        with self.assertRaises(TypeError):
            finite_attention(((0.,0.,0.),),1,1,constant)
        with patch('src.ordered_attention_v30._check_runtime',side_effect=RuntimeError('unsupported runtime')):
            with self.assertRaises(RuntimeError):
                finite_attention(rows([[0.,0.,0.]]),1,1,constant)
        with self.assertRaises(FiniteTargetError):
            batch_rounded_exp(np.array([np.inf]))
        with self.assertRaises(TypeError):
            batch_rounded_exp(np.array([1.],dtype=np.float32))
        for chunk in (0,-1,True,1.5):
            with self.assertRaises(ValueError):
                batch_rounded_exp(np.array([1.]),chunk_size=chunk)


if __name__ == '__main__':
    unittest.main()
