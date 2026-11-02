"""Check every existing write filesystem without creating or moving files.

Project outputs and the existing default temporary directory are separate
requirements. Aliases on the same filesystem share one quota and must be summed.
This observes capacity; it does not reserve capacity against concurrent writers.
The caller must supply the complete reviewed allowance, including overhead.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time

from research_v85.storage import admit, count, parse_quota, require

SCOPES = frozenset(('project', 'temporary'))
QUOTA_OPTIONS = frozenset(('quota', 'uquota', 'usrquota', 'uqnoenforce',
                          'gquota', 'grpquota', 'gqnoenforce',
                          'pquota', 'prjquota', 'pqnoenforce'))
GROUP_OPTIONS = frozenset(('gquota', 'grpquota', 'gqnoenforce'))
PROJECT_OPTIONS = frozenset(('pquota', 'prjquota', 'pqnoenforce'))


def group_quota(raw, source, filesystem_bytes):
    """A reported zero group limit is unlimited; a missing row is unknown."""
    require(type(raw) is str and len(raw) < 128*1024, 'Bounded group quota report required')
    require(any(line.split() == ['Filesystem', 'blocks', 'quota', 'limit', 'grace',
                'files', 'quota', 'limit', 'grace'] for line in raw.splitlines()), 'Raw group quota header required')
    rows = [line.split() for line in raw.splitlines() if line.split() and line.split()[0] == source]
    require(len(rows) == 1 and len(rows[0]) >= 7, 'Exactly one complete group quota row required')
    used, soft, hard = map(count, rows[0][1:4]);tail = rows[0][4:]
    if re.fullmatch(r'\d+\*?', tail[0]) is None:tail = tail[1:]
    require(len(tail) in (3, 4), 'Ambiguous group inode quota row')
    files, file_soft, file_hard = map(count, tail[:3])
    require(not tail[3:] or re.fullmatch(r'\d+\*?', tail[3]) is None, 'Unexpected group quota columns')
    require(not (soft and hard) or soft <= hard, 'Invalid group byte limits')
    require(not (file_soft and file_hard) or file_soft <= file_hard, 'Invalid group inode limits')
    limits = [x for x in (soft, hard) if x];file_limits = [x for x in (file_soft, file_hard) if x]
    return dict(source=source, used_bytes=used*1024, soft_limit_bytes=soft*1024,
        hard_limit_bytes=hard*1024, used_files=files, file_soft_limit=file_soft, file_hard_limit=file_hard,
        block_limits_explicitly_unlimited=not limits, file_limits_explicitly_unlimited=not file_limits,
        headroom_bytes=max(0, min(limits)-used)*1024 if limits else filesystem_bytes,
        file_headroom=min(file_limits)-files if file_limits else None,
        unlimited_bytes_limited_by_filesystem=not limits, refuses_soft_limit_grace=True)


def requests(value):
    require(type(value) is dict and set(value) == SCOPES,
            'Both project and existing temporary filesystem requirements are mandatory')
    result = {}
    for scope, item in sorted(value.items()):
        require(type(item) is dict and set(item) == {'path', 'required_bytes', 'required_files'},
                'Exact storage request fields required')
        path = item['path']
        require(type(path) is str and 0 < len(path) <= 4096 and '\x00' not in path,
                'Bounded literal storage path required')
        p = Path(path)
        require(p.is_absolute() and not path.startswith('//') and str(p) == path and '..' not in p.parts,
                'Absolute canonical storage path required')
        for key in ('required_bytes', 'required_files'):
            require(type(item[key]) is int and 0 < item[key] < 2**63,
                    'Positive finite registered storage allowance required')
        result[scope] = dict(item)
    return result


def evaluate(requested, observations, quota_text, group_reports=None):
    """Pure decision over one fresh host snapshot; never accepts saved admission."""
    requested = requests(requested)
    require(type(quota_text) is str and len(quota_text) < 128*1024,
            'Bounded quota output required')
    group_reports = {} if group_reports is None else group_reports
    require(type(group_reports) is dict, 'Group quota observations must be explicit')
    require(type(observations) is dict and set(observations) == SCOPES,
            'Every requested filesystem must be observed')
    groups = {}
    sources = {}
    for scope, row in sorted(observations.items()):
        require(type(row) is dict and set(row) == {
            'path', 'device', 'source', 'mount', 'filesystem', 'options',
            'available_bytes', 'available_files', 'fragment_bytes', 'write_group'},
            'Exact mounted filesystem observation fields required')
        require(row['path'] == requested[scope]['path'], 'Observed storage path differs')
        require(type(row['device']) is int and row['device'] >= 0,
                'Filesystem device identity required')
        require(type(row['write_group']) is int and row['write_group'] >= 0, 'Actual new-file group required')
        for key in ('available_bytes', 'available_files', 'fragment_bytes'):
            require(type(row[key]) is int and row[key] >= 0, 'Invalid filesystem capacity')
        require(row['fragment_bytes'] > 0, 'Known filesystem allocation fragment required')
        require(type(row['source']) is str and re.fullmatch(r'/dev/[A-Za-z0-9_./:-]+', row['source']) is not None,
                'Known quota-backed device required; do not assume unlimited temporary space')
        require(type(row['mount']) is str and Path(row['mount']).is_absolute()
                and Path(row['path']).is_relative_to(Path(row['mount'])), 'Mount does not contain output path')
        require(type(row['filesystem']) is str and re.fullmatch(r'[A-Za-z0-9_.-]+', row['filesystem']) is not None,
                'Known filesystem type required')
        require(type(row['options']) is str and 0 < len(row['options']) < 8192,
                'Observed mount options required')
        options = row['options'].split(',')
        require(len(set(options)) == len(options) and all(options) and 'rw' in options and 'ro' not in options,
                'Unambiguous writable mount options required')
        require(not PROJECT_OPTIONS.intersection(options), 'Project quota needs separate project-ID admission')
        device, source = row['device'], row['source']
        require(source not in sources or sources[source] == device, 'Quota source has inconsistent devices')
        sources[source] = device
        if device not in groups:
            groups[device] = dict(source=source, filesystem=row['filesystem'], options=sorted(options),
                fragment_bytes=row['fragment_bytes'], paths=[], scopes=[], required_bytes=0,
                required_files=0, available_bytes=row['available_bytes'], available_files=row['available_files'],
                write_groups={})
        group = groups[device]
        require((source, row['filesystem'], row['fragment_bytes'], sorted(options)) ==
                (group['source'], group['filesystem'], group['fragment_bytes'], group['options']),
                'Same-device aliases have inconsistent mount identities')
        group['paths'].append(row['path'])
        group['scopes'].append(scope)
        # Capacity is shared even when the directories differ. A partial plan
        # cannot spend the same free quota independently for each directory.
        group['required_bytes'] += requested[scope]['required_bytes']
        group['required_files'] += requested[scope]['required_files']
        group['available_bytes'] = min(group['available_bytes'], row['available_bytes'])
        group['available_files'] = min(group['available_files'], row['available_files'])
        gid = str(row['write_group'])
        group['write_groups'].setdefault(gid, dict(required_bytes=0, required_files=0))
        group['write_groups'][gid]['required_bytes'] += requested[scope]['required_bytes']
        group['write_groups'][gid]['required_files'] += requested[scope]['required_files']
    needed_groups = {gid for group in groups.values() if GROUP_OPTIONS.intersection(group['options'])
                     for gid in group['write_groups']}
    require(set(group_reports) == needed_groups, 'Every enabled new-file group quota must be checked')
    checked = {}
    for device, group in sorted(groups.items()):
        if group['scopes'] == ['temporary'] and group['filesystem'] == 'xfs' and 'noquota' in group['options']:
            # Linux XFS documents noquota as disabling all quota accounting and
            # enforcement. This is observed mount evidence, not an absent-row
            # assumption. It never excuses the project's required finite quota.
            require(not QUOTA_OPTIONS.intersection(group['options']), 'Conflicting quota mount options')
            require(not any(line.split() and line.split()[0] == group['source'] for line in quota_text.splitlines()),
                    'Quota report conflicts with explicit noquota mount')
            require(group['available_bytes'] >= group['required_bytes'] and
                    group['available_files'] >= group['required_files'], 'Insufficient temporary filesystem capacity')
            quota = dict(status='disabled_by_observed_xfs_noquota', source=group['source'])
            decision = dict(status='admitted_at_observation_only', capacity_reserved=False,
                            concurrent_writers_can_invalidate=True)
        else:
            require('noquota' not in group['options'], 'Project quota or mount identity is contradictory')
            quota = parse_quota(quota_text, group['source'])
            decision = admit(quota, group['available_bytes'], group['available_files'],
                             group['required_bytes'], group['required_files'])
        group_checks = {}
        if GROUP_OPTIONS.intersection(group['options']):
            for gid, wanted in sorted(group['write_groups'].items()):
                q = group_quota(group_reports[gid], group['source'], group['available_bytes'])
                group_checks[gid] = dict(quota=q, decision=admit(q, group['available_bytes'],
                    group['available_files'], wanted['required_bytes'], wanted['required_files']))
        checked[str(device)] = dict(group, quota=quota, decision=decision, group_checks=group_checks)
    return dict(status='admitted_at_observation_only', requested=requested, filesystems=checked,
                capacity_reserved=False, group_project_quota_attested=False,
                concurrent_writers_can_invalidate=True, whole_chain_allowance_verified=False,
                filesystem_paths_changed=False, observed_new_file_groups_checked=True,
                other_write_groups_covered=False)


def _identity(path):
    p = Path(path)
    require(p.is_dir() and not any(x.is_symlink() for x in (p, *p.parents)),
            'Existing nonsymbolic write root required; no creation or redirection')
    st = p.stat()
    return st.st_dev, st.st_ino, st.st_gid if st.st_mode & stat.S_ISGID else os.getegid(), st.st_mode


def _command(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=10,
                            env=dict(os.environ, LC_ALL='C'))
    require(len(result.stdout) < 128*1024 and len(result.stderr) < 128*1024,
            'Bounded host storage output required')
    require(not result.stderr.strip(), 'Host storage command reported an error')
    return result


def capture(requested):
    """Read one bounded Linux host snapshot, without granting admission.

