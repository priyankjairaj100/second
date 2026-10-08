"""Exact differentiation fixtures for untrusted corner proposals."""
from fractions import Fraction as Q
import unittest
from unittest.mock import patch

import numpy as np

from src.box_corner_witness import gradient_corners, CornerProposalUnresolved


class Dual:
    """Exact rational automatic differentiation, independent of the gradient formula."""
    def __init__(self, value, derivative=Q(0)):
        self.value, self.derivative = Q(value), Q(derivative)

    @staticmethod
    def lift(other):
        return other if isinstance(other, Dual) else Dual(other)

    def __add__(self, other):
        other = self.lift(other)
        return Dual(self.value+other.value, self.derivative+other.derivative)

    __radd__ = __add__

    def __neg__(self):
        return Dual(-self.value, -self.derivative)

    def __sub__(self, other):
        return self + -self.lift(other)

    def __rsub__(self, other):
        return self.lift(other) + -self

    def __mul__(self, other):
        other = self.lift(other)
        return Dual(self.value*other.value,
                    self.derivative*other.value+self.value*other.derivative)

    __rmul__ = __mul__

    def __truediv__(self, other):
        other = self.lift(other)
        return Dual(self.value/other.value,
                    (self.derivative*other.value-self.value*other.derivative)/other.value**2)


def conditional_decision(weights, codes, features, coordinate, beta):
    """Exact two-token inverse formula; accepts fractions or dual fractions."""
    gram = [[(beta if j == k else 0) + sum(
        (row[j]*row[k] for row in features[coordinate:]), Q(0)) for k in range(2)] for j in range(2)]
    accumulated = [sum(((weights[h]-codes[h])*features[h][k]
                        for h in range(coordinate)), Q(0)) for k in range(2)]
    a, b = gram[0]
    c, d = gram[1]
    determinant = a*d-b*c
    solution = ((d*accumulated[0]-b*accumulated[1])/determinant,
                (a*accumulated[1]-c*accumulated[0])/determinant)
    return weights[coordinate] + sum((features[coordinate][k]*solution[k] for k in range(2)), Q(0))


