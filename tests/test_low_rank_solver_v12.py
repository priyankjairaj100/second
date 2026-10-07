"""Software fixtures only. These tests are not empirical language-model results."""
import unittest
from fractions import Fraction as Q
from unittest.mock import patch

import numpy as np

from src.exact_core import reverse_ldl, sequential_oracle
from src.low_rank_exact import token_reverse_ldl, token_sequential_oracle
from src.low_rank_certified import (LowRankUnresolved, _coefficient_enclosures,
                                    certified_token_codes)


def covariance(features, ridge, normalization):
    d = len(features)
    return tuple(tuple((ridge if i == j else Q(0)) + sum(
        (x * y for x, y in zip(features[i], features[j])), Q(0)) / normalization
                       for j in range(d)) for i in range(d))


def exact(values):
    return tuple(tuple(Q.from_float(float(x)) for x in row) for row in values)


class TokenExactTests(unittest.TestCase):
    def test_all_factors_traces_and_codes_match_dense(self):
        rng = np.random.default_rng(1717)
        for d, rank in ((1, 0), (2, 1), (5, 3), (3, 5), (6, 2)):
            z = exact(rng.integers(-8, 9, (d, rank)).astype(np.float64) / 8)
            weights = exact(rng.integers(-9, 10, (4, d)).astype(np.float64) / 8)
            grids = [tuple(Q(j, 4) for j in range(-5, 6))] * d
            ridge, norm = Q(1, 100), Q(7, 3)
            dense = sequential_oracle(weights, covariance(z, ridge, norm), grids)
            compact = token_sequential_oracle(weights, z, grids, ridge=ridge, normalization=norm)
            self.assertEqual(compact.rows, dense.rows)
            self.assertEqual(compact.factors.pivots, dense.factors.t)
            self.assertEqual(compact.factors.g, dense.factors.g)
            for i in range(d):
                for h in range(i):
                    coefficient = sum((x * y for x, y in zip(
                        compact.factors.coefficients[i], z[h])), Q(0))
                    self.assertEqual(coefficient, dense.factors.L[i][h])

    def test_duplicates_zeros_deletion_and_fixed_normalization(self):
        z = ((Q(1), Q(1), Q(0)), (Q(2), Q(2), Q(0)), (Q(-1), Q(-1), Q(0)))
        weights = ((Q(1, 2), Q(-1, 2), Q(3, 2)),)
        grids = [(-1, 0, 1)] * 3
        for retained in ((0, 1, 2), (1, 2), ()):
            features = tuple(tuple(row[j] for j in retained) for row in z)
            reference = sequential_oracle(weights, covariance(features, Q(1, 10), Q(3)), grids)
            got = token_sequential_oracle(weights, features, grids, ridge=Q(1, 10), normalization=3)
            self.assertEqual(got.rows, reference.rows)

    def test_invalid_exact_inputs(self):
        for ridge, norm in ((0, 1), (1, 0), (-1, 1)):
            with self.assertRaises(ValueError):
                token_reverse_ldl(((1,),), ridge=ridge, normalization=norm)
        with self.assertRaises(TypeError):
            token_reverse_ldl(((0.5,),), ridge=1)
        with self.assertRaises(ValueError):
            token_reverse_ldl(((1,), (1, 2)), ridge=1)


