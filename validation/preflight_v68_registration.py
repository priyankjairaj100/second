"""Read-only host inventory for V68 admission; no corpus acquisition or launch."""
from pathlib import Path
import ast
import datetime
import hashlib
import json
import shutil
import subprocess

ROOT = Path('/nfs_home/users/poonam/second-20261010')
V65 = ROOT/'local_runs/disjoint-data-v65-20261016-a'
V67 = ROOT/'local_runs/disjoint-service-v67-20261016-a'
RUN = ROOT/'local_runs/quality-data-v68-20261016-a'


def bind(path, maximum=128*2**20):
    path = Path(path)
    assert path.is_file() and not any(p.is_symlink() for p in (path, *path.parents))
    before = path.stat()
    assert before.st_size <= maximum
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(2**20), b''):
            h.update(block)
    after = path.stat()
    assert (before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) == (
        after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
    return dict(path=str(path), bytes=after.st_size, sha256=h.hexdigest())


def command(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True, timeout=30).strip()


def main():
    assert command('git', 'rev-parse', 'HEAD') == 'f900999fcb200509dfad4fc081ce9c87fd172a16'
    assert not command('git', 'status', '--porcelain') and not RUN.exists()
    queue = command('squeue', '-h', '-u', 'poonam', '-o', '%i|%j|%T')
    assert not any('second' in row.lower() for row in queue.splitlines())
    accounting = command('sacct', '-n', '-P', '-j', ','.join(map(str, range(15261, 15276))),
                         '--format=JobIDRaw,State,ExitCode,Elapsed,TotalCPU')
    rows = {v[0]: v[1:] for row in accounting.splitlines() if (v := row.split('|')) and v[0].isdigit()}
    assert set(rows) == set(map(str, range(15261, 15276)))
    assert all(v[:2] == ['COMPLETED', '0:0'] for v in rows.values())
    p = json.loads((V67/'program.json').read_bytes())
    old = json.loads((V65/'registration.json').read_bytes())
    assert bind(V67/'program.json')['sha256'] == '11e0db146e79330852f550a1cc3b2dd7568a66cdfe8006b004dca3840149cc30'
    frozen = {**p['prior_sources'], **p['new_sources']}
    assert len(frozen) == 469 and p['runtime'] == old['base_runtime']
    for group in [frozen, p['dependency_files'], p['historical_ledgers'], old['tokenizer_runtime_files']]:
        for name, expected in group.items():
            actual = bind(name)
            assert {k: actual[k] for k in ('bytes', 'sha256')} == expected, name
    runtime_files = {}
    for package_name, package in old['base_runtime']['packages'].items():
        if 'files' not in package:
            assert package_name == 'scipy' and package == dict(installed=False, required_for_pinned_gelu_new_route=False)
            continue
        for name, expected in package['files'].items():
            actual = bind(name)
            assert {k: actual[k] for k in ('bytes', 'sha256')} == expected, name
            runtime_files[name] = expected
    paths = {key: V65/name for key, name in [
        ('v65_registration', 'registration.json'), ('v65_data', 'data.json'),
        ('v65_audit', 'audit.json'), ('v65_selection', 'outputs/selection.json'),
        ('v65_prefix', 'outputs/shard-2-prefix.gz.part'), ('v65_after', 'outputs/exclusions-after.json')]}
    paths.update({key: V67/name for key, name in [
        ('v67_program', 'program.json'), ('v67_primary', 'primary-audit.json'),
        ('v67_supplemental', 'supplemental-audit.json'), ('v67_primary_entry', 'primary-entry.json'),
        ('v67_supplemental_entry', 'supplemental-entry.json')]})
    paths.update(quality_exclusions=ROOT/'campaigns/heldout_quality_v30_exclusions.json',
                 tokenizer=ROOT/'tmp/models/distilgpt2/tokenizer.json')
    inputs = {key: bind(path) for key, path in paths.items()}
    tree = ast.parse((V65/'research_v65/data.py').read_text())
    names = ast.literal_eval(next(n.value for n in tree.body if isinstance(n, ast.Assign)
        and any(isinstance(x, ast.Name) and x.id == 'META_NAMES' for x in n.targets)))
    history = {}
    ledgers = {}
    total = 0
    for folder in ('pilots', 'campaigns', 'local_runs'):
        for path in sorted((ROOT/folder).rglob('*.json')):
            if path.name == 'ledger.json':
                e = bind(path); e.pop('path'); ledgers[str(path)] = e
            if path.name not in names or {'worker', 'source'} & set(path.relative_to(ROOT).parts):
                continue
            e = bind(path, 2*2**20); e.pop('path')
            total += e['bytes']
            assert len(history) < 5000 and total <= 64*2**20
            history[str(path.relative_to(ROOT))] = e
    wrapper = bind(ROOT/'cluster_setup/run_cpu.sbatch'); wrapper.pop('path')
    assert wrapper == old['slurm_wrapper']
    manifest = ROOT/'local_runs/cluster-setup-20261010/container-13155.sha256'
    expected, image = manifest.read_text().strip().split(None, 1)
    image = image.strip()
    container = bind(image, 2**30)
    assert container['sha256'] == expected
    assert shutil.disk_usage(ROOT).free > 2**30
    print(json.dumps(dict(schema='v68-read-only-registration-preflight',
        captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), queue=queue,
        terminal_accounting=accounting, partition=command('scontrol', 'show', 'partition', 'cpu-short', '-o'),
        frozen_sources=frozen, prior_dependency_files=p['dependency_files'], historical_ledgers=ledgers,
        tokenizer_runtime_files=old['tokenizer_runtime_files'], tokenizers_version=old['tokenizers_version'],
        base_runtime=old['base_runtime'], host_runtime_files=runtime_files, inputs=inputs,
        history=history, history_file_count=len(history), history_bytes=total, slurm_wrapper=wrapper,
        container=container, container_manifest=bind(manifest), new_run_exists=False,
        empirical_data_acquired=False, numerical_runtime_execution=False, jobs_submitted=False)))


if __name__ == '__main__':
    main()
