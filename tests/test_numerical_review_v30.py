"""Independent rational fixtures for the V30 algebra, not empirical datasets."""

from fractions import Fraction as Q
from itertools import product
import unittest
from unittest.mock import patch

import numpy as np

from src.exact_core import reverse_ldl


def solve(matrix, rhs):
    """Small exact Gauss-Jordan reference, independent of solver proposals."""
    n = len(rhs)
    work = [list(row) + [value] for row, value in zip(matrix, rhs)]
    for i in range(n):
        pivot = work[i][i]
        if not pivot:
            raise ArithmeticError("fixture pivot is zero")
        work[i] = [value / pivot for value in work[i]]
        for j in range(n):
            if j != i:
                factor = work[j][i]
                work[j] = [a - factor * b for a, b in zip(work[j], work[i])]
    return tuple(row[-1] for row in work)


def dot(a, b):
    return sum((x * y for x, y in zip(a, b)), Q(0))


FEATURES = (
    ((Q(1), Q(2)), (Q(-1), Q(3)), (Q(2), Q(0))),
    ((Q(0), Q(0)), (Q(0), Q(0)), (Q(0), Q(0))),
    ((Q(1, 4), Q(-3, 8), Q(2)),
     (Q(1, 2), Q(-3, 4), Q(4)),
     (Q(-1), Q(0), Q(1, 8)),
     (Q(3), Q(1, 2), Q(-1, 4))),
)


class IndependentPrimalAlgebraTests(unittest.TestCase):
    def test_primal_dual_and_reverse_schur_coefficients_agree_exactly(self):
        for x in FEATURES:
            d, tokens = len(x), len(x[0])
            gram = tuple(tuple(dot(a, b) for b in x) for a in x)
            for beta in (Q(1, 8), Q(1), Q(7, 3)):
                with self.subTest(width=d, tokens=tokens, beta=beta):
                    metric = tuple(tuple(gram[h][j] + beta * int(h == j)
                                         for j in range(d)) for h in range(d))
                    factors = reverse_ldl(metric)
                    for i in range(d):
                        suffix = tuple(tuple(metric[h][j] for j in range(i, d))
                                       for h in range(i, d))
                        y = solve(suffix, tuple(Q(int(k == 0)) for k in range(d - i)))
                        token_metric = tuple(tuple(
                            beta * int(s == t) + sum((x[k][s] * x[k][t]
                                                     for k in range(i, d)), Q(0))
                            for t in range(tokens)) for s in range(tokens))
                        coefficient = solve(token_metric, x[i])
                        pushed = tuple(sum((x[k][t] * y[k - i] for k in range(i, d)), Q(0))
                                       for t in range(tokens))
                        self.assertEqual(coefficient, pushed)
                        for h in range(i):
                            primal = dot(gram[h][i:], y)
                            dual = dot(x[h], coefficient)
                            self.assertEqual(primal, dual)
                            self.assertEqual(primal, factors.L[i][h])

    def test_ridge_cross_response_bound_contains_exact_error(self):
        for x in FEATURES:
            d = len(x)
            gram = tuple(tuple(dot(a, b) for b in x) for a in x)
            for beta in (Q(1, 8), Q(1), Q(7, 3)):
                for i in range(1, d):
                    matrix = tuple(tuple(gram[h][j] + beta * int(h == j)
                                         for j in range(i, d)) for h in range(i, d))
                    target = tuple(Q(int(k == 0)) for k in range(d - i))
                    exact = solve(matrix, target)
                    for offset in (Q(-1, 3), Q(0), Q(5, 7)):
                        proposal = tuple(v + (k + 1) * offset for k, v in enumerate(exact))
                        residual = tuple(target[k] - dot(row, proposal)
                                         for k, row in enumerate(matrix))
                        for h in range(i):
                            error = dot(gram[h][i:], tuple(a - b for a, b in zip(exact, proposal)))
                            bound_squared = gram[h][h] * dot(residual, residual) / (4 * beta)
                            self.assertLessEqual(error * error, bound_squared)

    def test_cross_response_constant_is_sharp(self):
        # beta=1, x_h=2, X_suffix=1 gives |K_hS B^-1|=1.
        beta, k_hh, k_hs, suffix = Q(1), Q(4), Q(2), ((Q(2),),)
        response = solve(suffix, (k_hs,))[0]
        self.assertEqual(response * response, k_hh / (4 * beta))

    def test_primal_native_and_python_enclose_correlated_gram_realizations(self):
        import src.primal_certificate_v30 as primal
        lower = np.array([[.25, -.5], [1., .125], [-.25, .75]])
        upper = lower + .0625
        beta = Q(1, 3)
        primal.prepare_primal_native()
        # Deliberately wrong proposals must remain harmless after residual checks.
        def wrong_proposal(nominal, inverse, i, beta_float):
            return np.arange(1., len(nominal) - i + 1.) / 8., False
        for backend in ('native', 'python'):
            with patch.object(primal, '_suffix_proposal', side_effect=wrong_proposal):
                evidence = primal._coefficient_bounds(lower, upper, beta,
                                                     arithmetic_backend=backend)
            for mask in product((False, True), repeat=lower.size):
                x = np.where(np.array(mask).reshape(lower.shape), upper, lower)
                exact_x = tuple(tuple(Q.from_float(float(value)) for value in row) for row in x)
                gram = tuple(tuple(dot(a, b) for b in exact_x) for a in exact_x)
                for i in range(1, len(x)):
                    matrix = tuple(tuple(gram[h][j] + beta * int(h == j)
                                         for j in range(i, len(x))) for h in range(i, len(x)))
                    y = solve(matrix, tuple(Q(int(k == 0)) for k in range(len(x) - i)))
                    for h in range(i):
                        coefficient = dot(gram[h][i:], y)
                        center = Q.from_float(float(evidence.centers[i, h]))
                        radius = Q.from_float(float(evidence.radii[i, h]))
                        self.assertLessEqual(abs(coefficient - center), radius)


if __name__ == "__main__":
    unittest.main()
