"""Focused disclosure fixtures; no experiments or evidence modifications."""
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from scripts import analyze_independent_requests_v34 as analysis

class RecoveryAnalysisTests(unittest.TestCase):
    def provenance(self,corpus,*,guard=False,cause='unknown'):
        root=Path('/fixture')
        recovery=SimpleNamespace(INCIDENT_RELATIVE='campaigns/independent_c4_v32/attempts/c4-delete-0-cold',
            AUDIT_RELATIVE='campaigns/recovery_v34/audit.json',SNAPSHOT_RELATIVE='campaigns/recovery_v34/snapshot',
            verify_completed=lambda _: {'model_artifact':{'sha256':'a'*64}})
        snapshot={'cause':cause,'files':{'outputs/progress.json':{}}}
        amendment={'cause':cause,'prior_text_bindings':{}}
        previous={'recovered_terminal_trials':['wikitext-delete-1-cold'] if corpus=='wikitext' else [],
            'evidence_paths':['campaigns/recovery_v32/audit.json'],'incident_original_strict_three_copy_guard_passed':False}
        with ExitStack() as stack:
            stack.enter_context(patch.object(analysis,'ROOT',root))
            stack.enter_context(patch.object(analysis,'prior_provenance',return_value=previous))
            stack.enter_context(patch.object(analysis.controller,'AMENDMENT',root/'campaigns/independent_c4_v32/continuation-v1.json'))
            stack.enter_context(patch.object(analysis.controller,'amendment',return_value=amendment))
            stack.enter_context(patch.object(analysis.controller,'recovery',recovery))
            stack.enter_context(patch.object(analysis.controller,'hashed',return_value='b'*64))
            stack.enter_context(patch.object(analysis.controller,'read_json',side_effect=lambda p:snapshot if p.name=='manifest.json' else {'original_three_copy_guard_passed':guard}))
            return analysis.verify_recovery_provenance(corpus)
    def test_c4_discloses_only_its_own_recovered_trial_and_both_provenances(self):
        x=self.provenance('c4')
        self.assertEqual(x['recovered_terminal_trials'],['c4-delete-0-cold'])
        self.assertIn('prior_wikitext_recovery_provenance',x)
        self.assertIn('c4_recovery_provenance',x)
        self.assertIn('campaigns/recovery_v32/audit.json',x['evidence_paths'])
    def test_wiki_retains_its_original_recovered_trial(self):
        x=self.provenance('wikitext')
        self.assertEqual(x['recovered_terminal_trials'],['wikitext-delete-1-cold'])
        self.assertFalse(x['evidence_rewritten'])
    def test_original_failure_cannot_be_relabelled(self):
        with self.assertRaisesRegex(ValueError,'strict guard failure'):self.provenance('c4',guard=True)
    def test_unknown_cause_cannot_be_relabelled(self):
        with self.assertRaisesRegex(ValueError,'cause was invented'):self.provenance('c4',cause='known bug')

if __name__=='__main__':unittest.main()
