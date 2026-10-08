#!/usr/bin/env python3
"""Run a frozen four-method complete-transaction comparison."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.measured_comparison import run_measured_comparison
from src.run_store import canonical_json

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan'); parser.add_argument('--output',required=True)
    parser.add_argument('--validate-only',action='store_true')
    parser.add_argument('--inventory'); parser.add_argument('--inventory-run-id')
    args=parser.parse_args()
    result=run_measured_comparison(args.plan,args.output,validate_only=args.validate_only,
        inventory_path=args.inventory,inventory_run_id=args.inventory_run_id)
    print(canonical_json(result).decode())
    return 0 if result.get('status')=='validated' or result.get('outcome',{}).get('status')=='complete' else 1
if __name__=='__main__':
    raise SystemExit(main())
