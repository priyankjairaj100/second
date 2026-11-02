"""Offline byte checks for review components and optionally supplied model inputs.

No download, model load, dataset read, installation, scheduler call or write.
This verifies file commitments only, not provenance, runtime admission or results.
"""
import argparse
import hashlib
import json
from pathlib import Path
import stat


def check(path, expected):
    path = Path(path)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_size != expected['bytes']:
        raise ValueError('Expected a regular file of the declared size: ' + path.name)
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            h.update(block)
    after = path.lstat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError('File changed during verification: ' + path.name)
    if h.hexdigest() != expected['sha256']:
        raise ValueError('SHA256 mismatch: ' + path.name)
    return path.name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--components', type=Path, help='Directory holding the three named ZIPs')
    parser.add_argument('--model-directory', type=Path, help='Optional already-acquired checkpoint/tokenizer files')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / 'MANIFEST.json').read_text())
    actual = {p.name for p in root.iterdir()}
    if actual != set(manifest) | {'MANIFEST.json'}:
        raise ValueError('Unexpected or missing guide component files')
    own = [check(root / name, entry) for name, entry in sorted(manifest.items())]
    inputs = json.loads((root / 'INPUTS.json').read_text())
    components = []
    if args.components:
        components = [check(args.components / name, entry) for name, entry in sorted(inputs['components'].items())]
    model = []
    if args.model_directory:
        model = [check(args.model_directory / name, entry) for name, entry in sorted(inputs['model_files'].items())]
    print(json.dumps(dict(status='byte_checks_passed', guide_files=len(own),
        components=components, model_files=model, network_used=False,
        model_loaded=False, runtime_qualified=False, empirical_result_verified=False,
        full_reproduction_verified=False), sort_keys=True))


if __name__ == '__main__':
    main()
