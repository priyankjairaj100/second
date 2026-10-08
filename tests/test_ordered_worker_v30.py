"""Worker contracts and miniature decoder fixtures, without empirical runs."""
import contextlib
import copy
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import run_ordered_service_v30 as worker
from src.adaptive_calibration_v30 import AdaptiveBudget,CalibrationWorkRefused
from src.run_store import canonical_json,digest,strict_json


def policy(method='repair'):
    return dict(method=method,phase='feasibility',use_candidates=False,solver_backend='auto',
        max_point_work_units=1_000_000_000,
        solver_budget=dict(max_workspace_bytes=64*2**20,max_work_units=100_000_000,
                           max_refinement_coordinates=4),
        original_token_count=4,record_ids=['b'],deleted_ids=['a'],
        source_sha256={'src/fixture.py':'1'*64})


def records():
    return {'records':[dict(id='a',tokens=[0,1]),dict(id='b',tokens=[2,1])]}


class WorkerContractTests(unittest.TestCase):
    def test_selects_generic_lengths_and_preserves_original_normalization(self):
        payload = {'records':[dict(id='other-corpus:17',tokens=[0,1,2]),
                              dict(id='other-corpus:203',tokens=[2,1,0,1,2])]}
        plan = dict(policy(),original_token_count=8,record_ids=['other-corpus:203'],deleted_ids=['other-corpus:17'])
        original,retained = worker.select_records(plan,payload)
        self.assertEqual([len(row['tokens']) for row in original],[3,5])
        self.assertEqual(retained[0]['id'],'other-corpus:203')
        with self.assertRaises(ValueError):
            worker.select_records(dict(plan,original_token_count=5),payload)

    def test_cold_access_excludes_prior_state_and_preparation_receipt(self):
        self.assertEqual(worker.required_inputs('model_only_fresh'),{'records','config','weights'})
        self.assertEqual(worker.required_inputs('direct_fresh'),{'records','config','weights'})
        self.assertEqual(worker.required_inputs('repair'),worker.required_inputs('indexed_fresh'))
        self.assertEqual(worker.required_inputs('repair'),set(worker.CAPS))
        with self.assertRaises(ValueError):
            worker.required_inputs('other')

    def test_bad_membership_tokens_and_policy_are_rejected(self):
        cases = [dict(policy(),record_ids=[]),dict(policy(),deleted_ids=['z']),
            dict(policy(),record_ids=['b','b']),dict(policy(),use_candidates=True),
            dict(policy(),method='direct_fresh'),dict(policy(),solver_backend='other'),
            dict(policy(),phase='confirmation'),dict(policy(),original_token_count=True),
            dict(policy(),expected_target='wrong'),dict(policy(),solver_budget={})]
        for plan in cases:
            with self.assertRaises((ValueError,TypeError)):
                worker.select_records(plan,records())
        for value in (True,-1,2**64,1.5):
            payload = records();payload['records'][0]['tokens'][0] = value
            with self.assertRaises(ValueError):
                worker.select_records(policy(),payload)
        payload = records();payload['records'].reverse()
        with self.assertRaises(ValueError):
            worker.select_records(policy(),payload)

    def preparation_fixture(self):
        plan = policy()
        plan['inputs'] = {name:dict(path='/fixture/'+name,sha256=(str(i+1)*64))
                          for i,name in enumerate(sorted(worker.required_inputs('repair')))}
        original,_ = worker.select_records(plan,records())
        completion = dict(schema=worker.SCHEMA,status='complete',method='direct_fresh',
            complete_model=True,complete_state=True,model_roundtrip_exact=True,state_roundtrip_canonical=True,
            use_candidates=False,confirmation=False,scientific_promotion=False,
            max_point_work_units=plan['max_point_work_units'],
            source_sha256=plan['source_sha256'],original_token_count=4,
            solver_backend=plan['solver_backend'],solver_budget=plan['solver_budget'],
            original_record_ids=['a','b'],retained_record_ids=['a','b'],committed_record_ids=['a','b'],
            deleted_record_ids=[],original_records_sha256=digest(canonical_json(records())),
            records_input_sha256=plan['inputs']['records']['sha256'],
            checkpoint_files_sha256={name:plan['inputs'][key]['sha256'] for name,key in (
                ('config.json','config'),('model.safetensors','weights'))},
            stage_count=24,stage_ids=['stage-'+str(i) for i in range(24)],worker_transaction_elapsed_ns=1,
            state_artifact=dict(file='state.bin',bytes=1,sha256=plan['inputs']['prior_state']['sha256']),
            model_artifact=dict(file='model.bin',bytes=1,sha256='9'*64),
            fixed_target_sha256='a'*64,base_target_sha256='b'*64)
        from src.ordered_fixed_service_v30 import ordered_preparer_binding
        completion['preparer_sha256'] = ordered_preparer_binding()
        completion['decoder_implementation_manifest'] = {'schema':'fixture'}
        completion['decoder_implementation_sha256'] = digest(canonical_json(completion['decoder_implementation_manifest']))
        completion['artifacts'] = {name:completion[name+'_artifact'] for name in ('model','state')}
        return plan,completion,original

    def test_bound_preparation_checks_all_material_provenance(self):
        plan,completion,original = self.preparation_fixture()
        self.assertEqual(worker.validate_preparation(plan,completion,original),completion['state_artifact'])
        changes = dict(status='failed',method='repair',complete_model=False,complete_state=False,
            model_roundtrip_exact=False,state_roundtrip_canonical=False,source_sha256={},
            use_candidates=True,confirmation=True,scientific_promotion=True,max_point_work_units=1,
            original_token_count=2,solver_backend='primal',solver_budget={},original_record_ids=['b'],
            retained_record_ids=['b'],committed_record_ids=['b'],deleted_record_ids=['a'],
            original_records_sha256='c'*64,records_input_sha256='d'*64,checkpoint_files_sha256={},
            stage_count=23,stage_ids=['same']*24,worker_transaction_elapsed_ns=None,
            fixed_target_sha256=None,base_target_sha256=None,preparer_sha256='0'*64,
            decoder_implementation_manifest={},decoder_implementation_sha256='0'*64,artifacts={},
            schema='adaptive-complete-service-transaction-v30')
        for name,value in changes.items():
            with self.subTest(name=name):
                bad = copy.deepcopy(completion);bad[name] = value
                with self.assertRaises(ValueError):
                    worker.validate_preparation(plan,bad,original)
        for name in ('state_artifact','model_artifact'):
            for field,value in (('bytes',True),('file','other.bin'),('sha256','wrong')):
                bad = copy.deepcopy(completion);bad[name][field] = value
                with self.assertRaises(ValueError):
                    worker.validate_preparation(plan,bad,original)
        with self.assertRaises(ValueError):
            worker.validate_preparation(dict(plan,expected_target='c'*64),completion,original)

    def test_point_preflight_covers_every_stage_and_forced_route(self):
        stages = [SimpleNamespace(stage_id='s'+str(i),width=3,weights=[[],[]]) for i in range(24)]
        report = worker.preflight_stages(stages,2,budget=AdaptiveBudget(),route='auto')
        self.assertTrue(report['all_stages_admitted'])
        self.assertEqual(len(report['stages']),24)
        self.assertFalse(report['neural_work_started'])
        with self.assertRaises(CalibrationWorkRefused) as caught:
            worker.preflight_stages(stages,2,budget=AdaptiveBudget(max_work_units=1),route='auto')
        self.assertFalse(caught.exception.admission['neural_work_started'])
        with self.assertRaises(CalibrationWorkRefused) as aggregate:
            worker.preflight_stages(stages,2,budget=AdaptiveBudget(),route='auto',max_point_work_units=1)
        self.assertFalse(aggregate.exception.admission['request_admitted'])
        self.assertTrue(aggregate.exception.admission['all_stages_admitted'])
        with patch('src.adaptive_calibration_v30.assess_routes',return_value=dict(
                selected='token',routes={'token':dict(admitted=True),'primal':dict(admitted=False)})):
            with self.assertRaises(CalibrationWorkRefused):
                worker.preflight_stages(stages,2,budget=AdaptiveBudget(),route='primal')

    def test_input_hashes_paths_and_method_access_are_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = dict(policy('model_only_fresh'),inputs={})
            for name in worker.required_inputs(plan['method']):
                path = root/name;path.write_bytes(name.encode())
                plan['inputs'][name] = dict(path=str(path),sha256=digest(path.read_bytes()))
            worker.validate_inputs(plan)
            bad = copy.deepcopy(plan);bad['inputs']['prior_state'] = bad['inputs']['weights']
            with self.assertRaises(ValueError):worker.validate_inputs(bad)
            bad = copy.deepcopy(plan);bad['inputs']['records']['sha256'] = '0'*64
            with self.assertRaises(ValueError):worker.validate_inputs(bad)
            (root/'alias').symlink_to(root/'records')
            bad = copy.deepcopy(plan);bad['inputs']['records']['path'] = str(root/'alias')
            with self.assertRaises(ValueError):worker.validate_inputs(bad)


