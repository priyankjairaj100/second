"""Compact-response arithmetic checks; no empirical coverage claims."""

import json
import unittest
from fractions import Fraction as F

from src.exact_core import reverse_ldl
from src.response_moments import ResponseBasis, ResponseIndex, record_moments
from src.linear_response import (
    LinearRecordMoments, LinearResponseIndex, linear_record_moments,
    linear_response_enclosure, shifted_linear_response_bound,
)


def subtract(a, b):
    return tuple(tuple(x-y for x, y in zip(ar, br)) for ar, br in zip(a, b))


def scale(matrix, coefficient):
    return tuple(tuple(coefficient*x for x in row) for row in matrix)


def psd_2x2(matrix):
    return matrix[0][0] >= 0 and matrix[1][1] >= 0 and matrix[0][0]*matrix[1][1] >= matrix[0][1]**2


class LinearResponseTests(unittest.TestCase):
    def setUp(self):
        self.basis = ResponseBasis("fixed-response", 2, 3, True)
        self.jets = (
            (((1, 2), (3, 4)), ((0, 1), (2, 0)), ((-1, 0), (1, 2))),
            (((2,), (1,)), ((3,), (-1,)), ((0,), (2,))),
        )
        self.records = tuple(linear_record_moments(self.basis, str(i), str(i), jet)
                             for i, jet in enumerate(self.jets))
        self.index = LinearResponseIndex.from_records(self.basis, self.records)
        self.full = ResponseIndex.from_records(self.basis,
            tuple(record_moments(self.basis, str(i), str(i), jet) for i, jet in enumerate(self.jets)))
        error_basis = ResponseBasis("zero-remainder", 1, 5, True)
        self.errors = ResponseIndex.from_records(error_basis,
            tuple(record_moments(error_basis, str(i), str(i), (((0,),),)*5) for i in range(2)))

    def test_compact_contraction_matches_direct_omitted_psd_term(self):
        for a in ((0, 0), (2, -1), (F(1, 5), F(-1, 7))):
            query = self.index.contract(a)
            full = self.full.gram(a)
            omitted = subtract(full, query.raw_linear_gram)
            self.assertTrue(psd_2x2(omitted))
            self.assertEqual(omitted[0][0]+omitted[1][1], query.omitted_psd_trace)
            self.assertEqual(full[0][0]+full[1][1], query.full_response_squared_frobenius_norm)
            beta_identity = ((query.omitted_psd_trace, F(0)), (F(0), query.omitted_psd_trace))
            self.assertTrue(psd_2x2(subtract(beta_identity, omitted)))

    def test_exact_relative_enclosure_with_zero_feature_residual(self):
        a, ridge, m0 = (F(1, 10), F(-1, 10)), F(10), F(3)
        proof = linear_response_enclosure(self.index, self.errors, a, ridge, m0)
        self.assertTrue(proof.usable)
        full = self.full.gram(a)
        target = tuple(tuple(full[i][j]/m0 + (ridge if i == j else 0) for j in range(2)) for i in range(2))
        self.assertTrue(psd_2x2(subtract(target, scale(proof.linear_covariance, proof.lower_scale))))
        self.assertTrue(psd_2x2(subtract(scale(proof.linear_covariance, proof.upper_scale), target)))
        self.assertFalse(proof.descriptor_premises_verified_by_module)

    def test_shifted_proposal_psd_and_bound(self):
        a, ridge, m0 = (2, -3), F(2), F(3)
        proof = shifted_linear_response_bound(self.index, self.errors, a, ridge, m0)
        self.assertTrue(psd_2x2(proof.raw_surrogate_gram))
        target = self.full.gram(a)
        difference = subtract(proof.raw_surrogate_gram, target)
        self.assertTrue(psd_2x2(difference))
        beta_i = ((proof.raw_absolute_gram_error, F(0)), (F(0), proof.raw_absolute_gram_error))
        self.assertTrue(psd_2x2(subtract(beta_i, difference)))
        shifted_covariance = tuple(tuple(proof.raw_surrogate_gram[i][j]/m0 +
                                         (ridge if i == j else 0) for j in range(2)) for i in range(2))
        reverse_ldl(shifted_covariance)

    def test_indefinite_linear_proposal_abstains_but_shift_survives(self):
        basis = ResponseBasis("one-dimensional-direction", 1, 2, True)
        record = linear_record_moments(basis, "a", "A", (((1,),), ((1,),)))
        index = LinearResponseIndex.from_records(basis, (record,))
        eb = ResponseBasis("zero-errors", 1, 4, True)
        errors = ResponseIndex.from_records(eb, (record_moments(eb, "a", "A", (((0,),),)*4),))
        proof = linear_response_enclosure(index, errors, (-2,), 1, 1)
        self.assertFalse(proof.usable)
        shifted = shifted_linear_response_bound(index, errors, (-2,), 1, 1)
        self.assertEqual(shifted.raw_surrogate_gram, ((F(1),),))
        # Shift is safe, but a useful relative lower scale is not promised.
        self.assertFalse(shifted.relative_enclosure_usable)

    def test_deletion_and_parser_canonical(self):
        for record in self.records:
            self.assertEqual(LinearRecordMoments.from_canonical_bytes(record.canonical_bytes()), record)
        repaired = self.index.remove((self.records[0],))
        fresh = LinearResponseIndex.from_records(self.basis, self.records[1:])
        self.assertEqual(repaired.canonical_bytes(), fresh.canonical_bytes())
        self.assertEqual(self.index.remove(self.records).canonical_bytes(),
                         LinearResponseIndex.from_records(self.basis, ()).canonical_bytes())
        self.assertEqual(self.index.remove(self.records).canonical_bytes(),
                         self.index.remove(self.records[1:]).remove(self.records[:1]).canonical_bytes())

    def test_storage_count_and_schema_no_quadratic_matrix_bank(self):
        self.assertEqual(self.index.stored_rational_count, 3*2*2+2*2)
        payload = json.loads(self.index.canonical_bytes())
        self.assertEqual(len(payload["first_response"]), 2)
        self.assertNotIn("cross_moments", payload)
        self.assertEqual(len(payload["tangent_scalar_gram"]), 2)

    def test_zero_direction_basis(self):
        basis = ResponseBasis("constant-only", 1, 1, True)
        record = linear_record_moments(basis, "a", "A", (((2,),),))
        index = LinearResponseIndex.from_records(basis, (record,))
        self.assertEqual(index.contract(()).raw_linear_gram, ((F(4),),))
        self.assertEqual(index.contract(()).omitted_psd_trace, 0)
        self.assertEqual(index.stored_rational_count, 1)

    def test_invalid_payloads_and_coefficients(self):
        with self.assertRaises(ValueError):
            self.index.remove((self.records[0], self.records[0]))
        for value in (True, 0.1):
            with self.assertRaises(TypeError):
                self.index.contract((value, 0))
        with self.assertRaises(ValueError):
            LinearRecordMoments.from_canonical_bytes(self.records[0].canonical_bytes() + b" ")


if __name__ == "__main__":
    unittest.main()