class CertifiedTokenTests(unittest.TestCase):
    def compare(self, weights, z, *, ridge=Q(1, 100), norm=8, grids=None, **limits):
        d = weights.shape[1]
        if grids is None:
            grids = [tuple(Q(j, 4) for j in range(-8, 9))] * d
        reference = token_sequential_oracle(exact(weights), exact(z), grids,
                                           ridge=ridge, normalization=norm)
        got = certified_token_codes(weights, z, grids, ridge=ridge, normalization=norm, **limits)
        self.assertEqual(exact(got.codes), reference.codes)
        self.assertEqual(got.interval_decisions + got.exact_decisions, weights.size)
        self.assertFalse(got.codes.flags.writeable)
        return got

    def test_random_and_rank_deficient_match_dense_target(self):
        rng = np.random.default_rng(143)
        for d, rank in ((1, 0), (7, 0), (2, 1), (6, 3), (4, 7), (20, 4)):
            for seed in range(3):
                z = rng.integers(-16, 17, (d, rank)).astype(np.float64) / 16
                if rank > 1:
                    z[:, 1] = z[:, 0]
                weights = rng.integers(-32, 33, (5, d)).astype(np.float64) / 32
                self.compare(weights, z, max_exact_coordinates=d)

    def test_exact_ties_saturation_and_singleton(self):
        w = np.array([[0.5, -0.5, 20.0], [-0.5, 0.5, -20.0]], dtype=np.float64)
        z = np.array([[1.0], [1.0], [-1.0]], dtype=np.float64)
        self.compare(w, z, grids=[(-1, 0, 1), (-1, 0, 1), (Q(1, 8),)], max_exact_coordinates=3)
        got = self.compare(w, np.empty((3, 0)), grids=[(-1, 0, 1)] * 3)
        self.assertEqual(got.codes[0, 0], 0)
        self.assertEqual(got.codes[1, 0], -1)

    def test_residual_bound_contains_exact_coefficients(self):
        z = np.array([[0.2, 0.7], [1.4, -0.5], [1.4, -0.5], [3.2, -9.1]])
        ridge, norm = Q(1, 100), Q(32)
        coefficients, errors = _coefficient_enclosures(z, ridge * norm)
        reference = token_reverse_ldl(exact(z), ridge=ridge, normalization=norm)
        for proposal, squared_error, truth in zip(coefficients, errors, reference.coefficients):
            error = sum(((Q.from_float(float(x)) - y) ** 2 for x, y in zip(proposal, truth)), Q(0))
            self.assertLessEqual(error, Q.from_float(float(squared_error)))

    def test_inaccurate_candidate_does_not_become_wrong_codes(self):
        # Large dynamic range gives poor inverse-update candidates and wide bounds.
        z = np.array([[1e6, 1.0], [-1e6, 1.0], [1e6, 2.0], [0.0, 0.0]])
        weights = np.array([[0.2, 0.7, -0.3, 0.5], [0.1, 0.2, 0.3, 0.4]])
        got = self.compare(weights, z, max_exact_coordinates=4, max_refinement_coordinates=0)
        self.assertGreater(got.exact_decisions, 0)
        refined = self.compare(weights, z, max_exact_coordinates=0)
        self.assertGreater(len(refined.refined_coordinates), 0)
        self.assertEqual(refined.exact_decisions, 0)

    def test_runtime_guard_is_required(self):
        with patch('src.low_rank_certified._check_runtime', side_effect=RuntimeError('unsupported rounding')):
            with self.assertRaises(RuntimeError):
                certified_token_codes(np.ones((1, 1)), np.ones((1, 1)), [(0, 1)], ridge=1)

    def test_fallback_budget_aborts(self):
        z = np.array([[1e6, 1.0], [-1e6, 1.0], [1e6, 2.0], [0.0, 0.0]])
        weights = np.array([[0.2, 0.7, -0.3, 0.5]])
        with self.assertRaises(LowRankUnresolved):
            certified_token_codes(weights, z, [(-1, 0, 1)] * 4,
                                  ridge=Q(1, 100), max_exact_coordinates=0, max_refinement_coordinates=0)

    def test_subnormal_features_and_nonrepresentable_midpoints(self):
        tiny = float(np.nextafter(0.0, 1.0))
        z = np.array([[tiny], [-tiny]])
        weights = np.array([[0.0, tiny], [-tiny, 0.0]])
        grid = (Q(0), Q.from_float(tiny), 2 * Q.from_float(tiny))
        self.compare(weights, z, grids=[grid] * 2, ridge=1, norm=1, max_exact_coordinates=2)

    def test_fails_closed_on_overflow_and_bad_types(self):
        class OverriddenArray(np.ndarray):
            pass
        with self.assertRaises(TypeError):
            certified_token_codes(np.ones((1, 1)).view(OverriddenArray), np.ones((1, 1)), [(0, 1)], ridge=1)
        with self.assertRaises(LowRankUnresolved):
            certified_token_codes(np.ones((1, 2)), np.full((2, 1), 1e308), [(-1, 0, 1)] * 2, ridge=1)
        with self.assertRaises(TypeError):
            certified_token_codes([[1.0]], np.ones((1, 1)), [(0, 1)], ridge=1)
        with self.assertRaises(ValueError):
            certified_token_codes(np.ones((1, 1)), np.ones((1, 1)), [(0, Q(1, 10))], ridge=1)
        with self.assertRaises(ValueError):
            certified_token_codes(np.ones((1, 1)), np.ones((1, 1)), [(0, 1)], ridge=1, max_exact_rank=True)


if __name__ == '__main__':
    unittest.main()
