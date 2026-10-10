"""Service/worker integration fixtures; no checkpoint load or neural inference.

Real canonical codecs/state validation surround a tiny independent feature
fixture. Numerical solver correctness remains in dispatcher/kernel tests.
"""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from research_v42.test_resource_plan import bind, fixture
from research_v43 import campaign, service, worker
from research_v43.state import build_state, validate_state
from research_v43.test_state import BUDGET, artifacts, codes, features, record
from src.fixed_factor_state import FactorBlock
from src.run_store import canonical_json
from src.transaction_timing import verify_command_admission


class FixtureService:
    """No decoder or numerical solver; actual source/state encoders remain live."""
    events = []

    def __init__(self, checkpoint, normalization, record_provenance, mark):
        self.bound = bind(*fixture(((2, 3), (1, 2)), original=normalization))
        self.target = SimpleNamespace(stages=self.bound.stages)
        self.normalization = normalization
        self.record_provenance = record_provenance
        self.provenance = canonical_json({'fixture': True})
        self.load_ns = 0
        self.gram_budget = BUDGET

    def records(self, rows):
        return tuple(record(row['id'], row['tokens']) for row in rows)

    def admit(self, rows, representation):
        self.events.append(('admit', tuple(r['id'] for r in rows), representation))
        return {'admitted': True}

    def extract(self, rows, telemetry):
        self.events.append(('extract', tuple(r['id'] for r in rows)))
        telemetry['neural_stage_record_pairs'] += len(rows)*len(self.bound.stages)
        return {(stage.stage_id, source.record_id): features(stage, source)
                for stage in self.bound.stages for source in self.records(rows)}

    def solve(self, rows, representation, payloads, grams, trust, telemetry, **kwargs):
        self.events.append(('solve', tuple(r['id'] for r in rows), representation))
        return codes(self.bound), {'admitted': True}

    def prepare_payloads(self, rows, values, representation, telemetry):
        self.events.append(('encode', tuple(r['id'] for r in rows), representation))
        result = artifacts(self.bound, self.records(rows), representation)
        return result['source_payloads'], result['stage_grams'], result['gram_trust']

    def serialize(self, rows, stage_codes, representation, payloads, grams, trust, telemetry):
        return build_state(self.bound, self.records(rows), stage_codes, representation,
            source_payloads=payloads, stage_grams=grams, gram_trust=trust, gram_budget=BUDGET)