Do not call tempfile.gettempdir(): its discovery can write probe files. The
registered launcher must provide the actual existing temporary path explicitly.
Actual use inside the numerical container remains a separate qualification.
"""
    require(sys.platform == 'linux', 'Linux host storage inspection required')
    requested = requests(requested)
    tick = time.perf_counter_ns()
    identities = {scope: _identity(row['path']) for scope, row in requested.items()}
    observations = {}
    for scope, row in requested.items():
        result = _command(['findmnt', '--json', '-T', row['path'], '-o', 'SOURCE,TARGET,FSTYPE,OPTIONS'])
        require(result.returncode == 0, 'Mounted filesystem query failed')
        try:
            parsed = json.loads(result.stdout)
        except (ValueError, TypeError) as exc:
            raise ValueError('Invalid mounted filesystem response') from exc
        require(type(parsed) is dict and set(parsed) == {'filesystems'}
                and type(parsed['filesystems']) is list and len(parsed['filesystems']) == 1,
                'Exactly one mounted filesystem required')
        mount = parsed['filesystems'][0]
        require(type(mount) is dict and set(mount) == {'source', 'target', 'fstype', 'options'},
                'Exact mounted filesystem identity required')
        vfs = os.statvfs(row['path'])
        observations[scope] = dict(path=row['path'], device=identities[scope][0],
            source=mount['source'], mount=mount['target'], filesystem=mount['fstype'], options=mount['options'],
            available_bytes=vfs.f_bavail*vfs.f_frsize, available_files=vfs.f_favail,
            fragment_bytes=vfs.f_frsize, write_group=identities[scope][2])
    quota = _command(['quota', '-v', '-w'])
    require(quota.returncode in (0, 1), 'Quota query failed; unknown capacity refuses admission')
    group_reports = {}
    for gid in sorted({row['write_group'] for row in observations.values()
                       if GROUP_OPTIONS.intersection(row['options'].split(','))}):
        report = _command(['quota', '-g', '-v', '-w', str(gid)])
        require(report.returncode in (0, 1), 'New-file group quota query failed')
        group_reports[str(gid)] = report.stdout
    for scope, row in requested.items():
        require(_identity(row['path']) == identities[scope], 'Write root changed during inspection')
    return dict(status='snapshot_only_not_admission', requested=requested,
                observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                inspection_elapsed_ns=time.perf_counter_ns()-tick,
                quota_text=quota.stdout, quota_exit_code=quota.returncode,
                group_reports=group_reports, observations=observations, read_only=True, launches_job=False)


def inspect(requested):
    """Capture fresh state and decide; never reuse a saved passing decision."""
    snapshot = capture(requested)
    result = evaluate(snapshot['requested'], snapshot['observations'], snapshot['quota_text'], snapshot['group_reports'])
    return dict(result, observed_utc=snapshot['observed_utc'],
                inspection_elapsed_ns=snapshot['inspection_elapsed_ns'],
                quota_report_sha256=hashlib.sha256(snapshot['quota_text'].encode()).hexdigest(),
                observations=snapshot['observations'], read_only=True, launches_job=False)
