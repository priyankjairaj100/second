#!/usr/bin/env python3
"""Read-only artifact analysis; does not execute experiments."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.measured_analysis import analyze_measured_campaign, analyze_measured_sequences
from src.run_store import canonical_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inventory', type=Path)
    parser.add_argument('output_root', type=Path, help='existing campaign output root')
    parser.add_argument('--sequence', action='store_true')
    parser.add_argument('--analysis-group', default='primary')
    args = parser.parse_args()
    analyze = analyze_measured_sequences if args.sequence else analyze_measured_campaign
    result = analyze(args.inventory, args.output_root, analysis_group=args.analysis_group)
    print(canonical_json(result).decode())


if __name__ == '__main__':
    main()
