"""Adaptive quality follow-up on eight already exposed development articles.

The primary control is archived fixed-feature calibration with sixteen tokens.
The new model uses 128 retained tokens and original normalization 256.
Archived sequential calibration has sixteen tokens and normalization 32.
That secondary comparison is deliberately unmatched and cannot identify a
fixed-feature versus sequential effect at the larger calibration workload.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.run_store import atomic_write, canonical_json, digest
from scripts.run_quality_v30 import NumpyQualityDecoder, nearest_prefix, nll_from_logits, check_generation

LABELS = ("full_precision", "nearest_rounding", "fixed16", "sequential16", "fixed128")
OLD_LABELS = {"full_precision": "full_precision", "nearest_rounding": "nearest_rounding",
              "fixed16": "fixed_feature", "sequential16": "sequential"}
ORIGINAL_IDS = ["wikitext2:train:article-row-27113", "wikitext2:train:article-row-5326"]
POLICY = dict(schema="adaptive-quality-policy-v30", articles=8, tokens_per_article=128,
              primary_control="fixed16", safety_control="fixed16",
              max_aggregate_ratio=1.05, max_each_article_ratio=1.20,
              historical_parity_max_mean_nll_deviation=1e-8,
              bootstrap_repetitions=10000, bootstrap_seed=31,
              confirmation=False, scientific_promotion=False, new_exclusions=False,
              sequential128_available=False, sequential_implementation=None)


def policy_for_mode(matched=False):
    if type(matched) is not bool:
        raise ValueError("matched mode must be Boolean")
    return dict(POLICY, primary_control="sequential128" if matched else "fixed16",
                sequential128_available=matched,
                sequential_implementation="ordered-finite-decoder-v30" if matched else None)


def bound(entry):
    if not isinstance(entry, dict) or set(entry) not in ({"path", "sha256"}, {"path", "sha256", "bytes"}):
        raise ValueError("invalid bound descriptor")
    path = Path(entry["path"])
    if not path.is_absolute():
        raise ValueError("bound paths must be absolute")
    raw = path.read_bytes()
    if digest(raw) != entry["sha256"] or ("bytes" in entry and len(raw) != entry["bytes"]):
        raise ValueError("bound input changed: " + str(path))
    return raw


def verify_terminal_payload(raw, verified):
    """Accept only the adapter's exact, checked addition to original records."""
    original = json.loads(raw)
    if canonical_json(original) != raw or any(verified.get(k) != value for k, value in original.items()):
        raise ValueError("verified terminal fields differ from bound original bytes")
    extra = set(verified) - set(original)
    if extra:
        if (extra != {"artifacts", "artifact_manifest_source"}
                or original.get("schema") not in ("adaptive-complete-service-transaction-v30", "sequential-quality-comparison-v30")
                or verified["artifact_manifest_source"] != "verified named model_artifact/state_artifact fields; original bytes unchanged"):
            raise ValueError("unexpected completion adapter fields")
        expected = dict(model=original["model_artifact"])
        if original.get("complete_state") is True:
            expected["state"] = original["state_artifact"]
        if verified["artifacts"] != expected:
            raise ValueError("derived service artifacts differ from original named fields")
    return original


def verified_terminal(entry):
    from src.service_terminal_evidence_v30 import verify_completed
    raw = bound(entry)
    path = Path(entry["path"])
    if path.name != "completion.json" or path.parent.name != "outputs":
        raise ValueError("completion input must name the original terminal artifact")
    attempt = path.parent.parent
    original = verify_terminal_payload(raw, verify_completed(attempt))
    return raw, original, attempt


