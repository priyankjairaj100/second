#!/usr/bin/env python3
"""Read-only recovery audit of evidence published at 604de5b.

This does not rerun inference or recover missing binary artifacts. It checks raw
metadata against the published manifest, then recomputes the reported contrasts.
The published commit remains the trust anchor. No output file is written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess

PUBLISHED_COMMIT = "604de5b830bd1386055b394df13275ef7e55475a"
MODEL_SHA256 = "25068a9373bb477123401124f07d5e02e09939f890fa16670d04d57e052bfce8"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def audit(root):
    manifest = subprocess.check_output(
        ["git", "show", f"{PUBLISHED_COMMIT}:MANIFEST.sha256"], cwd=root, text=True
    )
    expected = dict((line[66:], line[:64]) for line in manifest.splitlines())
    verified = {}
    missing_binary = []

    def read(relative):
        relative = str(relative)
        data = (root / relative).read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        require(expected.get(relative) == sha, f"Published hash mismatch: {relative}")
        verified[relative] = sha
        return json.loads(data)

    def trial(phase, name):
        base = Path("campaigns") / phase
        program = read(base / "program.json")
        protocol = read(base / "protocol.json")
        registration = read(base / "registration.json")
        require(registration["program_sha256"] == verified[str(base / "program.json")], "Program registration mismatch")
        require(registration["protocol_sha256"] == verified[str(base / "protocol.json")], "Protocol registration mismatch")
        require(protocol["program_sha256"] == registration["program_sha256"], "Protocol program mismatch")
        attempt = base / "attempts" / name
        transaction = read(attempt / "transaction.json")
        receipt = read(attempt / "worker/result.json")
        plan = read(attempt / "plan.json")
        result = read(attempt / "outputs/completion.json")
        sealed = read(attempt / "sealed-progress.json")
        require(result == sealed, f"Sealed result differs: {name}")
        require(transaction["receipt_sha256"] == verified[str(attempt / "worker/result.json")], f"Receipt mismatch: {name}")
        require(receipt["worker_identity"]["plan_sha256"] == verified[str(attempt / "plan.json")], f"Plan mismatch: {name}")
        require(result["plan_sha256"] == receipt["worker_identity"]["plan_sha256"], f"Result plan mismatch: {name}")
        require(plan["program_sha256"] == registration["program_sha256"], f"Trial program mismatch: {name}")
        require(plan["protocol_sha256"] == registration["protocol_sha256"], f"Trial protocol mismatch: {name}")
        require(receipt["outcome"] == transaction["worker_outcome"], f"Outcome mismatch: {name}")
        require(receipt["outcome"]["status"] == result["status"] == "complete", f"Incomplete: {name}")
        require(receipt["outcome"]["returncode"] == 0, f"Worker failed: {name}")
        debit = receipt["budget_debit"]
        require(debit["state"] == "settled", f"Unsettled trial: {name}")
        require(transaction["budget"]["attempts"][receipt["budget_attempt_id"]] == debit, f"Budget mismatch: {name}")
        require(not any(transaction["budget"]["over_cap"].values()), f"Budget cap exceeded: {name}")
        for filename, binding in receipt["artifacts"].items():
            relative = attempt / "worker" / receipt["attempt"] / filename
            read(relative)
            require(verified[str(relative)] == binding["sha256"], f"Worker artifact mismatch: {relative}")
            require((root / relative).stat().st_size == binding["bytes"], f"Worker artifact size mismatch: {relative}")
        for binding in result["artifacts"].values():
            path = attempt / "outputs" / binding["file"]
            if binding["file"].endswith(".bin") and not (root / path).is_file():
                missing_binary.append(str(path))
        if "model_code_elements" in result:
            require(result["model_code_elements"] == 42467328, f"Incomplete code count: {name}")
            require(result["stage_count"] == 24, f"Incomplete stage count: {name}")
            require(result["complete_model"] and result["model_roundtrip_exact"], f"Model checks failed: {name}")
        return transaction["controller_elapsed_ns"] / 1e9, result

    prep, _ = trial("ordered_service_v30", "prepare-256")
    original, _ = trial("ordered_service_v30", "original-model-256")
    indexed, indexed_result = trial("ordered_service_v30", "indexed-001")
    require(indexed_result["artifacts"]["model"]["sha256"] == MODEL_SHA256, "Indexed model mismatch")
    pairs = []
    lossless_state = None
    for i in range(1, 4):
        repair, repair_result = trial("ordered_service_v30", f"repair-{i:03d}")
        cold, cold_result = trial("ordered_service_v30", f"cold-{i:03d}")
        for result in (repair_result, cold_result):
            require(result["artifacts"]["model"]["sha256"] == MODEL_SHA256, "Retained model hash mismatch")
        state = repair_result["artifacts"]["state"]
        require(lossless_state is None or state == lossless_state, "Lossless state metadata differs")
        lossless_state = state
        pairs.append({"repair_seconds": repair, "cold_seconds": cold, "cold_over_repair": cold / repair})
    ordered = read("campaigns/ordered_service_v30/audit.json")
    geometric_mean = math.exp(sum(math.log(p["cold_over_repair"]) for p in pairs) / len(pairs))
    require(math.isclose(ordered["geometric_mean_cold_over_repair"], geometric_mean), "Ordered summary mismatch")

    compression = {}
    for phase, convert, repair_name in (
        ("compressed_service_v30", "convert-256", "repair-128"),
        ("compressed_service_v31", "convert-256-48", "repair-128-48"),
    ):
        conversion, _ = trial(phase, convert)
        repair, result = trial(phase, repair_name)
        gates = read(Path("campaigns") / phase / "attempts" / repair_name / "scientific-gates.json")
        require(result["artifacts"]["model"]["sha256"] == MODEL_SHA256, f"Compressed model mismatch: {phase}")
        minimum_cold = min(p["cold_seconds"] for p in pairs)
        storage = result["artifacts"]["state"]["bytes"]
        latency_pass = repair < minimum_cold
        storage_pass = storage < lossless_state["bytes"]
        require(gates["checks"]["latency"]["passed"] == latency_pass, "Latency gate mismatch")
        require(gates["checks"]["storage"]["passed"] == storage_pass, "Storage gate mismatch")
        compression[phase] = {
            "conversion_seconds": conversion,
            "repair_seconds": repair,
            "minimum_cold_over_repair": minimum_cold / repair,
            "state_bytes": storage,
            "state_reduction_percent": 100 * (1 - storage / lossless_state["bytes"]),
            "latency_gate_pass": latency_pass,
            "storage_gate_pass": storage_pass,
            "certified_stages": result["diagnostics"]["certificate_accepted_stages"],
            "preparation_plus_first_repair_seconds": prep + conversion + repair,
            "original_model_plus_fastest_cold_seconds": original + minimum_cold,
        }

    quality_seconds, quality = trial("heldout_quality_v30", "quality-40")
    quality_archive = read("campaigns/heldout_quality_v30_summary.json")
    require(quality_archive["completion_sha256"] == verified["campaigns/heldout_quality_v30/attempts/quality-40/outputs/completion.json"], "Quality completion mismatch")
    require(len(quality["article_ids"]) == 40 and len(set(quality["article_ids"])) == 40, "Quality article count mismatch")
    perplexities = {}
    by_model = {}
    for model, rows in quality["quality"].items():
        require(len(rows) == 40, f"Incomplete quality rows: {model}")
        require([row["id"] for row in rows] == quality["article_ids"], f"Unpaired quality rows: {model}")
        predictions = sum(row["predictions"] for row in rows)
        require(predictions == 5080, "Quality prediction count mismatch")
        perplexities[model] = math.exp(math.fsum(row["nll_sum"] for row in rows) / predictions)
        by_model[model] = {row["id"]: row for row in rows}
    ratio = perplexities["fixed128"] / perplexities["sequential128"]
    contrast = quality_archive["contrasts"]["sequential128"]
    require(math.isclose(ratio, contrast["perplexity_ratio"], rel_tol=1e-12), "Quality ratio mismatch")
    wins = sum(by_model["fixed128"][key]["nll_sum"] < by_model["sequential128"][key]["nll_sum"] for key in quality["article_ids"])
    require(wins == contrast["article_wins"] == 20, "Quality win count mismatch")
    require(len(set(quality["excluded_from_future_confirmation_ids"])) == 60, "Exclusion count mismatch")
    require(quality["bounded_pool_confirmation_gate_pass"] == quality_archive["bounded_pool_confirmation_gate_pass"], "Quality gate mismatch")
    return {
        "schema": "published-metadata-recovery-audit-v32",
        "published_commit": PUBLISHED_COMMIT,
        "status": "metadata_checks_passed",
        "scope": "Raw archived metadata and arithmetic only; missing model/state bytes were not reverified.",
        "neural_inference_performed": False,
        "files_written": False,
        "independent_v32_results_audited": False,
        "ordered_pairs": pairs,
        "ordered_geometric_mean_cold_over_repair": geometric_mean,
        "indexed_seconds": indexed,
        "lossless_retained_state_bytes": lossless_state["bytes"],
        "compression": compression,
        "heldout_quality": {
            "controller_seconds": quality_seconds,
            "articles": 40,
            "predictions_per_model": 5080,
            "perplexities_recomputed": perplexities,
            "fixed_over_sequential": ratio,
            "article_wins": wins,
            "article_losses": 40 - wins,
            "archived_bounded_pool_gate": quality["bounded_pool_confirmation_gate_pass"],
            "bootstrap_recomputed": False,
            "quality_superiority_established": False,
        },
        "verified_metadata_files": len(verified),
        "evidence_sha256": verified,
        "missing_binary_artifacts": sorted(set(missing_binary)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(audit(args.root.resolve()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
