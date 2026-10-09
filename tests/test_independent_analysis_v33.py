"""Recovery-analysis contract fixtures. No empirical worker is launched."""
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import analyze_independent_requests_v33 as analysis


class RecoveryAnalysisTests(unittest.TestCase):
    def provenance(self, corpus, *, guard=False, cause='unknown'):
        root = Path('/fixture')
        incident = 'campaigns/independent_wikitext_v32/attempts/wikitext-delete-1-cold'
        recovery = SimpleNamespace(
            INCIDENT_RELATIVE=incident,
            AUDIT_RELATIVE='campaigns/recovery_v32/independent-audit.json',
            SNAPSHOT_RELATIVE='campaigns/recovery_v32/snapshot',
            verify_completed=lambda path: {'model_artifact': {'sha256': 'a' * 64}},
        )
        snapshot = {'cause': cause, 'files': {
            'outputs/progress.json': {}, 'outputs/completion.json': {}, 'sealed-progress.json': {}}}
        amendment = {'cause': cause, 'prior_text_bindings': {
            'campaigns/independent_wikitext_v32/attempts/wikitext-root-prepare/plan.json': {}}}
        audit = {'original_three_copy_guard_passed': guard}
        with ExitStack() as stack:
            stack.enter_context(patch.object(analysis, 'ROOT', root))
            stack.enter_context(patch.object(analysis.controller, 'AMENDMENT', root / 'campaigns/continuation.json'))
            stack.enter_context(patch.object(analysis.controller, 'amendment', return_value=amendment))
            stack.enter_context(patch.object(analysis.controller, 'recovery', recovery))
            stack.enter_context(patch.object(analysis.controller, 'hashed', return_value='b' * 64))
            stack.enter_context(patch.object(analysis.controller, 'read_json',
                side_effect=lambda path: snapshot if path.name == 'manifest.json' else audit))
            return analysis.verify_recovery_provenance(corpus)

    def test_wikitext_reports_only_the_pinned_recovered_trial(self):
        result = self.provenance('wikitext')
        self.assertEqual(result['recovered_terminal_trials'], ['wikitext-delete-1-cold'])
        self.assertFalse(result['cross_corpus_prerequisite'])
        self.assertFalse(result['incident_original_strict_three_copy_guard_passed'])
        self.assertFalse(result['evidence_rewritten'])
        self.assertIn('campaigns/recovery_v32/snapshot/outputs/progress.json', result['evidence_paths'])
        self.assertIn('campaigns/independent_wikitext_v32/attempts/wikitext-delete-1-cold/outputs/progress.json', result['evidence_paths'])

    def test_c4_binds_the_incident_without_claiming_its_own_exception(self):
        result = self.provenance('c4')
        self.assertEqual(result['recovered_terminal_trials'], [])
        self.assertTrue(result['cross_corpus_prerequisite'])
        self.assertFalse(result['incident_original_strict_three_copy_guard_passed'])
        self.assertIn('campaigns/continuation.json', result['evidence_paths'])

    def test_failed_original_guard_cannot_be_relabelled(self):
        with self.assertRaisesRegex(ValueError, 'strict guard failure'):
            self.provenance('wikitext', guard=True)

    def test_unknown_cause_cannot_be_relabelled(self):
        with self.assertRaisesRegex(ValueError, 'cause was invented'):
            self.provenance('c4', cause='filesystem defect')


if __name__ == '__main__':
    unittest.main()
