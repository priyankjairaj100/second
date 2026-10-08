"""Initialize local handoff metadata or package explicitly selected review files.

No model execution, download, protocol authorization, or budget reset occurs here.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.runtime_contract import capture_runtime_contract

DEFAULT_FILES = ('report.json', 'checklist.json', 'runtime.json', 'hardware.json',
                 'dependencies.json', 'notes.md', 'software-tests.txt',
                 'request-analysis.json', 'sequence-analysis.json')
ALLOWED_SUFFIXES = {'.json', '.txt', '.md', '.patch'}
BLOCKED_WORDS = ('token', 'record', 'corpus', 'dataset', 'checkpoint', 'weight',
                 'secret', 'credential', 'password', 'model.safetensors')
MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_TOTAL_BYTES = 100 * 1024 * 1024


def encode(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git_value(*args):
    result = subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True, text=True)
    if result.returncode:
        raise ValueError('Git metadata unavailable: ' + result.stderr.strip())
    return result.stdout.strip()


def initialize(workspace):
    workspace = Path(workspace)
    if workspace.exists() or workspace.is_symlink():
        raise ValueError('Refusing an existing workspace; preserve or choose a new directory')
    # Build all metadata before creating the output directory.
    runtime = capture_runtime_contract()
    program = json.loads((ROOT / 'handoff/program.json').read_text())
    report = json.loads((ROOT / 'handoff/report-template.json').read_text())
    report['git_commit'] = git_value('rev-parse', 'HEAD')
    report['source_dirty'] = bool(git_value('status', '--porcelain', '--untracked-files=no'))
    report['runtime_sha256'] = sha(encode(runtime))
    dependencies = {d.metadata['Name']: d.version for d in importlib.metadata.distributions()
                    if d.metadata.get('Name')}
    memory = None
    if hasattr(os, 'sysconf'):
        try:
            memory = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
        except (ValueError, OSError):
            pass
    affinity = sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None
    hardware = dict(system=platform.system(), kernel=platform.release(), machine=platform.machine(),
                    processor=platform.processor(), logical_cpus=os.cpu_count(), affinity=affinity,
                    host_memory_bytes=memory, container_memory_limit_not_detected=True,
                    free_disk_bytes=shutil.disk_usage(ROOT).free,
                    thread_settings={k: os.environ.get(k) for k in (
                        'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'TOKENIZERS_PARALLELISM')},
                    missing_details=['physical CPU model if processor is empty',
                                     'container or cgroup limits', 'free RAM immediately before runs',
                                     'competing workload and cache policy'],
                    model_execution=False)
    contents = {'runtime.json': encode(runtime), 'hardware.json': encode(hardware),
                'dependencies.json': encode(dependencies), 'report.json': encode(report),
                'checklist.json': encode(program),
                'notes.md': b'# Local empirical notes\n\nNo research experiment has run in this workspace.\n'}
    workspace.mkdir(parents=True, exist_ok=False)
    for name, data in contents.items():
        with (workspace / name).open('xb') as out:
            out.write(data)
    return dict(status='initialized', workspace=str(workspace), cells=len(program['cells']),
                runnable_protocol=False, model_execution=False, budget_reset=False)


def checked_file(workspace, candidate):
    """Require a regular, non-symlink descendant with a permitted report suffix."""
    root = workspace.resolve(strict=True)
    candidate = Path(os.path.abspath(candidate))
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError('Evidence must remain inside the workspace') from exc
    if not relative.parts or any(part.startswith('.') for part in relative.parts):
        raise ValueError('Hidden evidence paths are not allowed')
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('Symlink evidence is not allowed')
    if not candidate.is_file():
        raise ValueError('Evidence must be a regular file')
    if candidate.suffix.lower() not in ALLOWED_SUFFIXES:
        raise ValueError('Only JSON, TXT, MD, and PATCH review files are allowed')
    if any(word in relative.as_posix().lower() for word in BLOCKED_WORDS):
        raise ValueError('Potential input, credential, or model artifact rejected')
    if candidate.stat().st_size > MAX_FILE_BYTES:
        raise ValueError('Review file exceeds 25 MiB; keep raw archives separately')
    return relative, candidate


def pack(workspace, output, evidence=()):
    workspace = Path(workspace).resolve(strict=True)
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError('Refusing an existing bundle')
    report = json.loads((workspace / 'report.json').read_text())
    if report.get('schema') != 'local-empirical-report-v1':
        raise ValueError('Report schema mismatch')
    checklist = json.loads((workspace / 'checklist.json').read_text())
    expected = json.loads((ROOT / 'handoff/program.json').read_text())
    actual_ids = [row['cell_id'] for row in checklist['cells']]
    expected_ids = [row['cell_id'] for row in expected['cells']]
    if sorted(actual_ids) != sorted(expected_ids):
        raise ValueError('Preserve every planned checklist cell exactly once')
    candidates = [workspace / name for name in DEFAULT_FILES if (workspace / name).exists()]
    candidates.extend(Path(p) for p in evidence)
    files = {}
    total = 0
    for candidate in candidates:
        relative, path = checked_file(workspace, candidate)
        name = relative.as_posix()
        if name in files:
            continue
        # Bounded read protects against growth after stat. This is not hostile-process containment.
        with path.open('rb') as stream:
            data = stream.read(MAX_FILE_BYTES + 1)
        if len(data) > MAX_FILE_BYTES:
            raise ValueError('Review file grew beyond 25 MiB')
        total += len(data)
        if total > MAX_TOTAL_BYTES:
            raise ValueError('Review bundle exceeds 100 MiB')
        files[name] = data
    manifest = dict(schema='local-review-bundle-v1', files={
        name: dict(sha256=sha(data), bytes=len(data)) for name, data in sorted(files.items())},
        raw_archive_complete=False, scientific_validation_performed=False,
        content_must_be_reviewed_before_sharing=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(name, data)
        archive.writestr('bundle-manifest.json', encode(manifest))
    return dict(status='packaged', output=str(output), files=len(files), input_bytes=total,
                scientific_validation_performed=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    init = commands.add_parser('init')
    init.add_argument('--workspace', type=Path, required=True)
    bundle = commands.add_parser('pack')
    bundle.add_argument('--workspace', type=Path, required=True)
    bundle.add_argument('--output', type=Path, required=True)
    bundle.add_argument('--evidence', type=Path, action='append', default=[])
    args = parser.parse_args()
    result = initialize(args.workspace) if args.command == 'init' else pack(args.workspace, args.output, args.evidence)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
