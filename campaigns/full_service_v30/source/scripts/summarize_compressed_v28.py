"""Summarize frozen development evidence without executing a research worker."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-artifacts", action="store_true",
                        help="Also require and hash ignored model/state binaries.")
    args = parser.parse_args()
    bindings: dict[str, str] = {}

    def read(rel: str) -> dict:
        path = ROOT / rel
        bindings[rel] = digest(path)
        return json.loads(path.read_text())

    def transaction(campaign: str, attempt: str) -> dict:
        prefix = f"campaigns/{campaign}/attempts/{attempt}"
        tx = read(f"{prefix}/transaction.json")
        receipt_path = f"{prefix}/worker/result.json"
        receipt = read(receipt_path)
        assert tx["receipt_sha256"] == bindings[receipt_path]
        p = read(f"{prefix}/sealed-progress.json")
        assert p["status"] == "complete"
        assert tx["worker_outcome"]["returncode"] == 0
        assert p["stage_count"] == 24
        assert p["model_code_elements"] == 42_467_328
        artifacts = {"model": p["model_artifact"]}
        if p.get("state_artifact"):
            artifacts["state"] = p["state_artifact"]
        if args.verify_artifacts:
            for info in artifacts.values():
                path = ROOT / prefix / "outputs" / info["file"]
                assert path.stat().st_size == info["bytes"]
                assert digest(path) == info["sha256"]
        live_path = ROOT / prefix / "outputs/progress.json"
        live_matches = digest(live_path) == bindings[f"{prefix}/sealed-progress.json"]
        bindings[str(live_path.relative_to(ROOT))] = digest(live_path)
        d = p["diagnostics"]
        keys = ["certificate_accepted_stages", "certificate_rejected_stages",
                "neural_stage_record_pairs", "avoided_neural_stage_record_pairs",
                "service_elapsed_ns", "certificate_elapsed_ns"]
        return {
            "attempt": prefix,
            "controller_elapsed_ns": tx["controller_elapsed_ns"],
            "controller_elapsed_seconds": tx["controller_elapsed_ns"] / 1e9,
            "receipt_wall_ns": tx["worker_outcome"]["elapsed_wall_ns"],
            "complete_model": p["complete_model"],
            "complete_state": p["complete_state"],
            "stage_count": p["stage_count"],
            "model_code_elements": p["model_code_elements"],
            "artifacts": artifacts,
            "live_progress_matches_sealed": live_matches,
            "metrics": {k: d.get(k) for k in keys},
            "sparse_rows": {
                k: sum(s.get("solver_diagnostics", {}).get(k, 0)
                       for s in d.get("stages", []))
                for k in ("first_ball_certified_rows", "ridge_interval_certified_rows",
                          "preconditioned_interval_certified_rows", "python_universal_rows")
            } if campaign.endswith("v28") else None,
        }

    old = transaction("compressed_timing_v27", "repair-001")
    cold = transaction("compressed_timing_v27", "cold-001")
    new = transaction("compressed_timing_v28", "repair-001")
    assert old["artifacts"]["model"] == new["artifacts"]["model"]
    assert cold["artifacts"]["model"] == new["artifacts"]["model"]
    assert old["artifacts"]["state"] == new["artifacts"]["state"]
    assert new["live_progress_matches_sealed"]
    assert not cold["live_progress_matches_sealed"]
    discrepancy_path = "campaigns/compressed_timing_v27/attempts/cold-001/progress-discrepancy.json"
    discrepancy = read(discrepancy_path)
    assert discrepancy["cause"] == "unknown"
    assert discrepancy["raw_progress_preserved"]
    assert discrepancy["receipt_sha256"] == bindings[
        "campaigns/compressed_timing_v27/attempts/cold-001/worker/result.json"]

    archive = read("campaigns/compressed_state_audit_v26/summary.json")
    generations = {}
    for name, generation in archive["generations"].items():
        p = generation["precisions"]["40"]
        generations[name] = {k: p[k] for k in (
            "complete_state_bytes", "exact_state_bytes", "complete_state_sha256",
            "complete_state_reduction_bytes", "complete_state_reduction_fraction")}
    retained = next(v for v in generations.values()
                    if v["complete_state_sha256"] == new["artifacts"]["state"]["sha256"])
    assert retained["complete_state_bytes"] == new["artifacts"]["state"]["bytes"]

    campaign_names = ["fixed_feature_v23", "compressed_v25b", "compressed_v25c",
                      "compressed_v25d", "compressed_v26b", "compressed_v27",
                      "compressed_timing_v27", "compressed_v28", "compressed_timing_v28"]
    charges = []
    recorded = unknown = 0
    for name in campaign_names:
        ledger = read(f"campaigns/{name}/phase-cpu-budget/ledger.json")
        settled = held = 0
        for attempt in ledger["attempts"].values():
            if attempt["state"] == "settled":
                settled += attempt["charged_cpu_seconds"]
            else:
                assert attempt["state"] == "reserved"
                assert attempt["observed_cpu_ns"] is None
                held += attempt["reserved_cpu_seconds"]
        recorded += settled
        unknown += held
        charges.append({"campaign": name, "recorded_cpu_seconds": settled,
                        "unknown_reserved_cpu_seconds": held,
                        "charged_or_reserved_cpu_seconds": settled + held})
    assert (recorded, unknown) == (776, 122)

    # Bind all stage screens and original unstarted registrations without changing them.
    for folder in sorted((ROOT / "campaigns").glob("compressed*")):
        if not folder.is_dir():
            continue
        for name in ("program.json", "registration.json", "plan.json", "summary.json"):
            path = folder / name
            if path.exists():
                read(str(path.relative_to(ROOT)))
        for path in sorted(folder.glob("attempts/*/sealed-progress.json")):
            read(str(path.relative_to(ROOT)))
        for path in sorted(folder.glob("attempts/*/transaction.json")):
            read(str(path.relative_to(ROOT)))

    report = {
        "schema": "compressed-evidence-summary-v28",
        "date_utc": "2026-10-08",
        "scope": "Adaptive development on one DistilGPT2/WikiText deletion; no confirmation.",
        "target": "Fixed nearest-grid ancestor features; not original sequential calibration.",
        "trusted_preparation_required": True,
        "full_model_results": {"v27_repair": old, "v27_cold_model_only": cold, "v28_repair": new},
        "ratios": {
            "v27_repair_over_v28_repair": old["controller_elapsed_ns"] / new["controller_elapsed_ns"],
            "cold_over_v28_repair": cold["controller_elapsed_ns"] / new["controller_elapsed_ns"],
            "v28_slower_than_cold_percent": (new["controller_elapsed_ns"] / cold["controller_elapsed_ns"] - 1) * 100,
        },
        "timing_conclusion": "Practically close: V28 is 0.101% slower in one comparison; no statistical equivalence or speed advantage established.",
        "comparison_limits": [
            "Single V28 retiming against the earlier same-session V27 cold comparator.",
            "Repair writes model and complete state; cold writes model only.",
            "No randomized repetitions, confidence interval, independent request, or lifetime claim.",
            "Equally indexed reconstruction shares the algorithm; no strict advantage follows.",
        ],
        "state_generations": generations,
        "retained_complete_state_reduction_percent": retained["complete_state_reduction_fraction"] * 100,
        "base_checkpoint_required": True,
        "storage_claim_scope": "Complete calibrated model plus repair state; excludes common base checkpoint.",
        "evidence_discrepancy": {"path": discrepancy_path, "cause": "unknown",
                                 "raw_preserved": True,
                                 "completion_basis": discrepancy["completion_basis"]},
        "budget": {
            "phase_cap_cpu_seconds": 900,
            "recorded_cpu_seconds": recorded,
            "unknown_reserved_cpu_seconds": unknown,
            "phase_charged_or_reserved_cpu_seconds": recorded + unknown,
            "phase_remaining_cpu_seconds": 900 - recorded - unknown,
            "legacy_cap_cpu_seconds": 10800,
            "legacy_charged_cpu_seconds": 10775,
            "legacy_remaining_cpu_seconds": 25,
            "combined_charged_or_reserved_cpu_seconds": 10775 + recorded + unknown,
            "independent_allowances_not_pooled": True,
            "campaigns": charges,
            "archive_analysis_and_software_checks_separately_reported": True,
        },
        "open_gates": ["Broader quality", "Realistic calibration size", "Independent deletion requests",
                       "Additional models and corpora", "Preparation and lifetime costs",
                       "Prospective confirmation", "Updated publication novelty assessment"],
        "acl_submission_ready": False,
        "empirical_program_complete": False,
        "artifact_binaries_reverified": args.verify_artifacts,
        "evidence_sha256": dict(sorted(bindings.items())),
    }
    path = ROOT / "campaigns/compressed_summary_v25_v28.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"report": str(path.relative_to(ROOT)), "bound_files": len(bindings),
                      "ratios": report["ratios"], "phase_held": recorded + unknown}))


if __name__ == "__main__":
    main()
