"""Universal certificate software fixtures; no empirical model evaluation."""
from dataclasses import replace
from fractions import Fraction as Q
import unittest
from unittest.mock import patch

import numpy as np

import src.native_box_coefficients_v31 as coefficient_module
import src.sparse_box_certificate_v30 as previous
import src.sparse_box_certificate_v31 as module
from src.token_box_certificate import TokenBoxUnresolved
from tests.test_native_box_v26 import corners, oracle


class NativeSparseCertificateTests(unittest.TestCase):
    def setUp(self):
        self.weights = np.array([[.21,2.6]])
        self.lower = np.ones((2,1))
        self.upper = self.lower+1e-6
        self.options = dict(ridge=Q(1,1_000_000),normalization=1)

    def certify(self, **kwargs):
        return module.certify_sparse_ball_dyadic_box(self.weights,self.lower,self.upper,**self.options,**kwargs)

    def test_native_and_reference_preserve_all_exact_corner_codes_and_refinement(self):
        fixtures = (
            (self.weights,self.lower,self.upper,self.options),
            (np.array([[.2,7.],[.5,7.],[-.2,7.]]),np.array([[0.],[1.]]),
             np.array([[0.],[1.+1e-8]]),dict(ridge=10,normalization=3)),
            (np.array([[2.6,.21,-.11],[-.3,1.7,.06]]),
             np.array([[.9,-.3],[.4,.7],[-.5,.2]]),
             np.array([[.9,-.3],[.4,.7],[-.5,.2]])+1e-8,dict(ridge=10,normalization=3)),
        )
        for weights,lower,upper,options in fixtures:
            expected = previous.certify_sparse_ball_dyadic_box(weights,lower,upper,**options)
            for backend in ('native','reference'):
                actual = module.certify_sparse_ball_dyadic_box(weights,lower,upper,
                    coefficient_backend=backend,**options)
                np.testing.assert_array_equal(actual.codes,expected.codes)
                for name in ('preconditioner_requested_coordinates','preconditioner_verified_coordinates',
                             'preconditioner_rounds','unresolved_coordinate_rounds','work_units_reserved',
                             'resource_reservations','max_coefficient_error_squared'):
                    self.assertEqual(getattr(actual,name),getattr(expected,name))
                for features in corners(lower,upper):
                    np.testing.assert_array_equal(actual.codes,oracle(weights,features,**options))
                self.assertEqual(actual.coefficient_backend,backend)
                self.assertFalse(actual.python_universal_fallback)
                self.assertEqual(actual.point_exact_decisions,0)

    def test_budget_type_and_structural_limits_are_shared_without_extra_reservations(self):
        self.assertIs(module.SparseCertificateBudget,previous.SparseCertificateBudget)
        for rows,width,tokens in ((1,1,0),(1,1,1),(2,3,2),(768,3072,128)):
            coefficient = coefficient_module.assess_native_box_coefficients(width,tokens,
                budget=coefficient_module.NativeBoxCoefficientBudget(max_work_units=10**15,
                    max_workspace_bytes=10**15))
            complete = module._workspace_allowance(rows,width,tokens,16,min(width,16))
            initial = width*tokens**2 + rows*width*(2*tokens+4+1)+width*tokens+rows*16
            self.assertLessEqual(coefficient['explicit_array_bytes'],complete)
            self.assertLessEqual(coefficient['work_units'],initial)
        result = self.certify(budget=module.SparseCertificateBudget(max_work_units=64))
        self.assertEqual(result.work_units_reserved,64)
        self.assertEqual(sum(item['units'] for item in result.resource_reservations),64)

    def test_reference_backend_never_invokes_native_builder_or_changes_globals(self):
        builder = module.boxes._box_coefficients
        helper = previous._requested_components
        with patch.object(module,'native_box_coefficient_enclosures',side_effect=AssertionError('native unused')):
            result = self.certify(coefficient_backend='reference')
        self.assertIs(module.boxes._box_coefficients,builder)
        self.assertIs(previous._requested_components,helper)
        self.assertIsNone(result.coefficient_evidence)
        with patch.object(module.boxes,'_box_coefficients',side_effect=AssertionError('reference unused')):
            native = self.certify()
        self.assertEqual(len(native.coefficient_evidence['native_source_sha256']),64)
        self.assertIn('-ffp-contract=off',native.coefficient_evidence['native_build_manifest']['flags'])

    def test_unaligned_readonly_coefficient_evidence_is_aligned_before_row_passes(self):
        evidence = coefficient_module.native_box_coefficient_enclosures(self.lower,self.upper,Q(1,1_000_000))
        unaligned = np.ndarray(evidence.coefficients.shape,dtype=np.float64,
            buffer=bytearray(evidence.coefficients.nbytes+1),offset=1)
        unaligned[:] = evidence.coefficients
        unaligned.flags.writeable = False
        self.assertFalse(unaligned.flags.aligned)
        actual_ball,actual_rows = module.previous._ball_pass,module.previous._interval_rows
        def ball_pass(*args):
            self.assertTrue(args[2].flags.aligned)
            self.assertTrue(args[2].flags.c_contiguous)
            return actual_ball(*args)
        def interval_rows(*args):
            self.assertTrue(args[3].flags.aligned)
            self.assertTrue(args[3].flags.c_contiguous)
            return actual_rows(*args)
        with patch.object(module,'native_box_coefficient_enclosures',return_value=replace(evidence,coefficients=unaligned)), \
             patch.object(module.previous,'_ball_pass',side_effect=ball_pass), \
             patch.object(module.previous,'_interval_rows',side_effect=interval_rows):
            result = self.certify()
        np.testing.assert_array_equal(result.codes,oracle(self.weights,self.lower,**self.options))

    def test_resource_refusal_precedes_native_construction(self):
        for budget in (module.SparseCertificateBudget(max_workspace_bytes=1),
                       module.SparseCertificateBudget(max_work_units=0)):
            with patch.object(module,'native_box_coefficient_enclosures',side_effect=AssertionError('unadmitted builder')):
                with self.assertRaises(TokenBoxUnresolved):
                    self.certify(budget=budget)

    def test_failed_coefficient_compilation_preserves_receipt_and_no_rows_execute(self):
        with patch.object(coefficient_module,'prepare_native_box_coefficients',
                          side_effect=TokenBoxUnresolved('deliberate compiler refusal')), \
             patch.object(module.previous,'_ball_pass',side_effect=AssertionError('no row certificate')):
            with self.assertRaises(TokenBoxUnresolved) as caught:
                self.certify()
        diagnostics = caught.exception.native_diagnostics
        coefficient = diagnostics['coefficient_diagnostics']
        self.assertEqual(diagnostics['passes'],[])
        self.assertGreater(diagnostics['coefficient_elapsed_ns'],0)
        self.assertGreater(coefficient['compile_elapsed_ns'],0)
        self.assertGreaterEqual(diagnostics['compile_elapsed_ns'],coefficient['compile_elapsed_ns'])
        self.assertFalse(coefficient['compilation_completed'])

    def test_real_box_disagreement_refuses_without_point_or_unbounded_fallback(self):
        upper = np.array([[4.],[1.]])
        self.assertFalse(np.array_equal(oracle(self.weights,self.lower,**self.options),
                                       oracle(self.weights,upper,**self.options)))
        with patch.object(module.ball,'native_ball_quantize_dyadic_rows',side_effect=AssertionError('no point fallback')), \
             patch.object(module.preconditioned,'certify_preconditioned_dyadic_box',
                          side_effect=AssertionError('no unbounded fallback')):
            for backend in ('native','reference'):
                with self.assertRaises(TokenBoxUnresolved):
                    module.certify_sparse_ball_dyadic_box(self.weights,self.lower,upper,
                        coefficient_backend=backend,**self.options)

    def test_singleton_empty_inputs_and_backend_contract(self):
        for lower,upper in ((self.lower,self.lower),(np.empty((2,0)),np.empty((2,0)))):
            actual = module.certify_sparse_ball_dyadic_box(self.weights,lower,upper,**self.options)
            np.testing.assert_array_equal(actual.codes,oracle(self.weights,lower,**self.options))
            self.assertEqual(actual.point_exact_decisions,0)
        for backend in (None,True,'untrusted',lambda *args:None):
            with self.assertRaises(ValueError):
                self.certify(coefficient_backend=backend)
        with self.assertRaises(ValueError):
            self.certify(allow_python_fallback=True)


if __name__ == '__main__':
    unittest.main()
