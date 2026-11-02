"""Check observed metadata and prepare an expanded notice component.

No legal conclusion, dependency installation, model/data access or experiment.
The existing six-component review bundle stays byte-for-byte unchanged.
"""
from pathlib import Path
from email.parser import BytesParser
import datetime
import hashlib
import json
import re
import stat
import tarfile
import tempfile
import zipfile
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

R = Path(__file__).resolve().parents[1]
OBSERVATION = R / 'validation/v71_installed_cuda_notices_20261018_b.tar.gz'
ARCHIVE = R / 'reports/development-dependency-notices-v71.zip'


def info(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def load_observation(path):
    with tarfile.open(path, 'r:gz') as archive:
        members = archive.getmembers()
        assert len(members) <= 501 and len({m.name for m in members}) == len(members)
        assert sum(m.size for m in members) <= 32 * 2**20
        for member in members:
            name = Path(member.name)
            assert member.isfile() and member.size <= 4 * 2**20
            assert not name.is_absolute() and '..' not in name.parts
        return {m.name: archive.extractfile(m).read() for m in members}


def verify(files):
    observation = json.loads(files['inventory.json'])
    assert observation['schema'] == 'installed-cuda-notice-observation-v71'
    assert observation['files'] == {n: info(b) for n, b in files.items() if n != 'inventory.json'}
    assert observation['collector_sha256'] == info((R / 'validation/collect_cuda_notices_v71.py').read_bytes())['sha256']
    for flag in ('historical_binary_notice_binding_verified', 'complete_transitive_system_notices',
                 'numerical_result', 'gpu_initialized', 'model_or_data_read',
                 'packages_installed', 'project_license_assigned'):
        assert observation[flag] is False
    environment = observation['marker_environment']
    assert environment['python_full_version'] == '3.10.19' and environment['extra'] == ''
    assert environment['platform_system'] == 'Linux' and environment['platform_machine'] == 'x86_64'
    packages = observation['distributions']
    assert packages['torch']['version'] == '2.10.0+cu128' and packages['numpy']['version'] == '2.2.6'
    runtime = json.loads((R / 'reports/review-reproduction-v71/RUNTIME.json').read_bytes())
    observed = runtime['future_cuda']['actual_runtime_bindings']['reviewcluster.cn4']
    assert observed['torch'] == packages['torch']['version'] and observed['numpy'] == packages['numpy']['version']
    edges = []
    coverage = set()
    for name, package in sorted(packages.items()):
        metadata_names = [n for n in package['files'] if n.endswith(('/METADATA', '/PKG-INFO'))]
        assert len(metadata_names) == 1
        metadata = BytesParser().parsebytes(files[metadata_names[0]])
        assert canonicalize_name(metadata['Name']) == name and metadata['Version'] == package['version']
        requirements = metadata.get_all('Requires-Dist', [])
        assert package['requires_dist'] == requirements
        for filename, commitment in package['files'].items():
            assert commitment == info(files[filename])
            coverage.add(filename)
        notices = [n for n in package['files'] if not n.endswith(('/METADATA', '/PKG-INFO', '/WHEEL'))]
        assert len(notices) == package['notice_files_found'] > 0
        for path, commitment in package['record_notice_entries_verified'].items():
            directory = Path(package['directory'])
            rel = Path(path)
            key = ('distributions/' + directory.name + '/' + str(rel.relative_to(directory))
                   if rel.is_relative_to(directory) else 'installation-notices/' + path)
            assert key in package['files'] and info(files[key]) == commitment
        for raw in requirements:
            requirement = Requirement(raw)
            active = requirement.marker is None or requirement.marker.evaluate(environment)
            target = canonicalize_name(requirement.name)
            edge = {'from': name, 'requirement': raw, 'target': target, 'active_without_extras': active}
            assert not requirement.url
            if active:
                assert not requirement.extras and target in packages
                version = packages[target]['version']
                assert requirement.specifier.contains(version, prereleases=True)
                edge['installed_version'] = version
            edges.append(edge)
    assert sorted(edges, key=lambda e: (e['from'], e['requirement'])) == sorted(
        observation['dependency_edges'], key=lambda e: (e['from'], e['requirement']))
    reachable = {'torch', 'numpy'}
    while True:
        new = reachable | {e['target'] for e in edges if e['from'] in reachable and e['active_without_extras']}
        if new == reachable:
            break
        reachable = new
    assert reachable == set(packages)
    assert coverage | {'python/LICENSE.txt', 'inventory.json'} == set(files)
    assert info(files['python/LICENSE.txt']) == observation['python_notice']
    assert len(packages) == 28
    assert sum(p['notice_files_found'] for p in packages.values()) + 1 == 35
    assert sum(len(p['record_notice_entries_verified']) for p in packages.values()) == 34
    assert len(edges) == 213 and sum(e['active_without_extras'] for e in edges) == 32
    return observation


def build():
    assert not ARCHIVE.exists()
    files = load_observation(OBSERVATION)
    observation = verify(files)
    payload = {'cuda/' + n: b for n, b in files.items() if n != 'inventory.json'}
    old_archive = R / 'reports/development-dependency-notices-v69.zip'
    expected = json.loads((R / 'validation/v69_review_dependency_notices.json').read_bytes())['archive']
    assert info(old_archive.read_bytes()) == {k: expected[k] for k in ('bytes', 'sha256')}
    with zipfile.ZipFile(old_archive) as archive:
        old = {n.removeprefix('dependency-notices/'): archive.read(n) for n in archive.namelist()}
    manifest = json.loads(old['MANIFEST.json'])
    assert manifest == {n: info(b) for n, b in old.items() if n != 'MANIFEST.json'}
    old_sources = json.loads(old['SOURCES.json'])
    for name, raw in old.items():
        if name.startswith('notices/'):
            payload['earlier/' + name] = raw
    assert len([n for n in payload if n.startswith('earlier/')]) == 5
    public_observation = {k: v for k, v in observation.items() if k not in ('installation', 'collector_sha256')}
    public_observation['installation'] = '/review/runtime'
    public_observation['original_notice_and_metadata_bytes_unchanged'] = True
    sources = {
        'schema': 'expanded-observed-dependency-notices-v71',
        'earlier_notice_sources': old_sources,
        'cuda_observation': public_observation,
        'complete_transitive_system_notices': False,
        'binary_redistribution_included': False,
        'project_license_assigned': False,
    }
    payload['SOURCES.json'] = encode(sources)
    payload['README.txt'] = b'''Expanded observed dependency notices: development component

This component preserves the five earlier CPU/publisher notice texts and adds
35 notice/attribution texts from the current shared CUDA Python installation.
The latter cover all 28 distributions reachable from torch and numpy using
installed Requires-Dist metadata on Linux/x86_64/Python3.10.19, with no extras,
plus the installed Python license. All 32 active dependency version constraints
were checked. Conditional and optional edges are retained, not called active.
The 34 distribution notice files match their installed RECORD size/hash entries.
Some notices are outside dist-info; those installation-relative files are included.
Original upstream authorship and notice text are preserved without editing.

METADATA and WHEEL files accompany the observed texts. SOURCES.json preserves
versions, origin scope, the complete declared dependency graph, marker environment,
and file hashes. Its installation path is a labelled placeholder. The current
Torch2.10.0+cu128 and NumPy2.2.6 version strings match the admitted runtime record;
this later file observation does not retroactively bind the notices to frozen
binaries. It is not a loaded-library trace, source/binary equivalence proof or
license clearance. The earlier tokenizers text remains a publisher-source notice,
and the CPU gmpy2 generic license texts do not resolve every native attribution.

No library, wheel, shared object, interpreter binary, model, article, token array
or container is included or installed. The read-only observer did not import Torch
or initialize CUDA. Its small process CPU is reporting overhead, not an empirical
worker debit. No registered job, numerical source, limit or threshold was changed.

Remaining scope includes the actual GPU-node driver/system/compiler/container
installation, non-metadata native dependencies, CPU GMP/MPFR/MPC attributions and
tokenizers Rust dependency/source correspondence. The source project's ownership
and release terms remain an author decision. Retained notices do not settle these.

MANIFEST.json gives size and SHA256 for every other member. Check the archive's
external hash as well; an editable manifest is not an authenticity signature.
This expanded component is staged for the next coherent review bundle. The prior
six-component bundle and its reproduction-guide bindings are unchanged. Do not
replace one of its ZIPs under an old filename. This is preparation, not a final
submission package or a new scientific result.
'''
    forbidden = re.compile(rb'priyankjairaj|poonam|\bcsis\b|csis_|172\.24\.16\.132|/nfs_home/|/Users/', re.I)
    findings = [n for n, raw in payload.items() if forbidden.search(raw)]
    assert not findings, findings
    payload['MANIFEST.json'] = encode({n: info(raw) for n, raw in sorted(payload.items())})
    with zipfile.ZipFile(ARCHIVE, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, raw in sorted(payload.items()):
            entry = zipfile.ZipInfo('dependency-notices/' + name, (2026, 10, 18, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(entry, raw, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with tempfile.TemporaryDirectory(prefix='expanded-notice-check-') as temp:
        root = Path(temp)
        with zipfile.ZipFile(ARCHIVE) as archive:
            assert len(archive.namelist()) == len(set(archive.namelist())) == len(payload)
            for entry in archive.infolist():
                path = Path(entry.filename)
                assert not path.is_absolute() and '..' not in path.parts and not entry.extra and not entry.comment
                assert stat.S_ISREG(entry.external_attr >> 16)
                out = root / path
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(archive.read(entry))
        extracted = {str(p.relative_to(root / 'dependency-notices')): p.read_bytes()
                     for p in root.rglob('*') if p.is_file()}
        assert extracted == payload
    # A missing file or altered dependency/notice metadata must fail the observer.
    probes = {}
    for label, target in [('notice_bytes', 'python/LICENSE.txt'), ('metadata_bytes', next(n for n in files if n.endswith('/METADATA')))]:
        altered = dict(files)
        altered[target] += b'changed'
        try:
            verify(altered)
        except (AssertionError, KeyError):
            probes[label] = 'rejected'
        else:
            raise AssertionError('Accepted altered observation')
    altered = dict(files)
    altered.pop('python/LICENSE.txt')
    try:
        verify(altered)
    except (AssertionError, KeyError):
        probes['missing_notice'] = 'rejected'
    else:
        raise AssertionError('Accepted missing notice')
    report = {
        'schema': 'expanded-dependency-notice-check-v71',
        'verified_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'archive': {'path': str(ARCHIVE.relative_to(R)), **info(ARCHIVE.read_bytes())},
        'raw_observation': {'path': str(OBSERVATION.relative_to(R)), **info(OBSERVATION.read_bytes())},
        'captured_at_utc': observation['captured_at_utc'], 'members': len(payload),
        'earlier_texts_preserved': 5, 'cuda_notice_texts': 35,
        'cuda_distributions': len(observation['distributions']),
        'active_dependency_edges': sum(e['active_without_extras'] for e in observation['dependency_edges']),
        'declared_dependency_edges': len(observation['dependency_edges']),
        'record_notice_hashes_verified': 34, 'metadata_graph_recomputed': True,
        'missing_notices_in_selected_distributions': [], 'clean_extraction_exact': True,
        'known_identity_findings': [], 'refusal_probes': probes,
        'process_cpu_seconds_reporting_observer': observation['observer_process_cpu_seconds'],
        'cpu_measurement_scope': 'Metadata-read window only; excludes interpreter startup, imports and tar serialization. Not the total observer cost or an empirical worker debit.',
        'old_review_components_unchanged': True, 'integrated_into_current_bundle': False,
        'complete_transitive_system_notices': False, 'historical_binary_notice_binding_verified': False,
        'scientific_result': False, 'model_or_data_read': False, 'packages_installed': False,
        'project_license_assigned': False, 'submission_ready': False,
    }
    with (R / 'validation/v71_expanded_dependency_notices.json').open('xb') as stream:
        stream.write(encode(report))
    print(json.dumps({k: report[k] for k in ('archive', 'members', 'cuda_notice_texts', 'cuda_distributions', 'active_dependency_edges', 'integrated_into_current_bundle')}))


if __name__ == '__main__':
    build()
