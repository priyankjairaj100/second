"""Sequential state semantics on tiny deterministic software fixtures only."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.experiment_runner import run_comparison
from src.run_store import RunStore, canonical_json, digest, strict_json
from src.sequence_runner import run_sequence, run_sequence_manifest, validate_requests
from tests import test_experiment_runner as fixtures


class SequenceRunnerTests(unittest.TestCase):
    def fixture(self):
        decoder, service, records, heldout, metadata = fixtures.ExperimentRunnerTests().fixture()
        metadata.pop('request_id')
        metadata['sequence_id'] = 'sequence-fixture'
        return decoder, service, records, heldout, metadata

    def test_all_deletion_comparison_matches_empty_fresh(self):
        decoder, service, records, heldout, metadata = self.fixture()
        metadata['request_id'] = 'all'
        with tempfile.TemporaryDirectory() as directory:
            result = run_comparison(decoder, service, records, [r.record_id for r in records], heldout,
                                    RunStore(directory, {'all': True}), metadata)
            self.assertEqual(result['status'], 'complete', result.get('failure'))
            for row in result['methods'].values():
                self.assertTrue(row['exact_state_equal'])
                self.assertTrue(row['exact_model_equal'])
            state = service.load_state((Path(directory)/result['attempt']/'repair-state.json').read_bytes())
            self.assertEqual(state.retained_ids, ())

    def test_live_sequence_empty_all_and_resume_without_repreparation(self):
        decoder, service, records, heldout, metadata = self.fixture()
        requests = [{'request_id': 'empty', 'deleted_ids': []},
                    {'request_id': 'first', 'deleted_ids': ['0']},
                    {'request_id': 'all', 'deleted_ids': ['1', '2']},
                    {'request_id': 'after_all', 'deleted_ids': []}]
        fresh_sizes = []
        original_fresh = service.fresh
        def tracked(_service, records, **kwargs):
            records = tuple(records)
            fresh_sizes.append(len(records))
            return original_fresh(records, **kwargs)
        with tempfile.TemporaryDirectory() as directory, patch.object(type(service), 'fresh', tracked):
            result = run_sequence(decoder, service, records, requests, heldout, directory, metadata)
            self.assertEqual(result['status'], 'complete', result.get('failure'))
            self.assertEqual(fresh_sizes, [3, 3, 2, 0, 0])
            self.assertEqual(result['final_retained_ids'], [])
            for i, step in enumerate(result['steps']):
                row = strict_json((Path(directory)/f'step-{i:04d}'/'result.json').read_bytes())
                self.assertEqual(row['setup']['source'], 'preceding_committed_state')
                self.assertFalse(row['setup']['original_preparation_executed'])
                self.assertEqual(row['sequence_lineage']['predecessor_state_sha256'], step['predecessor_state_sha256'])
                if i:
                    self.assertEqual(step['predecessor_state_sha256'], result['steps'][i-1]['state_sha256'])
            with patch.object(type(service), 'fresh', side_effect=AssertionError('resume must not compute fresh')):
                saved = run_sequence(decoder, service, records, requests, heldout, directory, metadata)
            self.assertEqual(saved, result)
            self.assertEqual(len(list((Path(directory)/'initial').glob('attempt-*'))), 1)

    def test_failure_retains_future_requests_and_restarts_from_committed_prefix(self):
        decoder, service, records, heldout, metadata = self.fixture()
        requests = [{'request_id': 'first', 'deleted_ids': ['0']},
                    {'request_id': 'second', 'deleted_ids': ['1']},
                    {'request_id': 'third', 'deleted_ids': ['2']}]
        repair = service.repair
        def broken(_service, state, *args, **kwargs):
            if len(state.retained_ids) == 2:
                raise ArithmeticError('controlled middle-step failure')
            return repair(state, *args, **kwargs)
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(type(service), 'repair', broken):
                failed = run_sequence(decoder, service, records, requests, heldout, directory, metadata)
            self.assertEqual(failed['status'], 'failed')
            self.assertEqual([r['status'] for r in failed['steps']], ['complete','failed','not_started'])
            first_bytes = (Path(directory)/'step-0000'/'result.json').read_bytes()
            result = run_sequence(decoder, service, records, requests, heldout, directory, metadata)
            self.assertEqual(result['status'], 'complete', result.get('failure'))
            self.assertEqual(first_bytes, (Path(directory)/'step-0000'/'result.json').read_bytes())
            self.assertEqual(len(list((Path(directory)/'initial').glob('attempt-*'))), 1)
            self.assertEqual(len(list((Path(directory)/'step-0001').glob('attempt-*'))), 2)
            old_attempt = strict_json((Path(directory)/'step-0001'/'attempt-0001'/'status.json').read_bytes())
            self.assertEqual(old_attempt['status'], 'failed')

    def test_schedule_changes_and_tampered_child_are_rejected(self):
        decoder, service, records, heldout, metadata = self.fixture()
        requests = [{'request_id': 'first', 'deleted_ids': ['0']}]
        with tempfile.TemporaryDirectory() as directory:
            result = run_sequence(decoder, service, records, requests, heldout, directory, metadata)
            self.assertEqual(result['status'], 'complete')
            with self.assertRaisesRegex(ValueError, 'identity'):
                run_sequence(decoder, service, records, [{'request_id':'first','deleted_ids':['1']}],
                             heldout, directory, metadata)
            completion = strict_json((Path(directory)/'step-0000'/'result.json').read_bytes())
            model = Path(directory)/'step-0000'/completion['attempt']/'repair-model.json'
            model.write_bytes(model.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError, 'hash'):
                run_sequence(decoder, service, records, requests, heldout, directory, metadata)

    def test_initial_failure_preserves_all_planned_steps(self):
        decoder, service, records, heldout, metadata = self.fixture()
        requests = [{'request_id': 'one', 'deleted_ids': ['0']}, {'request_id': 'two', 'deleted_ids': ['1']}]
        with tempfile.TemporaryDirectory() as directory, patch.object(type(service), 'fresh', side_effect=MemoryError('fixture')):
            result = run_sequence(decoder, service, records, requests, heldout, directory, metadata)
            self.assertEqual(result['status'], 'failed')
            self.assertEqual([r['status'] for r in result['steps']], ['not_started','not_started'])
            self.assertEqual(result['failure']['stage'], 'initial_state')
            initial = strict_json((Path(directory)/'initial'/'result.json').read_bytes())
            self.assertEqual(initial['failure']['kind'], 'memory_limit')

    def test_repeated_removed_ids_and_wrong_predecessor_fail_before_execution(self):
        with self.assertRaises(ValueError):
            validate_requests([{'request_id':'one','deleted_ids':['0']},
                               {'request_id':'two','deleted_ids':['0']}], ['0','1'])
        decoder, service, records, heldout, metadata = self.fixture()
        state = service.fresh(records[:2]).state
        metadata['request_id'] = 'wrong-live'
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'initial state records'):
                run_comparison(decoder, service, records, ['0'], heldout, RunStore(directory, {'bad':1}),
                               metadata, initial_state=state)
            with self.assertRaisesRegex(ValueError, 'predecessor'):
                run_comparison(decoder, service, records[:2], ['0'], heldout, RunStore(directory, {'bad':2}),
                               metadata, initial_state=state, sequence_lineage={'predecessor_state_sha256':'0'*64})
            self.assertFalse((Path(directory)/'result.json').exists())

    def test_local_manifest_pause_guard_and_full_deletion_execution(self):
        from tests.test_checkpoint_adapter import checkpoint_fixture, write_checkpoint
        from src.chart_construction import ChartRecipe
        from src.target_manifest import TargetRecipe
        config, weights, _ = checkpoint_fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint = root/'checkpoint'
            checkpoint.mkdir()
            write_checkpoint(checkpoint, config, weights)
            provenance = {'dataset_id':'software','dataset_revision':'fixture-v1','split':'test','license':'test',
                          'tokenizer_id':'integer-fixture','tokenizer_revision':'v1'}
            prepared = {'schema':'prepared-token-records-v1','provenance':provenance,
                        'records':[{'id':'a','tokens':[0,1]},{'id':'b','tokens':[1,0]}]}
            heldout = dict(prepared, records=[{'id':'eval','tokens':[2,1]}])
            refs = {}
            for name, data in [('calibration',prepared), ('heldout',heldout),
                               ('protocol',{'status':'experiments_paused'})]:
                raw = canonical_json(data)
                (root/(name+'.json')).write_bytes(raw)
                refs[name] = {'path':name+'.json','sha256':digest(raw)}
            manifest = dict(schema='calibration-sequence-v1',sequence_id='all-sequence',root_id='r',
                configuration_id='c',repeat_index=0,phase='software_test',
                checkpoint={'path':'checkpoint','files_sha256':{
                    p.name:digest(p.read_bytes()) for p in checkpoint.iterdir()},'max_parameter_elements':1000},
                requests=[{'request_id':'all','deleted_ids':['a','b']}],
                target=TargetRecipe(original_token_count=4).payload(),
                chart=ChartRecipe(mode='none').payload(), method_order=['repair','indexed_fresh','direct_fresh'], **refs)
            path = root/'sequence.json'
            path.write_bytes(canonical_json(manifest))
            validated = run_sequence_manifest(path, root/'out', validate_only=True)
            self.assertEqual(validated['status'], 'validated')
            self.assertFalse((root/'out').exists())
            executed = run_sequence_manifest(path, root/'out')
            self.assertEqual(executed['status'], 'complete', executed.get('failure'))
            self.assertEqual(executed['final_retained_ids'], [])
            manifest['service_family'] = 'identity_cache'
            manifest['configuration_id'] = 'identity-cache-fixture'
            path.write_bytes(canonical_json(manifest))
            identity = run_sequence_manifest(path, root/'identity')
            self.assertEqual(identity['status'], 'complete', identity.get('failure'))
            row = strict_json((root/'identity'/'step-0000'/'result.json').read_bytes())
            self.assertEqual(row['service_family'], 'identity_cache')
            self.assertTrue(row['methods']['repair']['exact_state_equal'])
            manifest['phase'] = 'development'
            path.write_bytes(canonical_json(manifest))
            with self.assertRaisesRegex(ValueError, 'paused'):
                run_sequence_manifest(path, root/'paused')
            failure_files = list((root/'paused').glob('preflight-failure-*.json'))
            self.assertEqual(len(failure_files), 1)
            failure = strict_json(failure_files[0].read_bytes())
            self.assertEqual(failure['planned_requests'], manifest['requests'])


if __name__ == '__main__':
    unittest.main()
