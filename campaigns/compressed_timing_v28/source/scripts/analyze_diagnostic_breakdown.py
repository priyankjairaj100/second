#!/usr/bin/env python3
"""Verify and decompose an existing diagnostic comparison; executes no worker."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.diagnostic_breakdown import diagnostic_report
from src.run_store import atomic_write,canonical_json

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('comparison',type=Path); parser.add_argument('--output',type=Path)
    args=parser.parse_args(); raw=canonical_json(diagnostic_report(args.comparison))
    if args.output is None: print(raw.decode())
    else: atomic_write(args.output,raw)
    return 0
if __name__=='__main__': raise SystemExit(main())
