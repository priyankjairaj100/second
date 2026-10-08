"""Save complete lossless states from validated archives. No model execution."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import signal
import sys
import time

START_WALL = time.perf_counter_ns()
START_CPU = time.process_time_ns()
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.analyze_fixed_codec_v24 import load_generation
from src.compact_state import CompactState, serialize as encode_model
from src.fixed_factor_state import serialize as encode_exact
from src.fixed_lossless_codec_v29 import codec_manifest, codec_binding, serialize as encode_descriptor
from src.fixed_lossless_state_v29 import from_factor_state, to_factor_state, serialize, parse

SOURCES = ('scripts/analyze_lossless_state_v29.py', 'scripts/analyze_fixed_codec_v24.py',
    'src/fixed_lossless_codec_v29.py', 'src/fixed_lossless_state_v29.py', 'src/fixed_factor_state.py',
    'src/fixed_anchor_service.py', 'src/compact_state.py', 'src/anchor_state.py',
    'src/sequential_finite.py', 'src/run_store.py')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def hashes():
    return {name:sha((ROOT/name).read_bytes()) for name in SOURCES}


def relative(path):
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def write_new(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def audit(plan, output):
    start_cpu = time.process_time_ns()
    report = dict(schema='lossless-state-archive-audit-v29', status='running', source_hashes=plan['source_hashes'],
        scope='archive conversion and state validation only; no neural inference, quantization, or service timing',
        empirical_worker_budget_charged=False,
        cost_account='archive analysis process outside empirical worker ledger', cpu_soft_cap_seconds=60,
        codec_manifest=plan['codec_manifest'], codec_sha256=plan['codec_sha256'], generations={},
        artifacts_saved=False, state_sizes_projected=False, speed_claim=False, quality_claim=False,
        trust_premise='validated exact source archives establish preparation; content hashes do not establish source execution')

    def timeout(*_):
        raise TimeoutError('lossless archive audit exceeded its CPU soft limit')

    previous = signal.signal(signal.SIGPROF, timeout)
    signal.setitimer(signal.ITIMER_PROF, 60)
    try:
        original = retained = retained_raw = None
        descriptor_count = 0
        for name, filename in (('prepare-001', 'original.bin'), ('repair-001', 'retained.bin')):
            before_cpu, before_wall = time.process_time_ns(), time.perf_counter_ns()
            exact, provenance = load_generation(ROOT/'campaigns/fixed_feature_v23/attempts'/name)
            state = from_factor_state(exact)
            raw = serialize(state)
            restored = parse(raw, expected_sha256=sha(raw))
            require(serialize(restored) == raw, 'lossless state canonical roundtrip differs')
            require(encode_model(CompactState(state.target_sha256, state.stages, ()))
                == encode_model(CompactState(exact.target_sha256, exact.stages, ())), 'complete model codes differ')
            decoded_exact = to_factor_state(restored)
            exact_bytes = encode_exact(decoded_exact)
            require(len(exact_bytes) == provenance['exact_state_bytes']
                and sha(exact_bytes) == provenance['state_sha256'], 'complete exact factor state was not reconstructed')
            descriptors = []
            for leaf, exact_leaf in zip(restored.anchors, exact.anchors):
                require(leaf.record_id == exact_leaf.record_id and leaf.tokens == exact_leaf.tokens,
                        'source membership changed')
                for descriptor, block in zip(leaf.descriptors, exact_leaf.blocks):
                    require(descriptor.binary64() == block.binary64, 'source factor bytes changed')
                    encoded = encode_descriptor(descriptor)
                    descriptors.append(dict(record_id=leaf.record_id, stage_id=descriptor.stage_id,
                        descriptor_bytes=len(encoded), descriptor_sha256=sha(encoded), mode=descriptor.mode,
                        payload_bytes=len(descriptor.payload), source_sha256=descriptor.source_sha256,
                        source_bytes=len(block.binary64), exact_source_bytes_equal=True))
                    descriptor_count += 1
            header_bytes = int.from_bytes(raw[8:16], 'little')
            descriptor_bytes = sum(row['descriptor_bytes'] for row in descriptors)
            require(len(raw) == 16+header_bytes+provenance['model_bytes']+descriptor_bytes,
                    'complete state byte accounting differs')
            artifact = output/filename
            with artifact.open('xb') as stream:
                stream.write(raw)
            require(artifact.read_bytes() == raw, 'saved lossless artifact differs')
            report['generations'][name] = dict(**provenance, complete_state_bytes=len(raw),
                complete_state_sha256=sha(raw), artifact=relative(artifact), source_count=len(state.anchors),
                roundtrip_exact=True, canonical=True, artifact_reloaded_equal=True,
                complete_model_bytes_equal=True, complete_exact_state_sha256=sha(exact_bytes),
                reduction_bytes=provenance['exact_state_bytes']-len(raw),
                reduction_fraction=1-len(raw)/provenance['exact_state_bytes'],
                framing_bytes=16, header_bytes=header_bytes, descriptor_bytes=descriptor_bytes,
                descriptors=descriptors, conversion_and_checks_cpu_ns=time.process_time_ns()-before_cpu,
                conversion_and_checks_wall_ns=time.perf_counter_ns()-before_wall)
            if name == 'prepare-001':
                original = state
            else:
                retained, retained_raw = state, raw
        require(set(retained.record_ids) < set(original.record_ids), 'archives do not describe strict source deletion')
        filtered = replace(original, stages=retained.stages,
            anchors=tuple(a for a in original.anchors if a.record_id in retained.record_ids))
        require(serialize(filtered) == retained_raw, 'source filtering differs from independent retained encoding')
        matches = 0
        by_id = {leaf.record_id:leaf for leaf in original.anchors}
        for leaf in retained.anchors:
            for before, after in zip(by_id[leaf.record_id].descriptors, leaf.descriptors):
                require(encode_descriptor(before) == encode_descriptor(after), 'retained descriptor bytes changed')
                matches += 1
        require(hashes() == plan['source_hashes'] and codec_manifest() == plan['codec_manifest']
                and codec_binding() == plan['codec_sha256'], 'audit source or compressor changed')
        report.update(status='complete', artifacts_saved=True, all_complete_models_preserved=True,
            all_retained_descriptors_unchanged=True, all_state_roundtrips_canonical=True,
            all_complete_exact_factor_states_preserved=True, descriptor_count=descriptor_count,
            surviving_descriptor_matches=matches, filtered_original_with_retained_model_matches=True)
    except Exception as exc:
        report.update(status='incomplete', error_type=type(exc).__name__, error=str(exc))
    finally:
        signal.setitimer(signal.ITIMER_PROF, 0)
        signal.signal(signal.SIGPROF, previous)
    report['analysis_cpu_ns'] = time.process_time_ns()-start_cpu
    report['process_cpu_ns_since_script_imports'] = time.process_time_ns()-START_CPU
    report['process_wall_ns_since_script_imports'] = time.perf_counter_ns()-START_WALL
    report['cost_scope'] = 'through artifact writes and checks; excludes final report serialization and write'
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT/'campaigns/lossless_state_audit_v29')
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    plan = dict(schema='lossless-state-archive-audit-plan-v29', source_hashes=hashes(),
        attempts=['prepare-001', 'repair-001'], artifacts=['original.bin', 'retained.bin'],
        codec_manifest=codec_manifest(), codec_sha256=codec_binding(), cpu_soft_cap_seconds=60,
        model_execution=False, quantization_execution=False, service_timing=False, outputs_fresh_only=True,
        command='python scripts/analyze_lossless_state_v29.py --output-dir <fresh-directory>')
    write_new(args.output_dir/'plan.json', plan)
    report = audit(plan, args.output_dir)
    report['plan_sha256'] = sha((args.output_dir/'plan.json').read_bytes())
    write_new(args.output_dir/'summary.json', report)
    print(json.dumps({key:report.get(key) for key in ('status', 'descriptor_count',
        'surviving_descriptor_matches', 'analysis_cpu_ns', 'error')}))
    if report['status'] != 'complete':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
