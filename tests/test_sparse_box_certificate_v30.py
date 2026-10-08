"""Exact software fixtures and refusal tests; no empirical dataset or model run."""
from fractions import Fraction as Q
from dataclasses import replace
import unittest
from unittest.mock import patch

import numpy as np

import src.sparse_box_certificate_v30 as module
from src.low_rank_certified import _exact_solve
from src.token_box_certificate import TokenBoxUnresolved
from tests.test_native_box_v26 import corners, oracle, rational


class SparseCertificateTests(unittest.TestCase):
    def setUp(self):
        self.weights = np.array([[.21, 2.6]])
        self.lower = np.ones((2, 1))
        self.upper = self.lower+1e-6
        self.options = dict(ridge=Q(1, 1_000_000), normalization=1)

    def certify(self, **kwargs):
        return module.certify_sparse_ball_dyadic_box(
            self.weights, self.lower, self.upper, **self.options, **kwargs)

    def test_requested_coordinate_matches_all_exact_corners(self):
        with patch.object(module.preconditioned, '_coefficient_bounds',
                          side_effect=AssertionError('no eager preconditioning')), \
             patch.object(module.preconditioned, 'certify_preconditioned_dyadic_box',
                          side_effect=AssertionError('no universal fallback')), \
             patch.object(module.preconditioned, '_preconditioned_error',
                          wraps=module.preconditioned._preconditioned_error) as checks:
            result = self.certify()
        self.assertEqual(checks.call_count, 1)
        self.assertEqual(result.preconditioner_requested_coordinates, (1,))
        self.assertEqual(result.preconditioner_verified_coordinates, (1,))
        self.assertEqual(result.coefficient_suffix_coordinates_visited, 1)
        self.assertEqual(result.preconditioner_rounds, 1)
        self.assertEqual(result.preconditioned_interval_certified_rows, 1)
        self.assertEqual(result.unresolved_coordinate_rounds, (((0, 1),),))
        self.assertFalse(result.python_universal_fallback)
        self.assertEqual(result.point_exact_decisions, 0)
        for features in corners(self.lower, self.upper):
            np.testing.assert_array_equal(result.codes, oracle(self.weights, features, **self.options))
        for alpha in (.125, .5, .875):
            features = self.lower+alpha*(self.upper-self.lower)
            np.testing.assert_array_equal(result.codes, oracle(self.weights, features, **self.options))
        with self.assertRaises(ValueError):
            result.codes.flags.writeable = True

    def test_first_ball_and_ridge_paths_equal_v28(self):
        weights = np.array([[.2, 7.], [.5, 7.], [-.2, 7.]])
        lower, upper = np.array([[0.], [1.]]), np.array([[0.], [1.+1e-8]])
        expected = module.previous.certify_ball_dyadic_box(
            weights, lower, upper, ridge=10, normalization=3, allow_python_fallback=False)
        with patch.object(module, '_requested_components', side_effect=AssertionError('no stronger check')):
            actual = module.certify_sparse_ball_dyadic_box(weights, lower, upper, ridge=10, normalization=3)
        np.testing.assert_array_equal(actual.codes, expected.codes)
        self.assertEqual(actual.first_ball_certified_rows, 2)
        self.assertEqual(actual.ridge_interval_certified_rows, 1)
        self.assertEqual(actual.preconditioner_rounds, 0)
        self.assertEqual(actual.preconditioner_requested_coordinates, ())
        self.assertEqual([x['policy'] for x in actual.native_passes], ['ridge', 'shared_ridge'])

    def test_coordinate_and_round_budgets_refuse_before_stronger_work(self):
        for field in ('max_preconditioned_coordinates', 'max_rounds'):
            budget = replace(module.SparseCertificateBudget(), **{field: 0})
            with patch.object(module, '_requested_components', side_effect=AssertionError('no expensive check')):
                with self.assertRaises(TokenBoxUnresolved) as caught:
                    self.certify(budget=budget)
            self.assertIn(caught.exception.native_diagnostics['resource_refusal']['reason'],
                          ('coordinate_limit', 'round_limit'))
            self.assertEqual(caught.exception.native_diagnostics['requested_coordinates'], [])

    def test_workspace_refusal_precedes_numerical_scan_or_compilation(self):
        with patch.object(module, '_matrix', side_effect=AssertionError('no scan')), \
             patch.object(module.ball, 'prepare_native_ball', side_effect=AssertionError('no compilation')), \
             patch.object(module.boxes, '_box_coefficients', side_effect=AssertionError('no allocation')):
            with self.assertRaises(TokenBoxUnresolved) as caught:
                self.certify(budget=replace(module.SparseCertificateBudget(), max_workspace_bytes=1))
        diag = caught.exception.native_diagnostics
        self.assertEqual(diag['resource_refusal']['reason'], 'workspace_allowance')
        self.assertEqual(diag['work_units_reserved'], 0)
        self.assertEqual(diag['passes'], [])

    def test_initial_work_refusal_precedes_compilation_and_coefficient_construction(self):
        with patch.object(module.ball, 'prepare_native_ball', side_effect=AssertionError('no compilation')), \
             patch.object(module.boxes, '_box_coefficients', side_effect=AssertionError('no allocation')):
            with self.assertRaises(TokenBoxUnresolved) as caught:
                self.certify(budget=replace(module.SparseCertificateBudget(), max_work_units=0))
        diag = caught.exception.native_diagnostics
        self.assertEqual(diag['resource_refusal']['operation'], 'initial_ball_and_ridge')
        self.assertEqual(diag['work_units_reserved'], 0)

    def test_sweep_and_row_retry_reservations_precede_expensive_checks(self):
        # The fixture needs 34 initial units, 14 ridge units, 2 sweep units, and 14 retry units.
        for limit, refused_operation in ((49, 'requested_preconditioner_sweep'),
                                          (63, 'mixed_component_rows')):
            with patch.object(module, '_requested_components', side_effect=AssertionError('no stronger computation')):
                with self.assertRaises(TokenBoxUnresolved) as caught:
                    self.certify(budget=replace(module.SparseCertificateBudget(), max_work_units=limit))
            diag = caught.exception.native_diagnostics
            self.assertEqual(diag['resource_refusal']['operation'], refused_operation)
            self.assertLessEqual(diag['work_units_reserved'], limit)
            self.assertEqual(diag['preconditioner_rounds'], 0)
        result = self.certify(budget=replace(module.SparseCertificateBudget(), max_work_units=64))
        self.assertEqual(result.work_units_reserved, 64)
        self.assertEqual(sum(x['units'] for x in result.resource_reservations), 64)

    def test_failed_preconditioner_is_not_recomputed(self):
        with patch.object(module.preconditioned, '_preconditioned_error', return_value=None) as checks:
            with self.assertRaises(TokenBoxUnresolved) as caught:
                self.certify()
        self.assertEqual(checks.call_count, 1)
        diag = caught.exception.native_diagnostics
        self.assertEqual(diag['requested_coordinates'], [1])
        self.assertEqual(diag['verified_coordinates'], [])
        self.assertEqual(diag['preconditioner_rounds'], 1)
        self.assertEqual(len(diag['unresolved_coordinate_rounds']), 2)

    def test_real_endpoint_disagreement_refuses_without_point_fallback(self):
        upper = np.array([[4.], [1.]])
        self.assertFalse(np.array_equal(oracle(self.weights, self.lower, **self.options),
                                       oracle(self.weights, upper, **self.options)))
        with patch.object(module.ball, 'native_ball_quantize_dyadic_rows',
                          side_effect=AssertionError('no point fallback')):
            with self.assertRaises(TokenBoxUnresolved):
                module.certify_sparse_ball_dyadic_box(self.weights, self.lower, upper, **self.options)

    def test_pairing_uses_existing_proposals_not_nominal_updates(self):
        lower = np.array([[.9, -.3], [.4, .7], [-.5, .2]])
        upper = lower+1e-8
        proposals, _ = module.boxes._box_coefficients(lower, upper, Q(30))
        # Perturb every proposal so equality with reconstructed nominal values cannot pass accidentally.
        proposals = proposals + .001
        with patch.object(module.preconditioned, '_preconditioned_error',
                          wraps=module.preconditioned._preconditioned_error) as checks:
            evidence, visited = module._requested_components(lower, upper, Q(30), proposals, (1,))
        self.assertEqual(visited, 2)
        self.assertEqual(checks.call_count, 1)
        certificate = evidence[1]
        np.testing.assert_array_equal(certificate.proposal, proposals[1])
        for features in corners(lower, upper):
            suffix = [[rational(x) for x in row] for row in features[1:]]
            gram = [[sum((row[j]*row[k] for row in suffix), Q(0))+(Q(30) if j == k else 0)
                     for k in range(2)] for j in range(2)]
            exact = _exact_solve(gram, [rational(x) for x in features[1]])
            for k in range(2):
                self.assertLessEqual(abs(exact[k]-rational(certificate.proposal[k])),
                                     rational(certificate.radius[k]))
        for vector in (certificate.proposal, certificate.radius):
            with self.assertRaises(ValueError):
                vector.flags.writeable = True

    def test_complete_rows_survive_and_failed_partial_rows_are_discarded(self):
        weights = np.array([[.2, 7.], [.5, 7.], [-.2, 7.]])
        lower, upper = np.array([[0.], [1.]]), np.array([[0.], [1.+1e-8]])
        actual = module.previous._ball_pass
        def poisoned(*args):
            codes, failed, receipt = actual(*args)
            codes[failed >= 0] = np.nan
            return codes, failed, receipt
        with patch.object(module.previous, '_ball_pass', side_effect=poisoned):
            result = module.certify_sparse_ball_dyadic_box(weights, lower, upper, ridge=10, normalization=3)
        np.testing.assert_array_equal(result.codes, oracle(weights, lower))
        self.assertEqual(result.native_passes[1]['global_row'], 1)
        self.assertEqual(result.native_passes[1]['rows_evaluated'], 1)

    def test_singleton_empty_rank_noncontiguous_and_unaligned_inputs(self):
        weights = np.array([[.2, 7.], [.5, 7.], [-.2, 7.]])
        lower = np.array([[0.], [1.]])
        def unaligned(value):
            result = np.ndarray(value.shape, dtype=np.float64,
                                buffer=bytearray(value.nbytes+1), offset=1)
            result[:] = value
            result.flags.writeable = False
            return result
        cases = ((weights, lower, lower), (weights[::-1], lower, lower+1e-8),
                 (unaligned(weights), unaligned(lower), unaligned(lower)),
                 (weights, np.empty((2, 0)), np.empty((2, 0))))
        for w, lo, hi in cases:
            before = tuple(value.tobytes() for value in (w, lo, hi))
            result = module.certify_sparse_ball_dyadic_box(w, lo, hi, ridge=10, normalization=3)
            np.testing.assert_array_equal(result.codes, oracle(w, lo))
            self.assertEqual(before, tuple(value.tobytes() for value in (w, lo, hi)))

    def test_adaptive_rounds_preserve_previous_component_evidence(self):
        weights = np.array([[.2, .2, .2, 7.]])
        lower, upper = np.ones((4, 1)), np.ones((4, 1))+1e-6
        with patch.object(module.preconditioned, '_preconditioned_error',
                          wraps=module.preconditioned._preconditioned_error) as checks:
            result = module.certify_sparse_ball_dyadic_box(weights, lower, upper, **self.options)
        self.assertEqual(checks.call_count, 2)
        self.assertEqual(result.preconditioner_requested_coordinates, (1, 2))
        self.assertEqual(result.preconditioner_rounds, 2)
        self.assertEqual(result.unresolved_coordinate_rounds, (((0, 1),), ((0, 2),)))
        # First sweep visits coordinates 3,2,1. Second visits 3,2 without repeating its predecessor check.
        self.assertEqual(result.coefficient_suffix_coordinates_visited, 5)
        for features in corners(lower, upper):
            np.testing.assert_array_equal(result.codes, oracle(weights, features, **self.options))
        with self.assertRaises(TokenBoxUnresolved) as caught:
            module.certify_sparse_ball_dyadic_box(weights, lower, upper, **self.options,
                budget=replace(module.SparseCertificateBudget(), max_rounds=1))
        self.assertEqual(caught.exception.native_diagnostics['resource_refusal']['reason'], 'round_limit')
        self.assertEqual(caught.exception.native_diagnostics['requested_coordinates'], [1])

    def test_union_of_failure_coordinates_shares_one_sweep(self):
        weights = np.array([[.2, .2, .2, 7.], [0., .2, .2, 7.]])
        lower, upper = np.ones((4, 1)), np.ones((4, 1))+1e-6
        with patch.object(module, '_requested_components', wraps=module._requested_components) as sweep:
            result = module.certify_sparse_ball_dyadic_box(weights, lower, upper, **self.options)
        self.assertEqual(sweep.call_count, 1)
        self.assertEqual(result.preconditioner_requested_coordinates, (1, 2))
        self.assertEqual(result.unresolved_coordinate_rounds, (((0, 1), (1, 2)),))
        self.assertEqual(result.coefficient_suffix_coordinates_visited, 3)
        for features in corners(lower, upper):
            np.testing.assert_array_equal(result.codes, oracle(weights, features, **self.options))

    def test_candidate_and_input_validation(self):
        result = self.certify()
        self.assertTrue(self.certify(candidate_codes=result.codes).candidate_checked)
        with self.assertRaises(TokenBoxUnresolved):
            self.certify(candidate_codes=np.zeros_like(self.weights))
        with self.assertRaises(ValueError):
            self.certify(allow_python_fallback=True)
        for value in (True, -1, 1.5):
            with self.assertRaises(ValueError):
                self.certify(max_exact_coordinates=value)
            with self.assertRaises(ValueError):
                module.SparseCertificateBudget(max_work_units=value)
        with self.assertRaises(TypeError):
            self.certify(budget={})
        with self.assertRaises(ValueError):
            module.certify_sparse_ball_dyadic_box(self.weights, self.upper, self.lower, **self.options)
        with self.assertRaises(ValueError):
            self.certify(scale_values=(1.,))
        for name in ('weights', 'lower', 'upper', 'candidate_codes'):
            kwargs = dict(weights=self.weights.copy(), lower=self.lower.copy(), upper=self.upper.copy())
            if name == 'candidate_codes':
                kwargs[name] = self.weights.copy()
            kwargs[name].flat[0] = np.nan
            with self.assertRaises(ValueError):
                module.certify_sparse_ball_dyadic_box(**kwargs, **self.options)

    def test_runtime_guard_remains_active(self):
        with patch.object(module, '_check_runtime', side_effect=RuntimeError('unsupported runtime')):
            with self.assertRaises(RuntimeError):
                self.certify()


if __name__ == '__main__':
    unittest.main()
