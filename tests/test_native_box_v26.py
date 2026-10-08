"""Exact rational software fixtures, never empirical evidence."""
import ctypes
import hashlib
import itertools
from fractions import Fraction as Q
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

import src.native_box_certificate as native
from src.dyadic_row_quantizer import dyadic_row_scales
from src.exact_core import sequential_oracle
from src.token_box_certificate import TokenBoxUnresolved


def rational(value):
    return Q.from_float(float(value))


def oracle(weights, features, ridge=Q(10), normalization=Q(3)):
    exact = [[rational(x) for x in row] for row in features]
    metric = [[sum((x*y for x, y in zip(a, b)), Q(0))/normalization
               + (ridge if i == j else 0)
               for j, b in enumerate(exact)] for i, a in enumerate(exact)]
    rows = []
    for row, scale in zip(weights, dyadic_row_scales(weights)):
        grid = tuple(k*rational(scale) for k in range(-8, 8))
        result = sequential_oracle([[rational(x) for x in row]], metric, [grid]*weights.shape[1])
        rows.append(result.codes[0])
    return np.asarray(rows, dtype=np.float64)


def corners(lower, upper):
    for mask in itertools.product((False, True), repeat=lower.size):
        yield np.where(np.asarray(mask).reshape(lower.shape), upper, lower)


class NativeBoxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        native.prepare_native_box()

    def setUp(self):
        self.weights = np.array([[2.6, .21, -.11], [-.3, 1.7, .06]])
        self.features = np.array([[.9, -.3], [.4, .7], [-.5, .2]])

    def test_directed_primitives_enclose_exact_corners_and_subnormals(self):
        tiny = np.nextafter(0., 1.)
        cases = [(1.1, 1.2, -.7, .3), (tiny, 2*tiny, .25, .5),
                 (-tiny, tiny, -2*tiny, tiny), (0., 0., -1., 1.),
                 (1., 1., -1., -1.), (-0., -0., 0., 0.)]
        ptr = ctypes.POINTER(ctypes.c_double)
        for case, operation in itertools.product(cases, (0, 1)):
            values, result = np.asarray(case), np.empty(2)
            status = native._NATIVE.nbc_probe(operation, values.ctypes.data_as(ptr), result.ctypes.data_as(ptr))
            self.assertEqual(status, 0)
            for a, b in itertools.product(case[:2], case[2:]):
                exact = rational(a)+rational(b) if operation == 0 else rational(a)*rational(b)
                self.assertLessEqual(rational(result[0]), exact)
                self.assertLessEqual(exact, rational(result[1]))
        values = np.array([1., 1., -1., -1.])
        result = np.empty(2)
        self.assertEqual(native._NATIVE.nbc_probe(0, values.ctypes.data_as(ptr), result.ctypes.data_as(ptr)), 0)
        np.testing.assert_array_equal(result, [0., 0.])

    def test_uncertain_box_matches_every_exact_corner_and_interior(self):
        lower, upper = self.features, self.features + 1e-8
        with patch.object(native, 'native_ball_quantize_dyadic_rows', side_effect=AssertionError('no uncertain point fallback')):
            result = native.certify_native_dyadic_box(self.weights, lower, upper,
                ridge=10, normalization=3, allow_python_fallback=False)
        for features in corners(lower, upper):
            np.testing.assert_array_equal(result.codes, oracle(self.weights, features))
        for alpha in (.125, .5, .875):
            np.testing.assert_array_equal(result.codes, oracle(self.weights, lower + alpha*(upper-lower)))
        self.assertEqual(result.native_passes[0]['policy'], 'ridge_component')
        self.assertEqual(len(result.native_passes), 1)
        self.assertEqual(result.native_certified_decisions, self.weights.size)
        self.assertFalse(result.python_universal_fallback)
        with self.assertRaises(ValueError):
            result.codes.flags.writeable = True

    def test_preconditioner_recovers_after_ridge_rejection(self):
        weights, lower = np.array([[.21, 2.6]]), np.ones((2, 1))
        upper = lower + 1e-6
        options = dict(ridge=Q(1, 1000000), normalization=1)
        result = native.certify_native_dyadic_box(weights, lower, upper,
            allow_python_fallback=False, **options)
        self.assertEqual(len(result.native_passes), 2)
        self.assertEqual(result.native_passes[0]['status'], 3)
        self.assertEqual(result.native_passes[1]['status'], 0)
        for features in corners(lower, upper):
            np.testing.assert_array_equal(result.codes, oracle(weights, features, **options))
        self.assertEqual(result.coefficient_elapsed_ns, sum(p['coefficient_elapsed_ns'] for p in result.native_passes))

    def test_python_universal_fallback_remains_sound_and_charged(self):
        original = native._box_coefficients
        def loose(*args):
            proposal, error = original(*args)
            return proposal, error + 1000
        with patch.object(native, '_box_coefficients', side_effect=loose), \
             patch.object(native.preconditioned, '_preconditioned_error', return_value=None):
            result = native.certify_native_dyadic_box(self.weights, self.features,
                self.features + 1e-8, ridge=10, normalization=3)
        self.assertTrue(result.python_universal_fallback)
        self.assertEqual(len(result.native_passes), 2)
        self.assertGreater(result.fallback_elapsed_ns, 0)
        np.testing.assert_array_equal(result.codes, oracle(self.weights, self.features))
        self.assertGreaterEqual(result.total_elapsed_ns, result.coefficient_elapsed_ns +
                                result.native_elapsed_ns + result.fallback_elapsed_ns + result.compile_elapsed_ns)

    def test_actual_ambiguous_box_rejects_without_point_fallback(self):
        weights, lower, upper = np.array([[.21, 2.6]]), np.ones((2, 1)), np.array([[4.], [1.]])
        options = dict(ridge=Q(1, 1000000), normalization=1)
        self.assertFalse(np.array_equal(oracle(weights, lower, **options), oracle(weights, upper, **options)))
        with patch.object(native, 'native_ball_quantize_dyadic_rows', side_effect=AssertionError('no uncertain point fallback')):
            with self.assertRaises(TokenBoxUnresolved) as raised:
                native.certify_native_dyadic_box(weights, lower, upper, **options)
        diagnostics = raised.exception.native_diagnostics
        self.assertEqual(len(diagnostics['passes']), 2)
        self.assertGreater(diagnostics['fallback_elapsed_ns'], 0)
        self.assertGreater(diagnostics['total_elapsed_ns'], diagnostics['fallback_elapsed_ns'])

    def test_lower_code_ties_remain_exact(self):
        weights = np.array([[.5, 7.], [-.5, 7.]])
        lower, upper = np.array([[0.], [1.]]), np.array([[0.], [1.+1e-8]])
        result = native.certify_native_dyadic_box(weights, lower, upper,
            ridge=10, normalization=3, allow_python_fallback=False)
        np.testing.assert_array_equal(result.codes[:, 0], [0., -1.])
        for features in corners(lower, upper):
            np.testing.assert_array_equal(result.codes, oracle(weights, features))

    def test_subnormal_box_and_exact_zero_accumulators(self):
        tiny = np.nextafter(0., 1.)
        weights = np.zeros((1, 2))
        lower, upper = np.full((2, 1), tiny), np.full((2, 1), 2*tiny)
        result = native.certify_native_dyadic_box(weights, lower, upper,
            ridge=10, normalization=3, allow_python_fallback=False)
        np.testing.assert_array_equal(result.codes, weights)
        for features in corners(lower, upper):
            np.testing.assert_array_equal(result.codes, oracle(weights, features))

    def test_singleton_and_empty_rank_use_shared_point_solver(self):
        for features in (self.features, np.empty((3, 0))):
            result = native.certify_native_dyadic_box(self.weights, features, features, ridge=10, normalization=3)
            np.testing.assert_array_equal(result.codes, oracle(self.weights, features))
            self.assertEqual(result.backend, 'native_singleton_point')
            self.assertEqual(result.uncertain_features, 0)

    def test_unaligned_readonly_and_noncontiguous_inputs(self):
        def unaligned(values):
            result = np.ndarray(values.shape, dtype=np.float64,
                                buffer=bytearray(values.nbytes + 1), offset=1)
            result[:] = values
            self.assertFalse(result.flags.aligned)
            result.flags.writeable = False
            return result
        upper = self.features + 1e-8
        for weights, lower, high in (
            (unaligned(self.weights), unaligned(self.features), unaligned(upper)),
            (self.weights[:, ::-1], self.features[::-1], upper[::-1]),
            (unaligned(self.weights), unaligned(self.features), unaligned(self.features)),
        ):
            result = native.certify_native_dyadic_box(weights, lower, high,
                ridge=10, normalization=3, allow_python_fallback=False)
            np.testing.assert_array_equal(result.codes, oracle(weights, lower))

    def test_candidates_and_validation(self):
        upper = self.features + 1e-8
        expected = oracle(self.weights, self.features)
        result = native.certify_native_dyadic_box(self.weights, self.features, upper,
            ridge=10, normalization=3, candidate_codes=expected)
        self.assertTrue(result.candidate_checked)
        with self.assertRaises(TokenBoxUnresolved):
            native.certify_native_dyadic_box(self.weights, self.features, upper,
                ridge=10, normalization=3, candidate_codes=np.zeros_like(self.weights))
        for keyword, value in [('max_exact_rank', True), ('allow_python_fallback', 1), ('ridge', 0)]:
            options = dict(ridge=10, normalization=3)
            options[keyword] = value
            with self.assertRaises(ValueError):
                native.certify_native_dyadic_box(self.weights, self.features, upper, **options)
        with self.assertRaises(ValueError):
            native.certify_native_dyadic_box(self.weights, upper, self.features, ridge=10)

    def test_nan_and_extreme_inputs_fail_closed(self):
        for name in ('weights', 'lower', 'upper', 'candidate_codes'):
            kwargs = dict(weights=self.weights.copy(), lower=self.features.copy(), upper=self.features.copy())
            if name == 'candidate_codes':
                kwargs[name] = self.weights.copy()
            kwargs[name].flat[0] = np.nan
            with self.assertRaises(ValueError):
                native.certify_native_dyadic_box(**kwargs, ridge=10)
        with self.assertRaises(TokenBoxUnresolved):
            native.certify_native_dyadic_box(self.weights,
                np.full_like(self.features, -1e100), np.full_like(self.features, 1e100), ridge=1)

    def test_runtime_and_build_bindings(self):
        with patch.object(native, '_check_runtime', side_effect=RuntimeError('unsupported')):
            with self.assertRaises(RuntimeError):
                native.certify_native_dyadic_box(self.weights, self.features, self.features, ridge=10)
        build = native.prepare_native_box()
        self.assertFalse(build['compiled_now'])
        self.assertEqual(build['call_compile_elapsed_ns'], 0)
        self.assertEqual(build['source_sha256'], hashlib.sha256(native._C_SOURCE.encode()).hexdigest())
        self.assertEqual(build['wrapper_sha256'], hashlib.sha256(Path(native.__file__).read_bytes()).hexdigest())
        self.assertEqual(build['coefficient_source_sha256'], hashlib.sha256(Path(native.preconditioned.__file__).read_bytes()).hexdigest())
        self.assertEqual(len(build['binary_sha256']), 64)
        self.assertIn('-fno-fast-math', build['flags'])
        self.assertIn('-ffp-contract=off', build['flags'])


if __name__ == '__main__':
    unittest.main()
