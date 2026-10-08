"""Exact mathematical fixtures, not calibration or language-model experiments."""

from fractions import Fraction as Q
from itertools import combinations
from math import comb
import unittest

import numpy as np

from src.dyadic_row_quantizer import dyadic_row_scales
from src.exact_core import sequential_oracle


GRID = tuple(range(-8, 8))


def balanced_assignments(n):
    for positive in combinations(range(n), n // 2):
        selected = set(positive)
        yield tuple(1 if r in selected else -1 for r in range(n))


def ridge_metric(records, width):
    # Form the metric independently from individual outer products.
    return tuple(tuple(
        Q(int(i == j)) + sum((Q(x[i]) * Q(x[j]) for x in records), Q(0))
        for j in range(width)) for i in range(width))


class ResponseLowerBoundTests(unittest.TestCase):
    def test_canonical_scale_and_binary64_domain_endpoints(self):
        for n in (2, 4, 8, 16, 1 << 51):
            with self.subTest(n=n):
                exact = (Q(1, 4), Q(1, 2) - Q(1, 8 * n), Q(7))
                weights = np.array([[float(x) for x in exact]], dtype=np.float64)
                self.assertEqual(tuple(Q.from_float(float(x)) for x in weights[0]), exact)
                for precision in (1, 24):
                    self.assertEqual(dyadic_row_scales(weights, 4, precision), (1.0,))
        # Beyond the stated domain, the untied dyadic weight may round to a tie.
        self.assertEqual(float(Q(1, 2) - Q(1, 8 * (1 << 52))), 0.5)

    def test_balanced_families_are_separated_by_exact_model_responses(self):
        for n in (2, 4, 8):
            epsilon = Q(1, 8 * n)
            weights = ((Q(1, 4), Q(1, 2) - epsilon, Q(7)),)
            original_metric = ((Q(n + 1), Q(0), Q(0)),
                               (Q(0), Q(n + 1), Q(0)),
                               (Q(0), Q(0), Q(n + 1)))
            response_vectors = set()
            for signs in balanced_assignments(n):
                records = tuple(((a, 1, 0), (0, 0, 1)) for a in signs)
                metric = ridge_metric(tuple(x for record in records for x in record), 3)
                self.assertEqual(metric, original_metric)
                original = sequential_oracle(weights, metric, (GRID,) * 3)
                self.assertEqual(original.codes, ((Q(0), Q(0), Q(7)),))
                self.assertEqual(original.rows[0].inputs, weights[0])
                responses = []
                for r, sign in enumerate(signs):
                    retained = records[:r] + records[r + 1:]
                    retained_metric = ridge_metric(tuple(x for record in retained for x in record), 3)
                    self.assertEqual(retained_metric,
                                     ((Q(n), Q(-sign), Q(0)),
                                      (Q(-sign), Q(n), Q(0)),
                                      (Q(0), Q(0), Q(n))))
                    result = sequential_oracle(weights, retained_metric, (GRID,) * 3)
                    expected_code = Q(int(sign == -1))
                    self.assertEqual(result.codes, ((Q(0), expected_code, Q(7)),))
                    decision = result.rows[0].inputs[1]
                    self.assertEqual(decision, Q(1, 2) - epsilon - Q(sign, 4 * n))
                    self.assertGreaterEqual(abs(decision - Q(1, 2)), epsilon)
                    self.assertGreater(decision, Q(0))
                    self.assertLess(decision, Q(1))
                    responses.append(result.codes[0][1])
                response_vectors.add(tuple(responses))
            self.assertEqual(len(response_vectors), comb(n, n // 2))

    def test_explicit_two_coordinate_grid_rational_and_tied_variants(self):
        for n in (2, 4, 6):
            signs = (1,) * (n // 2) + (-1,) * (n // 2)
            records = tuple((a, 1) for a in signs)
            for epsilon in (Q(0), Q(1, 8 * n)):
                weights = ((Q(1, 4), Q(1, 2) - epsilon),)
                original = sequential_oracle(weights, ridge_metric(records, 2), (GRID,) * 2)
                self.assertEqual(original.codes, ((Q(0), Q(0)),))
                for r, sign in enumerate(signs):
                    retained = records[:r] + records[r + 1:]
                    result = sequential_oracle(weights, ridge_metric(retained, 2), (GRID,) * 2)
                    self.assertEqual(result.rows[0].inputs[1],
                                     Q(1, 2) - epsilon - Q(sign, 4 * n))
                    self.assertEqual(result.codes[0][1], Q(int(sign == -1)))


if __name__ == "__main__":
    unittest.main()
