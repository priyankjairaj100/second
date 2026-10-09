"""Audit restart assets; optionally restore only the pinned DistilGPT2 checkpoint.

This helper performs no model inference, registration, or ledger mutation.
It never changes a historical descriptor or overwrites an existing file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ARCHIVED_ROOT = Path('/workspace/scratch/50cc2e342461/second')
REVISION = '2290a62682d06624634c1f46a6ad5be0f47f38aa'
CHECKPOINT = {
    'config.json': ('4ec5947c1d59fee6212cdf3b0ec1a53eac02092554c5ff0a733488cbd2c64f3a', 762),
    'model.safetensors': ('e1ff18884359fe8beb795a5f414feb85a6ce3d929ad019c0d958c039d2b94a1b', 352824413),
}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def local_path(raw):
    path = Path(raw)
    if path.is_absolute():
        if path.is_relative_to(ROOT):
            return path
        try:
            return ROOT / path.relative_to(ARCHIVED_ROOT)
        except ValueError:
            raise ValueError('external path is outside the archived repository: ' + str(path))
    if '..' in path.parts:
        raise ValueError('parent traversal is not allowed')
    return ROOT / path


def regular_path(path):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('symbolic path is not accepted: ' + str(path))


def restore_checkpoint(timeout=60):
    outcomes = []
    for name, (expected_hash, expected_bytes) in CHECKPOINT.items():
        destination = ROOT / 'tmp/models/distilgpt2' / name
        regular_path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if not destination.is_file() or destination.stat().st_size != expected_bytes or digest(destination) != expected_hash:
                raise ValueError('existing checkpoint differs; preserve it: ' + str(destination))
            outcomes.append({'file': name, 'status': 'already_verified'})
            continue
        url = f'https://huggingface.co/distilbert/distilgpt2/resolve/{REVISION}/{name}'
        fd, temporary = tempfile.mkstemp(prefix='recovery-', suffix='.part', dir=destination.parent)
        total, sha = 0, hashlib.sha256()
        try:
            request = Request(url, headers={'User-Agent': 'calibration-repair-recovery/32'})
            with os.fdopen(fd, 'wb') as output, urlopen(request, timeout=timeout) as response:
                if response.status != 200:
                    raise ValueError('checkpoint response must contain the complete file')
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > expected_bytes:
                        raise ValueError('checkpoint exceeds the exact expected byte count')
                    output.write(chunk)
                    sha.update(chunk)
                output.flush()
                os.fsync(output.fileno())
            if total != expected_bytes or sha.hexdigest() != expected_hash:
                raise ValueError('downloaded checkpoint identity differs')
            # Atomic installation without replacement, even if another process wins.
            os.link(temporary, destination)
            outcomes.append({'file': name, 'status': 'recovered_verified',
                             'sha256': expected_hash, 'bytes': expected_bytes})
        finally:
            Path(temporary).unlink(missing_ok=True)
    return outcomes


def checkpoint_inventory():
    """Check only the direct public checkpoint inputs, without claiming readiness."""
    rows = []
    for name, (expected_hash, expected_bytes) in CHECKPOINT.items():
        path = ROOT / 'tmp/models/distilgpt2' / name
        row = {'path': str(path.relative_to(ROOT)), 'expected_sha256': expected_hash,
               'expected_bytes': expected_bytes}
        try:
            regular_path(path)
            if not path.exists():
                row['status'] = 'missing'
            elif not path.is_file():
                row['status'] = 'not_regular'
            else:
                row['actual_bytes'], row['actual_sha256'] = path.stat().st_size, digest(path)
                row['status'] = 'verified' if (row['actual_bytes'] == expected_bytes and
                    row['actual_sha256'] == expected_hash) else 'mismatch'
        except (OSError, ValueError) as exc:
            row['status'], row['error'] = 'unavailable', str(exc)
        rows.append(row)
    return {'schema': 'checkpoint-recovery-audit-v32', 'root': str(ROOT),
            'checkpoint_verified': all(row['status'] == 'verified' for row in rows),
            'checkpoint_assets': rows, 'historical_assets_audited': False,
            'controller_ready': False, 'neural_execution': False,
            'scope': 'Only direct checkpoint inputs were checked; historical artifacts and controller gates were not checked.'}


def asset_inventory():
    """Describe checkpoint, selected records, and transitive historical inputs.

    The report is not a replacement for the controller's evidence verification.
    It identifies missing bytes without trusting a hash as a correctness proof.
    """
    assets, visited_attempts, metadata_errors = {}, set(), []

    def add(entry, reason):
        if not isinstance(entry, dict) or not {'path', 'sha256'} <= set(entry):
            return
        path = local_path(entry['path'])
        key = str(path.relative_to(ROOT))
        item = assets.setdefault(key, {'path': key, 'expected_sha256': entry['sha256'],
                                      'expected_bytes': entry.get('bytes'), 'required_by': []})
        if item['expected_sha256'] != entry['sha256']:
            raise ValueError('conflicting historical asset hashes: ' + key)
        if entry.get('bytes') is not None:
            if item['expected_bytes'] not in (None, entry['bytes']):
                raise ValueError('conflicting historical asset sizes: ' + key)
            item['expected_bytes'] = entry['bytes']
        if reason not in item['required_by']:
            item['required_by'].append(reason)

    def load(path):
        try:
            return json.loads(path.read_text())
        except (OSError, ValueError) as exc:
            metadata_errors.append({'path': str(path.relative_to(ROOT)), 'error': str(exc)})
            return None

    def attempt(path):
        path = local_path(path)
        if path in visited_attempts:
            return
        visited_attempts.add(path)
        label = str(path.relative_to(ROOT))
        result = load(path / 'outputs/completion.json')
        if result is not None:
            outputs = result.get('artifacts', {})
            if not outputs:
                outputs = {k: result[k + '_artifact'] for k in ('model', 'state')
                           if k + '_artifact' in result}
            for entry in outputs.values():
                add(dict(entry, path=str(path / 'outputs' / entry['file'])), label)
        plan = load(path / 'plan.json')
        if plan is not None:
            for entry in plan.get('inputs', {}).values():
                add(entry, label)

    for name, (sha, size) in CHECKPOINT.items():
        add({'path': 'tmp/models/distilgpt2/' + name, 'sha256': sha, 'bytes': size}, 'independent direct input')
    for corpus in ('wikitext', 'c4'):
        spec = load(ROOT / f'campaigns/independent_requests_v31_ready/{corpus}.spec.json')
        if spec is None:
            continue
        for entry in spec['prerequisite_files'].values():
            add(entry, corpus + ' prerequisite')
        for trial in spec['trials']:
            for entry in trial['plan']['inputs'].values():
                add(entry, trial['id'])
        for external in spec['external_attempts'].values():
            attempt(external['attempt'])
    # Registered pilot verification follows its parents and bound external inputs.
    pilot = ROOT / 'campaigns/compressed_service_v31'
    program = load(pilot / 'program.json')
    if program is not None:
        for external in program['external_attempts'].values():
            attempt(external['attempt'])
        for trial in program['trials']:
            attempt(pilot / 'attempts' / trial['id'])
    for item in assets.values():
        path = ROOT / item['path']
        try:
            regular_path(path)
            if not path.exists():
                item['status'] = 'missing'
            elif not path.is_file():
                item['status'] = 'not_regular'
            else:
                item['actual_bytes'] = path.stat().st_size
                item['actual_sha256'] = digest(path)
                item['status'] = 'verified' if (item['actual_sha256'] == item['expected_sha256'] and
                    item['expected_bytes'] in (None, item['actual_bytes'])) else 'mismatch'
        except (OSError, ValueError) as exc:
            item['status'], item['error'] = 'unavailable', str(exc)
    sys.path.insert(0, str(ROOT))
    from src.runtime_contract import capture_runtime_contract
    from src.experiment_inventory import source_hashes
    registration = load(pilot / 'registration.json')
    current_runtime = capture_runtime_contract()
    runtime_equal = registration is not None and current_runtime == registration['runtime']
    source_equal = program is not None and source_hashes(ROOT) == program['source_sha256']
    rows = [assets[key] for key in sorted(assets)]
    missing = [row for row in rows if row['status'] != 'verified']
    return {'schema': 'asset-recovery-audit-v32', 'root': str(ROOT),
            'archived_root_matches': ROOT == ARCHIVED_ROOT,
            'runtime_matches_registered_v31_pilot': runtime_equal,
            'numerical_sources_match_registered_v31_pilot': source_equal,
            'metadata_errors': metadata_errors, 'assets': rows,
            'checkpoint_verified': all(assets['tmp/models/distilgpt2/' + name]['status'] == 'verified'
                                       for name in CHECKPOINT),
            'historical_assets_audited': True,
            'unavailable_count': len(missing),
            'all_listed_assets_verified': not missing and not metadata_errors,
            'controller_ready': False,
            'controller_ready_reason': 'Full controller verification is still required; this is only an asset inventory.',
            'neural_execution': False, 'historical_evidence_changed': False,
            'scope': 'Selected V31 numerical requests need frozen token JSON and checkpoint bytes; raw corpora and tokenizer are unnecessary. The inventory additionally lists historical plan inputs, which are not all reopened by registration.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch-checkpoint', action='store_true', help='Restore only two pinned, hash-checked public files.')
    parser.add_argument('--checkpoint-only', action='store_true', help='Check only checkpoint inputs; exit 0 when both match.')
    parser.add_argument('--output', type=Path, help='Write a new audit JSON; existing reports are never replaced.')
    args = parser.parse_args()
    downloads = restore_checkpoint() if args.fetch_checkpoint else []
    report = checkpoint_inventory() if args.checkpoint_only else asset_inventory()
    report['downloads'] = downloads
    raw = json.dumps(report, indent=2, sort_keys=True) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x') as stream:
            stream.write(raw)
        print(json.dumps({'report': str(args.output), 'checkpoint_verified': report['checkpoint_verified'],
                          'unavailable_count': report.get('unavailable_count'),
                          'runtime_match': report.get('runtime_matches_registered_v31_pilot'),
                          'source_match': report.get('numerical_sources_match_registered_v31_pilot')}))
    else:
        print(raw, end='')
    verified = report['checkpoint_verified'] if args.checkpoint_only else report['all_listed_assets_verified']
    return 0 if verified else 2


if __name__ == '__main__':
    raise SystemExit(main())
