"""Exact-target software fixtures, not empirical quality measurements."""
from fractions import Fraction as Q
import unittest
from unittest.mock import patch

import numpy as np

from src.dyadic_row_quantizer import (
    _grid_arrays, dyadic_row_scale_metadata, dyadic_row_scales, quantize_dyadic_rows,
)
from src.exact_core import sequential_oracle
from src.low_rank_certified import LowRankUnresolved
from src.row_scaled_quantizer import row_scale_exponents


def exact(values):
    return tuple(tuple(Q.from_float(float(value)) for value in row) for row in values)


def covariance(features, ridge, normalization):
    return tuple(tuple((ridge if i == j else Q(0)) + sum(
        (x*y for x, y in zip(left, right)), Q(0)) / normalization
        for j, right in enumerate(features)) for i, left in enumerate(features))


class DyadicRowTests(unittest.TestCase):
    def compare(self, weights, features, *, bits=4, ridge=Q(1, 100), normalization=8, **limits):
        scales = dyadic_row_scales(weights, bits)
        got = quantize_dyadic_rows(weights, features, scales, bits=bits, ridge=ridge,
                                   normalization=normalization, **limits)
        metric = covariance(exact(features), ridge, normalization)
        half = 1 << (bits - 1)
        for row_index, (row, scale) in enumerate(zip(exact(weights), scales)):
            grid = tuple(k * Q.from_float(scale) for k in range(-half, half))
            expected = sequential_oracle([row], metric, [grid] * weights.shape[1]).codes[0]
            self.assertEqual(exact(got.codes)[row_index], expected)
        self.assertEqual(got.interval_decisions + got.exact_decisions, weights.size)
        self.assertFalse(got.codes.flags.writeable)
        return got

    def test_direct_grids_match_independent_dense_oracle(self):
        rng = np.random.default_rng(1324)
        for bits in (2, 4, 8):
            for width, rank in ((1, 0), (5, 0), (5, 3), (3, 5)):
                weights = rng.integers(-32, 33, (4, width)).astype(np.float64) / 32
                weights *= np.array([1., 2.**-10, 2.**10, 0.])[:, None]
                features = rng.integers(-8, 9, (width, rank)).astype(np.float64) / 8
                self.compare(weights, features, bits=bits, max_exact_coordinates=width)

    def test_scales_cover_rows_with_fine_relative_slack(self):
        weights = np.array([[1., -.1], [-1., .1], [2.625, -3.], [1e-200, -2e-200]])
        scales = dyadic_row_scales(weights)
        coarse = row_scale_exponents(weights)
        metadata = dyadic_row_scale_metadata(weights)
        for row, scale, exponent, record in zip(exact(weights), scales, coarse, metadata):
            needed = max(max(row)/7, -min(row)/8, Q(0))
            actual = Q.from_float(scale)
            self.assertGreaterEqual(actual, needed)
            self.assertLess(actual, needed * (1 + Q(1, 2**23)))
            self.assertLessEqual(actual, Q(2)**exponent)
            self.assertLessEqual(record["significant_bits"], 24)
            self.assertEqual(actual, record["significand"] * Q(2)**record["exponent"])
            self.assertEqual(float.fromhex(record["binary64_hex"]), scale)
        self.assertEqual(scales[2], .375)

    def test_small_precision_scales_are_minimal_by_enumeration(self):
        weights = np.array([[.01, -.025], [.3, -.1], [1.7, -2.3], [3., -1.]])
        for precision in (1, 2, 3, 4):
            candidates = sorted({Q(m) * Q(2)**e
                                 for m in range(1, 2**precision)
                                 for e in range(-20, 5)})
            for row, scale in zip(exact(weights), dyadic_row_scales(weights, significant_bits=precision)):
                needed = max(max(row)/7, -min(row)/8, Q(0))
                expected = next(candidate for candidate in candidates if candidate >= needed)
                self.assertEqual(Q.from_float(scale), expected)

    def test_all_grid_codes_and_midpoints_are_exact(self):
        weights = np.array([[.1, -.7], [2.625, -3.], [0., 2.**-1074], [1e100, -2e100]])
        for bits in (2, 4, 8):
            scales = dyadic_row_scales(weights, bits)
            codes, boundaries = _grid_arrays(scales, bits)
            half = 1 << (bits - 1)
            for row, scale in enumerate(scales):
                rational = Q.from_float(scale)
                for k, value in zip(range(-half, half), codes[row]):
                    self.assertEqual(Q.from_float(float(value)), k*rational)
                for k, value in zip(range(-half, half - 1), boundaries[row]):
                    self.assertEqual(Q.from_float(float(value)), Q(2*k+1, 2)*rational)

    def test_non_power_two_ties_and_no_inexact_normalization(self):
        weights = np.array([[2.625, -3., .1875, -.1875, .5625, .1]])
        scale = dyadic_row_scales(weights)[0]
        self.assertEqual(scale, .375)
        self.assertNotEqual(Q.from_float(float(weights[0, -1] / scale)),
                            Q.from_float(float(weights[0, -1])) / Q.from_float(scale))
        got = self.compare(weights, np.empty((6, 0)))
        self.assertEqual(got.codes[0, :5].tolist(), [2.625, -3., 0., -.375, .375])

    def test_subnormal_and_zero_rows_have_exact_half_steps(self):
        tiny = 2.**-1074
        weights = np.array([[0., tiny, -tiny, 2*tiny], [0., 0., 0., 0.]])
        self.assertEqual(dyadic_row_scales(weights), (2*tiny, 2*tiny))
        got = self.compare(weights, np.empty((4, 0)), ridge=Q(1), normalization=1,
                           max_exact_coordinates=4)
        self.assertEqual(got.codes[0].tolist(), [0., 0., -2*tiny, 2*tiny])
        self.assertEqual(got.codes[1].tolist(), [0.] * 4)

    def test_exact_fallback_refinement_and_budget_failure(self):
        features = np.array([[1e6, 1.], [-1e6, 1.], [1e6, 2.], [0., 0.]])
        weights = np.array([[.2, .7, -.3, .5], [.1, .2, .3, .4]])
        got = self.compare(weights, features, normalization=1,
                           max_exact_coordinates=4, max_refinement_coordinates=0)
        self.assertGreater(got.exact_decisions, 0)
        got = self.compare(weights, features, normalization=1, max_exact_coordinates=4)
        self.assertGreater(len(got.refined_coordinates), 0)
        with self.assertRaises(LowRankUnresolved):
            quantize_dyadic_rows(weights, features, ridge=Q(1, 100),
                                 max_exact_coordinates=0, max_refinement_coordinates=0)

    def test_overflow_nonfinite_scales_and_invalid_inputs_fail_closed(self):
        with self.assertRaises(ValueError):
            dyadic_row_scales(np.array([[np.finfo(np.float64).max]]))
        with self.assertRaises(LowRankUnresolved):
            quantize_dyadic_rows(np.ones((1, 2)), np.full((2, 1), 1e308), ridge=1)
        for value in (np.nan, np.inf, -np.inf):
            with self.assertRaises(ValueError):
                dyadic_row_scales(np.array([[value]]))
        for precision in (0, 25, True, 24.):
            with self.assertRaises(ValueError):
                dyadic_row_scales(np.ones((1, 1)), significant_bits=precision)
        with self.assertRaises(ValueError):
            quantize_dyadic_rows(np.ones((1, 1)), np.ones((1, 1)), (.25,), ridge=1)
        with self.assertRaises(ValueError):
            quantize_dyadic_rows(np.ones((1, 1)), np.ones((1, 1)), ridge=0)
        with self.assertRaises(ValueError):
            quantize_dyadic_rows(np.ones((1, 1)), np.ones((1, 1)), ridge=1, max_exact_rank=True)
        class Custom(np.ndarray):
            pass
        with self.assertRaises(TypeError):
            quantize_dyadic_rows(np.ones((1, 1)).view(Custom), np.ones((1, 1)), ridge=1)
        with patch("src.dyadic_row_quantizer._check_runtime", side_effect=RuntimeError("unsupported rounding")):
            with self.assertRaises(RuntimeError):
                quantize_dyadic_rows(np.ones((1, 1)), np.ones((1, 1)), ridge=1)


if __name__ == "__main__":
    unittest.main()