def validate_new_generation(completion, generation_plan, records, *, checkpoint_hashes, model_binding):
    """Validate the larger calibration contract without evaluating a model."""
    if (completion.get("schema") != "adaptive-complete-service-transaction-v30"
            or completion.get("status") != "complete" or completion.get("method") != "repair"
            or generation_plan.get("method") != "repair"
            or completion.get("complete_model") is not True
            or completion.get("complete_state") is not True
            or completion.get("model_roundtrip_exact") is not True
            or completion.get("state_roundtrip_canonical") is not True
            or completion.get("use_candidates") is not False
            or completion.get("confirmation") is not False
            or completion.get("scientific_promotion") is not False):
        raise ValueError("new model requires complete certified repair evidence")
    if (completion.get("source_sha256") != generation_plan.get("source_sha256")
            or not completion.get("source_sha256")
            or completion.get("checkpoint_files_sha256") != checkpoint_hashes
            or completion.get("original_token_count") != 256
            or generation_plan.get("original_token_count") != 256
            or completion.get("retained_token_count") != 128
            or completion.get("original_record_lengths") != [128, 128]
            or completion.get("retained_record_lengths") != [128]
            or completion.get("original_record_ids") != ORIGINAL_IDS
            or completion.get("retained_record_ids") != ORIGINAL_IDS[1:]
            or completion.get("committed_record_ids") != ORIGINAL_IDS[1:]
            or completion.get("deleted_record_ids") != ORIGINAL_IDS[:1]
            or generation_plan.get("record_ids") != ORIGINAL_IDS[1:]
            or generation_plan.get("deleted_ids") != ORIGINAL_IDS[:1]):
        raise ValueError("new calibration membership, normalization, source, or checkpoint differs")
    if (type(records) is not dict or set(records) != {"records"}
            or [r.get("id") for r in records["records"]] != ORIGINAL_IDS
            or any(len(r.get("tokens", [])) != 128 for r in records["records"])
            or completion.get("original_records_sha256") != digest(canonical_json(records))
            or completion.get("records_input_sha256") != generation_plan["inputs"]["records"]["sha256"]):
        raise ValueError("new calibration token binding differs")
    recipe = completion.get("target_recipe", {})
    if recipe.get("original_token_count") != 256 or recipe.get("bits") != 4:
        raise ValueError("new target recipe differs")
    artifact = completion.get("model_artifact", {})
    if (artifact.get("file") != "model.bin" or artifact.get("sha256") != model_binding["sha256"]
            or artifact.get("bytes") != model_binding["bytes"]
            or completion.get("stage_count") != 24
            or len(set(completion.get("stage_ids", []))) != 24
            or completion.get("model_code_elements") != 42467328):
        raise ValueError("new complete model artifact differs")


def validate_sequential_generation(completion, generation_plan, records, *, checkpoint_hashes,
                                   model_binding, fixed_completion):
    """A matched comparator needs the same tokens, normalization, and base target."""
    if (completion.get("schema") != "sequential-quality-comparison-v30"
            or completion.get("status") != "complete"
            or completion.get("method") != "model_only_fresh"
            or generation_plan.get("method") != "model_only_fresh"
            or completion.get("comparison_role") != "sequential_quality"
            or completion.get("complete_model") is not True
            or completion.get("complete_state") is not False
            or completion.get("model_roundtrip_exact") is not True
            or completion.get("confirmation") is not False
            or completion.get("scientific_promotion") is not False
            or completion.get("source_sha256") != generation_plan.get("source_sha256")
            or not completion.get("source_sha256")
            or set(generation_plan.get("inputs", {})) != {"records", "config", "weights"}):
        raise ValueError("matched sequential generation is incomplete or uses a different access contract")
    if (completion.get("checkpoint_files_sha256") != checkpoint_hashes
            or completion.get("original_token_count") != 256
            or generation_plan.get("original_token_count") != 256
            or completion.get("retained_token_count") != 128
            or completion.get("original_record_ids") != ORIGINAL_IDS
            or completion.get("retained_record_ids") != ORIGINAL_IDS[1:]
            or completion.get("deleted_record_ids") != ORIGINAL_IDS[:1]
            or generation_plan.get("record_ids") != ORIGINAL_IDS[1:]
            or generation_plan.get("deleted_ids") != ORIGINAL_IDS[:1]
            or completion.get("original_records_sha256") != digest(canonical_json(records))
            or completion.get("original_records_sha256") != fixed_completion["original_records_sha256"]
            or completion.get("records_input_sha256") != generation_plan["inputs"]["records"]["sha256"]
            or completion.get("target_recipe") != fixed_completion["target_recipe"]
            or completion.get("sequential_target_sha256") != fixed_completion["base_target_sha256"]
            or completion.get("base_target_sha256") != fixed_completion["base_target_sha256"]
            or completion.get("fixed_target_sha256") != fixed_completion["fixed_target_sha256"]):
        raise ValueError("matched sequential tokens, target, normalization, or checkpoint differ")
    artifact = completion.get("model_artifact", {})
    if (artifact.get("file") != "model.bin" or artifact.get("sha256") != model_binding["sha256"]
            or artifact.get("bytes") != model_binding["bytes"]
            or completion.get("stage_count") != 24
            or completion.get("stage_ids") != fixed_completion["stage_ids"]
            or completion.get("model_code_elements") != 42467328):
        raise ValueError("matched sequential complete model artifact differs")


