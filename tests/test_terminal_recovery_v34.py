"""Exact-incident recovery checks. No evidence edits, registration, or inference."""
import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts import launch_independent_requests_v34 as controller
from scripts import verify_terminal_recovery_v34 as recovery
from src.service_terminal_evidence_v30 import verify_completed as strict


class C4TerminalRecoveryTests(unittest.TestCase):
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
        self.assertEqual(result['model_artifact']['sha256'],'d4cca4f44263e10d682da32f205e81c01583873c04124e172e76539b1e722981')
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

    def test_every_other_path_delegates_unchanged_v33_verifier(self):
        other=self.attempt.parent/'c4-root-prepare'
        with patch.object(recovery,'prior_verify_completed',return_value={'strict':True}) as called:
            self.assertEqual(recovery.verify_completed(other),{'strict':True})
            called.assert_called_once_with(other)
        moved=self.attempt.parent/'other-copy'
        with patch.object(recovery,'prior_verify_completed',side_effect=ValueError('strict refusal')):
            with self.assertRaisesRegex(ValueError,'strict refusal'):recovery.verify_completed(moved)

    def test_both_prior_attempts_bind_registered_plans_and_debits(self):
        current=controller.campaign('c4')
        for name in controller.PRIOR_IDS:
            self.assertEqual(controller.verify_registered_attempt(current,name)['status'],'complete')

    def test_amendment_preserves_cap_program_and_only_five_unstarted_trials(self):
        value=self.amendment
        self.assertEqual(value['remaining_trials'],list(controller.REMAINING_IDS))
        self.assertEqual(value['unchanged_phase_cap_seconds'],1900)
        self.assertEqual(value['new_allowance_seconds'],0)
        self.assertFalse(value['original_three_copy_guard_passed'])
        self.assertEqual(value['cause'],'unknown')
        self.assertEqual(controller.AMENDMENT.exists(),self.existing_amendment)
        self.assertEqual(sum(x['charged_cpu_seconds'] for x in value['prior_ledger']['attempts'].values()),422)
        self.assertEqual(len(value['remaining_trials']),5)
        self.assertEqual(value['prior_wikitext_continuation_sha256'],controller.hashed(controller.prior.AMENDMENT))

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
        current=controller.campaign('c4');program,raw,protocol,registration=controller.registered_program(current)
        with patch.object(controller,'check_registered',return_value=(current,program,raw,protocol,registration)), \
             patch.object(controller,'PhaseBudget',side_effect=AssertionError('no reservation')):
            with self.assertRaisesRegex(ValueError,'prior trial cannot be repeated'):
                controller.run('c4',controller.PRIOR_IDS[0])

    def test_c4_design_is_unchanged_seven_trial_program(self):
        spec=controller.build_spec('c4')
        self.assertEqual(len(spec['trials']),7)
        self.assertEqual(sum(t['cpu_seconds']+2 for t in spec['trials']),1844)
        self.assertEqual(spec['phase_cpu_cap_seconds'],1900)
        controller.validate_design(spec)


    def test_wikitext_prior_exception_remains_exactly_original(self):
        prior=controller.prior.recovery
        attempt=prior.ROOT/prior.INCIDENT_RELATIVE
        self.assertEqual(recovery.verify_completed(attempt),prior.verify_completed(attempt))
        with self.assertRaisesRegex(ValueError,'terminal evidence copies differ'):strict(attempt)

    def test_c4_reference_input_is_preserved_and_adapter_is_verification_only(self):
        program,*_=controller.registered_program(controller.campaign('c4'))
        compressed=next(x for x in program['trials'] if x['id']==controller.ADAPTED_TRIAL)
        self.assertEqual(compressed['inputs_from_trial']['reference_completion']['trial'],'c4-delete-0-cold')
        contract=controller.adapter_contract()
        self.assertTrue(contract['verification_source_changed'])
        self.assertTrue(contract['worker_entrypoint_changed'])
        self.assertFalse(contract['numerical_source_changed'])
        self.assertTrue(contract['original_input_paths_unchanged'])

    def test_adapter_or_reference_contract_change_is_rejected(self):
        value=copy.deepcopy(self.amendment)
        value['worker_verification_adapter']['original_input_paths_unchanged']=False
        with self.assertRaisesRegex(ValueError,'adapter contract differs'):controller.validate_amendment(value)

    def test_adapter_schedule_requires_literal_registered_entrypoint_and_original_limits(self):
        current=controller.campaign('c4')
        program,_,_,registration=controller.registered_program(current)
        trial=next(x for x in program['trials'] if x['id']==controller.ADAPTED_TRIAL)
        cold=current/'attempts'/'c4-delete-0-cold'
        identity=controller.read_json(cold/'worker/identity.json')
        transaction=controller.read_json(cold/'transaction.json')
        identity['command']=[identity['command'][0],str(controller.ROOT/controller.ADAPTER),str(current/'attempts'/trial['id']/'plan.json')]
        identity['limits']['wall_seconds']=trial['wall_seconds']
        identity['limits']['cpu_seconds']=trial['cpu_seconds']
        original_hash=controller.hashed
        fake_hash='a'*64
        def hashed(path):return fake_hash if path==controller.AMENDMENT else original_hash(path)
        with patch.object(controller,'amendment',return_value=self.amendment), \
             patch.object(controller,'read_json',return_value={'controller_continuation_sha256':fake_hash}), \
             patch.object(controller,'hashed',side_effect=hashed):
            controller.verify_worker_schedule(current,trial,transaction,identity,registration,program)
            changed=copy.deepcopy(identity);changed['command'][1]=str(current/'source/scripts'/trial['script'])
            with self.assertRaisesRegex(ValueError,'registered frozen script'):
                controller.verify_worker_schedule(current,trial,transaction,changed,registration,program)
            changed=copy.deepcopy(identity);changed['limits']['cpu_seconds']+=1
            with self.assertRaisesRegex(ValueError,'resource limits differ'):
                controller.verify_worker_schedule(current,trial,transaction,changed,registration,program)

    def test_second_registration_would_never_reset_ledger(self):
        with patch.object(controller,'AMENDMENT') as path:
            path.exists.return_value=True
            with self.assertRaisesRegex(ValueError,'no overwrite'):controller.prepare_continuation()


if __name__=='__main__':unittest.main()
