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
from research_v89 import host, storage_plan as plan, config, mapping

SOURCES = {'research_v89/example.py': dict(bytes=123, sha256='a'*64)}


class PlanTests(unittest.TestCase):
    def test_original_order_caps_and_full_failure_charge(self):
        from research_v80 import config as old
        self.assertEqual(config.ORDER, old.ORDER)
        self.assertEqual(config.TRIALS, old.TRIALS)
        self.assertEqual(config.CAP, old.CAP)
        for key in ('process_address_space_bytes', 'file_size_bytes', 'normalization',
                    'record_count', 'tokens_per_record', 'retained_counts', 'precision',
                    'model_bytes', 'resident_reservation_bytes', 'controller_allowance_cpu_seconds'):
            self.assertEqual(config.design()[key], old.design()[key])
        self.assertEqual(config.design()['combined_recovery_reservation_cpu_seconds'], 120622)
        self.assertEqual(config.design()['combined_controller_reservation_cpu_seconds'], 6622)
        self.assertNotEqual(config.RUN, old.RUN)

    def test_exact_source_extents_and_worker_census(self):
        p = plan.build(SOURCES, 10240)
        staging = p['roles'][0]
        self.assertEqual(staging['bytes'], 2*(123+10240))
        workers = [r for r in p['roles'] if r['role'] == 'worker_outputs']
        self.assertEqual(sum(r['bytes'] for r in workers), 30_432_559_104)
        self.assertEqual(sum(r['files'] for r in workers), 5201)
        self.assertEqual(len(plan.artifacts('prepare')), 11)
        self.assertEqual(len(plan.artifacts('oracle')), 20)

    def test_remaining_capacity_excludes_prior_outputs_but_never_deletes(self):
        p = plan.build(SOURCES, 10240)
        before = plan.requests(p, SOURCES, 10240, 'prepare')
        after = plan.requests(p, SOURCES, 10240, 'oracle')
        self.assertGreater(before['project']['required_bytes'], after['project']['required_bytes'])
        self.assertEqual(before['temporary'], after['temporary'])
        self.assertFalse(p['capacity_reserved'])
        self.assertFalse(p['formal_disk_bound'])

    def test_changed_omitted_or_lowered_plan_refuses(self):
        p = plan.build(SOURCES, 10240)
        for changed in (dict(p, roles=p['roles'][:-1]), dict(p, allocation_fixed_margin_bytes=0)):
            with self.assertRaises(ValueError): plan.requests(changed, SOURCES, 10240)
        with self.assertRaises(ValueError): plan.requests(p, SOURCES, 10240, 'retry')

    def test_bad_source_extent_and_path_refuse(self):
        for source in ({'../escape': SOURCES[next(iter(SOURCES))]},
                       {'file': dict(bytes=-1, sha256='a'*64)},
                       {'file': dict(bytes=True, sha256='a'*64)},
                       {'file': dict(bytes=1, sha256='z'*64)}):
            with self.assertRaises(ValueError): plan.build(source, 100)

    def test_storage_refusal_propagates_before_dispatch(self):
        p = dict(storage_plan=plan.build(SOURCES, 10240), source_inventory=SOURCES, source_archive_bytes=10240)
        with patch.object(host, 'capture', side_effect=ValueError('quota exhausted')), patch.object(host, 'collect') as launch:
            with self.assertRaisesRegex(ValueError, 'quota'): host.admit(p, 'prepare')
            launch.assert_not_called()


