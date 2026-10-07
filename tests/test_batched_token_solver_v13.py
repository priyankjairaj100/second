"""Software checks for common batching. These fixtures are not research data."""
from fractions import Fraction as Q
import unittest
from unittest.mock import patch

import numpy as np

from src.batched_token_solver import (
    _advance_accumulator, _check_cells, _coefficient_enclosures, _compile_grids,
    _norm_squared_token_major, batched_quantize_row_scaled, batched_token_codes,
)
from src.exact_core import sequential_oracle
from src.low_rank_certified import (
    LowRankUnresolved, _add, _check_cells as old_check_cells,
    _coefficient_enclosures as old_coefficient_enclosures,
    _multiply_point, _norm_squared_upper, certified_token_codes,
)
from src.row_scaled_quantizer import quantize_row_scaled, row_scale_exponents


def exact(values):
    return tuple(tuple(Q.from_float(float(value)) for value in row) for row in values)


def covariance(features, ridge, normalization):
    return tuple(tuple((ridge if i == j else Q(0)) + sum(
        (x*y for x, y in zip(left, right)), Q(0)) / normalization
        for j, right in enumerate(features)) for i, left in enumerate(features))


class BatchedTokenTests(unittest.TestCase):
    def compare(self, weights, features, grids=None, *, ridge=Q(1, 100), normalization=8, **limits):
        if grids is None:
            grids = [tuple(Q(j, 4) for j in range(-8, 9))] * weights.shape[1]
        old = certified_token_codes(weights, features, grids, ridge=ridge,
                                    normalization=normalization, **limits)
        got = batched_token_codes(weights, features, grids, ridge=ridge,
                                  normalization=normalization, **limits)
        reference = sequential_oracle(exact(weights), covariance(exact(features), ridge, normalization), grids)
        self.assertEqual(exact(got.codes), reference.codes)
        self.assertEqual(got.codes.tobytes(), old.codes.tobytes())
        for name in ("interval_decisions", "exact_decisions", "exact_coordinates",
                     "refined_coordinates", "max_coefficient_error_squared", "runtime_premise"):
            self.assertEqual(getattr(got, name), getattr(old, name), name)
        self.assertFalse(got.codes.flags.writeable)
        return got

    def test_random_empty_rank_deficient_and_strided_inputs(self):
        rng = np.random.default_rng(1314)
        for width, rank in ((1, 0), (7, 0), (2, 1), (6, 3), (4, 7), (15, 4)):
            features = rng.integers(-16, 17, (width, rank)).astype(np.float64) / 16
            if rank > 1:
                features[:, 1] = features[:, 0]
            weights = rng.integers(-32, 33, (5, width)).astype(np.float64) / 32
            self.compare(weights, features, max_exact_coordinates=width)
            self.compare(weights[:, ::-1], features[::-1], max_exact_coordinates=width)

    def test_directed_bounds_and_accumulator_match_bitwise(self):
        rng = np.random.default_rng(1315)
        lower = rng.integers(-32, 32, (7, 5)).astype(np.float64) / 64
        upper = lower + rng.integers(0, 8, (7, 5)).astype(np.float64) / 64
        lower[0, 0], upper[0, 0] = -0.0, 0.0
        lower[1, 1], upper[1, 1] = -2.**-1074, 2.**-1074
        expected = _norm_squared_upper(lower, upper)
        got = _norm_squared_token_major(lower.T, upper.T)
        self.assertEqual(expected.tobytes(), got.tobytes())
        weights = rng.integers(-16, 17, 7).astype(np.float64) / 8
        codes = rng.integers(-2, 3, 7).astype(np.float64)
        features = np.array([0., 1., -1., 2.**-1074, -.25])
        old_lower, old_upper = lower.copy(), upper.copy()
        difference_lower, difference_upper = _add(weights, weights, -codes, -codes)
        for k in range(len(features)):
            term_lower, term_upper = _multiply_point(difference_lower, difference_upper, features[k])
            old_lower[:, k], old_upper[:, k] = _add(
                old_lower[:, k], old_upper[:, k], term_lower, term_upper)
        got_lower, got_upper = _advance_accumulator(lower.T, upper.T, weights, codes, features)
        self.assertEqual(old_lower.tobytes(), got_lower.T.tobytes())
        self.assertEqual(old_upper.tobytes(), got_upper.T.tobytes())

    def test_coefficient_bounds_and_cell_masks_match_reference(self):
        features = np.array([[.2, .7], [1.4, -.5], [1.4, -.5], [3.2, -9.1]])
        old_coefficients, old_errors = old_coefficient_enclosures(features, Q(8, 25))
        coefficients, errors = _coefficient_enclosures(features, Q(8, 25))
        self.assertEqual(coefficients.tobytes(), old_coefficients.tobytes())
        self.assertEqual(errors.tobytes(), old_errors.tobytes())
        grid = tuple(Q(j, 4) for j in range(-8, 9))
        compiled = _compile_grids([grid], 1)[0]
        lower = np.array([[.1, -.2], [-.3, .4], [.5, .6]])
        upper = lower + .01
        weights = np.array([.5, -.5, .25])
        for coefficient, error in zip(coefficients, errors):
            old_indices, old_safe = old_check_cells(weights, lower, upper, coefficient, error, grid)
            indices, safe = _check_cells(weights, lower.T, upper.T, coefficient, error, compiled)
            np.testing.assert_array_equal(indices, old_indices)
            np.testing.assert_array_equal(safe, old_safe)

    def test_ties_saturation_singleton_and_subnormal_boundaries(self):
        weights = np.array([[.5, -.5, 20.], [-.5, .5, -20.]])
        self.compare(weights, np.array([[1.], [1.], [-1.]]),
                     [(-1, 0, 1), (-1, 0, 1), (Q(1, 8),)], max_exact_coordinates=3)
        got = self.compare(weights, np.empty((3, 0)), [(-1, 0, 1)] * 3)
        self.assertEqual(got.codes[0, 0], 0.)
        self.assertEqual(got.codes[1, 0], -1.)
        tiny = 2.**-1074
        grid = (Q(0), Q.from_float(tiny), 2*Q.from_float(tiny))
        self.compare(np.array([[0., tiny], [-tiny, 0.]]), np.array([[tiny], [-tiny]]),
                     [grid] * 2, ridge=Q(1), normalization=1, max_exact_coordinates=2)

    def test_exact_fallback_and_refinement_preserve_decisions_and_counts(self):
        features = np.array([[1e6, 1.], [-1e6, 1.], [1e6, 2.], [0., 0.]])
        weights = np.array([[.2, .7, -.3, .5], [.1, .2, .3, .4]])
        got = self.compare(weights, features, max_exact_coordinates=4, max_refinement_coordinates=0)
        self.assertGreater(got.exact_decisions, 0)
        got = self.compare(weights, features, max_exact_coordinates=0)
        self.assertGreater(len(got.refined_coordinates), 0)
        self.assertEqual(got.exact_decisions, 0)
        with self.assertRaises(LowRankUnresolved):
            batched_token_codes(weights, features, [(-1, 0, 1)] * 4, ridge=Q(1, 100),
                                max_exact_coordinates=0, max_refinement_coordinates=0)

    def test_row_wrapper_preserves_target_and_diagnostics(self):
        rng = np.random.default_rng(1316)
        for bits in (2, 4, 8):
            weights = rng.integers(-32, 33, (4, 5)).astype(np.float64) / 32
            weights *= np.array([1., 2.**-10, 2.**10, 0.])[:, None]
            features = rng.integers(-8, 9, (5, 3)).astype(np.float64) / 8
            exponents = row_scale_exponents(weights, bits)
            old = quantize_row_scaled(weights, features, exponents, bits=bits,
                                      ridge=Q(1, 100), normalization=8, max_exact_coordinates=5)
            got = batched_quantize_row_scaled(weights, features, exponents, bits=bits,
                                              ridge=Q(1, 100), normalization=8, max_exact_coordinates=5)
            self.assertEqual(old.codes.tobytes(), got.codes.tobytes())
            self.assertEqual(old.exact_decisions, got.exact_decisions)
            self.assertEqual(old.exact_coordinates, got.exact_coordinates)
            self.assertEqual(old.refined_coordinates, got.refined_coordinates)
        with self.assertRaises(ValueError):
            batched_quantize_row_scaled(np.array([[8., 2.**-1074]]), np.empty((2, 0)),
                                        (1,), ridge=1)

    def test_grid_cache_preserves_exact_nonuniform_boundaries(self):
        grid = (Q(-1), Q(0), Q(1, 2), Q(3))
        compiled = _compile_grids([grid, grid, (-1, 1)], 3)
        self.assertIs(compiled[0], compiled[1])
        self.assertIsNot(compiled[0], compiled[2])
        self.compare(np.array([[.25, 1.75, 0.], [-.5, .25, -.1]]),
                     np.empty((3, 0)), [grid, grid, (-1, 1)])

    def test_fail_closed_on_overflow_invalid_values_and_runtime(self):
        with self.assertRaises(LowRankUnresolved):
            batched_token_codes(np.ones((1, 2)), np.full((2, 1), 1e308), [(-1, 0, 1)] * 2, ridge=1)
        for value in (np.nan, np.inf, -np.inf):
            with self.assertRaises(ValueError):
                batched_token_codes(np.array([[value]]), np.ones((1, 1)), [(-1, 0, 1)], ridge=1)
        class Custom(np.ndarray):
            pass
        with self.assertRaises(TypeError):
            batched_token_codes(np.ones((1, 1)).view(Custom), np.ones((1, 1)), [(0, 1)], ridge=1)
        with self.assertRaises(ValueError):
            batched_token_codes(np.ones((1, 1)), np.ones((1, 1)), [(0, Q(1, 10))], ridge=1)
        with self.assertRaises(ValueError):
            batched_token_codes(np.ones((1, 1)), np.ones((1, 1)), [(0, 1)], ridge=1, max_exact_rank=True)
        with patch("src.batched_token_solver._check_runtime", side_effect=RuntimeError("unsupported rounding")):
            with self.assertRaises(RuntimeError):
                batched_token_codes(np.ones((1, 1)), np.ones((1, 1)), [(0, 1)], ridge=1)


if __name__ == "__main__":
    unittest.main()
