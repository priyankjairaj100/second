"""Software fixtures only. These tests provide no empirical speed evidence."""
from fractions import Fraction as Q
import unittest
from unittest.mock import patch

import numpy as np

from src.dyadic_row_quantizer import dyadic_row_scales, quantize_dyadic_rows
from src.exact_core import sequential_oracle
from src.low_rank_certified import LowRankUnresolved
from src.native_ball_quantizer import (
    _coefficient_radii, _underflow_bounds, build_native_kernel,
    native_quantize_dyadic_rows,
)


class NativeBallTests(unittest.TestCase):
    def compare(self, weights, features, **options):
        options = dict(ridge=Q(1, 100), normalization=8,
                       max_exact_coordinates=weights.shape[1]) | options
        got = native_quantize_dyadic_rows(weights, features, **options)
        z = [[Q.from_float(float(x)) for x in row] for row in features]
        metric = [[(options['ridge'] if i == j else Q(0)) +
                   sum((a*b for a, b in zip(z[i], z[j])), Q(0)) / options['normalization']
                   for j in range(len(z))] for i in range(len(z))]
        bits = options.get('bits', 4)
        half = 1 << (bits - 1)
        for row, scale in enumerate(dyadic_row_scales(weights, bits)):
            grid = tuple(k * Q.from_float(scale) for k in range(-half, half))
            w = [Q.from_float(float(x)) for x in weights[row]]
            expected = sequential_oracle([w], metric, [grid] * len(w)).codes[0]
            self.assertEqual(tuple(Q.from_float(float(x)) for x in got.codes[row]), expected)
        self.assertFalse(got.codes.flags.writeable)
        self.assertEqual(got.native_certified_rows + got.fallback_rows, len(weights))
        self.assertEqual(got.interval_decisions + got.exact_decisions, weights.size)
        self.assertGreaterEqual(got.native_attempted_decisions, got.native_prefix_certified_decisions)
        self.assertLessEqual(got.native_attempted_decisions, weights.size)
        return got

    def test_dense_fraction_oracle_and_candidates(self):
        rng = np.random.default_rng(1701)
        for bits in (2, 4, 8):
            for width, rank in ((1, 0), (5, 0), (5, 3), (3, 5), (9, 2)):
                weights = rng.integers(-20, 21, (3, width)).astype(np.float64) / 16
                features = rng.integers(-5, 6, (width, rank)).astype(np.float64) / 8
                base = self.compare(weights, features, bits=bits)
                warm = self.compare(weights, features, bits=bits, candidate=base.codes)
                self.assertEqual(warm.candidate_source, 'supplied')
                self.assertGreater(warm.candidate_checks, 0)
                self.compare(weights, features, bits=bits, candidate=np.zeros_like(weights))

    def test_boundary_ties_and_subnormal_fallback(self):
        tiny = 2.**-1074
        weights = np.array([[2.625, -3., .1875, -.1875, .5625],
                            [0., tiny, -tiny, 2*tiny, 0.]])
        result = self.compare(weights, np.empty((5, 0)))
        self.assertGreater(result.fallback_rows, 0)
        np.testing.assert_array_equal(result.codes[0], [2.625, -3., 0., -.375, .375])
        np.testing.assert_array_equal(result.codes[1], [0., 0., -2*tiny, 2*tiny, 0.])

    def test_shared_exact_limits_and_ill_conditioned_features(self):
        features = np.array([[1e6, 1.], [-1e6, 1.], [1e6, 2.], [0., 0.]])
        weights = np.array([[.2, .7, -.3, .5], [.1, .2, .3, .4]])
        got = self.compare(weights, features, normalization=1, max_refinement_coordinates=0)
        self.assertGreater(got.exact_decisions, 0)
        self.assertEqual(len(set(got.exact_coordinates)), len(got.exact_coordinates))
        with self.assertRaises(LowRankUnresolved):
            native_quantize_dyadic_rows(weights, features, ridge=Q(1, 100),
                max_exact_coordinates=0, max_refinement_coordinates=0)

    def test_coefficient_square_root_is_exactly_enclosed(self):
        values = np.array([0., 2.**-1074, 2.**-1022, .1, 1., 1e200])
        for value, radius in zip(values, _coefficient_radii(values)):
            self.assertGreaterEqual(Q.from_float(float(radius))**2, Q.from_float(float(value)))

    def test_accumulator_bound_fraction_check(self):
        tiny = 2.**-1074
        weights = [1., 1e100, -1e100, tiny, -tiny, .1, -.1, 3., -2.]
        proposed = [0., 0., 0., 0., 0., .2, .2, -1., -1.]
        feature = [1., .1, .1, 1e100, -1e100, tiny, 1., -1., .25]
        z = np.array(feature)[:, None]
        umax, _ = _underflow_bounds(z, np.zeros_like(z))
        exact, s, a = Q(0), 0., 0.
        for i, (w, q, x) in enumerate(zip(weights, proposed, feature)):
            factor = Q(2*(i+6), 2**53)
            bound = factor * Q.from_float(a) + Q.from_float(float(umax[i]))
            self.assertLessEqual(abs(exact-Q.from_float(s)), bound)
            difference = w - q
            product = x * difference
            s = s + product
            a = a + abs(product)
            exact += Q.from_float(x) * (Q.from_float(w)-Q.from_float(q))

    def test_error_constants_cover_full_supported_dimension(self):
        unit = Q(1, 2**53)
        for width in (0, 1, 2, 16, 1024, 2**20):
            gamma = width * unit / (1-width*unit)
            self.assertLessEqual((gamma+6*unit)/(1-width*unit), 2*(width+6)*unit)
            self.assertLessEqual(2*gamma+4*unit, 4*(width+3)*unit)
            self.assertLessEqual(4*width*Q(1, 2**1074), Q(1, 2**1000))

    def test_accumulator_bounds_across_cancellation_and_exponents(self):
        rng = np.random.default_rng(1702)
        for exponent in (-1000, -500, -10, 0, 400):
            weights = np.ldexp(rng.integers(-20, 21, 25).astype(np.float64), exponent)
            proposed = np.roll(weights, 1)
            feature = np.ldexp(rng.integers(-4, 5, 25).astype(np.float64), -max(exponent, 0)//2)
            z = feature[:, None]
            umax, _ = _underflow_bounds(z, np.zeros_like(z))
            exact, s, a = Q(0), 0., 0.
            for i, (w, q, x) in enumerate(zip(weights, proposed, feature)):
                bound = Q(2*(i+6), 2**53)*Q.from_float(a)+Q.from_float(float(umax[i]))
                self.assertLessEqual(abs(exact-Q.from_float(s)), bound)
                product = float(x) * (float(w)-float(q))
                s, a = s+product, a+abs(product)
                exact += Q.from_float(float(x))*(Q.from_float(float(w))-Q.from_float(float(q)))

    def test_native_acceptance_matches_reference_without_candidate(self):
        weights = np.array([[.12, .3, -.47], [.71, -.54, .21]])
        features = np.array([[.2, .5], [-.4, .2], [.1, -.3]])
        result = self.compare(weights, features)
        self.assertEqual(result.fallback_rows, 0)
        self.assertEqual(result.candidate_checks, 0)
        expected = quantize_dyadic_rows(weights, features, ridge=Q(1, 100), normalization=8)
        np.testing.assert_array_equal(result.codes, expected.codes)

    def test_invalid_inputs_and_runtime_fail_closed(self):
        weights, features = np.array([[.1, -.3]]), np.ones((2, 1))
        for candidate in (np.ones((2, 1)), np.full((1, 2), np.nan), np.full((1, 2), .1234567)):
            with self.assertRaises(ValueError):
                native_quantize_dyadic_rows(weights, features, candidate=candidate, ridge=1)
        for options in ({'max_exact_rank':-1}, {'max_refinement_coordinates':True}):
            with self.assertRaises(ValueError):
                native_quantize_dyadic_rows(weights, features, ridge=1, **options)
        with np.errstate(over='ignore', invalid='ignore'):
            with self.assertRaises(LowRankUnresolved):
                native_quantize_dyadic_rows(weights, np.full((2, 1), 1e308), ridge=1)
        with patch('src.native_ball_quantizer._NATIVE.nb_run', return_value=1):
            with self.assertRaises(LowRankUnresolved):
                native_quantize_dyadic_rows(weights, features, ridge=1)

    def test_build_provenance_and_no_cached_binary_trust(self):
        info = build_native_kernel()
        self.assertIn('-fno-fast-math', info['flags'])
        self.assertIn('-ffp-contract=off', info['flags'])
        self.assertEqual(len(info['source_sha256']), 64)
        self.assertEqual(len(info['binary_sha256']), 64)
        self.assertFalse(info['compiled_now'])
        self.assertEqual(info['call_compile_elapsed_ns'], 0)


if __name__ == '__main__':
    unittest.main()
