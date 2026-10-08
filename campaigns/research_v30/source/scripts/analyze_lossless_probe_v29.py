"""Inspect archived factor bytes for lossless coding. No model execution."""
import argparse
import hashlib
import json
from pathlib import Path
import signal
import sys
import time
import zlib

START_WALL = time.perf_counter_ns()
START_CPU = time.process_time_ns()
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from scripts.analyze_fixed_codec_v24 import load_generation


def sha(value):
    return hashlib.sha256(value).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inspect_lattice(raw, block_size=256):
    words = np.frombuffer(raw, dtype='<u8')
    absolute = words & np.uint64((1 << 63)-1)
    exponent = (absolute >> np.uint64(52)).astype(np.int64)
    fraction = absolute & np.uint64((1 << 52)-1)
    mantissa = np.where(exponent == 0, fraction, fraction | np.uint64(1 << 52))
    powers = np.where(exponent == 0, -1074, exponent-1075)
    with np.errstate(over='ignore'):
        lowbit = mantissa & (np.uint64(0)-mantissa)
    trailing = np.frexp(lowbit.astype(np.float64))[1]-1
    significant = np.frexp(mantissa.astype(np.float64))[1]-trailing
    tops = powers+np.frexp(mantissa.astype(np.float64))[1]-1
    widths = []
    for start in range(0, len(words), block_size):
        index = slice(start, start+block_size)
        nonzero = mantissa[index] != 0
        if not np.any(nonzero):
            widths.append(1)
        else:
            least = int(np.min((powers+trailing)[index][nonzero]))
            top = int(np.max(tops[index][nonzero]))
            widths.append(top-least+2)
    return dict(block_size=block_size, blocks=len(widths),
        conservative_signed_width_histogram={str(n):widths.count(n) for n in sorted(set(widths))},
        blocks_width_at_most_48=sum(n <= 48 for n in widths),
        blocks_width_at_most_56=sum(n <= 56 for n in widths),
        blocks_width_at_most_64=sum(n <= 64 for n in widths),
        value_significand_width_histogram={str(n):int(np.count_nonzero((significant == n)&(mantissa != 0)))
            for n in sorted(set(significant[mantissa != 0].tolist()))},
        negative_zero_count=int(np.count_nonzero(words == np.uint64(1 << 63))),
        note='signed block width uses the largest exponent and smallest intrinsic dyadic power; metadata and zero signs cost extra')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT/'campaigns/lossless_probe_v29')
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    sources = {name:sha((ROOT/name).read_bytes()) for name in (
        'scripts/analyze_lossless_probe_v29.py', 'scripts/analyze_fixed_codec_v24.py',
        'src/fixed_factor_state.py', 'src/compact_state.py')}
    report = dict(schema='lossless-factor-archive-probe-v29', status='running', source_sha256=sources,
        scope='archive byte analysis only; no neural inference, quantization, or service timing',
        cpu_soft_cap_seconds=60, empirical_worker_budget_charged=False,
        cost_account='archive analysis process outside empirical worker ledger',
        zlib_compile_version=zlib.ZLIB_VERSION, zlib_runtime_version=zlib.ZLIB_RUNTIME_VERSION,
        settings=dict(zlib_level=6, byte_shuffle='eight little-endian byte planes', dyadic_block_size=256),
        generations={}, compression_cells=[], stored_format_implemented=False, speed_claim=False)

    def timeout(*_):
        raise TimeoutError('archive probe CPU soft cap exceeded')

    signal.signal(signal.SIGPROF, timeout)
    signal.setitimer(signal.ITIMER_PROF, 60)
    original_payloads = {}
    matches = 0
    try:
        for name in ('prepare-001', 'repair-001'):
            state, provenance = load_generation(ROOT/'campaigns/fixed_feature_v23/attempts'/name)
            totals = dict(raw=0, zlib6=0, shuffled_zlib6=0, raw_zlib_best=0)
            lattice_totals = dict(blocks=0, blocks_width_at_most_48=0,
                                  blocks_width_at_most_56=0, blocks_width_at_most_64=0)
            for leaf in state.anchors:
                for block in leaf.blocks:
                    raw = block.binary64
                    shuffled = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 8).T.copy().tobytes()
                    plain, shuf = zlib.compress(raw, 6), zlib.compress(shuffled, 6)
                    require(zlib.decompress(plain) == raw, 'raw zlib roundtrip failed')
                    restored = np.frombuffer(zlib.decompress(shuf), dtype=np.uint8).reshape(8, -1).T.copy().tobytes()
                    require(restored == raw, 'shuffled zlib roundtrip failed')
                    lattice = inspect_lattice(raw)
                    for key in lattice_totals:
                        lattice_totals[key] += lattice[key]
                    sizes = dict(raw=len(raw), zlib6=len(plain), shuffled_zlib6=len(shuf),
                                 raw_zlib_best=min(len(raw), len(plain), len(shuf)))
                    for key in totals:
                        totals[key] += sizes[key]
                    key = (leaf.record_id, block.stage_id)
                    hashes = (sha(plain), sha(shuf))
                    if name == 'prepare-001':
                        original_payloads[key] = hashes
                    else:
                        require(original_payloads[key] == hashes, 'retained lossless payload changed')
                        matches += 1
                    report['compression_cells'].append(dict(attempt=name, record_id=leaf.record_id,
                        stage_id=block.stage_id, source_sha256=sha(raw), payload_bytes=sizes,
                        payload_sha256=dict(zlib6=hashes[0], shuffled_zlib6=hashes[1]), lattice=lattice,
                        exact_roundtrips=True))
            report['generations'][name] = dict(**provenance, payload_bytes=totals,
                lattice_totals=lattice_totals, descriptor_and_state_overhead_excluded=True,
                ratios_to_raw={key:value/totals['raw'] for key,value in totals.items()})
        report.update(status='complete', retained_factor_payload_pairs_equal=matches,
                      all_roundtrips_exact=True)
    except Exception as exc:
        report.update(status='incomplete', error_type=type(exc).__name__, error=str(exc))
    finally:
        signal.setitimer(signal.ITIMER_PROF, 0)
    report['analysis_cpu_ns_since_script_imports'] = time.process_time_ns()-START_CPU
    report['analysis_wall_ns_since_script_imports'] = time.perf_counter_ns()-START_WALL
    report['cost_scope'] = 'through archive checks; excludes final report serialization and write'
    with (args.output_dir/'summary.json').open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    print(json.dumps({key:report.get(key) for key in ('status', 'analysis_cpu_ns_since_script_imports', 'error')}))
    if report['status'] != 'complete':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
