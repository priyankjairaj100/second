"""Fail-closed input and generation checks for the fixed v14 quality control.

Hashes preserve provenance on the trusted experiment filesystem. They do not
authenticate an attacker who replaces every receipt and its corresponding data.
"""
from pathlib import Path

from .run_store import digest, strict_json


MODEL_ORDER = ("dyadic_calibrated", "power2_calibrated", "dyadic_nearest", "base")


def bound_file(path):
    path = Path(path)
    return {"path": str(path), "sha256": digest(path.read_bytes())}


def read_bound(item):
    if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
        raise ValueError("invalid bound input")
    raw = Path(item["path"]).read_bytes()
    if digest(raw) != item["sha256"]:
        raise ValueError("bound input changed")
    return raw


def capture_generation(directory, kind):
    """Bind the original plan, sealed receipt, progress, and model artifact."""
    directory = Path(directory)
    if kind not in ("dyadic", "power2"):
        raise ValueError("unsupported generation kind")
    model_name = "model-index.json" if kind == "dyadic" else "model.bin"
    bundle = {"kind": kind,
              "plan": bound_file(directory / "plan.json"),
              "receipt": bound_file(directory / "worker/result.json"),
              "progress": bound_file(directory / "outputs/progress.json"),
              "model": bound_file(directory / "outputs" / model_name)}
    load_generation(bundle)
    return bundle


def load_generation(bundle):
    """Reject incomplete, stale, swapped, or altered generation evidence."""
    if (not isinstance(bundle, dict)
            or set(bundle) != {"kind", "plan", "receipt", "progress", "model"}
            or bundle["kind"] not in ("dyadic", "power2")):
        raise ValueError("invalid generation evidence bundle")
    plan_raw = read_bound(bundle["plan"])
    plan = strict_json(plan_raw)
    receipt = strict_json(read_bound(bundle["receipt"]))
    progress = strict_json(read_bound(bundle["progress"]))
    model_raw = read_bound(bundle["model"])
    if (receipt.get("status") != "complete"
            or receipt.get("budget_debit", {}).get("state") != "settled"
            or receipt.get("outcome", {}).get("status") != "complete"
            or receipt.get("outcome", {}).get("returncode") != 0):
        raise ValueError("model generation is incomplete")
    plan_hash = digest(plan_raw)
    if (receipt.get("worker_identity", {}).get("plan_sha256") != plan_hash
            or progress.get("plan_sha256") != plan_hash):
        raise ValueError("generation receipt or progress refers to another plan")
    if progress.get("status") != "complete":
        raise ValueError("generation progress is incomplete")
    if bundle["kind"] == "dyadic":
        if (plan.get("mode") != "full_quantization" or plan.get("grid_axis") != "dyadic_row"
                or progress.get("full_model_quantization") is not True):
            raise ValueError("dyadic generation requires complete model quantization")
        model = strict_json(model_raw)
        if (not model.get("stages") or model.get("stages") != progress.get("stages")
                or model.get("target_sha256") != progress.get("target_sha256")):
            raise ValueError("dyadic model index differs from generation progress")
    else:
        artifact = progress.get("model_artifact", {})
        if (progress.get("complete_model") is not True
                or artifact.get("file") != "model.bin"
                or artifact.get("sha256") != digest(model_raw)
                or artifact.get("bytes") != len(model_raw)):
            raise ValueError("power2 model differs from completed generation artifact")
        model = model_raw
    return plan, progress, model


def validate_quality_inputs(evaluation, calibration, previous_evaluations,
                            fine_plan, fine_progress, power2_plan, power2_progress,
                            checkpoint_sha256, calibration_sha256):
    """Validate all four controls, exclusions, and shared retained membership."""
    if (evaluation.get("schema") != "v14-prospective-finer-grid-quality"
            or evaluation.get("model_order") != list(MODEL_ORDER)):
        raise ValueError("the fixed four-model order is required")
    records = evaluation.get("records", [])
    if not isinstance(records, list) or len(records) != 4:
        raise ValueError("four evaluation records are required")
    ids = []
    for record in records:
        rid = record.get("id")
        tokens = record.get("tokens")
        if (not isinstance(rid, str) or not rid.startswith("wikitext2:validation:article-row-")
                or not isinstance(tokens, list) or len(tokens) != 16
                or any(type(token) is not int or token < 0 for token in tokens)):
            raise ValueError("evaluation requires validation articles and sixteen integer tokens")
        ids.append(rid)
    if len(set(ids)) != 4:
        raise ValueError("evaluation record IDs must be distinct")
    original = calibration.get("records", [])
    original_ids = [record["id"] for record in original]
    if (len(original_ids) != 2 or len(set(original_ids)) != 2
            or any(len(record["tokens"]) != 16 for record in original)):
        raise ValueError("the original two-record calibration control is required")
    if set(ids) & set(original_ids):
        raise ValueError("evaluation overlaps calibration")
    previous_ids = {record["id"] for prior in previous_evaluations for record in prior["records"]}
    if set(ids) & previous_ids:
        raise ValueError("evaluation repeats earlier quality articles")
    prior_exclusions = evaluation.get("prior_exclusions", [])
    future_exclusions = evaluation.get("excluded_from_future_confirmation_ids", [])
    if (len(prior_exclusions) != len(set(prior_exclusions))
            or set(prior_exclusions) != previous_ids
            or len(future_exclusions) != len(set(future_exclusions))
            or set(future_exclusions) != previous_ids | set(ids)):
        raise ValueError("quality exclusion metadata is incomplete or inconsistent")
    deleted = fine_plan.get("deleted_record_ids", [])
    if len(deleted) != 1 or not set(deleted) <= set(original_ids):
        raise ValueError("exactly one original calibration article must be deleted")
    retained = sorted(set(original_ids) - set(deleted))
    for plan, progress in ((fine_plan, fine_progress), (power2_plan, power2_progress)):
        if (plan.get("records_sha256") != calibration_sha256
                or plan.get("deleted_record_ids") != deleted
                or plan.get("checkpoint_sha256") != checkpoint_sha256
                or sorted(progress.get("original_record_ids", [])) != sorted(original_ids)
                or progress.get("deleted_record_ids") != deleted
                or sorted(progress.get("retained_record_ids", [])) != retained):
            raise ValueError("model calibration, checkpoint, or retained membership differs")
