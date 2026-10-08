"""Measure lossless controls on saved real factors. Execute no model work."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import time
import urllib.request

START_WALL = time.perf_counter_ns()
START_CPU = time.process_time_ns()
START_CHILD = resource.getrusage(resource.RUSAGE_CHILDREN)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.analyze_fixed_codec_v24 import load_generation
from src.compact_state import token_digest, _json
from src.lossless_controls_v30 import ControlRuntime, FPC_SOURCE_SHA256, encode, parse, sha


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def combined_cpu_ns():
    child = resource.getrusage(resource.RUSAGE_CHILDREN)
    return time.process_time_ns()-START_CPU+round(1e9*(
        child.ru_utime+child.ru_stime-START_CHILD.ru_utime-START_CHILD.ru_stime))


def prepare_fpc(directory):
    """Fetch official licensed source. Remove its email header without algorithm edits."""
    directory.mkdir(parents=True, exist_ok=False)
    files = {}
    for name, url, expected in (
            ('fpc.original.c', 'https://userweb.cs.txstate.edu/~burtscher/research/FPC/fpc.c', FPC_SOURCE_SHA256),
            ('FPClicense.pdf', 'https://userweb.cs.txstate.edu/~burtscher/research/FPC/FPClicense.pdf',
             '88cc4b914c62f76dd46d8dfe7fc10681293e07b77b49c0e43434b4c92b5db780')):
        with urllib.request.urlopen(url, timeout=30) as response:
            raw = response.read(1024*1024+1)
        if len(raw) > 1024*1024 or sha(raw) != expected:
            raise ValueError('official FPC source or license differs from pinned bytes')
        (directory/name).write_bytes(raw)
        files[name] = dict(url=url, sha256=sha(raw), bytes=len(raw))
    original = (directory/'fpc.original.c').read_bytes()
    prefix = b'Subject: FPC v1.1\r\n\r\n'
    if not original.startswith(prefix):
        raise ValueError('official FPC email prefix changed')
    changed = b'/* 2026-10-08: Removed the email Subject header only; algorithm unchanged. */\n'+original[len(prefix):]
    (directory/'fpc.c').write_bytes(changed)
    compiler = shutil.which('gcc')
    if compiler is None:
        raise ValueError('the official recommended compiler is unavailable')
    command = [compiler, '-O3', str(directory/'fpc.c'), '-o', str(directory/'fpc')]
    result = subprocess.run(command, capture_output=True, timeout=30, check=True)
    for name in ('fpc.c', 'fpc'):
        raw = (directory/name).read_bytes()
        files[name] = dict(sha256=sha(raw), bytes=len(raw))
    report = dict(schema='official-fpc-setup-v30', status='complete', files=files,
        algorithm_changes=False, source_change='remove email Subject header; add dated change notice',
        license='official noncommercial research and teaching terms; notice remains in compiled source',
        redistributed_vendor_source=False, compiler_command=command,
        compiler_version=subprocess.check_output([compiler, '--version'], text=True).splitlines()[0],
        compiler_binary_sha256=sha(Path(compiler).resolve().read_bytes()),
        compiler_stdout=result.stdout.decode(), compiler_stderr=result.stderr.decode(),
        combined_cpu_ns_since_imports=combined_cpu_ns(), wall_ns_since_imports=time.perf_counter_ns()-START_WALL,
        cost_scope='setup through source verification and compilation; excludes final receipt write')
    write(directory/'setup.json', report)
    print(json.dumps(dict(status='complete', setup_file=str(directory/'setup.json'))))


def projection(state, provenance, records, method, binding):
    index = dict(schema='projected-lossless-control-envelope-v30', method=method,
        target_sha256=state.target_sha256, anchor_target_sha256=state.anchor_target_sha256,
        decoder_sha256=state.decoder_sha256, provider_sha256=state.provider_sha256,
        anchor_sha256=state.anchor_sha256, preparer_sha256=state.preparer_sha256,
        runtime_sha256=binding,
        model=dict(bytes=provenance['model_bytes'], sha256=provenance['model_sha256']), records=records)
    header = _json(index)
    descriptors = sum(item['bytes'] for record in records for item in record['descriptors'])
    return dict(projected_only=True, service_format_implemented=False, framing_bytes=16,
        index_bytes=len(header), index_sha256=sha(header), descriptor_bytes=descriptors,
        complete_calibrated_model_bytes=provenance['model_bytes'],
        projected_complete_state_bytes=16+len(header)+descriptors+provenance['model_bytes'],
        required_common_base_checkpoint_excluded=True,
        framing_assumption='eight magic bytes; eight header-length bytes; canonical index; model; descriptors')


def audit(args):
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=False)
    setup_path = args.fpc_dir/'setup.json' if args.fpc_dir else None
    setup = json.loads(setup_path.read_bytes()) if setup_path else None
    if setup:
        if setup['status'] != 'complete':
            raise ValueError('FPC setup is incomplete')
        for name, info in setup['files'].items():
            if sha((args.fpc_dir/name).read_bytes()) != info['sha256']:
                raise ValueError('FPC setup artifact differs')
    runtime = ControlRuntime(args.fpc_dir/'fpc' if setup else None,
                             setup['files']['fpc']['sha256'] if setup else None)
    source_paths = ('scripts/analyze_lossless_controls_v30.py', 'src/lossless_controls_v30.py',
                    'tests/test_lossless_controls_v30.py', 'scripts/analyze_fixed_codec_v24.py',
                    'src/fixed_factor_state.py', 'src/compact_state.py', 'src/run_store.py')
    sources = {path: sha((ROOT/path).read_bytes()) for path in source_paths}
    alp = dict(status='unavailable_supported_compiler', measured=False,
        official_repository='https://github.com/cwida/ALP',
        checked_commit='31ca0ed11c93c99d3f5b5c30e01a3e1c3832d3ce',
        reason='official CMake requires Clang; clang++ is absent from PATH; no substitute or emulation measured',
        remaining='build the pinned official implementation with supported Clang, then add source-local bitwise checks')
    if args.alp_dir:
        alp['observed_commit'] = subprocess.check_output(['git', '-C', str(args.alp_dir), 'rev-parse', 'HEAD'], text=True).strip()
        alp['cmake_sha256'] = sha((args.alp_dir/'CMakeLists.txt').read_bytes())
        alp['clang_plus_plus_path'] = shutil.which('clang++')
        if alp['observed_commit'] != alp['checked_commit'] or alp['clang_plus_plus_path'] is not None:
            raise ValueError('ALP availability assumptions changed; review before measurement')
    plan = dict(schema='lossless-archive-controls-plan-v30', source_sha256=sources,
        methods=list(runtime.methods), runtime=runtime.manifest, runtime_sha256=runtime.binding,
        generations=['prepare-001', 'repair-001'], cpu_soft_cap_seconds=args.cpu_cap_seconds,
        scope='saved real factor bytes only; no model inference, quantization, service, or quality evaluation',
        cost_account='archive analysis outside empirical worker ledgers; includes child codec CPU',
        per_factor_selection='minimize actual descriptor bytes; ties follow the registered method order',
        setup_sha256=sha(setup_path.read_bytes()) if setup else None, alp=alp,
        empirical_worker_budget_charged=False, complete_service_timing=False)
    write(output/'plan.json', plan)
    if setup:
        write(output/'fpc_setup.json', setup)
    for name in source_paths:
        destination = output/'source'/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, destination)
    report = dict(schema='lossless-archive-controls-summary-v30', status='running',
        plan_sha256=sha((output/'plan.json').read_bytes()), generations={}, cells=[],
        available_methods=list(runtime.methods), alp=alp, complete_service_timing=False,
        speed_claim=False, stored_service_format_implemented=False)
    originals = {}
    matches = 0

    def check_cpu(*_):
        if combined_cpu_ns() > args.cpu_cap_seconds*10**9:
            raise TimeoutError('archive controls combined CPU soft cap exceeded')

    signal.signal(signal.SIGPROF, check_cpu)
    signal.setitimer(signal.ITIMER_PROF, 1, 1)
    try:
        for attempt_name in plan['generations']:
            state, provenance = load_generation(ROOT/'campaigns/fixed_feature_v23/attempts'/attempt_name)
            totals = {method: dict(payload_bytes=0, descriptor_bytes=0, factors=0) for method in runtime.methods}
            records = {method: [] for method in runtime.methods}
            selection_records = []
            selection_counts = {method: 0 for method in runtime.methods}
            raw_total = 0
            for leaf in state.anchors:
                entries = {method: [] for method in runtime.methods}
                selected_entries = []
                for block in leaf.blocks:
                    check_cpu()
                    raw = block.binary64
                    raw_total += len(raw)
                    options = []
                    for method in runtime.methods:
                        before = combined_cpu_ns()
                        descriptor = encode(raw, runtime=runtime, method=method,
                            target_sha256=state.target_sha256, anchor_target_sha256=state.anchor_target_sha256,
                            record_id=leaf.record_id, token_sha256=token_digest(leaf.tokens),
                            stage_id=block.stage_id, shape=(block.token_count, block.width))
                        encoded = descriptor.serialize()
                        parsed, restored = parse(encoded, runtime=runtime, expected_sha256=sha(encoded))
                        if restored != raw or parsed.serialize() != encoded:
                            raise ValueError('exact canonical roundtrip failed')
                        key = (leaf.record_id, block.stage_id, method)
                        if attempt_name == 'prepare-001':
                            originals[key] = sha(encoded)
                        elif originals[key] != sha(encoded):
                            raise ValueError('retained source descriptor changed')
                        else:
                            matches += 1
                        totals[method]['payload_bytes'] += len(descriptor.payload)
                        totals[method]['descriptor_bytes'] += len(encoded)
                        totals[method]['factors'] += 1
                        entry = dict(stage_id=block.stage_id, bytes=len(encoded), sha256=sha(encoded))
                        entries[method].append(entry)
                        options.append((len(encoded), list(runtime.methods).index(method), method, entry))
                        report['cells'].append(dict(attempt=attempt_name, record_id=leaf.record_id,
                            stage_id=block.stage_id, method=method, raw_bytes=len(raw), source_sha256=sha(raw),
                            payload_bytes=len(descriptor.payload), payload_sha256=sha(descriptor.payload),
                            descriptor_bytes=len(encoded), descriptor_sha256=sha(encoded),
                            exact_roundtrip=True, canonical_roundtrip=True,
                            diagnostic_encode_parse_cpu_ns=combined_cpu_ns()-before))
                    _, _, chosen, entry = min(options)
                    selection_counts[chosen] += 1
                    selected_entries.append(entry)
                for method in runtime.methods:
                    records[method].append(dict(record_id=leaf.record_id, tokens=list(leaf.tokens),
                                                descriptors=entries[method]))
                selection_records.append(dict(record_id=leaf.record_id, tokens=list(leaf.tokens),
                                               descriptors=selected_entries))
            for method, values in totals.items():
                values['payload_ratio_to_raw'] = values['payload_bytes']/raw_total
                values['projection'] = projection(state, provenance, records[method], method, runtime.binding)
            report['generations'][attempt_name] = dict(**provenance, raw_factor_bytes=raw_total,
                methods=totals, source_local_selection_counts=selection_counts,
                source_local_selection=projection(state, provenance, selection_records, 'min_descriptor', runtime.binding))
        if any(sha((ROOT/path).read_bytes()) != digest for path, digest in sources.items()):
            raise ValueError('analysis source changed during execution')
        report.update(status='complete', canonical_retained_descriptor_pairs_equal=matches,
                      all_roundtrips_bit_exact=True)
    except Exception as exc:
        report.update(status='incomplete', error_type=type(exc).__name__, error=str(exc))
    finally:
        signal.setitimer(signal.ITIMER_PROF, 0)
    child = resource.getrusage(resource.RUSAGE_CHILDREN)
    report.update(parent_cpu_ns_since_imports=time.process_time_ns()-START_CPU,
        child_cpu_ns_since_imports=round(1e9*(child.ru_utime+child.ru_stime-START_CHILD.ru_utime-START_CHILD.ru_stime)),
        combined_cpu_ns_since_imports=combined_cpu_ns(), wall_ns_since_imports=time.perf_counter_ns()-START_WALL,
        cost_scope='through archive verification; excludes final report serialization and write',
        diagnostic_clock_scope='nested encode, bounded decode, hash checks, and canonical re-encode; no throughput comparison',
        empirical_worker_budget_charged=False)
    write(output/'summary.json', report)
    print(json.dumps({key: report.get(key) for key in ('status', 'combined_cpu_ns_since_imports', 'error')}))
    if report['status'] != 'complete':
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-fpc', type=Path)
    parser.add_argument('--fpc-dir', type=Path)
    parser.add_argument('--alp-dir', type=Path)
    parser.add_argument('--output-dir', type=Path, default=ROOT/'campaigns/lossless_controls_v30')
    parser.add_argument('--cpu-cap-seconds', type=int, default=60)
    args = parser.parse_args()
    if not 1 <= args.cpu_cap_seconds <= 120:
        parser.error('archive CPU allowance must be between 1 and 120 seconds')
    if args.prepare_fpc:
        prepare_fpc(args.prepare_fpc)
    else:
        audit(args)


if __name__ == '__main__':
    main()
