"""Small software fixtures; no empirical dataset or timing evidence."""
from dataclasses import replace
from fractions import Fraction
import hashlib
import json
import math
import struct
import unittest

import numpy as np

from research_v35.exact_gram import (
    ExactGram, GramAdmissionError, GramBudget, accumulate, add_grams,
    assess_features, dumps, loads, require_trusted_gram, subtract_gram,
    to_float64_enclosure,
)


def exact_entries(gram):
    scale = Fraction(2) ** gram.exponent
    return tuple(value * scale for value in gram.packed)


def fraction_oracle(array):
    return tuple(sum((Fraction.from_float(float(array[i, k])) *
                      Fraction.from_float(float(array[j, k]))
                      for k in range(array.shape[1])), Fraction(0))
                 for i in range(array.shape[0]) for j in range(i + 1))


class ExactGramTests(unittest.TestCase):
    def test_fraction_differential(self):
        rng = np.random.default_rng(738)
        for width, tokens in ((1, 0), (1, 1), (3, 7), (8, 11)):
            x = np.ldexp(rng.integers(-128, 129, size=(width, tokens)).astype(float),
                         rng.integers(-12, 13, size=(width, tokens)))
            gram = accumulate(x, source_id="fixture")
            self.assertEqual(exact_entries(gram), fraction_oracle(x))
            self.assertEqual(gram.admission.product_terms, width * (width + 1) // 2 * tokens)

    def test_binary64_roundoff_is_not_accumulated(self):
        x = np.array([[1., 2.**-27, 2.**-27], [.1, -.2, .3]], dtype=np.float64)
        gram = accumulate(x, source_id="mixed")
        self.assertEqual(exact_entries(gram), fraction_oracle(x))
        self.assertNotEqual(exact_entries(gram)[0], Fraction.from_float(float((x @ x.T)[0, 0])))

    def test_source_algebra_and_canonical_bytes(self):
        a = accumulate(np.array([[1., .25], [3., -2.]]), source_id="a")
        b = accumulate(np.array([[.125, -7.], [2., .5]]), source_id="b")
        pooled = add_grams(a, b)
        self.assertEqual(dumps(subtract_gram(pooled, a)), dumps(b))
        self.assertEqual(dumps(add_grams(b, a)), dumps(pooled))
        self.assertEqual(pooled.normalization, Fraction(256))
        self.assertEqual(subtract_gram(pooled, a).tokens, 2)
        self.assertEqual(exact_entries(pooled), tuple(x + y for x, y in zip(exact_entries(a), exact_entries(b))))

    def test_commitment_identity_is_not_id_alone(self):
        a = accumulate(np.ones((2, 2)), source_id="a")
        other = accumulate(np.full((2, 2), 2.), source_id="a")
        with self.assertRaisesRegex(ValueError, "complete source commitments"):
            subtract_gram(a, other)
        with self.assertRaisesRegex(ValueError, "disjoint"):
            add_grams(a, a)

    def test_normalization_mismatch(self):
        a = accumulate(np.ones((1, 1)), source_id="a", normalization=256)
        b = accumulate(np.ones((1, 1)), source_id="b", normalization=128)
        with self.assertRaisesRegex(ValueError, "normalization"):
            add_grams(a, b)
        with self.assertRaises(ValueError):
            accumulate(np.ones((1, 1)), source_id="a", normalization=256.)

    def test_empty_and_zero_canonicalization(self):
        empty = accumulate(np.empty((2, 0)), source_id="empty")
        zero = accumulate(np.zeros((2, 3)), source_id="zero")
        large = accumulate(np.full((2, 1), 2.**900), source_id="large")
        self.assertEqual(empty.exponent, 0)
        self.assertEqual(zero.exponent, 0)
        self.assertEqual(exact_entries(add_grams(empty, large)), exact_entries(large))
        deleted = subtract_gram(large, large)
        self.assertEqual(deleted.sources, ())
        self.assertEqual(deleted.tokens, 0)
        self.assertEqual(deleted.exponent, 0)
        self.assertEqual(exact_entries(deleted), (0, 0, 0))
        self.assertEqual(dumps(loads(dumps(deleted))), dumps(deleted))

    def test_subnormal_exactness(self):
        tiny = np.nextafter(0., 1.)
        x = np.array([[tiny, -tiny], [2 * tiny, 0.]])
        gram = accumulate(x, source_id="tiny")
        self.assertEqual(exact_entries(gram), fraction_oracle(x))
        lo, hi = to_float64_enclosure(gram)
        self.assertEqual(lo[0, 0], 0.)
        self.assertEqual(hi[0, 0], tiny)

    def test_enclosures_against_exact_values(self):
        x = np.array([[.1, .2, .3], [-.5, .7, .9], [0., 1., -1.]])
        gram = accumulate(x, source_id="bounds")
        lo, hi = to_float64_enclosure(gram)
        k = 0
        for i in range(gram.width):
            for j in range(i + 1):
                exact = exact_entries(gram)[k]
                k += 1
                self.assertLessEqual(Fraction.from_float(float(lo[i, j])), exact)
                self.assertGreaterEqual(Fraction.from_float(float(hi[i, j])), exact)
                self.assertEqual(lo[i, j], lo[j, i])
                self.assertEqual(hi[i, j], hi[j, i])

    def test_enclosure_overflow_is_outward(self):
        gram = accumulate(np.array([[2.**900], [-2.**900]]), source_id="overflow")
        lo, hi = to_float64_enclosure(gram)
        self.assertEqual(lo[0, 0], np.finfo(float).max)
        self.assertEqual(hi[0, 0], math.inf)
        self.assertEqual(lo[1, 0], -math.inf)
        self.assertEqual(hi[1, 0], -np.finfo(float).max)

    def test_enclosure_rechecks_supplied_integer_budget(self):
        gram = accumulate(np.array([[1., 2.**-100]]), source_id="wide")
        with self.assertRaisesRegex(GramAdmissionError, "enclosure integer"):
            to_float64_enclosure(gram, budget=replace(GramBudget(), max_integer_bits=100))

    def test_invalid_feature_words_and_type(self):
        for x in (np.array([[math.nan]]), np.array([[math.inf]]), np.array([[1.]], dtype=np.float32), [[1.]]):
            with self.assertRaises(ValueError):
                accumulate(x, source_id="bad")

    def test_admission_before_products(self):
        x = np.ones((4, 5))
        with self.assertRaisesRegex(GramAdmissionError, "contribution"):
            assess_features(x, budget=replace(GramBudget(), max_product_terms=49))
        with self.assertRaisesRegex(GramAdmissionError, "bit budget"):
            accumulate(np.array([[1., np.nextafter(0., 1.)]]), source_id="wide")
        with self.assertRaises(GramAdmissionError):
            assess_features(x, budget=replace(GramBudget(), max_memory_bytes=100))

    def test_roundtrip_is_not_trust(self):
        gram = accumulate(np.array([[.1, .2], [.3, .4]]), source_id="a")
        data = dumps(gram)
        parsed = loads(data)
        self.assertFalse(parsed.trusted)
        self.assertEqual(dumps(parsed), data)
        with self.assertRaisesRegex(ValueError, "trusted"):
            require_trusted_gram(parsed)
        with self.assertRaisesRegex(ValueError, "both external"):
            loads(data, trusted_sha256=hashlib.sha256(data).hexdigest())
        restored = loads(data, trusted_sha256=hashlib.sha256(data).hexdigest(), expected_sources=gram.sources)
        require_trusted_gram(restored)
        self.assertEqual(dumps(restored), data)
        with self.assertRaisesRegex(ValueError, "commitments"):
            loads(data, trusted_sha256=hashlib.sha256(data).hexdigest(), expected_sources=())
        with self.assertRaises(TypeError):
            ExactGram(1, 0, Fraction(256), 0, (0,), ())

    def test_archive_checksum_and_canonical_header(self):
        gram = accumulate(np.ones((2, 1)), source_id="a")
        data = dumps(gram)
        with self.assertRaises(ValueError):
            loads(data[:-1] + bytes([data[-1] ^ 1]))
        n = struct.unpack(">I", data[8:12])[0]
        header = json.loads(data[12:12 + n])
        header["extra"] = "not canonical"
        encoded = json.dumps(header).encode()
        body = data[:8] + struct.pack(">I", len(encoded)) + encoded + data[12 + n:-32]
        with self.assertRaises(ValueError):
            loads(body + hashlib.sha256(body).digest())

    def test_parser_and_serializer_account_python_representation(self):
        gram = accumulate(np.ones((32, 1)), source_id="a")
        data = dumps(gram)
        budget = replace(GramBudget(), max_memory_bytes=10_000)
        self.assertLess(len(data) * 3, budget.max_memory_bytes)
        with self.assertRaisesRegex(GramAdmissionError, "representation"):
            loads(data, budget=budget)
        with self.assertRaisesRegex(GramAdmissionError, "buffer"):
            dumps(gram, budget=budget)


if __name__ == "__main__":
    unittest.main()
