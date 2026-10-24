"""Read installed GPU-runtime notice/metadata files; no model or CUDA imports.

This reporting observer is outside every numerical registration. It neither
changes an installation nor establishes a historical binary/notice binding.
Run with the already observed Python 3.10 interpreter; stdout is a bounded tar.
"""
from pathlib import Path
from email.parser import BytesParser
import datetime
import base64
import csv
import hashlib
import io
import json
import os
import resource
import signal
import sys
import tarfile
import time

resource.setrlimit(resource.RLIMIT_CPU, (30, 31))
resource.setrlimit(resource.RLIMIT_AS, (512 * 2**20, 512 * 2**20))
signal.alarm(60)
from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

BASE = Path('/nfs_home/software/envs/pytorch-12.8')
SITE = BASE / 'lib/python3.10/site-packages'
assert sys.version_info[:3] == (3, 10, 19)
assert Path(sys.executable).resolve() == (BASE / 'bin/python3.10').resolve()
assert sys.platform == 'linux'
started = time.process_time()
files = {}
inspected_bytes = 0


def info(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def read(path):
    global inspected_bytes
    assert path.is_relative_to(BASE)
    assert not any(p.is_symlink() for p in (path, *path.parents))
    before = path.stat()
    assert path.is_file() and before.st_size <= 4 * 2**20
    raw = path.read_bytes()
    after = path.stat()
    assert (before.st_size, before.st_mtime_ns, before.st_ino) == (
        after.st_size, after.st_mtime_ns, after.st_ino)
    raw.decode('utf-8')
    inspected_bytes += len(raw)
    assert inspected_bytes <= 32 * 2**20
    return raw


distributions = {}
directories = sorted(SITE.glob('*.dist-info')) + sorted(SITE.glob('*.egg-info'))
assert len(directories) <= 100
for directory in directories:
    assert directory.is_dir() and not directory.is_symlink()
    metadata_file = directory / ('METADATA' if directory.suffix == '.dist-info' else 'PKG-INFO')
    raw = read(metadata_file)
    metadata = BytesParser().parsebytes(raw)
    name = canonicalize_name(metadata['Name'])
    assert name and name not in distributions
    distributions[name] = (directory, metadata, raw, metadata_file.name)

environment = default_environment()
environment['extra'] = ''
assert environment['python_full_version'] == '3.10.19'
assert environment['platform_system'] == 'Linux'
assert environment['platform_machine'] == 'x86_64'
pending = {'torch', 'numpy'}
selected = {}
edges = []
while pending:
    name = min(pending)
    pending.remove(name)
    if name in selected:
        continue
    assert name in distributions, 'Required distribution missing: ' + name
    directory, metadata, raw, metadata_name = distributions[name]
    version = metadata['Version']
    selected[name] = {
        'version': version, 'directory': str(directory.relative_to(BASE)),
        'requires_dist': metadata.get_all('Requires-Dist', []), 'files': {},
        'notice_files_found': 0,
    }
    for requirement_text in metadata.get_all('Requires-Dist', []):
        requirement = Requirement(requirement_text)
        assert not requirement.url, 'Direct dependency URL needs separate review'
        target = canonicalize_name(requirement.name)
        active = requirement.marker is None or requirement.marker.evaluate(environment)
        edge = {'from': name, 'requirement': requirement_text, 'target': target,
                'active_without_extras': active}
        if active:
            assert not requirement.extras, 'Transitive extras need explicit resolution'
            assert target in distributions, 'Active dependency missing: ' + target
            installed = distributions[target][1]['Version']
            assert requirement.specifier.contains(installed, prereleases=True)
            edge['installed_version'] = installed
            pending.add(target)
        edges.append(edge)
    candidates = []
    for parent, dirs, names in os.walk(directory, followlinks=False):
        assert not any((Path(parent) / d).is_symlink() for d in dirs)
        for filename in names:
            path = Path(parent) / filename
            relative = path.relative_to(directory)
            is_notice = any(p.lower() in ('license', 'licenses') for p in relative.parts[:-1])
            is_notice |= path.name.lower().startswith(('license', 'copying', 'notice', 'authors'))
            if is_notice:
                candidates.append(path)
    assert len(candidates) <= 100
    record_entries = {}
    record_file = directory / 'RECORD'
    if record_file.is_file():
        record_raw = read(record_file)
        rows = list(csv.reader(record_raw.decode('utf-8').splitlines()))
        assert len(rows) <= 20000 and all(len(row) == 3 for row in rows)
        for relative_name, digest, length in rows:
            parts = Path(relative_name).parts
            notice_name = Path(relative_name).name.lower().startswith(('license', 'licence', 'copying', 'notice', 'authors', 'eula'))
            if not notice_name:
                continue
            path = SITE / relative_name
            assert not path.is_absolute() or path.is_relative_to(BASE)
            assert not any(p.is_symlink() for p in (path, *path.parents))
            path = path.resolve()
            assert path.is_relative_to(BASE), 'Notice outside the observed installation'
            assert digest.startswith('sha256=') and length.isdigit()
            content = read(path)
            expected = base64.urlsafe_b64decode(digest[7:] + '=' * (-len(digest[7:]) % 4)).hex()
            assert info(content) == {'bytes': int(length), 'sha256': expected}
            candidates.append(path)
            record_entries[str(path.relative_to(BASE))] = info(content)
        selected[name]['record_commitment'] = info(record_raw)
        selected[name]['record_notice_entries_verified'] = record_entries
    candidates = sorted(set(candidates))
    selected[name]['notice_files_found'] = len(candidates)
    candidates += [directory / metadata_name]
    if (directory / 'WHEEL').is_file():
        candidates.append(directory / 'WHEEL')
    for path in sorted(set(candidates)):
        if path.is_relative_to(directory):
            key = 'distributions/' + directory.name + '/' + str(path.relative_to(directory))
        else:
            key = 'installation-notices/' + str(path.relative_to(BASE))
        content = raw if path.name == metadata_name else read(path)
        assert key not in files or files[key] == content
        files[key] = content
        selected[name]['files'][key] = info(content)
    assert len(files) <= 500

assert selected['torch']['version'] == '2.10.0+cu128'
assert selected['numpy']['version'] == '2.2.6'
python_notice = read(BASE / 'lib/python3.10/LICENSE.txt')
files['python/LICENSE.txt'] = python_notice
inventory = {
    'schema': 'installed-cuda-notice-observation-v71',
    'captured_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'interpreter': sys.version, 'installation': str(BASE),
    'collector_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'selection': 'Installed torch and numpy; recursively active Requires-Dist without extras',
    'marker_environment': environment,
    'marker_parser': {'name': 'packaging', 'version': distributions['packaging'][1]['Version']},
    'distributions': selected, 'dependency_edges': edges,
    'python_notice': info(python_notice),
    'files': {name: info(raw) for name, raw in sorted(files.items())},
    'inspected_text_bytes': inspected_bytes,
    'observer_process_cpu_seconds': time.process_time() - started,
    'declared_dependency_versions_satisfied': True,
    'historical_binary_notice_binding_verified': False,
    'complete_transitive_system_notices': False,
    'numerical_result': False, 'gpu_initialized': False, 'model_or_data_read': False,
    'packages_installed': False, 'project_license_assigned': False,
    'scope': 'Current notice/metadata observation on the login host shared installation; '
             'not a GPU-node loaded-library inventory, dependency execution trace, '
             'license clearance, or proof of installed-wheel/source equivalence.',
}
files['inventory.json'] = (json.dumps(inventory, sort_keys=True, indent=2) + '\n').encode()
assert sum(map(len, files.values())) <= 32 * 2**20
with tarfile.open(fileobj=sys.stdout.buffer, mode='w|gz') as archive:
    for name, raw in sorted(files.items()):
        entry = tarfile.TarInfo(name)
        entry.mode = 0o644
        entry.size = len(raw)
        archive.addfile(entry, io.BytesIO(raw))
