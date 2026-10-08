"""Software fixtures for source-local archive compression controls."""
import copy
import os
from pathlib import Path
import struct
import unittest

import numpy as np
import zstandard as zstd

from src.compact_state import _json
from src.lossless_controls_v30 import (
    ControlRuntime, MAGIC, MAX_BYTES, Descriptor, encode, parse, sha,
)


class LosslessControlsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        binary = os.environ.get('V30_FPC_BINARY')
        cls.runtime = ControlRuntime(binary, sha(Path(binary).read_bytes()) if binary else None)
        cls.context = dict(target_sha256='a'*64, anchor_target_sha256='b'*64,
                           record_id='record-1', token_sha256='c'*64, stage_id='stage-1', shape=(2, 4))
        cls.raw = np.asarray([0, 1 << 63, 1, (1 << 63)+1, 0x3ff0000000000000,
                              0xbff0000000000000, 0x7fefffffffffffff, 0xffefffffffffffff],
                             dtype='<u8').tobytes()

    def descriptor(self, method='shuffle_zstd3', raw=None):
        return encode(self.raw if raw is None else raw, runtime=self.runtime, method=method, **self.context)

    def test_every_available_method_preserves_all_finite_edge_bits(self):
        for method in self.runtime.methods:
            with self.subTest(method=method):
                descriptor = self.descriptor(method)
                restored, raw = parse(descriptor.serialize(), runtime=self.runtime,
                                      expected_sha256=sha(descriptor.serialize()))
                self.assertEqual(raw, self.raw)
                self.assertEqual(restored.serialize(), descriptor.serialize())

    def test_source_local_determinism(self):
        before = self.descriptor().serialize()
        self.descriptor(raw=np.arange(8, dtype='<f8').tobytes())
        self.assertEqual(before, self.descriptor().serialize())

    def test_runtime_binding_and_source_hash_rejected(self):
        for key in ('runtime_sha256', 'source_sha256', 'payload_sha256', 'token_sha256'):
            d = self.descriptor()
            header = copy.deepcopy(d.header)
            header[key] = 'not-a-digest'
            with self.subTest(key=key), self.assertRaises(ValueError):
                parse(Descriptor(header, d.payload).serialize(), runtime=self.runtime)

    def test_size_limits_and_nonfinite_source_rejected(self):
        data = self.descriptor().serialize()
        with self.assertRaises(ValueError):
            parse(data, runtime=self.runtime, max_bytes=len(data)-1)
        with self.assertRaises(ValueError):
            self.runtime.decompress(b'', 'zstd3', MAX_BYTES+8)
        with self.assertRaises(ValueError):
            self.descriptor(raw=np.asarray([float('nan')]*8, dtype='<f8').tobytes())

    def test_truncated_and_extra_streams_rejected(self):
        for method in ('zlib6', 'shuffle_zlib6', 'zstd3', 'shuffle_zstd9'):
            payload = self.descriptor(method).payload
            for bad in (payload[:-1], payload+b'x', payload+payload):
                with self.subTest(method=method, size=len(bad)), self.assertRaises(ValueError):
                    self.runtime.decompress(bad, method, len(self.raw))

    def test_zstd_content_size_checksum_and_canonical_settings(self):
        for payload in (zstd.ZstdCompressor(write_checksum=False).compress(self.raw),
                        zstd.ZstdCompressor(write_content_size=False).compress(self.raw),
                        zstd.ZstdCompressor(write_checksum=True).compress(self.raw*2)):
            with self.assertRaises(ValueError):
                self.runtime.decompress(payload, 'zstd3', len(self.raw))
        d = self.descriptor('zstd3')
        payload = zstd.ZstdCompressor(level=3, write_checksum=True, write_content_size=True,
                                     write_dict_id=False).compress(self.raw)
        self.assertEqual(payload, d.payload)

    def test_duplicate_keys_and_noncanonical_json_rejected(self):
        d = self.descriptor()
        for header in (_json(d.header)+b' ', b'{"schema":"a","schema":"b"}'):
            data = MAGIC+struct.pack('<Q', len(header))+header+d.payload
            with self.assertRaises(ValueError):
                parse(data, runtime=self.runtime)

    def test_tampering_requires_matching_trusted_digest(self):
        data = self.descriptor().serialize()
        with self.assertRaises(ValueError):
            parse(data, runtime=self.runtime, expected_sha256='d'*64)
        for field, value in [('shape', [1, 1]), ('payload_bytes', True), ('raw_bytes', True),
                             ('method', 'unknown'), ('unexpected', 1)]:
            d = self.descriptor()
            header = copy.deepcopy(d.header)
            header[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                parse(Descriptor(header, d.payload).serialize(), runtime=self.runtime)

    def test_missing_fpc_is_explicit(self):
        runtime = ControlRuntime()
        self.assertNotIn('fpc8', runtime.methods)
        with self.assertRaises(ValueError):
            runtime.compress(self.raw, 'fpc8')


if __name__ == '__main__':
    unittest.main()
