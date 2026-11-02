"""Once-only V68 host launcher. Run only from the admitted directory with its hash."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = Path('/nfs_home/users/poonam/second-20261010')
RUN = ROOT/'local_runs/quality-data-v68-20261016-a'


def read(path, maximum=128*2**20):
    path = Path(path)
    assert path.is_file() and not any(p.is_symlink() for p in (path, *path.parents))
    a = path.stat(); assert a.st_size <= maximum
    raw = path.read_bytes(); b = path.stat()
    assert (a.st_ino, a.st_size, a.st_mtime_ns, a.st_ctime_ns) == (b.st_ino, b.st_size, b.st_mtime_ns, b.st_ctime_ns)
    return raw


def info(raw):
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def cmd(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True, timeout=30).strip()


def save(name, value):
    with (RUN/name).open('x') as f:
        json.dump(value, f, sort_keys=True, separators=(',', ':'), allow_nan=False)
        f.flush(); os.fsync(f.fileno())


def main(expected):
    assert Path(__file__).resolve() == RUN/'launch_v68_registered.py'
    assert re.fullmatch('[0-9a-f]{64}', expected)
    raw = read(RUN/'registration.json'); assert info(raw)['sha256'] == expected
    p = json.loads(raw)
    assert raw == json.dumps(p, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    assert p['schema'] == 'untouched-quality-data-admission-v68' and p['directory'] == str(RUN)
    assert p['caps'] == dict(checks=dict(cpu=300, wall=600), data=dict(cpu=600, wall=1200), audit=dict(cpu=600, wall=900))
    assert p['allowance_cpu_seconds'] == 1506 and p['expected_tests'] == 22 and p['automatic_retry'] is False
    assert p['model_inference'] is False and p['quality_evaluation'] is False
    assert len(p['frozen_sources']) == 469 and len(p['new_sources']) == p['new_source_count'] == 9
    assert cmd('git', 'rev-parse', 'HEAD') == p['numerical_checkout'] == 'f900999fcb200509dfad4fc081ce9c87fd172a16'
    assert not cmd('git', 'status', '--porcelain')
    queue = cmd('squeue', '-h', '-u', 'poonam', '-o', '%i|%j|%T')
    assert not any('second' in line.lower() for line in queue.splitlines())
    for group in ['frozen_sources', 'new_sources', 'tokenizer_runtime_files', 'historical_ledgers', 'administrative_sources', 'prior_dependency_files', 'host_runtime_files']:
        for name, binding in p[group].items():
            assert info(read(name)) == binding, name
    for binding in p['inputs'].values():
        assert info(read(binding['path'])) == {k: binding[k] for k in ['bytes', 'sha256']}
    for name, binding in p['history'].items():
        assert info(read(ROOT/name, 2*2**20)) == binding, name
    assert info(read(ROOT/'cluster_setup/run_cpu.sbatch')) == p['slurm_wrapper']
    container = p['container']; manifest = p['container_manifest']
    assert info(read(manifest['path'])) == {k: manifest[k] for k in ['bytes', 'sha256']}
    image = Path(container['path']); assert image.stat().st_size == container['bytes']
    subprocess.run(['sha256sum', '--check', '--status', manifest['path']], cwd=ROOT, check=True, timeout=30)
    partition = cmd('scontrol', 'show', 'partition', 'cpu-short', '-o')
    fields = dict(v.split('=', 1) for v in partition.split() if '=' in v)
    assert fields['State'] == 'UP' and 'csis.mn1' in fields['Nodes'] and fields['MaxTime'] == '12:00:00'
    assert fields['MaxMemPerNode'] == '128000' and fields['AllowGroups'] == fields['AllowAccounts'] == 'ALL'
    accounting = cmd('sacct', '-n', '-P', '-j', ','.join(map(str, range(15261, 15276))), '--format=JobIDRaw,State,ExitCode')
    rows = {c[0]: c[1:3] for line in accounting.splitlines() if (c := line.split('|')) and c[0].isdigit()}
    assert set(rows) == set(map(str, range(15261, 15276))) and all(v == ['COMPLETED', '0:0'] for v in rows.values())
    primary = json.loads(read(p['inputs']['v67_primary']['path']))
    supplemental = json.loads(read(p['inputs']['v67_supplemental']['path']))
    assert primary['status'] == supplemental['status'] == 'verified'
    assert len(primary['evidence']['comparisons']) == 10 and supplemental['evidence']['ten_actual_model_pairs_equal'] is True
    assert primary['costs'] == supplemental['costs'] and primary['controllers'] == supplemental['controllers']
    assert supplemental['evidence']['primary_receipt_sha256'] == p['inputs']['v67_primary']['sha256']
    save('preflight.json', dict(registration_sha256=expected, queue=queue, terminal_accounting=accounting,
        partition=partition, frozen_sources_verified=469, source_files=9, historical_metadata_files=len(p['history']),
        new_corpus_acquired=False, observed_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    save('submission-intent.json', dict(registration_sha256=expected, automatic_retry=False,
        created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    jobs = {}; previous = None
    for trial, wall in [('checks', '00:10:00'), ('data', '00:20:00'), ('audit', '00:15:00')]:
        args = ['sbatch', '--parsable', '--no-requeue', '--nodelist=csis.mn1', '--mem=4G', '--time='+wall,
                '--job-name=second68-'+trial, '--output='+str(RUN/(trial+'-%j.log'))]
        if previous:
            args += ['--dependency=afterok:'+previous, '--kill-on-invalid-dep=yes']
        args += ['cluster_setup/run_cpu.sbatch', p['container_manifest']['path'], str(RUN/'research_v68/data_runner.py'), expected, trial]
        save(trial+'-submission-intent.json', dict(arguments=args, registration_sha256=expected, automatic_retry=False))
        try:
            result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=30)
        except BaseException as exc:
            save(trial+'-submission-unknown.json', dict(error=repr(exc), automatic_retry=False))
            raise
        save(trial+'-submission-response.json', dict(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr))
        assert result.returncode == 0 and result.stdout.strip().isdigit(), 'Unknown submission; inspect before any further action'
        job = result.stdout.strip()
        save(trial+'-submission.json', dict(job_id=job, arguments=args, registration_sha256=expected))
        jobs[trial] = job; previous = job
    save('jobs.json', jobs)
    print(json.dumps(dict(status='submitted_once', registration_sha256=expected, jobs=jobs)))


if __name__ == '__main__':
    main(*sys.argv[1:])
