"""Software checks for a new row-specific target. No empirical quality claim."""
import unittest
from fractions import Fraction as Q

import numpy as np

from src.exact_core import sequential_oracle
from src.row_scaled_quantizer import row_scale_exponents, quantize_row_scaled


def exact(values):
    return tuple(tuple(Q.from_float(float(x)) for x in row) for row in values)


class RowScaledQuantizerTests(unittest.TestCase):
    def test_base_only_scales_cover_rows_minimally(self):
        weights = np.array([[0., 0., 0.], [-8., 7., 1.], [0., 8., 0.],
                            [-1., 0.5, 0.], [0., 2.**-1074, 0.]])
        exponents = row_scale_exponents(weights)
        self.assertEqual(exponents, (0, 0, 1, -3, -1074))
        for row, exponent in zip(exact(weights), exponents):
            scale = Q(2)**exponent
            self.assertGreaterEqual(min(row), -8*scale)
            self.assertLessEqual(max(row), 7*scale)
            if any(row) and exponent > -1074:
                self.assertTrue(min(row) < -8*scale/2 or max(row) > 7*scale/2)

    def test_matches_independent_dense_oracle_per_row(self):
        rng = np.random.default_rng(1719)
        for bits in (2, 4, 8):
            for d, rank in ((1, 0), (5, 3), (3, 5)):
                weights = rng.integers(-32, 33, size=(4, d)).astype(np.float64) / 32
                weights *= np.array([1., 2.**-10, 2.**10, 0.])[:, None]
                features = rng.integers(-8, 9, size=(d, rank)).astype(np.float64) / 8
                ridge, norm = Q(1, 100), Q(8)
                z = exact(features)
                covariance = [[(ridge if i == j else Q(0)) + sum(
                    (x*y for x,y in zip(z[i], z[j])), Q(0))/norm
                               for j in range(d)] for i in range(d)]
                exponents = row_scale_exponents(weights, bits)
                got = quantize_row_scaled(weights, features, exponents, bits=bits,
                                           ridge=ridge, normalization=norm, max_exact_coordinates=d)
                half = 1 << (bits-1)
                for row_index, (row, exponent) in enumerate(zip(exact(weights), exponents)):
                    grid = [Q(code)*Q(2)**exponent for code in range(-half, half)]
                    expected = sequential_oracle([row], covariance, [grid]*d).codes[0]
                    self.assertEqual(exact(got.codes)[row_index], expected)
                self.assertEqual(got.interval_decisions+got.exact_decisions, weights.size)
                self.assertFalse(got.codes.flags.writeable)

    def test_ties_zero_rows_and_subnormal_grid(self):
        # Covering extrema force scale one; +/-0.5 exercise lower-code ties.
        weights = np.array([[7., 0.5, -0.5], [0., 0., 0.],
                            [2.**-1074, 0., -2.**-1074]])
        features = np.empty((3, 0), dtype=np.float64)
        got = quantize_row_scaled(weights, features, row_scale_exponents(weights), ridge=1)
        self.assertEqual(got.codes[0].tolist(), [7., 0., -1.])
        self.assertEqual(got.codes[1].tolist(), [0., 0., 0.])
        self.assertEqual(got.codes[2].tolist(), weights[2].tolist())

    def test_rejects_lost_normalization_bits_and_nonfinite_grid(self):
        weights = np.array([[8., 2.**-1074]])
        exponents = row_scale_exponents(weights)
        self.assertEqual(exponents, (1,))
        with self.assertRaises(ValueError):
            quantize_row_scaled(weights, np.empty((2, 0)), exponents, ridge=1)
        with self.assertRaises(ValueError):
            row_scale_exponents(np.array([[np.finfo(np.float64).max]]))

    def test_rejects_foreign_scales_bits_and_array_subclasses(self):
        weights = np.array([[1., -1.]])
        with self.assertRaises(ValueError):
            quantize_row_scaled(weights, np.empty((2, 0)), (0,), ridge=1)
        for bits in (True, 1, 9, 4.0):
            with self.assertRaises(ValueError):
                row_scale_exponents(weights, bits)
        class Custom(np.ndarray):
            pass
        with self.assertRaises(TypeError):
            row_scale_exponents(weights.view(Custom))
        with self.assertRaises(ValueError):
            row_scale_exponents(np.array([[float('nan')]]))
        with self.assertRaises(ValueError):
            quantize_row_scaled(weights, np.empty((2, 0)), (True,), ridge=1)


if __name__ == '__main__':
    unittest.main()
