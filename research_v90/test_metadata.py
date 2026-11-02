"""Pure filesystem/admission guards; no model execution or empirical evidence."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import hashlib
import io
import json
import os
import unittest

from research_v90 import run_store as store, phase_budget as budget, worker_control as control
from src import run_store as historical


class MetadataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def test_oversize_refuses_before_directory_or_temporary_file(self):
        target = self.root/'absent/file'
        with patch.object(store.tempfile, 'mkstemp') as allocate:
            with self.assertRaisesRegex(ValueError, 'byte limit'):
                store.atomic_write(target, b'x'*(store.METADATA_BYTES+1))
            allocate.assert_not_called()
        self.assertFalse(target.parent.exists())

    def test_exact_ceiling_and_replacement_overflow_preserve_old_bytes(self):
        target = self.root/'record'
        payload = b'x'*store.METADATA_BYTES
        store.atomic_write(target, payload)
        self.assertEqual(store.read_metadata(target), payload)
        before = target.stat()
        with self.assertRaises(ValueError):
            store.atomic_write(target, payload+b'x')
        self.assertEqual(target.read_bytes(), payload)
        self.assertEqual(target.stat().st_ino, before.st_ino)
        self.assertEqual(list(self.root.glob('.pending-*')), [])

    def test_failed_replace_leaves_old_commit_and_no_false_new_record(self):
        target = self.root/'record'; target.write_bytes(b'old')
        with patch.object(store.os, 'replace', side_effect=OSError('fixture full device')):
            with self.assertRaises(OSError):
                store.atomic_write(target, b'new')
        self.assertEqual(target.read_bytes(), b'old')
        self.assertEqual(list(self.root.glob('.pending-*')), [])

    def test_symbolic_output_ancestor_is_refused(self):
        actual = self.root/'actual'; actual.mkdir()
        (self.root/'alias').symlink_to(actual, target_is_directory=True)
        with self.assertRaises(ValueError):
            store.atomic_write(self.root/'alias/file', b'data')
        self.assertEqual(list(actual.iterdir()), [])

    def test_oversize_existing_read_and_symbolic_read_refuse(self):
        target = self.root/'large'; target.write_bytes(b'x'*(store.METADATA_BYTES+1))
        with self.assertRaises(ValueError): store.read_metadata(target)
        target.write_bytes(b'ok'); (self.root/'alias').symlink_to(target)
        with self.assertRaises(ValueError): store.read_metadata(self.root/'alias')

    def test_nonregular_read_refuses_without_waiting_for_pipe_writer(self):
        pipe = self.root/'pipe'; os.mkfifo(pipe)
        with self.assertRaisesRegex(ValueError, 'regular file'): store.read_metadata(pipe)

    def test_changed_read_identity_refuses(self):
        target = self.root/'record'; target.write_bytes(b'old')
        original = store.os.read; replaced = False
        def mutate(fd, size):
            nonlocal replaced
            chunk = original(fd, size)
            if not replaced:
                replaced = True
                other = self.root/'other'; other.write_bytes(b'new'); other.replace(target)
            return chunk
        with patch.object(store.os, 'read', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'changed'):
                store.read_metadata(target)

    def test_identity_overflow_does_not_consume_worker_directory(self):
        with self.assertRaises(ValueError):
            store.RunStore(self.root/'worker', {'large': 'x'*store.METADATA_BYTES})
        self.assertFalse((self.root/'worker').exists())

    def test_existing_empty_partial_and_complete_roots_never_retry(self):
        for state in ('empty', 'partial', 'complete'):
            with self.subTest(state=state):
                root = self.root/state; root.mkdir()
                if state != 'empty': (root/'sentinel').write_bytes(state.encode())
                before = sorted((p.name, p.read_bytes()) for p in root.iterdir())
                with self.assertRaises(FileExistsError): store.RunStore(root, {'id': state})
                self.assertEqual(before, sorted((p.name, p.read_bytes()) for p in root.iterdir()))

    def test_existing_attempt_is_not_renumbered(self):
        record = store.RunStore(self.root/'worker', {})
        (record.root/'attempt-0001').mkdir()
        with self.assertRaises(FileExistsError): record.claim()
        self.assertFalse((record.root/'attempt-0002').exists())

    def test_only_fixed_artifacts_and_complete_hashes(self):
        identity = {'id': 'fixture'}
        with store.RunStore(self.root/'worker', identity) as record:
            for name in ('other.json', '../escape', 'status.json'):
                with self.assertRaises(ValueError): record.write_artifact(name, b'{}')
            for name in store.ARTIFACT_NAMES: record.write_artifact(name, b'{}')
            with self.assertRaises(ValueError): record.write_artifact('request.json', b'{}')
            finished = record.finish({'status': 'complete', 'outcome': {'status': 'failed'}})
        self.assertEqual(finished, historical.read_completed(record.root, identity))
        self.assertEqual(finished, store.read_completed(record.root, identity))
        self.assertEqual(finished['outcome']['status'], 'failed')
        (record.attempt/'request.json').write_bytes(b'changed')
        with self.assertRaises(ValueError): store.read_completed(record.root, identity)

    def test_failure_message_is_kept_verbatim_and_not_promoted(self):
        message = 'negative finding: '+('exact diagnostic; '*1000)
        with self.assertRaisesRegex(RuntimeError, 'negative finding'):
            with store.RunStore(self.root/'worker', {}) as record:
                record.write_artifact('request.json', b'{}')
                raise RuntimeError(message)
        result = json.loads((record.root/'result.json').read_bytes())
        self.assertEqual(result['failure']['message'], message)
        self.assertEqual(result['status'], 'failed')
        self.assertIsNone(store.read_completed(record.root, {}))

    def test_log_summary_byte_encoding_fits_without_new_truncation(self):
        # The historical 32KiB tail is retained exactly, including worst-case
        # six-byte JSON escapes. No new controller-specific truncation is used.
        raw = b'\xff' * 32768
        result = control._log_summary(io.BytesIO(raw))
        self.assertEqual(result['tail_utf8'], raw.decode('utf8', errors='replace'))
        self.assertLess(len(store.canonical_json(result)), store.METADATA_BYTES)

    def test_existing_worker_refuses_before_process_launch(self):
        limits = control.WorkerLimits(3, 2, 2**30, 1, (0,))
        target = self.root/'worker'; target.mkdir()
        with patch.object(control.WorkerLimits, 'check_host'), patch.object(control.subprocess, 'Popen') as launch:
            with self.assertRaises(FileExistsError):
                control.run_limited(['/bin/true'], target, limits, identity={}, cwd=self.root)
            launch.assert_not_called()


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()/'budget'
        self.identity = {'id': 'new-transfer-fixture'}
        self.caps = {'numerical': 1000}

    def make(self):
        return budget.PhaseBudget(self.root, identity=self.identity, phase_cpu_seconds=self.caps)

    def test_unknown_reservation_is_fully_charged_after_reopen(self):
        first = self.make(); first.reserve('numerical', 'one', 600)
        second = self.make(); before = (self.root/'ledger.json').read_bytes()
        with self.assertRaises(budget.BudgetExhausted): second.reserve('numerical', 'two', 401)
        self.assertEqual((self.root/'ledger.json').read_bytes(), before)
        self.assertEqual(second.snapshot()['charged_cpu_seconds'], {'numerical': 600})
        self.assertEqual(second.snapshot()['attempts']['one']['state'], 'reserved')

    def test_only_observed_usage_settles_and_overrun_is_not_clipped(self):
        record = self.make(); record.reserve('numerical', 'one', 10)
        for invalid in (None, -1, True):
            with self.assertRaises(ValueError): record.settle('one', invalid)
        self.assertEqual(record.snapshot()['charged_cpu_seconds']['numerical'], 10)
        self.assertEqual(record.settle('one', 11_000_000_001)['charged_cpu_seconds'], 12)
        with self.assertRaises(ValueError): record.settle('one', 1)

    def test_twenty_attempt_bound_and_reused_id_preserve_ledger(self):
        record = self.make()
        for i in range(20): record.reserve('numerical', str(i), 1)
        before = (self.root/'ledger.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'census'): record.reserve('numerical', 'overflow', 1)
        with self.assertRaisesRegex(ValueError, 'exists'): record.reserve('numerical', '0', 1)
        self.assertEqual((self.root/'ledger.json').read_bytes(), before)

    def test_oversize_reservation_keeps_previous_debits(self):
        record = self.make(); record.reserve('numerical', 'one', 100)
        before = (self.root/'ledger.json').read_bytes()
        with self.assertRaises(ValueError): record.reserve('numerical', 'x'*store.METADATA_BYTES, 1)
        self.assertEqual((self.root/'ledger.json').read_bytes(), before)
        self.assertEqual(record.snapshot()['charged_cpu_seconds']['numerical'], 100)

    def test_missing_existing_ledger_never_reinitializes_debits(self):
        self.root.mkdir()
        with self.assertRaisesRegex(ValueError, 'no committed ledger'): self.make()
        self.assertFalse((self.root/'ledger.json').exists())

    def test_snapshot_is_read_only_and_historical_reader_compatible(self):
        from src.phase_budget import read_budget_snapshot as old_read
        record = self.make(); record.reserve('numerical', 'one', 600)
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        new = budget.read_budget_snapshot(self.root, identity=self.identity, phase_cpu_seconds=self.caps)
        old = old_read(self.root, identity=self.identity, phase_cpu_seconds=self.caps)
        self.assertEqual(new, old)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})

    def test_parent_sources_are_still_exact(self):
        root = Path(__file__).resolve().parents[1]
        for name, expected in json.loads((root/'research_v90/PARENT_BINDINGS.json').read_bytes()).items():
            raw = (root/name).read_bytes()
            self.assertEqual(expected, {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})


if __name__ == '__main__': unittest.main()
