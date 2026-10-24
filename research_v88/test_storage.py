"""Generated filesystem/CLI refusal cases; no numerical or cluster execution."""
import copy
import json
import os
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from research_v88 import storage as s

HEADER = 'Filesystem blocks quota limit grace files quota limit grace\n'
RAW = HEADER + '/dev/project 100 900 1000 12 0 0\n/dev/temp 100 900 1000 12 0 0\n'


def fixture():
    request = {scope: dict(path=path, required_bytes=500*1024, required_files=10)
               for scope, path in [('project', '/project'), ('temporary', '/tmp')]}
    observed = {scope: dict(path=row['path'], source='/dev/project' if scope == 'project' else '/dev/temp',
                           device=1 if scope == 'project' else 2, mount='/', filesystem='ext4',
                           options='rw,relatime', available_bytes=800*1024, available_files=100,
                           fragment_bytes=4096, write_group=1008)
                for scope, row in request.items()}
    return request, observed


class FilesystemAdmission(unittest.TestCase):
    def test_separate_filesystems_must_each_fit(self):
        request, observed = fixture()
        self.assertEqual(len(s.evaluate(request, observed, RAW)['filesystems']), 2)
        for scope in s.SCOPES:
            bad = copy.deepcopy(observed);bad[scope]['available_bytes'] = request[scope]['required_bytes']-1
            with self.subTest(scope=scope), self.assertRaises(ValueError):s.evaluate(request, bad, RAW)

    def test_same_device_aliases_cannot_spend_quota_twice(self):
        request, observed = fixture()
        observed['temporary'].update(device=1, source='/dev/project')
        with self.assertRaises(ValueError):s.evaluate(request, observed, RAW)
        for row in request.values():row['required_bytes'] = 400*1024
        group = s.evaluate(request, observed, RAW)['filesystems']['1']
        self.assertEqual(group['required_bytes'], 800*1024)
        self.assertEqual(group['required_files'], 20)
        observed['temporary']['available_files'] = 19
        with self.assertRaises(ValueError):s.evaluate(request, observed, RAW)

    def test_missing_scope_path_change_and_invalid_requirements_refuse(self):
        request, observed = fixture()
        with self.assertRaises(ValueError):s.evaluate({'project': request['project']}, observed, RAW)
        with self.assertRaises(ValueError):s.evaluate(request, {'project': observed['project']}, RAW)
        for key, value in [('path', 'tmp'), ('path', '/tmp/../project'), ('path', '//tmp'),
                           ('required_bytes', True), ('required_files', 0), ('required_bytes', 2**63)]:
            bad = copy.deepcopy(request);bad['temporary'][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):s.evaluate(bad, observed, RAW)

    def test_device_source_or_alias_inconsistency_refuses(self):
        request, observed = fixture()
        for change in [dict(device=1), dict(source='/dev/project'),
                       dict(device=1, source='/dev/project', fragment_bytes=8192),
                       dict(device=1, source='/dev/project', options='rw,noexec')]:
            bad = copy.deepcopy(observed);bad['temporary'].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):s.evaluate(request, bad, RAW)

    def test_unknown_quota_is_not_unlimited(self):
        request, observed = fixture()
        for raw in [HEADER+'/dev/project 100 900 1000 12 0 0\n', RAW.replace('900 1000', '0 0')]:
            with self.assertRaises(ValueError):s.evaluate(request, observed, raw)
        observed['temporary'].update(filesystem='xfs', options='rw')
        with self.assertRaises(ValueError):s.evaluate(request, observed, HEADER+'/dev/project 100 900 1000 12 0 0\n')

    def test_explicit_xfs_noquota_only_covers_temporary_filesystem(self):
        request, observed = fixture()
        observed['temporary'].update(filesystem='xfs', options='rw,noquota')
        raw = HEADER+'/dev/project 100 900 1000 12 0 0\n'
        result = s.evaluate(request, observed, raw)
        self.assertEqual(result['filesystems']['2']['quota']['status'], 'disabled_by_observed_xfs_noquota')
        self.assertFalse(result['capacity_reserved'])
        self.assertFalse(result['whole_chain_allowance_verified'])
        observed['project'].update(filesystem='xfs', options='rw,noquota')
        with self.assertRaises(ValueError):s.evaluate(request, observed, HEADER)

    def test_noquota_contradiction_or_insufficient_temporary_space_refuses(self):
        request, observed = fixture()
        observed['temporary'].update(filesystem='xfs', options='rw,noquota')
        with self.assertRaises(ValueError):s.evaluate(request, observed, RAW)
        raw = HEADER+'/dev/project 100 900 1000 12 0 0\n'
        for change in [dict(options='rw,noquota,uquota'), dict(available_bytes=0),
                       dict(available_files=0), dict(filesystem='ext4')]:
            bad = copy.deepcopy(observed);bad['temporary'].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):s.evaluate(request, bad, raw)

    def test_malformed_observation_and_readonly_mount_refuse(self):
        request, observed = fixture()
        for change in [dict(device=True), dict(fragment_bytes=0), dict(available_files=-1),
                       dict(mount='/elsewhere'), dict(options='ro'), dict(options='rw,rw'),
                       dict(options='rw,ro'), dict(source='unknown')]:
            bad = copy.deepcopy(observed);bad['temporary'].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):s.evaluate(request, bad, RAW)

    def test_observed_overquota_project_is_not_excused_by_free_temporary_space(self):
        request, observed = fixture()
        observed['temporary'].update(filesystem='xfs', options='rw,noquota', available_bytes=2**40)
        raw = HEADER+'/dev/project 1048576004* 1047527424 1048576000 3days 3306263 0 0\n'
        with self.assertRaises(ValueError):s.evaluate(request, observed, raw)

    def test_enabled_group_quota_must_be_observed_and_fit(self):
        request, observed = fixture();observed['project']['options'] += ',grpquota'
        with self.assertRaises(ValueError):s.evaluate(request, observed, RAW)
        groups = {'1008': HEADER+'/dev/project 100 900 1000 12 0 0\n'}
        result = s.evaluate(request, observed, RAW, groups)
        self.assertTrue(result['observed_new_file_groups_checked'])
        for row in ['/dev/project 500 900 1000 12 0 0\n', '/dev/project 100 900 1000 12 20 30\n']:
            with self.subTest(row=row), self.assertRaises(ValueError):
                s.evaluate(request, observed, RAW, {'1008': HEADER+row})

    def test_reported_unlimited_group_does_not_bypass_user_quota(self):
        request, observed = fixture();observed['project']['options'] += ',grpquota'
        groups = {'1008': HEADER+'/dev/project 100 0 0 12 0 0\n'}
        result = s.evaluate(request, observed, RAW, groups)
        self.assertTrue(result['filesystems']['1']['group_checks']['1008']['quota']['block_limits_explicitly_unlimited'])
        with self.assertRaises(ValueError):
            s.evaluate(request, observed, RAW.replace('/dev/project 100', '/dev/project 999'), groups)

    def test_group_alias_allowances_are_aggregated_by_actual_gid(self):
        request, observed = fixture()
        for row in request.values():row['required_bytes'] = 350*1024
        for row in observed.values():row.update(device=1, source='/dev/project', options='rw,grpquota')
        groups = {'1008': HEADER+'/dev/project 100 900 1000 12 0 0\n'}
        decision = s.evaluate(request, observed, RAW, groups)['filesystems']['1']['group_checks']['1008']['decision']
        self.assertEqual(decision['required_bytes'], 700*1024)
        with self.assertRaises(ValueError):
            s.evaluate(request, observed, RAW, {'1008': HEADER+'/dev/project 300 900 1000 12 0 0\n'})
        observed['temporary']['write_group'] = 1009
        with self.assertRaises(ValueError):s.evaluate(request, observed, RAW, groups)
        groups['1009'] = groups['1008']
        self.assertEqual(len(s.evaluate(request, observed, RAW, groups)['filesystems']['1']['group_checks']), 2)

    def test_malformed_group_and_unresolved_project_quota_refuse(self):
        request, observed = fixture();observed['project']['options'] += ',grpquota'
        for row in ['', '/dev/other 100 0 0 12 0 0\n', '/dev/project 100 1001 1000 12 0 0\n',
                    '/dev/project 100G 0 0 12 0 0\n', '/dev/project 100 0 0 12 0 0\n'*2]:
            with self.subTest(row=row), self.assertRaises(ValueError):
                s.evaluate(request, observed, RAW, {'1008': HEADER+row})
        observed['project']['options'] = 'rw,prjquota'
        with self.assertRaises(ValueError):s.evaluate(request, observed, RAW)

    def host_patches(self, request, observed):
        def command(args):
            if args[0] == 'quota':return SimpleNamespace(returncode=1, stdout=RAW)
            path = args[args.index('-T')+1]
            row = next(r for r in observed.values() if r['path'] == path)
            return SimpleNamespace(returncode=0, stdout=json.dumps(dict(filesystems=[dict(
                source=row['source'], target=row['mount'], fstype=row['filesystem'], options=row['options'])])))
        return patch.multiple(s, _command=command,
            _identity=lambda path: (1 if path == request['project']['path'] else 2, 9, 1008, 0o40755)), \
            patch.object(s.os, 'statvfs', return_value=SimpleNamespace(f_bavail=200, f_frsize=4096, f_favail=100)), \
            patch.object(s.sys, 'platform', 'linux')

    def test_readonly_host_flow_accepts_quota_exit_one_with_valid_rows(self):
        request, observed = fixture()
        a,b,c = self.host_patches(request, observed)
        with a,b,c:
            result = s.inspect(request)
        self.assertTrue(result['read_only']);self.assertFalse(result['launches_job'])
        self.assertEqual(len(result['quota_report_sha256']), 64)

    def test_host_flow_refuses_changed_root_and_failed_query_without_retry(self):
        request, observed = fixture()
        a,b,c = self.host_patches(request, observed)
        with a,b,c,patch.object(s, '_identity', side_effect=[(1,9,1008,0o40755),(2,9,1008,0o40755),(1,10,1008,0o40755)]):
            with self.assertRaises(ValueError):s.inspect(request)
        a,b,c = self.host_patches(request, observed)
        with a,b,c,patch.object(s, '_command', return_value=SimpleNamespace(returncode=2, stdout='')) as command:
            with self.assertRaises(ValueError):s.inspect(request)
            self.assertEqual(command.call_count, 1)

    def test_mount_json_must_be_unambiguous(self):
        request, observed = fixture()
        for text in ['{}', '{', '{"filesystems":[]}', '{"filesystems":[{},{}]}']:
            a,b,c = self.host_patches(request, observed)
            with a,b,c,patch.object(s, '_command', return_value=SimpleNamespace(returncode=0, stdout=text)):
                with self.subTest(text=text), self.assertRaises(ValueError):s.inspect(request)

    def test_host_flow_queries_observed_group_once(self):
        request, observed = fixture()
        for row in observed.values():row['options'] += ',grpquota'
        a,b,c = self.host_patches(request, observed)
        with a,b,c:
            original = s._command
            with patch.object(s, '_command', side_effect=original) as command:
                result = s.inspect(request)
                group_calls = [call.args[0] for call in command.call_args_list if '-g' in call.args[0]]
        self.assertEqual(group_calls, [['quota','-g','-v','-w','1008']])
        self.assertTrue(result['observed_new_file_groups_checked'])

    def test_new_file_group_respects_actual_setgid_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            os.chmod(root, 0o700)
            with patch.object(s.os, 'getegid', return_value=9999):
                self.assertEqual(s._identity(str(root))[2], 9999)
                os.chmod(root, 0o700 | stat.S_ISGID)
                self.assertTrue(root.stat().st_mode & stat.S_ISGID)
                self.assertEqual(s._identity(str(root))[2], root.stat().st_gid)


if __name__ == '__main__':unittest.main()
