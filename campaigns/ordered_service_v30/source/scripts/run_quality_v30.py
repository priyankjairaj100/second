"""Matched quality evaluation with a declared NumPy binary64 inference path.

This path evaluates existing model codes. It never constructs calibration
features or changes the finite calibration target. Its BLAS arithmetic differs
from the certified decoder, so a prospective historical NLL check precedes
every new development article. These NLL values have no interval certificate.
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

LABELS = ("full_precision", "nearest_rounding", "fixed_feature", "sequential")
OLD_LABELS = {"fixed_feature": "fixed_anchor_calibrated",
              "sequential": "archived_sequential_calibrated"}


def read_bound(entry):
    path = Path(entry["path"])
    raw = path.read_bytes()
    if len(raw) != entry["bytes"] or digest(raw) != entry["sha256"]:
        raise ValueError("bound input changed: " + str(path))
    return raw


def select_records(pools, old, *, count=8, length=128):
    """Select articles before inference, using the frozen development order."""
    excluded = set(old["excluded_from_future_confirmation_ids"])
    if len(excluded) != 12:
        raise ValueError("the twelve prior exclusions are required")
    reserve = {r["id"] for r in pools["confirmation"]}
    eligible = [r for r in pools["evaluation"]
                if r["id"] not in excluded and len(r["tokens"]) >= length]
    selected = [dict(id=r["id"], tokens=r["tokens"][:length],
                     body_sha256=r["body_sha256"], document_id=r["document_id"])
                for r in eligible[:count]]
    ids = [r["id"] for r in selected]
    if (len(ids) != count or len(set(ids)) != count or set(ids) & reserve
            or any(not rid.startswith("wikitext2:validation:article-row-") for rid in ids)):
        raise ValueError("insufficient distinct development articles")
    return selected


def validate_selection(reg, pools, old):
    expected = select_records(pools, old)
    ids = [r["id"] for r in expected]
    previous = sorted(old["excluded_from_future_confirmation_ids"])
    if (reg["records"] != expected or reg["prior_exclusions"] != previous
            or reg["excluded_from_future_confirmation_ids"] != sorted(set(previous) | set(ids))
            or reg["confirmation"] is not False or reg["scientific_promotion"] is not False):
        raise ValueError("selection or exclusion chain differs")
    if (reg["labels"] != list(LABELS) or len(reg["quality_order"]) != 8
            or any(sorted(order) != sorted(LABELS) for order in reg["quality_order"])):
        raise ValueError("matched four-model order differs")


def paired_summary(quality, record_ids, *, repetitions=10000, seed=30):
    """Resample whole paired articles; never treat tokens as independent units."""
    import numpy as np
    tables = {label: {r["id"]: r for r in quality[label]} for label in LABELS}
    if len(set(record_ids)) != len(record_ids) or not record_ids:
        raise ValueError("distinct article IDs are required")
    if any(set(table) != set(record_ids) or len(quality[label]) != len(record_ids)
           for label, table in tables.items()):
        raise ValueError("the full matched article set is required")
    counts = np.asarray([tables[LABELS[0]][rid]["predictions"] for rid in record_ids], dtype=np.int64)
    if np.any(counts <= 0):
        raise ValueError("positive prediction counts are required")
    for table in tables.values():
        if any(table[rid]["predictions"] != int(n) or not math.isfinite(table[rid]["nll_sum"])
               for rid, n in zip(record_ids, counts)):
            raise ValueError("article counts or finite losses differ")
    losses = {label: np.asarray([table[rid]["nll_sum"] for rid in record_ids])
              for label, table in tables.items()}
    rng = np.random.default_rng(seed)
    sample = rng.integers(0, len(record_ids), size=(repetitions, len(record_ids)))
    sampled_counts = counts[sample].sum(axis=1)
    totals = {label: dict(nll_sum=float(x.sum()), predictions=int(counts.sum()),
                         mean_nll=float(x.sum() / counts.sum()),
                         perplexity=math.exp(float(x.sum() / counts.sum())))
              for label, x in losses.items()}
    comparisons = {}
    for reference in ("sequential", "nearest_rounding", "full_precision"):
        delta = losses["fixed_feature"] - losses[reference]
        aggregate = float(delta.sum() / counts.sum())
        draws = delta[sample].sum(axis=1) / sampled_counts
        interval = np.quantile(draws, [.025, .975], method="linear")
        comparisons[reference] = dict(
            token_weighted_mean_nll_difference=aggregate,
            perplexity_ratio=math.exp(aggregate),
            mean_article_nll_difference=float((delta / counts).mean()),
            article_perplexity_ratios={rid: math.exp(float(d / n))
                                      for rid, d, n in zip(record_ids, delta, counts)},
            paired_article_bootstrap_95_percentile_nll=[float(v) for v in interval],
            paired_article_bootstrap_95_percentile_ratio=[math.exp(float(v)) for v in interval],
            bootstrap_scope="descriptive development sensitivity; no population or confirmation guarantee")
    return dict(totals=totals, fixed_feature_comparisons=comparisons,
                bootstrap=dict(unit="whole paired article", repetitions=repetitions, seed=seed,
                               generator="numpy.default_rng/PCG64", interval="percentile 2.5%,97.5%; linear quantile"))


class NumpyQualityDecoder:
    """Shared inference implementation; no calibration or certificate claims."""
    def __init__(self, base):
        import numpy as np
        from src.ordered_finite import FiniteWeights
        self.np, self.base, self.config = np, base, base.config
        matrix = lambda x: FiniteWeights(x).array()
        self.weights = {k: matrix(v) for k, v in base._float_weights.items()}
        self.embeddings = matrix(base._token_embeddings)
        self.positions = matrix(base._position_embeddings)
        self.head = matrix(base._lm_head)
        self.head_bias = np.asarray(base._lm_head_bias, dtype=np.float64)
        self.blocks = [{k: np.asarray(v, dtype=np.float64) for k, v in block.items()
                        if k.endswith("_bias") or k.endswith("_scale")}
                       for block in base._blocks]
        self.final_scale = np.asarray(base._final_norm_scale, dtype=np.float64)
        self.final_bias = np.asarray(base._final_norm_bias, dtype=np.float64)

    def _norm(self, x, scale, bias):
        np = self.np
        centered = x - x.mean(axis=-1, keepdims=True)
        return (centered / np.sqrt((centered * centered).mean(axis=-1, keepdims=True)
                                  + self.config.layernorm_epsilon)) * scale + bias

    def logits(self, tokens, prefix=None):
        np, cfg = self.np, self.config
        tokens = self.base._tokens(tokens)
        prefix = {} if prefix is None else prefix
        if set(prefix) - set(self.weights):
            raise ValueError("unknown installed stage")
        for stage, array in prefix.items():
            if (type(array) is not np.ndarray or array.dtype != np.float64
                    or array.shape != self.weights[stage].shape or not np.isfinite(array).all()):
                raise ValueError("installed matrix differs from declared shape")
        n, d, heads = len(tokens), cfg.model_width, cfg.head_count
        hd = d // heads
        x = self.embeddings[list(tokens)] + self.positions[:n]
        mask = np.triu(np.ones((n, n), dtype=bool), k=1)
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            for index, block in enumerate(self.blocks):
                stem = f"block.{index:04d}."
                def linear(value, name):
                    stage = stem + name
                    return value @ prefix.get(stage, self.weights[stage]).T + block[name + "_bias"]
                norm = self._norm(x, block["norm1_scale"], block["norm1_bias"])
                qkv = linear(norm, "qkv")
                q, k, v = [part.reshape(n, heads, hd).transpose(1, 0, 2)
                           for part in np.split(qkv, 3, axis=1)]
                score = q @ k.transpose(0, 2, 1) / math.sqrt(hd)
                score[:, mask] = -np.inf
                score -= score.max(axis=-1, keepdims=True)
                prob = np.exp(score)
                prob /= prob.sum(axis=-1, keepdims=True)
                mixed = (prob @ v).transpose(1, 0, 2).reshape(n, d)
                x = x + linear(mixed, "attn_out")
                norm = self._norm(x, block["norm2_scale"], block["norm2_bias"])
                up = linear(norm, "mlp_up")
                if cfg.activation == "gelu_new":
                    c = float.fromhex("0x1.9884533d43651p-1")
                    activated = (0.5 * up) * (1 + np.tanh(c * (up + ((0.044715 * up) * up) * up)))
                elif cfg.activation == "gelu":
                    from scipy.special import erf
                    activated = (0.5 * up) * (1 + erf(up / math.sqrt(2)))
                else:
                    raise ValueError("unsupported activation")
                x = x + linear(activated, "mlp_down")
            x = self._norm(x, self.final_scale, self.final_bias)
            logits = x @ self.head.T + self.head_bias
        if not np.isfinite(logits).all():
            raise ArithmeticError("nonfinite quality logits")
        return logits


def nll_from_logits(logits, tokens):
    import numpy as np
    rows = np.asarray(logits, dtype=np.float64)
    if (rows.ndim != 2 or rows.shape[0] != len(tokens) or len(tokens) < 2
            or any(type(t) is not int or not 0 <= t < rows.shape[1] for t in tokens)
            or not np.isfinite(rows).all()):
        raise ValueError("invalid matched likelihood inputs")
    rows = rows[:-1]
    maximum = rows.max(axis=1)
    logsum = maximum + np.log(np.exp(rows - maximum[:, None]).sum(axis=1))
    terms = logsum - rows[np.arange(len(tokens) - 1), tokens[1:]]
    value = float(terms.sum())
    if not math.isfinite(value):
        raise ArithmeticError("nonfinite likelihood")
    return value


def nearest_prefix(base, stages):
    import numpy as np
    from src.ordered_finite import FiniteWeights
    result = {}
    for stage in stages:
        weights = FiniteWeights(base._float_weights[stage.stage_id]).array()
        scale = np.asarray(stage.scale_values, dtype=np.float64)[:, None]
        half = 1 << (stage.bits - 1)
        indices = np.zeros(weights.shape, dtype=np.uint8)
        # Strict comparison selects the lower cell at an exact midpoint.
        for code in range(-half, half - 1):
            indices += weights > scale * (code + 0.5)
        result[stage.stage_id] = (indices.astype(np.float64) - half) * scale
    return result


def check_generation(inputs, prefix):
    plan_raw = read_bound(inputs[prefix + "_plan"])
    progress = json.loads(read_bound(inputs[prefix + "_progress"]))
    receipt = json.loads(read_bound(inputs[prefix + "_receipt"]))
    model_raw = read_bound(inputs[prefix + "_model"])
    if (progress.get("status") != "complete" or receipt.get("status") != "complete"
            or receipt.get("outcome", {}).get("status") != "complete"
            or receipt.get("outcome", {}).get("returncode") != 0
            or receipt.get("budget_debit", {}).get("state") != "settled"
            or progress.get("plan_sha256") != digest(plan_raw)
            or receipt.get("worker_identity", {}).get("plan_sha256") != digest(plan_raw)
            or progress.get("model_artifact", {}).get("sha256") != digest(model_raw)
            or progress.get("model_artifact", {}).get("bytes") != len(model_raw)):
        raise ValueError("generation provenance differs: " + prefix)
    return json.loads(plan_raw), progress, model_raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    args = parser.parse_args()
    raw = args.plan.read_bytes()
    plan = json.loads(raw)
    root = Path(__file__).resolve().parents[1]
    from src.experiment_inventory import source_hashes
    from src.transaction_timing import verify_command_admission
    if source_hashes(root) != plan["source_sha256"]:
        raise ValueError("source snapshot differs")
    verify_command_admission(plan["protocol_sha256"], "feasibility",
                             [sys.executable, str(Path(__file__).resolve()), str(args.plan.absolute())])
    reg_raw = read_bound(plan["registration"])
    reg = json.loads(reg_raw)
    if reg["schema"] != "matched-quality-registration-v30" or reg["status"] != "prospectively_registered":
        raise ValueError("invalid registration")
    output = Path(plan["output"])
    output.mkdir(parents=True, exist_ok=True)
    if (output / "completion.json").exists() or (output / "progress.json").exists():
        raise ValueError("cannot overwrite quality evidence")
    tick = time.perf_counter_ns()
    result = dict(schema="matched-quality-v30", status="running", plan_sha256=digest(raw),
                  registration_sha256=digest(reg_raw), confirmation=False, scientific_promotion=False,
                  calibration_target_changed=False, evaluation_arithmetic_changed=True,
                  nll_is_not_certified_interval=True, phases=[], quality={}, historical_parity=[])
    def save(phase, **details):
        event = dict(phase=phase, elapsed_ns=time.perf_counter_ns() - tick, **details)
        result["phases"].append(event)
        result["peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        atomic_write(output / "progress.json", canonical_json(result))
        print(json.dumps(event), flush=True)
    try:
        save("validate_inputs")
        inputs = plan["inputs"]
        if set(inputs) != set(reg["inputs"]):
            raise ValueError("input inventory differs")
        for key, entry in inputs.items():
            if any(entry[k] != reg["inputs"][key][k] for k in ("sha256", "bytes")):
                raise ValueError("registered input binding differs")
            read_bound(entry)
        for path, expected in reg["worker_source_sha256"].items():
            if digest((root / path).read_bytes()) != expected:
                raise ValueError("registered quality source differs")
        pools = json.loads(read_bound(inputs["pools"]))
        old = json.loads(read_bound(inputs["old_evaluation"]))
        validate_selection(reg, pools, old)
        fp, history, fixed_raw = check_generation(inputs, "fixed")
        sp, sequential_progress, seq_raw = check_generation(inputs, "sequential")
        calibration_raw = read_bound(inputs["calibration"])
        calibration = json.loads(calibration_raw)["records"]
        if (sp["records_sha256"] != digest(calibration_raw)
                or fp["program"]["record_id"] != reg["retained_calibration_id"]
                or fp["inputs"]["records"]["sha256"] != digest(calibration_raw)
                or sequential_progress["committed_record_ids"] != [reg["retained_calibration_id"]]
                or len(calibration) != 2 or any(len(r["tokens"]) != 16 for r in calibration)
                or sp["checkpoint_sha256"]["model.safetensors"] != inputs["weights"]["sha256"]
                or fp["inputs"]["weights"]["sha256"] != inputs["weights"]["sha256"]
                or sp["checkpoint_sha256"]["config.json"] != inputs["config"]["sha256"]
                or fp["inputs"]["config"]["sha256"] != inputs["config"]["sha256"]):
            raise ValueError("calibration or checkpoint controls differ")
        import numpy as np
        from src.checkpoint_adapter import load_gpt2_checkpoint
        from src.compact_state import parse
        from src.runtime_contract import capture_runtime_contract
        fixed, sequential = parse(fixed_raw), parse(seq_raw)
        base_target = json.loads(read_bound(inputs["base_target"]))
        fixed_target = json.loads(read_bound(inputs["fixed_target"]))
        if (fixed.target_sha256 != digest(read_bound(inputs["fixed_target"]))
                or fixed_target["anchor_target_sha256"] != digest(read_bound(inputs["base_target"]))
                or sequential.target_sha256 != sequential_progress["target_sha256"]
                or fixed.target_sha256 == sequential.target_sha256
                or fixed.factors or sequential.factors
                or history.get("complete_new_target_model") is not True
                or sequential_progress.get("complete_model") is not True
                or len(base_target["stages"]) != 24
                or len(fixed.stages) != 24 or len(sequential.stages) != 24):
            raise ValueError("incomplete or incorrectly identified model")
        for left, right, target in zip(fixed.stages, sequential.stages, base_target["stages"]):
            if (left.stage_id != right.stage_id or left.stage_id != target["stage_id"]
                    or left.shape != right.shape or list(left.shape) != target["shape"]
                    or left.scale_values != right.scale_values
                    or [v.hex() for v in left.scale_values] != target["row_scale_hex"]
                    or left.bits != right.bits or left.bits != 4):
                raise ValueError("quantized models use different grids")
        loaded = load_gpt2_checkpoint(plan["checkpoint"], identity_encoding="binary64_tree_v2")
        if loaded.provenance["files_sha256"] != {
                "config.json": inputs["config"]["sha256"],
                "model.safetensors": inputs["weights"]["sha256"]}:
            raise ValueError("loaded checkpoint differs from bound input files")
        evaluator = NumpyQualityDecoder(loaded.decoder)
        if set(evaluator.weights) != {stage.stage_id for stage in fixed.stages}:
            raise ValueError("calibrated stages differ from loaded checkpoint")
        prefixes = {"full_precision": None,
                    "nearest_rounding": nearest_prefix(loaded.decoder, fixed.stages),
                    "fixed_feature": {s.stage_id: s.array() for s in fixed.stages},
                    "sequential": {s.stage_id: s.array() for s in sequential.stages}}
        runtime = capture_runtime_contract()
        runtime_raw = canonical_json(runtime)
        atomic_write(output / "runtime.json", runtime_raw)
        result["artifacts"] = dict(runtime=dict(file="runtime.json", bytes=len(runtime_raw),
                                                sha256=digest(runtime_raw)))
        result["inference"] = dict(implementation="NumPy binary64 BLAS and NumPy nonlinear operations",
                                   numpy_version=np.__version__, shared_by=list(LABELS),
                                   finite_schedule_equivalence=False,
                                   model_targets=dict(fixed_feature=fixed.target_sha256,
                                                      sequential=sequential.target_sha256))
        result["excluded_from_future_confirmation_ids"] = reg["excluded_from_future_confirmation_ids"]
        save("models_loaded")
        # This check uses only the two previously evaluated articles.
        for record in old["records"]:
            for label, old_label in OLD_LABELS.items():
                expected = next(r for r in history["quality"][old_label] if r["id"] == record["id"])
                if expected["predictions"] != len(record["tokens"]) - 1 or not math.isfinite(expected["nll_sum"]):
                    raise ValueError("historical prediction count or loss differs")
                measured = nll_from_logits(evaluator.logits(record["tokens"], prefixes[label]), record["tokens"])
                deviation = abs(measured - expected["nll_sum"]) / expected["predictions"]
                result["historical_parity"].append(dict(id=record["id"], model=label,
                    old_nll_sum=expected["nll_sum"], new_nll_sum=measured,
                    absolute_mean_nll_deviation=deviation))
                save("historical_parity_record", model=label, record_id=record["id"], deviation=deviation)
                if deviation > reg["historical_parity_max_mean_nll_deviation"]:
                    raise ArithmeticError("historical parity gate failed before new articles")
        result["historical_parity_pass"] = True
        for record, order in zip(reg["records"], reg["quality_order"]):
            for label in order:
                start = time.perf_counter_ns()
                save("quality_started", model=label, record_id=record["id"])
                nll = nll_from_logits(evaluator.logits(record["tokens"], prefixes[label]), record["tokens"])
                predictions = len(record["tokens"]) - 1
                result["quality"].setdefault(label, []).append(dict(id=record["id"], nll_sum=nll,
                    mean_nll=nll / predictions, predictions=predictions,
                    elapsed_ns=time.perf_counter_ns() - start))
                save("quality_complete", model=label, record_id=record["id"])
        result["summary"] = paired_summary(result["quality"], [r["id"] for r in reg["records"]],
                                           repetitions=reg["bootstrap_repetitions"], seed=reg["bootstrap_seed"])
        primary = result["summary"]["fixed_feature_comparisons"]["sequential"]
        result["development_quality_gate_pass"] = (
            primary["perplexity_ratio"] <= reg["gate"]["max_aggregate_ratio_to_sequential"]
            and max(primary["article_perplexity_ratios"].values()) <= reg["gate"]["max_each_article_ratio"])
        result["primary_observed_win"] = primary["perplexity_ratio"] < 1
        result["predictions_per_model"] = 8 * 127
        result.update(status="complete", scope="eight development articles; no confirmation or population claim")
        save("complete")
        complete = canonical_json(result)
        with (output / "completion.json").open("xb") as stream:
            stream.write(complete)
            stream.flush()
            os.fsync(stream.fileno())
        print(json.dumps({"terminal_sha256": digest(complete)}), flush=True)
    except Exception as exc:
        result.update(status="failed", error_type=type(exc).__name__, error=str(exc))
        save("failed")
        raise


if __name__ == "__main__":
    main()
