"""Sequential comparator software contracts. No empirical dataset is used."""
import contextlib
import copy
from dataclasses import replace
from fractions import Fraction as Q
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from scripts import run_sequential_comparison_v30 as worker
from src.adaptive_calibration_v30 import AdaptiveBudget,CalibrationWorkRefused,quantize_adaptive_dyadic_rows
from src.certified_transformer import CertifiedDecoder
from src.compact_state import CompactState,parse as decode_model
from src.dyadic_row_quantizer import quantize_dyadic_rows
from src.dyadic_row_target import build_dyadic_row_target
from src.fixed_anchor_target import build_fixed_anchor_target
from src.ordered_finite import FiniteWeights
from src.run_store import canonical_json,digest,strict_json
from src.target_manifest import TargetRecipe
from tests.test_transformer_backend import decoder_fixture


def plan_fixture():
    return dict(method='model_only_fresh',phase='feasibility',use_candidates=False,solver_backend='auto',
        solver_budget=dict(max_workspace_bytes=64*2**20,max_work_units=100_000_000,max_refinement_coordinates=4),
        max_point_work_units=1_000_000_000,original_token_count=4,
        record_ids=['b'],deleted_ids=['a'],source_sha256={'src/fixture.py':'a'*64})


RECORDS = [dict(id='a',tokens=[0,1]),dict(id='b',tokens=[2,1])]


class SequentialCalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decoder = CertifiedDecoder(decoder_fixture(block_count=2),primitive_backend='mpfr_enclosure')
        cls.target = build_dyadic_row_target(cls.decoder,TargetRecipe(original_token_count=4,group_count=1))

    def test_each_stage_uses_preceding_calibrated_outputs(self):
        prefix = {}
        seen = []
        def checked(weights,features,scales,**options):
            index = len(seen)
            stage = self.target.stages[index]
            expected = np.concatenate([np.asarray(self.decoder.stage_features(stage.stage_id,row['tokens'],prefix),
                dtype=np.float64) for row in RECORDS],axis=1)
            np.testing.assert_array_equal(features,expected)
            actual = quantize_adaptive_dyadic_rows(weights,features,scales,**options)
            reference = quantize_dyadic_rows(weights,expected,scales,ridge=stage.ridge,
                normalization=stage.normalization,max_exact_coordinates=stage.width)
            np.testing.assert_array_equal(actual.codes,reference.codes)
            prefix[stage.stage_id] = tuple(tuple(Q.from_float(float(x)) for x in row) for row in actual.codes)
            seen.append(stage.stage_id)
            return actual
        with patch('src.adaptive_calibration_v30.quantize_adaptive_dyadic_rows',side_effect=checked):
            stages,diagnostics = worker.calibrate_sequential(self.decoder,self.target,RECORDS,
                budget=AdaptiveBudget(),route='auto',max_point_work_units=10**9)
        self.assertEqual(seen,list(self.decoder.stage_ids))
        self.assertEqual(len(stages),8)
        self.assertEqual(diagnostics['neural_stage_record_pairs'],16)
        for index,row in enumerate(diagnostics['stages']):
            self.assertEqual(row['installed_parent_stage_id'],seen[index-1] if index else None)
            self.assertEqual(row['installed_parent_packed_sha256'],digest(stages[index-1].packed_indices) if index else None)

    def test_fixed_target_cannot_enter_sequential_calibration(self):
        fixed = build_fixed_anchor_target(self.decoder,self.target)
        self.assertNotEqual(fixed.digest,self.target.digest)
        with self.assertRaises(ValueError):
            worker.calibrate_sequential(self.decoder,fixed,RECORDS,
                budget=AdaptiveBudget(),route='auto',max_point_work_units=10**9)

    def test_budget_refusal_precedes_neural_features(self):
        with patch('src.sequential_finite.sequential_features',side_effect=AssertionError('no neural work')):
            with self.assertRaises(CalibrationWorkRefused):
                worker.calibrate_sequential(self.decoder,self.target,RECORDS,
                    budget=AdaptiveBudget(),route='auto',max_point_work_units=1)

    def test_failure_retains_completed_work_without_partial_output(self):
        calls = []
        def stop(weights,features,scales,**options):
            calls.append(1)
            if len(calls) == 2:
                raise ArithmeticError('software refusal')
            return quantize_adaptive_dyadic_rows(weights,features,scales,**options)
        with patch('src.adaptive_calibration_v30.quantize_adaptive_dyadic_rows',side_effect=stop):
            with self.assertRaises(ArithmeticError) as caught:
                worker.calibrate_sequential(self.decoder,self.target,RECORDS,
                    budget=AdaptiveBudget(),route='auto',max_point_work_units=10**9)
        metrics = caught.exception.service_diagnostics
        self.assertTrue(metrics['aborted'])
        self.assertEqual(metrics['completed_stages'],1)
        self.assertEqual(metrics['neural_stage_record_pairs'],4)

    def test_empty_retained_set_has_no_neural_traversals(self):
        stages,diagnostics = worker.calibrate_sequential(self.decoder,self.target,[],
            budget=AdaptiveBudget(),route='auto',max_point_work_units=10**9)
        self.assertEqual(len(stages),8)
        self.assertEqual(diagnostics['neural_stage_record_pairs'],0)
        for code,stage in zip(stages,self.target.stages):
            reference = quantize_dyadic_rows(FiniteWeights(stage.weights).array(),
                np.empty((stage.width,0)),stage.scale_values,ridge=stage.ridge,normalization=stage.normalization)
            np.testing.assert_array_equal(code.array(),reference.codes)

    def test_quality_contract_rejects_prior_methods_and_state_output(self):
        worker.validate_comparison_plan(plan_fixture())
        for method in ('repair','direct_fresh','indexed_fresh'):
            with self.assertRaises(ValueError):
                worker.validate_comparison_plan(dict(plan_fixture(),method=method))
        with self.assertRaises(ValueError):
            worker.validate_comparison_plan(dict(plan_fixture(),expected_state_sha256='1'*64))


