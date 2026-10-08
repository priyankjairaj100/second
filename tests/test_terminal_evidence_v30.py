"""Tamper checks for immutable research completion evidence."""
import copy
from pathlib import Path
import tempfile
import unittest

from src.run_store import canonical_json, digest, strict_json
from src.terminal_evidence_v30 import verify_completed


class TerminalEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.attempt = Path(self.temporary.name)/'trial-001'
        self.inner = self.attempt/'worker/attempt-0001'
        self.inner.mkdir(parents=True)
        (self.attempt/'outputs').mkdir()
        self.plan = {'schema': 'software-fixture-plan'}
        self.write('plan.json', self.plan)
        self.plan_sha = digest((self.attempt/'plan.json').read_bytes())
        self.worker_identity = {'campaign': 'fixture', 'plan_sha256': self.plan_sha}
        self.request = {'command': ['python', 'worker.py', 'plan.json'], 'cwd': '/fixture',
                        'limits': {'cpu_seconds': 3}}
        self.identity = dict(self.request, identity=self.worker_identity)
        self.write('worker/identity.json', self.identity)
        self.write('worker/attempt-0001/request.json', self.request)
        output = b'fixture model bytes'
        (self.attempt/'outputs/model.bin').write_bytes(output)
        self.terminal = {'status': 'complete', 'plan_sha256': self.plan_sha,
            'artifacts': {'model': {'file': 'model.bin', 'bytes': len(output), 'sha256': digest(output)}}}
        self.write_terminal(self.terminal)
        self.write_stdout()
        self.debit = {'state': 'settled', 'phase': 'feasibility', 'observed_cpu_ns': 1_250_000_000,
                      'charged_cpu_seconds': 2, 'reserved_cpu_seconds': 5}
        self.outcome = {'status': 'complete', 'returncode': 0}
        self.receipt = {'status': 'complete', 'attempt': 'attempt-0001', 'outcome': self.outcome,
            'worker_identity': self.worker_identity, 'identity_sha256': digest(canonical_json(self.identity)),
            'budget_attempt_id': 'test-attempt', 'budget_debit': self.debit,
            'resource_usage': {'total_cpu_ns': self.debit['observed_cpu_ns']}}
        self.seal()

    def write(self, relative, value):
        (self.attempt/relative).write_bytes(canonical_json(value))

    def write_terminal(self, value):
        for name in ('outputs/completion.json', 'outputs/progress.json', 'sealed-progress.json'):
            self.write(name, value)

    def write_stdout(self, marker=None):
        marker = marker or {'phase': 'terminal_record_committed',
                            'sha256': digest((self.attempt/'outputs/completion.json').read_bytes())}
        log = canonical_json({'phase': 'complete'})+b'\n'+canonical_json(marker)+b'\n'
        self.write('worker/attempt-0001/stdout-summary.json',
                   {'bytes': len(log), 'sha256': digest(log), 'tail_max_bytes': 32768,
                    'tail_utf8': log.decode()})

    def seal(self):
        self.receipt['artifacts'] = {p.name: {'bytes': p.stat().st_size, 'sha256': digest(p.read_bytes())}
                                     for p in self.inner.iterdir() if p.is_file()}
        self.write('worker/result.json', self.receipt)
        self.write('transaction.json', {'worker_outcome': self.outcome,
            'receipt_sha256': digest((self.attempt/'worker/result.json').read_bytes()),
            'budget': {'attempts': {'test-attempt': self.debit}}})

    def test_valid_complete_record_and_both_marker_formats(self):
        self.assertEqual(verify_completed(self.attempt), self.terminal)
        self.write_stdout({'terminal_sha256': digest((self.attempt/'outputs/completion.json').read_bytes())})
        self.seal()
        self.assertEqual(verify_completed(self.attempt), self.terminal)

    def test_coherent_three_file_rewrite_fails_stdout_commitment(self):
        changed = dict(self.terminal, invented_result=True)
        self.write_terminal(changed)
        with self.assertRaisesRegex(ValueError, 'stdout terminal digest'):
            verify_completed(self.attempt)

    def test_changed_receipt_and_changed_receipt_artifact_fail(self):
        original = (self.attempt/'worker/result.json').read_bytes()
        self.write('worker/result.json', dict(self.receipt, invented_result=True))
        with self.assertRaisesRegex(ValueError, 'receipt digest'):
            verify_completed(self.attempt)
        (self.attempt/'worker/result.json').write_bytes(original)
        self.write('worker/attempt-0001/stdout-summary.json', {'tail_utf8': 'forged'})
        with self.assertRaisesRegex(ValueError, 'artifact hash or byte count'):
            verify_completed(self.attempt)

    def test_unsettled_or_inconsistent_cpu_charge_fails(self):
        original = copy.deepcopy(self.debit)
        for changed in (dict(original, state='reserved'), dict(original, observed_cpu_ns=None),
                        dict(original, charged_cpu_seconds=1)):
            self.debit = changed
            self.receipt['budget_debit'] = changed
            self.seal()
            with self.subTest(debit=changed), self.assertRaises(ValueError):
                verify_completed(self.attempt)

    def test_plan_identity_change_fails(self):
        self.write('plan.json', dict(self.plan, changed=True))
        with self.assertRaisesRegex(ValueError, 'plan identity'):
            verify_completed(self.attempt)

    def test_output_hash_and_byte_count_are_checked(self):
        (self.attempt/'outputs/model.bin').write_bytes(b'changed bytes')
        with self.assertRaisesRegex(ValueError, 'artifact hash or byte count'):
            verify_completed(self.attempt)
        changed = copy.deepcopy(self.terminal)
        raw = (self.attempt/'outputs/model.bin').read_bytes()
        changed['artifacts']['model']['sha256'] = digest(raw)
        self.write_terminal(changed)
        self.write_stdout()
        self.seal()
        with self.assertRaisesRegex(ValueError, 'artifact hash or byte count'):
            verify_completed(self.attempt)

    def test_missing_and_duplicate_terminal_markers_fail(self):
        for log in ('{"phase":"complete"}\n',
                    ''.join(canonical_json({'terminal_sha256': digest(canonical_json(self.terminal))}).decode()+'\n'
                            for _ in range(2))):
            encoded = log.encode()
            self.write('worker/attempt-0001/stdout-summary.json',
                       {'bytes': len(encoded), 'sha256': digest(encoded), 'tail_max_bytes': 32768,
                        'tail_utf8': log})
            self.seal()
            with self.assertRaisesRegex(ValueError, 'stdout terminal digest'):
                verify_completed(self.attempt)

    def test_trailing_partial_log_does_not_hide_terminal_marker(self):
        terminal_sha = digest(canonical_json(self.terminal))
        log = 'partial prefix\n'+canonical_json({'terminal_sha256': terminal_sha}).decode()+'\n'
        self.write('worker/attempt-0001/stdout-summary.json',
                   {'bytes': 100000, 'sha256': '1'*64, 'tail_max_bytes': 32768, 'tail_utf8': log})
        self.seal()
        self.assertEqual(verify_completed(self.attempt), self.terminal)

    def test_path_traversal_and_symlink_artifacts_fail(self):
        original = copy.deepcopy(self.terminal)
        changed = copy.deepcopy(original)
        changed['artifacts']['model']['file'] = '../model.bin'
        self.write_terminal(changed)
        self.write_stdout()
        self.seal()
        with self.assertRaisesRegex(ValueError, 'unsafe evidence basename'):
            verify_completed(self.attempt)
        self.write_terminal(original)
        self.write_stdout()
        self.seal()
        path = self.attempt/'outputs/model.bin'
        raw = path.read_bytes()
        path.unlink()
        other = Path(self.temporary.name)/'outside.bin'
        other.write_bytes(raw)
        path.symlink_to(other)
        with self.assertRaisesRegex(ValueError, 'unsafe evidence file'):
            verify_completed(self.attempt)


if __name__ == '__main__':
    unittest.main()
