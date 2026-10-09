"""Small exact software fixtures; these are not empirical datasets."""
from fractions import Fraction as Q
import unittest
from unittest.mock import patch

import numpy as np

from research_v35.direct_gram import (
    DirectGramUnresolved, assess_direct_gram_budget, certify_exact_gram,
    _coefficient_bounds,
)
from research_v35.exact_gram import accumulate, add_grams, subtract_gram, dumps, loads
from src import primal_certificate_v30 as primal
from src.dyadic_row_quantizer import dyadic_row_scales
from src.exact_core import sequential_oracle
from src.low_rank_certified import _exact_solve


def exact_gram(features):
    return [[sum((Q.from_float(float(x)) * Q.from_float(float(y))
                  for x, y in zip(left, right)), Q(0))
             for right in features] for left in features]


def oracle(weights, features, ridge=Q(10), normalization=Q(256)):
    gram = exact_gram(features)
    metric = [[value / normalization + (ridge if i == j else 0)
               for j, value in enumerate(row)] for i, row in enumerate(gram)]
    codes = []
    for row, scale in zip(weights, dyadic_row_scales(weights)):
        grid = tuple(k * Q.from_float(scale) for k in range(-8, 8))
        codes.append(sequential_oracle(
            [[Q.from_float(float(value)) for value in row]], metric,
            [grid] * weights.shape[1]).codes[0])
    return np.asarray(codes, dtype=np.float64)


class DirectGramTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = primal.prepare_primal_native()

    def setUp(self):
        self.weights = np.array([[2.6, .21, -.11], [-.3, 1.7, .06]])
        self.features = np.array([[.9, -.3], [.4, .7], [-.5, .2]])

    def gram(self, features=None, normalization=256):
        return accumulate(self.features if features is None else features,
                          source_id='software-fixture', normalization=normalization)

    def test_point_and_empty_gram_match_independent_rational_oracle(self):
        for backend in ('native', 'python'):
            for features in (self.features, np.empty((3, 0))):
                result = certify_exact_gram(self.weights, self.gram(features), ridge=10,
                                           arithmetic_backend=backend)
                np.testing.assert_array_equal(result.codes, oracle(self.weights, features))
                self.assertEqual(result.point_exact_decisions, 0)
                self.assertEqual(result.interval_decisions, self.weights.size)
                self.assertEqual(result.tokens, features.shape[1])
                self.assertEqual(result.normalization_numerator, 256)
                self.assertEqual(result.normalization_denominator, 1)
                self.assertEqual(result.uncertain_features, 0)
                self.assertIn('trusted exact PSD Gram', result.guarantee)
                with self.assertRaises(ValueError):
                    result.codes.flags.writeable = True

    def test_direct_and_existing_feature_primal_target_agree(self):
        for backend in ('native', 'python'):
            direct = certify_exact_gram(self.weights, self.gram(), ridge=Q(3, 7),
                                        arithmetic_backend=backend)
            features = primal.certify_primal_dyadic_box(
                self.weights, self.features, self.features,
                ridge=Q(3, 7), normalization=256, arithmetic_backend=backend)
            np.testing.assert_array_equal(direct.codes, features.codes)
            np.testing.assert_array_equal(direct.codes, oracle(
                self.weights, self.features, ridge=Q(3, 7)))

    def test_deleted_and_independently_retained_grams_recover_exact_codes(self):
        retained = accumulate(self.features[:, :1], source_id='retained', normalization=256)
        deleted = accumulate(self.features[:, 1:], source_id='deleted', normalization=256)
        repaired = subtract_gram(add_grams(retained, deleted), deleted)
        self.assertEqual(repaired.packed, retained.packed)
        self.assertEqual(repaired.exponent, retained.exponent)
        self.assertEqual(repaired.normalization, Q(256))
        for backend in ('native', 'python'):
            result = certify_exact_gram(self.weights, repaired, ridge=Q(1, 100),
                                       arithmetic_backend=backend)
            np.testing.assert_array_equal(result.codes, oracle(
                self.weights, self.features[:, :1], ridge=Q(1, 100)))

    def test_parsed_checksum_alone_cannot_restore_psd_trust(self):
        gram = loads(dumps(self.gram()))
        self.assertFalse(gram.trusted)
        with self.assertRaises(ValueError):
            certify_exact_gram(self.weights, gram, ridge=10)

    def test_original_normalization_is_not_retained_token_count(self):
        weights = np.array([[.21, 1.7, 2.6]])
        features = np.array([[1.], [1.], [0.]])
        outputs = []
        for normalization in (1, 256):
            gram = self.gram(features, normalization=normalization)
            result = certify_exact_gram(weights, gram, ridge=1)
            np.testing.assert_array_equal(result.codes, oracle(
                weights, features, ridge=Q(1), normalization=Q(normalization)))
            outputs.append(result.codes)
        self.assertFalse(np.array_equal(*outputs))

    def test_coefficient_intervals_contain_exact_suffix_solutions(self):
        from research_v35.exact_gram import to_float64_enclosure
        gram = self.gram()
        lower, upper = to_float64_enclosure(gram)
        exact = exact_gram(self.features)
        beta = Q(3, 7)
        for backend in ('native', 'python'):
            evidence = _coefficient_bounds(lower, upper, beta, arithmetic_backend=backend)
            for i in range(1, self.features.shape[0]):
                matrix = [[exact[h][j] + (beta if h == j else 0)
                           for j in range(i, 3)] for h in range(i, 3)]
                solution = _exact_solve(matrix, [Q(1)] + [Q(0)] * (2 - i))
                for h in range(i):
                    expected = sum((exact[h][j] * solution[j-i]
                                    for j in range(i, 3)), Q(0))
                    self.assertLessEqual(abs(expected - Q.from_float(evidence.centers[i, h])),
                                         Q.from_float(evidence.radii[i, h]))

    def test_zero_gram_ties_choose_lower_code(self):
        weights = np.array([[.5, 1.5, 7.], [-.5, -1.5, 7.]])
        gram = self.gram(np.zeros((3, 2)))
        for backend in ('native', 'python'):
            result = certify_exact_gram(weights, gram, ridge=1, arithmetic_backend=backend)
            np.testing.assert_array_equal(result.codes, [[0., 1., 7.], [-1., -2., 7.]])

    def test_wrong_nominal_proposals_cannot_override_residuals(self):
        gram = self.gram()
        def broken(nominal, inverse, i, beta):
            return np.full(len(nominal)-i, 1e10), True
        for backend in ('native', 'python'):
            with patch('src.primal_certificate_v30._suffix_proposal', side_effect=broken):
                with self.assertRaises(DirectGramUnresolved):
                    certify_exact_gram(self.weights, gram, ridge=10, arithmetic_backend=backend)

    def test_candidate_and_input_contracts(self):
        gram = self.gram()
        result = certify_exact_gram(self.weights, gram, ridge=10)
        checked = certify_exact_gram(self.weights, gram, ridge=10, candidate_codes=result.codes)
        self.assertTrue(checked.candidate_checked)
        with self.assertRaises(DirectGramUnresolved):
            certify_exact_gram(self.weights, gram, ridge=10, candidate_codes=np.zeros_like(self.weights))
        with self.assertRaises(ValueError):
            certify_exact_gram(self.weights, gram, [1., 1.], ridge=1)
        for ridge in (0, -1):
            with self.assertRaises(ValueError):
                certify_exact_gram(self.weights, gram, ridge=ridge)
        with self.assertRaises(TypeError):
            certify_exact_gram(self.weights, gram, ridge=.1)
        with self.assertRaises(ValueError):
            certify_exact_gram(self.weights[:, :2].copy(), gram, ridge=1)
        for name in ('weights', 'candidate_codes'):
            options = dict(weights=self.weights.copy(), gram=gram, ridge=1)
            options[name] = self.weights.copy()
            options[name].flat[0] = np.nan
            with self.assertRaises(ValueError):
                certify_exact_gram(**options)

    def test_arbitrary_gram_arrays_and_fake_psd_flags_are_refused(self):
        class FakeGram:
            width = 3
            normalization = Q(256)
            trusted = True
            positive_semidefinite = True
        for gram in (np.eye(3), (np.eye(3), np.eye(3)), FakeGram()):
            with self.assertRaises((TypeError, ValueError)):
                certify_exact_gram(self.weights, gram, ridge=1)

    def test_resource_admission_precedes_enclosure_and_compilation(self):
        gram = self.gram()
        with patch('research_v35.exact_gram.to_float64_enclosure', side_effect=AssertionError('no arrays')):
            with patch('src.primal_certificate_v30.prepare_primal_native', side_effect=AssertionError('no compiler')):
                with self.assertRaises(DirectGramUnresolved):
                    certify_exact_gram(self.weights, gram, ridge=1,
                                      budget=primal.PrimalBudget(max_work_units=1))
        limits = primal.PrimalBudget(max_work_units=6_000_000_000,
                                     max_workspace_bytes=512*1024*1024)
        pilot = assess_direct_gram_budget(rows=4, width=768, budget=limits)
        wide = assess_direct_gram_budget(rows=768, width=3072, budget=limits)
        self.assertTrue(pilot['admitted'])
        self.assertEqual(pilot['work_units'], 768**3 + 4*768**2 + 2*4*16)
        self.assertFalse(wide['admitted'])
        self.assertEqual(pilot['tokens'], 0)

    def test_native_result_binds_unchanged_strict_kernel(self):
        result = certify_exact_gram(self.weights, self.gram(), ridge=10)
        self.assertEqual(result.native_source_sha256, self.build['source_sha256'])
        self.assertEqual(result.native_binary_sha256, self.build['binary_sha256'])
        self.assertEqual(result.native_flags, tuple(self.build['flags']))
        self.assertIn('-ffp-contract=off', result.native_flags)
        self.assertIn('-fno-fast-math', result.native_flags)
        self.assertEqual(result.native_attempted_decisions, self.weights.size)
        self.assertEqual(result.native_certified_decisions, self.weights.size)
        self.assertEqual(result.compile_elapsed_ns, 0)

    def test_subnormal_feature_products_and_tiny_beta_fail_closed(self):
        weights = self.weights[:, :2].copy()
        features = np.array([[1e-200, -1e-200], [-1e-200, 0.]])
        for backend in ('native', 'python'):
            result = certify_exact_gram(weights, self.gram(features), ridge=1,
                                       arithmetic_backend=backend)
            np.testing.assert_array_equal(result.codes, oracle(
                weights, features, ridge=Q(1)))
            with self.assertRaises(DirectGramUnresolved):
                certify_exact_gram(self.weights, self.gram(), ridge=Q(1, 1 << 1000),
                                   arithmetic_backend=backend)


if __name__ == '__main__':
    unittest.main()
