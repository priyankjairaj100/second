"""Source-local archive controls using standard zlib, Zstandard, and FPC.

This module does not change the V29 service. It implements measured archive
descriptors, not a complete service state. FPC requires the official binary.
"""
from dataclasses import dataclass
import hashlib
import inspect
import json
from pathlib import Path
import resource
import struct
import subprocess
import sys
import tempfile
import zlib

import numpy as np
import zstandard as zstd

from .compact_state import _digest, _name, _json
from .run_store import strict_json

MAGIC = b'V30LCTRL'
MAX_BYTES = 128 * 2**20
METHODS = ('raw', 'zlib6', 'shuffle_zlib6', 'zstd3', 'shuffle_zstd3',
           'zstd9', 'shuffle_zstd9', 'fpc8', 'fpc20')
FPC_SOURCE_SHA256 = 'f826ebc3d5aeece2b86bf5062a4ed4122f6605a66c5bfec813ddb44d2fc5843b'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def shuffle(raw):
    return np.frombuffer(raw, dtype=np.uint8).reshape(-1, 8).T.copy().tobytes()


def unshuffle(raw):
    return np.frombuffer(raw, dtype=np.uint8).reshape(8, -1).T.copy().tobytes()


class ControlRuntime:
    """Bound standard runtimes. Each FPC call receives explicit process limits."""

    def __init__(self, fpc_binary=None, fpc_sha256=None):
        self.fpc_binary = None if fpc_binary is None else Path(fpc_binary).resolve(strict=True)
        self.fpc_sha256 = fpc_sha256
        if self.fpc_binary is not None:
            _digest(fpc_sha256)
            if sys.byteorder != 'little' or sha(self.fpc_binary.read_bytes()) != fpc_sha256:
                raise ValueError('FPC requires the bound executable and a little-endian machine')
        elif fpc_sha256 is not None:
            raise ValueError('FPC digest requires its executable')
        self.manifest = dict(
            schema='archive-lossless-controls-runtime-v30',
            source_sha256={name: sha(Path(__file__).with_name(name).read_bytes())
                           for name in ('lossless_controls_v30.py', 'compact_state.py', 'run_store.py')},
            zstandard_package_version=zstd.__version__, zstandard_version=list(zstd.ZSTD_VERSION),
            zstandard_backend=zstd.backend,
            zstandard_binary_sha256=sha(Path(inspect.getfile(zstd.ZstdCompressor)).read_bytes()),
            zlib_version=zlib.ZLIB_RUNTIME_VERSION,
            zlib_binary_sha256=sha(Path(getattr(zlib, '__file__', sys.executable)).read_bytes()),
            fpc_binary_sha256=fpc_sha256,
            fpc_official_source_sha256=FPC_SOURCE_SHA256 if self.fpc_binary is not None else None,
            zstandard_settings=dict(levels=[3, 9], checksum=True, content_size=True, dict_id=False, threads=0),
            fpc_settings=dict(levels=[8, 20], cpu_limit_seconds=2, wall_timeout_seconds=5,
                              address_limit_bytes=256*2**20),
            canonical_scope='this encoder and the hash-bound trusted runtime')
        self.binding = sha(_json(self.manifest))

    @property
    def methods(self):
        return METHODS if self.fpc_binary is not None else METHODS[:-2]

    def _fpc(self, payload, method, decode, expected):
        if self.fpc_binary is None or sha(self.fpc_binary.read_bytes()) != self.fpc_sha256:
            raise ValueError('official FPC binary is unavailable or changed')
        level = int(method[3:])
        if decode and (not payload or payload[0] != level):
            raise ValueError('FPC level differs from descriptor')
        bound = expected + 8 if decode else expected*2 + 65536

        def restrict():
            resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
            resource.setrlimit(resource.RLIMIT_AS, (256*2**20, 256*2**20))
            resource.setrlimit(resource.RLIMIT_FSIZE, (bound, bound))
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

        command = [str(self.fpc_binary)] + ([] if decode else [str(level)])
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
            result = subprocess.run(command, input=payload, stdout=output, stderr=errors,
                                    preexec_fn=restrict, timeout=5, check=False)
            if result.returncode != 0:
                raise ValueError('bounded official FPC process failed')
            output.seek(0)
            raw = output.read(bound+1)
            if len(raw) > bound:
                raise ValueError('FPC output exceeds bound')
        return raw

    def compress(self, raw, method):
        if method not in self.methods:
            raise ValueError('unavailable compression method')
        if method == 'raw':
            return raw
        transformed = shuffle(raw) if method.startswith('shuffle_') else raw
        if 'zlib' in method:
            return zlib.compress(transformed, level=6)
        if 'zstd' in method:
            level = int(method[-1])
            return zstd.ZstdCompressor(level=level, write_checksum=True, write_content_size=True,
                                      write_dict_id=False, threads=0).compress(transformed)
        return self._fpc(raw, method, False, len(raw))

    def decompress(self, payload, method, expected):
        if type(payload) is not bytes or type(expected) is not int or not 8 <= expected <= MAX_BYTES:
            raise ValueError('invalid bounded decoded size or payload')
        if expected % 8 or method not in self.methods:
            raise ValueError('invalid binary64 size or unavailable method')
        if method == 'raw':
            raw = payload
        elif 'zlib' in method:
            decoder = zlib.decompressobj()
            try:
                raw = decoder.decompress(payload, expected+1)
            except zlib.error as exc:
                raise ValueError('invalid zlib stream') from exc
            if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
                raise ValueError('zlib stream is incomplete or has trailing data')
        elif 'zstd' in method:
            try:
                frame = zstd.get_frame_parameters(payload)
                if (frame.content_size != expected or frame.window_size > MAX_BYTES
                        or frame.dict_id != 0 or not frame.has_checksum):
                    raise ValueError('Zstandard frame differs from bounded format')
                raw = zstd.ZstdDecompressor(max_window_size=MAX_BYTES//1024).decompress(
                    payload, max_output_size=expected, allow_extra_data=False)
            except zstd.ZstdError as exc:
                raise ValueError('invalid Zstandard frame') from exc
        else:
            raw = self._fpc(payload, method, True, expected)
        if len(raw) != expected:
            raise ValueError('decoded length differs from descriptor shape')
        if method.startswith('shuffle_'):
            raw = unshuffle(raw)
        if not np.isfinite(np.frombuffer(raw, dtype='<f8')).all():
            raise ValueError('factor contains nonfinite binary64 words')
        return raw