class ServiceIntegrationTests(unittest.TestCase):
    def test_controller_ledger_binds_program_sources_and_literal_worker_command(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root/'program.json').write_bytes(canonical_json({'fixture': True}))
            program = dict(directory=str(root), phase_cpu_seconds=campaign.CAP)
            command = [worker.sys.executable, '-B', '-m', 'research_v43.worker', str(root/'plan.json')]
            with patch('src.experiment_inventory.source_hashes', return_value={'fixture.py': '1'*64}):
                budget = campaign.budget(program)
                budget.reserve('feasibility', 'fixture-attempt', 10)
                admission = dict(phase_budget_root=str(budget.root),
                    phase_budget_binding_sha256=budget.identity_digest,
                    attempt_id='fixture-attempt', phase='feasibility', command=command,
                    cwd=str(campaign.ROOT))
                with patch.dict(os.environ, CALIBRATION_PHASE_CPU_ADMISSION=canonical_json(admission).decode()):
                    actual = verify_command_admission(worker.sha(root/'program.json'), 'feasibility', command)
                    self.assertEqual(actual['attempt_id'], 'fixture-attempt')
                    with self.assertRaisesRegex(ValueError, 'exact command'):
                        verify_command_admission(worker.sha(root/'program.json'), 'feasibility',
                                                 [arg for arg in command if arg != '-B'])

    def test_record_contract_uses_dataset_provenance(self):
        item = record('alpha', (1, 2))
        instance = object.__new__(service.Service)
        instance.record_provenance = {'alpha': json.loads(item.provenance)}
        result = instance.records([{'id': 'alpha', 'tokens': [1, 2]}])
        self.assertEqual(result, (item,))
        instance.record_provenance = {'alpha': {'schema': 'execution-only'}}
        with self.assertRaises(ValueError):
            instance.records([{'id': 'alpha', 'tokens': [1, 2]}])

    def test_extract_runs_once_per_source_and_keeps_every_ordered_stage(self):
        instance = object.__new__(service.Service)
        instance.decoder, instance.base, instance.context = object(), object(), object()
        instance.mark = lambda *a, **k: None
        stages = tuple(SimpleNamespace(stage_id=f'stage-{i:02d}', width=2) for i in range(24))
        instance.target = SimpleNamespace(stages=stages)
        rows = [{'id': 'alpha', 'tokens': [1, 2]}, {'id': 'beta', 'tokens': [3]}]
        def leaf(decoder, base, row, *, context):
            self.assertIs(decoder, instance.decoder)
            self.assertIs(base, instance.base)
            self.assertIs(context, instance.context)
            return SimpleNamespace(blocks=tuple(FactorBlock.from_array(stage.stage_id,
                np.array([[t, i] for t in row['tokens']], dtype=np.float64))
                for i, stage in enumerate(stages)))
        timing = service.telemetry()
        with patch.object(service, 'prepare_ordered_leaf', side_effect=leaf) as prepare:
            result = instance.extract(rows, timing)
        self.assertEqual(prepare.call_count, 2)
        self.assertEqual(timing['neural_stage_record_pairs'], 48)
        self.assertEqual(len(result), 48)
        np.testing.assert_array_equal(result['stage-23', 'beta'], [[3., 23.]])

    def _program(self, root):
        rows = [{'id': name, 'tokens': tokens} for name, tokens in
                [('alpha', [1, 2]), ('beta', [3, 4]), ('gamma', [5, 6])]]
        return dict(directory=str(root), normalization=6, records=rows,
            record_provenance={r['id']: json.loads(record(r['id'], r['tokens']).provenance) for r in rows},
            sources={}, shared_checkpoint_bytes=123)

    def _run(self, root, program, trial, *, state_observer=None):
        trial_root = root/trial
        trial_root.mkdir()
        program_path = root/'program.json'
        if not program_path.exists():
            program_path.write_bytes(canonical_json(program))
        plan_path = trial_root/'plan.json'
        plan_path.write_bytes(canonical_json(dict(trial=trial, program=str(program_path),
            program_sha256=worker.sha(program_path), output=str(trial_root/'outputs'), slurm_job_id='fixture')))
        with ExitStack() as stack:
            stack.enter_context(patch.object(worker, 'ROOT', root))
            stack.enter_context(patch.object(worker, 'Service', FixtureService))
            stack.enter_context(patch.object(worker, 'verify', return_value=program))
            command_check = stack.enter_context(patch.object(worker, 'verify_command_admission'))
            if state_observer:
                stack.enter_context(patch.object(worker, 'validate_state', side_effect=state_observer))
            worker.main(plan_path)
            command_check.assert_called_once_with(worker.sha(program_path), 'feasibility',
                [worker.sys.executable, '-B', '-m', 'research_v43.worker', str(plan_path)])
        return json.loads((trial_root/'outputs/completion.json').read_bytes())

    def test_worker_cached_requests_use_actual_successor_and_complete_admission(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            program = self._program(root)
            FixtureService.events = []
            self._run(root, program, 'prepare')
            predecessors = []
            def observe(blob, **kwargs):
                parsed = validate_state(blob, **kwargs)
                predecessors.append(tuple(r.record_id for r in parsed.records))
                return parsed
            FixtureService.events = []
            result = self._run(root, program, 'cached', state_observer=observe)
            self.assertEqual(predecessors, [('alpha', 'beta', 'gamma'), ('beta', 'gamma')])
            self.assertEqual([step['deleted_ids'] for step in result['steps']], [['alpha'], ['beta']])
            self.assertTrue(result['complete_model'])
            self.assertTrue(all(e[0] == 'admit' for e in FixtureService.events[:9]))
            self.assertFalse(any(e[0] == 'extract' for e in FixtureService.events))
            final = validate_state((root/'cached/outputs/step-2-state.bin').read_bytes())
            self.assertEqual(tuple(r.record_id for r in final.records), ('gamma',))

    def test_oracle_runs_without_preparation_artifacts_and_rebuilds_each_membership(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            program = self._program(root)
            FixtureService.events = []
            result = self._run(root, program, 'oracle')
            self.assertFalse((root/'prepare').exists())
            self.assertEqual([e[1] for e in FixtureService.events if e[0] == 'extract'],
                             [('beta', 'gamma'), ('gamma',)])
            self.assertEqual(len([e for e in FixtureService.events if e[0] == 'encode']), 6)
            self.assertTrue(all(e[0] == 'admit' for e in FixtureService.events[:9]))
            self.assertTrue(all(step['prior_state_read'] is False for step in result['steps']))
            self.assertTrue(result['complete_model'])

    def test_cold_rebuilds_complete_lossless_state_without_prior_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            program = self._program(root)
            FixtureService.events = []
            result = self._run(root, program, 'cold')
            self.assertFalse((root/'prepare').exists())
            self.assertEqual([e[1] for e in FixtureService.events if e[0] == 'extract'],
                             [('beta', 'gamma'), ('gamma',)])
            self.assertEqual([e[2] for e in FixtureService.events if e[0] == 'encode'],
                             ['lossless', 'lossless'])
            self.assertTrue(all(step['state_bytes'] > 0 for step in result['steps']))
            final = validate_state((root/'cold/outputs/step-2-state.bin').read_bytes())
            self.assertEqual(tuple(r.record_id for r in final.records), ('gamma',))

    def test_failed_second_request_preserves_failure_without_releasing_partial_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            program = self._program(root)
            self._run(root, program, 'prepare')
            original_solve = FixtureService.solve
            def fail_final(instance, rows, *args, **kwargs):
                if len(rows) == 1:
                    raise service.dispatch.DispatchRefused('fixture refusal', {'admitted': True})
                return original_solve(instance, rows, *args, **kwargs)
            with patch.object(FixtureService, 'solve', fail_final), \
                 self.assertRaises(service.dispatch.DispatchRefused):
                self._run(root, program, 'cached')
            output = root/'cached/outputs'
            result = json.loads((output/'completion.json').read_bytes())
            self.assertEqual(result['status'], 'failed')
            self.assertFalse(result['complete_model'])
            self.assertTrue(result['partial_artifacts_are_not_a_committed_complete_model'])
            self.assertTrue((output/'step-1-state.bin').exists())
            self.assertFalse((output/'step-2-state.bin').exists())
            self.assertFalse((output/'step-2-model.bin').exists())


if __name__ == '__main__':
    unittest.main()
