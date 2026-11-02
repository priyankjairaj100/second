"""Bound worker output extents before writing, including failed attempts.

This bounds only files written through this object on a trusted filesystem.
It neither reserves account capacity nor budgets controllers, logs or compilers.
Every output directory is one-use. Partial writes remain physically present.
"""
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import stat
from src.run_store import canonical_json

STATE_BYTES = 2**30
METADATA_BYTES = 64*2**20
PROGRESS_BYTES = 2**20
PROGRESS_FILES = 512


def require(ok, message):
    if not ok:
        raise ValueError(message)


def safe_name(name):
    require(type(name) is str and name and len(name) < 160, 'Bounded output name required')
    path = PurePosixPath(name)
    require(not path.is_absolute() and str(path) == name
            and all(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', p) for p in path.parts)
            and all(p not in ('.', '..') for p in path.parts), 'Unsafe output name')
    return path


def layout(artifacts, model_bytes):
    require(type(artifacts) in (set, frozenset) and 0 < len(artifacts) <= 20,
            'Exact finite artifact set required')
    require(type(model_bytes) is int and 0 < model_bytes <= STATE_BYTES,
            'Bounded positive model extent required')
    limits = {}
    for name in sorted(artifacts):
        path = safe_name(name)
        require(path.name != 'completion.json' and not path.name.startswith('progress-'),
                'Reserved worker metadata name')
        if path.name == 'model.bin':
            limits[name] = model_bytes
        elif path.name.endswith('state.bin'):
            limits[name] = STATE_BYTES
        else:
            require(path.suffix == '.json', 'Unknown artifact role')
            limits[name] = METADATA_BYTES
    return limits


def allowance(artifacts, model_bytes):
    limits = layout(artifacts, model_bytes)
    return dict(artifact_bytes=sum(limits.values()),
                progress_bytes=PROGRESS_FILES*PROGRESS_BYTES,
                completion_bytes=METADATA_BYTES,
                output_bytes=sum(limits.values())+PROGRESS_FILES*PROGRESS_BYTES+METADATA_BYTES,
                output_files=len(limits)+PROGRESS_FILES+1,
                capacity_reserved=False, whole_chain_storage_bound=False,
                includes_filesystem_allocation_overhead=False)


def inspect_outputs(root, artifacts, model_bytes):
    """Read actual extents; semantic/byte-equality audits remain separate."""
    root = Path(root).absolute()
    limits = layout(artifacts, model_bytes)
    require(root.is_dir() and not any(p.is_symlink() for p in (root, *root.parents)),
            'Nonsymbolic existing output directory required')
    files = {}; progress = []; identities = {}
    allowed_dirs = {str(parent) for name in artifacts for parent in PurePosixPath(name).parents
                    if str(parent) != '.'}
    for path in sorted(root.rglob('*')):
        name = str(path.relative_to(root));entry = path.lstat()
        if stat.S_ISDIR(entry.st_mode):
            require(name in allowed_dirs, 'Unknown output directory')
            continue
        require(stat.S_ISREG(entry.st_mode), 'Nonregular output refused')
        if name in limits:
            maximum = limits[name]
            if path.name == 'model.bin':
                require(entry.st_size == model_bytes, 'Saved model extent differs')
        elif name == 'completion.json':
            maximum = METADATA_BYTES
        else:
            match = re.fullmatch(r'progress-([0-9]{4})\.json', name)
            require(match is not None, 'Unknown output file')
            progress.append(int(match[1]));maximum = PROGRESS_BYTES
        require(entry.st_size <= maximum, 'Saved output exceeds allowance')
        files[name] = dict(bytes=entry.st_size)
        identities[name] = (entry.st_dev,entry.st_ino,entry.st_size,entry.st_mtime_ns,entry.st_ctime_ns)
    require(set(limits) | {'completion.json'} <= set(files), 'Missing complete worker output')
    require(sorted(progress) == list(range(len(progress))) and len(progress) <= PROGRESS_FILES,
            'Progress sequence is incomplete or exceeds its allowance')
    for name, before in identities.items():
        entry = (root/name).lstat()
        require(before == (entry.st_dev,entry.st_ino,entry.st_size,entry.st_mtime_ns,entry.st_ctime_ns),
                'Output changed during extent inspection')
    return dict(status='extent_checked',files=files,output_bytes=sum(e['bytes'] for e in files.values()),
                output_files=len(files),progress_files=len(progress),allowance=allowance(artifacts,model_bytes),
                scientific_correctness_checked=False,capacity_reserved=False)


class Outputs:
    def __init__(self, root, artifacts, model_bytes):
        self.limits = layout(artifacts, model_bytes)
        self.root = Path(root).absolute()
        self.model_bytes = model_bytes
        self.seen = set()
        self.progress_count = 0
        self.poisoned = False
        self.finished = False
        require('..' not in self.root.parts and not any(p.is_symlink() for p in (self.root, *self.root.parents)),
                'Nonsymbolic output directory required')
        # A prior partial or complete directory is never an invitation to resume.
        self.root.mkdir(parents=True, exist_ok=False)

    def _write(self, name, blob, maximum):
        require(not self.finished, 'Worker outputs already finished')
        safe_name(name)
        require(type(blob) is bytes and len(blob) <= maximum, 'Output extent exceeds declared allowance')
        require(name not in self.seen, 'Output name already consumed')
        path = self.root/name
        require(not any(p.is_symlink() for p in (path, *path.parents)), 'Symlink output refused')
        # Mark before I/O, so even a partial failure cannot reuse the same path.
        self.seen.add(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        try:
            view = memoryview(blob)
            offset = 0
            while offset < len(view):
                written = os.write(fd, view[offset:])
                if written <= 0:
                    raise OSError('Output write made no progress')
                offset += written
            os.fsync(fd)
        finally:
            os.close(fd)
        return dict(file=name, bytes=len(blob), sha256=hashlib.sha256(blob).hexdigest())

    def artifact(self, name, blob):
        try:
            require(not self.poisoned, 'A failed writer cannot produce more artifacts')
            require(name in self.limits, 'Unknown declared artifact')
            if PurePosixPath(name).name == 'model.bin':
                require(type(blob) is bytes and len(blob) == self.model_bytes,
                        'Complete matched model extent differs before write')
            return self._write(name, blob, self.limits[name])
        except BaseException:
            self.poisoned = True
            raise

    def progress(self, item):
        try:
            require(not self.poisoned, 'A failed writer cannot produce more progress')
            require(self.progress_count < PROGRESS_FILES, 'Worker progress count exceeded')
            blob = canonical_json(item)
            result = self._write(f'progress-{self.progress_count:04d}.json', blob, PROGRESS_BYTES)
            self.progress_count += 1
            return result
        except BaseException:
            self.poisoned = True
            raise

    def finish(self, result):
        require(type(result) is dict and result.get('status') in ('complete', 'failed'),
                'Explicit complete or failed worker result required')
        complete = result['status'] == 'complete'
        require(result.get('complete_model') is complete, 'Worker status/model flag disagree')
        require(not complete or (not self.poisoned and set(self.limits) <= self.seen),
                'Failed or incomplete outputs cannot be promoted')
        blob = canonical_json(result)
        try:
            saved = self._write('completion.json', blob, METADATA_BYTES)
        finally:
            # A failed completion write is also consumed; never rewrite it.
            self.finished = True
        return saved