class BoxCornerWitnessTests(unittest.TestCase):
    def setUp(self):
        self.weights = np.array([.375, 1.625, -.375, .875])
        self.codes = np.array([.25, 1.5, -.5, 1.])
        self.features = np.array([[.75, -.375], [.5, .875], [-.625, .25], [.375, .5]])
        self.lower, self.upper = self.features-2.**-20, self.features+2.**-20
        self.beta, self.coordinate = Q(3, 8), 2

    def call(self, **changes):
        options = dict(weights_row=self.weights, candidate_row=self.codes,
                       lower=self.lower, upper=self.upper, coordinate=self.coordinate, beta=self.beta)
        options.update(changes)
        return gradient_corners(**options)

    def test_gradient_matches_independent_exact_differentiation(self):
        result = self.call()
        weights, codes = list(map(Q, self.weights)), list(map(Q, self.codes))
        for h, k in np.ndindex(self.features.shape):
            dual = [[Dual(Q(value), int((i, j) == (h, k)))
                     for j, value in enumerate(row)] for i, row in enumerate(self.features)]
            exact = conditional_decision(weights, codes, dual, self.coordinate, self.beta)
            self.assertAlmostEqual(result.gradient[h, k], float(exact.derivative), places=13)
            self.assertAlmostEqual(result.midpoint_decision, float(exact.value), places=13)

    def test_exact_central_differences_cover_each_coordinate_region(self):
        result = self.call()
        weights, codes = list(map(Q, self.weights)), list(map(Q, self.codes))
        for h in (0, self.coordinate, 3):
            for k in range(2):
                approximations = []
                for epsilon in (Q(1, 512), Q(1, 1024)):
                    plus = [list(map(Q, row)) for row in self.features]
                    minus = [list(map(Q, row)) for row in self.features]
                    plus[h][k] += epsilon
                    minus[h][k] -= epsilon
                    fd = (conditional_decision(weights, codes, plus, self.coordinate, self.beta)
                          - conditional_decision(weights, codes, minus, self.coordinate, self.beta))/(2*epsilon)
                    approximations.append(float(fd))
                self.assertLess(abs(approximations[-1]-result.gradient[h, k]), 2e-6)
                self.assertLessEqual(abs(approximations[-1]-result.gradient[h, k]),
                                     abs(approximations[0]-result.gradient[h, k])+1e-15)

    def test_corners_use_exact_endpoints_and_preserve_inputs(self):
        before = [a.copy() for a in (self.weights, self.codes, self.lower, self.upper)]
        result = self.call()
        mask = result.gradient >= 0.
        expected_plus = np.where(mask, self.upper, self.lower)
        expected_minus = np.where(mask, self.lower, self.upper)
        np.testing.assert_array_equal(result.plus.view(np.uint64), expected_plus.view(np.uint64))
        np.testing.assert_array_equal(result.minus.view(np.uint64), expected_minus.view(np.uint64))
        for original, saved in zip((self.weights, self.codes, self.lower, self.upper), before):
            np.testing.assert_array_equal(original, saved)
        self.assertEqual(result.plus.shape, self.features.shape)
        for array in (result.plus, result.minus, result.gradient, result.midpoint):
            with self.assertRaises(ValueError):
                array.flags.writeable = True

    def test_zero_gradient_policy_preserves_signed_endpoint_bits(self):
        lower, upper = self.lower.copy(), self.upper.copy()
        lower[0, 0], upper[0, 0] = -0., 0.
        result = self.call(lower=lower, upper=upper, coordinate=0)
        np.testing.assert_array_equal(result.gradient, np.zeros_like(result.gradient))
        np.testing.assert_array_equal(result.plus.view(np.uint64), upper.view(np.uint64))
        np.testing.assert_array_equal(result.minus.view(np.uint64), lower.view(np.uint64))
        self.assertEqual(result.midpoint_decision, self.weights[0])

    def test_subnormal_midpoint_and_empty_rank(self):
        tiny = np.nextafter(0., 1.)
        lower = np.full((4, 2), tiny)
        result = self.call(lower=lower, upper=lower.copy())
        np.testing.assert_array_equal(result.midpoint, lower)
        empty = self.call(lower=np.empty((4, 0)), upper=np.empty((4, 0)))
        self.assertEqual(empty.plus.shape, (4, 0))
        self.assertEqual(empty.midpoint_decision, self.weights[self.coordinate])

    def test_invalid_boxes_coordinates_and_types(self):
        for coordinate in (True, -1, 4, .5):
            with self.assertRaises(ValueError):
                self.call(coordinate=coordinate)
        with self.assertRaises(ValueError):
            self.call(lower=self.upper, upper=self.lower)
        with self.assertRaises(ValueError):
            self.call(weights_row=self.weights[:-1])
        with self.assertRaises(TypeError):
            self.call(weights_row=self.weights.astype(np.float32))
        for beta in (0, -1):
            with self.assertRaises(ValueError):
                self.call(beta=beta)
        with self.assertRaises(CornerProposalUnresolved):
            self.call(beta=Q(1, 2**2000))

    def test_nonfinite_inputs_and_failed_solves_produce_no_proposal(self):
        for name in ('weights_row', 'candidate_row', 'lower', 'upper'):
            array = dict(weights_row=self.weights, candidate_row=self.codes,
                         lower=self.lower, upper=self.upper)[name].copy()
            array.flat[0] = np.nan
            with self.assertRaises(ValueError):
                self.call(**{name: array})
        with patch('src.box_corner_witness.np.linalg.solve', side_effect=np.linalg.LinAlgError('singular')):
            with self.assertRaises(CornerProposalUnresolved):
                self.call()
        with patch('src.box_corner_witness.np.linalg.solve', return_value=np.full((2, 2), np.nan)):
            with self.assertRaises(CornerProposalUnresolved):
                self.call()
        with self.assertRaises(CornerProposalUnresolved):
            self.call(lower=np.full((4, 2), 1e200), upper=np.full((4, 2), 1e200))


if __name__ == '__main__':
    unittest.main()
