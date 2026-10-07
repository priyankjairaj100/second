"""Rational enclosures and correctly rounded binary64 transcendental primitives.

This module defines a new scalar numerical program.  It makes no accuracy
assumption about host ``math.exp``, ``math.erf``, ``math.tanh`` or ``math.sqrt``.
All interval endpoints are rational.  Arithmetic rounds endpoints outwards to
a dyadic grid; nonlinear routines use integer arithmetic and explicit series
remainders.  Resource limits fail closed instead of returning an estimate.

``bits`` is the dyadic fractional precision, not a significant-digit count.
Correct rounding refines this precision and can report UnresolvedRounding.
These routines favor auditability.  They are not a fast production kernel.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from math import isqrt
import struct
from typing import Callable


class ArithmeticLimit(ArithmeticError):
    """The requested rigorous enclosure exceeds a declared resource limit."""


class UnresolvedRounding(ArithmeticError):
    """The enclosure still crosses a binary64 rounding boundary."""


def _q(value: int | Fraction) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise TypeError("Use int/Fraction, or explicit Interval.from_float().")
    return Fraction(value)


def _precision(bits: int) -> int:
    if isinstance(bits, bool) or not isinstance(bits, int) or not 1 <= bits <= 16384:
        raise ValueError("bits must be an integer between 1 and 16384")
    return bits


def _floor_dyadic(x: Fraction, bits: int) -> Fraction:
    return Fraction((x.numerator << bits) // x.denominator, 1 << bits)


def _ceil_dyadic(x: Fraction, bits: int) -> Fraction:
    return -_floor_dyadic(-x, bits)


@dataclass(frozen=True)
class Interval:
    lo: Fraction
    hi: Fraction
    bits: int = 96

    def __post_init__(self) -> None:
        object.__setattr__(self, "lo", _q(self.lo))
        object.__setattr__(self, "hi", _q(self.hi))
        _precision(self.bits)
        if self.lo > self.hi:
            raise ValueError("reversed interval")

    @classmethod
    def point(cls, value: int | Fraction, bits: int = 96) -> Interval:
        x = _q(value)
        return cls(x, x, bits)

    @classmethod
    def from_float(cls, value: float, bits: int = 96) -> Interval:
        if not isinstance(value, float):
            raise TypeError("from_float requires a float")
        return cls.point(Fraction.from_float(value), bits)

    @property
    def width(self) -> Fraction:
        return self.hi - self.lo

    @property
    def midpoint(self) -> Fraction:
        return (self.lo + self.hi) / 2

    def contains(self, value: int | Fraction) -> bool:
        return self.lo <= _q(value) <= self.hi

    def abs_bound(self) -> Fraction:
        return max(abs(self.lo), abs(self.hi))

    def outward(self, bits: int | None = None) -> Interval:
        p = self.bits if bits is None else _precision(bits)
        return Interval(_floor_dyadic(self.lo, p), _ceil_dyadic(self.hi, p), p)

    def _other(self, value: Interval | int | Fraction) -> Interval:
        return value if isinstance(value, Interval) else Interval.point(value, self.bits)

    def __neg__(self) -> Interval:
        return Interval(-self.hi, -self.lo, self.bits)

    def __add__(self, value: Interval | int | Fraction) -> Interval:
        b = self._other(value)
        p = min(self.bits, b.bits)
        return Interval(self.lo + b.lo, self.hi + b.hi, p).outward()

    __radd__ = __add__

    def __sub__(self, value: Interval | int | Fraction) -> Interval:
        return self + -self._other(value)

    def __rsub__(self, value: Interval | int | Fraction) -> Interval:
        return self._other(value) - self

    def __mul__(self, value: Interval | int | Fraction) -> Interval:
        b = self._other(value)
        terms = (self.lo * b.lo, self.lo * b.hi, self.hi * b.lo, self.hi * b.hi)
        return Interval(min(terms), max(terms), min(self.bits, b.bits)).outward()

    __rmul__ = __mul__

    def reciprocal(self) -> Interval:
        if self.lo <= 0 <= self.hi:
            raise ZeroDivisionError("interval denominator contains zero")
        return Interval(1 / self.hi, 1 / self.lo, self.bits).outward()

    def __truediv__(self, value: Interval | int | Fraction) -> Interval:
        return self * self._other(value).reciprocal()

    def __rtruediv__(self, value: Interval | int | Fraction) -> Interval:
        return self._other(value) / self

    def square(self) -> Interval:
        lower = 0 if self.lo <= 0 <= self.hi else min(self.lo**2, self.hi**2)
        return Interval(lower, max(self.lo**2, self.hi**2), self.bits).outward()

    def __pow__(self, exponent: int) -> Interval:
        if isinstance(exponent, bool) or not isinstance(exponent, int):
            raise TypeError("interval power requires an integer")
        if exponent < 0:
            return (self ** -exponent).reciprocal()
        result = Interval.point(1, self.bits)
        base = self
        while exponent:
            if exponent & 1:
                result = result * base
            exponent >>= 1
            if exponent:
                base = base.square()
        return result

    def __abs__(self) -> Interval:
        lower = 0 if self.lo <= 0 <= self.hi else min(abs(self.lo), abs(self.hi))
        return Interval(lower, self.abs_bound(), self.bits)

    def sqrt(self, bits: int | None = None) -> Interval:
        p = self.bits if bits is None else _precision(bits)
        if self.lo < 0:
            raise ValueError("sqrt interval includes negative values")
        return Interval(_sqrt_point(self.lo, p).lo, _sqrt_point(self.hi, p).hi, p)

    def exp(self, bits: int | None = None) -> Interval:
        p = self.bits if bits is None else _precision(bits)
        return Interval(_exp_point(self.lo, p).lo, _exp_point(self.hi, p).hi, p)

    def erf(self, bits: int | None = None) -> Interval:
        p = self.bits if bits is None else _precision(bits)
        return Interval(_erf_point(self.lo, p).lo, _erf_point(self.hi, p).hi, p)

    def tanh(self, bits: int | None = None) -> Interval:
        p = self.bits if bits is None else _precision(bits)
        return Interval(_tanh_point(self.lo, p).lo, _tanh_point(self.hi, p).hi, p)


def _sqrt_point(x: Fraction, bits: int) -> Interval:
    if x < 0:
        raise ValueError("negative square root")
    scaled_numerator = x.numerator << (2 * bits)
    root = isqrt(scaled_numerator // x.denominator)
    lower = Fraction(root, 1 << bits)
    exact = root * root * x.denominator == scaled_numerator
    upper = lower if exact else Fraction(root + 1, 1 << bits)
    return Interval(lower, upper, bits)


def _exp_point(x: Fraction, bits: int) -> Interval:
    if not x:
        return Interval.point(1, bits)
    if x <= -bits:
        # e > 2, hence exp(-t) <= 2**(-bits) when t >= bits.
        return Interval(0, Fraction(1, 1 << bits), bits)
    if x < 0:
        positive = _exp_point(-x, bits + 8)
        return Interval(1 / positive.hi, 1 / positive.lo, bits).outward()
    if x > 8192:
        raise ArithmeticLimit("positive exp argument exceeds 8192")
    shifts = 0
    y = x
    while y > Fraction(1, 8):
        y /= 2
        shifts += 1
    work_bits = _precision(bits + shifts + 12)
    target = Fraction(1, 1 << work_bits)
    term = Fraction(1)
    total = term
    n = 0
    while True:
        next_term = term * y / (n + 1)
        # All later successive ratios are <= y/(n+2).
        tail = next_term / (1 - y / (n + 2))
        if tail <= target:
            break
        total += next_term
        term = next_term
        n += 1
        if n > 20000:
            raise ArithmeticLimit("exp Taylor term limit")
    result = Interval(total, total + tail, work_bits).outward()
    for _ in range(shifts):
        result = result.square()
    return result.outward(bits)


def _atan_reciprocal(denominator: int, bits: int) -> Interval:
    x = Fraction(1, denominator)
    x2 = x * x
    power = x
    total = Fraction(0)
    target = Fraction(1, 1 << bits)
    n = 0
    while True:
        term = power / (2 * n + 1)
        total += term if n % 2 == 0 else -term
        power *= x2
        next_term = power / (2 * n + 3)
        if next_term <= target:
            if n % 2 == 0:
                return Interval(total - next_term, total, bits)
            return Interval(total, total + next_term, bits)
        n += 1


@lru_cache(maxsize=32)
def pi_interval(bits: int = 96) -> Interval:
    """Machin's identity with alternating arctangent remainder bounds."""
    p = _precision(bits)
    work_bits = _precision(p + 8)
    a = _atan_reciprocal(5, work_bits)
    b = _atan_reciprocal(239, work_bits)
    # The rational tangent addition formula gives 4 atan(1/5)-atan(1/239)=pi/4.
    return (16 * a - 4 * b).outward(p)