@dataclass(frozen=True)
class Descriptor:
    header: dict
    payload: bytes

    def serialize(self):
        header = _json(self.header)
        return MAGIC+struct.pack('<Q', len(header))+header+self.payload


def encode(raw, *, runtime, method, target_sha256, anchor_target_sha256,
           record_id, token_sha256, stage_id, shape):
    if type(raw) is not bytes or len(shape) != 2 or any(type(n) is not int or n <= 0 for n in shape):
        raise ValueError('immutable binary64 bytes and a positive matrix shape are required')
    if len(raw) != 8*shape[0]*shape[1] or not 8 <= len(raw) <= MAX_BYTES:
        raise ValueError('source length differs from bounded shape')
    if not np.isfinite(np.frombuffer(raw, dtype='<f8')).all():
        raise ValueError('source contains nonfinite binary64 words')
    for value in (target_sha256, anchor_target_sha256, token_sha256):
        _digest(value)
    _name(record_id)
    _name(stage_id)
    payload = runtime.compress(raw, method)
    return Descriptor(dict(schema='source-local-lossless-control-v30', method=method,
        target_sha256=target_sha256, anchor_target_sha256=anchor_target_sha256,
        record_id=record_id, token_sha256=token_sha256, stage_id=stage_id,
        shape=list(shape), source_sha256=sha(raw), runtime_sha256=runtime.binding,
        raw_bytes=len(raw), payload_bytes=len(payload), payload_sha256=sha(payload)), payload)


def parse(data, *, runtime, expected_sha256=None, max_bytes=MAX_BYTES*2+65536):
    if type(data) is not bytes or type(max_bytes) is not int or max_bytes <= 0:
        raise ValueError('immutable bytes and a positive file bound are required')
    if not 16 <= len(data) <= max_bytes or data[:8] != MAGIC:
        raise ValueError('invalid descriptor framing or file size')
    if expected_sha256 is not None and sha(data) != _digest(expected_sha256):
        raise ValueError('descriptor digest differs')
    size = struct.unpack_from('<Q', data, 8)[0]
    if size > 65536 or size > len(data)-16:
        raise ValueError('descriptor header exceeds bound')
    encoded_header = data[16:16+size]
    try:
        header = strict_json(encoded_header)
        if _json(header) != encoded_header or type(header) is not dict:
            raise ValueError('descriptor header is not canonical')
        required = {'schema', 'method', 'target_sha256', 'anchor_target_sha256', 'record_id',
                    'token_sha256', 'stage_id', 'shape', 'source_sha256', 'runtime_sha256',
                    'raw_bytes', 'payload_bytes', 'payload_sha256'}
        if set(header) != required or header['schema'] != 'source-local-lossless-control-v30':
            raise ValueError('invalid descriptor schema')
        shape = header['shape']
        if (type(shape) is not list or len(shape) != 2
                or any(type(n) is not int or n <= 0 for n in shape)):
            raise ValueError('invalid descriptor shape')
        if header['runtime_sha256'] != runtime.binding:
            raise ValueError('descriptor runtime binding differs')
        for key in ('target_sha256', 'anchor_target_sha256', 'token_sha256',
                    'source_sha256', 'runtime_sha256', 'payload_sha256'):
            _digest(header[key])
        _name(header['record_id'])
        _name(header['stage_id'])
        expected = 8*shape[0]*shape[1]
        if type(header['raw_bytes']) is not int or header['raw_bytes'] != expected:
            raise ValueError('raw byte count differs from shape')
        payload = data[16+size:]
        if (type(header['payload_bytes']) is not int or header['payload_bytes'] != len(payload)
                or header['payload_sha256'] != sha(payload)):
            raise ValueError('payload binding differs')
        raw = runtime.decompress(payload, header['method'], expected)
        if sha(raw) != header['source_sha256']:
            raise ValueError('decoded source binding differs')
        canonical = encode(raw, runtime=runtime, method=header['method'],
            target_sha256=header['target_sha256'], anchor_target_sha256=header['anchor_target_sha256'],
            record_id=header['record_id'], token_sha256=header['token_sha256'],
            stage_id=header['stage_id'], shape=shape)
        if canonical.serialize() != data:
            raise ValueError('descriptor encoding is not canonical')
        return canonical, raw
    except (KeyError, TypeError, UnicodeError, RecursionError) as exc:
        raise ValueError('invalid descriptor content') from exc