class AccountingTests(unittest.TestCase):
    def entry(self):
        return dict(process_cpu_ns=10, waited_child_cpu_ns=50, sealed_worker_cpu_ns=40)

    def test_helper_children_and_bootstrap_are_charged_once(self):
        r = host.reconcile_cpu('run', 3, 7, 100, self.entry())
        self.assertEqual(r['envelope_cpu_ns'], 110)
        self.assertEqual(r['contained_numerical_cpu_ns'], 40)
        self.assertEqual(r['nonnumerical_cpu_ns'], 70)

    def test_entry_cpu_plus_numerical_must_fit_subtree(self):
        e = self.entry();e['process_cpu_ns'] = 70
        with self.assertRaises(ValueError): host.reconcile_cpu('run', 0, 0, 100, e)
        e = self.entry();e['sealed_worker_cpu_ns'] = 51
        with self.assertRaises(ValueError): host.reconcile_cpu('run', 0, 0, 100, e)

    def test_full_host_cost_can_refuse_otherwise_passing_entry(self):
        with self.assertRaisesRegex(ValueError, 'allowance'):
            host.reconcile_cpu('run', 603*10**9, 0, 100, self.entry())

    def test_software_has_no_numerical_cpu_discount(self):
        r = host.reconcile_cpu('checks', 3, 7, 100, self.entry())
        self.assertEqual(r['nonnumerical_cpu_ns'], 110)


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
        start = dict(program_sha256='a', operation='run', arguments=['prepare'], job_id='1',
                     admission=dict(status='admitted_at_observation_only'),
                     snapshot=dict(observations={k:dict(device=1, write_group=2) for k in ('project', 'temporary')}))
        with patch.dict(os.environ, SLURM_JOB_ID='1'), patch.object(mapping.tempfile, 'gettempdir', return_value='/tmp'), patch.object(mapping.Path, 'resolve', return_value=Path('/tmp')):
            for ident in ((2, 3, 2, 0), (1, 3, 9, 0)):
                with patch.object(mapping, '_identity', return_value=ident):
                    with self.assertRaises(ValueError): mapping.verify(start, 'a', 'run', ['prepare'])
            with patch.object(mapping, '_identity', return_value=(1, 3, 2, 0)):
                r = mapping.verify(start, 'a', 'run', ['prepare'])
                self.assertFalse(r['paths_redirected'])

    def test_stale_job_or_different_temporary_root_refuses(self):
        start = dict(program_sha256='a', operation='run', arguments=['prepare'], job_id='1',
                     admission=dict(status='admitted_at_observation_only'))
        with patch.dict(os.environ, SLURM_JOB_ID='2'):
            with self.assertRaises(ValueError): mapping.verify(start, 'a', 'run', ['prepare'])
        with patch.dict(os.environ, SLURM_JOB_ID='1'), patch.object(mapping.tempfile, 'gettempdir', return_value='/var/tmp'):
            with self.assertRaises(ValueError): mapping.verify(start, 'a', 'run', ['prepare'])


class CancelTests(unittest.TestCase):
    def test_cancellation_only_current_job_once_and_no_environment_filters(self):
        from research_v80.io import write
        with tempfile.TemporaryDirectory() as folder, patch.object(host, 'RUN', Path(folder).resolve()), patch.dict(os.environ, SLURM_JOB_ID='99999', SCANCEL_NAME='unrelated', SLURM_CLUSTERS='other'):
            write(Path(folder).resolve()/'prepare-host-start.json', dict(job_id='99999', program_sha256='a'))
            with patch.object(host.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='', stderr='')) as run:
                host.cancel_current('prepare', 'a', 'log_limit_exceeded')
                self.assertEqual(run.call_args.args[0], ['scancel', '99999'])
                self.assertNotIn('SCANCEL_NAME', run.call_args.kwargs['env'])
                self.assertNotIn('SLURM_CLUSTERS', run.call_args.kwargs['env'])
                with self.assertRaises(FileExistsError): host.cancel_current('prepare', 'a', 'log_limit_exceeded')
                self.assertEqual(run.call_count, 1)

    def test_other_job_binding_refuses_before_scancel(self):
        from research_v80.io import write
        with tempfile.TemporaryDirectory() as folder, patch.object(host, 'RUN', Path(folder).resolve()), patch.dict(os.environ, SLURM_JOB_ID='99999'):
            write(Path(folder).resolve()/'prepare-host-start.json', dict(job_id='15905', program_sha256='a'))
            with patch.object(host.subprocess, 'run') as run:
                with self.assertRaises(ValueError): host.cancel_current('prepare', 'a', 'wall_timeout')
                run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