def _erf_point(x: Fraction, bits: int) -> Interval:
    if not x:
        return Interval.point(0, bits)
    if x < 0:
        return -_erf_point(-x, bits)
    work_bits = _precision(bits + 16)
    root_pi = pi_interval(work_bits).sqrt()
    x2 = x * x
    target = Fraction(1, 1 << bits)
    if x >= 1:
        # Integral comparison: erfc(x) <= exp(-x*x)/(sqrt(pi)*x).
        tail = _exp_point(-x2, work_bits).hi / (root_pi.lo * x)
        if tail <= target:
            return Interval(max(Fraction(0), 1 - tail), 1, bits).outward()
    # erf(x)=2/sqrt(pi) sum (-1)^n x^(2n+1)/(n! (2n+1)).
    # Alternating remainder applies after the terms become nonincreasing.
    if x2 > 20000:
        raise ArithmeticLimit("erf series range limit")
    tolerance = Fraction(1, 1 << work_bits)
    power_over_factorial = x
    total = Fraction(0)
    n = 0
    while True:
        term = power_over_factorial / (2 * n + 1)
        total += term if n % 2 == 0 else -term
        next_power = power_over_factorial * x2 / (n + 1)
        next_term = next_power / (2 * n + 3)
        if n + 1 >= x2 and next_term <= tolerance:
            if n % 2 == 0:
                series = Interval(total - next_term, total, work_bits)
            else:
                series = Interval(total, total + next_term, work_bits)
            result = 2 * series / root_pi
            return Interval(max(Fraction(0), result.lo), min(Fraction(1), result.hi), bits).outward()
        n += 1
        power_over_factorial = next_power
        if n > 20000:
            raise ArithmeticLimit("erf Taylor term limit")


