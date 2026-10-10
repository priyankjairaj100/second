"""Small rational software oracles. These are not empirical datasets."""
from fractions import Fraction as Q
import itertools
import unittest
from unittest.mock import patch

import numpy as np

from research_v39.feature_primal_ball import certify_feature_primal_ball, assess_feature_primal_ball
from research_v35.exact_gram import accumulate
from research_v37.direct_gram_ball import certify_exact_gram_ball, DirectGramBallUnresolved
from src.primal_certificate_v30 import PrimalBudget, PrimalUnresolved
from tests.test_direct_gram_v35 import oracle

BUDGET = PrimalBudget(max_workspace_bytes=32 * 2**20, max_work_units=1_000_000)


class FeaturePrimalBallTests(unittest.TestCase):
    def test_point_matches_independent_rational_oracle_and_direct_gram(self):
        weights = np.array([[2.6, .21, -.11], [-.3, 1.7, .06]])
        for features in (np.array([[.9, -.3], [.4, .7], [-.5, .2]]), np.empty((3, 0))):
            answer = certify_feature_primal_ball(weights, features, features,
                ridge=Q(3, 7), normalization=256, budget=BUDGET)
            gram = accumulate(features, source_id='fixture', normalization=256)
            direct = certify_exact_gram_ball(weights, gram, ridge=Q(3, 7), budget=BUDGET)
            np.testing.assert_array_equal(answer.codes, oracle(weights, features, ridge=Q(3, 7)))
            np.testing.assert_array_equal(answer.codes, direct.codes)
            self.assertEqual(answer.diagnostics['row_build']['source_sha256'], direct.native_source_sha256)

    def test_nonzero_box_acceptance_matches_every_rational_corner(self):
        weights = np.array([[2.6, .21]])
        lower = np.array([[.09], [.19]])
        upper = lower + .00001
        answer = certify_feature_primal_ball(weights, lower, upper,
            ridge=10, normalization=256, budget=BUDGET)
        for choices in itertools.product((0, 1), repeat=2):
            features = np.array([[upper[i, 0] if choices[i] else lower[i, 0]] for i in range(2)])
            np.testing.assert_array_equal(answer.codes, oracle(weights, features))
        with self.assertRaises(ValueError):
            answer.codes.flags.writeable = True

    def test_exact_ties_use_shared_interval_fallback(self):
        weights = np.array([[.5, 1.5, 7.], [-.5, -1.5, 7.]])
        features = np.zeros((3, 2))
        answer = certify_feature_primal_ball(weights, features, features, ridge=1, budget=BUDGET)
        np.testing.assert_array_equal(answer.codes, [[0., 1., 7.], [-1., -2., 7.]])
        self.assertEqual(answer.diagnostics['rows']['fallback_rows'], 2)

    def test_unresolved_interval_never_returns_partial_codes(self):
        with patch('src.primal_certificate_v30._rows_native', side_effect=PrimalUnresolved('fixture refusal')):
            with self.assertRaises(DirectGramBallUnresolved):
                certify_feature_primal_ball(np.array([[.5, 1.5, 7.]]), np.zeros((3, 2)),
                    np.zeros((3, 2)), ridge=1, budget=BUDGET)

    def test_admission_precedes_gram_formation(self):
        with patch('src.primal_certificate_v30._gram_bounds') as gram:
            with self.assertRaises(PrimalUnresolved):
                certify_feature_primal_ball(np.ones((2, 3)), np.ones((3, 4)), np.ones((3, 4)),
                    ridge=1, budget=PrimalBudget(max_work_units=1))
            gram.assert_not_called()

    def test_budget_grows_with_tokens_and_keeps_two_row_passes(self):
        a = assess_feature_primal_ball(rows=2, width=3, tokens=0, budget=BUDGET)
        b = assess_feature_primal_ball(rows=2, width=3, tokens=5, budget=BUDGET)
        self.assertEqual(b['work_units'] - a['work_units'], 45)
        self.assertEqual(b['explicit_array_bytes'] - a['explicit_array_bytes'], 480)
        self.assertEqual(b['admitted_full_row_passes'], 2)

    def test_invalid_box_or_scale_is_rejected(self):
        weights, features = np.ones((1, 2)), np.ones((2, 2))
        for lower, upper, scale in ((features + 1, features, None),
                                     (features, features, (123.,))):
            with self.assertRaises(ValueError):
                certify_feature_primal_ball(weights, lower, upper, scale, ridge=1, budget=BUDGET)


if __name__ == '__main__':
    unittest.main()