class WorkerMiniatureIntegrationTests(unittest.TestCase):
    """The adapter is replaced with a small deterministic software decoder."""
    def fixture(self,root):
        from tests.test_transformer_backend import decoder_fixture
        checkpoint = root/'checkpoint';checkpoint.mkdir()
        (checkpoint/'config.json').write_bytes(b'{}')
        (checkpoint/'model.safetensors').write_bytes(b'miniature software fixture, not a model checkpoint')
        manifest = root/'records.json';manifest.write_bytes(canonical_json(records()))
        inputs = {name:dict(path=str(path),sha256=digest(path.read_bytes())) for name,path in (
            ('records',manifest),('config',checkpoint/'config.json'),('weights',checkpoint/'model.safetensors'))}
        loaded = SimpleNamespace(decoder=decoder_fixture(block_count=6),provenance={
            'files_sha256':{name:inputs[key]['sha256'] for name,key in (
                ('config.json','config'),('model.safetensors','weights'))}})
        return checkpoint,inputs,loaded

    def invoke(self,root,plan,loaded,label):
        path = root/(label+'-plan.json');path.write_bytes(canonical_json(plan))
        with patch.object(sys_module := worker.sys,'argv',['run_ordered_service_v30.py',str(path)]):
            with patch.object(worker,'source_hashes',return_value=plan['source_sha256']):
                with patch.object(worker,'verify_command_admission') as admission:
                    with patch('src.checkpoint_adapter.load_gpt2_checkpoint',return_value=loaded):
                        with contextlib.redirect_stdout(io.StringIO()):
                            worker.main()
                    admission.assert_called_once_with(plan['protocol_sha256'],'feasibility',
                        [sys_module.executable,str(Path(worker.__file__).resolve()),str(path.absolute())])
        out = Path(plan['output'])
        terminal = (out/'completion.json').read_bytes()
        self.assertEqual(terminal,(out/'progress.json').read_bytes())
        return strict_json(terminal)

    def test_complete_prepare_repair_indexed_and_cold_artifacts_match(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint,inputs,loaded = self.fixture(root)
            prepare = dict(policy('direct_fresh'),checkpoint=str(checkpoint),inputs=inputs,
                protocol_sha256='f'*64,output=str(root/'prepare'),record_ids=['a','b'],deleted_ids=[])
            original = self.invoke(root,prepare,loaded,'prepare')
            self.assertEqual(original['stage_count'],24)
            self.assertEqual(original['diagnostics']['neural_stage_record_pairs'],48)
            results = {}
            for method in ('repair','indexed_fresh','model_only_fresh'):
                bound = copy.deepcopy(inputs)
                if method != 'model_only_fresh':
                    bound['prior_state'] = dict(path=str(root/'prepare/state.bin'),
                        sha256=original['state_artifact']['sha256'])
                    bound['preparation_completion'] = dict(path=str(root/'prepare/completion.json'),
                        sha256=digest((root/'prepare/completion.json').read_bytes()))
                plan = dict(policy(method),checkpoint=str(checkpoint),inputs=bound,
                    protocol_sha256='f'*64,output=str(root/method),expected_target=original['fixed_target_sha256'])
                result = self.invoke(root,plan,loaded,method)
                self.assertTrue(result['model_roundtrip_exact'])
                self.assertEqual(result['artifacts'],{kind:result[kind+'_artifact']
                    for kind in ('model','state') if kind+'_artifact' in result})
                self.assertEqual(result['decoder_implementation_manifest'],original['decoder_implementation_manifest'])
                self.assertEqual(result['preparer_sha256'],original['preparer_sha256'])
                self.assertFalse(result['cross_method_model_agreement_checked'])
                results[method] = result
            self.assertEqual(len({row['model_artifact']['sha256'] for row in results.values()}),1)
            self.assertEqual(results['repair']['state_artifact'],results['indexed_fresh']['state_artifact'])
            self.assertEqual(results['repair']['diagnostics']['neural_stage_record_pairs'],0)
            self.assertEqual(results['model_only_fresh']['diagnostics']['neural_stage_record_pairs'],24)
            self.assertNotIn('state_artifact',results['model_only_fresh'])

    def test_new_preparer_matches_old_models_and_original_cold_is_supported(self):
        from tests.test_adaptive_worker_v30 import WorkerMiniatureIntegrationTests as OldWorkerTests
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint,inputs,loaded = self.fixture(root)
            common = dict(policy('direct_fresh'),checkpoint=str(checkpoint),inputs=inputs,
                protocol_sha256='f'*64,record_ids=['a','b'],deleted_ids=[])
            old_plan = dict(common,output=str(root/'old'))
            old = OldWorkerTests().invoke(root,old_plan,loaded,'old')
            prepared = self.invoke(root,dict(common,output=str(root/'new'),
                expected_model_sha256=old['model_artifact']['sha256']),loaded,'new')
            self.assertTrue(prepared['expected_model_agreement'])
            self.assertEqual(prepared['model_artifact'],old['model_artifact'])
            self.assertNotEqual(prepared['state_artifact']['sha256'],old['state_artifact']['sha256'])
            cold = self.invoke(root,dict(common,method='model_only_fresh',output=str(root/'cold-original'),
                expected_model_sha256=prepared['model_artifact']['sha256']),loaded,'cold-original')
            self.assertEqual(cold['model_artifact'],prepared['model_artifact'])
            self.assertTrue(cold['expected_model_agreement'])
            self.assertEqual(set(cold['artifacts']),{'model'})
            self.assertEqual(cold['diagnostics']['neural_stage_record_pairs'],48)
            bound = copy.deepcopy(inputs)
            bound['prior_state'] = dict(path=str(root/'old/state.bin'),sha256=old['state_artifact']['sha256'])
            bound['preparation_completion'] = dict(path=str(root/'old/completion.json'),
                sha256=digest((root/'old/completion.json').read_bytes()))
            rejected = dict(policy(),checkpoint=str(checkpoint),inputs=bound,
                protocol_sha256='f'*64,output=str(root/'old-rejected'))
            with self.assertRaisesRegex(ValueError,'preparation schema'):
                self.invoke(root,rejected,loaded,'old-rejected')
            self.assertFalse((root/'old-rejected/completion.json').exists())

    def test_registered_model_disagreement_is_an_explicit_failed_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint,inputs,loaded = self.fixture(root)
            plan = dict(policy('model_only_fresh'),checkpoint=str(checkpoint),inputs=inputs,
                protocol_sha256='f'*64,output=str(root/'bad-model'),expected_model_sha256='0'*64)
            with self.assertRaisesRegex(ValueError,'registered model hash differs'):
                self.invoke(root,plan,loaded,'bad-model')
            result = strict_json((root/'bad-model/progress.json').read_bytes())
            self.assertFalse(result['expected_model_agreement'])
            self.assertFalse((root/'bad-model/completion.json').exists())
            self.assertFalse((root/'bad-model/model.bin').exists())

    def test_failed_point_preflight_stops_before_service_or_neural_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint,inputs,loaded = self.fixture(root)
            plan = dict(policy('model_only_fresh'),checkpoint=str(checkpoint),inputs=inputs,
                protocol_sha256='f'*64,output=str(root/'cold'))
            plan['solver_budget']['max_work_units'] = 1
            with patch('src.ordered_fixed_service_v30.OrderedFixedAnchorService',
                       side_effect=AssertionError('service construction must not start')):
                with self.assertRaises(CalibrationWorkRefused):
                    self.invoke(root,plan,loaded,'refused')
            failed = strict_json((root/'cold/progress.json').read_bytes())
            self.assertEqual(failed['status'],'failed')
            self.assertFalse(failed['failure_admission']['neural_work_started'])
            self.assertFalse((root/'cold/model.bin').exists())
            self.assertFalse((root/'cold/completion.json').exists())


if __name__ == '__main__':
    unittest.main()
