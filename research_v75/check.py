"""Generated fixtures only: compatibility, malformed payloads and local timing."""
from contextlib import contextmanager
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import platform
import statistics
import struct
import sys
import time
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parent
REPO = Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT.parent
sys.path.insert(0, str(REPO))
from src import fixed_factor_codec_v26 as reference
from fast_decode import decode_payload, library

ORIGINAL = reference._decode_payload
BINDINGS = dict(target_sha256='a'*64, anchor_target_sha256='b'*64,
    record_id='generated-software-fixture', token_sha256='c'*64, stage_id='stage.fixture')

@contextmanager
def using(fn):
    # Single process, fixture-only dispatch. Never saved into campaign code.
    reference._decode_payload = fn
    try:
        yield
    finally:
        reference._decode_payload = ORIGINAL

def outcome(fn, payload, shape, bits, block, radius):
    try:
        values = fn(payload, shape, bits, block, with_radius=radius)
        return ('ok', tuple(v.tobytes() if isinstance(v, np.ndarray) else v for v in values))
    except (ValueError, TypeError):
        return ('reject',)

def main():
    start = time.perf_counter()
    source = REPO/'src/fixed_factor_codec_v26.py'
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    library()  # Compile/load outside timing samples; no cold-start claim.
    report = dict(scope='Generated software fixtures; no model, dataset, service or Linux campaign result',
        platform=platform.platform(), machine=platform.machine(), python=sys.version,
        numpy=np.__version__, reference_sha256=before, clock='perf_counter_ns',
        fixture_seed=20261022, compile_excluded=True)
    spec = importlib.util.spec_from_file_location('legacy_codec_tests', REPO/'tests/test_fixed_factor_codec_v26.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report['legacy_tests'] = {}
    for name, fn in [('reference', ORIGINAL), ('prototype', decode_payload)]:
        output = io.StringIO()
        with using(fn):
            result = unittest.TextTestRunner(stream=output).run(unittest.defaultTestLoader.loadTestsFromModule(module))
        report['legacy_tests'][name] = dict(tests=result.testsRun, passed=result.wasSuccessful(), log=output.getvalue())
        if not result.wasSuccessful():
            raise AssertionError(output.getvalue())
    rng = np.random.default_rng(20261022)
    counts = dict(valid=0, mutated=0, boundary=0, accepted_mutations=0, rejected_mutations=0)
    for bits in reference.PRECISIONS:
        words = rng.integers(0, 2**64, size=16384, dtype=np.uint64)
        # Replace nonfinite exponents with the largest finite exponent.
        nonfinite = ((words >> np.uint64(52)) & np.uint64(2047)) == 2047
        words[nonfinite] ^= np.uint64(1 << 52)
        values = words.view(np.float64).reshape(64, 256)
        for block in (1, 19, 256, 4096):
            descriptor = reference.encode_factor(values, bits=bits, block_size=block, **BINDINGS)
            for radius in (False, True):
                assert outcome(ORIGINAL, descriptor.payload, values.shape, bits, block, radius) == outcome(
                    decode_payload, descriptor.payload, values.shape, bits, block, radius)
                counts['valid'] += 1
        # A small corpus makes byte mutation/truncation exhaustive enough to be useful.
        edge = np.array([[0., -0., 1., -1., np.finfo(float).max, -np.finfo(float).max,
                          np.nextafter(0., 1.), 0.12345, 4., -7., 1e-200, 1e200, -0.333]])
        descriptor = reference.encode_factor(edge, bits=bits, block_size=5, **BINDINGS)
        corpus = [descriptor.payload[:i] for i in range(len(descriptor.payload))]
        corpus += [descriptor.payload+b'\x00', descriptor.payload+b'bad']
        for _ in range(600):
            bad = bytearray(descriptor.payload)
            for __ in range(int(rng.integers(1, 5))):
                index = int(rng.integers(len(bad)))
                bad[index] ^= int(rng.integers(1, 256))
            corpus.append(bytes(bad))
        for payload in corpus:
            for radius in (False, True):
                a = outcome(ORIGINAL, payload, edge.shape, bits, 5, radius)
                b = outcome(decode_payload, payload, edge.shape, bits, 5, radius)
                assert a == b, (bits, radius, payload.hex(), a[0], b[0])
                counts['mutated'] += 1
                counts['accepted_mutations' if a[0] == 'ok' else 'rejected_mutations'] += 1
        # Target exponent and integer extremes, reserved flags and escape cases.
        for top in (-32768, -1075, -1074, -1022, 0, 1023, 1024, 32767):
            for integer in (-(1 << (bits-1)), -1, 0, 1, (1 << (bits-1))-1):
                for flag in range(4):
                    p = struct.pack('<hB', top, flag)+integer.to_bytes(bits//8, 'little', signed=True)
                    for radius in (False, True):
                        assert outcome(ORIGINAL, p, (1, 1), bits, 1, radius) == outcome(
                            decode_payload, p, (1, 1), bits, 1, radius)
                        counts['boundary'] += 1
    report['differential_cases'] = counts
    report['benchmarks'] = []
    for width in (768, 3072):
        values = rng.normal(size=(128, width))
        values[:, ::31] = 0.
        descriptor = reference.encode_factor(values, bits=48, block_size=256, **BINDINGS)
        blob = reference.serialize(descriptor)
        expected = reference.parse(blob).box()
        samples = {'reference': [], 'prototype': []}
        for repetition in range(6):
            order = [('reference', ORIGINAL), ('prototype', decode_payload)]
            if repetition%2:
                order.reverse()
            for name, fn in order:
                with using(fn):
                    tick = time.perf_counter_ns()
                    box = reference.parse(blob).box()
                    elapsed = time.perf_counter_ns()-tick
                # Comparison outside timed region, exact words including signed zeros.
                assert box.lower.tobytes() == expected.lower.tobytes()
                assert box.upper.tobytes() == expected.upper.tobytes()
                samples[name].append(elapsed)
        medians = {name: statistics.median(times)/1e9 for name, times in samples.items()}
        report['benchmarks'].append(dict(shape=list(values.shape), bits=48, block_size=256,
            operation='legacy parse(blob).box(), two full decodes plus checks/copies',
            payload_sha256=hashlib.sha256(blob).hexdigest(), bytes=len(blob),
            samples_ns=samples, median_seconds=medians,
            ratio_reference_over_prototype=medians['reference']/medians['prototype']))
    assert before == hashlib.sha256(source.read_bytes()).hexdigest()
    report['source_hashes'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (ROOT/'decode.c', ROOT/'fast_decode.py', ROOT/'check.py')}
    report['elapsed_seconds'] = time.perf_counter()-start
    (ROOT/'software-results.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k in ('scope', 'platform', 'differential_cases', 'benchmarks', 'elapsed_seconds')}, indent=2))

if __name__ == '__main__':
    main()
