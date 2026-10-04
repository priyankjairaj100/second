"""Independent numerical boundary checks; these are software fixtures."""
from decimal import Decimal, localcontext
from fractions import Fraction
import math
import struct
import unittest

from src.certified_intervals import (
    ArithmeticLimit, Interval, binary64_enclosure, round_fraction,
    round_exp, round_sqrt, round_erf, round_tanh,
)


def bits(x):
    return struct.unpack('>Q', struct.pack('>d', x))[0]


class IndependentPrimitiveReviewTests(unittest.TestCase):
    def test_rounding_subnormal_normal_and_overflow_boundaries(self):
        tiny = Fraction(1, 1 << 1074)
        self.assertEqual(bits(round_fraction(tiny / 2)), 0)
        self.assertEqual(bits(round_fraction(-tiny / 2)), 1 << 63)
        self.assertEqual(bits(round_fraction(3 * tiny / 2)), 2)
        self.assertEqual(bits(round_fraction(-3 * tiny / 2)), (1 << 63) | 2)
        normal = Fraction(1, 1 << 1022)
        self.assertEqual(bits(round_fraction(normal - tiny / 2)), 1 << 52)
        maximum = Fraction((1 << 53) - 1) * (1 << 971)
        halfway = maximum + (1 << 970)
        self.assertEqual(round_fraction(halfway - 1), float.fromhex('0x1.fffffffffffffp+1023'))
        self.assertTrue(math.isinf(round_fraction(halfway)))
        self.assertTrue(math.isinf(round_fraction(-halfway)))
        with self.assertRaises(ArithmeticLimit):
            binary64_enclosure(Interval(maximum, halfway))

    def test_rational_rounding_agrees_with_independent_python_conversion(self):
        for numerator in (1, 3, 5, (1 << 53) - 1, (1 << 54) + 3):
            for shift in (-1077, -1050, -55, 0, 50, 970):
                scale = Fraction(1 << shift) if shift >= 0 else Fraction(1, 1 << -shift)
                for sign in (-1, 1):
                    value = sign * numerator * scale / 3
                    try:
                        expected = float(value)
                    except OverflowError:
                        self.assertTrue(math.isinf(round_fraction(value)))
                    else:
                        self.assertEqual(bits(round_fraction(value)), bits(expected))

    def test_exp_intervals_contain_high_precision_independent_values(self):
        # Decimal provides a separate implementation. This check is not the proof.
        for value in (Fraction(-30), Fraction(-1), Fraction(-1, 3),
                      Fraction(1, 3), Fraction(1), Fraction(30)):
            enclosed = Interval.point(value, 128).exp()
            with localcontext() as ctx:
                ctx.prec = 200
                estimate = Fraction((Decimal(value.numerator) / Decimal(value.denominator)).exp())
            uncertainty = Fraction(1, 10**170)
            self.assertLessEqual(enclosed.lo, estimate - uncertainty)
            self.assertGreaterEqual(enclosed.hi, estimate + uncertainty)

    def test_sqrt_certificates_and_signed_zero_contract(self):
        for value in (Fraction(1, 3), Fraction(2), Fraction(7, 11), Fraction(1, 1 << 2000)):
            enclosed = Interval.point(value, 128).sqrt()
            self.assertLessEqual(enclosed.lo * enclosed.lo, value)
            self.assertGreaterEqual(enclosed.hi * enclosed.hi, value)
        for function in (round_sqrt, round_erf, round_tanh):
            self.assertEqual(bits(function(-0.0)), 1 << 63)
        self.assertEqual(round_exp(-0.0), 1.0)


class IndependentJetReviewTests(unittest.TestCase):
    def test_mixed_derivatives_match_independent_rational_formula(self):
        from src.certified_transformer import Jet
        p = 128
        zero = Interval.point(0, p)
        one = Interval.point(1, p)
        h = ((zero, zero), (zero, zero))
        x = Jet(Interval.point(2, p), (one, zero), h)
        y = Jet(Interval.point(3, p), (zero, one), h)
        result = x / y + x * y
        self.assertTrue(result.value.contains(Fraction(20, 3)))
        self.assertTrue(result.gradient[0].contains(Fraction(10, 3)))
        self.assertTrue(result.gradient[1].contains(Fraction(16, 9)))
        self.assertTrue(result.hessian[0][0].contains(0))
        self.assertTrue(result.hessian[0][1].contains(Fraction(8, 9)))
        self.assertTrue(result.hessian[1][0].contains(Fraction(8, 9)))
        self.assertTrue(result.hessian[1][1].contains(Fraction(4, 27)))
        finite = 2.0 / 3.0 + 2.0 * 3.0
        self.assertLessEqual(abs(Fraction.from_float(finite) - Fraction(20, 3)), result.error)

    def test_error_bound_covers_cancellation_and_underflow(self):
        from src.certified_transformer import Jet, UnsupportedCertificate
        for xf, yf in ((1.0 + 2**-52, 1.0 - 2**-53),
                       (float.fromhex('0x0.0000000000001p-1022'), 0.5)):
            xq, yq = Fraction.from_float(xf), Fraction.from_float(yf)
            x, y = Jet.constant(xq, 0, 128), Jet.constant(yq, 0, 128)
            result = x * y - x
            ideal = xq * yq - xq
            finite = xf * yf - xf
            self.assertLessEqual(abs(Fraction.from_float(finite) - ideal), result.error)
        maximum = Fraction.from_float(float.fromhex('0x1.fffffffffffffp+1023'))
        with self.assertRaises(UnsupportedCertificate):
            Jet.constant(maximum, 0, 128) * 2


class IndependentSoftmaxReviewTests(unittest.TestCase):
    def test_mixed_score_curvature_enters_probability_hessian(self):
        from src.certified_transformer import Jet, _softmax
        p = 128
        zero, one = Interval.point(0, p), Interval.point(1, p)
        h = ((zero, zero), (zero, zero))
        x = Jet(one, (one, zero), h)
        y = Jet(one, (zero, one), h)
        const = lambda value: Jet.constant(Fraction(value), 2, p)
        first, second = _softmax((x * y, const(1)), const)
        self.assertTrue(first.value.contains(Fraction(1, 2)))
        self.assertTrue(first.gradient[0].contains(Fraction(1, 4)))
        self.assertTrue(first.gradient[1].contains(Fraction(1, 4)))
        self.assertTrue(first.hessian[0][0].contains(0))
        self.assertTrue(first.hessian[0][1].contains(Fraction(1, 4)))
        self.assertTrue(first.hessian[1][0].contains(Fraction(1, 4)))
        self.assertTrue(first.hessian[1][1].contains(0))
        self.assertTrue(second.hessian[0][1].contains(Fraction(-1, 4)))

    def test_max_shift_prevents_positive_exponential_overflow(self):
        from src.certified_transformer import Jet, _Finite, _softmax
        finite = _softmax((_Finite(0.0), _Finite(1000.0)), lambda value: _Finite(float(value)))
        self.assertEqual(tuple(x.value for x in finite), (0.0, 1.0))
        const = lambda value: Jet.constant(Fraction(value), 0, 128)
        proof = _softmax((const(0), const(1000)), const)
        for actual, item in zip(finite, proof):
            self.assertLessEqual(item.value.lo - item.error, Fraction.from_float(actual.value))
            self.assertGreaterEqual(item.value.hi + item.error, Fraction.from_float(actual.value))
