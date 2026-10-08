"""Version 26 codec software fixtures. No models or empirical datasets."""
from dataclasses import replace
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import struct
import unittest

import numpy as np

from src.compact_state import _json
from src.fixed_factor_codec import encode_factor as encode_v24, parse as parse_v24
from src.fixed_factor_codec_v26 import (
    PRECISIONS, MAGIC, encode_factor, serialize, parse, LoadLimits,
    codec_binding, codec_dependencies, _word_float, _GUARD_BITS,
)

BINDINGS = dict(target_sha256='a'*64, anchor_target_sha256='b'*64,
    record_id='software-fixture', token_sha256='c'*64, stage_id='stage.fixture')


def encode(values, **options):
    return encode_factor(np.asarray(values, dtype=np.float64), **BINDINGS, **options)


def rewrite_header(raw, update):
    length = struct.unpack_from('<Q', raw, 8)[0]
    header = json.loads(raw[16:16+length])
    update(header)
    encoded = _json(header)
    return MAGIC+struct.pack('<Q', len(encoded))+encoded+raw[16+length:]


class FixedFactorCodecV26Tests(unittest.TestCase):
    def test_all_exponent_classes_have_exact_containment_and_nested_cells(self):
        words = []
        fractions = (0, 1, (1 << 20)-1, 1 << 38, (1 << 52)-1)
        for exponent in range(2047):
            for fraction in fractions:
                for sign in (0, 1 << 63):
                    words.append(sign | (exponent << 52) | fraction)
        values = np.asarray(words, dtype='<u8').view('<f8').reshape(1, -1)
        previous = None
        for bits in PRECISIONS:
            descriptor = encode(values, bits=bits, block_size=31)
            box = descriptor.box()
            self.assertTrue(box.contains(values))
            if previous is not None:
                self.assertTrue(np.all(previous.lower <= box.lower))
                self.assertTrue(np.all(box.upper <= previous.upper))
            center, radius = descriptor.center_radius()
            for index in range(0, values.size, 10):
                x, lo, hi, c, r = (Q.from_float(float(a.flat[index]))
                                   for a in (values, box.lower, box.upper, center, radius))
                self.assertLessEqual(lo, x)
                self.assertLessEqual(x, hi)
                self.assertLessEqual(abs(x-c), r)
                self.assertLessEqual(c-r, lo)
                self.assertLessEqual(hi, c+r)
            previous = box

    def test_low_subnormal_words_boundaries_and_signed_zeros(self):
        positive = set(range(8192))
        for power in range(13, 53):
            positive.update(n for n in ((1 << power)-2, (1 << power)-1,
                                       1 << power, (1 << power)+1) if n < (1 << 52))
        positive = np.asarray(sorted(positive), dtype='<u8')
        words = np.concatenate((positive, positive | np.uint64(1 << 63)))
        values = words.view('<f8').reshape(1, -1)
        previous = None
        for bits in PRECISIONS:
            descriptor = encode(values, bits=bits, block_size=19)
            box = descriptor.box()
            self.assertTrue(box.contains(values))
            self.assertEqual(descriptor.escape_count, 0)
            self.assertFalse(np.signbit(box.lower[0, 0]))
            self.assertFalse(np.signbit(box.lower[0, len(positive)]))
            self.assertEqual(descriptor.source_sha256, hashlib.sha256(values.astype('<f8').tobytes()).hexdigest())
            if previous is not None:
                self.assertTrue(np.all(previous.lower <= box.lower))
                self.assertTrue(np.all(box.upper <= previous.upper))
            previous = box

    def test_overflow_guard_escapes_and_exact_centers_match_every_precision(self):
        guard = _word_float(_GUARD_BITS)
        maximum = np.finfo(np.float64).max
        values = np.array([[np.nextafter(guard, 0), guard, np.nextafter(guard, np.inf), maximum,
                            np.nextafter(-guard, 0), -guard, np.nextafter(-guard, -np.inf), -maximum]])
        previous = None
        for bits in PRECISIONS:
            descriptor = encode(values, bits=bits, block_size=8)
            box = descriptor.box()
            self.assertTrue(box.contains(values))
            self.assertEqual(descriptor.escape_count, 4)
            center, radius = descriptor.center_radius()
            for index in (2, 3, 6, 7):
                self.assertEqual(center.flat[index], values.flat[index])
                self.assertEqual(radius.flat[index], 0)
            for value, c, r in zip(values.flat, center.flat, radius.flat):
                self.assertLessEqual(abs(Q.from_float(float(value))-Q.from_float(float(c))),
                                     Q.from_float(float(r)))
            if previous is not None:
                self.assertTrue(np.all(previous.lower <= box.lower))
                self.assertTrue(np.all(box.upper <= previous.upper))
            previous = box

    def test_grid_neighbors_have_exact_endpoints_and_radii_through_48_bits(self):
        values = [0., -0., 1., -1.]
        for bits in PRECISIONS:
            step = Q(2)**(-(bits-2))
            for integer in (-32767, -19, -1, 0, 1, 19, 32767):
                value = float(integer*step)
                values.extend((np.nextafter(value, -np.inf), value, np.nextafter(value, np.inf)))
        array = np.array(values).reshape(1, -1)
        for bits in PRECISIONS:
            descriptor = encode(array, bits=bits, block_size=11)
            box = descriptor.box()
            center, radius = descriptor.center_radius()
            for x, lo, hi, c, r in zip(array.flat, box.lower.flat, box.upper.flat, center.flat, radius.flat):
                x, lo, hi, c, r = (Q.from_float(float(v)) for v in (x, lo, hi, c, r))
                self.assertLessEqual(lo, x)
                self.assertLessEqual(x, hi)
                self.assertLessEqual(c-r, lo)
                self.assertLessEqual(hi, c+r)

    def test_packed_payloads_keep_v24_bytes_at_existing_precisions(self):
        array = np.linspace(-3., 5., 1024, dtype=np.float64).reshape(16, 64)
        for bits in (16, 24):
            old = encode_v24(array, **BINDINGS, bits=bits, block_size=29)
            new = encode(array, bits=bits, block_size=29)
            self.assertEqual(old.payload, new.payload)
            self.assertEqual(old.source_sha256, new.source_sha256)
            self.assertNotEqual(old.codec_sha256, new.codec_sha256)
            with self.assertRaises(ValueError):
                parse_v24(serialize(new))

    def test_roundtrip_real_packing_and_dependency_binding(self):
        array = np.linspace(-3., 5., 4096, dtype=np.float64).reshape(16, 256)
        dependencies = codec_dependencies()
        self.assertEqual(set(dependencies), {'fixed_factor_codec_v26.py', 'compact_state.py', 'finite_feature_boxes.py'})
        root = Path(__file__).resolve().parents[1]/'src'
        for name, digest in dependencies.items():
            self.assertEqual(digest, hashlib.sha256((root/name).read_bytes()).hexdigest())
        self.assertEqual(codec_binding(), hashlib.sha256(_json(dependencies)).hexdigest())
        for bits in PRECISIONS:
            descriptor = encode(array, bits=bits, block_size=256)
            encoded = serialize(descriptor)
            restored = parse(encoded, expected_sha256=descriptor.digest)
            self.assertEqual(restored, descriptor)
            self.assertEqual(serialize(restored), encoded)
            self.assertEqual(len(descriptor.payload), 16*(2+64+256*(bits//8)))
            self.assertLess(len(descriptor.payload), array.nbytes)
            center, radius = restored.center_radius()
            for values in (center, radius, restored.box().lower, restored.box().upper):
                with self.assertRaises(ValueError):
                    values.setflags(write=True)

    def test_parser_rejects_unsupported_precisions_and_malformed_headers(self):
        descriptor = encode(np.array([[0., 1.25, -0.3]]), bits=48, block_size=3)
        data = serialize(descriptor)
        for bits in (True, False, 8, 15, 31, 49, 56, 64, '48', 48.0):
            with self.assertRaises(ValueError):
                parse(rewrite_header(data, lambda h: h.update(bits=bits)))
        for update in (
            lambda h: h.update(schema='source-local-dyadic-factor-enclosure-v1'),
            lambda h: h.update(shape=[1, 100000000]),
            lambda h: h.update(codec_sha256='bad'),
            lambda h: h.update(payload_bytes=True),
            lambda h: h.update(block_size=0),
            lambda h: h.update(zero_rule='unsupported'),
        ):
            with self.assertRaises(ValueError):
                parse(rewrite_header(data, update))
        for bad in (data+b'x', data[:-1], data[:25]+bytes([data[25]^1])+data[26:]):
            with self.assertRaises(ValueError):
                parse(bad)
        for limits in (LoadLimits(max_bytes=16), LoadLimits(max_values=2),
                       LoadLimits(max_width=2), LoadLimits(max_header_bytes=1), LoadLimits(max_block_size=2)):
            with self.assertRaises(ValueError):
                parse(data, limits=limits)
        with self.assertRaises(ValueError):
            parse(data, expected_sha256='0'*64)

    def test_reserved_flags_padding_and_invalid_inputs_fail_closed(self):
        descriptor = encode(np.array([[0., 1.25, -0.3]]), bits=40, block_size=3)
        for index, mask, message in ((2, 3, 'reserved'), (2, 64, 'unused')):
            payload = bytearray(descriptor.payload)
            payload[index] |= mask
            with self.assertRaisesRegex(ValueError, message):
                replace(descriptor, payload=bytes(payload))
        for value in (np.nan, np.inf, -np.inf):
            with self.assertRaises(ValueError):
                encode(np.array([[value]]), bits=48)
        with self.assertRaises(TypeError):
            encode_factor(np.array([[1.]], dtype=np.float32), **BINDINGS, bits=48)
        for options in ({'bits': 56}, {'bits': True}, {'block_size': 0}, {'block_size': 4097}):
            with self.assertRaises(ValueError):
                encode(np.array([[1.]]), **options)


if __name__ == '__main__':
    unittest.main()
