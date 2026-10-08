"""Exact rational software checks for uncertain-feature native balls."""
import hashlib
import itertools
from fractions import Fraction as Q
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

import src.ball_box_certificate_v27 as module
from src.dyadic_row_quantizer import _grid_arrays, dyadic_row_scales
from src.token_box_certificate import TokenBoxUnresolved
from tests.test_native_box_v26 import corners, oracle, rational


class BallBoxTests(unittest.TestCase):
    def setUp(self):
        self.weights = np.array([[2.6, .21, -.11], [-.3, 1.7, .06]])
        self.features = np.array([[.9, -.3], [.4, .7], [-.5, .2]])

    def test_prefix_bound_covers_every_corner_and_grid_endpoint_sequence(self):
        weights = np.array([[2.6, .21], [-.3, 1.7]])
        lower = np.array([[.9, -.3], [.4, .7]])
        upper = lower + .001
        grid, _ = _grid_arrays(dyadic_row_scales(weights), 4)
        center, radius, prefix, discrepancy = module._feature_uncertainty_bounds(weights, lower, upper, grid)
        for i, k in itertools.product(range(2), repeat=2):
            self.assertLessEqual(max(abs(rational(lower[i,k])-rational(center[i,k])),
                                     abs(rational(upper[i,k])-rational(center[i,k]))), rational(radius[i,k]))
        for row in range(2):
            for i, q in itertools.product(range(2), grid[row]):
                self.assertLessEqual(abs(rational(weights[row,i])-rational(q)), rational(discrepancy[i]))
            for features, indices in itertools.product(corners(lower, upper), itertools.product((0, -1), repeat=2)):
                q = grid[row, indices]
                for i, k in itertools.product(range(2), repeat=2):
                    exact = sum(((rational(weights[row,h])-rational(q[h])) *
                                 (rational(features[h,k])-rational(center[h,k])) for h in range(i)), Q(0))
                    self.assertLessEqual(abs(exact), rational(prefix[i]))

    def test_center_and_radius_cover_subnormals_and_wide_finite_boxes(self):
        tiny = np.nextafter(0., 1.)
        weights = np.zeros((1, 4))
        lower = np.array([[-tiny], [tiny], [-2*tiny], [-1e308]])
        upper = np.array([[tiny], [2*tiny], [tiny], [1e308]])
        grid, _ = _grid_arrays(dyadic_row_scales(weights), 4)
        center, radius, prefix, _ = module._feature_uncertainty_bounds(weights, lower, upper, grid)
        self.assertTrue(np.all(lower <= center) and np.all(center <= upper))
        for a, b, c, r in zip(lower.flat, upper.flat, center.flat, radius.flat):
            self.assertLessEqual(abs(rational(a)-rational(c)), rational(r))
            self.assertLessEqual(abs(rational(b)-rational(c)), rational(r))
        self.assertGreater(prefix[1], 0.)

    def test_augmented_ball_contains_exact_uncertain_accumulators(self):
        tiny = np.nextafter(0., 1.)
        weights = np.array([[1e10, -1e10, .1, -.1]])
        lower = np.array([[1e-10], [-1e-10], [tiny], [1.]])
        upper = lower + np.array([[1e-18], [1e-18], [tiny], [1e-8]])
        grid, _ = _grid_arrays(dyadic_row_scales(weights), 4)
        center, _, error, _ = module._feature_uncertainty_bounds(weights, lower, upper, grid)
        augmented, _ = module._augmented_underflow_bounds(center, np.zeros_like(center), error)
        for features, indices in itertools.product(corners(lower, upper), itertools.product((0, -1), repeat=4)):
            q = grid[0, indices]
            exact, rounded, absolute = Q(0), 0., 0.
            for i in range(4):
                bound = Q(2*(i+6), 2**53)*rational(absolute) + rational(augmented[i])
                self.assertLessEqual(abs(exact-rational(rounded)), bound)
                product = float(center[i, 0]) * (float(weights[0, i])-float(q[i]))
                rounded = rounded + product
                absolute = absolute + abs(product)
                exact += rational(features[i,0]) * (rational(weights[0,i])-rational(q[i]))

    def test_accepted_box_matches_all_exact_corners_and_interiors(self):
        lower, upper = self.features, self.features + 1e-8
        with patch.object(module.ball, 'native_ball_quantize_dyadic_rows',
                          side_effect=AssertionError('uncertain boxes cannot use point fallback')):
            result = module.certify_ball_dyadic_box(self.weights, lower, upper,
                ridge=10, normalization=3, allow_python_fallback=False)
        self.assertEqual(len(result.native_passes), 1)
        self.assertEqual(result.native_passes[0]['policy'], 'ridge')
        self.assertFalse(result.python_universal_fallback)
        self.assertEqual(result.native_certified_decisions, self.weights.size)
        for features in corners(lower, upper):
            np.testing.assert_array_equal(result.codes, oracle(self.weights, features))
        for alpha in (.125, .5, .875):
            np.testing.assert_array_equal(result.codes, oracle(self.weights, lower+alpha*(upper-lower)))
        self.assertGreater(result.max_feature_accumulator_error, 0.)
        with self.assertRaises(ValueError):
            result.codes.flags.writeable = True

    def test_preconditioned_radius_retains_exact_target(self):
        weights, lower = np.array([[.21, 2.6]]), np.ones((2, 1))
        upper = lower + 1e-6
        options = dict(ridge=Q(1, 1000000), normalization=1)
        result = module.certify_ball_dyadic_box(weights, lower, upper,
            allow_python_fallback=False, **options)
        self.assertEqual(len(result.native_passes), 2)
        self.assertGreater(result.native_passes[0]['failed_rows'], 0)
        self.assertEqual(result.native_passes[1]['failed_rows'], 0)
        for features in corners(lower, upper):
            np.testing.assert_array_equal(result.codes, oracle(weights, features, **options))

    def test_exact_ties_use_universal_fallback_and_keep_lower_codes(self):
        weights = np.array([[.5, 7.], [-.5, 7.]])
        lower, upper = np.array([[0.], [1.]]), np.array([[0.], [1.+1e-8]])
        with patch.object(module.ball, 'native_ball_quantize_dyadic_rows',
                          side_effect=AssertionError('uncertain boxes cannot use point fallback')):
            result = module.certify_ball_dyadic_box(weights, lower, upper, ridge=10, normalization=3)
        self.assertTrue(result.python_universal_fallback)
        self.assertGreater(result.fallback_elapsed_ns, 0)
        np.testing.assert_array_equal(result.codes[:, 0], [0., -1.])
        for features in corners(lower, upper):
            np.testing.assert_array_equal(result.codes, oracle(weights, features))

    def test_actual_ambiguity_rejects_and_records_all_failed_work(self):
        weights, lower, upper = np.array([[.21, 2.6]]), np.ones((2, 1)), np.array([[4.], [1.]])
        options = dict(ridge=Q(1, 1000000), normalization=1)
        self.assertFalse(np.array_equal(oracle(weights, lower, **options), oracle(weights, upper, **options)))
        with self.assertRaises(TokenBoxUnresolved) as raised:
            module.certify_ball_dyadic_box(weights, lower, upper, **options)
        receipt = raised.exception.native_diagnostics
        self.assertEqual(len(receipt['passes']), 2)
        self.assertGreater(receipt['fallback_elapsed_ns'], 0)
        self.assertGreater(receipt['total_elapsed_ns'], receipt['fallback_elapsed_ns'])

    def test_singletons_empty_rank_subnormals_and_alignment(self):
        def unaligned(x):
            result = np.ndarray(x.shape, dtype=np.float64, buffer=bytearray(x.nbytes+1), offset=1)
            result[:] = x
            result.flags.writeable = False
            return result
        for features in (self.features, np.empty((3, 0))):
            result = module.certify_ball_dyadic_box(unaligned(self.weights), unaligned(features),
                unaligned(features), ridge=10, normalization=3)
            self.assertEqual(result.backend, 'native_singleton_point')
            np.testing.assert_array_equal(result.codes, oracle(self.weights, features))
        result = module.certify_ball_dyadic_box(unaligned(self.weights), unaligned(self.features),
            unaligned(self.features+1e-8), ridge=10, normalization=3, allow_python_fallback=False)
        np.testing.assert_array_equal(result.codes, oracle(self.weights, self.features))
        tiny = np.nextafter(0., 1.)
        weights, lower, upper = np.zeros((1, 2)), np.full((2, 1), tiny), np.full((2, 1), 2*tiny)
        result = module.certify_ball_dyadic_box(weights, lower, upper, ridge=10, normalization=3)
        self.assertTrue(result.python_universal_fallback)
        np.testing.assert_array_equal(result.codes, weights)

    def test_validation_dimension_runtime_and_source_bindings(self):
        upper = self.features + 1e-8
        for name in ('weights', 'lower', 'upper', 'candidate_codes'):
            kwargs = dict(weights=self.weights.copy(), lower=self.features.copy(), upper=upper.copy())
            if name == 'candidate_codes':
                kwargs[name] = self.weights.copy()
            kwargs[name].flat[0] = np.nan
            with self.assertRaises(ValueError):
                module.certify_ball_dyadic_box(**kwargs, ridge=10)
        # A strided broadcast supplies the shape guard without a large allocation.
        huge = np.broadcast_to(np.array([[1.]]), (1, 2**20+1))
        with self.assertRaises(ValueError):
            module.certify_ball_dyadic_box(np.ones((1, 1)), huge, huge, ridge=1)
        with patch.object(module, '_check_runtime', side_effect=RuntimeError('unsupported')):
            with self.assertRaises(RuntimeError):
                module.certify_ball_dyadic_box(self.weights, self.features, upper, ridge=10)
        result = module.certify_ball_dyadic_box(self.weights, self.features, upper,
            ridge=10, normalization=3, candidate_codes=oracle(self.weights, self.features))
        self.assertTrue(result.candidate_checked)
        self.assertEqual(result.native_source_sha256, hashlib.sha256(module.ball._C_SOURCE.encode()).hexdigest())
        self.assertEqual(result.wrapper_source_sha256, hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest())
        self.assertGreaterEqual(result.total_elapsed_ns, result.feature_bounds_elapsed_ns +
            result.coefficient_elapsed_ns + result.ball_bounds_elapsed_ns + result.native_elapsed_ns +
            result.fallback_elapsed_ns + result.compile_elapsed_ns)
        with self.assertRaises(TokenBoxUnresolved):
            module.certify_ball_dyadic_box(self.weights, self.features, upper,
                ridge=10, normalization=3, candidate_codes=np.zeros_like(self.weights))


if __name__ == '__main__':
    unittest.main()
