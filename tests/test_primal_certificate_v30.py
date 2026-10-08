"""Small exact software fixtures. These are not empirical research datasets."""
import itertools
from fractions import Fraction as Q
import unittest
from unittest.mock import patch

import numpy as np

from src.dyadic_row_quantizer import dyadic_row_scales
from src.exact_core import sequential_oracle
from src.low_rank_certified import _exact_solve
from src.primal_certificate_v30 import (
    PrimalBudget, PrimalUnresolved, assess_primal_budget,
    certify_primal_dyadic_box, prepare_primal_native,
    _coefficient_bounds, _gram_bounds, _sqrt_upper,
)


def rational(value):
    return Q.from_float(float(value))


def exact_gram(features):
    return [[sum((rational(x)*rational(y) for x,y in zip(a,b)),Q(0))
             for b in features] for a in features]


def oracle(weights,features,ridge=Q(10),normalization=Q(3)):
    gram = exact_gram(features)
    metric = [[entry/normalization + (ridge if i == j else 0)
               for j,entry in enumerate(row)] for i,row in enumerate(gram)]
    output = []
    for row,scale in zip(weights,dyadic_row_scales(weights)):
        grid = tuple(k*rational(scale) for k in range(-8,8))
        output.append(sequential_oracle([[rational(x) for x in row]],metric,
                                       [grid]*weights.shape[1]).codes[0])
    return np.asarray(output,dtype=np.float64)


def corners(lower,upper):
    for bits in itertools.product((False,True),repeat=lower.size):
        yield np.where(np.asarray(bits).reshape(lower.shape),upper,lower)


class PrimalCertificateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = prepare_primal_native()

    def setUp(self):
        self.weights = np.array([[2.6,.21,-.11],[-.3,1.7,.06]])
        self.features = np.array([[.9,-.3],[.4,.7],[-.5,.2]])

    def test_point_and_empty_tokens_match_independent_oracle(self):
        for backend in ('native','python'):
            for features in (self.features,np.empty((3,0))):
                result = certify_primal_dyadic_box(self.weights,features,features,
                    ridge=10,normalization=3,arithmetic_backend=backend)
                np.testing.assert_array_equal(result.codes,oracle(self.weights,features))
                self.assertEqual(result.point_exact_decisions,0)
                self.assertEqual(result.interval_decisions,self.weights.size)
                self.assertEqual(result.width,3)
                self.assertEqual(result.tokens,features.shape[1])
                self.assertEqual(result.uncertain_features,0)

    def test_uncertain_box_contains_every_corner_and_interior(self):
        lower,upper = self.features,self.features+1e-7
        for backend in ('native','python'):
            result = certify_primal_dyadic_box(self.weights,lower,upper,
                ridge=10,normalization=3,arithmetic_backend=backend)
            for features in corners(lower,upper):
                np.testing.assert_array_equal(result.codes,oracle(self.weights,features))
            for alpha in (.125,.5,.875):
                features = lower + alpha*(upper-lower)
                np.testing.assert_array_equal(result.codes,oracle(self.weights,features))
            self.assertEqual(result.uncertain_features,6)

    def test_directed_gram_contains_exact_point_and_box_grams(self):
        lower = np.array([[-.7,.2],[.4,-.3],[0.,1.]])
        upper = lower + np.array([[.02,.01],[.01,.03],[.01,.02]])
        for backend in ('native','python'):
            lo,hi = _gram_bounds(lower,upper,arithmetic_backend=backend)
            self.assertTrue(np.all(np.diag(lo) >= 0))
            np.testing.assert_array_equal(lo,lo.T)
            np.testing.assert_array_equal(hi,hi.T)
            for features in corners(lower,upper):
                gram = exact_gram(features)
                for i,j in itertools.product(range(3),repeat=2):
                    self.assertLessEqual(rational(lo[i,j]),gram[i][j])
                    self.assertLessEqual(gram[i][j],rational(hi[i,j]))

    def test_primal_coefficients_contain_exact_suffix_solutions(self):
        lower = np.array([[-.7,.2],[.4,-.3],[0.,1.]])
        upper = lower+.002
        beta = Q(3,7)
        for backend in ('native','python'):
            evidence = _coefficient_bounds(lower,upper,beta,arithmetic_backend=backend)
            for features in corners(lower,upper):
                gram = exact_gram(features)
                for i in range(1,3):
                    matrix = [[gram[h][j]+(beta if h == j else 0)
                               for j in range(i,3)] for h in range(i,3)]
                    solution = _exact_solve(matrix,[Q(1)]+[Q(0)]*(2-i))
                    for h in range(i):
                        coefficient = sum((gram[h][j]*solution[j-i] for j in range(i,3)),Q(0))
                        self.assertLessEqual(abs(coefficient-rational(evidence.centers[i,h])),
                                             rational(evidence.radii[i,h]))

    def test_norm_radius_verification_handles_subnormal_and_large_values(self):
        for squared in (0.,np.nextafter(0.,1.),np.nextafter(np.finfo(float).tiny,0.),np.finfo(float).tiny,2.**-1000,.1,1.,2.,1e200,np.finfo(float).max):
            bound = _sqrt_upper(squared)
            self.assertGreaterEqual(rational(bound)**2,rational(squared))
        for squared in (-1.,np.inf,np.nan):
            with self.assertRaises(PrimalUnresolved):
                _sqrt_upper(squared)
        with patch('src.primal_certificate_v30.np.sqrt',return_value=0.):
            with self.assertRaises(PrimalUnresolved):
                _sqrt_upper(1.)

    def test_zero_feature_ties_choose_lower_code(self):
        weights = np.array([[.5,1.5,7.],[-.5,-1.5,7.]])
        features = np.zeros((3,2))
        for backend in ('native','python'):
            result = certify_primal_dyadic_box(weights,features,features,
                ridge=1,arithmetic_backend=backend)
            np.testing.assert_array_equal(result.codes,[[0.,1.,7.],[-1.,-2.,7.]])

    def test_real_box_disagreement_is_refused(self):
        weights = np.array([[.21,2.6]])
        lower,upper = np.ones((2,1)),np.array([[4.],[1.]])
        options = dict(ridge=Q(1,1000000),normalization=1)
        self.assertFalse(np.array_equal(oracle(weights,lower,**options),oracle(weights,upper,**options)))
        for backend in ('native','python'):
            with self.assertRaises(PrimalUnresolved):
                certify_primal_dyadic_box(weights,lower,upper,arithmetic_backend=backend,**options)

    def test_wrong_nominal_proposals_never_override_residual_evidence(self):
        for backend in ('native','python'):
            def broken(nominal,inverse,i,beta):
                return np.full(len(nominal)-i,1e10),True
            with patch('src.primal_certificate_v30._suffix_proposal',side_effect=broken):
                with self.assertRaises(PrimalUnresolved):
                    certify_primal_dyadic_box(self.weights,self.features,self.features,
                        ridge=10,normalization=3,arithmetic_backend=backend)

    def test_resource_guards_run_before_coefficient_or_compile_work(self):
        report = assess_primal_budget(rows=2,width=3,tokens=2,
                                      budget=PrimalBudget(max_work_units=1))
        self.assertFalse(report['admitted'])
        self.assertIn('work',report['refusal_reason'])
        memory = assess_primal_budget(rows=2,width=3,tokens=2,
                                     budget=PrimalBudget(max_workspace_bytes=1))
        self.assertFalse(memory['admitted'])
        with patch('src.primal_certificate_v30._coefficient_bounds',side_effect=AssertionError('no allocation')):
            with patch('src.primal_certificate_v30.prepare_primal_native',side_effect=AssertionError('no compile')):
                with self.assertRaises(PrimalUnresolved):
                    certify_primal_dyadic_box(self.weights,self.features,self.features,
                        ridge=1,budget=PrimalBudget(max_work_units=1))
        for value in (True,0,-1,1.5):
            with self.assertRaises(ValueError):
                PrimalBudget(max_work_units=value)

    def test_token_scaling_is_linear_and_coefficient_storage_ignores_tokens(self):
        large = PrimalBudget(max_workspace_bytes=10**15,max_work_units=10**18)
        first = assess_primal_budget(rows=2,width=3,tokens=100,budget=large)
        second = assess_primal_budget(rows=2,width=3,tokens=200,budget=large)
        self.assertEqual(second['work_units']-first['work_units'],900)
        self.assertEqual(first['coefficient_workspace_bytes'],second['coefficient_workspace_bytes'])
        self.assertEqual(second['explicit_array_bytes']-first['explicit_array_bytes'],8*4*3*100)

    def test_candidate_scales_normalization_and_input_contracts(self):
        result = certify_primal_dyadic_box(self.weights,self.features,self.features,ridge=10,normalization=3)
        checked = certify_primal_dyadic_box(self.weights,self.features,self.features,
            ridge=10,normalization=3,candidate_codes=result.codes)
        self.assertTrue(checked.candidate_checked)
        with self.assertRaises(PrimalUnresolved):
            certify_primal_dyadic_box(self.weights,self.features,self.features,
                ridge=10,normalization=3,candidate_codes=np.zeros_like(self.weights))
        with self.assertRaises(ValueError):
            result.codes.flags.writeable = True
        with self.assertRaises(ValueError):
            certify_primal_dyadic_box(self.weights,self.features+1,self.features,ridge=1)
        with self.assertRaises(ValueError):
            certify_primal_dyadic_box(self.weights,self.features,self.features,[1.,1.],ridge=1)
        with self.assertRaises(ValueError):
            certify_primal_dyadic_box(self.weights,self.features,self.features,ridge=1,normalization=0)
        with self.assertRaises(TypeError):
            certify_primal_dyadic_box(self.weights,self.features,self.features,ridge=.1)
        for name in ('weights','lower','upper','candidate_codes'):
            args = dict(weights=self.weights.copy(),lower=self.features.copy(),upper=self.features.copy(),ridge=1)
            if name == 'candidate_codes':
                args[name] = self.weights.copy()
            args[name].flat[0] = np.nan
            with self.assertRaises(ValueError):
                certify_primal_dyadic_box(**args)

    def test_noncontiguous_and_unaligned_inputs_remain_exact(self):
        unaligned = np.ndarray(self.features.shape,dtype=np.float64,
                               buffer=bytearray(self.features.nbytes+1),offset=1)
        unaligned[:] = self.features
        reversed_features = self.features[:,::-1]
        for features in (unaligned,reversed_features):
            result = certify_primal_dyadic_box(self.weights,features,features,ridge=10,normalization=3)
            np.testing.assert_array_equal(result.codes,oracle(self.weights,features))

    def test_overflow_and_tiny_beta_fail_closed(self):
        for backend in ('native','python'):
            with self.assertRaises(PrimalUnresolved):
                certify_primal_dyadic_box(self.weights,np.full((3,2),1e200),np.full((3,2),1e200),
                    ridge=1,arithmetic_backend=backend)
            with self.assertRaises(PrimalUnresolved):
                certify_primal_dyadic_box(self.weights,self.features,self.features,
                    ridge=Q(1,1 << 1000),arithmetic_backend=backend)

    def test_normalization_changes_the_declared_target(self):
        weights = np.array([[.21,1.7,2.6]])
        features = np.array([[1.],[1.],[0.]])
        outputs = []
        for normalization in (1,100):
            result = certify_primal_dyadic_box(weights,features,features,
                ridge=1,normalization=normalization)
            np.testing.assert_array_equal(result.codes,oracle(weights,features,
                ridge=Q(1),normalization=Q(normalization)))
            outputs.append(result.codes)
        self.assertFalse(np.array_equal(*outputs))

    def test_subnormal_gram_products_remain_enclosed(self):
        features = np.array([[1e-200,-1e-200],[-1e-200,0.]])
        exact = exact_gram(features)
        for backend in ('native','python'):
            lo,hi = _gram_bounds(features,features,arithmetic_backend=backend)
            for i,j in itertools.product(range(2),repeat=2):
                self.assertLessEqual(rational(lo[i,j]),exact[i][j])
                self.assertLessEqual(exact[i][j],rational(hi[i,j]))

    def test_native_build_binds_source_binary_and_runtime(self):
        build = prepare_primal_native()
        self.assertFalse(build['compiled_now'])
        self.assertEqual(build['call_compile_elapsed_ns'],0)
        self.assertEqual(len(build['source_sha256']),64)
        self.assertEqual(len(build['binary_sha256']),64)
        with patch('src.primal_certificate_v30._check_runtime',side_effect=RuntimeError('unsupported')):
            with self.assertRaises(RuntimeError):
                certify_primal_dyadic_box(self.weights,self.features,self.features,ridge=1)


if __name__ == '__main__':
    unittest.main()
