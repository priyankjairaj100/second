#!/usr/bin/env python3
"""Execute a frozen local isolated campaign with pause and budget enforcement."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.isolated_inventory import run_isolated_campaign


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    try:
        result = run_isolated_campaign(args.inventory, args.output, validate_only=args.validate_only)
    except Exception as exc:
        print(json.dumps({"status": "failed", "type": type(exc).__name__, "message": str(exc)}))
        return 2
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0 if result.get("status") in ("validated", "complete") and result.get("outcome", "complete") == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
