#!/usr/bin/env python3
"""Verify and convert an archived fixed-feature state without model execution."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.compact_service import model_digest
from src.compact_state import parse as parse_model
from src.fixed_anchor_service import FixedAnchorState, parse, serialize
from src.fixed_factor_state import FixedFactorState, from_anchor, preparer_binding

DEFAULT_SOURCE_SHA256 = '1e2937e09e9a20f8a3536b6a27620842d13c448928205d9c915959f4f01da142'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    raw = path.read_bytes()
    return json.loads(raw), sha(raw)


def relative(path):
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def analyze(attempt, expected_state_sha256, save_state=None):
    attempt = attempt.resolve()
    plan, plan_sha = read_json(attempt/'plan.json')
    receipt, receipt_sha = read_json(attempt/'worker/result.json')
    progress, progress_sha = read_json(attempt/'outputs/progress.json')
    require(receipt['status'] == 'complete' and receipt['outcome']['status'] == 'complete'
            and receipt['outcome']['returncode'] == 0, 'source worker did not complete')
    require(receipt['worker_identity']['plan_sha256'] == plan_sha
            and progress['plan_sha256'] == plan_sha, 'source plan bindings differ')
    require(sha((attempt/'program.json').read_bytes()) == plan['program_sha256'], 'program hash differs')
    require(sha((attempt/'protocol.json').read_bytes()) == plan['protocol_sha256'], 'protocol hash differs')
    require(sha((attempt/'worker/identity.json').read_bytes()) == receipt['identity_sha256'], 'worker identity differs')
    worker_attempt = receipt['attempt']
    require(Path(worker_attempt).name == worker_attempt, 'invalid worker attempt name')
    for name, metadata in receipt['artifacts'].items():
        require(Path(name).name == name, 'invalid receipt artifact name')
        value = (attempt/'worker'/worker_attempt/name).read_bytes()
        require(len(value) == metadata['bytes'] and sha(value) == metadata['sha256'], 'receipt artifact differs')
    for name, digest in plan['source_sha256'].items():
        path = Path(name)
        require(not path.is_absolute() and '..' not in path.parts, 'invalid archived source path')
        require(sha((attempt/'source'/path).read_bytes()) == digest, 'archived source hash differs: '+name)
    require(progress['complete_new_target_model'] and progress['complete_new_target_state'], 'source output is incomplete')
    state_info, model_info = progress['state_artifact'], progress['model_artifact']
    require(state_info['file'] == 'state.bin' and model_info['file'] == 'model.bin', 'unexpected output artifact name')
    source = attempt/'outputs/state.bin'
    data = source.read_bytes()
    require(len(data) == state_info['bytes'] and sha(data) == state_info['sha256']
            and sha(data) == expected_state_sha256, 'source state differs from trusted expected hash')
    model_data = (attempt/'outputs/model.bin').read_bytes()
    require(len(model_data) == model_info['bytes'] and sha(model_data) == model_info['sha256'], 'model artifact differs')
    old, model = parse(data), parse_model(model_data)
    require(type(old) is FixedAnchorState, 'source must use the legacy complete-anchor representation')
    require(old.target_sha256 == progress['fixed_target_sha256'] == model.target_sha256, 'model target differs')
    require(old.anchor_target_sha256 == progress['base_target_sha256'], 'anchor target differs')
    require(old.stages == model.stages and not model.factors, 'source model codes differ')
    tick = time.perf_counter_ns()
    leaves = tuple(from_anchor(a) for a in old.anchors)
    new = FixedFactorState(old.target_sha256, old.anchor_target_sha256, old.decoder_sha256,
        old.provider_sha256, old.anchor_sha256, preparer_binding(), old.stages, leaves)
    minimal = serialize(new)
    conversion_ns = time.perf_counter_ns()-tick
    comparisons = []
    for source_leaf, destination in zip(old.anchors, leaves):
        require(source_leaf.record_id == destination.record_id and source_leaf.tokens == destination.tokens,
                'converted record identity differs')
        require(len(source_leaf.factors) == len(destination.blocks), 'converted factor count differs')
        for (sid, _, values), block in zip(source_leaf.factors, destination.blocks):
            require(sid == block.stage_id and values.shape == (block.token_count, block.width),
                    'converted factor metadata differs')
            comparisons.append(values.astype('<f8', copy=False).tobytes() == block.binary64)
    require(all(comparisons), 'converted factor bytes differ')
    require(new.stages == old.stages, 'converted code bytes or metadata differ')
    require(serialize(parse(minimal)) == minimal, 'minimal state does not roundtrip canonically')
    digest = model_digest(old.stages)
    require(digest == progress['model_sha256'], 'decoded model digest differs from worker output')
    artifact = None
    if save_state is not None:
        save_state.parent.mkdir(parents=True, exist_ok=True)
        save_state.write_bytes(minimal)
        artifact = relative(save_state)
    return dict(schema='fixed-factor-storage-audit-v22',
        scope='archive conversion and serialization only; no model execution or repair timing',
        source=relative(source), source_sha256=sha(data), expected_source_sha256=expected_state_sha256,
        source_plan_sha256=plan_sha, source_receipt_sha256=receipt_sha,
        source_progress_sha256=progress_sha, archived_source_files_verified=len(plan['source_sha256']),
        receipt_artifacts_verified=True, plan_and_output_bindings_verified=True,
        target_sha256=old.target_sha256, anchor_target_sha256=old.anchor_target_sha256,
        old_state_bytes=len(data), minimal_state_bytes=len(minimal), saved_bytes=len(data)-len(minimal),
        state_size_ratio=len(minimal)/len(data), factor_payload_bytes=sum(len(b.binary64) for a in leaves for b in a.blocks),
        factor_count=len(comparisons), all_factor_bytes_equal=all(comparisons), all_code_bytes_equal=True,
        source_model_digest=digest, minimal_model_digest=digest, minimal_state_sha256=sha(minimal),
        minimal_state_artifact=artifact, canonical_roundtrip=True, preparer_sha256=preparer_binding(),
        source_hashes={name:sha((ROOT/name).read_bytes()) for name in (
            'src/fixed_factor_state.py', 'src/fixed_anchor_service.py', 'src/sequential_finite.py',
            'scripts/analyze_fixed_factor_v22.py')}, conversion_and_serialization_elapsed_ns=conversion_ns,
        timing_use='descriptive controller work; no empirical speed claim')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt', type=Path, default=ROOT/'pilots/v21/attempt-001')
    parser.add_argument('--expected-state-sha256', default=DEFAULT_SOURCE_SHA256)
    parser.add_argument('--output', type=Path, default=ROOT/'pilots/v22/factor-storage-audit.json')
    parser.add_argument('--save-state', type=Path)
    args = parser.parse_args()
    report = analyze(args.attempt, args.expected_state_sha256, args.save_state)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
    print(json.dumps({key:report[key] for key in ('old_state_bytes', 'minimal_state_bytes',
        'all_factor_bytes_equal', 'all_code_bytes_equal', 'plan_and_output_bindings_verified')}))


if __name__ == '__main__':
    main()
