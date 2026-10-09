"""Software fixtures for the V38 one-use controller. No model work runs."""
import copy
import hashlib
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import execute_ci_c4_v38 as ci
from scripts import launch_independent_requests_v32 as old
from research_v38 import c4_controller as current


class AdmissionTests(unittest.TestCase):
    def env(self):
        return dict(GITHUB_ACTIONS='true', GITHUB_REPOSITORY=ci.REPOSITORY,
                    GITHUB_REF='refs/heads/main', GITHUB_EVENT_NAME='push',
                    GITHUB_RUN_ATTEMPT='1', GITHUB_SHA='a' * 40,
                    RUNNER_ENVIRONMENT='github-hosted', RUNNER_OS='Linux',
                    RUNNER_ARCH='X64', GITHUB_RUN_ID='123')

    def event(self):
        return dict(repository=dict(private=False, full_name=ci.REPOSITORY), after='a' * 40)

    def guarded(self, env=None, event=None):
        with patch.object(ci, 'read', return_value=ci.TRIGGER_PAYLOAD):
            return ci.event_guard(self.env() if env is None else env, self.event() if event is None else event)

    def test_public_standard_runner_accepts_once(self):
        self.assertEqual(self.guarded()['run_attempt'], 1)

    def test_private_runner_is_refused(self):
        event = self.event()
        event['repository']['private'] = True
        with self.assertRaisesRegex(ValueError, 'Private'):
            self.guarded(event=event)

    def test_reruns_and_nonstandard_runners_are_refused(self):
        for field, value in [('GITHUB_RUN_ATTEMPT', '2'), ('RUNNER_ENVIRONMENT', 'self-hosted'),
                             ('GITHUB_REPOSITORY', 'other/repo'), ('GITHUB_EVENT_NAME', 'workflow_dispatch'),
                             ('GITHUB_REF', 'refs/heads/other'), ('RUNNER_OS', 'Windows')]:
            env = self.env()
            env[field] = value
            with self.assertRaises(ValueError):
                self.guarded(env=env)

    def test_changed_revision_is_refused(self):
        event = self.event()
        event['after'] = 'b' * 40
        with self.assertRaisesRegex(ValueError, 'revision'):
            self.guarded(event=event)

    def portability_report(self, status):
        return dict(schema='runtime-portability-crosscheck-v38', status=status,
            c4_original_backend_admitted=True, portable_gate_7_passed=status == 'passed',
            checks={'old_cpu_record_mapping': {'status': 'passed'},
                    'old_cpu_record_mapping_after': {'status': 'passed'},
                    'stable_original_runtime_evidence': True, 'stable_live_evidence': True,
                    'cpu': {'status': 'passed'}, 'libraries': {'status': 'passed'}},
            raw_manifests={'old_transformer': {}, 'old_primitive': {},
                          'old_transformer_after': {}, 'old_primitive_after': {},
                          'new_before': {}, 'new_after': {}},
            error=None if status == 'passed' else {'reason': 'required live loader API is absent: fixture'})

    def test_narrow_portable_refusal_keeps_original_backend_only(self):
        report = self.portability_report('unsupported_portable_interface')
        decision = ci.admit_original_backend(report, 0)
        self.assertTrue(decision['original_c4_admitted'])
        self.assertFalse(decision['portable_gate_7_passed'])
        self.assertIsNotNone(decision['portable_refusal'])
        self.assertTrue(ci.admit_original_backend(self.portability_report('passed'), 0)['portable_gate_7_passed'])

    def test_contradictions_and_unknown_refusals_block_original_backend(self):
        for status in ('contradictory_runtime_facts', 'unexpected_error', 'unrecognized'):
            with self.assertRaisesRegex(ValueError, 'does not admit'):
                ci.admit_original_backend(self.portability_report(status), 0)

    def test_portable_refusal_requires_valid_original_evidence(self):
        report = self.portability_report('unsupported_portable_interface')
        report['checks']['old_cpu_record_mapping']['status'] = 'failed'
        with self.assertRaisesRegex(ValueError, 'mapping did not pass'):
            ci.admit_original_backend(report, 0)
        report = self.portability_report('unsupported_portable_interface')
        report['portable_gate_7_passed'] = True
        with self.assertRaisesRegex(ValueError, 'promotion flag'):
            ci.admit_original_backend(report, 0)

    def test_missing_stability_checks_refuse_both_routes(self):
        for status, field in [('passed', 'stable_live_evidence'),
                              ('unsupported_portable_interface', 'stable_original_runtime_evidence')]:
            report = self.portability_report(status)
            report['checks'].pop(field)
            with self.assertRaisesRegex(ValueError, 'stability evidence is missing'):
                ci.admit_original_backend(report, 0)

    def test_changed_before_after_manifests_refuse_both_routes(self):
        for status, field in [('passed', 'new_after'),
                              ('unsupported_portable_interface', 'old_transformer_after')]:
            report = self.portability_report(status)
            report['raw_manifests'][field] = {'changed': True}
            with self.assertRaisesRegex(ValueError, 'manifests changed'):
                ci.admit_original_backend(report, 0)

    def test_existing_claim_blocks_all_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ci.PREFIX).mkdir(parents=True)
            with patch.object(ci, 'ROOT', root), patch.object(ci, 'event_guard', return_value={'event_commit': 'a'}), \
                 patch.object(ci, 'git', return_value='a'), patch.object(ci, 'save_new') as save:
                with self.assertRaisesRegex(ValueError, 'already exists'):
                    ci.claim_once()
                save.assert_not_called()

    def test_binary_outputs_never_enter_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / ci.CAMPAIGN / 'attempts' / 'one' / 'outputs'
            folder.mkdir(parents=True)
            (folder / 'model.bin').write_bytes(b'\0raw')
            (folder / 'completion.json').write_text('{}')
            (folder / 'writer.lock').write_text('')
            with patch.object(ci, 'ROOT', root):
                paths = ci.collect_text_paths()
            self.assertEqual(paths, [str((folder / 'completion.json').relative_to(root))])

    def test_credentials_and_unexpected_files_block_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / ci.PREFIX
            folder.mkdir(parents=True)
            path = folder / 'unsafe.json'
            path.write_text('ghp_' + 'x' * 35)
            with patch.object(ci, 'ROOT', root):
                with self.assertRaisesRegex(ValueError, 'credential'):
                    ci.collect_text_paths()
                path.unlink()
                (folder / 'library.so').write_bytes(b'abc')
                with self.assertRaisesRegex(ValueError, 'Unexpected'):
                    ci.collect_text_paths()

    def test_push_failure_blocks_further_publication(self):
        with patch.object(ci, 'PUBLISH_BROKEN', True), patch.object(ci, 'git') as git:
            with self.assertRaisesRegex(ValueError, 'earlier publication failed'):
                ci.publish('must not run')
            git.assert_not_called()

    def test_remote_change_stops_before_staging(self):
        with patch.object(ci, 'PUBLISH_BROKEN', False), \
             patch.object(ci, 'git', side_effect=['a', 'b\trefs/heads/main']) as git, \
             patch.object(ci, 'collect_text_paths') as collect:
            with self.assertRaisesRegex(ValueError, 'Remote main moved'):
                ci.publish('must not run')
            collect.assert_not_called()
            self.assertEqual(git.call_count, 2)


