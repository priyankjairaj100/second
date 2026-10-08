"""Codec arithmetic fixtures. These are not empirical datasets or benchmarks."""
from dataclasses import replace
from fractions import Fraction as Q
import hashlib
import json
import struct
import unittest
import numpy as np

from src.fixed_factor_codec import (encode_factor, serialize, parse, LoadLimits,
    _cell, _dyadic_word, _word_float, _GUARD_BITS, _decode_payload)

BINDINGS = dict(target_sha256='a'*64, anchor_target_sha256='b'*64,
                record_id='software-fixture', token_sha256='c'*64, stage_id='block.0000.qkv')


def encode(array, **options):
    return encode_factor(np.asarray(array, dtype=np.float64), **BINDINGS, **options)


class FixedFactorCodecTests(unittest.TestCase):
    def test_every_finite_exponent_edge_contains_source_and_refines(self):
        words = []
        fractions = (0, 1, (1 << 28)-1, 1 << 28, (1 << 38)-1, 1 << 38, (1 << 52)-1)
        for exponent in range(2047):
            for mantissa in fractions:
                for sign in (0, 1 << 63):
                    words.append(sign | (exponent << 52) | mantissa)
        array = np.asarray(words, dtype='<u8').view('<f8').reshape(1, -1)
        coarse, fine = (encode(array, bits=bits, block_size=31) for bits in (16,24))
        left, right = coarse.box(), fine.box()
        self.assertTrue(left.contains(array))
        self.assertTrue(right.contains(array))
        self.assertTrue(np.all(right.lower >= left.lower))
        self.assertTrue(np.all(right.upper <= left.upper))
        self.assertEqual(coarse.escape_count, fine.escape_count)
        self.assertEqual(coarse.escape_count, int(np.count_nonzero(np.asarray(words, dtype='<u8') & ((1 << 63)-1) > _GUARD_BITS)))
        # Exact rational center/radius checks sample every exponent class.
        center, radius = fine.center_radius()
        for i in range(0, array.size, len(fractions)*2):
            self.assertLessEqual(abs(Q.from_float(float(array.flat[i]))-Q.from_float(float(center.flat[i]))),
                                 Q.from_float(float(radius.flat[i])))

    def test_exhaustive_low_subnormal_words_and_signed_zeros(self):
        positive = np.arange(65536, dtype='<u8')
        words = np.concatenate((positive, positive | np.uint64(1 << 63)))
        array = words.view('<f8').reshape(1, -1)
        coarse = encode(array, bits=16, block_size=256)
        fine = encode(array, bits=24, block_size=256)
        self.assertTrue(coarse.box().contains(array))
        self.assertTrue(fine.box().contains(array))
        self.assertTrue(fine.box().singleton)
        self.assertEqual(coarse.escape_count, 0)
        self.assertEqual(fine.escape_count, 0)
        for box in (coarse.box(), fine.box()):
            self.assertFalse(np.signbit(box.lower[0, 0]))
            self.assertFalse(np.signbit(box.lower[0, 65536]))
        self.assertEqual(fine.source_sha256, hashlib.sha256(array.astype('<f8').tobytes()).hexdigest())

    def test_cell_floor_and_endpoint_bit_construction_match_rationals(self):
        values = [0., -0., 1., -1., 1.5, -1.5, np.finfo(np.float64).max,
                  -np.finfo(np.float64).max, float.fromhex('0x0.0000000000001p-1022')]
        for value in values:
            word = struct.unpack('<Q', struct.pack('<d', value))[0]
            for power in (-1074, -52, -1, 0, 1, 1009):
                integer, exact = _cell(word, power)
                scaled = Q.from_float(float(value)) / Q(2)**power
                self.assertEqual(integer, scaled.numerator//scaled.denominator)
                self.assertEqual(exact, scaled.denominator == 1)
        for integer in (-8388608, -32768, -1, 0, 1, 32767, 8388607):
            for power in (-1074, -1073, -1022, -23, 0, 999):
                exact = Q(integer)*Q(2)**power
                try:
                    actual = _word_float(_dyadic_word(integer, power))
                except ValueError:
                    self.assertGreater(abs(exact), Q.from_float(np.finfo(np.float64).max))
                else:
                    self.assertEqual(Q.from_float(actual), exact)
        with self.assertRaises(ValueError):
            _dyadic_word(1, -1075)
        with self.assertRaises(ValueError):
            _dyadic_word(1, 1024)

    def test_overflow_guard_escapes_are_precision_independent_and_nested(self):
        guard = _word_float(_GUARD_BITS)
        values = np.array([[guard, np.nextafter(guard, np.inf), np.finfo(np.float64).max,
                            -guard, np.nextafter(-guard, -np.inf), -np.finfo(np.float64).max]])
        first, second = (encode(values, bits=bits, block_size=6) for bits in (16,24))
        self.assertEqual(first.escape_count, 4)
        self.assertEqual(second.escape_count, 4)
        self.assertTrue(first.box().singleton)
        self.assertTrue(second.box().singleton)
        self.assertTrue(first.box().contains(values))
        center, radius = first.center_radius()
        self.assertTrue(np.array_equal(center, values))
        self.assertTrue(np.all(radius == 0))

    def test_grid_neighbors_and_center_radius_proof(self):
        values = []
        for integer in range(-50, 51):
            value = integer / 32768.
            values.extend((np.nextafter(value, -np.inf), value, np.nextafter(value, np.inf)))
        array = np.array(values, dtype=np.float64).reshape(1, -1)
        for bits in (16,24):
            descriptor = encode(array, bits=bits, block_size=17)
            box = descriptor.box()
            center, radius = descriptor.center_radius()
            for x, lo, hi, c, r in zip(array.flat, box.lower.flat, box.upper.flat, center.flat, radius.flat):
                x, lo, hi, c, r = (Q.from_float(float(v)) for v in (x,lo,hi,c,r))
                self.assertLessEqual(lo, x)
                self.assertLessEqual(x, hi)
                self.assertLessEqual(abs(x-c), r)
                self.assertLessEqual(c-r, lo)
                self.assertLessEqual(hi, c+r)

    def test_format_roundtrip_bindings_immutability_and_real_packing(self):
        array = np.linspace(-3., 5., 16384, dtype=np.float64).reshape(16,1024)
        for bits, bound in ((16,0.32),(24,0.45)):
            descriptor = encode(array, bits=bits)
            raw = serialize(descriptor)
            self.assertLess(len(raw), bound*array.nbytes)
            restored = parse(raw, expected_sha256=descriptor.digest)
            self.assertEqual(restored, descriptor)
            self.assertEqual(serialize(restored), raw)
            self.assertTrue(restored.box().contains(array))
            with self.assertRaises(ValueError):
                restored.box().lower.setflags(write=True)
            center, radius = restored.center_radius()
            with self.assertRaises(ValueError):
                center.setflags(write=True)
            with self.assertRaises(ValueError):
                radius.setflags(write=True)
            for field in ('record_id', 'stage_id'):
                self.assertNotEqual(replace(descriptor, **{field:'different'}).digest, descriptor.digest)
            self.assertNotEqual(replace(descriptor, target_sha256='0'*64).digest, descriptor.digest)

    def test_parser_caps_corruption_and_reserved_payload_forms(self):
        descriptor = encode(np.array([[0., 1.25, -0.3]]), bits=16, block_size=3)
        data = serialize(descriptor)
        for bad in (data+b'x', data[:-1], data[:25]+bytes([data[25]^1])+data[26:]):
            with self.assertRaises(ValueError):
                parse(bad)
        for limits in (LoadLimits(max_bytes=16), LoadLimits(max_header_bytes=1),
                       LoadLimits(max_values=2), LoadLimits(max_width=2), LoadLimits(max_block_size=2)):
            with self.assertRaises(ValueError):
                parse(data, limits=limits)
        with self.assertRaises(ValueError):
            parse(data, expected_sha256='0'*64)
        payload = bytearray(descriptor.payload)
        payload[2] |= 3
        with self.assertRaisesRegex(ValueError, 'reserved'):
            replace(descriptor, payload=bytes(payload))
        payload = bytearray(descriptor.payload)
        payload[2] |= 64
        with self.assertRaisesRegex(ValueError, 'unused'):
            replace(descriptor, payload=bytes(payload))
        payload = bytearray(descriptor.payload)
        payload[:2] = struct.pack('<h', 2047)
        with self.assertRaisesRegex(ValueError, 'exponent'):
            replace(descriptor, payload=bytes(payload))

    def test_nonfinite_inputs_and_invalid_settings_fail_closed(self):
        for value in (np.nan, np.inf, -np.inf):
            with self.assertRaises(ValueError):
                encode(np.array([[value]]))
        for options in ({'bits':8}, {'bits':True}, {'bits':32}, {'block_size':0}, {'block_size':4097}):
            with self.assertRaises(ValueError):
                encode(np.array([[1.]]), **options)
        with self.assertRaises(TypeError):
            encode_factor(np.array([[1.]], dtype=np.float32), **BINDINGS)


if __name__ == '__main__':
    unittest.main()
