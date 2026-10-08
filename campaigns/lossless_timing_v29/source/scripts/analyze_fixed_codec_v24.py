"""Bounded archive-only compression audit. No model loading or evaluation."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import zlib
from fractions import Fraction as Q

_WALL_START = time.perf_counter_ns()
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from src.compact_state import token_digest, serialize as serialize_model, CompactState
from src.fixed_anchor_service import parse as parse_state
from src.fixed_factor_state import FixedFactorState, preparer_binding
from src.fixed_factor_codec import encode_factor, serialize, parse, codec_binding, _GUARD_BITS

EXPECTED_STATES = {
    'prepare-001':'508c36848902bddc407ff84c660b48b5704451729ae5151ad18b4f5ff1b113dc',
    'repair-001':'01fa90da490a29a1199c3c7ce22727248d79fd8584af28c1ac1ff4acb33ac640',
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')


def sha(value):
    return hashlib.sha256(value).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_json(path):
    raw = path.read_bytes()
    return json.loads(raw), sha(raw)


def relative(path):
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def load_generation(attempt):
    campaign = attempt.parent.parent
    plan, plan_hash = load_json(attempt/'plan.json')
    progress, progress_hash = load_json(attempt/'outputs/progress.json')
    receipt, receipt_hash = load_json(attempt/'worker/result.json')
    require(receipt['status'] == receipt['outcome']['status'] == progress['status'] == 'complete'
        and receipt['outcome']['returncode'] == 0 and receipt['budget_debit']['state'] == 'settled',
        'incomplete source generation')
    require(receipt['worker_identity']['plan_sha256'] == progress['plan_sha256'] == plan_hash,
            'source generation plan binding differs')
    require(sha((campaign/'program.json').read_bytes()) == plan['program_sha256'], 'source program binding differs')
    require(sha((campaign/'protocol.json').read_bytes()) == plan['protocol_sha256'], 'source protocol binding differs')
    for name, digest in plan['source_sha256'].items():
        source = Path(name)
        require(not source.is_absolute() and '..' not in source.parts, 'unsafe frozen source path')
        require(sha((campaign/'source'/source).read_bytes()) == digest, 'frozen source binding differs: '+name)
    artifact = progress['state_artifact']
    state_bytes = (attempt/'outputs/state.bin').read_bytes()
    require(artifact['file'] == 'state.bin' and len(state_bytes) == artifact['bytes']
        and sha(state_bytes) == artifact['sha256'] == EXPECTED_STATES[attempt.name], 'source state artifact differs')
    state = parse_state(state_bytes, expected_sha256=artifact['sha256'])
    require(type(state) is FixedFactorState and progress['complete_state'] and progress['complete_model'],
            'source is not a complete minimal factor state')
    require(state.target_sha256 == progress['fixed_target_sha256']
        and state.anchor_target_sha256 == progress['base_target_sha256'], 'source target binding differs')
    expected_preparer = sha(canonical({name:plan['source_sha256']['src/'+name]
        for name in ('fixed_factor_state.py', 'sequential_finite.py')}))
    require(state.preparer_sha256 == expected_preparer == preparer_binding(), 'preparer provenance or current binding differs')
    model_bytes = (attempt/'outputs/model.bin').read_bytes()
    require(len(model_bytes) == progress['model_artifact']['bytes']
        and sha(model_bytes) == progress['model_artifact']['sha256'], 'source model artifact differs')
    require(serialize_model(CompactState(state.target_sha256, state.stages, ())) == model_bytes,
            'state codes differ from complete model artifact')
    require(list(state.record_ids) == plan['record_ids'] == progress['retained_record_ids'], 'source membership differs')
    return state, dict(attempt=relative(attempt), plan_sha256=plan_hash, progress_sha256=progress_hash,
        receipt_sha256=receipt_hash, state_sha256=sha(state_bytes), exact_state_bytes=len(state_bytes),
        model_sha256=sha(model_bytes), model_bytes=len(model_bytes), frozen_source_files_verified=len(plan['source_sha256']))


def projection(state, provenance, records, label, codec_sha):
    """A declared accounting envelope, not an implemented service serialization."""
    index = dict(schema='projected-compressed-state-accounting-v24', representation=label,
        target_sha256=state.target_sha256, anchor_target_sha256=state.anchor_target_sha256,
        decoder_sha256=state.decoder_sha256, provider_sha256=state.provider_sha256,
        anchor_sha256=state.anchor_sha256, preparer_sha256=state.preparer_sha256, codec_sha256=codec_sha,
        model=dict(bytes=provenance['model_bytes'], sha256=provenance['model_sha256']), records=records)
    raw = canonical(index)
    descriptors = sum(item['bytes'] for record in records for item in record['descriptors'])
    total = 16+len(raw)+provenance['model_bytes']+descriptors
    return dict(projected_only=True, service_format_implemented=False,
        framing_bytes=16, index_bytes=len(raw), index_sha256=sha(raw),
        framing_assumption='eight magic bytes plus eight header-length bytes',
        index_contents='target and provenance bindings; model binding; record IDs and tokens; per-stage descriptor lengths and hashes',
        descriptor_bytes=descriptors, complete_model_bytes=provenance['model_bytes'], projected_complete_state_bytes=total,
        ratio_to_exact_state=total/provenance['exact_state_bytes'],
        exact_state_bytes=provenance['exact_state_bytes'])


def audit(campaign, cpu_cap_seconds):
    started_cpu = time.process_time_ns()
    codec_sha = codec_binding()
    report = dict(schema='saved-factor-codec-audit-v24', status='running',
        scope='archive factor compression only; no model loading, model evaluation, or repair transaction',
        codec_sha256=codec_sha, bits=[16,24], block_size=256, cells=[], generations={},
        analysis_cpu_cap_seconds=cpu_cap_seconds, empirical_worker_budget_charged=False,
        cost_account='controller analysis process; separate from every empirical worker ledger',
        binding_scope='trusted source state hashes and verified generation plans; parsed descriptor alone does not prove containment',
        containment_check='all finite binary64 entries use exact order comparisons; three positions per block also use exact rational comparisons',
        projection_scope='descriptor files and model file are real; complete compressed service envelope is projected accounting only',
        lossless_comparator='zlib level6 compresses the same exact source-stage bytes and retains more information than lossy enclosures',
        zlib_version=zlib.ZLIB_VERSION, speed_inference=False)
    originals = {}
    retained_matches = 0

    def check_cap():
        if time.process_time_ns()-started_cpu > cpu_cap_seconds*10**9:
            raise TimeoutError('analysis CPU soft cap exceeded between factors')

    try:
        for name in ('prepare-001', 'repair-001'):
            check_cap()
            state, provenance = load_generation(campaign/'attempts'/name)
            precision_records = {16:[],24:[], 'zlib6':[]}
            raw_total = payload_totals = 0
            generation_cells = []
            for leaf in state.anchors:
                entries = {16:[],24:[], 'zlib6':[]}
                for block in leaf.blocks:
                    check_cap()
                    values = block.array()
                    raw_total += len(block.binary64)
                    descriptors, boxes = {}, {}
                    for bits in (16,24):
                        descriptor = encode_factor(values, target_sha256=state.target_sha256,
                            anchor_target_sha256=state.anchor_target_sha256, record_id=leaf.record_id,
                            token_sha256=token_digest(leaf.tokens), stage_id=block.stage_id, bits=bits, block_size=256)
                        encoded = serialize(descriptor)
                        decoded = parse(encoded, expected_sha256=sha(encoded))
                        require(decoded == descriptor and serialize(decoded) == encoded, 'descriptor roundtrip differs')
                        require(decoded.codec_sha256 == codec_sha == codec_binding()
                            and decoded.source_sha256 == sha(block.binary64), 'descriptor source or current codec binding differs')
                        require((decoded.target_sha256, decoded.anchor_target_sha256, decoded.record_id,
                            decoded.token_sha256, decoded.stage_id, decoded.shape) ==
                            (state.target_sha256, state.anchor_target_sha256, leaf.record_id,
                            token_digest(leaf.tokens), block.stage_id, values.shape), 'descriptor context binding differs')
                        box = decoded.box()
                        require(box.contains(values), 'compressed endpoints exclude source factors')
                        rational_checks = 0
                        for start in range(0, values.size, 256):
                            for index in sorted({start, min(start+127, values.size-1), min(start+255, values.size-1)}):
                                lo, value, hi = (Q.from_float(float(x.flat[index])) for x in (box.lower, values, box.upper))
                                require(lo <= value <= hi, 'exact rational containment failed')
                                rational_checks += 1
                        key = (leaf.record_id, block.stage_id, bits)
                        if name == 'prepare-001':
                            originals[key] = encoded
                        else:
                            require(originals[key] == encoded, 'surviving source descriptor changed after deletion')
                            retained_matches += 1
                        words = np.frombuffer(block.binary64, dtype='<u8')
                        escaped = int(np.count_nonzero((words & np.uint64((1 << 63)-1)) > np.uint64(_GUARD_BITS)))
                        cell = dict(attempt=name, record_id=leaf.record_id, stage_id=block.stage_id,
                            bits=bits, values=values.size, raw_factor_bytes=len(block.binary64),
                            payload_bytes=len(descriptor.payload), descriptor_bytes=len(encoded),
                            descriptor_sha256=sha(encoded), source_sha256=sha(block.binary64), escapes=escaped,
                            all_float_endpoint_checks_passed=True, rational_checks=rational_checks,
                            canonical_roundtrip=True, current_codec_binding_verified=True)
                        report['cells'].append(cell)
                        generation_cells.append(cell)
                        descriptors[bits], boxes[bits] = descriptor, box
                        entries[bits].append(dict(stage_id=block.stage_id, bytes=len(encoded), sha256=sha(encoded)))
                    require(np.all(boxes[24].lower >= boxes[16].lower)
                        and np.all(boxes[24].upper <= boxes[16].upper), 'precision refinement is not nested')
                    compressed = zlib.compress(block.binary64, level=6)
                    require(zlib.decompress(compressed) == block.binary64, 'lossless comparator changed source bytes')
                    lossless_header = canonical(dict(schema='bound-zlib-factor-accounting-v24',
                        target_sha256=state.target_sha256, anchor_target_sha256=state.anchor_target_sha256,
                        record_id=leaf.record_id, token_sha256=token_digest(leaf.tokens), stage_id=block.stage_id,
                        shape=list(values.shape), source_sha256=sha(block.binary64), codec='zlib', level=6,
                        zlib_version=zlib.ZLIB_VERSION, payload_bytes=len(compressed), payload_sha256=sha(compressed)))
                    lossless = b'VCZL\x01\0\0\0'+len(lossless_header).to_bytes(8,'little')+lossless_header+compressed
                    entries['zlib6'].append(dict(stage_id=block.stage_id, bytes=len(lossless), sha256=sha(lossless)))
                    for cell in generation_cells[-2:]:
                        cell.update(zlib_payload_bytes=len(compressed), zlib_bound_descriptor_bytes=len(lossless),
                                    lossless_roundtrip=True, nested_16_to_24=True)
                for bits in precision_records:
                    precision_records[bits].append(dict(record_id=leaf.record_id, tokens=list(leaf.tokens),
                        token_sha256=token_digest(leaf.tokens), descriptors=entries[bits]))
            projections = {str(bits):projection(state, provenance, records, str(bits), codec_sha)
                           for bits, records in precision_records.items()}
            report['generations'][name] = dict(**provenance, records=len(state.anchors), stages=len(state.stages),
                source_stage_factors=sum(len(a.blocks) for a in state.anchors), raw_factor_bytes=raw_total,
                precision={str(bits):dict(payload_bytes=sum(c['payload_bytes'] for c in generation_cells if c['bits']==bits),
                    descriptor_bytes=sum(c['descriptor_bytes'] for c in generation_cells if c['bits']==bits),
                    descriptor_to_raw_ratio=sum(c['descriptor_bytes'] for c in generation_cells if c['bits']==bits)/raw_total)
                    for bits in (16,24)}, projected_states=projections)
        report.update(status='complete', source_stage_factor_count=72, descriptor_count=len(report['cells']),
            surviving_descriptor_matches=retained_matches, all_containment_checks_passed=True,
            all_refinements_nested=True, all_roundtrips_canonical=True,
            unchanged_retained_descriptors_verified=retained_matches == 48)
    except Exception as exc:
        report.update(status='incomplete', error_type=type(exc).__name__, error=str(exc))
    report['analysis_cpu_ns'] = time.process_time_ns()-started_cpu
    report['process_cpu_ns_including_imports'] = time.process_time_ns()
    report['analysis_wall_ns_from_script_imports'] = time.perf_counter_ns()-_WALL_START
    report['analysis_source_hashes'] = {name:sha((ROOT/name).read_bytes()) for name in (
        'src/fixed_factor_codec.py', 'src/fixed_factor_state.py', 'scripts/analyze_fixed_codec_v24.py')}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign', type=Path, default=ROOT/'campaigns/fixed_feature_v23')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--cpu-cap-seconds', type=int, default=30)
    args = parser.parse_args()
    require(1 <= args.cpu_cap_seconds <= 60, 'analysis CPU cap must be between one and sixty seconds')
    report = audit(args.campaign, args.cpu_cap_seconds)
    output = args.output or args.campaign/'codec-audit-v24.json'
    output.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
    print(json.dumps({key:report.get(key) for key in ('status', 'descriptor_count',
        'surviving_descriptor_matches', 'analysis_cpu_ns', 'error')}))
    if report['status'] != 'complete':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
