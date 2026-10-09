"""Regression checks for clean-runner setup. No model inference occurs."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from scripts import execute_ci_c4_v38 as ci
from research_v38 import c4_controller as controller
from research_v38 import bootstrap_target


class SetupOrderTests(unittest.TestCase):
    def test_fixture_checks_stop_before_subprocess_when_assets_missing(self):
        with patch.object(ci, 'verify_claim'), patch.object(ci, 'read', side_effect=FileNotFoundError('checkpoint-audit')), patch.object(ci.subprocess, 'run') as run:
            with self.assertRaises(FileNotFoundError):
                ci.software_fixtures()
            run.assert_not_called()

    def test_fixture_checks_stop_when_checkpoint_changed(self):
        assets = SimpleNamespace(checkpoint_inventory=lambda: {'checkpoint_verified': False})
        with patch.object(ci, 'verify_claim'), patch.object(ci, 'read', return_value={'checkpoint_verified': True}), patch.object(ci, 'modules', return_value=(None,None,None,assets,None)), patch.object(ci.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'missing or changed'):
                ci.software_fixtures()
            run.assert_not_called()

    def test_preparation_restores_then_verifies_then_publishes(self):
        events=[]
        assets=SimpleNamespace(restore_checkpoint=lambda: events.append('restore') or [], checkpoint_inventory=lambda: events.append('verify') or {'checkpoint_verified':True})
        with tempfile.TemporaryDirectory() as directory, patch.object(ci,'ROOT',Path(directory)), patch.object(ci,'verify_claim'), patch.object(ci,'modules',return_value=(None,None,None,assets,None)), patch.object(ci,'save_new',side_effect=lambda *args:events.append('save')), patch.object(ci,'publish',side_effect=lambda *args:events.append('publish')):
            ci.prepare_checkpoint()
        self.assertEqual(events,['restore','verify','save','publish'])

    def test_failed_checkpoint_verification_cannot_pass(self):
        assets=SimpleNamespace(restore_checkpoint=lambda:[],checkpoint_inventory=lambda:{'checkpoint_verified':False})
        with tempfile.TemporaryDirectory() as directory, patch.object(ci,'ROOT',Path(directory)), patch.object(ci,'verify_claim'), patch.object(ci,'modules',return_value=(None,None,None,assets,None)), patch.object(ci,'save_new'), patch.object(ci,'publish'):
            with self.assertRaisesRegex(ValueError,'Checkpoint identity failed'):
                ci.prepare_checkpoint()

    def test_existing_checkpoint_audit_blocks_repetition(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); audit=root/ci.PREFIX/'checkpoint-audit.json';audit.parent.mkdir(parents=True);audit.write_text('{}')
            with patch.object(ci,'ROOT',root),patch.object(ci,'verify_claim'),patch.object(ci,'modules') as modules:
                with self.assertRaisesRegex(ValueError,'already ran'):
                    ci.prepare_checkpoint()
                modules.assert_not_called()

    def test_new_namespace_preserves_old_claim(self):
        self.assertNotEqual(ci.PREFIX,Path('campaigns/ci_v38'))
        self.assertTrue((ci.ROOT/'campaigns/ci_v38/execution-claim.json').is_file())
        self.assertEqual(ci.sha(ci.ROOT/'campaigns/ci_v38/execution-claim.json'), '3e3f936f22b0906bdd9bec7d093bee6651030a3d131f56a41d7cf0ab0e754fa0')

    def test_bootstrap_uses_selected_workspace(self):
        with patch.object(controller,'WORKSPACE','campaigns/fixture-new-workspace'), patch.object(bootstrap_target,'verify_bootstrap',side_effect=ValueError('fixture-stop')) as verify:
            with self.assertRaisesRegex(ValueError,'fixture-stop'):
                controller.build_spec('c4')
            verify.assert_called_once_with(controller.ROOT/'campaigns/fixture-new-workspace/bootstrap')


if __name__=='__main__':
    unittest.main()
