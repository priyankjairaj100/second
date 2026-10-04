#!/usr/bin/env python3
"""Create deterministic tables from immutable run records. No models are executed."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.result_analysis import analyze_runs


def read_records(path: Path, raw: bytes | None = None) -> list[dict]:
    text = (path.read_bytes() if raw is None else raw).decode("utf-8")
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    value = json.loads(text)
    if isinstance(value, list):
        return value
    if isinstance(value, dict) and "planned_runs" in value:
        return value["planned_runs"]
    if isinstance(value, dict):
        return [value]
    raise ValueError(f"Unsupported record container: {path}")


def save_tables(summary: dict, directory: Path) -> None:
    """Write values without rounding the canonical JSON analysis."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    with (directory / "outcomes.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["configuration_id", "phase", "cache_mode", "method", "outcome", "attempt_count", "total_attempts"])
        for stratum in summary["strata"]:
            for method, stats in sorted(stratum["methods"].items()):
                for outcome, count in sorted(stats["outcomes"].items()):
                    writer.writerow([stratum["configuration_id"], stratum["phase"], stratum["cache_mode"], method, outcome, count, stats["attempts"]])
    with (directory / "paired_requests.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["configuration_id", "phase", "cache_mode", "root_id", "request_id", "repetitions", "pair_outcome", "baseline_median_ns", "candidate_median_ns"])
        for stratum in summary["strata"]:
            for request in stratum["requests"]:
                times = request["median_time_ns"]
                writer.writerow([stratum["configuration_id"], stratum["phase"], stratum["cache_mode"], request["root_id"], request["request_id"], request["repetitions"], request["pair_outcome"], times.get(summary["baseline"], ""), times.get(summary["candidate"], "")])
    lines = ["# Recorded result summary", "", "This table includes all supplied planned attempts.",
             "Speed ratios apply only to pairs with exact completion in every repeat.",
             "The measured boundary appears in each section.", ""]
    if not summary["planned_inventory_supplied"]:
        lines += ["No separate plan was supplied.", "Missing attempts cannot be inferred from the observed records.", ""]
    for stratum in summary["strata"]:
        ratio = stratum["conditional_ratio"]
        interval = ratio["root_interval"]
        estimate = "unavailable" if ratio["estimate"] is None else f'{ratio["estimate"]:.4g}'
        ci = "unavailable" if interval is None else f'[{interval[0]:.4g}, {interval[1]:.4g}]'
        lines += [f'## {stratum["configuration_id"]} / {stratum["phase"]} / {stratum["cache_mode"]}', "",
                  f'Measured boundary: `{stratum["service_boundary"]}`.', "",
                  "| Quantity | Value |", "| --- | ---: |",
                  f'| Planned requests | {stratum["planned_request_count"]} |',
                  f'| Independent root labels | {stratum["independent_root_count"]} |',
                  f'| Eligible requests for conditional ratio | {ratio["eligible_requests"]} |',
                  f'| Conditional {summary["baseline"]}/{summary["candidate"]} ratio | {estimate} |',
                  f'| Root bootstrap interval | {ci} |', "",
                  "| Method | Outcome | Attempts |", "| --- | --- | ---: |"]
        for method, stats in sorted(stratum["methods"].items()):
            for state, count in sorted(stats["outcomes"].items()):
                lines.append(f"| {method} | {state} | {count} |")
        lines.append("")
    (directory / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def save_plots(summary: dict, directory: Path) -> None:
    """Plot actual recorded outcomes and conditional root ratios only."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for index, stratum in enumerate(summary["strata"]):
        methods = sorted(stratum["methods"])
        categories = sorted({key for method in methods for key in stratum["methods"][method]["outcomes"]})
        if methods:
            fig, axis = plt.subplots(figsize=(7, 4))
            bottoms = [0] * len(methods)
            for category in categories:
                counts = [stratum["methods"][method]["outcomes"].get(category, 0) for method in methods]
                axis.bar(methods, counts, bottom=bottoms, label=category)
                bottoms = [left + right for left, right in zip(bottoms, counts)]
            axis.set_ylabel("Planned attempts")
            axis.set_title(f'{stratum["configuration_id"]}: all outcomes')
            axis.legend(fontsize=8)
            fig.tight_layout()
            fig.savefig(directory / f"stratum_{index:03d}_outcomes.png", dpi=180, metadata={"Software": "calibration-analysis-v1"})
            plt.close(fig)
        ratios = stratum["conditional_ratio"]["root_ratios"]
        if ratios:
            fig, axis = plt.subplots(figsize=(7, 4))
            axis.scatter(list(ratios), list(ratios.values()))
            axis.axhline(1.0, color="black", linestyle="--", linewidth=1)
            axis.set_ylabel(f'{summary["baseline"]}/{summary["candidate"]} ratio')
            axis.set_xlabel("Independent root label")
            axis.set_title("Conditional ratios: both methods complete exactly")
            axis.tick_params(axis="x", labelrotation=45)
            fig.tight_layout()
            fig.savefig(directory / f"stratum_{index:03d}_conditional_ratios.png", dpi=180, metadata={"Software": "calibration-analysis-v1"})
            plt.close(fig)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", nargs="+", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--baseline", default="indexed_fresh")
    parser.add_argument("--candidate", default="repair")
    parser.add_argument("--bootstrap-draws", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20261004)
    parser.add_argument("--plots", action="store_true")
    args = parser.parse_args(argv)
    paths = sorted(args.records)
    input_bytes = {path: path.read_bytes() for path in paths}
    records = [record for path in paths for record in read_records(path, input_bytes[path])]
    plan_bytes = args.plan.read_bytes() if args.plan else None
    plan = read_records(args.plan, plan_bytes) if args.plan else None
    summary = analyze_runs(records, planned_runs=plan, baseline=args.baseline, candidate=args.candidate, draws=args.bootstrap_draws, seed=args.seed)
    summary["input_sha256"] = {str(path): hashlib.sha256(input_bytes[path]).hexdigest() for path in paths}
    if args.plan:
        summary["plan_sha256"] = hashlib.sha256(plan_bytes).hexdigest()
    save_tables(summary, args.output)
    if args.plots:
        save_plots(summary, args.output)


if __name__ == "__main__":
    main()
