"""Run the model-output control over local prepared inputs."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.model_fresh import run_model_fresh


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest')
    parser.add_argument('--output', required=True)
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--inventory', type=Path)
    parser.add_argument('--inventory-run-id')
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--sequence-step', type=int)
    parser.add_argument('--execution-mode', choices=('clean','diagnostic'))
    args = parser.parse_args()
    result = run_model_fresh(args.manifest, args.output, validate_only=args.validate_only,
        inventory_path=args.inventory, inventory_run_id=args.inventory_run_id, plan_path=args.plan,
        sequence_step=args.sequence_step, execution_mode=args.execution_mode)
    print(json.dumps({'schema': result['schema'], 'status': result['status'],
                      'outcome': result.get('outcome')}, sort_keys=True))
    return 0 if result.get('outcome', {}).get('status', result['status']) in ('complete', 'validated') else 1


if __name__ == '__main__':
    raise SystemExit(main())