class ControllerPreservationTests(unittest.TestCase):
    def test_worker_checks_and_execution_are_unchanged(self):
        for name in ('run', 'completed', 'verify_registered_attempt', 'check_registered',
                     'resource_admission', 'registered_program', 'archive_evidence'):
            self.assertEqual(inspect.getsource(getattr(current, name)), inspect.getsource(getattr(old, name)), name)

    def test_only_host_target_changes_in_seven_trial_plans(self):
        from research_v38 import bootstrap_target
        original_read = current.read_json
        target_path = current.ROOT / 'campaigns/ci_v38/bootstrap/outputs/fixed-target.json'
        target_hash = hashlib.sha256(b'fixture target only').hexdigest()
        def read_fixture(path):
            if Path(path) == target_path:
                return {'schema': 'fixed-nearest-anchor-calibration-target-v1'}
            return original_read(path)
        original_hash = current.hashed
        def hash_fixture(path):
            return target_hash if Path(path) == target_path else original_hash(path)
        with patch.object(bootstrap_target, 'verify_bootstrap', return_value={'status': 'verified'}), \
             patch.object(current, 'read_json', side_effect=read_fixture), \
             patch.object(current, 'hashed', side_effect=hash_fixture), \
             patch.object(old, 'WORKSPACE', current.WORKSPACE):
            before = old.build_spec('c4')
            after = current.build_spec('c4')
            self.assertEqual(before['execution_order'], after['execution_order'])
            self.assertEqual(before['requests'], after['requests'])
            self.assertEqual(sum(t['cpu_seconds'] + 2 for t in after['trials']), 1844)
            for left, right in zip(before['trials'], after['trials']):
                expected = copy.deepcopy(left)
                expected['plan']['expected_target'] = target_hash
                self.assertEqual(expected, right)
            current.validate_design(after, inputs=False)

    def test_missing_bootstrap_blocks_target_selection(self):
        from research_v38 import bootstrap_target
        with patch.object(bootstrap_target, 'verify_bootstrap', side_effect=ValueError('missing receipt')):
            with self.assertRaisesRegex(ValueError, 'missing receipt'):
                current.build_spec('c4')

    def test_old_and_new_numerical_sources_are_equal(self):
        self.assertEqual(current.source_hashes(current.ROOT), old.source_hashes(old.ROOT))
        self.assertEqual(current.source_hashes(current.ROOT),
                         old.read_json(old.ROOT / 'campaigns/compressed_service_v31/program.json')['source_sha256'])

    def test_published_wikitext_metadata_prerequisite_verifies(self):
        report = ci.published_wiki_prerequisite()
        self.assertEqual(report['bound_files_verified'], 699)
        self.assertFalse(report['historical_binary_outputs_reverified_here'])

    def test_historical_mutation_is_refused(self):
        with patch.object(ci, 'sha', return_value='0' * 64):
            with self.assertRaisesRegex(ValueError, 'WikiText analysis changed'):
                ci.published_wiki_prerequisite()

    def test_direct_registration_is_disabled(self):
        with self.assertRaisesRegex(ValueError, 'one-use V38 wrapper'):
            current.register('c4')

    def test_workflow_has_no_paid_storage_or_rerun_trigger(self):
        text = (ci.ROOT / '.github/workflows/c4-v38.yml').read_text()
        self.assertIn('github.event.repository.private == false', text)
        self.assertIn("github.run_attempt == '1'", text)
        self.assertIn('runs-on: ubuntu-24.04', text)
        self.assertIn('timeout-minutes: 60', text)
        self.assertIn('--require-hashes', text)
        self.assertNotIn('workflow_dispatch', text)
        self.assertNotIn('upload-artifact', text)
        self.assertNotIn('actions/cache', text)
        self.assertNotIn('cache:', text)
        self.assertEqual(text.count('contents: write'), 1)


if __name__ == '__main__':
    unittest.main()
