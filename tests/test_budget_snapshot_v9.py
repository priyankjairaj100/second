"""Read-only ledger/storage correctness; these are not resource measurements."""
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from src.phase_budget import PhaseBudget, read_budget_snapshot
from src.run_store import canonical_json, read_completed
from src.measured_analysis import _resource_snapshots


class ReadOnlyBudgetTests(unittest.TestCase):
    def test_missing_does_not_create_directory_or_zero_unknown_usage(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'absent'
            result=read_budget_snapshot(path,identity={'fixture':True},phase_cpu_seconds={'software_test':10})
            self.assertEqual(result['status'],'unavailable');self.assertIsNone(result['attempts'])
            self.assertIsNone(result['charged_cpu_seconds']);self.assertFalse(path.exists())
            self.assertIsNone(read_completed(path,{'fixture':True}));self.assertFalse(path.exists())

    def test_all_attempts_unknown_reservations_and_overrun_without_lock_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);identity={'fixture':True};caps={'development':10,'confirmation':20}
            budget=PhaseBudget(path,identity=identity,phase_cpu_seconds=caps)
            budget.reserve('development','unknown',3)
            budget.reserve('development','overrun',2);budget.settle('overrun',12_000_000_000)
            budget.reserve('confirmation','other-phase',4);budget.settle('other-phase',1)
            (path/'ledger.lock').unlink();before={p.name:p.read_bytes() for p in path.iterdir()}
            with patch('src.phase_budget.PhaseBudget.__init__',side_effect=AssertionError('mutable reader')):
                result=read_budget_snapshot(path,identity=identity,phase_cpu_seconds=caps)
            self.assertEqual(set(result['attempts']),{'unknown','overrun','other-phase'})
            self.assertEqual(result['reserved_unknown_attempts'],1)
            self.assertEqual(result['reservation_overrun_attempts'],['overrun'])
            self.assertEqual(result['charged_cpu_seconds'],{'development':15,'confirmation':1})
            self.assertTrue(result['over_cap']['development'])
            self.assertEqual(before,{p.name:p.read_bytes() for p in path.iterdir()})

    def test_binding_bounds_canonical_bytes_and_invalid_debit_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);budget=PhaseBudget(path,identity={'x':1},phase_cpu_seconds={'development':10})
            budget.reserve('development','attempt',3)
            raw=(path/'ledger.json').read_bytes()
            with self.assertRaisesRegex(ValueError,'identity'):
                read_budget_snapshot(path,identity={'x':2},phase_cpu_seconds={'development':10})
            with self.assertRaisesRegex(ValueError,'bounded regular'):
                read_budget_snapshot(path,identity={'x':1},phase_cpu_seconds={'development':10},max_bytes=1)
            (path/'ledger.json').write_bytes(raw+b' ')
            with self.assertRaisesRegex(ValueError,'canonical'):
                read_budget_snapshot(path,identity={'x':1},phase_cpu_seconds={'development':10})
            (path/'ledger.json').write_bytes(raw.replace(b'"charged_cpu_seconds":3',b'"charged_cpu_seconds":2'))
            with self.assertRaisesRegex(ValueError,'pending budget debit'):
                read_budget_snapshot(path,identity={'x':1},phase_cpu_seconds={'development':10})

    def test_symlink_is_rejected_without_following(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);(path/'actual').mkdir();(path/'alias').symlink_to(path/'actual',target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'symbolic'):
                read_budget_snapshot(path/'alias',identity={},phase_cpu_seconds={'software_test':1})

    def test_archive_sizes_include_nontransaction_files_and_deduplicate_hardlinks(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);out=root/'out';out.mkdir()
            (out/'one.bin').write_bytes(b'12345');os.link(out/'one.bin',out/'alias.bin')
            (out/'two.bin').write_bytes(b'abc')
            checked={'inventory':{'source_sha256':{}},'protocol_path':root/'protocol.json',
                     'protocol_sha256':'a'*64,'phase_cpu_seconds':{'software_test':10}}
            ledger,storage=_resource_snapshots(checked,out)
            self.assertEqual(ledger['status'],'unavailable')
            self.assertEqual(storage['status'],'verified_at_read');self.assertEqual(storage['file_paths'],3)
            self.assertEqual(storage['unique_files'],2);self.assertEqual(storage['total_unique_file_bytes'],8)
            self.assertEqual(storage['nontransaction_file_bytes'],8);self.assertEqual(storage['transaction_file_bytes'],0)
            self.assertEqual(sum(info['same_file_as'] is not None for info in storage['files'].values()),1)
            self.assertFalse((root/('phase-cpu-budget-'+'a'*64)).exists())


if __name__=='__main__':unittest.main()
