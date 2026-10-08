"""Exact rational software fixtures, not empirical research datasets."""
import itertools
from fractions import Fraction as Q
import unittest
from unittest.mock import patch

import numpy as np

from src.dyadic_box_certificate import certify_dyadic_box
from src.dyadic_row_quantizer import dyadic_row_scales
from src.exact_core import sequential_oracle
from src.preconditioned_box_certificate import (
    certify_preconditioned_dyadic_box, _left_product,
    _preconditioned_error, _supersolution, _positive_product_add, _component_cells,
)
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
        result = sequential_oracle([[rational(x) for x in row]],
                                   metric, [grid]*weights.shape[1])
        rows.append(result.codes[0])
    return np.asarray(rows, dtype=np.float64)


def corners(lower, upper):
    for mask in itertools.product((False, True), repeat=lower.size):
        yield np.where(np.asarray(mask).reshape(lower.shape), upper, lower)


class PreconditionedCoefficientTests(unittest.TestCase):
    def test_directed_matrix_product_contains_rational_results(self):
        point = np.array([[1.1, -.3], [0., 2.3]])
        lower = np.array([[.7, -.6], [.1, 2.]])
        upper = lower + .01
        lo, hi = _left_product(point, lower, upper)
        for matrix in corners(lower, upper):
            for i, j in itertools.product(range(2), repeat=2):
                exact = sum((rational(point[i, k])*rational(matrix[k, j])
                             for k in range(2)), Q(0))
                self.assertLessEqual(rational(lo[i, j]), exact)
                self.assertLessEqual(exact, rational(hi[i, j]))

    def test_supersolution_has_exact_componentwise_proof(self):
        defect = np.array([[.1, .03], [.02, .2]])
        residual = np.array([1e-7, 2e-5])
        bound = _supersolution(defect, residual)
        self.assertIsNotNone(bound)
        for i in range(2):
            required = rational(residual[i]) + sum(
                (rational(defect[i, j])*rational(bound[j]) for j in range(2)), Q(0))
            self.assertLessEqual(required, rational(bound[i]))

    def test_contraction_and_nonfinite_inputs_fail_closed(self):
        self.assertIsNone(_supersolution(np.eye(2), np.ones(2)))
        self.assertIsNone(_supersolution(np.array([[np.inf]]), np.ones(1)))
        self.assertIsNone(_supersolution(np.array([[-.1]]), np.ones(1)))
        zero = _supersolution(np.zeros((2, 2)), np.zeros(2))
        np.testing.assert_array_equal(zero, np.zeros(2))

    def test_positive_products_enclose_subnormal_terms(self):
        tiny = np.nextafter(0., 1.)
        matrix = np.array([[tiny, 0.], [tiny, tiny]])
        vector = np.array([.5, .25])
        bound = _positive_product_add(matrix, vector, np.zeros(2))
        for i in range(2):
            exact = sum((rational(matrix[i, j])*rational(vector[j]) for j in range(2)), Q(0))
            self.assertLessEqual(exact, rational(bound[i]))
        self.assertGreater(bound[0], 0.)
        np.testing.assert_array_equal(
            _positive_product_add(np.zeros((2, 2)), vector, np.zeros(2)), np.zeros(2))

    def test_near_one_contraction_is_verified_or_rejected(self):
        defect = np.array([[1.-2.**-20]])
        residual = np.array([1e-100])
        bound = _supersolution(defect, residual)
        self.assertIsNotNone(bound)
        self.assertLessEqual(rational(residual[0]) + rational(defect[0, 0])*rational(bound[0]),
                             rational(bound[0]))
        # Outward sums cannot prove a strict gap at the preceding float.
        self.assertIsNone(_supersolution(np.array([[np.nextafter(1., 0.)]]), residual))

    def test_component_cells_preserve_exact_lower_code_ties(self):
        boundaries = np.array([[.5, 1.5], [.5, 1.5]])
        weights = np.array([.5, 1.5])
        indices, safe = _component_cells(weights, np.zeros((1, 2)), np.zeros((1, 2)),
                                        np.ones(1), np.zeros(1), boundaries)
        np.testing.assert_array_equal(indices, [0, 1])
        self.assertTrue(safe.all())
        _, uncertain = _component_cells(weights, np.ones((1, 2)), np.ones((1, 2)),
                                        np.zeros(1), np.array([1e-3]), boundaries)
        self.assertFalse(uncertain.any())

    def test_coefficient_radius_contains_exact_two_by_two_solutions(self):
        center = np.array([[4., .25], [.25, 2.]])
        gram_lo, gram_hi = center - .002, center + .002
        rhs = np.array([.4, -.6])
        rhs_lo, rhs_hi = rhs - .001, rhs + .001
        inverse = np.linalg.inv(center)
        proposal = inverse @ rhs
        bound = _preconditioned_error(gram_lo, gram_hi, rhs_lo, rhs_hi, proposal, inverse)
        self.assertIsNotNone(bound)
        for gram, vector in itertools.product(corners(gram_lo, gram_hi), corners(rhs_lo, rhs_hi)):
            a, b, c, d = map(rational, gram.reshape(-1))
            x, y = map(rational, vector)
            determinant = a*d-b*c
            exact = ((d*x-b*y)/determinant, (a*y-c*x)/determinant)
            for i in range(2):
                self.assertLessEqual(abs(exact[i]-rational(proposal[i])), rational(bound[i]))
        self.assertIsNone(_preconditioned_error(
            gram_lo, gram_hi, rhs_lo, rhs_hi, proposal, np.zeros((2, 2))))