def validate_reused_articles(registration, first_result, pools):
    records = registration["records"]
    ids = [r["id"] for r in records]
    excluded = registration["excluded_from_future_confirmation_ids"]
    if (registration.get("schema") != "matched-quality-registration-v30"
            or first_result.get("status") != "complete"
            or first_result.get("development_quality_gate_pass") is not True
            or first_result.get("historical_parity_pass") is not True
            or first_result.get("confirmation") is not False
            or first_result.get("scientific_promotion") is not False
            or len(ids) != len(set(ids))
            or len(ids) != 8 or any(len(r["tokens"]) != 128 for r in records)
            or len(set(excluded)) != len(excluded) or len(excluded) != 20
            or first_result.get("excluded_from_future_confirmation_ids") != excluded
            or not set(ids) <= set(excluded)):
        raise ValueError("follow-up must reuse the complete exposed eight-article set")
    pool = {r["id"]: r for r in pools["evaluation"]}
    reserve = {r["id"] for r in pools["confirmation"]}
    if set(ids) & reserve or any(r["tokens"] != pool[r["id"]]["tokens"][:128] for r in records):
        raise ValueError("evaluation token or reserve binding differs")
    for label in OLD_LABELS.values():
        rows = first_result["quality"][label]
        if (len(rows) != 8 or {r["id"] for r in rows} != set(ids)
                or any(r["predictions"] != 127 or not math.isfinite(r["nll_sum"]) for r in rows)):
            raise ValueError("first quality result is incomplete")
    return records


