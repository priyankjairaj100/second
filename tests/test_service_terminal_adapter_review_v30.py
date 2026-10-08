"""Independent named-artifact and continuation checks. No workers execute."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import scripts.continue_full_service_v30 as controller
from src.run_store import canonical_json, digest
from src.service_terminal_evidence_v30 import verify_completed
import tests.test_terminal_evidence_v30 as original_fixture


class ServiceTerminalAdapterTests(unittest.TestCase):
    def setUp(self):
        self.fixture = original_fixture.TerminalEvidenceTests(methodName='test_valid_complete_record_and_both_marker_formats')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.named = copy.deepcopy(self.fixture.terminal)
        self.named.update(schema='adaptive-complete-service-transaction-v30',
                          complete_model=True, complete_state=False,
                          model_artifact=self.named.pop('artifacts')['model'])

    def seal_named(self, value):
        self.fixture.write_terminal(value)
        self.fixture.write_stdout()
        self.fixture.seal()

    def hashes(self):
        return {str(p.relative_to(self.fixture.attempt)): digest(p.read_bytes())
                for p in self.fixture.attempt.rglob('*') if p.is_file()}

    def test_named_mapping_is_read_only_and_follows_receipt_validation(self):
        self.seal_named(self.named)
        before = self.hashes()
        result = verify_completed(self.fixture.attempt)
        self.assertEqual(result['artifacts'], {'model': self.named['model_artifact']})
        self.assertIn('original bytes unchanged', result['artifact_manifest_source'])
        self.assertEqual(before, self.hashes())
        changed = dict(self.named, complete_state=True)
        self.fixture.write_terminal(changed)  # Do not alter the receipt commitment.
        with self.assertRaisesRegex(ValueError, 'stdout terminal digest'):
            verify_completed(self.fixture.attempt)

    def test_complete_named_state_is_required_and_byte_checked(self):
        self.seal_named(dict(self.named, complete_state=True))
        with self.assertRaisesRegex(ValueError, 'output binding'):
            verify_completed(self.fixture.attempt)
        state = b'exact state fixture'
        (self.fixture.attempt/'outputs/state.bin').write_bytes(state)
        named = dict(self.named, complete_state=True,
                     state_artifact={'file': 'state.bin', 'bytes': len(state), 'sha256': digest(state)})
        self.seal_named(named)
        self.assertEqual(set(verify_completed(self.fixture.attempt)['artifacts']), {'model', 'state'})
        (self.fixture.attempt/'outputs/state.bin').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'artifact hash or byte count'):
            verify_completed(self.fixture.attempt)

    def test_unknown_schema_and_incomplete_model_cannot_use_adapter(self):
        for changed in (dict(self.named, schema='unregistered-format'), dict(self.named, complete_model=False)):
            self.seal_named(changed)
            with self.assertRaises(ValueError):
                verify_completed(self.fixture.attempt)


class ContinuationComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.campaign = Path(self.temporary.name)
        self.current = self.campaign/'attempts/current'
        self.current.mkdir(parents=True)
        self.program = {'trials': [{'id': 'reference'},
            {'id': 'current', 'compare_to': [{'trial': 'reference', 'artifacts': ['model', 'state']}]}]}
        (self.campaign/'program.json').write_bytes(canonical_json(self.program))
        self.model = {'file': 'model.bin', 'bytes': 7, 'sha256': 'a'*64}
        self.state = {'file': 'state.bin', 'bytes': 9, 'sha256': 'b'*64}
        self.records = {name: {'artifacts': {'model': dict(self.model), 'state': dict(self.state)}}
                        for name in ('reference', 'current')}

    def verify(self):
        with patch.object(controller, 'C', self.campaign), \
             patch('src.service_terminal_evidence_v30.verify_completed',
                   side_effect=lambda path: self.records[path.name]) as reader:
            result = controller.completed('current')
            self.assertEqual(reader.call_count, 2)
            return result

    def test_missing_sidecar_still_checks_every_registered_artifact(self):
        self.assertEqual(self.verify(), self.records['current'])
        self.assertFalse((self.current/'cross-method-agreement.json').exists())
        self.records['current']['artifacts']['state']['bytes'] += 1
        with self.assertRaisesRegex(ValueError, 'registered complete outputs disagree'):
            self.verify()

    def test_true_sidecar_cannot_hide_a_mismatch(self):
        (self.current/'cross-method-agreement.json').write_bytes(canonical_json({'all_equal': True}))
        self.records['current']['artifacts']['model']['sha256'] = 'c'*64
        with self.assertRaisesRegex(ValueError, 'registered complete outputs disagree'):
            self.verify()

    def test_sidecar_must_match_the_recomputed_comparison(self):
        comparisons = [dict(reference_trial='reference', artifact=name, equal=True,
                            actual_sha256=entry['sha256'], reference_sha256=entry['sha256'])
                       for name, entry in (('model', self.model), ('state', self.state))]
        sidecar = self.current/'cross-method-agreement.json'
        sidecar.write_bytes(canonical_json(dict(all_equal=True, comparisons=comparisons)))
        self.assertEqual(self.verify(), self.records['current'])
        comparisons[1]['reference_sha256'] = 'd'*64
        sidecar.write_bytes(canonical_json(dict(all_equal=True, comparisons=comparisons)))
        with self.assertRaisesRegex(ValueError, 'sidecar differs'):
            self.verify()

    def test_cycles_and_forward_comparisons_are_rejected_without_recursion(self):
        self.program['trials'][1]['compare_to'] = [{'trial': 'current'}]
        (self.campaign/'program.json').write_bytes(canonical_json(self.program))
        with self.assertRaisesRegex(ValueError, 'earlier registered trial'):
            self.verify()


if __name__ == '__main__':
    unittest.main()
