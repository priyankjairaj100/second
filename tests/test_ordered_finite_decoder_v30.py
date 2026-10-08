"""Exact decoder equivalence fixtures, without empirical model evaluation."""
from fractions import Fraction as Q
import struct
import unittest
from unittest.mock import patch

import numpy as np

import src.certified_transformer as original
from src.certified_transformer import CertifiedDecoder, _Finite
from src.finite_primitives import primitive_scope, rounded, _BACKEND
from src.ordered_attention_v30 import batch_rounded_primitive
from src.ordered_finite_decoder_v30 import (
    OrderedFiniteDecoder, OrderedFinitePrefix, ordered_activation, ordered_sequential_features,
)
from src.prepared_finite import PreparedFinitePrefix
from src.sequential_finite import sequential_features
from src.transformer_backend import FiniteTargetError
from tests.test_checkpoint_adapter import checkpoint_fixture
from tests.test_transformer_backend import decoder_fixture


def constant(value):
    return _Finite(float(value))


def binary(values):
    return tuple(tuple(struct.pack('>d',float(value)) for value in row) for row in values)


def scalar_activation(rows,activation):
    if activation == 'gelu':
        divisor = constant(2).sqrt()
        return tuple(tuple((constant(Q(1,2))*x)*(1+(x/divisor).erf()) for x in row) for row in rows)
    c = constant(float.fromhex('0x1.9884533d43651p-1'))
    return tuple(tuple((constant(Q(1,2))*x)*(1+(c*(x+constant(.044715)*x*x*x)).tanh())
                       for x in row) for row in rows)


