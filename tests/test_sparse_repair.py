"""Arithmetic correctness checks, not empirical quantization experiments."""

import unittest
from dataclasses import replace
from fractions import Fraction as F

from src.exact_core import sequential_oracle, reverse_ldl
from src.sparse_repair import sparse_repair


def solve(matrix, rhs):
    """Independent dense Gaussian elimination for conditional minimization."""
    a = [[F(x) for x in row] + [F(y)] for row, y in zip(matrix, rhs)]
    n = len(a)
    for i in range(n):
        pivot_row = next(j for j in range(i, n) if a[j][i])
        a[i], a[pivot_row] = a[pivot_row], a[i]
        pivot = a[i][i]
        a[i] = [x / pivot for x in a[i]]
        for j in range(n):
            if j != i:
                scale = a[j][i]
                a[j] = [x - scale * y for x, y in zip(a[j], a[i])]
    return [row[-1] for row in a]


def independent_quantizer(weights, hessian, grids):
    """Minimize the quadratic over the unrounded suffix at every step."""
    result = []
    for raw_row in weights:
        row = tuple(map(F, raw_row))
        codes = []
        for i in range(len(row)):
            suffix = [h[i:] for h in hessian[i:]]
            rhs = [-sum(F(hessian[j][k]) * (row[k] - codes[k]) for k in range(i))
                   for j in range(i, len(row))]
            best_error = solve(suffix, rhs)[0]
            desired = row[i] - best_error
            code = min(grids[i], key=lambda x: (abs(F(x) - desired), F(x)))
            codes.append(F(code))
        result.append(tuple(codes))
    return tuple(result)


class SparseRepairTests(unittest.TestCase):
    def setUp(self):
        self.weights = ((F(1, 2), F(3, 5), F(-7, 10)),
                        (F(2, 3), F(-2, 5), F(9, 10)))
        self.old_h = ((3, 0, 0), (0, 3, 0), (0, 0, 3))
        self.new_h = ((5, 1, -1), (1, 4, 1), (-1, 1, 3))
        self.grids = ((-1, 0, 1),) * 3
        self.old = sequential_oracle(self.weights, self.old_h, self.grids)
        self.target_b = reverse_ldl(self.new_h).B

    def exact_envelope(self, row_index, coordinate):
        row, old_q = self.weights[row_index], self.old.rows[row_index].codes
        value = -sum((self.target_b[coordinate][h] - self.old.factors.B[coordinate][h]) *
                     (row[h] - old_q[h]) for h in range(coordinate))
        return value, value

    def test_fallback_matches_independent_quadratic_oracle(self):
        result = sparse_repair(self.weights, self.old, self.target_b)
        self.assertEqual(result.codes, independent_quantizer(self.weights, self.new_h, self.grids))
        self.assertEqual(result.work.exact_fallbacks, 6)
        self.assertTrue(result.used_envelopes_verified_by_module)

    def test_exact_envelopes_inject_changed_codes(self):
        result = sparse_repair(self.weights, self.old, self.target_b, self.exact_envelope,
                               verify_envelopes=True)
        self.assertEqual(result.codes, independent_quantizer(self.weights, self.new_h, self.grids))
        self.assertEqual(result.work.exact_fallbacks, 0)
        self.assertGreater(result.work.changed_codes, 0)
        self.assertGreater(result.work.injection_terms, 0)
        self.assertTrue(result.used_envelopes_verified_by_module)
        self.assertFalse(result.target_provenance_verified_by_module)

    def test_ambiguous_envelopes_trigger_exact_fallback(self):
        result = sparse_repair(self.weights, self.old, self.target_b, lambda _r, _i: (-100, 100))
        self.assertEqual(result.codes, independent_quantizer(self.weights, self.new_h, self.grids))
        self.assertEqual(result.work.exact_fallbacks, 6)

    def test_tie_to_lower_and_saturated_cells(self):
        weights = ((F(1, 2), -10, 10),)
        old = sequential_oracle(weights, self.old_h, self.grids)
        result = sparse_repair(weights, old, old.factors.B, lambda _r, i: (0, 0) if i == 0 else (-1, 1))
        self.assertEqual(result.codes, ((F(0), F(-1), F(1)),))
        self.assertEqual(result.work.exact_fallbacks, 0)
        self.assertFalse(result.used_envelopes_verified_by_module)

    def test_singleton_grid_accepts_all_intervals(self):
        weights, h, grids = ((3,),), ((1,),), ((7,),)
        old = sequential_oracle(weights, h, grids)
        result = sparse_repair(weights, old, ((0,),), lambda _r, _i: (-1000, 1000))
        self.assertEqual(result.codes, ((F(7),),))
        self.assertEqual(result.work.accepted_envelopes, 1)

    def test_bad_envelope_detected_when_verified(self):
        with self.assertRaisesRegex(ValueError, "excludes"):
            sparse_repair(self.weights, self.old, self.target_b, lambda _r, _i: (1, 2),
                          verify_envelopes=True)

    def test_bad_old_trace_detected(self):
        bad_row = replace(self.old.rows[0], inputs=(F(9),) + self.old.rows[0].inputs[1:])
        bad = replace(self.old, rows=(bad_row, self.old.rows[1]))
        with self.assertRaisesRegex(ValueError, "old trace"):
            sparse_repair(self.weights, bad, self.target_b)

    def test_rejects_nonexact_and_nontriangular_inputs(self):
        for value in (0.0, True):
            with self.subTest(value=value), self.assertRaises(TypeError):
                sparse_repair(self.weights, self.old, self.target_b, lambda _r, _i: (value, 1))
        with self.assertRaisesRegex(ValueError, "lower triangular"):
            sparse_repair(self.weights, self.old, ((1, 0, 0), (0, 0, 0), (0, 0, 0)))

    def test_small_exact_family_against_independent_solver(self):
        # Finite arithmetic branch coverage; no corpus/model or timings.
        for coupling in (-2, -1, 0, 1, 2):
            h = ((5, coupling, 1), (coupling, 5, -1), (1, -1, 5))
            result = sparse_repair(self.weights, self.old, reverse_ldl(h).B)
            self.assertEqual(result.codes, independent_quantizer(self.weights, h, self.grids))


if __name__ == "__main__":
    unittest.main()
