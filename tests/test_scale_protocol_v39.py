"""Software fixtures for registered design, refusal policy, and larger Gram admission."""
from fractions import Fraction
import inspect
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from research_v39 import controller, policy
from research_v39.ci import event_guard
from research_v39.worker import scientific_refusal
from research_v39.scaled_gram_ball import certify_exact_gram_ball
from research_v35.exact_gram import accumulate, GramBudget, GramAdmissionError
from src.primal_certificate_v30 import PrimalBudget, PrimalUnresolved
from src.token_box_certificate import TokenBoxUnresolved
from tests.test_direct_gram_v35 import oracle


class ScaleProtocolTests(unittest.TestCase):
    def test_all_registered_reservations_fit_separate_caps(self):
        trials = controller.trial_specs()
        self.assertEqual([t['id'] for t in trials], ['data', 'prepare', 'retain-01', 'retain-06', 'retain-12'])
        for group, cap in [('data', 122), ('model', 2400)]:
            self.assertLessEqual(sum(t['cpu_seconds'] + 2 for t in trials if t['phase_group'] == group), cap)
        self.assertEqual([t['retained_count'] * 128 for t in trials if t['kind'] == 'case'], [128, 768, 1536])

    def test_prespecified_arm_sets_have_no_adaptive_order(self):
        base = {'gram_delete', 'gram_fresh', 'cached_token', 'cached_primal', 'compressed_48'}
        for count in (1, 6, 12):
            expected = base | ({'compressed_32', 'compressed_40'} if count == 6 else set())
            self.assertEqual(set(policy.arm_order(count)), expected)
            self.assertEqual(policy.arm_order(count), policy.arm_order(count))
        self.assertEqual(policy.NORMALIZATION, 1664)

    def test_larger_gram_requires_explicit_archive_admission_and_matches_oracle(self):
        features = np.tile(np.array([[.3], [.2]]), (1, 257))
        weights = np.array([[1.2, -.11]])
        budget = GramBudget(max_tokens=300)
        gram = accumulate(features, source_id='software', normalization=1664, budget=budget)
        with self.assertRaises(GramAdmissionError):
            certify_exact_gram_ball(weights, gram, ridge=Fraction(1, 100))
        answer = certify_exact_gram_ball(weights, gram, ridge=Fraction(1, 100), gram_budget=budget,
            budget=PrimalBudget(max_work_units=100000))
        np.testing.assert_array_equal(answer.codes,
            oracle(weights, features, ridge=Fraction(1, 100), normalization=1664))

    def test_refusal_classifier_separates_numeric_limits_from_runtime_failures(self):
        self.assertTrue(scientific_refusal(PrimalUnresolved(
            'primal native row verification failed: status=3, row=9, coordinate=4')))
        self.assertTrue(scientific_refusal(TokenBoxUnresolved('preconditioner coordinate budget exhausted')))
        for error in [MemoryError(), RuntimeError('preconditioner coordinate budget exhausted'),
            TokenBoxUnresolved('native ball runtime or allocation failure; no codes committed'),
            PrimalUnresolved('primal native row verification failed: status=1, row=9, coordinate=4')]:
            self.assertFalse(scientific_refusal(error))

    def test_event_guard_blocks_reruns_private_and_wrong_repository(self):
        env = dict(GITHUB_ACTIONS='true', GITHUB_REPOSITORY=policy.REPOSITORY,
            GITHUB_REF='refs/heads/main', GITHUB_EVENT_NAME='push', GITHUB_RUN_ATTEMPT='1',
            GITHUB_SHA='a' * 40, GITHUB_RUN_ID='123', RUNNER_ENVIRONMENT='github-hosted',
            RUNNER_OS='Linux', RUNNER_ARCH='X64')
        event = dict(repository=dict(private=False, full_name=policy.REPOSITORY), after='a' * 40)
        with patch('research_v39.ci.read', return_value=policy.TRIGGER):
            self.assertEqual(event_guard(env, event)['run_attempt'], 1)
            for key, value in [('GITHUB_RUN_ATTEMPT', '2'), ('GITHUB_REPOSITORY', 'other/repo'),
                               ('RUNNER_ENVIRONMENT', 'self-hosted')]:
                with self.assertRaises(ValueError):
                    event_guard(dict(env, **{key: value}), event)
            with self.assertRaises(ValueError):
                event_guard(env, dict(event, repository=dict(private=True, full_name=policy.REPOSITORY)))

    def test_new_evidence_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'record.json'
            first = policy.new(path, {'x': 1})
            with self.assertRaises(FileExistsError):
                policy.new(path, {'x': 2})
            self.assertEqual(policy.sha(path), first['sha256'])
            self.assertEqual(policy.read(path), {'x': 1})

    def test_scaled_adapter_keeps_v37_numerical_steps(self):
        from research_v37 import direct_gram_ball as old
        old_source = inspect.getsource(old.certify_exact_gram_ball)
        expected = old_source.replace('budget=primal.PrimalBudget()):',
            'budget=primal.PrimalBudget(), gram_budget=GramBudget()):', 1)
        expected = expected.replace('to_float64_enclosure(gram)', 'to_float64_enclosure(gram, budget=gram_budget)')
        self.assertEqual(inspect.getsource(certify_exact_gram_ball), expected)

    def test_expected_plan_rejects_unregistered_id(self):
        with self.assertRaises(ValueError):
            controller.expected_plan({'trials': controller.trial_specs()}, 'unregistered')

    def test_workflow_is_one_use_without_cache_or_artifact_upload(self):
        workflow = (policy.ROOT / '.github/workflows/scale-v39.yml').read_text()
        for required in ['ubuntu-24.04', "github.run_attempt == '1'", 'timeout-minutes: 60',
                         '.github/ci/scale-v39-trigger.json', '-m research_v39.ci execute']:
            self.assertIn(required, workflow)
        for forbidden in ['workflow_dispatch:', 'schedule:', 'actions/cache', 'upload-artifact']:
            self.assertNotIn(forbidden, workflow)
        self.assertEqual(json.loads((policy.ROOT / '.github/ci/scale-v39-trigger.json').read_text()), policy.TRIGGER)


if __name__ == '__main__':
    unittest.main()
