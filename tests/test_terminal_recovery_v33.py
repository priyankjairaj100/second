"""Exact-incident recovery checks. No evidence edits, registration, or inference."""
import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts import launch_independent_requests_v33 as controller
from scripts import verify_terminal_recovery_v33 as recovery
from src.service_terminal_evidence_v30 import verify_completed as strict


class TerminalRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.attempt=recovery.ROOT/recovery.INCIDENT_RELATIVE
        if not (cls.attempt/'outputs/model.bin').exists():
            raise unittest.SkipTest('incident binary unavailable; use preserved metadata audit on a clone')
        cls.existing_amendment=controller.AMENDMENT.exists()
        cls.amendment=(controller.amendment() if cls.existing_amendment else controller.prepare_continuation())

    def test_original_strict_contract_remains_failed(self):
        with self.assertRaisesRegex(ValueError,'terminal evidence copies differ'):strict(self.attempt)
        result=recovery.verify_completed(self.attempt)
        self.assertEqual(result['status'],'complete')
        self.assertEqual(result['model_artifact']['sha256'],'e3cc6f2e2597875f7a2c7fd08c9adc86ddd543125fb8e6fad89f56fda3e7d7b0')
        self.assertEqual(recovery.digest((self.attempt/'outputs/progress.json').read_bytes()),recovery.LIVE_SHA256)

    def changed_read(self,path,match):
        original=recovery._raw
        def changed(location):return b'{}' if Path(location)==path else original(location)
        with patch.object(recovery,'_raw',side_effect=changed):
            with self.assertRaisesRegex(ValueError,match):recovery.verify_completed(self.attempt)

    def test_live_copy_must_remain_exactly_the_reviewed_stale_bytes(self):
        self.changed_read(self.attempt/'outputs/progress.json','exact reviewed terminal/live pair')

    def test_completion_and_controller_seal_must_still_agree(self):
        self.changed_read(self.attempt/'sealed-progress.json','completion and controller seal differ')
        self.changed_read(self.attempt/'outputs/completion.json','completion and controller seal differ')

    def test_snapshot_manifest_mutation_is_rejected(self):
        self.changed_read(recovery.ROOT/recovery.SNAPSHOT_RELATIVE/'manifest.json','incident manifest changed')

    def test_original_program_mutation_is_rejected(self):
        self.changed_read(self.attempt.parent.parent/'program.json','program or protocol differs')

    def test_missing_or_changed_model_is_still_rejected(self):
        original=recovery._verify_file
        def check(path,entry):
            if Path(path)==self.attempt/'outputs/model.bin':raise ValueError('model bytes changed')
            return original(path,entry)
        with patch.object(recovery,'_verify_file',side_effect=check):
            with self.assertRaisesRegex(ValueError,'model bytes changed'):recovery.verify_completed(self.attempt)

    def test_every_other_path_uses_strict_verifier(self):
        other=self.attempt.parent/'wikitext-delete-0-cold'
        with patch.object(recovery,'strict_verify_completed',return_value={'strict':True}) as called:
            self.assertEqual(recovery.verify_completed(other),{'strict':True})
            called.assert_called_once_with(other)
        moved=self.attempt.parent/'other-copy'
        with patch.object(recovery,'strict_verify_completed',side_effect=ValueError('strict refusal')):
            with self.assertRaisesRegex(ValueError,'strict refusal'):recovery.verify_completed(moved)

    def test_all_four_prior_attempts_bind_registered_plans_and_debits(self):
        current=controller.campaign('wikitext')
        for name in controller.PRIOR_IDS:
            self.assertEqual(controller.verify_registered_attempt(current,name)['status'],'complete')

    def test_amendment_preserves_cap_program_and_only_three_unstarted_trials(self):
        value=self.amendment
        self.assertEqual(value['remaining_trials'],list(controller.REMAINING_IDS))
        self.assertEqual(value['unchanged_phase_cap_seconds'],1900)
        self.assertEqual(value['new_allowance_seconds'],0)
        self.assertFalse(value['original_three_copy_guard_passed'])
        self.assertEqual(value['cause'],'unknown')
        self.assertEqual(controller.AMENDMENT.exists(),self.existing_amendment)

    def test_budget_reset_source_change_or_trial_replacement_is_rejected(self):
        changes=[]
        for field in ('budget_reset','evidence_changed','numerical_source_changed','preparation_repeated','samples_changed','thresholds_changed'):
            value=copy.deepcopy(self.amendment);value[field]=True;changes.append(value)
        value=copy.deepcopy(self.amendment);value['new_allowance_seconds']=1;changes.append(value)
        value=copy.deepcopy(self.amendment);value['remaining_trials'].reverse();changes.append(value)
        for value in changes:
            with self.assertRaises(ValueError):controller.validate_amendment(value)

    def test_prior_debit_change_is_rejected(self):
        value=copy.deepcopy(self.amendment)
        first=next(iter(value['prior_ledger']['attempts'].values()));first['charged_cpu_seconds']+=1
        with self.assertRaisesRegex(ValueError,'prior settled debit changed'):controller.validate_amendment(value)

    def test_completed_prior_trial_cannot_be_reexecuted(self):
        current=controller.campaign('wikitext');program,raw,protocol,registration=controller.registered_program(current)
        with patch.object(controller,'check_registered',return_value=(current,program,raw,protocol,registration)), \
             patch.object(controller,'PhaseBudget',side_effect=AssertionError('no reservation')):
            with self.assertRaisesRegex(ValueError,'prior trial cannot be repeated'):
                controller.run('wikitext',controller.PRIOR_IDS[0])

    def test_c4_design_is_unchanged_seven_trial_program(self):
        spec=controller.build_spec('c4')
        self.assertEqual(len(spec['trials']),7)
        self.assertEqual(sum(t['cpu_seconds']+2 for t in spec['trials']),1844)
        self.assertEqual(spec['phase_cpu_cap_seconds'],1900)
        controller.validate_design(spec)


if __name__=='__main__':unittest.main()
