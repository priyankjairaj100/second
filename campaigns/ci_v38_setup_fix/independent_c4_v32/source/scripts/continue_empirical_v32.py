#!/usr/bin/env python3
"""Run the remaining fourteen registered development transactions, without retries.

The controller verifies the evidence and next trial at every step. This wrapper
changes no policy or budget. Use a new --workspace for a local reproduction.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / 'scripts/launch_independent_requests_v32.py'


def call(corpus, action, workspace):
    command = [sys.executable, str(CONTROLLER), '--corpus', corpus, action]
    if workspace:
        command += ['--workspace', workspace]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        if result.stdout:
            print(result.stdout, end='', flush=True)
        if result.stderr:
            print(result.stderr, end='', file=sys.stderr, flush=True)
        raise RuntimeError('Controller stopped; preserve evidence and do not retry automatically.')
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', help='New local reproduction path, e.g. local_runs/replay-001')
    parser.add_argument('--execute', action='store_true', help='Execute the fixed program; default only reports status.')
    args = parser.parse_args()
    for corpus in ('wikitext', 'c4'):
        status = call(corpus, '--status', args.workspace)
        if not args.execute:
            print(json.dumps(status, sort_keys=True), flush=True)
            continue
        if not status.get('registered'):
            print(json.dumps(call(corpus, '--register', args.workspace), sort_keys=True), flush=True)
        for _ in range(8):
            status = call(corpus, '--status', args.workspace)
            if status.get('blocked'):
                raise RuntimeError('Existing trial is blocked: ' + json.dumps(status['blocked']))
            if status.get('complete'):
                print(json.dumps({'corpus': corpus, 'complete': True,
                    'completed_trials': len(status['completed']),
                    'budget': status['budget']}, sort_keys=True), flush=True)
                break
            outcome = call(corpus, '--run-next', args.workspace)
            print(json.dumps(outcome, sort_keys=True), flush=True)
            if outcome.get('status') != 'complete':
                raise RuntimeError('Trial did not complete; no automatic retry.')
        else:
            raise RuntimeError('Unexpected trial count; no further execution.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
