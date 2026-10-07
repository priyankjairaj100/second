"""Capture or verify the declared local runtime without loading model inputs."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.runtime_contract import capture_runtime_contract, verify_runtime_contract
from src.run_store import atomic_write, canonical_json, strict_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--capture', type=Path)
    choice.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.capture is not None:
        if args.capture.exists() or args.capture.is_symlink():
            raise ValueError('runtime capture refuses an existing output')
        atomic_write(args.capture, canonical_json(capture_runtime_contract()))
        print('runtime contract captured')
    else:
        verify_runtime_contract(strict_json(args.verify.read_bytes()))
        print('runtime contract matches')


if __name__ == '__main__':
    main()
