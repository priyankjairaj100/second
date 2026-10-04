"""Numerical contract checks.  These are not research experiments."""

from decimal import Decimal, localcontext
from fractions import Fraction as F
import math
import struct
import unittest

from src.certified_intervals import (
    ArithmeticLimit, Interval, UnresolvedRounding, binary64_enclosure,
    pi_interval, round_erf, round_exp, round_fraction, round_interval,
    round_sqrt, round_tanh,
)


def bits(value):
    return struct.unpack(">Q", struct.pack(">d", value))[0]


class CertifiedIntervalTests(unittest.TestCase):
    def test_types_domains_and_precision(self):
        for args in ((1, 0), (True, 2), (0.0, 1), (0, 1, 0)):
            with self.assertRaises((TypeError, ValueError)):
                Interval(*args)
        with self.assertRaises(ZeroDivisionError):
            Interval(-1, 1).reciprocal()
        with self.assertRaises(ValueError):
            Interval(-1, 2).sqrt()
        with self.assertRaises((ValueError, OverflowError)):
            Interval.from_float(float("inf"))
        self.assertEqual(Interval.from_float(0.125), Interval.point(F(1, 8)))

    def test_outward_arithmetic(self):
        a, b = Interval(F(-1, 3), F(2, 5), 12), Interval(F(2, 7), F(3, 4), 12)
        for x in (a.lo, F(0), a.hi):
            for y in (b.lo, b.midpoint, b.hi):
                self.assertTrue((a + b).contains(x + y))
                self.assertTrue((a - b).contains(x - y))
                self.assertTrue((a * b).contains(x * y))
                self.assertTrue((a / b).contains(x / y))
        self.assertEqual(Interval(-2, 3).square(), Interval(0, 9))
        self.assertEqual(abs(Interval(-2, 3)), Interval(0, 3))
        self.assertTrue((a ** 3).contains(a.lo ** 3))
        self.assertTrue((b ** -2).contains(1 / b.hi ** 2))

    def test_sqrt_integer_enclosure(self):
        for value in (F(0), F(1, 9), F(2), F(10) ** 50, F(1, 1 << 1074)):
            result = Interval.point(value, 112).sqrt()
            self.assertLessEqual(result.lo ** 2, value)
            self.assertGreaterEqual(result.hi ** 2, value)
            self.assertLessEqual(result.width, F(1, 1 << 112))
        self.assertEqual(Interval.point(F(9, 16)).sqrt(), Interval.point(F(3, 4)))

    def test_exp_and_sqrt_against_high_precision_decimal(self):
        with localcontext() as context:
            context.prec = 180
            for value in (F(-20), F(-1, 3), F(0), F(1, 7), F(2), F(17), F(700)):
                decimal_value = Decimal(value.numerator) / Decimal(value.denominator)
                self.assertTrue(Interval.point(value, 128).exp().contains(F(decimal_value.exp())))
                if value >= 0:
                    self.assertTrue(Interval.point(value, 128).sqrt().contains(F(decimal_value.sqrt())))

    def test_exp_reciprocity_monotonicity_and_far_negative(self):
        for value in (F(1, 7), F(5), F(23)):
            self.assertTrue((Interval.point(value).exp() * Interval.point(-value).exp()).contains(1))
        result = Interval(-2, 3).exp()
        self.assertLess(result.lo, 1)
        self.assertGreater(result.hi, 1)
        small = Interval.point(-10**6).exp()
        self.assertEqual(small.lo, 0)
        self.assertEqual(small.hi, F(1, 1 << 96))
        with self.assertRaises(ArithmeticLimit):
            Interval.point(10000).exp()

    def test_pi_encloses_decimal_reference(self):
        # This decimal is a check vector, not a premise of the implementation.
        value = F("3.141592653589793238462643383279502884197169399375105820974944592307816406286")
        result = pi_interval(160)
        self.assertTrue(result.contains(value))
        self.assertLessEqual(result.width, F(1, 1 << 158))

    def test_erf_integral_bounds_and_oddness(self):
        coefficient = 2 / pi_interval().sqrt()
        for value in (F(1, 8), F(1, 2), F(1), F(2), F(4), F(8)):
            result = Interval.point(value).erf()
            self.assertEqual(Interval.point(-value).erf(), -result)
            self.assertGreaterEqual(result.lo, 0)
            self.assertLessEqual(result.hi, 1)
            # Monotone Riemann bounds integrate exp(-t*t) independently.
            count = 32
            step = value / count
            lower_sum = sum((Interval.point(-(i * step)**2).exp().lo for i in range(1, count + 1)), F(0))
            upper_sum = sum((Interval.point(-(i * step)**2).exp().hi for i in range(count)), F(0))
            lower = step * lower_sum * coefficient.lo
            upper = step * upper_sum * coefficient.hi
            self.assertGreaterEqual(result.lo, lower)
            self.assertLessEqual(result.hi, upper)

    def test_erf_saturation_and_tanh(self):
        self.assertEqual(Interval.point(0).erf(), Interval.point(0))
        self.assertGreater(Interval.point(1000).erf().lo, 1 - F(1, 1 << 95))
        for value in (F(0), F(1, 3), F(3), F(1000)):
            result = Interval.point(value).tanh()
            self.assertEqual(Interval.point(-value).tanh(), -result)
            self.assertGreaterEqual(result.lo, 0)
            self.assertLessEqual(result.hi, 1)

    def test_rational_rounding_normal_ties_and_signs(self):
        even = F(1)
        odd = even + F(1, 1 << 52)
        middle_even = even + F(1, 1 << 53)
        middle_odd = odd + F(1, 1 << 53)
        self.assertEqual(round_fraction(middle_even), 1.0)
        self.assertEqual(bits(round_fraction(middle_odd)), bits(1.0) + 2)
        self.assertEqual(round_fraction(-middle_even), -1.0)
        for value in (F(1, 3), F(2, 7), F(-11, 5), F(10) ** 100):
            self.assertEqual(round_fraction(value), float(value))

    def test_rational_rounding_subnormal_and_overflow_boundaries(self):
        quantum = F(1, 1 << 1074)
        self.assertEqual(bits(round_fraction(quantum / 2)), 0)
        self.assertEqual(bits(round_fraction(-quantum / 2)), 1 << 63)
        self.assertEqual(bits(round_fraction(3 * quantum / 2)), 2)
        self.assertEqual(bits(round_fraction((2**52 - F(1, 2)) * quantum)), 1 << 52)
        threshold = F(2) ** 1024 - F(2) ** 970
        self.assertEqual(bits(round_fraction(threshold - 1)), 0x7FEFFFFFFFFFFFFF)
        self.assertTrue(math.isinf(round_fraction(threshold)))
        self.assertTrue(math.isinf(round_fraction(threshold + 1)))

    def test_exact_rational_roundtrip(self):
        encodings = (1, 2, 0x000FFFFFFFFFFFFF, 0x0010000000000000,
                     0x3FD5555555555555, 0x3FF0000000000001, 0x7FEFFFFFFFFFFFFF)
        for encoding in encodings:
            for sign in (0, 1 << 63):
                value = struct.unpack(">d", struct.pack(">Q", encoding | sign))[0]
                self.assertEqual(bits(round_fraction(F.from_float(value))), encoding | sign)

    def test_rounding_primitive_values_and_signed_zero(self):
        self.assertEqual(round_exp(0.0), 1.0)
        self.assertEqual(round_sqrt(2.0), math.sqrt(2.0))
        self.assertEqual(round_exp(1.0), math.e)
        self.assertEqual(round_erf(1.0), 0.8427007929497149)
        self.assertEqual(round_tanh(1.0), 0.7615941559557649)
        self.assertEqual(round_erf(1000.0), 1.0)
        self.assertEqual(round_tanh(-1000.0), -1.0)
        self.assertEqual(round_exp(-1000.0), 0.0)
        self.assertTrue(math.isinf(round_exp(1000.0)))
        for function in (round_sqrt, round_erf, round_tanh):
            self.assertEqual(bits(function(-0.0)), 1 << 63)
        self.assertEqual(round_sqrt(float.fromhex("0x0.0000000000001p-1022")), 2.0**-537)

    def test_correct_rounding_against_decimal_and_enclosure(self):
        with localcontext() as context:
            context.prec = 200
            for value in (-745.0, -50.0, -0.125, 0.125, 50.0, 709.0):
                target = F(Decimal.from_float(value).exp())
                self.assertEqual(round_exp(value), round_fraction(target))
            for value in (0.1, 3.0, 1e-300, 1e300):
                target = F(Decimal.from_float(value).sqrt())
                self.assertEqual(round_sqrt(value), round_fraction(target))
        enclosure = binary64_enclosure(Interval(F(1), F(1) + F(1, 1 << 53)))
        self.assertEqual(enclosure, Interval.point(1))
        with self.assertRaises(ArithmeticLimit):
            binary64_enclosure(Interval.point(F(2) ** 1024))

    def test_unresolved_rounding_fails_closed(self):
        boundary = F(1) + F(1, 1 << 53)
        with self.assertRaises(UnresolvedRounding):
            round_interval(lambda p: Interval(boundary - F(1, 1 << p), boundary + F(1, 1 << p), p),
                           initial_bits=64, max_bits=128)
        with self.assertRaises((ValueError, OverflowError)):
            round_exp(float("nan"))


if __name__ == "__main__":
    unittest.main()
