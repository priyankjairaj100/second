"""Software fixtures for streamed universal certificates."""
import itertools
import unittest
from unittest.mock import patch
import numpy as np

from research_v40.streamed_primal_ball import certify_streamed_primal_ball as solve, assess_streamed
from src.primal_certificate_v30 import PrimalBudget, PrimalUnresolved
from tests.test_direct_gram_v35 import oracle

BUDGET = PrimalBudget(max_work_units=10**7, max_workspace_bytes=32 * 2**20)


class StreamedPrimalTests(unittest.TestCase):
    def test_partitioned_points_match_independent_rational_oracle(self):
        weights = np.array([[2.6, .21, -.11], [-.3, 1.7, .06]])
        features = np.array([[.9, -.3, .7], [.4, .7, -.2], [-.5, .2, 1.1]])
        for split in (1, 2):
            parts = [features[:, :split], features[:, split:]]
            answer = solve(weights, ((x, x) for x in parts), total_tokens=3, block_tokens=2,
                           ridge=10, normalization=256, budget=BUDGET)
            np.testing.assert_array_equal(answer.codes, oracle(weights, features))
            self.assertEqual(answer.diagnostics['blocks'], 2)

    def test_nonpoint_boxes_cover_every_small_corner(self):
        weights, lo = np.array([[2.6, .21]]), np.array([[.09, .21], [.19, .11]])
        hi = lo + .00001
        answer = solve(weights, ((lo[:, i:i+1], hi[:, i:i+1]) for i in range(2)),
                       total_tokens=2, block_tokens=1, ridge=10, normalization=256, budget=BUDGET)
        for selector in itertools.product((False, True), repeat=4):
            features = np.where(np.array(selector).reshape(2, 2), hi, lo)
            np.testing.assert_array_equal(answer.codes, oracle(weights, features))

    def test_zero_and_empty_stream_preserve_exact_ties(self):
        weights = np.array([[.5, 1.5, 7.]])
        for total, blocks in [(0, []), (2, [(np.zeros((3, 1)), np.zeros((3, 1))) for _ in range(2)])]:
            answer = solve(weights, blocks, total_tokens=total, block_tokens=1, ridge=1, budget=BUDGET)
            np.testing.assert_array_equal(answer.codes, [[0., 1., 7.]])
            self.assertEqual(answer.diagnostics['rows']['fallback_rows'], 1)

    def test_incorrect_token_totals_return_no_codes(self):
        values, weights = np.ones((2, 1)), np.ones((1, 2))
        for total, blocks in [(0, [(values, values)]), (2, [(values, values)]),
                              (1, [(np.empty((2, 0)), np.empty((2, 0)))])]:
            with self.assertRaises(ValueError):
                solve(weights, blocks, total_tokens=total, block_tokens=1, ridge=1, budget=BUDGET)

    def test_memory_is_independent_of_total_tokens_above_block_limit(self):
        a = assess_streamed(rows=2, width=3, tokens=8, block_tokens=4, budget=BUDGET)
        b = assess_streamed(rows=2, width=3, tokens=800, block_tokens=4, budget=BUDGET)
        self.assertEqual(a['explicit_array_bytes'], b['explicit_array_bytes'])
        self.assertGreater(b['work_units'], a['work_units'])

    def test_budget_refusal_does_not_consume_stream(self):
        stream = iter([(np.ones((2, 1)), np.ones((2, 1)))])
        with patch('src.primal_certificate_v30._gram_bounds') as gram:
            with self.assertRaises(PrimalUnresolved):
                solve(np.ones((1, 2)), stream, total_tokens=1, block_tokens=1,
                      ridge=1, budget=PrimalBudget(max_work_units=1))
            gram.assert_not_called()
        self.assertEqual(next(stream)[0].shape, (2, 1))

    def test_explicit_block_count_limits_are_enforced(self):
        weights, x = np.ones((1, 2)), np.ones((2, 1))
        with self.assertRaises(ValueError):
            solve(weights, [(x, x), (x, x)], total_tokens=2, block_tokens=2,
                  max_blocks=1, ridge=1, budget=BUDGET)
        with self.assertRaises(ValueError):
            assess_streamed(rows=1, width=2, tokens=3, block_tokens=1, max_blocks=2, budget=BUDGET)


if __name__ == '__main__':
    unittest.main()