def _tanh_point(x: Fraction, bits: int) -> Interval:
    if not x:
        return Interval.point(0, bits)
    if x < 0:
        return -_tanh_point(-x, bits)
    y = _exp_point(-2 * x, _precision(bits + 8))
    # This rational map decreases on [0,1].  Use endpoints directly.
    lower = (1 - y.hi) / (1 + y.hi)
    upper = (1 - y.lo) / (1 + y.lo)
    return Interval(max(Fraction(0), lower), min(Fraction(1), upper), bits).outward()


def _nearest_integer(numerator: int, denominator: int) -> int:
    quotient, remainder = divmod(numerator, denominator)
    twice = 2 * remainder
    return quotient + int(twice > denominator or (twice == denominator and quotient % 2 == 1))


def _float_from_bits(bits: int) -> float:
    return struct.unpack(">d", struct.pack(">Q", bits))[0]


def _float_bits(value: float) -> int:
    return struct.unpack(">Q", struct.pack(">d", value))[0]


def round_fraction(value: int | Fraction) -> float:
    """Round a rational to IEEE binary64, nearest with ties to even.

    Integer quotient/remainder decisions cover normal values, subnormals,
    ties and overflow.  Struct only transfers the chosen IEEE encoding.
    """
    x = _q(value)
    negative = x < 0
    sign = int(negative) << 63
    x = abs(x)
    if not x:
        return _float_from_bits(sign)
    n, d = x.numerator, x.denominator
    exponent = n.bit_length() - d.bit_length()
    if exponent >= 0:
        exponent -= int(n < (d << exponent))
    else:
        exponent -= int((n << -exponent) < d)
    if exponent < -1022:
        code = _nearest_integer(n << 1074, d)
        # code == 2**52 is the smallest normal encoding.
        return _float_from_bits(sign | code)
    if exponent > 1023:
        return _float_from_bits(sign | (0x7FF << 52))
    shift = 52 - exponent
    code = _nearest_integer(n << shift, d) if shift >= 0 else _nearest_integer(n, d << -shift)
    if code == 1 << 53:
        code >>= 1
        exponent += 1
    if exponent > 1023:
        return _float_from_bits(sign | (0x7FF << 52))
    encoding = ((exponent + 1023) << 52) | (code - (1 << 52))
    return _float_from_bits(sign | encoding)


