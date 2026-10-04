"""Small software fixtures. These tests are not research measurements."""
from pathlib import Path
import tempfile
import unittest

from src.experiment_runner import (ComparisonMismatch, METHODS, heldout_nll, prepared_records,
                                   run_comparison, run_manifest)
from src.run_store import RunStore, canonical_json, digest, strict_json
from src.repair_service import Record
from tests.test_certified_transformer import small_decoder, grids


class ExperimentRunnerTests(unittest.TestCase):
    def fixture(self):
        decoder, chart = small_decoder()
        service = decoder.make_repair_service(grids(decoder), chart, group_count=1)
        records = tuple(Record(str(i), decoder.record_payload(t)) for i,t in enumerate(((0,1),(1,0),(0,2))))
        heldout = (Record('eval', decoder.record_payload((2,1))),)
        metadata = dict(root_id='software-root', request_id='delete-one', configuration_id='fixture',
                        repeat_index=0, phase='software_test', protocol_sha256='1'*64)
        return decoder, service, records, heldout, metadata

    def test_complete_equality_persistence_and_resume(self):
        decoder, service, records, heldout, metadata = self.fixture()
        with tempfile.TemporaryDirectory() as folder:
            store = RunStore(folder, {'fixture': 1})
            result = run_comparison(decoder, service, records, ['0'], heldout, store, metadata)
            self.assertEqual(result['status'], 'complete', result.get('failure'))
            self.assertEqual(set(result['planned_methods']), set(METHODS))
            for method in METHODS:
                row = result['methods'][method]
                self.assertTrue(row['exact_state_equal'])
                self.assertTrue(row['exact_model_equal'])
                self.assertGreater(row['complete_wall_time_ns'], 0)
                self.assertGreater(row['state_bytes'], 0)
            self.assertEqual(result['quality']['repaired'], result['quality']['retained_direct'])
            resumed = run_comparison(decoder, service, records, ['0'], heldout,
                                     RunStore(folder, {'fixture': 1}), metadata)
            self.assertEqual(resumed, result)
            self.assertEqual(len(list(Path(folder).glob('attempt-*'))), 1)
            state = Path(folder) / result['attempt'] / 'repair-state.json'
            state.write_bytes(state.read_bytes() + b' ')
            with self.assertRaises(ValueError):
                RunStore(folder, {'fixture': 1}).completed()

    def test_service_failure_preserves_attempted_and_unstarted_rows(self):
        decoder, service, records, heldout, metadata = self.fixture()
        class Broken:
            target_manifest_digest = service.target_manifest_digest
            manifest_digest = service.manifest_digest
            def fresh(self, records):
                raise ArithmeticError('controlled software failure')
        with tempfile.TemporaryDirectory() as folder:
            result = run_comparison(decoder, Broken(), records, ['0'], heldout,
                                    RunStore(folder, {'failure_fixture': 1}), metadata)
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(result['failure']['stage'], 'initial_fresh')
            self.assertTrue(all(x['status'] == 'not_started' for x in result['methods'].values()))
            self.assertIsNone(RunStore(folder, {'failure_fixture': 1}).completed())
            self.assertTrue((Path(folder) / 'writer.lock').exists())
            restarted=RunStore(folder, {'failure_fixture': 1})
            restarted.claim();restarted.close()

    def test_duplicate_requests_and_bad_method_order_fail_before_execution(self):
        decoder, service, records, heldout, metadata = self.fixture()
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                run_comparison(decoder, service, records, ['0','0'], heldout,
                               RunStore(folder, {'fixture': 1}), metadata)
            with self.assertRaises(ValueError):
                run_comparison(decoder, service, records, ['0'], heldout,
                               RunStore(folder, {'fixture': 1}), metadata, method_order=['repair']*3)
            self.assertFalse((Path(folder) / 'result.json').exists())

    def test_token_manifest_rejects_boolean_and_overlap_is_manifest_gate(self):
        decoder, *_ = self.fixture()
        payload = {'schema':'prepared-token-records-v1', 'provenance': {
            'dataset_id':'software','dataset_revision':'fixture-v1','split':'test','license':'test',
            'tokenizer_id':'integer-fixture','tokenizer_revision':'v1'},
            'records':[{'id':'a','tokens':[0,True]}]}
        with self.assertRaises(ValueError): prepared_records(payload,decoder)
        payload['records'][0]['tokens'] = [0, 1]
        self.assertEqual(len(prepared_records(payload,decoder)),1)

    def test_atomic_store_rejects_unsafe_names_and_complete_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            store=RunStore(folder,{'test':1})
            store.claim()
            for name in ('../bad','status.json','bad/name'):
                with self.assertRaises(ValueError): store.write_artifact(name,b'bad')
            store.write_artifact('state.json',b'{}')
            store.finish({'status':'complete'})
            with self.assertRaises(RuntimeError): store.write_artifact('late.json',b'{}')
            store.close()
            with self.assertRaises(RuntimeError): RunStore(folder,{'test':1}).claim()
            with self.assertRaises(ValueError): RunStore(folder,{'test':2}).completed()

    def test_exception_after_commit_releases_lock_and_preserves_completion(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(RuntimeError, 'after commit'):
                with RunStore(folder, {'sealed':1}) as store:
                    store.write_artifact('state.json',b'{}')
                    store.finish({'status':'complete'})
                    raise RuntimeError('after commit')
            self.assertEqual(RunStore(folder, {'sealed':1}).completed()['status'],'complete')
            with self.assertRaisesRegex(RuntimeError, 'already completed'):
                RunStore(folder, {'sealed':1}).claim()

    def test_preflight_failure_has_durable_record(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            path=root/'bad.json'
            path.write_bytes(b'{"schema":"wrong"}')
            with self.assertRaises(ValueError): run_manifest(path,root/'out',validate_only=True)
            failed=list((root/'out').glob('preflight-failure-*.json'))
            self.assertEqual(len(failed),1)
            self.assertEqual(strict_json(failed[0].read_bytes())['status'],'failed')
            self.assertFalse((root/'out'/'result.json').exists())

    def test_validate_only_local_checkpoint_without_feature_execution(self):
        from tests.test_checkpoint_adapter import checkpoint_fixture, write_checkpoint
        from src.target_manifest import TargetRecipe
        from src.chart_construction import ChartRecipe
        config,weights,_ = checkpoint_fixture()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            checkpoint=root/'checkpoint';checkpoint.mkdir()
            write_checkpoint(checkpoint,config,weights)
            provenance={'dataset_id':'software','dataset_revision':'fixture-v1','split':'test','license':'test',
                        'tokenizer_id':'integer-fixture','tokenizer_revision':'v1'}
            calibration={'schema':'prepared-token-records-v1','provenance':provenance,
                         'records':[{'id':'a','tokens':[0,1]},{'id':'b','tokens':[1,0]}]}
            heldout={'schema':'prepared-token-records-v1','provenance':provenance,
                     'records':[{'id':'eval','tokens':[2,1]}]}
            refs={}
            for name,data in (('calibration',calibration),('heldout',heldout),('protocol',{'phase':'software_test'})):
                raw=canonical_json(data);(root/(name+'.json')).write_bytes(raw)
                refs[name]={'path':name+'.json','sha256':digest(raw)}
            manifest=dict(schema='calibration-run-v1',root_id='r',request_id='q',configuration_id='c',repeat_index=0,
                phase='software_test',checkpoint={'path':'checkpoint','files_sha256':{
                    p.name:digest(p.read_bytes()) for p in checkpoint.iterdir()},'max_parameter_elements':1000},
                deleted_ids=['a'],target=TargetRecipe(original_token_count=4).payload(),
                chart=ChartRecipe(mode='none').payload(),method_order=list(METHODS),**refs)
            run=root/'run.json';run.write_bytes(canonical_json(manifest))
            result=run_manifest(run,root/'output',validate_only=True)
            self.assertEqual(result['status'],'validated')
            self.assertFalse(result['empirical_work_executed'])
            self.assertFalse((root/'output').exists())
            executed=run_manifest(run,root/'output')
            self.assertEqual(executed['status'],'complete',executed.get('failure'))
            from src.result_analysis import validate_run
            validate_run(executed)
            self.assertNotEqual(executed['target_manifest_sha256'],executed['service_job_sha256'])
            manifest['phase']='confirmation'
            run.write_bytes(canonical_json(manifest))
            with self.assertRaisesRegex(ValueError, 'frozen protocol'):
                run_manifest(run,root/'unfrozen-confirmation')


if __name__=='__main__': unittest.main()
