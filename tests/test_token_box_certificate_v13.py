"""Software fixtures for a quantizer implication, not empirical datasets."""
from fractions import Fraction as Q
import itertools
import unittest
from unittest.mock import patch

import numpy as np

from src.low_rank_exact import token_reverse_ldl, token_sequential_oracle
from src.row_scaled_quantizer import row_scale_exponents, quantize_row_scaled
from src.token_box_certificate import (
    TokenBoxUnresolved, _box_coefficients, certify_row_scaled_box, certify_token_box,
)


def exact(values):
    return tuple(tuple(Q.from_float(float(value)) for value in row) for row in values)


def vertices(lower, upper):
    for choices in itertools.product((False, True), repeat=lower.size):
        yield np.where(np.asarray(choices).reshape(lower.shape), lower, upper)


class TokenBoxTests(unittest.TestCase):
    def test_zero_width_matches_exact_point_oracle(self):
        rng = np.random.default_rng(1313)
        for width, rank in ((1, 0), (5, 0), (3, 2), (4, 5)):
            weights = rng.integers(-12, 13, size=(3, width)).astype(np.float64) / 8
            factors = rng.integers(-8, 9, size=(width, rank)).astype(np.float64) / 8
            grids = [(-2, -1, 0, 1, 2)] * width
            got = certify_token_box(weights, factors, factors, grids, ridge=Q(1, 10),
                                    normalization=7, max_exact_coordinates=width)
            reference = token_sequential_oracle(exact(weights), exact(factors), grids,
                                                ridge=Q(1, 10), normalization=7)
            self.assertEqual(exact(got.codes), reference.codes)
            self.assertEqual(got.interval_decisions + got.point_exact_decisions, weights.size)
            self.assertEqual(got.uncertain_features, 0)

    def test_positive_width_certificate_matches_all_vertices_and_interior(self):
        weights = np.array([[1.1, -1.2, .3], [-.3, 1.2, -.1]])
        lower = np.array([[.9, -.3], [.4, .7], [-.5, .2]])
        upper = lower + .02
        grids = [(-2, -1, 0, 1, 2)] * 3
        got = certify_token_box(weights, lower, upper, grids, ridge=1)
        self.assertEqual(got.uncertain_features, 6)
        self.assertEqual(got.point_exact_decisions, 0)
        cases = list(vertices(lower, upper))
        cases.extend(lower + (upper-lower) * fraction for fraction in (.125, .5, .875))
        for factors in cases:
            expected = token_sequential_oracle(exact(weights), exact(factors), grids, ridge=1)
            self.assertEqual(exact(got.codes), expected.codes)
        with self.assertRaises(ValueError):
            got.codes.flags.writeable = True

    def test_residual_bounds_contain_exact_coefficients_at_every_vertex(self):
        lower = np.array([[.9, -.3], [.4, .7], [-.5, .2]])
        upper = lower + .02
        proposals, bounds = _box_coefficients(lower, upper, Q(3, 10))
        for factors in vertices(lower, upper):
            truth = token_reverse_ldl(exact(factors), ridge=Q(1, 10), normalization=3)
            for proposal, bound, coefficient in zip(proposals, bounds, truth.coefficients):
                error = sum((Q.from_float(float(a))-b)**2 for a, b in zip(proposal, coefficient))
                self.assertLessEqual(error, Q.from_float(float(bound)))

    def test_abstains_when_actual_codes_differ_inside_box(self):
        weights = np.array([[.4, .4]])
        lower = np.array([[0.], [1.]])
        upper = np.array([[1.], [1.]])
        grids = [(-1, 0, 1)] * 2
        left = token_sequential_oracle(exact(weights), exact(lower), grids, ridge=1)
        right = token_sequential_oracle(exact(weights), exact(upper), grids, ridge=1)
        self.assertNotEqual(left.codes, right.codes)
        with self.assertRaises(TokenBoxUnresolved):
            certify_token_box(weights, lower, upper, grids, ridge=1)

    def test_candidate_reuse_checks_exact_values(self):
        weights = np.array([[.4, .4]])
        lower, upper = np.array([[0.], [1.]]), np.array([[.1], [1.]])
        grids = [(-1, 0, 1)] * 2
        got = certify_token_box(weights, lower, upper, grids, ridge=1,
                                candidate_codes=np.zeros_like(weights))
        self.assertTrue(got.candidate_checked)
        with self.assertRaises(TokenBoxUnresolved):
            certify_token_box(weights, lower, upper, grids, ridge=1,
                              candidate_codes=np.ones_like(weights))

    def test_lower_ties_saturation_and_singleton_with_uncertain_features(self):
        weights = np.array([[.5], [-.5], [20.], [-20.]])
        lower, upper = np.array([[-1.]]), np.array([[1.]])
        got = certify_token_box(weights, lower, upper, [(-1, 0, 1)], ridge=1)
        self.assertEqual(got.codes[:, 0].tolist(), [0., -1., 1., -1.])
        got = certify_token_box(weights, lower, upper, [(Q(1, 8),)], ridge=1)
        self.assertEqual(got.codes[:, 0].tolist(), [.125] * 4)

    def test_zero_width_exact_boundary_uses_bounded_fallback(self):
        weights = np.array([[.5, .25]])
        factors = np.array([[1.], [1.]])
        got = certify_token_box(weights, factors, factors, [(-1, 0, 1)] * 2, ridge=1)
        self.assertEqual(got.codes.tolist(), [[0., 0.]])
        self.assertGreater(got.point_exact_decisions, 0)
        with self.assertRaises(TokenBoxUnresolved):
            certify_token_box(weights, factors, factors, [(-1, 0, 1)] * 2,
                              ridge=1, max_exact_coordinates=0)

    def test_row_wrapper_matches_point_target_and_box_vertices(self):
        weights = np.array([[7., .2, -.1], [.125, -.25, .05]])
        lower = np.array([[.9], [.4], [-.5]])
        upper = lower + .001
        exponents = row_scale_exponents(weights)
        got = certify_row_scaled_box(weights, lower, upper, exponents, ridge=10)
        for factors in vertices(lower, upper):
            expected = quantize_row_scaled(weights, factors, exponents, ridge=10)
            np.testing.assert_array_equal(got.codes, expected.codes)
        checked = certify_row_scaled_box(weights, lower, upper, exponents, ridge=10,
                                          candidate_codes=got.codes)
        self.assertTrue(checked.candidate_checked)
        with self.assertRaises(TokenBoxUnresolved):
            certify_row_scaled_box(weights, lower, upper, exponents, ridge=10,
                                   candidate_codes=np.ones_like(weights))

    def test_rejects_invalid_boxes_grids_and_candidates(self):
        weights, lower, upper = np.array([[.1]]), np.array([[0.]]), np.array([[1.]])
        for value in (np.nan, np.inf, -np.inf):
            with self.assertRaises(ValueError):
                certify_token_box(weights, lower, np.array([[value]]), [(-1, 0, 1)], ridge=1)
        with self.assertRaises(ValueError):
            certify_token_box(weights, upper, lower, [(-1, 0, 1)], ridge=1)
        with self.assertRaises(ValueError):
            certify_token_box(weights, lower, upper, [(Q(1, 3),)], ridge=1)
        with self.assertRaises(ValueError):
            certify_token_box(weights, lower, upper, [(-1, 0, 1)], ridge=0)
        with self.assertRaises(ValueError):
            certify_token_box(weights, lower, upper, [(-1, 0, 1)], ridge=1,
                              candidate_codes=np.zeros((2, 1)))
        with self.assertRaises(ValueError):
            certify_token_box(weights, lower, upper, [(-1, 0, 1)], ridge=1,
                              max_exact_rank=True)
        class Custom(np.ndarray):
            pass
        with self.assertRaises(TypeError):
            certify_token_box(weights.view(Custom), lower, upper, [(-1, 0, 1)], ridge=1)

    def test_rejects_nonfinite_intermediates_and_tiny_ridge(self):
        weights = np.array([[.1]])
        with self.assertRaises(TokenBoxUnresolved):
            certify_token_box(weights, np.array([[1e200]]), np.array([[2e200]]), [(-1, 0, 1)], ridge=1)
        with self.assertRaises(TokenBoxUnresolved):
            certify_token_box(weights, np.array([[0.]]), np.array([[1.]]), [(-1, 0, 1)], ridge=Q(1, 10**400))

    def test_runtime_guard_remains_required(self):
        with patch("src.token_box_certificate._check_runtime", side_effect=RuntimeError("unsupported runtime")):
            with self.assertRaises(RuntimeError):
                certify_token_box(np.array([[.1]]), np.array([[0.]]), np.array([[1.]]), [(-1, 0, 1)], ridge=1)


if __name__ == "__main__":
    unittest.main()
