"""Exact codec software fixtures. No neural models or empirical datasets."""
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib

import numpy as np

from src.compact_state import _json
from src.fixed_lossless_codec_v29 import (
    LosslessFactorDescriptor, LoadLimits, MAX_DECODED_BYTES, MAGIC,
    encode_factor, parse, serialize, codec_manifest, codec_binding, _compress,
)

BINDINGS = dict(target_sha256='a'*64, anchor_target_sha256='b'*64,
                record_id='fixture', token_sha256='c'*64, stage_id='stage.fixture')


def encode(values):
    return encode_factor(np.asarray(values, dtype=np.float64), **BINDINGS)


def rewrite(raw, changes, payload=None):
    length = struct.unpack_from('<Q', raw, 8)[0]
    header = json.loads(raw[16:16+length])
    header.update(changes)
    body = raw[16+length:] if payload is None else payload
    if payload is not None:
        header.update(payload_bytes=len(body), payload_sha256=hashlib.sha256(body).hexdigest())
    encoded = _json(header)
    return MAGIC+struct.pack('<Q', len(encoded))+encoded+body


class FixedLosslessCodecTests(unittest.TestCase):
    def test_every_finite_exponent_and_signed_zero_preserve_exact_bytes(self):
        words = []
        for exponent in range(2047):
            for fraction in (0, 1, (1 << 20)-1, 1 << 38, (1 << 52)-1):
                for sign in (0, 1 << 63):
                    words.append(sign | exponent << 52 | fraction)
        array = np.asarray(words, dtype='<u8').view('<f8').reshape(1, -1)
        descriptor = encode(array)
        raw = array.astype('<f8').tobytes()
        self.assertEqual(descriptor.binary64(), raw)
        restored = parse(serialize(descriptor), expected_sha256=descriptor.digest)
        self.assertEqual(restored.binary64(), raw)
        self.assertEqual(restored, descriptor)
        self.assertTrue(np.signbit(restored.array()[0, 1]))
        with self.assertRaises(ValueError):
            restored.array().setflags(write=True)

    def test_all_three_modes_choose_deterministically_and_roundtrip(self):
        fixtures = ((np.array([[1.]]), 0), (np.zeros((1, 2048)), 1),
                    (np.linspace(-3., 5., 8192).reshape(16, 512), 2))
        for values, mode in fixtures:
            descriptor = encode(values)
            self.assertEqual(descriptor.mode, mode)
            self.assertEqual(serialize(encode(values.copy())), serialize(descriptor))
            self.assertEqual(parse(serialize(descriptor)).binary64(), values.astype('<f8').tobytes())
        fortran = np.asfortranarray(fixtures[2][0])
        self.assertEqual(serialize(encode(fortran)), serialize(encode(fixtures[2][0])))

    def test_trusted_encode_avoids_duplicate_compression_but_keeps_metadata_checks(self):
        from src import fixed_lossless_codec_v29 as codec
        with patch.object(codec, '_select', wraps=codec._select) as selected:
            descriptor = encode(np.ones((2, 8)))
            self.assertEqual(selected.call_count, 1)
            descriptor.binary64()
            self.assertEqual(selected.call_count, 1)
            parse(serialize(descriptor))
            self.assertEqual(selected.call_count, 2)
        for key, value in (('record_id', ''), ('target_sha256', 'bad'), ('token_sha256', 4)):
            with self.assertRaises(ValueError):
                encode_factor(np.ones((1, 1)), **dict(BINDINGS, **{key:value}))

    def test_constructor_rejects_noncanonical_modes_and_alternative_streams(self):
        descriptor = encode(np.zeros((1, 2048)))
        with self.assertRaisesRegex(ValueError, 'not canonical'):
            replace(descriptor, mode=0, payload=descriptor.binary64())
        alternate = zlib.compress(descriptor.binary64(), 1)
        self.assertNotEqual(alternate, descriptor.payload)
        with self.assertRaisesRegex(ValueError, 'not canonical'):
            replace(descriptor, payload=alternate)
        with self.assertRaisesRegex(ValueError, 'source hash'):
            replace(descriptor, source_sha256='0'*64)
        with self.assertRaisesRegex(ValueError, 'runtime binding'):
            replace(descriptor, codec_sha256='0'*64)

    def test_bounded_decompression_rejects_bombs_truncation_trailing_and_nonfinite(self):
        small = encode(np.zeros((1, 1)))
        for payload in (_compress(b'\0'*1000000), _compress(b'\0'*8)[:-1],
                        _compress(b'\0'*8)+b'trailing', _compress(b'\0'*8)*2):
            with self.assertRaises(ValueError):
                replace(small, mode=1, payload=payload)
        for value in (np.nan, np.inf, -np.inf):
            raw = np.array([[value]], dtype='<f8').tobytes()
            with self.assertRaisesRegex(ValueError, 'finite'):
                replace(small, mode=1, payload=_compress(raw), source_sha256=hashlib.sha256(raw).hexdigest())
        with patch('src.fixed_lossless_codec_v29._decode', side_effect=AssertionError('decoded too early')):
            with self.assertRaisesRegex(ValueError, 'hard byte bound'):
                replace(small, shape=(1, MAX_DECODED_BYTES//8+1))

    def test_parser_bounds_precede_decompression_and_bind_headers(self):
        descriptor = encode(np.ones((2, 4)))
        raw = serialize(descriptor)
        for limits in (LoadLimits(max_bytes=16), LoadLimits(max_header_bytes=1),
                       LoadLimits(max_values=7), LoadLimits(max_tokens=1), LoadLimits(max_width=3)):
            with patch('src.fixed_lossless_codec_v29._decode', side_effect=AssertionError('decoded too early')):
                with self.assertRaises(ValueError):
                    parse(raw, limits=limits)
        for changes in ({'shape':[1, 10**9]}, {'raw_bytes':False}, {'mode':True}, {'mode':3},
                        {'codec_sha256':'0'*64}, {'schema':'other'}, {'source_sha256':'0'*64}):
            with self.assertRaises(ValueError):
                parse(rewrite(raw, changes))
        for damaged in (raw+b'x', raw[:-1], raw[:30]+bytes([raw[30]^1])+raw[31:]):
            with self.assertRaises(ValueError):
                parse(damaged)
        with self.assertRaises(ValueError):
            parse(raw, expected_sha256='0'*64)
        with self.assertRaises(TypeError):
            parse(bytearray(raw))

    def test_parser_rejects_duplicate_keys_and_noncanonical_json(self):
        raw = serialize(encode(np.zeros((1, 1))))
        length = struct.unpack_from('<Q', raw, 8)[0]
        header = raw[16:16+length]
        duplicate = b'{"mode":0,'+header[1:]
        for invalid in (duplicate, json.dumps(json.loads(header), indent=1).encode()):
            with self.assertRaises(ValueError):
                parse(MAGIC+struct.pack('<Q', len(invalid))+invalid+raw[16+length:])

    def test_bindings_immutability_and_invalid_inputs(self):
        descriptor = encode(np.array([[0., -0., 1., -1.]]))
        manifest = codec_manifest()
        self.assertEqual(codec_binding(), hashlib.sha256(_json(manifest)).hexdigest())
        self.assertEqual(manifest['zlib_runtime_version'], zlib.ZLIB_RUNTIME_VERSION)
        self.assertIn(manifest['zlib_module_kind'], ('builtin', 'extension'))
        for field in ('record_id', 'stage_id'):
            self.assertNotEqual(replace(descriptor, **{field:'other'}).digest, descriptor.digest)
        for values in (np.array([[np.nan]]), np.array([[np.inf]])):
            with self.assertRaises(ValueError):
                encode(values)
        with self.assertRaises(TypeError):
            encode_factor(np.ones((1, 1), dtype=np.float32), **BINDINGS)
        with self.assertRaises(TypeError):
            replace(descriptor, payload=bytearray(descriptor.payload))

    def test_runtime_hash_cache_hits_invalidates_and_stays_bounded(self):
        from src import fixed_lossless_codec_v29 as codec
        codec._RUNTIME_HASH_CACHE.clear()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'runtime.bin'
            path.write_bytes(b'abcd')
            before = path.stat()
            original_read = Path.read_bytes
            with patch.object(Path, 'read_bytes', autospec=True, side_effect=original_read) as reads:
                first = codec._runtime_binary_digest(path)
                self.assertEqual(codec._runtime_binary_digest(path), first)
                self.assertEqual(reads.call_count, 1)
                path.write_bytes(b'wxyz')
                os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
                self.assertEqual(codec._runtime_binary_digest(path), hashlib.sha256(b'wxyz').hexdigest())
                self.assertEqual(reads.call_count, 2)
                replacement = Path(folder)/'replacement.bin'
                replacement.write_bytes(b'new!')
                os.replace(replacement, path)
                self.assertEqual(codec._runtime_binary_digest(path), hashlib.sha256(b'new!').hexdigest())
                self.assertEqual(reads.call_count, 3)
            for index in range(codec._RUNTIME_CACHE_ENTRIES+3):
                extra = Path(folder)/str(index)
                extra.write_bytes(bytes([index+1]))
                codec._runtime_binary_digest(extra)
                self.assertLessEqual(len(codec._RUNTIME_HASH_CACHE), codec._RUNTIME_CACHE_ENTRIES)
        codec._RUNTIME_HASH_CACHE.clear()

    def test_runtime_hash_cache_rejects_changed_identity_on_reads_and_hits(self):
        from src import fixed_lossless_codec_v29 as codec
        codec._RUNTIME_HASH_CACHE.clear()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'runtime.bin'
            path.write_bytes(b'abcd')
            identity = codec._binary_identity(path.resolve())
            changed = (*identity[:-1], identity[-1]+1)
            with patch.object(codec, '_binary_identity', side_effect=(identity, changed)):
                with self.assertRaisesRegex(ValueError, 'changed during'):
                    codec._runtime_binary_digest(path)
            self.assertEqual(codec._RUNTIME_HASH_CACHE, {})
            codec._runtime_binary_digest(path)
            with patch.object(codec, '_binary_identity', side_effect=(identity, changed)):
                with self.assertRaisesRegex(ValueError, 'changed during'):
                    codec._runtime_binary_digest(path)
            with self.assertRaisesRegex(ValueError, 'regular file'):
                codec._runtime_binary_digest(Path(folder))
        codec._RUNTIME_HASH_CACHE.clear()


if __name__ == '__main__':
    unittest.main()