def summarize(quality, records, *, matched=False):
    import numpy as np
    ids = [r["id"] for r in records]
    labels = LABELS + (("sequential128",) if matched else ())
    if len(ids) != 8 or len(set(ids)) != 8 or set(quality) != set(labels):
        raise ValueError("complete five-model article inventory is required")
    losses = {}
    for label in labels:
        table = {r["id"]: r for r in quality[label]}
        if (len(quality[label]) != 8 or set(table) != set(ids)
                or any(r["predictions"] != 127 or not math.isfinite(r["nll_sum"]) for r in table.values())):
            raise ValueError("matched prediction counts differ")
        losses[label] = np.asarray([table[rid]["nll_sum"] for rid in ids])
    rng = np.random.default_rng(POLICY["bootstrap_seed"])
    indices = rng.integers(0, 8, size=(POLICY["bootstrap_repetitions"], 8))
    totals = {label: dict(nll_sum=float(values.sum()), predictions=1016,
                         mean_nll=float(values.sum() / 1016),
                         perplexity=math.exp(float(values.sum() / 1016)))
              for label, values in losses.items()}
    comparisons = {}
    for reference in [label for label in labels if label != "fixed128"]:
        delta = losses["fixed128"] - losses[reference]
        draws = delta[indices].sum(axis=1) / 1016
        interval = np.quantile(draws, [.025, .975], method="linear")
        comparisons[reference] = dict(perplexity_ratio=math.exp(float(delta.sum() / 1016)),
            mean_nll_difference=float(delta.sum() / 1016),
            article_perplexity_ratios={rid: math.exp(float(d / 127)) for rid, d in zip(ids, delta)},
            bootstrap_95_percentile_ratio=[math.exp(float(v)) for v in interval],
            descriptive_only=True,
            comparison_scope=("primary adaptive safety check; calibration length and normalization both change"
                              if reference == "fixed16" else
                              "unmatched secondary contrast; calibration length, normalization, and feature rule differ"
                              if reference == "sequential16" else "secondary common control"))
        if reference == "sequential128":
            comparisons[reference]["comparison_scope"] = "prospectively chosen primary; matched tokens, grids, normalization, checkpoint; different feature rules"
    primary = comparisons["fixed16"]
    result = dict(totals=totals, fixed128_comparisons=comparisons,
        development_safety_gate_pass=primary["perplexity_ratio"] <= POLICY["max_aggregate_ratio"]
            and max(primary["article_perplexity_ratios"].values()) <= POLICY["max_each_article_ratio"],
        bootstrap=dict(unit="whole paired article", repetitions=POLICY["bootstrap_repetitions"],
            seed=POLICY["bootstrap_seed"], interval="percentile2.5%,97.5%; linear quantile",
            scope="adaptive reused development articles; no population or confirmation inference"))
    if matched:
        primary = comparisons["sequential128"]
        result["matched_quality_gate_pass"] = (primary["perplexity_ratio"] <= POLICY["max_aggregate_ratio"]
            and max(primary["article_perplexity_ratios"].values()) <= POLICY["max_each_article_ratio"])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    args = parser.parse_args()
    raw = args.plan.read_bytes()
    plan = json.loads(raw)
    root = Path(__file__).resolve().parents[1]
    from src.experiment_inventory import source_hashes
    from src.transaction_timing import verify_command_admission
    matched = plan.get("policy", {}).get("sequential128_available")
    if source_hashes(root) != plan["source_sha256"] or plan.get("policy") != policy_for_mode(matched):
        raise ValueError("source or prospective follow-up policy differs")
    verify_command_admission(plan["protocol_sha256"], "feasibility",
                             [sys.executable, str(Path(__file__).resolve()), str(args.plan.absolute())])
    output = Path(plan["output"])
    if output.exists() and any(output.iterdir()):
        raise ValueError("cannot overwrite follow-up output")
    output.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter_ns()
    result = dict(schema="adaptive-quality-followup-v30", status="running", plan_sha256=digest(raw),
        phases=[], quality={}, parity=[], confirmation=False, scientific_promotion=False,
        adaptive_followup=True, new_evaluation_articles=False, new_exclusions=False,
        matched_sequential128_comparator=matched, nll_is_not_certified_interval=True, policy=plan["policy"])
    def save(phase, **details):
        event = dict(phase=phase, elapsed_ns=time.perf_counter_ns() - start, **details)
        result["phases"].append(event)
        result["peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        atomic_write(output / "progress.json", canonical_json(result))
        print(json.dumps(event), flush=True)
    try:
        save("validate_inputs")
        inputs = plan["inputs"]
        required_extra = {"first_registration", "first_completion", "new_completion", "new_model"}
        if matched:
            required_extra |= {"new_sequential_completion", "new_sequential_model"}
        for entry in inputs.values():
            bound(entry)
        reg = json.loads(bound(inputs["first_registration"]))
        if set(inputs) != set(reg["inputs"]) | required_extra:
            raise ValueError("follow-up input inventory differs")
        old_inputs = {key: inputs[key] for key in reg["inputs"]}
        for key, entry in old_inputs.items():
            if entry["sha256"] != reg["inputs"][key]["sha256"]:
                raise ValueError("archived control binding changed")
            entry.setdefault("bytes", reg["inputs"][key]["bytes"])
        helper = "scripts/run_quality_v30.py"
        if digest((root / helper).read_bytes()) != reg["worker_source_sha256"][helper]:
            raise ValueError("shared evaluator changed since the first quality pilot")
        first_raw, first, first_attempt = verified_terminal(inputs["first_completion"])
        if first["registration_sha256"] != inputs["first_registration"]["sha256"]:
            raise ValueError("first quality registration differs")
        records = validate_reused_articles(reg, first, json.loads(bound(inputs["pools"])))
        result["excluded_from_future_confirmation_ids"] = reg["excluded_from_future_confirmation_ids"]
        new_raw, new, new_attempt = verified_terminal(inputs["new_completion"])
        generation_raw = (new_attempt / "plan.json").read_bytes()
        generation_plan = json.loads(generation_raw)
        if digest(generation_raw) != new["plan_sha256"]:
            raise ValueError("new generation plan changed")
        if source_hashes(new_attempt.parents[1] / "source") != generation_plan["source_sha256"]:
            raise ValueError("new generation source snapshot changed")
        target_raw = (new_attempt / "outputs/fixed-target.json").read_bytes()
        base_raw = (new_attempt / "outputs/base-target.json").read_bytes()
        if (digest(target_raw) != new["fixed_target_sha256"]
                or digest(base_raw) != new["base_target_sha256"]
                or json.loads(target_raw)["anchor_target_sha256"] != new["base_target_sha256"]
                or json.loads(base_raw)["recipe"] != new["target_recipe"]):
            raise ValueError("new generation target manifests differ")
        larger_records_raw = bound(generation_plan["inputs"]["records"])
        larger_records = json.loads(larger_records_raw)
        new_model_raw = bound(inputs["new_model"])
        checkpoint_hashes = {"config.json": inputs["config"]["sha256"],
                             "model.safetensors": inputs["weights"]["sha256"]}
        validate_new_generation(new, generation_plan, larger_records, checkpoint_hashes=checkpoint_hashes,
            model_binding=dict(sha256=digest(new_model_raw), bytes=len(new_model_raw)))
        pool_development = {r["id"]: r["tokens"] for r in json.loads(bound(inputs["pools"]))["development"]}
        if any(r["tokens"] != pool_development[r["id"]][:128] for r in larger_records["records"]):
            raise ValueError("larger calibration tokens differ from the frozen development pool")
        fixed_plan, fixed_progress, fixed_raw = check_generation(old_inputs, "fixed")
        seq_plan, seq_progress, seq_raw = check_generation(old_inputs, "sequential")
        for key, filename in (("config", "config.json"), ("weights", "model.safetensors")):
            if (fixed_plan["inputs"][key]["sha256"] != inputs[key]["sha256"]
                    or seq_plan["checkpoint_sha256"][filename] != inputs[key]["sha256"]
                    or generation_plan["inputs"][key]["sha256"] != inputs[key]["sha256"]):
                raise ValueError("calibrated models use different checkpoints")
        import numpy as np
        from src.checkpoint_adapter import load_gpt2_checkpoint
        from src.compact_state import parse
        from src.runtime_contract import capture_runtime_contract
        fixed16, seq16, fixed128 = parse(fixed_raw), parse(seq_raw), parse(new_model_raw)
        sequential128 = None
        sequential_provenance = None
        if matched:
            seq128_raw, seq128_result, seq128_attempt = verified_terminal(inputs["new_sequential_completion"])
            seq128_plan_raw = (seq128_attempt / "plan.json").read_bytes()
            seq128_plan = json.loads(seq128_plan_raw)
            if (digest(seq128_plan_raw) != seq128_result["plan_sha256"]
                    or source_hashes(seq128_attempt.parents[1] / "source") != seq128_plan["source_sha256"]):
                raise ValueError("matched sequential plan or source snapshot changed")
            if (seq128_result.get("implementation") != plan["policy"]["sequential_implementation"]
                    or seq128_result.get("target_identity_matches_scalar_reference") is not True):
                raise ValueError("matched sequential implementation differs from the prospective policy")
            implementation_raw = (seq128_attempt / "outputs/implementation.json").read_bytes()
            implementation = json.loads(implementation_raw)
            if (digest(implementation_raw) != seq128_result.get("implementation_manifest_sha256")
                    or implementation != seq128_result.get("implementation_manifest")
                    or implementation.get("schema") != "ordered-equivalent-finite-decoder-v30"
                    or implementation.get("global_mutation") is not False
                    or not implementation.get("source_sha256")):
                raise ValueError("matched sequential implementation manifest differs")
            for name, expected in implementation["source_sha256"].items():
                if Path(name).name != name or digest((seq128_attempt.parents[1] / "source/src" / name).read_bytes()) != expected:
                    raise ValueError("matched sequential implementation source differs")
            seq128_records = json.loads(bound(seq128_plan["inputs"]["records"]))
            if seq128_records != larger_records:
                raise ValueError("matched sequential calibration tokens differ")
            seq128_model_raw = bound(inputs["new_sequential_model"])
            validate_sequential_generation(seq128_result, seq128_plan, seq128_records,
                checkpoint_hashes=checkpoint_hashes,
                model_binding=dict(sha256=digest(seq128_model_raw), bytes=len(seq128_model_raw)), fixed_completion=new)
            sequential128 = parse(seq128_model_raw)
            if (sequential128.target_sha256 != seq128_result["sequential_target_sha256"]
                    or len(sequential128.stages) != 24 or sequential128.factors):
                raise ValueError("matched sequential model target or completeness differs")
            sequential_provenance = dict(completion_sha256=digest(seq128_raw), plan_sha256=digest(seq128_plan_raw),
                model_sha256=digest(seq128_model_raw), generation_sources_verified=True,
                implementation_manifest_sha256=digest(implementation_raw), implementation_source_verified=True)
        if (fixed128.target_sha256 != new["fixed_target_sha256"]
                or fixed16.target_sha256 != first["inference"]["model_targets"]["fixed_feature"]
                or seq16.target_sha256 != first["inference"]["model_targets"]["sequential"]
                or any(len(model.stages) != 24 or model.factors for model in (fixed16, seq16, fixed128))):
            raise ValueError("complete calibrated model identities differ")
        for a, b, c in zip(fixed16.stages, seq16.stages, fixed128.stages):
            for other in (b, c):
                if (a.stage_id != other.stage_id or a.shape != other.shape
                        or a.grid_axis != other.grid_axis or a.bits != other.bits
                        or a.bits != 4 or a.scale_values != other.scale_values):
                    raise ValueError("calibrated grids differ")
        if matched:
            for a, b in zip(fixed128.stages, sequential128.stages):
                if (a.stage_id != b.stage_id or a.shape != b.shape or a.bits != b.bits
                        or a.grid_axis != b.grid_axis or a.scale_values != b.scale_values):
                    raise ValueError("matched sequential grid differs")
        loaded = load_gpt2_checkpoint(plan["checkpoint"], identity_encoding="binary64_tree_v2")
        if loaded.provenance["files_sha256"] != checkpoint_hashes:
            raise ValueError("loaded checkpoint differs from registered controls")
        evaluator = NumpyQualityDecoder(loaded.decoder)
        if list(evaluator.weights) != [s.stage_id for s in fixed128.stages]:
            raise ValueError("complete checkpoint stage order differs")
        prefixes = {"full_precision": None,
            "nearest_rounding": nearest_prefix(loaded.decoder, fixed16.stages),
            "fixed16": {s.stage_id: s.array() for s in fixed16.stages},
            "sequential16": {s.stage_id: s.array() for s in seq16.stages},
            "fixed128": {s.stage_id: s.array() for s in fixed128.stages}}
        if matched:
            prefixes["sequential128"] = {s.stage_id: s.array() for s in sequential128.stages}
        runtime_raw = canonical_json(capture_runtime_contract())
        atomic_write(output / "runtime.json", runtime_raw)
        result["artifacts"] = dict(runtime=dict(file="runtime.json", bytes=len(runtime_raw), sha256=digest(runtime_raw)))
        result["model_protocols"] = dict(fixed16=dict(retained_tokens=16, original_normalization=32),
            sequential16=dict(retained_tokens=16, original_normalization=32),
            fixed128=dict(retained_tokens=128, original_normalization=256))
        result["provenance"] = dict(first_registration_sha256=inputs["first_registration"]["sha256"],
            first_completion_sha256=digest(first_raw), new_completion_sha256=digest(new_raw),
            new_model_sha256=digest(new_model_raw), new_plan_sha256=digest(generation_raw),
            new_fixed_target_sha256=digest(target_raw), new_base_target_sha256=digest(base_raw),
            new_generation_sources_verified=True, shared_evaluator_sha256=digest((root / helper).read_bytes()),
            numpy_version=np.__version__)
        if matched:
            result["model_protocols"]["sequential128"] = dict(retained_tokens=128, original_normalization=256)
            result["provenance"]["sequential128"] = sequential_provenance
        save("models_loaded")
        historical = {label: {r["id"]: r for r in first["quality"][old_label]}
                      for label, old_label in OLD_LABELS.items()}
        for i, record in enumerate(records):
            labels = LABELS + (("sequential128",) if matched else ())
            order = labels[i % len(labels):] + labels[:i % len(labels)]
            for label in order:
                save("quality_started", model=label, record_id=record["id"])
                nll = nll_from_logits(evaluator.logits(record["tokens"], prefixes[label]), record["tokens"])
                result["quality"].setdefault(label, []).append(dict(id=record["id"], predictions=127,
                    nll_sum=nll, mean_nll=nll / 127))
                if label in historical:
                    deviation = abs(nll - historical[label][record["id"]]["nll_sum"]) / 127
                    result["parity"].append(dict(id=record["id"], model=label, mean_nll_deviation=deviation))
                    if deviation > POLICY["historical_parity_max_mean_nll_deviation"]:
                        raise ArithmeticError("shared evaluator no longer reproduces the previous quality result")
                save("quality_complete", model=label, record_id=record["id"])
        result["summary"] = summarize(result["quality"], records, matched=matched)
        result.update(status="complete", predictions_per_model=1016,
            development_safety_gate_pass=result["summary"]["development_safety_gate_pass"],
            primary_comparison_control=plan["policy"]["primary_control"],
            primary_observed_win=result["summary"]["fixed128_comparisons"][plan["policy"]["primary_control"]]["perplexity_ratio"] < 1,
            historical_control_parity_pass=True,
            scope=("adaptive matched follow-up on exposed articles; no confirmation or causal token-count claim"
                   if matched else "adaptive follow-up on exposed articles; no matched sequential128, confirmation, or causal token-count claim"))
        if matched:
            result["matched_quality_gate_pass"] = result["summary"]["matched_quality_gate_pass"]
        save("complete")
        terminal = canonical_json(result)
        with (output / "completion.json").open("xb") as stream:
            stream.write(terminal)
            stream.flush()
            os.fsync(stream.fileno())
        print(json.dumps(dict(terminal_sha256=digest(terminal))), flush=True)
    except Exception as exc:
        result.update(status="failed", error_type=type(exc).__name__, error=str(exc))
        save("failed")
        raise


if __name__ == "__main__":
    main()
