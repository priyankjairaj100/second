#!/usr/bin/env python3
"""Audit the original two request roots under the reviewed V33 continuation.

This adapter preserves V32 analysis and its strict verifier. It binds the one
pinned terminal-copy exception without changing any original evidence. Fresh
local V32 replications must use analyze_independent_requests_v32.py instead.
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
from scripts import launch_independent_requests_v33 as controller
from scripts.analyze_independent_requests_v32 import (
    require, equal_file_bytes, verified_seconds, changed_model_codes,
    verify_native_receipts, verify_result_fields,
)
from scripts.analyze_full_service_v30 import verify_final_budget
from scripts.analyze_compressed_service_v31 import verify_diagnostics
from src.pilot_budget import research_worker_lock
from src.run_store import digest


def verify_recovery_provenance(corpus):
    """Bind the exception and its prerequisite for both original root analyses."""
    require(corpus in ("wikitext", "c4"), "Unknown corpus")
    amendment = controller.amendment()
    recovery = controller.recovery
    result = recovery.verify_completed(ROOT / recovery.INCIDENT_RELATIVE)
    audit_path = ROOT / recovery.AUDIT_RELATIVE
    snapshot_path = ROOT / recovery.SNAPSHOT_RELATIVE / 'manifest.json'
    audit = controller.read_json(audit_path)
    snapshot = controller.read_json(snapshot_path)
    require(audit['original_three_copy_guard_passed'] is False,
            'Incident audit must preserve the original strict guard failure')
    require(amendment['cause'] == snapshot['cause'] == 'unknown', 'Incident cause was invented')
    incident_trial = Path(recovery.INCIDENT_RELATIVE).name
    recovered = [incident_trial] if corpus == 'wikitext' else []
    paths = [str(controller.AMENDMENT.relative_to(ROOT)), recovery.AUDIT_RELATIVE,
             str(snapshot_path.relative_to(ROOT))]
    for name in sorted(snapshot['files']):
        paths.extend((str(Path(recovery.SNAPSHOT_RELATIVE) / name),
                      str(Path(recovery.INCIDENT_RELATIVE) / name)))
    paths.extend(amendment['prior_text_bindings'])
    return {
        'recovered_terminal_trials': recovered,
        'cross_corpus_prerequisite': corpus == 'c4',
        'incident_trial': incident_trial,
        'incident_root': 'campaigns/independent_wikitext_v32',
        'incident_cause': 'unknown',
        'incident_original_strict_three_copy_guard_passed': False,
        'evidence_rewritten': False,
        'amendment_sha256': controller.hashed(controller.AMENDMENT),
        'incident_audit_sha256': controller.hashed(audit_path),
        'preserved_snapshot_sha256': controller.hashed(snapshot_path),
        'incident_model_sha256': result['model_artifact']['sha256'],
        'evidence_paths': sorted(set(paths)),
        'scope': 'Only the pinned WikiText cold-1 trial uses recovered terminal evidence. All other trials retain the original strict guard.',
    }


def analyze(corpus):
    started = time.process_time_ns()
    require(controller.base.WORKSPACE is None, "V33 analysis is limited to the original incident-bound roots")
    incident = verify_recovery_provenance(corpus)
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
    bind(ROOT / controller.base.BINDINGS)
    for name in controller.read_json(ROOT / controller.base.BINDINGS)['files']:
        bind(ROOT / name)
    for name in controller.CONTROLLERS:
        bind(ROOT / name)
    for name in incident['evidence_paths']:
        bind(ROOT / name)
    for trial in program['trials']:
        for entry in trial['plan']['inputs'].values():
            path = Path(entry['path'])
            if str(path.relative_to(ROOT)) not in evidence:
                bind(path)
    for path in (Path(__file__), ROOT / 'scripts/analyze_independent_requests_v32.py', ROOT / 'scripts/analyze_compressed_service_v31.py'):
        bind(path)
    artifact_evidence = {str((current / 'attempts' / trial_id / 'outputs' / entry['file']).relative_to(ROOT)):
                        {'sha256': entry['sha256'], 'bytes': entry['bytes']}
                        for trial_id, result in results.items() for entry in result['artifacts'].values()}
    base_bytes = sum(Path(entry["path"]).stat().st_size for name, entry in
                     program["trials"][0]["plan"]["inputs"].items() if name in ("config", "weights"))
    return {
        "schema": "independent-request-analysis-v33", "status": "complete_verified",
        "verification_contract": "V33 strict verification with one pinned, append-only terminal-copy exception",
        "recovered_terminal_trials": incident["recovered_terminal_trials"],
        "original_strict_three_copy_guard_passed": corpus != "wikitext",
        "recovery_provenance": incident,
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
                    "original_strict_three_copy_guard_passed": trial['id'] not in incident['recovered_terminal_trials'],
                    "declared_terminal_recovery_used": trial['id'] in incident['recovered_terminal_trials'],
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
    parser.add_argument("--output", type=Path, help="New output filename; existing files are never replaced")
    args = parser.parse_args()
    with research_worker_lock(ROOT):
        result = analyze(args.corpus)
    raw = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as stream:
            stream.write(raw)
        print(json.dumps({"output": str(args.output), "corpus": args.corpus, "status": result["status"],
                          "recovered_terminal_trials": result["recovered_terminal_trials"]}))
    else:
        print(raw, end="")


if __name__ == "__main__":
    main()
