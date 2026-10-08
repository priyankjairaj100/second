"""Independent adversarial software checks for the universal box proof."""
from fractions import Fraction as Q
import unittest
from unittest.mock import patch

import numpy as np

import src.native_box_coefficients_v31 as module
from src.low_rank_certified import _exact_coefficient, _initial_gram
from tests.test_native_box_v26 import corners, rational


class NativeBoxIndependentReviewTests(unittest.TestCase):
    def test_finite_wrong_nonsymmetric_inverse_remains_untrusted(self):
        lower = np.array([[-.5, .125], [.25, -.5], [-.25, -.125]])
        upper = np.array([[.25, .25], [.5, -.125], [.125, .375]])
        beta = Q(2, 7)
        initial = _initial_gram(2, beta)

        def correct_gram(*args):
            return initial[0].copy(), initial[1].copy(), initial[2]

        # Corrupt only the untrusted proposal generator. The enclosure's
        # initial Gram remains correct, including exact beta rounding.
        wrong_inverse_seed = np.array([[13., -7.], [5., 2.]])
        with patch.object(module, '_initial_gram', side_effect=correct_gram), \
             patch.object(module.np, 'eye', return_value=wrong_inverse_seed):
            result = module.native_box_coefficient_enclosures(lower, upper, beta)

        self.assertEqual(result.zero_proposal_fallbacks, 0)
        self.assertTrue(np.any(result.coefficients != 0.))
        ordinary = module.native_box_coefficient_enclosures(lower, upper, beta)
        self.assertFalse(np.array_equal(result.coefficients, ordinary.coefficients))

        realizations = list(corners(lower, upper))
        for numerator in (1, 2, 3):
            point = lower + (upper - lower) * (numerator / 4.)
            realizations.append(point)
        self.assertEqual(len(realizations), 67)
        for features in realizations:
            for coordinate in range(len(lower)):
                exact = _exact_coefficient(features, coordinate, beta)
                distance_squared = sum(
                    ((value - rational(proposal)) ** 2 for value, proposal in
                     zip(exact, result.coefficients[coordinate])), Q(0))
                self.assertLessEqual(distance_squared, rational(result.errors[coordinate]))


if __name__ == '__main__':
    unittest.main()
