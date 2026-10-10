"""Independent rational and archive oracles for integer software fixtures."""
from fractions import Fraction as Q
import unittest
from unittest.mock import patch
import numpy as np

from research_v35 import exact_gram as old
from research_v40 import native_exact_gram as new


class NativeExactGramTests(unittest.TestCase):
    def check(self, values):
        budget = old.GramBudget(max_width=16, max_tokens=1024, max_memory_bytes=64 * 2**20)
        expected = old.accumulate(values, source_id='fixture', normalization=1664, budget=budget)
        actual = new.accumulate(values, source_id='fixture', normalization=1664, budget=budget)
        self.assertEqual(old.dumps(expected, budget=budget), old.dumps(actual, budget=budget))
        scale = Q(2) ** actual.exponent
        offset = 0
        for i in range(values.shape[0]):
            for j in range(i + 1):
                exact = sum((Q.from_float(float(x)) * Q.from_float(float(y))
                             for x, y in zip(values[i], values[j])), Q(0))
                self.assertEqual(actual.packed[offset] * scale, exact)
                offset += 1
        return actual

    def test_zero_empty_and_signed_cancellation(self):
        for values in [np.empty((3, 0)), np.zeros((3, 4)),
                       np.array([[1., -1., 0., -0.], [1., 1., 0., 0.]])]:
            self.check(values)

    def test_cross_limb_products_and_carries(self):
        # Smallest entry sets the shared exponent. Other entries span two limbs.
        values = np.array([[1., 2.**70, -(2.**70), 2.**80],
                           [2.**60, -(2.**75), 2.**76, 3.]])
        self.check(values)

    def test_normal_and_subnormal_boundary(self):
        tiny = np.finfo(np.float64).smallest_subnormal
        self.check(np.array([[tiny, -tiny, 2.**-1022], [tiny * 3, tiny * 9, -(2.**-1022)]]))

    def test_deterministic_finite_word_patterns(self):
        # Generated values exercise software arithmetic; these are not empirical data.
        rng = np.random.default_rng(4001)
        for _ in range(12):
            values = np.ldexp(rng.integers(-2**48, 2**48, size=(5, 17)).astype(np.float64),
                             rng.integers(-30, 31, size=(5, 17)))
            self.check(values)

    def test_large_cancellation_keeps_exact_negative_cross_entry(self):
        values = np.array([[1., 2.**100, -(2.**100)], [1., -(2.**100), 2.**100]])
        actual = self.check(values)
        self.assertLess(actual.packed[1], 0)

    def test_admitted_255_bit_boundary(self):
        values = np.array([[1., 2.**126], [-1., -(2.**126)]])
        actual = self.check(values)
        self.assertEqual(actual.admission.accumulator_magnitude_bits, 255)

    def test_workspace_admission_precedes_compilation(self):
        values = np.ones((2, 2))
        _, admission = old._feature_scan(values, old.GramBudget())
        budget = old.GramBudget(max_memory_bytes=admission.explicit_memory_bound)
        with patch.object(new, 'prepare_native') as build:
            with self.assertRaises(old.GramAdmissionError):
                new.accumulate(values, source_id='workspace', budget=budget)
            build.assert_not_called()

    def test_rejects_overflow_before_native_work(self):
        values = np.array([[1., 2.**128]])
        with patch.object(new, 'prepare_native') as build:
            with self.assertRaises(old.GramAdmissionError):
                new.accumulate(values, source_id='too-wide', budget=old.GramBudget(max_integer_bits=512))
            build.assert_not_called()

    def test_exact_subtraction_matches_fresh_archive(self):
        left = np.array([[.3, .8], [-.2, .7]])
        right = np.array([[.2, -.1], [1.5, .9]])
        a = new.accumulate(left, source_id='a')
        b = new.accumulate(right, source_id='b')
        pooled = old.add_grams(a, b)
        self.assertEqual(old.dumps(old.subtract_gram(pooled, a)), old.dumps(old.accumulate(right, source_id='b')))

    def test_nonfinite_inputs_cannot_become_trusted(self):
        for value in [float('nan'), float('inf'), -float('inf')]:
            with self.assertRaises(ValueError):
                new.accumulate(np.array([[value]]), source_id='invalid')


if __name__ == '__main__':
    unittest.main()
