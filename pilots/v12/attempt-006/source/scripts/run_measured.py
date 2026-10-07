#!/usr/bin/env python3
"""Measure a complete local transaction with an external immutable receipt."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.transaction_timing import run_measured_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--receipt',type=Path,required=True)
    args = parser.parse_args()
    try:
        result = run_measured_manifest(args.manifest,args.receipt)
    except Exception as exc:
        print(json.dumps({'status':'failed','type':type(exc).__name__,'message':str(exc)}))
        return 2
    print(json.dumps(result,sort_keys=True,allow_nan=False))
    return 0 if result['receipt']['outcome']['status']=='complete' else 1


if __name__=='__main__':
    raise SystemExit(main())
