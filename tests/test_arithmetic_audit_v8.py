"""Instrumentation correctness fixtures, not empirical measurements."""
from fractions import Fraction as Q
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import tracemalloc
import unittest
from unittest.mock import patch

from src.arithmetic_audit import ArithmeticAudit, audit_local_run


class ArithmeticAuditTests(unittest.TestCase):
    def test_constructor_and_fast_allocator_count_once_without_changing_values(self):
        with ArithmeticAudit() as audit:
            result = Q(1, 2) + Q(1, 3)
        data = audit.payload()
        self.assertEqual(result, Q(5, 6))
        self.assertEqual(data['constructed_fraction_endpoints']['fraction_objects'], 3)
        self.assertEqual(data['allocator_returns'], {'__new__': 2, '_from_coprime_ints': 1})
        self.assertEqual(data['constructed_fraction_endpoints']['numerator_bits_sum'], 5)
        self.assertEqual(data['constructed_fraction_endpoints']['denominator_bits_sum'], 7)
        self.assertFalse(data['clean_latency_eligible'])
        self.assertFalse(data['numerical_functions_replaced'])

    def test_large_values_report_only_endpoint_bit_lengths(self):
        with ArithmeticAudit(sample_every=1) as audit:
            value = Q(2 ** 20000 + 1, 3 ** 15000)
            value *= value
        data = audit.payload()
        self.assertGreater(data['constructed_fraction_endpoints']['maximum_numerator_bits'], 20000)
        self.assertGreater(data['constructed_fraction_endpoints']['maximum_denominator_bits'], 20000)
        encoded = json.dumps(data)
        self.assertLess(len(encoded), 50000)
        self.assertNotIn('"numerator":', encoded)
        self.assertNotIn('"denominator":', encoded)

    def test_initial_values_are_separate_from_new_constructions(self):
        initial = Q(2 ** 1234 + 1, 17)
        with ArithmeticAudit() as audit:
            value = Q(1, 2)
        data = audit.payload()
        self.assertGreaterEqual(data['initial_live_fraction_snapshot']['maximum_numerator_bits'], 1235)
        self.assertEqual(data['constructed_fraction_endpoints']['fraction_objects'], 1)
        self.assertEqual(data['constructed_fraction_endpoints']['maximum_numerator_bits'], 1)
        self.assertEqual(initial.denominator, 17)
        self.assertEqual(value.denominator, 2)

    def test_phase_attribution_is_bounded_and_overflow_preserves_totals(self):
        with ArithmeticAudit(max_attributions=2) as audit:
            for index in range(6):
                with audit.phase('phase-' + str(index)):
                    Q(index)
        data = audit.payload()
        self.assertEqual(len(data['by_phase']), 3)
        self.assertEqual(data['by_phase']['<other>']['fraction_objects'], 4)
        self.assertEqual(sum(v['fraction_objects'] for v in data['by_phase'].values()), 6)

    def test_existing_profiler_is_preserved_and_nested_audit_is_rejected(self):
        def existing(frame, event, arg):
            return None
        previous = sys.getprofile()
        sys.setprofile(existing)
        try:
            with self.assertRaisesRegex(RuntimeError, 'existing profiler'):
                with ArithmeticAudit():
                    self.fail('nested observer ran')
            self.assertIs(sys.getprofile(), existing)
        finally:
            sys.setprofile(previous)
        with ArithmeticAudit() as outer:
            with self.assertRaisesRegex(RuntimeError, 'existing profiler'):
                with ArithmeticAudit():
                    self.fail('nested observer ran')
            Q(1, 2)
        self.assertEqual(outer.payload()['constructed_fraction_endpoints']['fraction_objects'], 1)

    def test_exception_cleanup_restores_profiler_without_hiding_failure(self):
        previous = sys.getprofile()
        audit = ArithmeticAudit()
        with self.assertRaisesRegex(ZeroDivisionError, 'controlled'):
            with audit:
                Q(1, 2)
                raise ZeroDivisionError('controlled')
        self.assertIs(sys.getprofile(), previous)
        self.assertEqual(audit.payload()['exception_type'], 'ZeroDivisionError')
        with self.assertRaisesRegex(RuntimeError, 'single-use'):
            with audit:
                pass

    def test_failed_constructor_does_not_count_a_finished_fraction(self):
        with ArithmeticAudit() as audit:
            with self.assertRaises(ZeroDivisionError):
                Q(1, 0)
        data = audit.payload()
        self.assertEqual(data['constructed_fraction_endpoints']['fraction_objects'], 0)
        self.assertGreater(data['events']['allocator_returns_without_fraction'], 0)

    def test_runner_owned_tracemalloc_scopes_are_observed_without_nesting(self):
        from src.experiment_runner import measure
        self.assertFalse(tracemalloc.is_tracing())
        with ArithmeticAudit() as audit:
            result, metrics = measure(lambda: [Q(index, 13) for index in range(20)])
        data = audit.payload()
        self.assertFalse(tracemalloc.is_tracing())
        self.assertEqual(len(result), 20)
        self.assertGreater(data['memory']['maximum_observed_traced_peak_bytes'], 0)
        self.assertIn('before_tracemalloc_stop', [v['reason'] for v in data['memory']['samples']])
        self.assertGreater(metrics['peak_python_bytes'], 0)

    def test_unavailable_tracemalloc_stays_null_and_existing_trace_is_preserved(self):
        with ArithmeticAudit() as audit:
            Q(1)
        self.assertIsNone(audit.payload()['memory']['maximum_observed_traced_peak_bytes'])
        tracemalloc.start()
        try:
            with ArithmeticAudit() as traced:
                Q(1)
            self.assertTrue(tracemalloc.is_tracing())
            self.assertTrue(traced.payload()['memory']['tracemalloc_at_entry'])
        finally:
            tracemalloc.stop()

    def test_thread_and_child_work_are_explicitly_uncovered(self):
        with ArithmeticAudit() as audit:
            worker = threading.Thread(target=lambda: Q(1, 7))
            worker.start()
            worker.join()
            subprocess.run([sys.executable, '-c', 'from fractions import Fraction; Fraction(1,7)'], check=True)
        data = audit.payload()
        self.assertEqual(data['audit_status'], 'incomplete')
        self.assertFalse(data['coverage']['whole_runner_coverage_eligible'])
        self.assertGreater(data['coverage']['thread_launch_attempts'], 0)
        self.assertGreater(data['coverage']['child_process_launch_attempts'], 0)

    def test_replaced_profiler_or_observer_error_marks_audit_incomplete(self):
        with ArithmeticAudit() as audit:
            sys.setprofile(None)
            Q(1)
        self.assertTrue(audit.payload()['coverage']['profile_replaced'])
        self.assertEqual(audit.payload()['audit_status'], 'incomplete')
        with ArithmeticAudit() as interrupted:
            current = sys.getprofile()
            sys.setprofile(None)
            Q(1, 5)
            sys.setprofile(current)
        self.assertFalse(interrupted.payload()['coverage']['profile_replaced'])
        self.assertGreater(interrupted.payload()['coverage']['profile_mutation_attempts'], 0)
        self.assertEqual(interrupted.payload()['audit_status'], 'incomplete')
        with ArithmeticAudit() as broken:
            with patch.object(broken, '_attribution', side_effect=RuntimeError('diagnostic-only')):
                value = Q(1, 3)
        self.assertEqual(value, Q(1, 3))
        self.assertEqual(broken.payload()['audit_status'], 'incomplete')
        self.assertIn('RuntimeError', broken.payload()['coverage']['observer_errors'])

    @staticmethod
    def manifest_fixture(root):
        from tests.test_checkpoint_adapter import checkpoint_fixture, write_checkpoint
        from src.target_manifest import TargetRecipe
        from src.chart_construction import ChartRecipe
        from src.run_store import canonical_json, digest
        config, weights, _ = checkpoint_fixture()
        checkpoint = root / 'checkpoint'
        checkpoint.mkdir()
        write_checkpoint(checkpoint, config, weights)
        provenance = {'dataset_id': 'software', 'dataset_revision': 'fixture-v1', 'split': 'test',
                      'license': 'test', 'tokenizer_id': 'integer-fixture', 'tokenizer_revision': 'v1'}
        calibration = {'schema': 'prepared-token-records-v1', 'provenance': provenance,
                       'records': [{'id': 'a', 'tokens': [0, 1]}, {'id': 'b', 'tokens': [1, 0]}]}
        heldout = {'schema': 'prepared-token-records-v1', 'provenance': provenance,
                   'records': [{'id': 'heldout', 'tokens': [2, 1]}]}
        refs = {}
        for name, data in (('calibration', calibration), ('heldout', heldout),
                           ('protocol', {'phase': 'software_test'})):
            raw = canonical_json(data)
            (root / (name + '.json')).write_bytes(raw)
            refs[name] = {'path': name + '.json', 'sha256': digest(raw)}
        manifest = dict(schema='calibration-run-v1', root_id='r', request_id='q', configuration_id='c',
                        repeat_index=0, phase='software_test',
                        checkpoint={'path': 'checkpoint', 'files_sha256': {
                            p.name: digest(p.read_bytes()) for p in checkpoint.iterdir()}, 'max_parameter_elements': 1000},
                        deleted_ids=['a'], target=TargetRecipe(original_token_count=4).payload(),
                        chart=ChartRecipe(mode='none').payload(),
                        method_order=['repair', 'indexed_fresh', 'direct_fresh'], **refs)
        path = root / 'manifest.json'
        path.write_bytes(canonical_json(manifest))
        return path

    def test_actual_local_runner_preserves_model_and_state_artifacts(self):
        from src.experiment_runner import run_manifest
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = self.manifest_fixture(root)
            plain = run_manifest(manifest, root / 'plain')
            report = audit_local_run('experiment', manifest, root / 'observed', root / 'audit.json', sample_every=4096)
            observed = json.loads((root / 'observed' / 'result.json').read_text())
            self.assertEqual(report['runner_status'], 'complete')
            self.assertEqual(report['audit_status'], 'complete_declared_scope')
            self.assertFalse(report['clean_latency_eligible'])
            self.assertTrue(observed['profiler_active'])
            self.assertNotIn('profiler_active', plain)
            for method in ('repair', 'indexed_fresh', 'direct_fresh'):
                self.assertTrue(observed['methods'][method]['profiler_active'])
                self.assertNotIn('profiler_active', plain['methods'][method])
                self.assertEqual(observed['methods'][method]['model_sha256'], plain['methods'][method]['model_sha256'])
                self.assertEqual(observed['methods'][method]['state_sha256'], plain['methods'][method]['state_sha256'])
            self.assertGreater(report['constructed_fraction_endpoints']['fraction_objects'], 0)
            self.assertEqual(report['identity']['runner_output']['protocol_sha256'], plain['protocol_sha256'])
            self.assertIn('precision_bits', report['identity']['declared_chart'])
            self.assertGreater(report['artifacts']['total_listed_bytes'], 0)
            self.assertEqual(json.loads((root / 'audit.json').read_text())['audit_source_sha256'], report['audit_source_sha256'])
            with self.assertRaisesRegex(FileExistsError, 'fresh runner'):
                audit_local_run('experiment', manifest, root / 'observed', root / 'other-audit.json')

    def test_wrapper_preserves_runner_failure_and_writes_diagnostic_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = root / 'bad.json'
            manifest.write_text('{"schema":"wrong"}')
            with self.assertRaises(ValueError):
                audit_local_run('experiment', manifest, root / 'results', root / 'audit.json')
            report = json.loads((root / 'audit.json').read_text())
            self.assertEqual(report['runner_failure']['type'], 'ValueError')
            self.assertEqual(report['exception_type'], 'ValueError')
            self.assertIsNone(sys.getprofile())

    def test_unsupported_or_overlapping_outputs_fail_before_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaisesRegex(ValueError, 'current-process'):
                audit_local_run('isolated', root / 'unused.json', root / 'out', root / 'audit.json')
            with self.assertRaisesRegex(ValueError, 'outside'):
                audit_local_run('experiment', root / 'unused.json', root / 'out', root / 'out' / 'audit.json')
            self.assertFalse((root / 'out').exists())

    def test_receipt_failure_does_not_replace_original_runner_exception(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = root / 'bad.json'
            manifest.write_text('{"schema":"wrong"}')
            with patch('src.arithmetic_audit._write_report', side_effect=OSError('controlled receipt failure')):
                with self.assertRaises(ValueError) as caught:
                    audit_local_run('experiment', manifest, root / 'out', root / 'audit.json')
            self.assertIn('Arithmetic audit receipt failed: OSError', caught.exception.__notes__)
            self.assertIsNone(sys.getprofile())

    def test_changed_manifest_during_execution_marks_receipt_incomplete(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = root / 'input.json'
            manifest.write_text('{"identity":"before"}')
            def mutate(*args, **kwargs):
                manifest.write_text('{"identity":"after"}')
                return {'status': 'complete'}
            with patch('src.experiment_runner.run_manifest', side_effect=mutate):
                report = audit_local_run('experiment', manifest, root / 'out', root / 'audit.json')
            self.assertEqual(report['audit_status'], 'incomplete')
            self.assertFalse(report['source_stability']['manifest_unchanged'])
            self.assertFalse(report['coverage']['whole_runner_coverage_eligible'])


if __name__ == '__main__':
    unittest.main()
