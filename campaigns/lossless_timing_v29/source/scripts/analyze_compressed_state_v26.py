"""Audit and save version 26 compressed states from sealed archives. No model execution."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import signal
import sys
import time

_WALL_START = time.perf_counter_ns()
_CPU_START = time.process_time_ns()
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.analyze_fixed_codec_v24 import load_generation
from src.compact_state import CompactState, serialize as encode_model
from src.fixed_compressed_state_v26 import from_factor_state, serialize, parse
from src.fixed_factor_codec_v26 import codec_binding, serialize as encode_descriptor

SOURCES = (
    'scripts/analyze_compressed_state_v26.py', 'scripts/analyze_fixed_codec_v24.py',
    'src/fixed_compressed_state_v26.py', 'src/fixed_factor_codec_v26.py',
    'src/fixed_factor_state.py', 'src/fixed_anchor_service.py',
    'src/compact_state.py', 'src/anchor_state.py', 'src/sequential_finite.py',
    'src/finite_feature_boxes.py',
)
REVIEWED_SOURCES = {
    'src/fixed_compressed_state_v26.py': 'ca474697fe4ad404baf4cbd4b1100a5ccd58f7d0a63ef4c02234dd4d58cd07d0',
    'src/fixed_factor_codec_v26.py': 'd5f8a4c5279ef759b7d58eadd85429cffdfe7bdb3fe788aaaed05d12501f8711',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def source_hashes():
    return {name: sha((ROOT/name).read_bytes()) for name in SOURCES}


def relative(path):
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def write_new(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def audit(campaign, plan, output_dir):
    started_cpu = time.process_time_ns()
    report = dict(schema='compressed-state-archive-audit-v26', status='running',
        scope='archive conversion and serialization only; no neural or quantization execution',
        bits=[40], block_size=256, generations={}, comparisons={},
        source_hashes=plan['source_hashes'], cpu_cap_seconds=plan['cpu_cap_seconds'],
        empirical_worker_budget_charged=False,
        cost_account='archive analysis process; separate from empirical worker ledgers',
        state_format_implemented=True, state_sizes_projected=False,
        artifacts_saved=False, reviewed_source_hashes=REVIEWED_SOURCES,
        speed_claim=False, quality_claim=False, certificate_acceptance_measured=False,
        trust_premise='validated trusted exact archives establish descriptor containment; hashes alone do not establish it')

    def timeout(*_):
        raise TimeoutError('archive audit exceeded its CPU soft limit')

    def check_cap():
        if time.process_time_ns()-started_cpu >= plan['cpu_cap_seconds']*10**9:
            timeout()

    previous_handler = signal.signal(signal.SIGPROF, timeout)
    signal.setitimer(signal.ITIMER_PROF, plan['cpu_cap_seconds'])
    try:
        states, provenance = {}, {}
        for name in ('prepare-001', 'repair-001'):
            check_cap()
            states[name], provenance[name] = load_generation(campaign/'attempts'/name)
            report['generations'][name] = dict(**provenance[name], precisions={})
        original, retained = states['prepare-001'], states['repair-001']
        retained_ids = set(retained.record_ids)
        require(retained_ids < set(original.record_ids), 'archive does not describe strict source deletion')
        require(original.target_sha256 == retained.target_sha256, 'archive targets differ')
        descriptor_count, surviving_matches = 0, 0
        for bits in (40,):
            converted = {}
            for name in ('prepare-001', 'repair-001'):
                check_cap()
                source = states[name]
                start_wall, start_cpu = time.perf_counter_ns(), time.process_time_ns()
                state = from_factor_state(source, bits=bits, block_size=256)
                raw = serialize(state)
                restored = parse(raw, expected_sha256=sha(raw))
                require(serialize(restored) == raw, 'compressed state roundtrip differs')
                require(restored == state, 'parsed state fields differ')
                require(encode_model(CompactState(restored.target_sha256, restored.stages, ()))
                    == encode_model(CompactState(source.target_sha256, source.stages, ())),
                    'compressed state changed complete model codes')
                descriptors = []
                for leaf, exact in zip(restored.anchors, source.anchors):
                    require(leaf.record_id == exact.record_id and leaf.tokens == exact.tokens,
                            'compressed source membership differs')
                    for descriptor, block in zip(leaf.descriptors, exact.blocks):
                        check_cap()
                        require(descriptor.source_sha256 == sha(block.binary64), 'source factor hash differs')
                        require(descriptor.codec_sha256 == codec_binding(), 'codec source binding differs')
                        require(descriptor.box().contains(block.array()), 'compressed factor excludes its source')
                        encoded = encode_descriptor(descriptor)
                        descriptors.append(dict(record_id=leaf.record_id, stage_id=descriptor.stage_id,
                            descriptor_bytes=len(encoded), descriptor_sha256=sha(encoded),
                            source_sha256=descriptor.source_sha256, values=descriptor.shape[0]*descriptor.shape[1]))
                        descriptor_count += 1
                header_length = int.from_bytes(raw[8:16], 'little')
                header = json.loads(raw[16:16+header_length])
                descriptor_bytes = sum(item['descriptor_bytes'] for item in descriptors)
                require(len(raw) == 16+header_length+provenance[name]['model_bytes']+descriptor_bytes,
                        'complete state byte accounting differs')
                artifact_name = 'original40.bin' if name == 'prepare-001' else 'retained40.bin'
                artifact_path = output_dir/artifact_name
                with artifact_path.open('xb') as stream:
                    stream.write(raw)
                saved = artifact_path.read_bytes()
                require(saved == raw, 'written compressed state artifact differs')
                report['generations'][name]['precisions'][str(bits)] = dict(
                    complete_state_bytes=len(raw), complete_state_sha256=sha(raw),
                    artifact=relative(artifact_path), artifact_reloaded_equal=True,
                    exact_state_bytes=provenance[name]['exact_state_bytes'],
                    complete_state_reduction_bytes=provenance[name]['exact_state_bytes']-len(raw),
                    complete_state_reduction_fraction=1-len(raw)/provenance[name]['exact_state_bytes'],
                    framing_bytes=16, header_bytes=header_length,
                    complete_model_bytes=provenance[name]['model_bytes'], descriptor_bytes=descriptor_bytes,
                    source_count=len(state.anchors), descriptors=descriptors,
                    canonical_roundtrip=True, complete_model_bytes_equal=True, all_source_containment_checks_passed=True,
                    conversion_and_checks_cpu_ns=time.process_time_ns()-start_cpu,
                    conversion_and_checks_wall_ns=time.perf_counter_ns()-start_wall)
                converted[name] = (state, raw)
            original_compressed = converted['prepare-001'][0]
            retained_compressed, retained_raw = converted['repair-001']
            filtered = replace(original_compressed, stages=retained.stages,
                anchors=tuple(a for a in original_compressed.anchors if a.record_id in retained_ids))
            require(serialize(filtered) == retained_raw,
                    'filtered original descriptors and retained model differ from fresh retained encoding')
            original_lookup = {a.record_id: a for a in original_compressed.anchors}
            matches = 0
            for leaf in retained_compressed.anchors:
                for before, after in zip(original_lookup[leaf.record_id].descriptors, leaf.descriptors):
                    require(encode_descriptor(before) == encode_descriptor(after),
                            'retained descriptor changed after deletion')
                    matches += 1
            surviving_matches += matches
            report['comparisons'][str(bits)] = dict(surviving_descriptor_byte_matches=matches,
                filtered_original_with_retained_model_matches_fresh_retained_bytes=True,
                compared_complete_state_sha256=sha(retained_raw))
        require(source_hashes() == plan['source_hashes'], 'audit sources changed during execution')
        report.update(status='complete', artifacts_saved=True, descriptor_count=descriptor_count,
            surviving_descriptor_matches=surviving_matches, all_state_roundtrips_canonical=True,
            all_complete_models_preserved=True, all_retained_descriptors_unchanged=True)
    except Exception as exc:
        report.update(status='incomplete', error_type=type(exc).__name__, error=str(exc))
    finally:
        signal.setitimer(signal.ITIMER_PROF, 0)
        signal.signal(signal.SIGPROF, previous_handler)
    report['analysis_cpu_ns'] = time.process_time_ns()-started_cpu
    report['process_cpu_ns_since_script_imports'] = time.process_time_ns()-_CPU_START
    report['process_wall_ns_since_script_imports'] = time.perf_counter_ns()-_WALL_START
    report['cost_scope'] = 'through artifact writes and checks; excludes final report serialization and filesystem write'
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign', type=Path, default=ROOT/'campaigns/fixed_feature_v23')
    parser.add_argument('--output-dir', type=Path, default=ROOT/'campaigns/compressed_state_audit_v26')
    parser.add_argument('--cpu-cap-seconds', type=int, default=60)
    args = parser.parse_args()
    require(1 <= args.cpu_cap_seconds <= 60, 'CPU cap must be between one and sixty seconds')
    hashes = source_hashes()
    require(all(hashes[name] == digest for name, digest in REVIEWED_SOURCES.items()),
            'state or codec differs from independently reviewed source')
    args.output_dir.mkdir(parents=True, exist_ok=False)
    plan = dict(schema='compressed-state-archive-audit-plan-v26',
        campaign=relative(args.campaign), output_dir=relative(args.output_dir),
        attempts=['prepare-001', 'repair-001'], bits=[40], block_size=256,
        cpu_cap_seconds=args.cpu_cap_seconds, source_hashes=hashes,
        reviewed_source_hashes=REVIEWED_SOURCES,
        artifacts=['original40.bin', 'retained40.bin'],
        command='python scripts/analyze_compressed_state_v26.py --output-dir <fresh-directory>',
        outputs_fresh_only=True, model_execution=False, quantization_execution=False)
    write_new(args.output_dir/'plan.json', plan)
    report = audit(args.campaign, plan, args.output_dir)
    report['plan_sha256'] = sha((args.output_dir/'plan.json').read_bytes())
    write_new(args.output_dir/'summary.json', report)
    print(json.dumps({key: report.get(key) for key in (
        'status', 'descriptor_count', 'surviving_descriptor_matches', 'analysis_cpu_ns', 'error')}))
    if report['status'] != 'complete':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
