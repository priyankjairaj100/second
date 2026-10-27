"""Pure accounting/path fixtures and tiny nonnumerical child-process checks."""
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from unittest.mock import Mock
from types import SimpleNamespace
from research_v111 import host, mapping
from research_v111.records import writer

SOURCES = {'research_v89/example.py': dict(bytes=123, sha256='a'*64)}


class CollectorTests(unittest.TestCase):
    def test_all_output_preserved_and_second_call_refuses(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(host, 'ROOT', Path(folder)):
            p = Path(folder)/'log'
            command = [sys.executable, '-B', '-c', 'import os;os.write(1,b"out");os.write(2,b"err")']
            r = host.collect(command, p, 5)
            self.assertEqual(r['exit_code'], 0)
            self.assertIsNone(r['failure'])
            self.assertEqual(p.read_bytes(), b'outerr')
            self.assertEqual(r['log']['sha256'], hashlib.sha256(p.read_bytes()).hexdigest())
            with self.assertRaises(FileExistsError): host.collect(command, p, 5)

    def test_overflow_is_failed_with_explicit_incomplete_prefix(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(host, 'ROOT', Path(folder)), patch.object(host, 'LOG_BYTES', 128):
            p = Path(folder)/'log'
            cancel = Mock()
            r = host.collect([sys.executable, '-B', '-c', 'import os;os.write(1,b"x"*8192)'], p, 5, on_abort=cancel)
            self.assertEqual(r['failure'], 'log_limit_exceeded')
            self.assertFalse(r['log']['complete'])
            self.assertEqual(p.stat().st_size, 128)
            cancel.assert_called_once_with('log_limit_exceeded')

    def test_timeout_ends_process_group_and_preserves_output(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(host, 'ROOT', Path(folder)):
            p = Path(folder)/'log'
            r = host.collect([sys.executable, '-B', '-c', 'import time;print("started",flush=True);time.sleep(60)'], p, 1)
            self.assertEqual(r['failure'], 'wall_timeout')
            self.assertNotEqual(r['exit_code'], 0)
            self.assertIn(b'started', p.read_bytes())

    def test_nonzero_exit_is_not_hidden(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(host, 'ROOT', Path(folder)):
            r = host.collect([sys.executable, '-B', '-c', 'raise SystemExit(7)'], Path(folder)/'log', 5)
            self.assertEqual(r['exit_code'], 7)


class MappingTests(unittest.TestCase):
    def test_group_and_device_mismatch_refuse_without_redirect(self):
        start = dict(program_sha256='a', operation='run', arguments=['checks'], job_id='1',
                     admission=dict(status='admitted_at_observation_only'),
                     snapshot=dict(observations={k:dict(device=1, write_group=2) for k in ('project', 'temporary')}))
        with patch.dict(os.environ, SLURM_JOB_ID='1'), patch.object(mapping.tempfile, 'gettempdir', return_value='/tmp'), patch.object(mapping.Path, 'resolve', return_value=Path('/tmp')):
            for ident in ((2, 3, 2, 0), (1, 3, 9, 0)):
                with patch.object(mapping, '_identity', return_value=ident):
                    with self.assertRaises(ValueError): mapping.verify(start, 'a', 'run', ['checks'])
            with patch.object(mapping, '_identity', return_value=(1, 3, 2, 0)):
                r = mapping.verify(start, 'a', 'run', ['checks'])
                self.assertFalse(r['paths_redirected'])

    def test_stale_job_or_different_temporary_root_refuses(self):
        start = dict(program_sha256='a', operation='run', arguments=['checks'], job_id='1',
                     admission=dict(status='admitted_at_observation_only'))
        with patch.dict(os.environ, SLURM_JOB_ID='2'):
            with self.assertRaises(ValueError): mapping.verify(start, 'a', 'run', ['checks'])
        with patch.dict(os.environ, SLURM_JOB_ID='1'), patch.object(mapping.tempfile, 'gettempdir', return_value='/var/tmp'):
            with self.assertRaises(ValueError): mapping.verify(start, 'a', 'run', ['checks'])


class CancelTests(unittest.TestCase):
    def test_cancellation_only_current_job_once_and_no_environment_filters(self):
        from research_v80.io import write
        with tempfile.TemporaryDirectory() as folder, patch.object(host, 'RUN', Path(folder).resolve()), patch.object(host,'writer',side_effect=lambda:writer(Path(folder).resolve())), patch.dict(os.environ, SLURM_JOB_ID='99999', SCANCEL_NAME='unrelated', SLURM_CLUSTERS='other'):
            write(Path(folder).resolve()/'checks-host-start.json', dict(job_id='99999', program_sha256='a'))
            with patch.object(host.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='', stderr='')) as run:
                host.cancel_current('checks', 'a', 'log_limit_exceeded')
                self.assertEqual(run.call_args.args[0], ['scancel', '99999'])
                self.assertNotIn('SCANCEL_NAME', run.call_args.kwargs['env'])
                self.assertNotIn('SLURM_CLUSTERS', run.call_args.kwargs['env'])
                with self.assertRaises(FileExistsError): host.cancel_current('checks', 'a', 'log_limit_exceeded')
                self.assertEqual(run.call_count, 1)

    def test_other_job_binding_refuses_before_scancel(self):
        from research_v80.io import write
        with tempfile.TemporaryDirectory() as folder, patch.object(host, 'RUN', Path(folder).resolve()), patch.object(host,'writer',side_effect=lambda:writer(Path(folder).resolve())), patch.dict(os.environ, SLURM_JOB_ID='99999'):
            write(Path(folder).resolve()/'checks-host-start.json', dict(job_id='15905', program_sha256='a'))
            with patch.object(host.subprocess, 'run') as run:
                with self.assertRaises(ValueError): host.cancel_current('checks', 'a', 'wall_timeout')
                run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