def binary64_enclosure(value: Interval) -> Interval:
    """Enclose all finite RN-even outputs for real inputs in ``value``."""
    lower = round_fraction(value.lo)
    upper = round_fraction(value.hi)
    try:
        return Interval(Fraction.from_float(lower), Fraction.from_float(upper), value.bits)
    except (OverflowError, ValueError) as exc:
        raise ArithmeticLimit("binary64 enclosure includes infinity") from exc


def round_interval(
    evaluator: Callable[[int], Interval], *, initial_bits: int = 96, max_bits: int = 3072
) -> float:
    """Refine until every enclosed real rounds to the same binary64 value."""
    precision = _precision(initial_bits)
    limit = _precision(max_bits)
    if precision > limit:
        raise ValueError("initial_bits exceeds max_bits")
    while True:
        enclosure = evaluator(precision)
        lo, hi = round_fraction(enclosure.lo), round_fraction(enclosure.hi)
        if _float_bits(lo) == _float_bits(hi):
            return lo
        if precision == limit:
            raise UnresolvedRounding("interval crosses a binary64 rounding boundary")
        precision = min(2 * precision, limit)


def _finite_input(value: float) -> Fraction:
    if not isinstance(value, float):
        raise TypeError("rounded primitives require binary64 float input")
    return Fraction.from_float(value)


def round_exp(value: float, *, initial_bits: int = 96, max_bits: int = 3072) -> float:
    x = _finite_input(value)
    if x >= 1024:
        return _float_from_bits(0x7FF << 52)
    return round_interval(lambda p: _exp_point(x, p), initial_bits=initial_bits, max_bits=max_bits)


def round_sqrt(value: float, *, initial_bits: int = 96, max_bits: int = 3072) -> float:
    x = _finite_input(value)
    if x < 0:
        raise ValueError("negative square root")
    if not x:
        return value  # Preserve -0.0.
    a, b = isqrt(x.numerator), isqrt(x.denominator)
    if a * a == x.numerator and b * b == x.denominator:
        return round_fraction(Fraction(a, b))
    return round_interval(lambda p: _sqrt_point(x, p), initial_bits=initial_bits, max_bits=max_bits)


def round_erf(value: float, *, initial_bits: int = 96, max_bits: int = 3072) -> float:
    x = _finite_input(value)
    if not x:
        return value
    return round_interval(lambda p: _erf_point(x, p), initial_bits=initial_bits, max_bits=max_bits)


def round_tanh(value: float, *, initial_bits: int = 96, max_bits: int = 3072) -> float:
    x = _finite_input(value)
    if not x:
        return value
    return round_interval(lambda p: _tanh_point(x, p), initial_bits=initial_bits, max_bits=max_bits)
