"""Software fixtures for certified speculative quantization, not empirical data."""
from fractions import Fraction as Q
import unittest
from unittest.mock import patch

import numpy as np

from src.dyadic_row_quantizer import dyadic_row_scales, quantize_dyadic_rows
from src.exact_core import sequential_oracle
from src.low_rank_certified import LowRankUnresolved
from src.speculative_dyadic_solver import exclusive_interval_scan, speculative_quantize_dyadic_rows


class DirectedScanTests(unittest.TestCase):
    def test_exact_prefix_containment_with_cancellation_and_padding(self):
        tiny = 2.**-1074
        for count in (0, 1, 2, 3, 5, 8, 9):
            values = np.resize(np.array([1., 1e100, -1e100, tiny, -tiny, -0., 3.]), (count, 2, 3))
            before = values.copy()
            lo, hi = exclusive_interval_scan(values, values)
            for channel in np.ndindex(values.shape[1:]):
                exact = Q(0)
                for i in range(count):
                    idx = (i,) + channel
                    self.assertLessEqual(Q.from_float(float(lo[idx])), exact)
                    self.assertGreaterEqual(Q.from_float(float(hi[idx])), exact)
                    exact += Q.from_float(float(values[idx]))
            np.testing.assert_array_equal(values, before)
            if count:
                np.testing.assert_array_equal(lo[0], 0.)
                np.testing.assert_array_equal(hi[0], 0.)

    def test_interval_inputs_and_invalid_endpoints(self):
        lo = np.array([[-2., 0.], [1., -3.], [-.25, 1.]])
        hi = np.array([[1., 0.], [2., 1.], [.75, 2.]])
        out_lo, out_hi = exclusive_interval_scan(lo, hi)
        for j in range(2):
            self.assertTrue(np.all(out_lo[:, j] <= np.r_[0., np.cumsum(lo[:-1, j])]))
            self.assertTrue(np.all(out_hi[:, j] >= np.r_[0., np.cumsum(hi[:-1, j])]))
        with self.assertRaises(ValueError):
            exclusive_interval_scan(hi, lo)
        with self.assertRaises(LowRankUnresolved):
            exclusive_interval_scan(np.array([np.nan]), np.array([np.nan]))
        with np.errstate(over="ignore"):
            with self.assertRaises(LowRankUnresolved):
                exclusive_interval_scan(np.array([1e308, 1e308]), np.array([1e308, 1e308]))


