#!/usr/bin/env python3
"""Profile rational endpoint sizes in a standard local runner; no clean latency claim."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.arithmetic_audit import audit_local_run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner', choices=('experiment', 'sequence'))
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--audit-output', type=Path, required=True)
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--sample-every', type=int, default=1024)
    parser.add_argument('--max-attributions', type=int, default=64)
    args = parser.parse_args()
    try:
        report = audit_local_run(args.runner, args.manifest, args.output, args.audit_output,
                                 validate_only=args.validate_only, sample_every=args.sample_every,
                                 max_attributions=args.max_attributions)
    except Exception as exc:
        print(json.dumps({'status': 'failed', 'type': type(exc).__name__, 'message': str(exc)}))
        return 2
    print(json.dumps({'status': report['runner_status'], 'audit_output': str(args.audit_output),
                      'audit_status': report['audit_status'],
                      'constructed_fraction_objects': report['constructed_fraction_endpoints']['fraction_objects'],
                      'clean_latency_eligible': False, 'coverage': report['coverage']}, sort_keys=True))
    return 0 if (report['runner_status'] in ('complete', 'validated') and
                 report['audit_status'] == 'complete_declared_scope') else 1


if __name__ == '__main__':
    raise SystemExit(main())
