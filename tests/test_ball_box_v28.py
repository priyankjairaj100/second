"""Software fixtures for selecting complete universally certified rows."""
import hashlib
from fractions import Fraction as Q
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

import src.ball_box_certificate_v28 as module
from src.token_box_certificate import TokenBoxUnresolved
from tests.test_native_box_v26 import corners, oracle


class SparseBallBoxTests(unittest.TestCase):
    def setUp(self):
        # Only the middle row has an exact boundary tie in the first coordinate.
        self.weights = np.array([[.2, 7.], [.5, 7.], [-.2, 7.]])
        self.lower = np.array([[0.], [1.]])
        self.upper = np.array([[0.], [1.+1e-8]])

    def test_real_sparse_failure_reuses_coefficients_and_preserves_completed_rows(self):
        with patch.object(module.boxes, '_box_coefficients', wraps=module.boxes._box_coefficients) as ridge, \
             patch.object(module.preconditioned, '_coefficient_bounds', side_effect=AssertionError('no preconditioning needed')), \
             patch.object(module.preconditioned, 'certify_preconditioned_dyadic_box', side_effect=AssertionError('no fallback needed')):
            result = module.certify_ball_dyadic_box(self.weights, self.lower, self.upper,
                ridge=10, normalization=3, allow_python_fallback=False)
        self.assertEqual(ridge.call_count, 1)
        self.assertEqual(result.first_ball_certified_rows, 2)
        self.assertEqual(result.ridge_interval_certified_rows, 1)
        self.assertEqual(result.preconditioned_interval_certified_rows, 0)
        self.assertEqual(result.python_universal_rows, 0)
        self.assertEqual(len(result.native_passes), 2)
        self.assertEqual(result.native_passes[0]['failed_row_indices'], (1,))
        self.assertEqual(result.native_passes[1]['global_row'], 1)
        self.assertEqual(result.native_passes[1]['rows_evaluated'], 1)
        self.assertEqual(result.native_passes[1]['policy'], 'shared_ridge')
        for features in corners(self.lower, self.upper):
            np.testing.assert_array_equal(result.codes, oracle(self.weights, features))
        with self.assertRaises(ValueError):
            result.codes.flags.writeable = True

    def test_successful_ball_rows_never_enter_interval_pass(self):
        weights = self.weights[[0, 2]]
        with patch.object(module.interval, 'prepare_native_box', side_effect=AssertionError('no interval compilation')):
            result = module.certify_ball_dyadic_box(weights, self.lower, self.upper,
                ridge=10, normalization=3, allow_python_fallback=False)
        self.assertEqual(result.first_ball_certified_rows, 2)
        self.assertEqual(len(result.native_passes), 1)
        self.assertEqual(result.interval_source_sha256, '')
        np.testing.assert_array_equal(result.codes, oracle(weights, self.lower))

    def test_failed_partial_rows_are_discarded_even_when_poisoned(self):
        actual = module._ball_pass
        def poisoned(*args):
            codes, failed, receipt = actual(*args)
            codes[failed >= 0] = np.nan
            return codes, failed, receipt
        with patch.object(module, '_ball_pass', side_effect=poisoned):
            result = module.certify_ball_dyadic_box(self.weights, self.lower, self.upper,
                ridge=10, normalization=3, allow_python_fallback=False)
        np.testing.assert_array_equal(result.codes, oracle(self.weights, self.lower))
        self.assertTrue(np.all(np.isfinite(result.codes)))

    def test_preconditioning_only_follows_unresolved_shared_ridge_rows(self):
        weights, lower = np.array([[.21, 2.6]]), np.ones((2, 1))
        upper = lower + 1e-6
        options = dict(ridge=Q(1, 1000000), normalization=1)
        with patch.object(module.boxes, '_box_coefficients', wraps=module.boxes._box_coefficients) as ridge, \
             patch.object(module.preconditioned, '_coefficient_bounds', wraps=module.preconditioned._coefficient_bounds) as preconditioned:
            result = module.certify_ball_dyadic_box(weights, lower, upper,
                allow_python_fallback=False, **options)
        self.assertEqual(ridge.call_count, 1)
        self.assertEqual(preconditioned.call_count, 1)
        self.assertEqual(result.first_ball_certified_rows, 0)
        self.assertEqual(result.ridge_interval_certified_rows, 0)
        self.assertEqual(result.preconditioned_interval_certified_rows, 1)
        self.assertEqual(result.python_universal_rows, 0)
        self.assertEqual([p['policy'] for p in result.native_passes], ['ridge', 'shared_ridge', 'shared_preconditioned'])
        for features in corners(lower, upper):
            np.testing.assert_array_equal(result.codes, oracle(weights, features, **options))

    def test_python_universal_receives_only_remaining_full_width_rows(self):
        actual = module.preconditioned.certify_preconditioned_dyadic_box
        def unresolved(weights, *args):
            return 3, np.full_like(weights, np.nan), dict(native_elapsed_ns=0,
                unresolved_row=0, unresolved_coordinate=0, attempted_decisions=1, certified_decisions=0)
        def checked(weights, lower, upper, scales, **options):
            self.assertEqual(weights.shape, (1, 2))
            np.testing.assert_array_equal(weights, self.weights[[1]])
            self.assertIs(lower, self.lower)
            self.assertIs(upper, self.upper)
            return actual(weights, lower, upper, scales, **options)
        with patch.object(module.interval, '_native_pass', side_effect=unresolved), \
             patch.object(module.preconditioned, 'certify_preconditioned_dyadic_box', side_effect=checked) as fallback, \
             patch.object(module.ball, 'native_ball_quantize_dyadic_rows', side_effect=AssertionError('no uncertain point fallback')):
            result = module.certify_ball_dyadic_box(self.weights, self.lower, self.upper, ridge=10, normalization=3)
        self.assertEqual(fallback.call_count, 1)
        self.assertEqual(result.first_ball_certified_rows, 2)
        self.assertEqual(result.python_universal_rows, 1)
        self.assertTrue(result.python_universal_fallback)
        self.assertGreater(result.fallback_elapsed_ns, 0)
        for receipt in result.native_passes[1:]:
            self.assertEqual(receipt['failed_row_indices'], (1,))
            self.assertEqual(receipt['unresolved_row'], 1)
            self.assertEqual(receipt['local_unresolved_row'], 0)
        np.testing.assert_array_equal(result.codes, oracle(self.weights, self.lower))

    def test_ambiguous_row_blocks_whole_model_and_retains_global_identity(self):
        weights = np.array([[0., 0.], [.21, 2.6], [0., 0.]])
        lower, upper = np.ones((2, 1)), np.array([[4.], [1.]])
        options = dict(ridge=Q(1, 1000000), normalization=1)
        for allow in (False, True):
            with self.assertRaises(TokenBoxUnresolved) as raised:
                module.certify_ball_dyadic_box(weights, lower, upper, allow_python_fallback=allow, **options)
            diagnostics = raised.exception.native_diagnostics
            self.assertIn(1, diagnostics['python_universal_row_indices'])
            self.assertGreater(diagnostics['total_elapsed_ns'], 0)
            if allow:
                self.assertGreater(diagnostics['fallback_elapsed_ns'], 0)

    def test_noncontiguous_unaligned_readonly_and_singleton_contracts(self):
        def unaligned(x):
            result = np.ndarray(x.shape, dtype=np.float64, buffer=bytearray(x.nbytes+1), offset=1)
            result[:] = x
            result.flags.writeable = False
            return result
        for weights, lower, upper in (
            (unaligned(self.weights), unaligned(self.lower), unaligned(self.upper)),
            (self.weights[::-1], self.lower, self.upper),
            (unaligned(self.weights), unaligned(self.lower), unaligned(self.lower)),
            (self.weights, np.empty((2, 0)), np.empty((2, 0))),
        ):
            result = module.certify_ball_dyadic_box(weights, lower, upper, ridge=10, normalization=3)
            np.testing.assert_array_equal(result.codes, oracle(weights, lower))

    def test_validation_runtime_candidates_provenance_and_complete_cost(self):
        expected = oracle(self.weights, self.lower)
        result = module.certify_ball_dyadic_box(self.weights, self.lower, self.upper,
            ridge=10, normalization=3, candidate_codes=expected)
        self.assertTrue(result.candidate_checked)
        self.assertEqual(result.native_source_sha256, hashlib.sha256(module.ball._C_SOURCE.encode()).hexdigest())
        self.assertEqual(result.interval_source_sha256, hashlib.sha256(module.interval._C_SOURCE.encode()).hexdigest())
        self.assertEqual(result.wrapper_source_sha256, hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest())
        self.assertEqual(result.native_attempted_decisions, sum(p['attempted_decisions'] for p in result.native_passes))
        self.assertEqual(result.native_certified_decisions, sum(p['certified_decisions'] for p in result.native_passes))
        self.assertEqual(sum((result.first_ball_certified_rows, result.ridge_interval_certified_rows,
            result.preconditioned_interval_certified_rows, result.python_universal_rows)), len(self.weights))
        self.assertGreaterEqual(result.total_elapsed_ns, sum((result.feature_bounds_elapsed_ns,
            result.coefficient_elapsed_ns, result.ball_bounds_elapsed_ns, result.interval_bounds_elapsed_ns,
            result.native_elapsed_ns, result.fallback_elapsed_ns, result.compile_elapsed_ns)))
        with self.assertRaises(TokenBoxUnresolved):
            module.certify_ball_dyadic_box(self.weights, self.lower, self.upper,
                ridge=10, normalization=3, candidate_codes=np.zeros_like(self.weights))
        for name in ('weights', 'lower', 'upper', 'candidate_codes'):
            kwargs = dict(weights=self.weights.copy(), lower=self.lower.copy(), upper=self.upper.copy())
            if name == 'candidate_codes':
                kwargs[name] = self.weights.copy()
            kwargs[name].flat[0] = np.nan
            with self.assertRaises(ValueError):
                module.certify_ball_dyadic_box(**kwargs, ridge=10)
        huge = np.broadcast_to(np.array([[1.]]), (1, 2**20+1))
        with self.assertRaises(ValueError):
            module.certify_ball_dyadic_box(np.ones((1, 1)), huge, huge, ridge=1)
        with patch.object(module, '_check_runtime', side_effect=RuntimeError('unsupported')):
            with self.assertRaises(RuntimeError):
                module.certify_ball_dyadic_box(self.weights, self.lower, self.upper, ridge=10)


if __name__ == '__main__':
    unittest.main()
