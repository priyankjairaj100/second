"""Exact moment and canonical-state verification, without empirical data."""

import unittest
from dataclasses import replace
from fractions import Fraction as F

from src.response_moments import ResponseBasis, ResponseIndex, RecordMoments, record_moments, extract_record_moments


def direct_gram(records, coefficients):
    """Construct all feature columns and multiply, independently of moments."""
    a = (F(1),) + tuple(map(F, coefficients))
    d = len(records[0][0])
    columns = [[] for _ in range(d)]
    for jets in records:
        for i in range(d):
            columns[i].extend(sum(a[t] * jets[t][i][k] for t in range(len(a)))
                              for k in range(len(jets[0][0])))
    return tuple(tuple(sum((x * y for x, y in zip(columns[i], columns[j])), F(0))
                       for j in range(d)) for i in range(d))


class ResponseMomentTests(unittest.TestCase):
    def setUp(self):
        self.basis = ResponseBasis("fixed-jet-program-fixture-v1", 2, 3, True)
        self.jets = (
            (((1, 2), (3, 4)), ((0, 1), (2, 0)), ((-1, 0), (1, 2))),
            (((2,), (1,)), ((3,), (-1,)), ((0,), (2,))),
            (((F(1, 2),), (F(2, 3),)), ((1,), (0,)), ((-2,), (1,))),
        )
        self.records = tuple(record_moments(self.basis, str(i), f"source-{i}", jet)
                             for i, jet in enumerate(self.jets))
        self.index = ResponseIndex.from_records(self.basis, self.records)

    def test_quadratic_gram_matches_explicit_features(self):
        for a in ((0, 0), (2, -3), (F(1, 3), F(-2, 5))):
            gram = self.index.gram(a)
            self.assertEqual(gram, direct_gram(self.jets, a))
            self.assertEqual(self.index.squared_frobenius_norm(a), gram[0][0] + gram[1][1])
        self.assertEqual(self.index.total_columns, 4)

    def test_offdiagonal_cross_moment_is_oriented(self):
        # C_01 is generally nonsymmetric; retaining only its diagonal fails.
        c01 = self.records[0].cross_moments[1]
        self.assertNotEqual(c01[0][1], c01[1][0])
        self.assertEqual(self.index.gram((2, 3)), direct_gram(self.jets, (2, 3)))

    def test_deletion_matches_fresh_and_order_independent_bytes(self):
        left = self.index.remove((self.records[0],)).remove((self.records[2],))
        right = self.index.remove((self.records[2], self.records[0]))
        fresh = ResponseIndex.from_records(self.basis, (self.records[1],))
        self.assertEqual(left.canonical_bytes(), right.canonical_bytes())
        self.assertEqual(left.canonical_bytes(), fresh.canonical_bytes())
        self.assertEqual(left.gram((3, 2)), direct_gram((self.jets[1],), (3, 2)))
        self.assertEqual(left.retained_ids, ("1",))

    def test_constructor_order_is_canonical(self):
        reverse = ResponseIndex.from_records(self.basis, reversed(self.records))
        self.assertEqual(reverse.canonical_bytes(), self.index.canonical_bytes())

    def test_delete_all_and_empty_constructor_agree(self):
        empty = ResponseIndex.from_records(self.basis, ())
        self.assertEqual(self.index.remove(self.records).canonical_bytes(), empty.canonical_bytes())
        self.assertEqual(empty.gram((2, -1)), ((F(0), F(0)), (F(0), F(0))))
        self.assertEqual(empty.squared_frobenius_norm((2, -1)), 0)

    def test_wrong_payload_rejected_before_subtraction(self):
        wrong = replace(self.records[0], source_digest="other-content")
        before = self.index.canonical_bytes()
        with self.assertRaisesRegex(ValueError, "committed payload"):
            self.index.remove((wrong,))
        self.assertEqual(self.index.canonical_bytes(), before)
        with self.assertRaises(KeyError):
            self.index.remove((self.records[0],)).remove((self.records[0],))
        with self.assertRaisesRegex(ValueError, "unique"):
            self.index.remove((self.records[0], self.records[0]))

    def test_explicit_extractor_adapter(self):
        result = extract_record_moments(self.basis, "0", "source-0", self.jets[0], lambda record: record)
        self.assertEqual(result.canonical_bytes(), self.records[0].canonical_bytes())
        self.assertFalse(self.basis.corpus_independence_verified_by_module)

    def test_canonical_payload_parser_roundtrip(self):
        for record in self.records:
            payload = record.canonical_bytes()
            self.assertEqual(RecordMoments.from_canonical_bytes(payload), record)
            with self.assertRaises(ValueError):
                RecordMoments.from_canonical_bytes(payload + b" ")

    def test_nonexact_inputs_rejected(self):
        for value in (True, 0.2):
            with self.subTest(value=value), self.assertRaises(TypeError):
                self.index.gram((value, 0))
            with self.subTest(value=value), self.assertRaises(TypeError):
                record_moments(self.basis, "bad", "bad", (((value,), (0,)), ((0,), (0,)), ((0,), (0,))))
        with self.assertRaises(ValueError):
            ResponseBasis("unattested", 2, 3, False)

    def test_shape_and_manifest_mismatch(self):
        with self.assertRaises(ValueError):
            self.index.gram((1,))
        wrong_basis = ResponseBasis("another-extractor", 2, 3, True)
        wrong = record_moments(wrong_basis, "0", "source-0", self.jets[0])
        with self.assertRaisesRegex(ValueError, "same fixed"):
            ResponseIndex.from_records(self.basis, (wrong,))
        with self.assertRaisesRegex(ValueError, "different basis"):
            self.index.remove((wrong,))


if __name__ == "__main__":
    unittest.main()