class SpeculativeDyadicTests(unittest.TestCase):
    def compare(self, weights, features, **options):
        options = dict(ridge=Q(1, 100), normalization=8, max_exact_coordinates=weights.shape[1]) | options
        got = speculative_quantize_dyadic_rows(weights, features, **options)
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
        self.assertEqual(got.speculative_certified_rows + got.sequential_fallback_rows, len(weights))
        self.assertEqual(got.interval_decisions + got.exact_decisions, weights.size)
        self.assertEqual(got.prefix_verified_decisions + got.fallback_decisions, weights.size)
        return got

    def test_fresh_supplied_candidates_and_dense_oracle(self):
        rng = np.random.default_rng(1601)
        for bits in (2, 4, 8):
            for width, rank in ((1, 0), (5, 0), (5, 3), (3, 5)):
                weights = rng.integers(-20, 21, (3, width)).astype(np.float64) / 16
                features = rng.integers(-5, 6, (width, rank)).astype(np.float64) / 8
                base = self.compare(weights, features, bits=bits, row_batch_size=2)
                exact_proposal = self.compare(weights, features, bits=bits, candidate=base.codes,
                                              max_sweeps=1, row_batch_size=1)
                self.assertEqual(exact_proposal.candidate_source, 'supplied')
                self.compare(weights, features, bits=bits, candidate=np.zeros_like(weights), max_sweeps=1)

    def test_no_sweeps_forces_reference_fallback(self):
        weights = np.array([[.1, .2, .4], [-.8, 1., .3]])
        features = np.array([[1., .2], [-1., .5], [.2, .1]])
        got = self.compare(weights, features, max_sweeps=0, row_batch_size=1)
        self.assertEqual(got.speculative_sweeps, 0)
        self.assertEqual(got.sequential_fallback_rows, 2)
        expected = quantize_dyadic_rows(weights, features, ridge=Q(1, 100), normalization=8)
        np.testing.assert_array_equal(got.codes, expected.codes)

    def test_fixed_point_accepts_without_sequential_work(self):
        weights = np.array([[2.625, -3., .2, -.2], [0., 0., 0., 0.]])
        features = np.empty((4, 0))
        got = self.compare(weights, features, max_sweeps=1)
        self.assertEqual(got.speculative_certified_rows, 2)
        self.assertEqual(got.sequential_fallback_rows, 0)
        self.assertEqual(got.fallback_elapsed_ns, 0)

    def test_partial_prefixes_seed_only_the_needed_suffixes(self):
        weights = np.array([[2.625, -3., .2, -.2, .4], [-3., 2.625, .4, .2, -.2]])
        features = np.empty((5, 0))
        reference = quantize_dyadic_rows(weights, features, ridge=Q(1, 100), normalization=8)
        candidate = reference.codes.copy()
        candidate[0, 3] = candidate[1, 1] = 0.
        before = candidate.copy()
        got = self.compare(weights, features, candidate=candidate, max_sweeps=1)
        self.assertEqual(got.prefix_verified_decisions, 4)
        self.assertEqual(got.fallback_decisions, 6)
        self.assertEqual(got.sequential_fallback_rows, 2)
        np.testing.assert_array_equal(candidate, before)
        np.testing.assert_array_equal(got.codes, reference.codes)

    def test_nonzero_saved_accumulator_matches_independent_oracle(self):
        weights = np.array([[2.625, -3., .2, -.2, .4], [-3., 2.625, .4, .2, -.2]])
        features = np.array([[1., .25], [-.25, .5], [.125, -.25], [.5, .5], [.75, .2]])
        reference = quantize_dyadic_rows(weights, features, ridge=Q(1, 100), normalization=8)
        candidate = reference.codes.copy()
        candidate[:, -1] = np.where(candidate[:, -1] == 0., -.375, 0.)
        got = self.compare(weights, features, candidate=candidate, max_sweeps=1, row_batch_size=1)
        self.assertEqual(got.prefix_verified_decisions, 8)
        self.assertEqual(got.fallback_decisions, 2)
        np.testing.assert_array_equal(got.codes, reference.codes)
        with patch('src.speculative_dyadic_solver._check_row_cells',
                   side_effect=lambda w, *_: (np.zeros(len(w), dtype=np.int64), np.zeros(len(w), dtype=bool))):
            forced = self.compare(weights, features, candidate=candidate, max_sweeps=1,
                                  max_refinement_coordinates=0)
        self.assertEqual(forced.prefix_verified_decisions, 8)
        self.assertEqual(forced.exact_decisions, 2)
        self.assertEqual(forced.exact_coordinates, (4,))
        np.testing.assert_array_equal(forced.codes, reference.codes)

    def test_ties_subnormals_and_batch_invariance(self):
        tiny = 2.**-1074
        weights = np.array([[2.625, -3., .1875, -.1875, .5625],
                            [0., tiny, -tiny, 2*tiny, 0.]])
        a = self.compare(weights, np.empty((5, 0)), row_batch_size=1)
        b = self.compare(weights, np.empty((5, 0)), row_batch_size=20)
        np.testing.assert_array_equal(a.codes, b.codes)
        np.testing.assert_array_equal(a.codes[0], [2.625, -3., 0., -.375, .375])
        np.testing.assert_array_equal(a.codes[1], [0., 0., -2*tiny, 2*tiny, 0.])

    def test_exact_fallback_and_shared_coordinate_limits(self):
        features = np.array([[1e6, 1.], [-1e6, 1.], [1e6, 2.], [0., 0.]])
        weights = np.array([[.2, .7, -.3, .5], [.1, .2, .3, .4]])
        got = self.compare(weights, features, normalization=1, max_refinement_coordinates=0, row_batch_size=1)
        self.assertGreater(got.exact_decisions, 0)
        self.assertEqual(len(set(got.exact_coordinates)), len(got.exact_coordinates))
        with self.assertRaises(LowRankUnresolved):
            speculative_quantize_dyadic_rows(weights, features, ridge=Q(1, 100),
                max_exact_coordinates=0, max_refinement_coordinates=0, max_sweeps=0, row_batch_size=1)

    def test_invalid_candidates_and_limits_fail_closed(self):
        weights, features = np.array([[.1, -.3]]), np.ones((2, 1))
        for candidate in (np.ones((2, 1)), np.full((1, 2), np.nan), np.full((1, 2), .1234567)):
            with self.assertRaises(ValueError):
                speculative_quantize_dyadic_rows(weights, features, candidate=candidate, ridge=1)
        for options in ({'max_sweeps':-1}, {'max_sweeps':True}, {'row_batch_size':0}, {'row_batch_size':1.}):
            with self.assertRaises(ValueError):
                speculative_quantize_dyadic_rows(weights, features, ridge=1, **options)
        with np.errstate(over="ignore"):
            with self.assertRaises(LowRankUnresolved):
                speculative_quantize_dyadic_rows(weights, np.full((2, 1), 1e308), ridge=1)


if __name__ == '__main__':
    unittest.main()
