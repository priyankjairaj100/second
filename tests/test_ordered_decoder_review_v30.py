"""Independent numerical contract fixtures; no model-scale empirical runs."""
from fractions import Fraction as Q
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from src.certified_transformer import CertifiedDecoder
from src.finite_primitives import _BACKEND, primitive_scope, rounded
from src.ordered_attention_v30 import batch_rounded_primitive
from src.ordered_finite_decoder_v30 import OrderedFiniteDecoder
from src.transformer_backend import FiniteTargetError
from tests.test_transformer_backend import decoder_fixture


def settings(context):
    return tuple(getattr(context, name) for name in (
        'precision', 'round', 'emin', 'emax', 'subnormalize', 'trap_underflow',
        'trap_overflow', 'trap_inexact', 'trap_invalid', 'trap_erange', 'trap_divzero',
        'allow_complex'))


class OrderedDecoderReviewTests(unittest.TestCase):
    def test_exp_adjacent_overflow_and_zero_rounding_inputs(self):
        upper, lower = 709.782712893384, -745.1332191019411
        values = np.array([np.nextafter(upper, -np.inf), upper,
                           np.nextafter(upper, np.inf), np.nextafter(lower, -np.inf),
                           lower, np.nextafter(lower, np.inf)])
        with primitive_scope('mpfr_enclosure'):
            expected = np.array([rounded('exp', float(x)) for x in values])
            actual = batch_rounded_primitive('exp', values, chunk_size=1)
        np.testing.assert_array_equal(actual.view(np.uint64), expected.view(np.uint64))
        self.assertTrue(np.isinf(expected[2]))
        self.assertEqual(expected[3], 0.)
        self.assertEqual(expected[4], np.nextafter(0., 1.))

    def test_noncontiguous_arrays_and_hostile_context_for_all_primitives(self):
        import gmpy2 as g
        tiny = np.nextafter(0., 1.)
        for name in ('exp', 'sqrt', 'tanh', 'erf'):
            values = np.array([[0., -0., tiny, .125], [1., 2., 20., 1024.]])
            if name != 'sqrt':
                values[1] *= -1.
            values = values.T[:, ::-1]
            self.assertFalse(values.flags.c_contiguous)
            with primitive_scope('mpfr_enclosure'):
                expected = np.array([rounded(name, float(x)) for x in values.flat]).reshape(values.shape)
                with g.context(precision=3, round=g.RoundDown, emin=-3, emax=3,
                               trap_underflow=True, trap_overflow=True, trap_inexact=True):
                    before = settings(g.get_context())
                    actual = batch_rounded_primitive(name, values, chunk_size=3)
                    self.assertEqual(before, settings(g.get_context()))
            np.testing.assert_array_equal(actual.view(np.uint64), expected.view(np.uint64))

    def test_fallback_exception_restores_both_contexts(self):
        import gmpy2 as g
        with primitive_scope('rational'):
            with g.context(precision=7, round=g.RoundUp, emin=-7, emax=7):
                before = settings(g.get_context())
                with self.assertRaisesRegex(RuntimeError, 'deliberate unresolved primitive'):
                    with primitive_scope('mpfr_enclosure'):
                        with patch('src.ordered_attention_v30._round_mpfr_endpoint', side_effect=[0., 1.]), \
                             patch('src.ordered_attention_v30.primitives.rounded',
                                   side_effect=RuntimeError('deliberate unresolved primitive')):
                            batch_rounded_primitive('tanh', np.array([.125]))
                self.assertEqual(settings(g.get_context()), before)
                self.assertEqual(_BACKEND.get(), 'rational')

    def test_generator_matches_independent_restarts_after_each_installed_stage(self):
        base = decoder_fixture(block_count=2, head_count=2)
        reference = CertifiedDecoder(base, primitive_backend='mpfr_enclosure')
        decoder = OrderedFiniteDecoder(base, primitive_backend='mpfr_enclosure')
        tokens, prefix = (0, 1, 2), {}
        stream = decoder.sequential_features(tokens)
        current = next(stream)
        for index, stage in enumerate(base.stage_ids):
            self.assertEqual(current[0], stage)
            expected = reference.stage_features(stage, tokens, prefix)
            expected = np.array([[float(x) for x in column] for column in expected]).T
            actual = np.array(current[1])
            np.testing.assert_array_equal(actual.view(np.uint64), expected.view(np.uint64))
            weights = tuple(tuple(Q(value) / (index + 2) for value in row)
                            for row in base.stage_weights(stage))
            prefix[stage] = weights
            if index + 1 < len(base.stage_ids):
                current = stream.send(weights)
            else:
                with self.assertRaises(StopIteration):
                    stream.send(weights)

    def test_generator_failure_and_explicit_throw_do_not_leak_scope(self):
        decoder = OrderedFiniteDecoder(decoder_fixture(), primitive_backend='mpfr_enclosure')
        with primitive_scope('rational'):
            stream = decoder.sequential_features((0, 1))
            next(stream)
            with self.assertRaises(FiniteTargetError):
                stream.send(((1.,),))
            self.assertEqual(_BACKEND.get(), 'rational')
            stream = decoder.sequential_features((0, 1))
            next(stream)
            with self.assertRaisesRegex(RuntimeError, 'deliberate stop'):
                stream.throw(RuntimeError('deliberate stop'))
            self.assertEqual(_BACKEND.get(), 'rational')

    def test_implementation_manifest_binds_current_sources_separately(self):
        base = decoder_fixture()
        old, new = CertifiedDecoder(base), OrderedFiniteDecoder(base)
        self.assertEqual(old.evaluator_id, new.evaluator_id)
        self.assertEqual(old.kernel_manifest, new.kernel_manifest)
        root = Path(__file__).resolve().parents[1] / 'src'
        manifest = new.implementation_manifest
        for name, digest in manifest['source_sha256'].items():
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), digest)
        self.assertFalse(manifest['same_resource_or_refusal_behavior_claimed'])
        self.assertFalse(manifest['global_mutation'])


if __name__ == '__main__':
    unittest.main()
