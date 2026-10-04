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
    args = parser.parse_args()
    result = run_model_fresh(args.manifest, args.output, validate_only=args.validate_only)
    print(json.dumps({'schema': result['schema'], 'status': result['status'],
                      'outcome': result.get('outcome')}, sort_keys=True))
    return 0 if result.get('outcome', {}).get('status', result['status']) in ('complete', 'validated') else 1


if __name__ == '__main__':
    raise SystemExit(main())
