"""Small exact numerical fixtures; no empirical dataset or model evaluation."""
from fractions import Fraction as Q
import unittest
from unittest.mock import patch

import numpy as np

import src.native_token_coefficients_v30 as module
from src.batched_token_solver import _coefficient_enclosures
from src.exact_core import sequential_oracle
from src.low_rank_certified import (
    LowRankUnresolved, _add, _check_cells, _exact_coefficient, _multiply_point,
)


def rational(value):
    return Q.from_float(float(value))


class NativeTokenCoefficientTests(unittest.TestCase):
    def setUp(self):
        self.features = np.array([[.9,-.3],[.4,.7],[-.5,.2]])

    def test_directed_results_equal_existing_reference(self):
        fixtures = (self.features, np.zeros((3,2)),
                    np.array([[0.,1.,-2.],[.125,-.0625,3.],[-1.,0.,.25],[.5,.5,.5]]))
        for features in fixtures:
            for beta in (Q(1,3),Q(1),Q(30)):
                actual = module.native_token_coefficient_enclosures(features,beta)
                expected_coefficients,expected_errors = _coefficient_enclosures(features,beta)
                np.testing.assert_array_equal(actual.coefficients,expected_coefficients)
                np.testing.assert_array_equal(actual.errors,expected_errors)

    def test_exact_rational_coefficients_lie_inside_error_balls(self):
        features = np.array([[.25,-.5,1.],[.5,0.,-.125],[-.75,.125,.25]])
        for beta in (Q(1,3),Q(1,1000),Q(13,7)):
            result = module.native_token_coefficient_enclosures(features,beta)
            for i in range(len(features)):
                exact = _exact_coefficient(features,i,beta)
                squared = sum(((value-rational(proposed))**2
                               for value,proposed in zip(exact,result.coefficients[i])),Q(0))
                self.assertLessEqual(squared,rational(result.errors[i]))

    def test_existing_row_certificate_matches_exact_quantizer(self):
        weights = np.array([[.21,.1,2.6],[-.2,.05,1.7]])
        beta = Q(30)
        result = module.native_token_coefficient_enclosures(self.features,beta)
        grid = tuple(Q(i,4) for i in range(-16,17))
        codes = np.empty_like(weights)
        lower = np.zeros((len(weights),self.features.shape[1]))
        upper = lower.copy()
        for i in range(weights.shape[1]):
            indices,safe = _check_cells(weights[:,i],lower,upper,
                                       result.coefficients[i],result.errors[i],grid)
            self.assertTrue(np.all(safe))
            codes[:,i] = np.asarray(grid,dtype=np.float64)[indices]
            dlo,dhi = _add(weights[:,i],weights[:,i],-codes[:,i],-codes[:,i])
            for k in range(self.features.shape[1]):
                tlo,thi = _multiply_point(dlo,dhi,self.features[i,k])
                lower[:,k],upper[:,k] = _add(lower[:,k],upper[:,k],tlo,thi)
        exact_x = [[rational(value) for value in row] for row in self.features]
        metric = [[sum((x*y for x,y in zip(a,b)),Q(0))+(beta if h == j else 0)
                   for j,b in enumerate(exact_x)] for h,a in enumerate(exact_x)]
        expected = sequential_oracle([[rational(value) for value in row] for row in weights],
                                     metric,(grid,)*weights.shape[1])
        np.testing.assert_array_equal(codes,np.array(expected.codes,dtype=np.float64))

    def test_empty_tokens_have_exact_zero_error_without_compilation(self):
        with patch.object(module,'prepare_native_token_coefficients',side_effect=AssertionError('no compiler')):
            result = module.native_token_coefficient_enclosures(np.empty((3,0)),Q(1))
        self.assertEqual(result.coefficients.shape,(3,0))
        np.testing.assert_array_equal(result.errors,np.zeros(3))
        self.assertEqual(result.compile_elapsed_ns,0)
        self.assertEqual(result.native_source_sha256,'')

    def test_unaligned_noncontiguous_readonly_inputs_are_preserved(self):
        unaligned = np.ndarray(self.features.shape,dtype=np.float64,
            buffer=bytearray(self.features.nbytes+1),offset=1)
        unaligned[:] = self.features
        readonly = self.features.copy()
        readonly.flags.writeable = False
        for features in (unaligned,readonly,self.features[:,::-1]):
            before = features.tobytes()
            result = module.native_token_coefficient_enclosures(features,Q(3))
            expected = _coefficient_enclosures(np.ascontiguousarray(features),Q(3))
            np.testing.assert_array_equal(result.coefficients,expected[0])
            np.testing.assert_array_equal(result.errors,expected[1])
            self.assertEqual(before,features.tobytes())
            for value in (result.coefficients,result.errors):
                with self.assertRaises(ValueError):
                    value.flags.writeable = True

    def test_subnormal_products_match_reference_and_exact_containment(self):
        tiny = np.nextafter(0.,1.)
        features = np.array([[tiny,-tiny],[2.**-540,0.],[-2.**-530,2.**-535]])
        actual = module.native_token_coefficient_enclosures(features,Q(1))
        expected = _coefficient_enclosures(features,Q(1))
        np.testing.assert_array_equal(actual.coefficients,expected[0])
        np.testing.assert_array_equal(actual.errors,expected[1])
        for i in range(len(features)):
            exact = _exact_coefficient(features,i,Q(1))
            squared = sum(((value-rational(proposed))**2
                           for value,proposed in zip(exact,actual.coefficients[i])),Q(0))
            self.assertLessEqual(squared,rational(actual.errors[i]))

    def test_overflow_and_underflow_refuse_without_result(self):
        for features,beta in ((np.full((3,2),1e200),Q(1)),
                              (self.features,Q(1,1 << 1000))):
            with self.assertRaises(LowRankUnresolved):
                module.native_token_coefficient_enclosures(features,beta)

    def test_admission_precedes_compilation_and_numerical_allocation(self):
        for budget in (module.NativeCoefficientBudget(max_work_units=1),
                       module.NativeCoefficientBudget(max_workspace_bytes=1)):
            with (patch.object(module,'_initial_gram',side_effect=AssertionError('no Gram')),
                  patch.object(module,'prepare_native_token_coefficients',side_effect=AssertionError('no compiler'))):
                with self.assertRaises(LowRankUnresolved) as caught:
                    module.native_token_coefficient_enclosures(self.features,Q(1),budget=budget)
            self.assertFalse(caught.exception.coefficient_admission['admitted'])

    def test_shape_value_and_scalar_contracts(self):
        for features in (self.features.astype(np.float32),np.array([[1,2]]),[[1.,2.]],self.features[0]):
            with self.assertRaises(TypeError):
                module.native_token_coefficient_enclosures(features,Q(1))
        for beta in (0,-1):
            with self.assertRaises(ValueError):
                module.native_token_coefficient_enclosures(self.features,beta)
        for beta in (.1,True):
            with self.assertRaises(TypeError):
                module.native_token_coefficient_enclosures(self.features,beta)
        for value in (np.inf,np.nan):
            invalid = self.features.copy(); invalid[0,0] = value
            with self.assertRaises(ValueError):
                module.native_token_coefficient_enclosures(invalid,Q(1))
        for value in (True,0,-1,1.5):
            with self.assertRaises(ValueError):
                module.NativeCoefficientBudget(max_work_units=value)
        with self.assertRaises(ValueError):
            module.native_token_coefficient_enclosures(np.empty((0,2)),Q(1))

    def test_runtime_and_build_identities(self):
        result = module.native_token_coefficient_enclosures(self.features,Q(1))
        build = module.prepare_native_token_coefficients()
        self.assertFalse(build['compiled_now'])
        self.assertEqual(build['call_compile_elapsed_ns'],0)
        self.assertEqual(result.native_source_sha256,build['source_sha256'])
        self.assertEqual(result.native_binary_sha256,build['binary_sha256'])
        self.assertEqual(len(result.wrapper_source_sha256),64)
        self.assertGreaterEqual(result.total_elapsed_ns,result.native_elapsed_ns)
        with patch.object(module,'_check_runtime',side_effect=RuntimeError('unsupported runtime')):
            with self.assertRaises(RuntimeError):
                module.native_token_coefficient_enclosures(self.features,Q(1))


if __name__ == '__main__':
    unittest.main()
