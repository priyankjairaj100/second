#!/usr/bin/env python3
"""Verify and summarize one completed V32 independent request root.

All seven registered trials and their binary artifacts must be available.
This script performs archive analysis only. It never launches a worker.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import launch_independent_requests_v32 as controller
from scripts.analyze_full_service_v30 import verify_final_budget
from scripts.analyze_compressed_service_v31 import verify_diagnostics, verify_native_evidence
from src.pilot_budget import research_worker_lock
from src.run_store import digest


def require(condition, message):
    if not condition:
        raise ValueError(message)


def equal_file_bytes(left, right):
    """Compare complete model bytes after the controller checked both identities."""
    with Path(left).open('rb') as a, Path(right).open('rb') as b:
        while True:
            x, y = a.read(1024 * 1024), b.read(1024 * 1024)
            if x != y:
                return False
            if not x:
                return True


def verified_seconds(transaction):
    ns = transaction['controller_elapsed_ns']
    require(type(ns) is int and ns > 0, 'Controller duration must be a positive integer')
    return ns / 1e9


def changed_four_bit_codes(left, right, count):
    """Count unequal packed four-bit integer decisions, including an odd tail."""
    import numpy as np
    require(type(count) is int and count >= 0 and len(left) == len(right) == (count + 1) // 2,
            'Packed code lengths differ')
    if count % 2:
        require((left[-1] | right[-1]) >> 4 == 0, 'Noncanonical packed padding')
    changed = np.bitwise_xor(np.frombuffer(left, dtype=np.uint8), np.frombuffer(right, dtype=np.uint8))
    return int(np.count_nonzero(changed & 15) + np.count_nonzero(changed >> 4))


def changed_model_codes(original, retained):
    require(original.target_sha256 == retained.target_sha256 and not original.factors and not retained.factors,
            'Deletion code comparison target or artifact kind differs')
    require(len(original.stages) == len(retained.stages), 'Deletion code comparison omits stages')
    rows = []
    for left, right in zip(original.stages, retained.stages):
        fields = ('stage_id', 'rows', 'columns', 'grid_axis', 'bits', 'scale_exponents', 'scale_values')
        require(all(getattr(left, field) == getattr(right, field) for field in fields) and left.bits == 4,
                'Deletion code comparison grids or shapes differ')
        total = left.rows * left.columns
        rows.append({'stage_id': left.stage_id, 'code_count': total,
                     'changed_code_count': changed_four_bit_codes(left.packed_indices, right.packed_indices, total)})
    return {'changed_code_count': sum(row['changed_code_count'] for row in rows),
            'total_code_count': sum(row['code_count'] for row in rows), 'stages': rows,
            'scope': 'Exact integer code differences from original calibration; no behavioral or privacy-erasure claim.'}


def verify_native_receipts(result, plan, program, source):
    """Extend the published V31 audit with complete sparse budget bindings."""
    evidence = verify_native_evidence(result, plan, program, source)
    for stage in result['diagnostics']['stages']:
        if stage['route'] != 'box_certificate':
            continue
        details = stage['solver_diagnostics']
        pairs = details.get('resource_budget')
        require(type(pairs) is list and all(type(row) is list and len(row) == 2 for row in pairs),
                'Accepted sparse certificate lacks its complete resource budget')
        actual = dict(pairs)
        require(len(actual) == len(pairs), 'Sparse resource budget repeats a field')
        expected = dict(plan['sparse_budget'],
                        max_work_units=stage['certificate_admission']['routes']['sparse']['work_units_reserved'],
                        max_workspace_bytes=min(plan['sparse_budget']['max_workspace_bytes'],
                                                plan['max_certificate_workspace_bytes']))
        require(actual == expected, 'Sparse internal resource budget differs from registered policy')
    return evidence


def verify_result_fields(result, trial):
    """Check the values used in this summary, in addition to receipt bindings."""
    plan = trial['plan']
    require(result['stage_count'] == 24 and result['model_code_elements'] == 42467328,
            'Complete model coverage differs')
    require(len(result['stage_ids']) == len(set(result['stage_ids'])) == 24,
            'Complete stage identities differ')
    require(result['model_roundtrip_exact'] is True, 'Model roundtrip verification failed')
    require(result['original_token_count'] == plan['original_token_count'] == 256,
            'Original normalization differs')
    require(result['retained_token_count'] == 128 * len(plan['record_ids']), 'Retained token count differs')
    stateful = plan['method'] != 'model_only_fresh'
    require(result['complete_state'] is stateful and
            set(result['artifacts']) == ({'model', 'state'} if stateful else {'model'}),
            'Complete output contract differs')
    if stateful:
        require(result['state_roundtrip_canonical'] is True, 'State roundtrip verification failed')
    for kind, artifact in result['artifacts'].items():
        require(artifact == result[kind + '_artifact'], 'Named artifact differs from output manifest')
        value = artifact['sha256']
        require(type(value) is str and len(value) == 64 and set(value) <= set('0123456789abcdef'),
                'Invalid full artifact hash')
        require(type(artifact['bytes']) is int and artifact['bytes'] > 0, 'Invalid artifact byte count')
    if trial['script'] == 'run_ordered_service_v30.py':
        diagnostics = result['diagnostics']
        neural = diagnostics['neural_stage_record_pairs']
        if plan['method'] == 'model_only_fresh':
            neural += diagnostics.get('anchor_preparation_stage_record_pairs', 0)
        expected = 0 if plan['method'] == 'repair' else 24 * len(plan['record_ids'])
        require(type(neural) is int and neural == expected, 'Ordered neural work differs from method')


def analyze(corpus):
    started = time.process_time_ns()
    current, program, raw, protocol, registration = controller.check_registered(corpus)
    require(len(program["trials"]) == 7, "Expected all seven registered trials")
    require(len(program["requests"]) == 2, "Expected both registered deletion directions")
    expected_ids = program["execution_order"]
    actual_ids = sorted(p.name for p in (current / "attempts").iterdir() if p.is_dir())
    require(actual_ids == sorted(expected_ids), "Missing or extra attempt directory")
    results, transactions, receipts = {}, {}, []
    for trial in program["trials"]:
        trial_id = trial["id"]
        results[trial_id] = controller.completed(current, trial_id)
        attempt = current / "attempts" / trial_id
        transactions[trial_id] = controller.read_json(attempt / "transaction.json")
        receipts.append(controller.read_json(attempt / "worker/result.json"))
        verify_result_fields(results[trial_id], trial)
        verified_seconds(transactions[trial_id])
    budget = verify_final_budget(current, program, digest(protocol), receipts)

    def seconds(trial_id):
        return verified_seconds(transactions[trial_id])

    def model_path(trial_id):
        return current / 'attempts' / trial_id / 'outputs' / results[trial_id]['artifacts']['model']['file']

    preparation_id = next(t['id'] for t in program['trials'] if t['plan']['method'] == 'direct_fresh')
    from src.compact_state import parse
    original_model = parse(model_path(preparation_id).read_bytes(),
                           expected_sha256=results[preparation_id]['artifacts']['model']['sha256'])
    pairs = []
    for request in program["requests"]:
        repair_id, cold_id = request["repair_trial"], request["cold_trial"]
        repair, cold = results[repair_id], results[cold_id]
        require(repair["artifacts"]["model"] == cold["artifacts"]["model"], "Pair model descriptors differ")
        require(equal_file_bytes(model_path(repair_id), model_path(cold_id)), 'Pair model bytes differ')
        require(repair["retained_record_ids"] == cold["retained_record_ids"] == request["retained_ids"],
                "Pair retained membership differs")
        require(repair["deleted_record_ids"] == cold["deleted_record_ids"] == request["deleted_ids"],
                "Pair deleted membership differs")
        require(repair["state_roundtrip_canonical"] is True, "Retained state roundtrip failed")
        retained_model = parse(model_path(repair_id).read_bytes(), expected_sha256=repair['artifacts']['model']['sha256'])
        code_changes = changed_model_codes(original_model, retained_model)
        require(code_changes['total_code_count'] == 42467328, 'Deletion code comparison is incomplete')
        del retained_model
        repair_time, cold_time = seconds(repair_id), seconds(cold_id)
        pairs.append({
            "request": request["id"], "method_order": request["method_order"],
            "retained_ids": request["retained_ids"], "deleted_ids": request["deleted_ids"],
            "repair_seconds": repair_time, "cold_seconds": cold_time,
            "repair_controller_ns": transactions[repair_id]['controller_elapsed_ns'],
            "cold_controller_ns": transactions[cold_id]['controller_elapsed_ns'],
            "cold_over_repair": cold_time / repair_time,
            "repair_faster": repair_time < cold_time,
            "model": repair["artifacts"]["model"],
            "lossless_retained_state": repair["artifacts"]["state"],
            "repair_neural_stage_record_pairs": repair["diagnostics"]["neural_stage_record_pairs"],
            "cold_neural_stage_record_pairs": cold["diagnostics"]["neural_stage_record_pairs"],
            "exact_model_bytes_reverified": True,
            "deletion_code_changes": code_changes,
        })
    del original_model
    conversion_id = next(t["id"] for t in program["trials"] if t["plan"]["method"] == "convert_lossless")
    compressed_trial = next(t for t in program["trials"] if "latency_gate" in t)
    compressed_id = compressed_trial["id"]
    compressed = results[compressed_id]
    request = next(r for r in program["requests"] if r["id"] == program["compressed_request_id"])
    compressed_time = seconds(compressed_id)
    cold_time = seconds(request["cold_trial"])
    lossless_time = seconds(request["repair_trial"])
    state_bytes = compressed["artifacts"]["state"]["bytes"]
    lossless_bytes = results[request["repair_trial"]]["artifacts"]["state"]["bytes"]
    gates = compressed["registered_scientific_gates"]
    require(gates["checks"]["latency"]["passed"] ==
            (transactions[compressed_id]['controller_elapsed_ns'] < transactions[request['cold_trial']]['controller_elapsed_ns']),
            "Latency gate differs")
    require(gates["checks"]["storage"]["passed"] == (state_bytes < lossless_bytes), "Storage gate differs")
    require(compressed["artifacts"]["model"] == results[request["cold_trial"]]["artifacts"]["model"],
            "Compressed complete model descriptor differs")
    require(equal_file_bytes(model_path(compressed_id), model_path(request['cold_trial'])),
            'Compressed complete model bytes differ')
    require(compressed["state_roundtrip_canonical"] is True, "Compressed state roundtrip failed")
    conversion_trial = next(t for t in program['trials'] if t['id'] == conversion_id)
    conversion_diagnostics = verify_diagnostics(results[conversion_id], conversion_trial['plan'])
    compressed_diagnostics = verify_diagnostics(compressed, compressed_trial['plan'])
    native_evidence = verify_native_receipts(compressed, compressed_trial['plan'], program, current / 'source')

    evidence = {}
    def bind(path):
        path = Path(path)
        evidence[str(path.relative_to(ROOT))] = controller.hashed(path)
    for path in sorted(current.rglob("*")):
        if path.is_file() and path.suffix in (".json", ".py"):
            bind(path)
    # Include the historical metadata, current control code, and static inputs
    # used by check_registered, not just files under the new campaign directory.
    bind(ROOT / controller.BINDINGS)
    for name in controller.read_json(ROOT / controller.BINDINGS)['files']:
        bind(ROOT / name)
    for name in controller.CONTROLLERS:
        bind(ROOT / name)
    for trial in program['trials']:
        for entry in trial['plan']['inputs'].values():
            path = Path(entry['path'])
            if str(path.relative_to(ROOT)) not in evidence:
                bind(path)
    for path in (Path(__file__), ROOT / 'scripts/analyze_compressed_service_v31.py'):
        bind(path)
    artifact_evidence = {str((current / 'attempts' / trial_id / 'outputs' / entry['file']).relative_to(ROOT)):
                        {'sha256': entry['sha256'], 'bytes': entry['bytes']}
                        for trial_id, result in results.items() for entry in result['artifacts'].values()}
    base_bytes = sum(Path(entry["path"]).stat().st_size for name, entry in
                     program["trials"][0]["plan"]["inputs"].items() if name in ("config", "weights"))
    return {
        "schema": "independent-request-analysis-v32", "status": "complete_verified",
        "corpus": corpus, "campaign": str(current.relative_to(ROOT)),
        "program_sha256": digest(raw), "protocol_sha256": digest(protocol),
        "registered_runtime": registration["runtime"],
        "numerical_target": "fixed nearest-anchor features; distinct from original sequential calibration",
        "primary_clock": program["primary_clock"],
        "clock_limit": "Recorded controller transaction excludes prerequisite/bootstrap checks and post-receipt agreement/gate/archive analysis; not whole CLI invocation latency.",
        "statistical_scope": "Two alternative deletion requests sharing one root; one timing per method and request. Development replication, no population interval.",
        "confirmation": False, "neural_inference_performed": False,
        "new_quality_inference_performed": False, "historical_binary_outputs_reverified": False,
        "all_seven_trials_verified": True, "current_binary_artifacts_reverified": True,
        "independent_fresh_canonical_retained_state_comparator": False,
        "state_scope": "Actual successor state bytes and canonical parser roundtrips verified; no separately prepared retained-state oracle measured.",
        "pairs": pairs,
        "trials": [{"id": trial['id'], "method": trial['plan']['method'],
                    "controller_elapsed_ns": transactions[trial['id']]['controller_elapsed_ns'],
                    "controller_seconds": seconds(trial['id']), "artifacts": results[trial['id']]['artifacts'],
                    "scientific_gates": results[trial['id']]['registered_scientific_gates']}
                   for trial in program['trials']],
        "descriptive_geometric_mean_cold_over_lossless_repair": math.exp(sum(math.log(p["cold_over_repair"]) for p in pairs) / len(pairs)),
        "all_observed_lossless_pairs_favor_repair": all(p["repair_faster"] for p in pairs),
        "compressed": {
            "request": request["id"], "trial": compressed_id,
            "repair_seconds": compressed_time, "cold_seconds": cold_time, "lossless_repair_seconds": lossless_time,
            "cold_over_compressed": cold_time / compressed_time,
            "lossless_over_compressed": lossless_time / compressed_time,
            "scientific_gates": gates,
            "model": compressed["artifacts"]["model"], "state": compressed["artifacts"]["state"],
            "state_reduction_percent_over_lossless": 100 * (1 - state_bytes / lossless_bytes),
            "certificate_accepted_stages": compressed["diagnostics"]["certificate_accepted_stages"],
            "certificate_rejected_stages": compressed['diagnostics']['certificate_rejected_stages'],
            "point_solver_stages": compressed['diagnostics']['point_solver_stages'],
            "neural_stage_record_pairs": compressed["diagnostics"]["neural_stage_record_pairs"],
            "complete_state_plus_base_bytes": state_bytes + base_bytes,
            "lossless_state_plus_base_bytes": lossless_bytes + base_bytes,
        },
        "preparation_seconds": seconds(preparation_id), "conversion_seconds": seconds(conversion_id),
        "conversion_diagnostics": conversion_diagnostics,
        "compressed_diagnostics": compressed_diagnostics,
        "native_certificate_evidence": native_evidence,
        "common_base_checkpoint_bytes": base_bytes,
        "state_already_contains_calibrated_model": True,
        "changing_state_lifetime_benefit_established": False,
        "lifetime_limit": program["lifetime_limit"],
        "phase_budget": budget,
        "analysis_cpu_ns": time.process_time_ns() - started,
        "analysis_cost_excluded_from_worker_ledger": True,
        "analysis_source_sha256": controller.hashed(Path(__file__)),
        "evidence_sha256": evidence,
        "verified_binary_artifacts": artifact_evidence,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", choices=("wikitext", "c4"), required=True)
    parser.add_argument("--workspace", help="Same local_runs namespace used by the controller")
    parser.add_argument("--output", type=Path, help="New output filename; existing files are never replaced")
    args = parser.parse_args()
    controller.WORKSPACE = controller.validate_workspace(args.workspace)
    with research_worker_lock(ROOT):
        result = analyze(args.corpus)
    raw = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as stream:
            stream.write(raw)
        print(json.dumps({"output": str(args.output), "corpus": args.corpus, "status": result["status"]}))
    else:
        print(raw, end="")


if __name__ == "__main__":
    main()
