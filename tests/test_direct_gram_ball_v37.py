"""Exact software fixtures for a shared kernel; no empirical datasets."""
from fractions import Fraction as Q
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from research_v35.exact_gram import accumulate, add_grams, subtract_gram, dumps, loads
from research_v35.direct_gram import certify_exact_gram
from research_v37.direct_gram_ball import (
    DirectGramBallUnresolved, assess_direct_gram_ball_budget,
    certify_exact_gram_ball, _euclidean_radii,
)
from src import native_ball_quantizer as ball
from src import primal_certificate_v30 as primal
from src.low_rank_certified import LowRankUnresolved
from tests.test_direct_gram_v35 import oracle


class DirectGramBallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.coefficient_build = primal.prepare_primal_native()
        cls.row_build = ball.prepare_native_ball()

    def setUp(self):
        self.weights = np.array([[2.6, .21, -.11], [-.3, 1.7, .06]])
        self.features = np.array([[.9, -.3], [.4, .7], [-.5, .2]])

    def gram(self, features=None, normalization=256):
        return accumulate(self.features if features is None else features,
                          source_id='software-fixture', normalization=normalization)

    def test_independent_rational_oracle_and_old_interval_backend(self):
        for features in (self.features, np.empty((3, 0))):
            result = certify_exact_gram_ball(self.weights, self.gram(features), ridge=Q(3, 7))
            old = certify_exact_gram(self.weights, self.gram(features), ridge=Q(3, 7))
            np.testing.assert_array_equal(result.codes, oracle(self.weights, features, ridge=Q(3, 7)))
            np.testing.assert_array_equal(result.codes, old.codes)
            self.assertEqual(result.interval_decisions, self.weights.size)
            self.assertEqual(result.point_exact_decisions, 0)
            self.assertEqual(result.virtual_rank, 3)
            self.assertEqual(result.normalization_numerator, 256)
            with self.assertRaises(ValueError):
                result.codes.flags.writeable = True

    def test_deleted_gram_retains_original_normalization(self):
        retained = accumulate(self.features[:, :1], source_id='retained', normalization=256)
        deleted = accumulate(self.features[:, 1:], source_id='deleted', normalization=256)
        repaired = subtract_gram(add_grams(retained, deleted), deleted)
        result = certify_exact_gram_ball(self.weights, repaired, ridge=Q(1, 100))
        np.testing.assert_array_equal(result.codes, oracle(
            self.weights, self.features[:, :1], ridge=Q(1, 100)))
        self.assertEqual(result.normalization_numerator, 256)
        self.assertEqual(result.tokens, 1)

    def test_ball_tie_refusals_receive_exact_interval_fallback(self):
        weights = np.array([[.5, 1.5, 7.], [-.5, -1.5, 7.]])
        result = certify_exact_gram_ball(weights, self.gram(np.zeros((3, 2))), ridge=1)
        np.testing.assert_array_equal(result.codes, [[0., 1., 7.], [-1., -2., 7.]])
        self.assertEqual(result.fallback_rows, 2)
        self.assertEqual(result.fallback_row_indices, (0, 1))
        self.assertEqual(result.ball_failed_coordinates, (0, 0))
        self.assertEqual(result.native_prefix_certified_decisions, 0)
        self.assertEqual(result.native_attempted_decisions, 2)
        self.assertEqual(result.fallback_certified_decisions, 6)

    def test_failed_interval_fallback_returns_no_model(self):
        weights = np.array([[.5, 1.5, 7.]])
        with patch('src.primal_certificate_v30._rows_native',
                   side_effect=primal.PrimalUnresolved('fixture interval refusal')):
            with self.assertRaises(DirectGramBallUnresolved) as error:
                certify_exact_gram_ball(weights, self.gram(np.zeros((3, 2))), ridge=1)
        self.assertEqual(error.exception.native_ball_diagnostics['fallback_rows'], 1)
        self.assertIsNone(error.exception.native_ball_diagnostics['fallback_native_elapsed_ns'])
        self.assertIsNone(error.exception.native_ball_diagnostics['fallback_attempted_decisions'])
        self.assertIsNone(error.exception.native_ball_diagnostics['fallback_certified_decisions'])
        self.assertIn('fixture interval refusal', str(error.exception))

    def test_euclidean_radii_cover_exact_sum_of_squares(self):
        values = np.array([[0., 0., 0.], [.1, .2, .3],
                           [np.nextafter(0., 1.), 1e-200, 0.], [1e100, -0., .7]])
        rho = _euclidean_radii(values)
        for row, bound in zip(values, rho):
            self.assertGreaterEqual(Q.from_float(bound)**2,
                sum((Q.from_float(float(x))**2 for x in row), Q(0)))
        self.assertEqual(rho[0], 0.)
        with self.assertRaises(ValueError):
            _euclidean_radii(np.array([[-1.]]))
        with self.assertRaises(LowRankUnresolved):
            with np.errstate(over='ignore'):
                _euclidean_radii(np.array([[1e200]]))

    def test_coefficients_computed_once_even_with_refused_rows(self):
        from research_v35 import direct_gram
        weights = np.array([[.5, 1.5, 7.], [-.5, -1.5, 7.]])
        with patch('research_v35.direct_gram._coefficient_bounds',
                   wraps=direct_gram._coefficient_bounds) as coefficient:
            result = certify_exact_gram_ball(weights, self.gram(np.zeros((3, 2))), ridge=1)
        self.assertEqual(coefficient.call_count, 1)
        self.assertEqual(result.fallback_rows, 2)

    def test_kernel_provenance_keeps_ball_and_coefficient_builds_distinct(self):
        result = certify_exact_gram_ball(self.weights, self.gram(), ridge=10)
        self.assertEqual(result.native_source_sha256, self.row_build['source_sha256'])
        self.assertEqual(result.native_binary_sha256, self.row_build['binary_sha256'])
        self.assertEqual(result.coefficient_native_source_sha256, self.coefficient_build['source_sha256'])
        self.assertEqual(result.coefficient_native_binary_sha256, self.coefficient_build['binary_sha256'])
        self.assertNotEqual(result.native_source_sha256, result.coefficient_native_source_sha256)
        self.assertEqual(result.native_flags, result.coefficient_native_flags)
        self.assertIn('-fno-fast-math', result.native_flags)
        self.assertIn('-ffp-contract=off', result.native_flags)
        self.assertEqual(result.compile_elapsed_ns, 0)
        self.assertEqual(result.native_certified_rows + result.fallback_rows, len(self.weights))

    def test_resource_admission_counts_both_passes_and_precedes_work(self):
        limits = primal.PrimalBudget(max_work_units=6_000_000_000,
                                     max_workspace_bytes=512*1024*1024)
        report = assess_direct_gram_ball_budget(rows=2304, width=768, budget=limits)
        self.assertTrue(report['admitted'])
        self.assertEqual(report['admitted_full_row_passes'], 2)
        self.assertEqual(report['work_units'], 768**3 + 2*2304*768**2 + 2*2304*16 + 3*768**2)
        gram = self.gram()
        with patch('research_v37.direct_gram_ball.to_float64_enclosure', side_effect=AssertionError('no Gram')):
            with patch('src.primal_certificate_v30.prepare_primal_native', side_effect=AssertionError('no compile')):
                with self.assertRaises(DirectGramBallUnresolved):
                    certify_exact_gram_ball(self.weights, gram, ridge=1,
                                           budget=primal.PrimalBudget(max_work_units=1))

    def test_inputs_trust_and_candidate_contracts(self):
        gram = self.gram()
        result = certify_exact_gram_ball(self.weights, gram, ridge=10)
        checked = certify_exact_gram_ball(self.weights, gram, ridge=10, candidate_codes=result.codes)
        self.assertTrue(checked.candidate_checked)
        with self.assertRaises(DirectGramBallUnresolved):
            certify_exact_gram_ball(self.weights, gram, ridge=10, candidate_codes=np.zeros_like(self.weights))
        with self.assertRaises(ValueError):
            certify_exact_gram_ball(self.weights, loads(dumps(gram)), ridge=10)
        with self.assertRaises(ValueError):
            certify_exact_gram_ball(self.weights, gram, [1., 1.], ridge=10)
        with self.assertRaises(TypeError):
            certify_exact_gram_ball(self.weights, gram, ridge=.1)
        with self.assertRaises(ValueError):
            certify_exact_gram_ball(self.weights, gram, ridge=0)
        invalid = self.weights.copy(); invalid[0, 0] = np.nan
        with self.assertRaises(ValueError):
            certify_exact_gram_ball(invalid, gram, ridge=1)

    def test_native_runtime_failure_does_not_trigger_numerical_fallback(self):
        fake = SimpleNamespace(nb_run=lambda *args: 1)
        with patch('src.native_ball_quantizer._NATIVE', fake):
            with patch('src.primal_certificate_v30._rows_native', side_effect=AssertionError('no fallback')):
                with self.assertRaisesRegex(DirectGramBallUnresolved, 'runtime or allocation failure'):
                    certify_exact_gram_ball(self.weights, self.gram(), ridge=10)

    def test_wrong_proposals_and_tiny_beta_fail_closed(self):
        def broken(nominal, inverse, i, beta):
            return np.full(len(nominal)-i, 1e10), True
        with patch('src.primal_certificate_v30._suffix_proposal', side_effect=broken):
            with self.assertRaises(DirectGramBallUnresolved):
                certify_exact_gram_ball(self.weights, self.gram(), ridge=10)
        with self.assertRaises(DirectGramBallUnresolved):
            certify_exact_gram_ball(self.weights, self.gram(), ridge=Q(1, 1 << 1000))


if __name__ == '__main__':
    unittest.main()
