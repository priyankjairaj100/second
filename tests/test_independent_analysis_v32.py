"""Archive analysis fixtures only. No empirical worker or neural model is run."""
from contextlib import ExitStack
import copy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import analyze_independent_requests_v32 as analysis
from scripts import launch_independent_requests_v32 as controller


class IndependentAnalysisTests(unittest.TestCase):
    def test_packed_integer_count_handles_odd_tail_and_padding(self):
        self.assertEqual(analysis.changed_four_bit_codes(bytes([0x21, 0x03]), bytes([0x31, 0x04]), 3), 2)
        self.assertEqual(analysis.changed_four_bit_codes(b'', b'', 0), 0)
        with self.assertRaisesRegex(ValueError, 'padding'):
            analysis.changed_four_bit_codes(bytes([0x13]), bytes([0x03]), 1)
        with self.assertRaisesRegex(ValueError, 'lengths'):
            analysis.changed_four_bit_codes(b'a', b'ab', 2)

    def test_model_code_comparison_rejects_different_grids(self):
        stage = SimpleNamespace(stage_id='a', rows=1, columns=2, grid_axis='dyadic_row', bits=4,
                                scale_exponents=(), scale_values=(1.,), packed_indices=b'\x21')
        original = SimpleNamespace(target_sha256='a'*64, factors=(), stages=(stage,))
        retained = copy.deepcopy(original)
        retained.stages[0].packed_indices = b'\x31'
        self.assertEqual(analysis.changed_model_codes(original, retained)['changed_code_count'], 1)
        retained.stages[0].scale_values = (2.,)
        with self.assertRaisesRegex(ValueError, 'grids or shapes'):
            analysis.changed_model_codes(original, retained)

    def test_direct_model_byte_comparison_detects_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/'a', Path(tmp)/'b'
            a.write_bytes(b'a' * (1024 * 1024) + b'x')
            b.write_bytes(a.read_bytes())
            self.assertTrue(analysis.equal_file_bytes(a, b))
            b.write_bytes(b'a' * (1024 * 1024) + b'y')
            self.assertFalse(analysis.equal_file_bytes(a, b))

    def test_invalid_clocks_are_rejected(self):
        for value in (True, 0, -1, 0.5, float('nan')):
            with self.assertRaisesRegex(ValueError, 'positive integer'):
                analysis.verified_seconds({'controller_elapsed_ns': value})

    def test_published_native_receipts_pass_and_budget_mutation_fails(self):
        root = analysis.ROOT / 'campaigns/compressed_service_v31'
        result = controller.read_json(root/'attempts/repair-128-48/outputs/completion.json')
        plan = controller.read_json(root/'attempts/repair-128-48/plan.json')
        program = controller.read_json(root/'program.json')
        diagnostics = analysis.verify_diagnostics(result, plan)
        evidence = analysis.verify_native_receipts(result, plan, program, root/'source')
        self.assertEqual(diagnostics['certificate_accepted_stages'], 24)
        self.assertEqual(evidence['attempted_stages'], 24)
        result['diagnostics']['stages'][0]['solver_diagnostics']['resource_budget'][0][1] += 1
        with self.assertRaisesRegex(ValueError, 'internal resource budget'):
            analysis.verify_native_receipts(result, plan, program, root/'source')

    def fixture(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        program = controller.build_spec('wikitext')
        program = controller.relocate(program, str(controller.ROOT), root)
        current = Path(program['campaign'])
        program.update(primary_clock='fixture transaction clock', source_sha256={})
        models = {'file': 'model.bin', 'bytes': 3, 'sha256': hashlib.sha256(b'abc').hexdigest()}
        state = {'file': 'state.bin', 'bytes': 10, 'sha256': hashlib.sha256(b'0123456789').hexdigest()}
        compressed_state = {'file': 'state.bin', 'bytes': 8, 'sha256': hashlib.sha256(b'01234567').hexdigest()}
        times = [30, 12, 10, 11, 7, 4, 14]
        results = {}
        for trial, seconds in zip(program['trials'], times):
            name, plan = trial['id'], trial['plan']
            attempt = current/'attempts'/name
            (attempt/'outputs').mkdir(parents=True)
            (attempt/'worker').mkdir()
            (attempt/'transaction.json').write_text(json.dumps({'controller_elapsed_ns': seconds*10**9}))
            (attempt/'worker/result.json').write_text(json.dumps({'fixture_receipt': name}))
            (attempt/'outputs/model.bin').write_bytes(b'abc')
            stateful = plan['method'] != 'model_only_fresh'
            compressed = name.endswith('-compressed')
            artifacts = {'model': copy.deepcopy(models)}
            if stateful:
                artifacts['state'] = copy.deepcopy(compressed_state if compressed else state)
                (attempt/'outputs/state.bin').write_bytes(b'01234567' if compressed else b'0123456789')
            gates = {'checks': {}, 'all_passed': True}
            if compressed:
                gates = {'checks': {'latency': {'passed': False}, 'storage': {'passed': True}}, 'all_passed': False}
            neural = 0 if plan['method'] in ('repair', 'convert_lossless') else 24*len(plan['record_ids'])
            result = dict(stage_count=24, model_code_elements=42467328, stage_ids=[str(i) for i in range(24)],
                model_roundtrip_exact=True, original_token_count=256, retained_token_count=128*len(plan['record_ids']),
                complete_state=stateful, artifacts=artifacts, model_artifact=artifacts['model'],
                retained_record_ids=plan['record_ids'], deleted_record_ids=plan['deleted_ids'],
                registered_scientific_gates=gates, diagnostics=dict(neural_stage_record_pairs=neural,
                    certificate_accepted_stages=24, certificate_rejected_stages=0, point_solver_stages=0))
            if stateful:
                result.update(state_roundtrip_canonical=True, state_artifact=artifacts['state'])
            results[name] = result
            for entry in plan['inputs'].values():
                path = Path(entry['path'])
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'fixture input')
        manifest = root/controller.BINDINGS
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text('{"files":{}}')
        for name in ('analyze_independent_requests_v32.py', 'analyze_compressed_service_v31.py'):
            path = root/'scripts'/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('# software fixture\n')
        stack = self.enterContext(ExitStack())
        stack.enter_context(patch.object(analysis, 'ROOT', root))
        stack.enter_context(patch.object(analysis, '__file__', str(root/'scripts/analyze_independent_requests_v32.py')))
        stack.enter_context(patch.object(controller, 'CONTROLLERS', ()))
        stack.enter_context(patch.object(controller, 'check_registered', return_value=(current,program,b'program',b'protocol',{'runtime': {'fixture': True}})))
        checked = stack.enter_context(patch.object(controller, 'completed', side_effect=lambda _, name: copy.deepcopy(results[name])))
        budget = stack.enter_context(patch.object(analysis, 'verify_final_budget', return_value={'status': 'verified'}))
        stack.enter_context(patch.object(analysis, 'verify_diagnostics', return_value={'fixture': True}))
        native = stack.enter_context(patch.object(analysis, 'verify_native_receipts', return_value={'fixture': True}))
        stack.enter_context(patch('src.compact_state.parse', return_value=object()))
        stack.enter_context(patch.object(analysis, 'changed_model_codes', return_value={'changed_code_count': 1, 'total_code_count': 42467328}))
        return current, program, results, checked, budget, native

    def test_all_seven_rows_and_losses_survive_summary(self):
        _, program, _, checked, budget, native = self.fixture()
        result = analysis.analyze('wikitext')
        self.assertEqual([row['id'] for row in result['trials']], program['execution_order'])
        self.assertEqual(checked.call_count, 7)
        self.assertEqual(len(budget.call_args.args[3]), 7)
        native.assert_called_once()
        self.assertFalse(result['pairs'][0]['repair_faster'])
        self.assertTrue(result['pairs'][1]['repair_faster'])
        self.assertFalse(result['compressed']['scientific_gates']['all_passed'])
        self.assertFalse(result['all_observed_lossless_pairs_favor_repair'])
        self.assertAlmostEqual(result['pairs'][0]['cold_over_repair'], 10/12)
        self.assertAlmostEqual(result['compressed']['cold_over_compressed'], 10/14)
        self.assertFalse(result['changing_state_lifetime_benefit_established'])
        self.assertIn('not whole CLI invocation latency', result['clock_limit'])
        self.assertEqual(len(result['verified_binary_artifacts']), 12)

    def test_extra_attempt_cannot_be_omitted(self):
        current, _, _, checked, _, _ = self.fixture()
        (current/'attempts/unregistered-loss').mkdir()
        with self.assertRaisesRegex(ValueError, 'Missing or extra attempt'):
            analysis.analyze('wikitext')
        checked.assert_not_called()

    def test_missing_attempt_cannot_be_summarized_as_complete(self):
        current, program, _, _, _, _ = self.fixture()
        import shutil
        shutil.rmtree(current/'attempts'/program['execution_order'][-1])
        with self.assertRaisesRegex(ValueError, 'Missing or extra attempt'):
            analysis.analyze('wikitext')

    def test_ledger_failure_stops_complete_report(self):
        _, _, _, _, budget, _ = self.fixture()
        budget.side_effect = ValueError('unsettled ledger fixture')
        with self.assertRaisesRegex(ValueError, 'unsettled ledger'):
            analysis.analyze('wikitext')

    def test_changed_bound_membership_is_rejected(self):
        _, program, results, _, _, _ = self.fixture()
        results[program['requests'][0]['repair_trial']]['retained_record_ids'] = ['other source']
        with self.assertRaisesRegex(ValueError, 'retained membership'):
            analysis.analyze('wikitext')

    def test_falsified_certificate_counter_is_rejected_by_route_audit(self):
        root = analysis.ROOT/'campaigns/compressed_service_v31/attempts/repair-128-48'
        result = controller.read_json(root/'outputs/completion.json')
        plan = controller.read_json(root/'plan.json')
        result['diagnostics']['certificate_accepted_stages'] = 23
        with self.assertRaisesRegex(ValueError, 'aggregate route counts'):
            analysis.verify_diagnostics(result, plan)


if __name__ == '__main__':
    unittest.main()