class SequentialWorkerIntegrationTests(unittest.TestCase):
    def setup_plan(self,root):
        checkpoint = root/'checkpoint';checkpoint.mkdir()
        (checkpoint/'config.json').write_bytes(b'{}')
        (checkpoint/'model.safetensors').write_bytes(b'miniature software decoder fixture')
        manifest = root/'records.json';manifest.write_bytes(canonical_json({'records':RECORDS}))
        inputs = {name:dict(path=str(path),sha256=digest(path.read_bytes())) for name,path in (
            ('records',manifest),('config',checkpoint/'config.json'),('weights',checkpoint/'model.safetensors'))}
        loaded = SimpleNamespace(decoder=decoder_fixture(block_count=6),provenance={
            'files_sha256':{name:inputs[key]['sha256'] for name,key in (
                ('config.json','config'),('model.safetensors','weights'))}})
        plan = dict(plan_fixture(),checkpoint=str(checkpoint),inputs=inputs,
                    protocol_sha256='f'*64,output=str(root/'output'))
        return plan,loaded

    def invoke(self,root,plan,loaded):
        path = root/'plan.json';path.write_bytes(canonical_json(plan))
        with patch.object(worker.sys,'argv',['run_sequential_comparison_v30.py',str(path)]):
            with patch.object(worker,'source_hashes',return_value=plan['source_sha256']):
                with patch.object(worker,'verify_command_admission') as admission:
                    with patch('src.checkpoint_adapter.load_gpt2_checkpoint',return_value=loaded):
                        with contextlib.redirect_stdout(io.StringIO()):
                            worker.main()
                    admission.assert_called_once_with(plan['protocol_sha256'],'feasibility',
                        [worker.sys.executable,str(Path(worker.__file__).resolve()),str(path.absolute())])

    def test_complete_twenty_four_stage_model_has_distinct_sequential_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan,loaded = self.setup_plan(root)
            self.invoke(root,plan,loaded)
            output = Path(plan['output'])
            terminal = (output/'completion.json').read_bytes()
            self.assertEqual(terminal,(output/'progress.json').read_bytes())
            result = strict_json(terminal)
            self.assertEqual(result['schema'],worker.SCHEMA)
            self.assertEqual(result['comparison_role'],'sequential_quality')
            self.assertFalse(result['repair_speed_comparator'])
            self.assertEqual(result['original_token_count'],4)
            self.assertEqual(result['retained_token_count'],2)
            self.assertEqual(result['stage_count'],24)
            self.assertEqual(result['diagnostics']['neural_stage_record_pairs'],24)
            self.assertNotEqual(result['sequential_target_sha256'],result['fixed_target_sha256'])
            self.assertEqual(result['sequential_target_sha256'],result['base_target_sha256'])
            model = decode_model((output/'model.bin').read_bytes(),expected_sha256=result['model_artifact']['sha256'])
            self.assertEqual(model.target_sha256,result['sequential_target_sha256'])
            self.assertFalse(model.factors)
            self.assertFalse((output/'state.bin').exists())
            self.assertTrue(result['model_roundtrip_exact'])
            self.assertFalse(result['complete_state'])

    def test_target_mismatch_refuses_before_sequential_features(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan,loaded = self.setup_plan(root)
            plan['expected_target'] = '0'*64
            with patch.object(worker,'calibrate_sequential',side_effect=AssertionError('no features')):
                with self.assertRaises(ValueError):
                    self.invoke(root,plan,loaded)
            failure = strict_json((Path(plan['output'])/'progress.json').read_bytes())
            self.assertEqual(failure['status'],'failed')
            self.assertFalse((Path(plan['output'])/'completion.json').exists())

    def test_prior_inputs_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan,loaded = self.setup_plan(root)
            plan['inputs']['prior_state'] = copy.deepcopy(plan['inputs']['weights'])
            with patch('src.checkpoint_adapter.load_gpt2_checkpoint',side_effect=AssertionError('no checkpoint')):
                with self.assertRaises(ValueError):
                    self.invoke(root,plan,loaded)


if __name__ == '__main__':
    unittest.main()
