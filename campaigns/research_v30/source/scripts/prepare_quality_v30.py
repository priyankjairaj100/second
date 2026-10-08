"""Inspect or freeze the eight-article quality pilot without model inference."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.run_store import canonical_json, digest
from scripts.run_quality_v30 import LABELS, select_records


def prepare(root):
    root = Path(root)
    paths = dict(pools="tmp/data/wikitext2/prepared-pools.json",
                 old_evaluation="pilots/v21/quality-records.json",
                 calibration="pilots/v10/wikitext2/preflight-records.json",
                 config="tmp/models/distilgpt2/config.json",
                 weights="tmp/models/distilgpt2/model.safetensors",
                 tokenizer="tmp/models/distilgpt2/tokenizer.json",
                 base_target="pilots/v21/attempt-001/outputs/base-target.json",
                 fixed_target="pilots/v21/attempt-001/outputs/fixed-target.json")
    for label, directory in (("fixed", "pilots/v21/attempt-001"),
                             ("sequential", "pilots/v17/attempt-003")):
        paths.update({label + "_model": directory + "/outputs/model.bin",
                      label + "_progress": directory + "/outputs/progress.json",
                      label + "_receipt": directory + "/worker/result.json",
                      label + "_plan": directory + "/plan.json"})
    inputs = {}
    for name, path in paths.items():
        with (root / path).open("rb") as stream:
            sha = hashlib.file_digest(stream, "sha256").hexdigest()
        inputs[name] = dict(path=path, sha256=sha, bytes=(root / path).stat().st_size)
    old = json.loads((root / paths["old_evaluation"]).read_bytes())
    if inputs["pools"]["sha256"] != old["pool_sha256"]:
        raise ValueError("restored pool differs from historical pool")
    if inputs["tokenizer"]["sha256"] != old["tokenizer_sha256"]:
        raise ValueError("tokenizer differs from historical tokenizer")
    pools = json.loads((root / paths["pools"]).read_bytes())
    records = select_records(pools, old)
    previous = sorted(old["excluded_from_future_confirmation_ids"])
    rng = random.Random(30)
    initial = list(LABELS)
    rng.shuffle(initial)
    orders = [initial[i % 4:] + initial[:i % 4] for i in range(8)]
    source_paths = ("scripts/run_quality_v30.py",)
    return dict(schema="matched-quality-registration-v30", status="prospectively_registered",
        inputs=inputs, records=records, prior_exclusions=previous,
        excluded_from_future_confirmation_ids=sorted(set(previous) | {r["id"] for r in records}),
        labels=list(LABELS), quality_order=orders, order_seed=30,
        selection="next eight eligible validation articles in frozen pilot-order-v1; first128 tokens",
        retained_calibration_id="wikitext2:train:article-row-5326",
        scope="development quality screen of archived four-bit DistilGPT2 variants",
        confirmation=False, scientific_promotion=False, repair_timing=False,
        evaluation_arithmetic="shared NumPy binary64; BLAS reductions differ from certified finite decoder",
        historical_parity_max_mean_nll_deviation=1e-8,
        historical_parity_rule="all four old article/model values pass before any new article inference",
        bootstrap_repetitions=10000, bootstrap_seed=30,
        estimator="sum NLL differences divided by sum predicted tokens; resample whole paired articles",
        gate=dict(max_aggregate_ratio_to_sequential=1.05, max_each_article_ratio=1.20),
        gate_scope="development decision only; no inference from passing the threshold",
        resource_plan=dict(cpu_seconds=300, wall_seconds=420, process_memory_bytes=6 * 2**30,
                           threads=1, total_model_article_evaluations=36,
                           new_predictions_per_model=1016, allocation_admission="single longest logits array 128*50257*8 bytes; conservative process cap is enforced separately",
                           runtime_prediction="not measured; limits are abort ceilings, not completion guarantees"),
        stop_rule="stop on parity, provenance, nonfinite, timeout, or incomplete comparison; no automatic retuning or retry",
        preparation_source_sha256=digest(Path(__file__).read_bytes()),
        worker_source_sha256={p: digest((root / p).read_bytes()) for p in source_paths})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    reg = prepare(root)
    raw = canonical_json(reg)
    if args.freeze:
        path = root / "campaigns/quality_v30/registration.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
    print(json.dumps(dict(status="frozen" if args.freeze else "preview_only", sha256=digest(raw),
        articles=[r["id"] for r in reg["records"]], predictions_per_model=1016,
        old_exclusions=len(reg["prior_exclusions"]), future_exclusions=len(reg["excluded_from_future_confirmation_ids"]),
        resource_plan=reg["resource_plan"])))


if __name__ == "__main__":
    main()