class PreconditionedBoxTests(unittest.TestCase):
    def setUp(self):
        self.weights = np.array([[2.6, .21, -.11], [-.3, 1.7, .06]])
        self.features = np.array([[.9, -.3], [.4, .7], [-.5, .2]])

    def test_singletons_and_empty_rank_match_exact_dense_oracle(self):
        for features in (self.features, np.empty((3, 0))):
            result = certify_preconditioned_dyadic_box(
                self.weights, features, features, ridge=10, normalization=3)
            np.testing.assert_array_equal(result.codes, oracle(self.weights, features))
            self.assertEqual(result.uncertain_features, 0)

    def test_every_box_corner_and_interiors_match_exact_dense_oracle(self):
        lower, upper = self.features, self.features + 1e-8
        with patch('src.preconditioned_box_certificate.certify_dyadic_box',
                   side_effect=AssertionError('no point fallback for uncertain boxes')):
            result = certify_preconditioned_dyadic_box(
                self.weights, lower, upper, ridge=10, normalization=3)
        for features in corners(lower, upper):
            np.testing.assert_array_equal(result.codes, oracle(self.weights, features))
        for alpha in (.125, .5, .875):
            features = lower + alpha*(upper-lower)
            np.testing.assert_array_equal(result.codes, oracle(self.weights, features))
        self.assertGreater(result.verified_preconditioner_coordinates, 0)
        self.assertEqual(result.point_exact_decisions, 0)
        with self.assertRaises(ValueError):
            result.codes.flags.writeable = True

    def test_preconditioning_resolves_ridge_floor_fixture(self):
        weights = np.array([[.21, 2.6]])
        lower = np.ones((2, 1))
        upper = lower + 1e-6
        options = dict(ridge=Q(1, 1000000), normalization=1)
        with self.assertRaises(TokenBoxUnresolved):
            certify_dyadic_box(weights, lower, upper, **options)
        result = certify_preconditioned_dyadic_box(weights, lower, upper, **options)
        self.assertGreater(result.decisions_requiring_preconditioner, 0)
        for features in corners(lower, upper):
            np.testing.assert_array_equal(result.codes, oracle(weights, features, **options))

    def test_failed_preconditioner_preserves_ridge_certificate(self):
        upper = self.features + 1e-8
        expected = certify_dyadic_box(self.weights, self.features, upper, ridge=10, normalization=3)
        with patch('src.preconditioned_box_certificate._preconditioned_error', return_value=None):
            result = certify_preconditioned_dyadic_box(
                self.weights, self.features, upper, ridge=10, normalization=3)
        np.testing.assert_array_equal(result.codes, expected.codes)
        self.assertEqual(result.verified_preconditioner_coordinates, 0)
        self.assertEqual(result.rejected_preconditioner_coordinates, self.weights.shape[1])

    def test_real_endpoint_disagreement_cannot_be_certified(self):
        weights = np.array([[.21, 2.6]])
        lower, upper = np.ones((2, 1)), np.array([[4.], [1.]])
        options = dict(ridge=Q(1, 1000000), normalization=1)
        self.assertFalse(np.array_equal(oracle(weights, lower, **options), oracle(weights, upper, **options)))
        with self.assertRaises(TokenBoxUnresolved):
            certify_preconditioned_dyadic_box(weights, lower, upper, **options)

    def test_candidate_and_input_contracts(self):
        upper = self.features + 1e-8
        result = certify_preconditioned_dyadic_box(
            self.weights, self.features, upper, ridge=10, normalization=3)
        matched = certify_preconditioned_dyadic_box(self.weights, self.features, upper,
            ridge=10, normalization=3, candidate_codes=result.codes)
        self.assertTrue(matched.candidate_checked)
        with self.assertRaises(TokenBoxUnresolved):
            certify_preconditioned_dyadic_box(self.weights, self.features, upper,
                ridge=10, normalization=3, candidate_codes=np.zeros_like(self.weights))
        with self.assertRaises(ValueError):
            certify_preconditioned_dyadic_box(self.weights, upper, self.features, ridge=10)
        with self.assertRaises(ValueError):
            certify_preconditioned_dyadic_box(self.weights, self.features, upper, [1., 1.], ridge=10)
        for value in (True, -1, 1.5):
            with self.assertRaises(ValueError):
                certify_preconditioned_dyadic_box(self.weights, self.features, upper,
                    ridge=10, max_exact_coordinates=value)

    def test_extreme_bounds_fail_closed(self):
        with self.assertRaises(TokenBoxUnresolved):
            certify_preconditioned_dyadic_box(self.weights,
                np.full_like(self.features, -1e100), np.full_like(self.features, 1e100), ridge=1)

    def test_runtime_guard(self):
        with patch('src.preconditioned_box_certificate._check_runtime', side_effect=RuntimeError('unsupported')):
            with self.assertRaises(RuntimeError):
                certify_preconditioned_dyadic_box(self.weights, self.features, self.features, ridge=1)

    def test_nan_inputs_are_rejected_directly(self):
        for name in ('weights', 'lower', 'upper', 'candidate_codes'):
            inputs = dict(weights=self.weights.copy(), lower=self.features.copy(), upper=self.features.copy())
            if name == 'candidate_codes':
                inputs[name] = self.weights.copy()
            inputs[name].flat[0] = np.nan
            with self.assertRaises(ValueError):
                certify_preconditioned_dyadic_box(**inputs, ridge=10)


if __name__ == '__main__':
    unittest.main()
