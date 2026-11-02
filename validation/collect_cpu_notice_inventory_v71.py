"""Read installed CPU distribution metadata/notices, without importing packages.

This is a bounded reporting observer, not an experiment or a claim of complete
native dependency/source correspondence. Native binary bodies are not read.
"""
from pathlib import Path
from email.parser import BytesParser
import base64
import csv
import datetime
import hashlib
import io
import json
import resource
import signal
import sys
import tarfile

resource.setrlimit(resource.RLIMIT_CPU, (30, 31))
resource.setrlimit(resource.RLIMIT_AS, (512 * 2**20, 512 * 2**20))
signal.alarm(60)
ROOT = Path('/nfs_home/users/poonam/second-20261010')
SITE = ROOT / '.venv-container/lib/python3.12/site-packages'
RUN = ROOT / 'local_runs/untouched-quality-v71-20261018-a'
REG = '3ec767a20be59ed81330d68a067166bc14a369e967d9d3cbf274166baa32c56c'
BASES = {name: SITE / (name + '-' + version + '.dist-info') for name, version in
         [('numpy', '2.3.5'), ('gmpy2', '2.3.2'), ('tokenizers', '0.23.2')]}
BASES['zstandard'] = ROOT / 'local_runs/lossless-control-v63-20261016-a/deps/zstandard-0.25.0.dist-info'
files = {}
read_bytes = 0


def info(raw):
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def read(path):
    global read_bytes
    assert path.is_relative_to(ROOT)
    assert not any(p.is_symlink() for p in (path, *path.parents))
    before = path.stat()
    assert path.is_file() and before.st_size <= 2 * 2**20
    raw = path.read_bytes()
    after = path.stat()
    assert (before.st_size, before.st_mtime_ns, before.st_ino) == (after.st_size, after.st_mtime_ns, after.st_ino)
    raw.decode('utf-8')
    read_bytes += len(raw)
    assert read_bytes <= 8 * 2**20
    return raw


def decode_entry(digest, length):
    assert digest.startswith('sha256=') and length.isdigit()
    return dict(bytes=int(length), sha256=base64.urlsafe_b64decode(digest[7:] + '=' * (-len(digest[7:]) % 4)).hex())


reg_raw = read(RUN / 'program.json')
assert info(reg_raw)['sha256'] == REG
program = json.loads(reg_raw)
pinned = {}


def gather(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key.startswith(str(ROOT) + '/') and isinstance(item, dict) and {'bytes', 'sha256'} <= set(item):
                pin = {k: item[k] for k in ('bytes', 'sha256')}
                assert key not in pinned or pinned[key] == pin
                pinned[key] = pin
            else:
                gather(item)
    elif isinstance(value, list):
        for item in value:
            gather(item)


gather(program['dependency_files'])
gather(program['runtimes']['cpu'])
packages = {}
for name, directory in sorted(BASES.items()):
    metadata = read(directory / 'METADATA')
    parsed = BytesParser().parsebytes(metadata)
    assert parsed['Name'].lower() == name
    record = read(directory / 'RECORD')
    rows = list(csv.reader(record.decode().splitlines()))
    assert len(rows) <= 10000 and all(len(row) == 3 for row in rows)
    assert len({row[0] for row in rows}) == len(rows)
    inventory = dict(version=parsed['Version'], directory=str(directory), native_entries={},
                     installed_notice_entries={}, record_matches_registered_files={}, metadata_pinned=False,
                     actual_text_files_match_registered={}, unhashed_registered_record_entries=[])
    if str(directory / 'METADATA') in pinned:
        assert info(metadata) == pinned[str(directory / 'METADATA')]
        inventory['metadata_pinned'] = True
    for basename, raw in [('METADATA', metadata), ('RECORD', record), ('WHEEL', read(directory / 'WHEEL'))]:
        files[name + '/' + basename] = raw
        if str(directory / basename) in pinned:
            assert info(raw) == pinned[str(directory / basename)]
            inventory['actual_text_files_match_registered'][basename] = info(raw)
    for relative_name, digest, length in rows:
        assert not Path(relative_name).is_absolute()
        target = directory.parent / relative_name
        assert not any(p.is_symlink() for p in (target, *target.parents))
        target = target.resolve()
        assert target.is_relative_to(ROOT)
        native = '.so' in target.name
        notice = target.name.lower().startswith(('license', 'licence', 'copying', 'notice', 'authors', 'eula'))
        if native:
            inventory['native_entries'][relative_name] = decode_entry(digest, length)
        if str(target) in pinned:
            if not digest and not length:
                assert target == directory / 'RECORD', 'Unexpected unhashed registered entry: ' + relative_name
                assert info(record) == pinned[str(target)]
                inventory['unhashed_registered_record_entries'].append(relative_name)
            else:
                item = decode_entry(digest, length)
                assert item == pinned[str(target)]
                inventory['record_matches_registered_files'][relative_name] = item
        if notice:
            item = decode_entry(digest, length)
            raw = read(target)
            assert info(raw) == item
            key = name + '/notices/' + str(target.relative_to(directory.parent))
            files[key] = raw
            inventory['installed_notice_entries'][relative_name] = dict(file=key, **item)
    packages[name] = inventory
assert len(files) <= 100
collection = dict(schema='cpu-installed-notice-inventory-v71',
    captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    collector_sha256=info(Path(__file__).read_bytes())['sha256'], registration_sha256=REG,
    packages=packages, files={n: info(b) for n, b in sorted(files.items())},
    total_text_bytes=sum(map(len, files.values())), binary_bodies_read=False,
    package_runtime_imported=False, model_or_corpus_read=False, new_job=False,
    all_native_notices_complete=False, rust_dependency_graph_verified=False,
    original_wheel_or_build_source_verified=False, historical_record_observation=False,
    scope='Current installed metadata and RECORD-declared native entries only. '
          'Matching RECORD digests to registered hashes is not binary reinspection, '
          'historical wheel provenance, full native dependency closure or redistribution clearance.')
files['collection.json'] = (json.dumps(collection, indent=2, sort_keys=True) + '\n').encode()
with tarfile.open(fileobj=sys.stdout.buffer, mode='w|gz') as archive:
    for name, raw in sorted(files.items()):
        entry = tarfile.TarInfo(name)
        entry.mode = 0o600
        entry.size = len(raw)
        archive.addfile(entry, io.BytesIO(raw))
