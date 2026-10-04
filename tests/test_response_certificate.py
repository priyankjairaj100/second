"""Exact response-descriptor composition checks; no neural proof inferred."""

import unittest
from fractions import Fraction as F

from src.response_moments import ResponseBasis, ResponseIndex, record_moments
from src.response_certificate import dyadic_sqrt_upper, response_gram_enclosure


class ResponseCertificateTests(unittest.TestCase):
    def setUp(self):
        self.feature_basis = ResponseBasis("fixed-feature", 1, 2, True)
        self.descriptor_basis = ResponseBasis("fixed-descriptors", 1, 4, True)
        self.features = (
            record_moments(self.feature_basis, "a", "A", (((1, 2),), ((3, 0),))),
            record_moments(self.feature_basis, "b", "B", (((2,),), ((-1,),))),
        )
        # b=(numerical/base error,directional error,curvature,residual slope).
        self.descriptors = (
            record_moments(self.descriptor_basis, "a", "A", (((1,),), ((2,),), ((3,),), ((4,),))),
            record_moments(self.descriptor_basis, "b", "B", (((0,),), ((1,),), ((2,),), ((3,),))),
        )
        self.index = ResponseIndex.from_records(self.feature_basis, self.features)
        self.error_index = ResponseIndex.from_records(self.descriptor_basis, self.descriptors)

    def test_exact_error_polynomial_includes_cross_terms(self):
        bound = response_gram_enclosure(self.index, self.error_index, (-2,), 5, 3)
        # v=(1,2,2,3), record errors 23 and 15.
        self.assertEqual(bound.squared_feature_error_bound_normalized, F(23**2 + 15**2, 5))
        # Response features (-5,2), (4); squared norm = 45.
        self.assertEqual(bound.squared_surrogate_frobenius_norm_normalized, 9)
        self.assertEqual(bound.raw_surrogate_gram, ((F(45),),))
        self.assertFalse(bound.descriptor_premises_verified_by_module)
        self.assertEqual(bound.raw_absolute_gram_error, 5 * bound.normalized_absolute_gram_error)

    def test_derived_bound_contains_direct_scalar_gram_change(self):
        bound = response_gram_enclosure(self.index, self.error_index, (1,), 1, 0)
        # Choose actual error +1 on each feature column, within each record bound.
        surrogate = (4, 2, 1)
        actual = (5, 3, 2)
        difference = abs(sum(x*x for x in actual) - sum(x*x for x in surrogate))
        self.assertLessEqual(difference, bound.normalized_absolute_gram_error)

    def test_zero_error_is_exact(self):
        zeros = tuple(record_moments(self.descriptor_basis, r.record_id, r.source_digest,
                                    (((0,),),) * 4) for r in self.features)
        error_index = ResponseIndex.from_records(self.descriptor_basis, zeros)
        bound = response_gram_enclosure(self.index, error_index, (3,), 7)
        self.assertEqual(bound.normalized_absolute_gram_error, 0)

    def test_deletion_composes_with_fresh_identical_bounds(self):
        repaired = response_gram_enclosure(self.index.remove((self.features[0],)),
                                          self.error_index.remove((self.descriptors[0],)), (2,), 5)
        fresh = response_gram_enclosure(ResponseIndex.from_records(self.feature_basis, self.features[1:]),
                                       ResponseIndex.from_records(self.descriptor_basis, self.descriptors[1:]),
                                       (2,), 5)
        self.assertEqual(repaired, fresh)

    def test_identity_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "identities"):
            response_gram_enclosure(self.index, self.error_index.remove((self.descriptors[0],)), (1,), 2)

    def test_dyadic_sqrt_is_outward_and_minimal(self):
        for x in (F(0), F(1, 9), F(2), F(4), F(7, 3), F(1, 2**41)):
            for bits in (0, 1, 7, 32):
                upper = dyadic_sqrt_upper(x, bits)
                step = F(1, 2**bits)
                self.assertGreaterEqual(upper*upper, x)
                if upper:
                    self.assertLess((upper-step)**2, x)
        self.assertEqual(dyadic_sqrt_upper(F(9, 16), 2), F(3, 4))

    def test_strict_numerics(self):
        for value in (True, 0.25):
            with self.assertRaises(TypeError):
                dyadic_sqrt_upper(value)
            with self.assertRaises(TypeError):
                response_gram_enclosure(self.index, self.error_index, (value,), 2)
        with self.assertRaises(ValueError):
            dyadic_sqrt_upper(-1)
        with self.assertRaises(ValueError):
            response_gram_enclosure(self.index, self.error_index, (1,), 0)


if __name__ == "__main__":
    unittest.main()