class OrderedFiniteDecoderTests(unittest.TestCase):
    def test_default_rational_decoder_matches_complete_logits(self):
        base = decoder_fixture()
        self.assertEqual(binary(OrderedFiniteDecoder(base).logits((0,1))),
                         binary(CertifiedDecoder(base).logits((0,1))))

    def test_generic_batched_primitives_match_exact_reference_bits(self):
        tiny = np.nextafter(0.,1.)
        for name in ('tanh','erf','sqrt'):
            numbers = [0.,-0.,tiny,2.**-1022,.1,1.,20.,1024.,1025.]
            if name != 'sqrt':
                numbers += [-tiny,-.1,-1.,-20.,-1024.,-1025.]
            values = np.array(numbers)
            for backend in ('rational','mpfr_enclosure'):
                with primitive_scope(backend):
                    expected = np.array([rounded(name,float(value)) for value in values])
                    actual = batch_rounded_primitive(name,values,chunk_size=3)
                np.testing.assert_array_equal(actual.view(np.uint64),expected.view(np.uint64))

    def test_activations_preserve_every_scalar_operation(self):
        tiny = np.nextafter(0.,1.)
        values = np.array([[0.,-0.,tiny,-tiny,.1,-.1,.5,-.5,1.,-1.,20.,-20.]])
        rows = tuple(tuple(constant(value) for value in row) for row in values)
        for activation in ('gelu','gelu_new'):
            for backend in ('rational','mpfr_enclosure'):
                with primitive_scope(backend):
                    expected = scalar_activation(rows,activation)
                    actual = ordered_activation(rows,activation,constant)
                self.assertEqual(binary([[x.value for x in row] for row in actual]),
                                 binary([[x.value for x in row] for row in expected]))

    def test_target_identity_and_all_features_match(self):
        before = original._attention,original._execute,original._Finite.exp,original._Finite.tanh
        for activation in ('gelu','gelu_new'):
            base = checkpoint_fixture(activation)[2]
            old = CertifiedDecoder(base,primitive_backend='mpfr_enclosure')
            new = OrderedFiniteDecoder(base,primitive_backend='mpfr_enclosure')
            self.assertEqual(old.kernel_manifest,new.kernel_manifest)
            self.assertEqual(old.evaluator_id,new.evaluator_id)
            self.assertEqual(old.reference_id,new.reference_id)
            first = base.stage_ids[0]
            prefix = {first:tuple(tuple(value/2 for value in row) for row in base.stage_weights(first))}
            for installed in (None,prefix):
                for stage in base.stage_ids:
                    self.assertEqual(old.stage_features(stage,(0,1,2),installed),
                                     new.stage_features(stage,(0,1,2),installed))
                self.assertEqual(binary(old.logits((0,1,2),installed)),binary(new.logits((0,1,2),installed)))
        self.assertEqual(before,(original._attention,original._execute,original._Finite.exp,original._Finite.tanh))

    def test_multiple_blocks_heads_and_causal_prefixes_match(self):
        base = decoder_fixture(block_count=2,head_count=2)
        old = CertifiedDecoder(base,primitive_backend='mpfr_enclosure')
        new = OrderedFiniteDecoder(base,primitive_backend='mpfr_enclosure')
        for tokens in ((0,),(0,1),(0,1,2)):
            self.assertEqual(binary(old.logits(tokens)),binary(new.logits(tokens)))
        self.assertEqual(binary(new.logits((0,1))),binary(new.logits((0,1,2))[:2]))

    def test_ordered_generator_matches_reference_with_installed_matrices(self):
        base = decoder_fixture(block_count=2,head_count=2)
        old = CertifiedDecoder(base,primitive_backend='mpfr_enclosure')
        new = OrderedFiniteDecoder(base,primitive_backend='mpfr_enclosure')
        first,second = sequential_features(old,(0,1,2)),ordered_sequential_features(new,(0,1,2))
        a,b = next(first),next(second)
        for index,stage in enumerate(base.stage_ids):
            self.assertEqual(a[0],stage); self.assertEqual(b[0],stage)
            self.assertEqual(binary(a[1]),binary(b[1]))
            weights = tuple(tuple(value/Q(index+2) for value in row) for row in base.stage_weights(stage))
            if index+1 < len(base.stage_ids):
                a,b = first.send(weights),second.send(weights)
            else:
                for stream in (first,second):
                    with self.assertRaises(StopIteration):stream.send(weights)

    def test_generator_primitive_scope_does_not_leak_across_suspension(self):
        base = decoder_fixture()
        new = OrderedFiniteDecoder(base,primitive_backend='mpfr_enclosure')
        with primitive_scope('rational'):
            stream = new.sequential_features((0,1))
            stage,_ = next(stream)
            self.assertEqual(_BACKEND.get(),'rational')
            stream.send(base.stage_weights(stage))
            self.assertEqual(_BACKEND.get(),'rational')
            stream.close()
            self.assertEqual(_BACKEND.get(),'rational')

    def test_prepared_prefix_matches_reference_and_is_immutable(self):
        base = checkpoint_fixture()[2]
        old = CertifiedDecoder(base,primitive_backend='mpfr_enclosure')
        new = OrderedFiniteDecoder(base,primitive_backend='mpfr_enclosure')
        stage = base.stage_ids[0]
        prefix = {stage:base.stage_weights(stage)}
        expected = PreparedFinitePrefix(old,prefix)
        actual = new.prepare_prefix(prefix)
        prefix.clear()
        self.assertEqual(binary(actual.logits((0,1,2))),binary(expected.logits((0,1,2))))
        with self.assertRaises(AttributeError):actual.decoder=old
        with self.assertRaises(TypeError):actual.installed[stage]=()

    def test_implementation_manifest_is_separate_and_immutable(self):
        base = decoder_fixture()
        new = OrderedFiniteDecoder(base,primitive_backend='mpfr_enclosure')
        implementation = new.implementation_manifest
        self.assertFalse(implementation['global_mutation'])
        self.assertIn('ordered_attention_v30.py',implementation['source_sha256'])
        implementation['source_sha256'].clear()
        self.assertTrue(new.implementation_manifest['source_sha256'])
        with self.assertRaises(AttributeError):new.base=base

    def test_finite_refusal_and_api_validation(self):
        huge = ((constant(1e200),),)
        with primitive_scope('mpfr_enclosure'):
            for operation in (lambda:scalar_activation(huge,'gelu_new'),
                              lambda:ordered_activation(huge,'gelu_new',constant)):
                with self.assertRaises(FiniteTargetError):operation()
            with self.assertRaises(ValueError):batch_rounded_primitive('sqrt',np.array([-1.]))
        with self.assertRaises(ValueError):batch_rounded_primitive('unknown',np.array([1.]))
        old = CertifiedDecoder(decoder_fixture(),primitive_backend='mpfr_enclosure')
        with self.assertRaises(TypeError):next(ordered_sequential_features(old,(0,)))
        with self.assertRaises(TypeError):OrderedFinitePrefix(old)
        new = OrderedFiniteDecoder(old.base,primitive_backend='mpfr_enclosure')
        with self.assertRaises(ValueError):new.prepare_prefix({'unknown':()})
        with patch('src.ordered_finite_decoder_v30._check_runtime',side_effect=RuntimeError('unsupported')):
            with self.assertRaises(RuntimeError):new.logits((0,))


if __name__ == '__main__':
    unittest.main()
