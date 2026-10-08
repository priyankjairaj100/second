"""Small exact numerical fixtures, not empirical datasets or benchmarks."""
import ctypes
from fractions import Fraction as Q
import itertools
import unittest
from unittest.mock import patch

import numpy as np

import src.native_box_coefficients_v31 as module
import src.token_box_certificate as reference
from src.low_rank_certified import LowRankUnresolved, _add, _exact_coefficient, _initial_gram
from src.token_box_certificate import TokenBoxUnresolved
from tests.test_native_box_v26 import corners, rational


class NativeBoxCoefficientTests(unittest.TestCase):
    def compare(self, lower, upper, beta):
        with np.errstate(over='ignore',under='ignore',invalid='ignore',divide='ignore'):
            expected = reference._box_coefficients(lower,upper,beta)
        actual = module.native_box_coefficient_enclosures(lower,upper,beta)
        np.testing.assert_array_equal(actual.coefficients.view(np.uint64),expected[0].view(np.uint64))
        np.testing.assert_array_equal(actual.errors.view(np.uint64),expected[1].view(np.uint64))
        return actual

    def test_point_and_uncertain_coefficients_match_reference_encodings(self):
        tiny = np.nextafter(0.,1.)
        fixtures = (
            (np.array([[.9,-.3],[.4,.7],[-.5,.2]]),1e-8),
            (np.zeros((3,2)),0.),
            (np.array([[0.,-0.,tiny],[-tiny,2*tiny,0.]]),0.),
            (np.array([[-1.,-.5],[.25,-.125]]),.75),
            (np.array([[2.**-40,2.**40],[2.**-30,-2.**30]]),0.),
        )
        for lower,delta in fixtures:
            for beta in (Q(1,3),Q(1),Q(30)):
                self.compare(lower,lower+delta,beta)

    def test_each_native_gram_update_matches_reference_directed_endpoints(self):
        module.prepare_native_box_coefficients()
        lower = np.array([[-.4,.2,-0.],[.3,-.7,.125],[-1.,0.,-.25]])
        upper = np.array([[.5,.4,0.],[.3,-.6,.125],[-.9,0.,.75]])
        old_lo,old_hi,_ = _initial_gram(3,Q(1,3))
        new_lo,new_hi = old_lo.copy(),old_hi.copy()
        for i in range(len(lower)-1,-1,-1):
            outer = reference._outer_bounds(lower[i],upper[i])
            old_lo,old_hi = _add(old_lo,old_hi,*outer)
            status = module._NATIVE.nbxc_update(3,module._ptr(lower[i]),module._ptr(upper[i]),
                module._ptr(new_lo),module._ptr(new_hi))
            self.assertEqual(status,0)
            np.testing.assert_array_equal(new_lo.view(np.uint64),old_lo.view(np.uint64))
            np.testing.assert_array_equal(new_hi.view(np.uint64),old_hi.view(np.uint64))

    def test_correlated_diagonal_squares_and_cross_products_enclose_exact_values(self):
        module.prepare_native_box_coefficients()
        tiny = np.nextafter(0.,1.)
        cases = ((-1.,2.,-.25,.75),(tiny,2*tiny,-tiny,tiny),
                 (0.,-0.,-1.,1.),(-.5,-.25,.25,.5))
        for case,diagonal in itertools.product(cases,(0,1)):
            inputs,output = np.array(case),np.empty(2)
            status = module._NATIVE.nbxc_outer_probe(module._ptr(inputs),diagonal,module._ptr(output))
            self.assertEqual(status,0)
            points = (case[0],case[1]) + ((0.,) if case[0] <= 0 <= case[1] else ())
            products = [rational(x)**2 for x in points] if diagonal else [
                rational(x)*rational(y) for x,y in itertools.product(case[:2],case[2:])]
            for exact in products:
                self.assertLessEqual(rational(output[0]),exact)
                self.assertLessEqual(exact,rational(output[1]))
            if diagonal and case[0] <= 0 <= case[1]:
                self.assertEqual(output[0],0.)

    def test_all_exact_corner_coefficients_satisfy_universal_error_balls(self):
        lower = np.array([[.25,-.5],[.5,-.125],[-.75,.125]])
        upper = lower+np.array([[.0625,.03125],[.03125,.0625],[.125,.125]])
        for beta in (Q(1,3),Q(1,1000),Q(13,7)):
            result = module.native_box_coefficient_enclosures(lower,upper,beta)
            for features in corners(lower,upper):
                for i in range(len(lower)):
                    exact = _exact_coefficient(features,i,beta)
                    error = sum(((x-rational(p))**2 for x,p in zip(exact,result.coefficients[i])),Q(0))
                    self.assertLessEqual(error,rational(result.errors[i]))

    def test_invalid_nominal_inverse_uses_same_verified_zero_proposal_policy(self):
        lower,upper = np.array([[.25,-.5],[.5,.125]]),np.array([[.3,-.4],[.6,.2]])
        initial = _initial_gram(2,Q(1))
        def gram(*args):
            return initial[0].copy(),initial[1].copy(),initial[2]
        with patch.object(reference,'_initial_gram',side_effect=gram), \
             patch.object(module,'_initial_gram',side_effect=gram), \
             patch.object(module.np,'eye',return_value=np.full((2,2),np.inf)):
            with np.errstate(over='ignore',invalid='ignore',divide='ignore'):
                expected = reference._box_coefficients(lower,upper,Q(1))
            actual = module.native_box_coefficient_enclosures(lower,upper,Q(1))
        self.assertEqual(actual.zero_proposal_fallbacks,1)
        np.testing.assert_array_equal(actual.coefficients,expected[0])
        np.testing.assert_array_equal(actual.errors,expected[1])
        np.testing.assert_array_equal(actual.coefficients,np.zeros_like(lower))
        for features in corners(lower,upper):
            for i in range(len(lower)):
                exact = _exact_coefficient(features,i,Q(1))
                self.assertLessEqual(sum((x*x for x in exact),Q(0)),rational(actual.errors[i]))

    def test_alignment_layout_and_immutable_outputs(self):
        lower = np.array([[.9,-.3],[.4,.7],[-.5,.2]])
        def unaligned(array):
            result = np.ndarray(array.shape,dtype=np.float64,buffer=bytearray(array.nbytes+1),offset=1)
            result[:] = array
            result.flags.writeable = False
            return result
        for lo,hi in ((unaligned(lower),unaligned(lower+1e-8)),
                      (lower[:,::-1],(lower+1e-8)[:,::-1]),
                      (np.asfortranarray(lower),np.asfortranarray(lower+1e-8))):
            before = lo.tobytes(),hi.tobytes()
            result = self.compare(lo,hi,Q(30))
            self.assertEqual(before,(lo.tobytes(),hi.tobytes()))
            for value in (result.coefficients,result.errors):
                with self.assertRaises(ValueError):
                    value.flags.writeable = True

    def test_empty_tokens_charge_positive_work_without_compilation(self):
        with patch.object(module,'prepare_native_box_coefficients',side_effect=AssertionError('no compiler')):
            result = module.native_box_coefficient_enclosures(np.empty((3,0)),np.empty((3,0)),Q(1))
        self.assertEqual(result.coefficients.shape,(3,0))
        np.testing.assert_array_equal(result.errors,np.zeros(3))
        self.assertEqual(result.work_units,3)
        self.assertEqual(result.compile_elapsed_ns,0)
        self.assertEqual(result.native_build_manifest,{})

    def test_admission_precedes_gram_and_compilation(self):
        lower = np.ones((3,2))
        for budget in (module.NativeBoxCoefficientBudget(max_work_units=1),
                       module.NativeBoxCoefficientBudget(max_workspace_bytes=1)):
            with patch.object(module,'_initial_gram',side_effect=AssertionError('no Gram')), \
                 patch.object(module,'prepare_native_box_coefficients',side_effect=AssertionError('no compiler')):
                with self.assertRaises(TokenBoxUnresolved) as caught:
                    module.native_box_coefficient_enclosures(lower,lower,Q(1),budget=budget)
            self.assertFalse(caught.exception.coefficient_admission['admitted'])

    def test_overflow_and_underflow_refuse_with_no_coefficient_result(self):
        for lower,beta in ((np.array([[1e308]]),Q(1)),
                           (np.ones((2,1)),Q(1,1 << 1074))):
            with np.errstate(over='ignore',under='ignore',invalid='ignore',divide='ignore'):
                with self.assertRaises(LowRankUnresolved):
                    reference._box_coefficients(lower,lower,beta)
            with self.assertRaises(LowRankUnresolved) as caught:
                module.native_box_coefficient_enclosures(lower,lower,beta)
            self.assertEqual(caught.exception.coefficient_diagnostics['completed_coordinates'],0)
            self.assertGreater(caught.exception.coefficient_diagnostics['total_elapsed_ns'],0)

    def test_failed_compilation_and_runtime_guards_remain_visible(self):
        lower = np.ones((2,1))
        with patch.object(module,'prepare_native_box_coefficients',side_effect=TokenBoxUnresolved('compiler refused')):
            with self.assertRaises(TokenBoxUnresolved) as caught:
                module.native_box_coefficient_enclosures(lower,lower,Q(1))
        self.assertFalse(caught.exception.coefficient_diagnostics['compilation_completed'])
        self.assertGreater(caught.exception.coefficient_diagnostics['compile_elapsed_ns'],0)
        with patch.object(module,'_check_runtime',side_effect=RuntimeError('unsupported')):
            with self.assertRaises(RuntimeError):
                module.native_box_coefficient_enclosures(lower,lower,Q(1))

    def test_api_validation_and_build_identity(self):
        lower = np.ones((2,1))
        for bad in (lower.astype(np.float32),[[1.],[1.]],lower.ravel()):
            with self.assertRaises(TypeError):
                module.native_box_coefficient_enclosures(bad,lower,Q(1))
        for lo,hi in ((np.empty((0,1)),np.empty((0,1))),
                      (lower,lower[:-1]),(lower,lower-.1),(lower*np.inf,lower)):
            with self.assertRaises(ValueError):
                module.native_box_coefficient_enclosures(lo,hi,Q(1))
        for beta in (0,-1):
            with self.assertRaises(ValueError):
                module.native_box_coefficient_enclosures(lower,lower,beta)
        for beta in (.1,True):
            with self.assertRaises(TypeError):
                module.native_box_coefficient_enclosures(lower,lower,beta)
        for value in (True,0,-1,1.5):
            with self.assertRaises(ValueError):
                module.NativeBoxCoefficientBudget(max_work_units=value)
        result = module.native_box_coefficient_enclosures(lower,lower,Q(1))
        build = module.prepare_native_box_coefficients()
        self.assertEqual(result.native_source_sha256,build['source_sha256'])
        self.assertEqual(result.native_binary_sha256,build['binary_sha256'])
        self.assertEqual(result.native_build_manifest['flags'],list(module.native_box._FLAGS))
        self.assertFalse(build['compiled_now'])
        self.assertEqual(build['call_compile_elapsed_ns'],0)


if __name__ == '__main__':
    unittest.main()
