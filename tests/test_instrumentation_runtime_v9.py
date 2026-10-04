"""Execution contract correctness fixtures, not research measurements."""
from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import tempfile
import tracemalloc
import unittest
from unittest.mock import patch

from src.experiment_runner import _commit_state, _run_manifest, measure
from src.instrumentation import instrumentation_scope, instrumentation_state
from src.run_store import RunStore, canonical_json, strict_json
from src.runtime_contract import capture_runtime_contract, validate_runtime_contract, verify_runtime_contract
from src.service_telemetry import ServiceTelemetry, _CURRENT, operation
from tests import test_aggregate_response_service as aggregate_fixture
from tests import test_isolated_comparison_v7 as isolated_fixture


class InstrumentationTests(unittest.TestCase):
    def test_clean_bypasses_collectors_and_lazy_diagnostics(self):
        with instrumentation_scope('clean'):
            collector = ServiceTelemetry(clock=lambda: self.fail('optional clock called'))
            @operation
            def calculation():
                self.assertIsNone(_CURRENT.get())
                self.assertFalse(collector.diagnostic('stage', 'event', build=lambda _: self.fail('diagnostic builder called')))
                with collector.span('output'):
                    return 7
            self.assertEqual(calculation(telemetry=collector), 7)
            self.assertFalse(collector.payload()['instrumented'])
            self.assertIsNone(collector.payload()['details'])
        self.assertEqual(instrumentation_state()['mode'], 'diagnostic')

    def test_preexisting_diagnostic_collector_cannot_leak_into_clean(self):
        collector = ServiceTelemetry()
        with instrumentation_scope('clean'):
            with self.assertRaises(RuntimeError):
                with collector.span('foreign'):
                    pass
            with self.assertRaises(RuntimeError):
                collector.event('foreign')
            with self.assertRaises(RuntimeError):
                collector.diagnostic('s', 'foreign')
            with self.assertRaises(RuntimeError):
                ServiceTelemetry(enabled=True)
            with self.assertRaises(RuntimeError):
                with instrumentation_scope('diagnostic'):
                    pass

    def test_clean_measure_omits_allocation_trace_and_preserves_failure(self):
        with instrumentation_scope('clean'), patch('src.experiment_runner.tracemalloc.start', side_effect=AssertionError('tracing enabled')):
            value, metrics = measure(lambda: 11)
            self.assertEqual(value, 11)
            self.assertIsNone(metrics['peak_python_bytes'])
            self.assertFalse(metrics['allocation_tracking'])
            failure = ArithmeticError('fixture failure')
            with self.assertRaises(ArithmeticError) as caught:
                measure(lambda: (_ for _ in ()).throw(failure))
            self.assertIs(caught.exception, failure)
            self.assertIsNone(failure.runner_metrics['peak_python_bytes'])

    def test_active_profiler_trace_and_allocation_tracking_reject(self):
        for method in ('getprofile', 'gettrace'):
            with self.subTest(method=method), patch('src.instrumentation.sys.'+method, return_value=object()):
                with self.assertRaises(RuntimeError):
                    with instrumentation_scope('clean'):
                        self.fail('active instrumentation accepted')
        tracemalloc.start()
        try:
            with self.assertRaises(RuntimeError):
                with instrumentation_scope('clean'):
                    self.fail('allocation tracing accepted')
        finally:
            tracemalloc.stop()

    def test_instrumentation_activated_inside_scope_rejects_exit(self):
        try:
            with self.assertRaises(RuntimeError):
                with instrumentation_scope('clean'):
                    tracemalloc.start()
        finally:
            tracemalloc.stop()
        self.assertEqual(instrumentation_state()['mode'], 'diagnostic')

    def test_clean_and_diagnostic_preserve_model_and_state_bytes(self):
        fixture = aggregate_fixture.AggregateServiceTests()
        service, _, _, _ = fixture.build()
        records = fixture.records()[:2]
        diagnostic = service.fresh(records, telemetry=ServiceTelemetry())
        with tempfile.TemporaryDirectory() as folder, instrumentation_scope('clean'):
            clean = service.fresh(records, telemetry=ServiceTelemetry())
            self.assertEqual(clean.state.canonical_bytes(), diagnostic.state.canonical_bytes())
            self.assertEqual(clean.state.model, diagnostic.state.model)
            store = RunStore(folder, {'fixture': 'clean-output'})
            store.claim()
            try:
                with patch('src.experiment_runner._integer_sizes', side_effect=AssertionError('optional size scan')):
                    info = _commit_state(store, 'clean', clean)
                self.assertIsNone(info['maximum_integer_bits'])
                self.assertIsNone(info['stages'])
                self.assertEqual(info['state_sha256'], clean.state.digest)
            finally:
                store.close()

    def test_diagnostic_output_spans_account_without_changing_artifacts(self):
        fixture = aggregate_fixture.AggregateServiceTests()
        service, _, _, _ = fixture.build()
        output = service.fresh(fixture.records()[:2])
        telemetry = ServiceTelemetry()
        with tempfile.TemporaryDirectory() as folder:
            store = RunStore(folder, {'fixture': 'diagnostic-output'})
            store.claim()
            try:
                info = _commit_state(store, 'diagnostic', output, telemetry=telemetry)
                self.assertEqual((store.attempt/'diagnostic-state.json').read_bytes(), output.state.canonical_bytes())
                self.assertEqual(info['state_sha256'], output.state.digest)
                timings = telemetry.payload()['timings']
                for category in ('serialization', 'durable_output', 'artifact_diagnostics'):
                    self.assertIn(category, timings)
            finally:
                store.close()

    def test_loader_and_construction_windows_are_disjoint(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            isolated_fixture.IsolatedComparisonTests().fixture(root)
            prepared = _run_manifest(root/'run.json', root/'unused', prepare_only=True)
            preflight = prepared['preflight']
            windows = [preflight[key]['timing_window'] for key in
                       ('loading_measurement', 'chart_construction_measurement')]
            for window in windows:
                self.assertEqual(window['clock'], 'time.perf_counter_ns_system_monotonic')
                self.assertEqual(window['end_ns'] - window['start_ns'], window['wall_ns'])
                self.assertGreaterEqual(window['wall_ns'], 0)
            self.assertLessEqual(windows[0]['end_ns'], windows[1]['start_ns'])

    def test_nonquality_preparation_can_skip_heldout_without_changing_target(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _, manifest = isolated_fixture.IsolatedComparisonTests().fixture(root)
            with instrumentation_scope('clean'):
                expected = _run_manifest(root/'run.json', root/'unused', prepare_only=True)
            manifest['heldout'] = {'path': 'absent-evaluation.json', 'sha256': 'a'*64}
            (root/'run.json').write_bytes(canonical_json(manifest))
            with instrumentation_scope('clean'):
                actual = _run_manifest(root/'run.json', root/'unused', prepare_only=True, skip_heldout=True)
            self.assertEqual(actual['metadata']['target_manifest_sha256'], expected['metadata']['target_manifest_sha256'])
            self.assertEqual(actual['service'].manifest_digest, expected['service'].manifest_digest)
            self.assertEqual(actual['heldout'], ())
            self.assertIsNone(actual['preflight']['loading_measurement']['peak_python_bytes'])
            with self.assertRaises(ValueError):
                _run_manifest(root/'run.json', root/'unused', skip_heldout=True)


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = capture_runtime_contract()

    def test_runtime_is_stable_across_a_fresh_process(self):
        command = [sys.executable, '-c', 'from src.runtime_contract import capture_runtime_contract; from src.run_store import canonical_json; import sys; sys.stdout.buffer.write(canonical_json(capture_runtime_contract()))']
        actual = strict_json(subprocess.check_output(command, cwd=Path(__file__).resolve().parents[1]))
        self.assertEqual(actual, self.contract)
        self.assertEqual(verify_runtime_contract(self.contract), self.contract)

    def test_schema_rejects_incomplete_forged_and_boolean_fields(self):
        cases = []
        for key in ('interpreter', 'modules', 'float_model'):
            value = deepcopy(self.contract); del value[key]; cases.append(value)
        value = deepcopy(self.contract); value['pointer_bits'] = True; cases.append(value)
        value = deepcopy(self.contract); value['interpreter']['bytes'] = True; cases.append(value)
        value = deepcopy(self.contract); value['float_model']['mant_dig'] = 24; cases.append(value)
        value = deepcopy(self.contract); value['modules']['unbound'] = {'kind': 'built-in'}; cases.append(value)
        for value in cases:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_runtime_contract(value)

    def test_valid_shape_does_not_allow_changed_runtime(self):
        for key in ('python_version', 'kernel', 'machine'):
            changed = deepcopy(self.contract); changed[key] += '-changed'
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'runtime contract differs'):
                verify_runtime_contract(changed)
        changed = deepcopy(self.contract); changed['modules']['fractions']['sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'modules'):
            verify_runtime_contract(changed)
        changed = deepcopy(self.contract); changed['execution_flags']['integer_string_digit_limit'] += 1
        with self.assertRaisesRegex(ValueError, 'execution_flags'):
            verify_runtime_contract(changed)

    def test_validated_payload_is_detached_and_omits_local_paths(self):
        copy = validate_runtime_contract(self.contract)
        copy['modules'].clear()
        self.assertTrue(self.contract['modules'])
        encoded = canonical_json(self.contract)
        self.assertNotIn(str(Path(sys.executable).parent).encode(), encoded)
        self.assertNotIn(b'hostname', encoded)


if __name__ == '__main__':
    unittest.main()
