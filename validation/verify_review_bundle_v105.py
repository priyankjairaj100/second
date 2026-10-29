"""Offline byte and source-coverage checks; no experiment or external access."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import sys
import zipfile


def identity(blob):
    return dict(bytes=len(blob), sha256=hashlib.sha256(blob).hexdigest())


def archive_files(path):
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        assert len(entries) == len({e.filename for e in entries})
        assert sum(e.file_size for e in entries) <= 512*2**20
        files = {}
        prefixes = set()
        for entry in entries:
            name = PurePosixPath(entry.filename)
            assert not name.is_absolute() and '..' not in name.parts and len(name.parts) >= 2
            # Historical Python writestr archives omit the Unix type bits.
            # Accept their ordinary file entries, but never directories or links.
            assert not entry.is_dir() and stat.S_IFMT(entry.external_attr >> 16) in (0, stat.S_IFREG)
            assert entry.file_size <= 64*2**20
            prefixes.add(name.parts[0])
            relative = str(PurePosixPath(*name.parts[1:]))
            assert relative not in files
            files[relative] = archive.read(entry)
        assert len(prefixes) == 1
        return files


def main(directory):
    directory = Path(directory)
    manifest = json.loads((directory/'MANIFEST.json').read_bytes())
    assert {p.name for p in directory.iterdir()} == set(manifest)|{'MANIFEST.json'}
    for name, expected in manifest.items():
        assert PurePosixPath(name).name == name
        path = directory/name
        assert path.is_file() and not path.is_symlink() and identity(path.read_bytes()) == expected
    components = {n: archive_files(directory/n) for n in manifest if n.endswith('.zip')}
    assert len(components) == 10
    base_name = 'development-source-review-v72.zip'
    extra_name = 'development-optimization-source-v105.zip'
    base, extra = components[base_name], components[extra_name]
    base_hashes = dict((line[66:], line[:64]) for line in base['MANIFEST.sha256'].decode().splitlines())
    assert set(base_hashes) == set(base)-{'MANIFEST.sha256'}
    assert all(hashlib.sha256(base[n]).hexdigest() == h for n, h in base_hashes.items())
    extra_manifest = json.loads(extra['MANIFEST.json'])
    assert set(extra_manifest) == set(extra)-{'MANIFEST.json'}
    assert all(identity(extra[n]) == e for n, e in extra_manifest.items())
    coverage = json.loads(extra['SOURCE_COVERAGE.json'])
    assert coverage['executed_archive_entries'] == 934 and len(coverage['files']) == 930
    assert len(coverage['omitted_execution_receipts']) == 4
    counts = {base_name: 0, extra_name: 0}
    for name, expected in coverage['files'].items():
        component = expected['component']
        assert component in counts and identity(components[component][name]) == expected['derivative']
        counts[component] += 1
    assert counts == {base_name: 583, extra_name: 347}
    print(json.dumps(dict(status='verified_supplied_bytes_and_source_coverage',
        components=len(components), source_files=930, source_component_counts=counts,
        empirical_pipeline_executed=False, adapted_code_execution_qualified=False,
        full_anonymity_verified=False, external_inputs_acquired=False), sort_keys=True))


if __name__ == '__main__':
    main(sys.argv[1])
