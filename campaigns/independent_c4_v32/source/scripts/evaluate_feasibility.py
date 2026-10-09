#!/usr/bin/env python3
"""Evaluate existing local archives; never execute a model or accept asserted evidence."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.feasibility_archive import evaluate_archive_feasibility
from src.measured_analysis import load_measured_sequence_evidence
from src.run_store import atomic_write, canonical_json, strict_json


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", default=str(Path(__file__).resolve().parents[1]/"configs/feasibility_gates_v1.json"))
    parser.add_argument("--clean-inventory", required=True)
    parser.add_argument("--clean-output", required=True)
    parser.add_argument("--diagnostic-inventory")
    parser.add_argument("--diagnostic-output")
    parser.add_argument("--output", required=True, help="New report path outside the verified archives")
    args = parser.parse_args(argv)
    if bool(args.diagnostic_inventory) != bool(args.diagnostic_output):
        parser.error("supply both diagnostic inventory and output, or neither")
    def resolved(path):
        value = Path(path).absolute()
        if value.is_symlink() or any(parent.is_symlink() for parent in value.parents):
            raise ValueError("input/report paths must not traverse symbolic links")
        return value.resolve(strict=False)
    output = resolved(args.output)
    for root in (args.clean_output, args.diagnostic_output):
        if root is not None and output.is_relative_to(resolved(root)):
            raise ValueError("the report must be outside immutable input archives")
    policy_path = resolved(args.policy)
    inputs = [policy_path, resolved(args.clean_inventory)]
    if args.diagnostic_inventory is not None:
        inputs.append(resolved(args.diagnostic_inventory))
    if output in inputs:
        raise ValueError("the report must not replace an input policy or inventory")
    policy = strict_json(policy_path.read_bytes())
    clean = load_measured_sequence_evidence(args.clean_inventory, args.clean_output, execution_mode="clean")
    diagnostic = (None if args.diagnostic_inventory is None else
        load_measured_sequence_evidence(args.diagnostic_inventory, args.diagnostic_output, execution_mode="diagnostic"))
    result = evaluate_archive_feasibility(policy, clean, diagnostic)
    raw = canonical_json(result)
    if output.exists():
        if not output.is_file() or output.read_bytes() != raw:
            raise ValueError("refuse to overwrite a different feasibility report")
    else:
        atomic_write(output, raw)
    print(result["decision"])
    # Exit 0 means a report was produced, never that feasibility was established.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
