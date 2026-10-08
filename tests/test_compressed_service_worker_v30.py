"""Compressed worker software fixtures; no empirical checkpoint is loaded."""
import contextlib
import copy
from dataclasses import replace
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import run_compressed_service_v30 as worker
from src.adaptive_calibration_v30 import CalibrationWorkRefused
from src.run_store import canonical_json, digest, strict_json
from tests import test_adaptive_worker_v30 as point_fixtures
from tests import test_ordered_worker_v30 as ordered_fixtures
from tests.test_adaptive_worker_v30 import policy as point_policy, records


def policy(method='repair'):
    result = point_policy(method)
    result.update(codec_bits=40, block_size=256, decoder_backend='scalar', certificate_backend='auto',
        sparse_budget=dict(max_workspace_bytes=64*2**20, max_work_units=100_000_000,
            max_preconditioned_coordinates=4, max_rounds=4),
        max_certificate_work_units=1_000_000_000,
        max_certificate_workspace_bytes=64*2**20,
        max_neural_stage_record_pairs=0 if method == 'convert_lossless' else 24,
        expected_target='a'*64)
    if method == 'convert_lossless':
        result.update(record_ids=['a', 'b'], deleted_ids=[])
    return result


def completion_fixture():
    plan = policy()
    plan['inputs'] = {'records': dict(path='/fixture/records', sha256='1'*64)}
    original = tuple(records()['records'])
    completion = dict(schema=worker.SCHEMA, method='convert_lossless', status='complete',
        decoder_backend='scalar', preparer_sha256=worker.expected_preparer('scalar'),
        max_certificate_workspace_bytes=plan['max_certificate_workspace_bytes'],
        complete_model=True, complete_state=True, model_roundtrip_exact=True, state_roundtrip_canonical=True,
        confirmation=False, scientific_promotion=False, use_candidates=False,
        original_record_ids=['a', 'b'], retained_record_ids=['a', 'b'], committed_record_ids=['a', 'b'],
        deleted_record_ids=[], original_token_count=4,
        original_records_sha256=digest(canonical_json(records())), records_input_sha256='1'*64,
        fixed_target_sha256='a'*64, base_target_sha256='b'*64,
        stage_count=24, stage_ids=['stage-'+str(i) for i in range(24)],
        solver_backend=plan['solver_backend'], solver_budget=plan['solver_budget'],
        max_point_work_units=plan['max_point_work_units'],
        target_recipe=dict(schema='fixed-target-recipe-v1', bits=4, group_count=1,
            max_grid_entries=1000000, original_token_count=4, ridge=[1, 100]),
        evaluator_id='software-fixture', checkpoint_files_sha256={'config.json':'2'*64, 'model.safetensors':'3'*64},
        model_artifact=dict(file='model.bin', bytes=1, sha256='4'*64))
    return plan, completion, original


class WorkerContractTests(unittest.TestCase):
    def test_policy_is_explicit_bounded_and_initial_codec_is_fixed(self):
        worker.validate_policy(policy())
        cases = dict(codec_bits=24, block_size=128, decoder_backend=None, expected_target=None, use_candidates=True,
            certificate_backend='unlimited', solver_backend='rational', max_point_work_units=0,
            max_certificate_work_units=-1, max_neural_stage_record_pairs=True, sparse_budget={},
            max_certificate_workspace_bytes=2**30+1,
            original_token_count=True, phase='confirmation')
        for key, value in cases.items():
            with self.subTest(key=key), self.assertRaises((ValueError, TypeError)):
                worker.validate_policy(dict(policy(), **{key:value}))
        with self.assertRaisesRegex(ValueError, 'zero neural'):
            worker.validate_policy(dict(policy('convert_lossless'), max_neural_stage_record_pairs=1))
        with self.assertRaisesRegex(ValueError, 'scalar certificate workspace'):
            worker.validate_policy(dict(policy(), max_certificate_workspace_bytes=2**30))
        worker.validate_policy(dict(policy(), decoder_backend='ordered', max_certificate_workspace_bytes=2**30))

    def test_records_keep_original_normalization_and_allow_full_deletion(self):
        original, retained = worker.select_records(policy(), records())
        self.assertEqual([row['id'] for row in retained], ['b'])
        self.assertEqual(sum(len(row['tokens']) for row in original), 4)
        _, retained = worker.select_records(dict(policy(), record_ids=[], deleted_ids=['a', 'b']), records())
        self.assertEqual(retained, ())
        for changes in ({'original_token_count':2}, {'record_ids':['a', 'b']}, {'deleted_ids':['z']}):
            with self.assertRaises(ValueError):
                worker.select_records(dict(policy(), **changes), records())
        worker.select_records(policy('convert_lossless'), records())
        with self.assertRaises(ValueError):
            worker.select_records(dict(policy('convert_lossless'), record_ids=['b'], deleted_ids=['a']), records())

    def test_input_capabilities_exclude_exact_factor_input_from_repair(self):
        self.assertEqual(worker.required_inputs('convert_lossless'),
            {'records', 'lossless_state', 'lossless_model', 'lossless_completion'})
        self.assertEqual(worker.required_inputs('repair'), worker.required_inputs('indexed_fresh'))
        self.assertNotIn('lossless_state', worker.required_inputs('repair'))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = dict(policy(), inputs={})
            for name in worker.required_inputs('repair'):
                path = root/name; path.write_bytes(name.encode())
                plan['inputs'][name] = dict(path=str(path), sha256=digest(path.read_bytes()))
            worker.validate_inputs(plan)
            bad = copy.deepcopy(plan); bad['inputs']['lossless_state'] = bad['inputs']['prior_state']
            with self.assertRaises(ValueError):worker.validate_inputs(bad)
            bad = copy.deepcopy(plan); bad['inputs']['prior_state']['sha256'] = '0'*64
            with self.assertRaises(ValueError):worker.validate_inputs(bad)
            (root/'alias').symlink_to(root/'prior_state')
            bad = copy.deepcopy(plan); bad['inputs']['prior_state']['path'] = str(root/'alias')
            with self.assertRaises(ValueError):worker.validate_inputs(bad)

    def test_original_and_reference_metadata_reject_target_or_membership_drift(self):
        plan, completion, original = completion_fixture()
        worker.validate_original_metadata(plan, completion, original, schema=worker.SCHEMA, method='convert_lossless')
        changes = dict(status='failed', complete_model=False, complete_state=False, committed_record_ids=['b'],
            original_token_count=2, records_input_sha256='0'*64, fixed_target_sha256='c'*64,
            solver_backend='primal', max_point_work_units=1, target_recipe={}, stage_count=23,
            stage_ids=['same']*24, state_roundtrip_canonical=False, scientific_promotion=True,
            decoder_backend='ordered', preparer_sha256='0'*64)
        for key, value in changes.items():
            with self.subTest(key=key), self.assertRaises(ValueError):
                worker.validate_original_metadata(plan, dict(completion, **{key:value}), original,
                    schema=worker.SCHEMA, method='convert_lossless')
        reference = dict(completion, schema=worker.LOSSLESS_SCHEMA, method='model_only_fresh',
            retained_record_ids=['b'], deleted_record_ids=['a'])
        worker.validate_reference(plan, reference, original, original[1:], completion)
        for key, value in dict(evaluator_id='other', checkpoint_files_sha256={}, retained_record_ids=['a'],
                target_recipe={}, solver_budget={}, records_input_sha256='0'*64).items():
            with self.subTest(reference_key=key), self.assertRaises(ValueError):
                worker.validate_reference(plan, dict(reference, **{key:value}), original, original[1:], completion)

    def test_ordered_schema_preparer_and_implementation_are_bound_together(self):
        plan, completion, original = completion_fixture()
        plan = dict(plan, decoder_backend='ordered')
        manifest = {'schema':'software-ordered-manifest'}
        completion.update(decoder_backend='ordered', preparer_sha256=worker.expected_preparer('ordered'),
            decoder_implementation_manifest=manifest, decoder_implementation_sha256=digest(canonical_json(manifest)))
        worker.validate_original_metadata(plan, completion, original, schema=worker.SCHEMA, method='convert_lossless')
        reference = dict(completion, schema=worker.ORDERED_LOSSLESS_SCHEMA, method='repair',
            retained_record_ids=['b'], deleted_record_ids=['a'])
        worker.validate_reference(plan, reference, original, original[1:], completion)
        for bad in (dict(completion, preparer_sha256=worker.expected_preparer('scalar')),
                    dict(completion, decoder_implementation_sha256='0'*64)):
            with self.assertRaises(ValueError):
                worker.validate_backend_metadata(plan, bad)
        with self.assertRaisesRegex(ValueError, 'schema'):
            worker.validate_reference(plan, dict(reference, schema=worker.LOSSLESS_SCHEMA), original, original[1:], completion)


class ConversionTests(unittest.TestCase):
    def fixture(self):
        from tests.test_fixed_compressed_state_v26 import factor_state
        from src.fixed_factor_state import preparer_binding
        from src.fixed_lossless_state_v29 import from_factor_state
        from src.compact_state import CompactState, serialize
        exact = factor_state()
        binding = preparer_binding()
        exact = replace(exact, preparer_sha256=binding,
            anchors=tuple(replace(leaf, preparer_sha256=binding) for leaf in exact.anchors))
        lossless = from_factor_state(exact)
        model = serialize(CompactState(exact.target_sha256, exact.stages, ()))
        source = tuple(dict(id=leaf.record_id, tokens=list(leaf.tokens)) for leaf in exact.anchors)
        return exact, lossless, model, source

    def test_conversion_checks_every_factor_and_preserves_canonical_model(self):
        from src.fixed_compressed_state_v26 import serialize, parse
        exact, lossless, model, source = self.fixture()
        converted, metrics = worker.convert_verified_state(lossless, model, source)
        self.assertEqual(metrics['decoded_exact_factors'], 6)
        self.assertEqual(metrics['checked_enclosures'], 6)
        self.assertEqual(metrics['decoded_source_bytes'], sum(len(b.binary64) for a in exact.anchors for b in a.blocks))
        self.assertTrue(metrics['every_enclosure_contains_source'])
        self.assertEqual(metrics['neural_stage_record_pairs'], 0)
        self.assertEqual(metrics['point_solver_stages'], 0)
        self.assertEqual((converted.bits, converted.block_size), (40, 256))
        self.assertEqual(parse(serialize(converted)), converted)
        worker.verify_state_model(converted, model, source)

    def test_wrong_model_preparer_source_hash_or_containment_is_rejected(self):
        from src.fixed_factor_codec_v26 import FactorDescriptor
        _, lossless, model, source = self.fixture()
        with self.assertRaisesRegex(ValueError, 'model bytes'):
            worker.convert_verified_state(lossless, model+b'x', source)
        bad = replace(lossless, preparer_sha256='0'*64)
        with self.assertRaisesRegex(ValueError, 'preparer'):
            worker.convert_verified_state(bad, model, source)
        with patch.object(FactorDescriptor, 'box', return_value=SimpleNamespace(contains=lambda array:False)):
            with self.assertRaisesRegex(ValueError, 'excludes'):
                worker.convert_verified_state(lossless, model, source)
        converted, _ = worker.convert_verified_state(lossless, model, source)
        first = converted.anchors[0]
        bad_descriptor = replace(first.descriptors[0], source_sha256='0'*64)
        bad_leaf = replace(first, descriptors=(bad_descriptor, *first.descriptors[1:]))
        bad_state = replace(converted, anchors=(bad_leaf, *converted.anchors[1:]))
        with patch('src.fixed_compressed_state_v26.from_factor_state', return_value=bad_state):
            with self.assertRaisesRegex(ValueError, 'source hash'):
                worker.convert_verified_state(lossless, model, source)


class HistoricalClosureTests(unittest.TestCase):
    def test_historical_sources_registration_and_terminal_verifier_are_required(self):
        with tempfile.TemporaryDirectory() as directory:
            campaign = Path(directory)/'campaign'; attempt = campaign/'attempts'/'original'
            output = attempt/'outputs'; output.mkdir(parents=True)
            source = campaign/'source'; (source/'src').mkdir(parents=True); (source/'scripts').mkdir()
            (source/'src'/'fixture.py').write_text('SOFTWARE_FIXTURE = True\n')
            hashes = worker.source_hashes(source)
            program = canonical_json(dict(source_sha256=hashes))
            protocol = canonical_json(dict(program_sha256=digest(program)))
            registration = dict(program_sha256=digest(program), protocol_sha256=digest(protocol))
            plan = dict(registration, source_sha256=hashes)
            completed = dict(source_sha256=hashes, plan_sha256=digest(canonical_json(plan)), worker_transaction_elapsed_ns=7)
            for path, value in ((campaign/'registration.json', registration), (attempt/'plan.json', plan),
                    (attempt/'transaction.json', dict(controller_elapsed_ns=9, receipt_sha256='a'*64)),
                    (output/'completion.json', completed)):
                path.write_bytes(canonical_json(value))
            (campaign/'program.json').write_bytes(program); (campaign/'protocol.json').write_bytes(protocol)
            entry = dict(path=str(output/'completion.json'), sha256=digest(canonical_json(completed)))
            with patch.object(worker, 'verify_completed', return_value=completed) as verified:
                result, evidence, path = worker.verify_registered_completion(entry)
                verified.assert_called_once_with(attempt)
                self.assertEqual(path, attempt)
                self.assertEqual(result, completed)
                self.assertEqual(evidence['controller_elapsed_ns'], 9)
                self.assertEqual(evidence['worker_elapsed_ns'], 7)
            with patch.object(worker, 'verify_completed', side_effect=ValueError('receipt tamper')):
                with self.assertRaisesRegex(ValueError, 'receipt tamper'):
                    worker.verify_registered_completion(entry)
            (source/'src'/'fixture.py').write_text('CHANGED = True\n')
            with patch.object(worker, 'verify_completed', side_effect=AssertionError('must reject source first')):
                with self.assertRaisesRegex(ValueError, 'frozen source'):
                    worker.verify_registered_completion(entry)


class MiniatureWorkerTests(unittest.TestCase):
    """Only the small deterministic decoder fixture substitutes checkpoint loading."""
    def invoke(self, root, plan, loaded, label):
        path = root/(label+'-plan.json'); path.write_bytes(canonical_json(plan))
        def verified(entry):
            completion = strict_json(Path(entry['path']).read_bytes())
            self.assertEqual(digest(canonical_json(completion)), entry['sha256'])
            return completion, dict(completion_sha256=entry['sha256'], controller_elapsed_ns=9,
                worker_elapsed_ns=7, software_fixture=True), Path(entry['path']).parent.parent
        with patch.object(worker.sys, 'argv', ['run_compressed_service_v30.py', str(path)]), \
             patch.object(worker, 'source_hashes', return_value=plan['source_sha256']), \
             patch.object(worker, 'verify_command_admission') as admission, \
             patch.object(worker, 'verify_registered_completion', side_effect=verified), \
             patch('src.checkpoint_adapter.load_gpt2_checkpoint', return_value=loaded), \
             contextlib.redirect_stdout(io.StringIO()):
            worker.main()
            admission.assert_called_once_with(plan['protocol_sha256'], 'feasibility',
                [worker.sys.executable, str(Path(worker.__file__).resolve()), str(path.absolute())])
        output = Path(plan['output']); raw = (output/'completion.json').read_bytes()
        self.assertEqual(raw, (output/'progress.json').read_bytes())
        result = strict_json(raw)
        self.assertEqual(result['artifacts']['model'], result['model_artifact'])
        self.assertEqual(result['artifacts']['state'], result['state_artifact'])
        for item in result['artifacts'].values():
            payload = (output/item['file']).read_bytes()
            self.assertEqual(digest(payload), item['sha256']); self.assertEqual(len(payload), item['bytes'])
        return result

    def check_backend(self, decoder_backend):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture_module = ordered_fixtures if decoder_backend == 'ordered' else point_fixtures
            helper = fixture_module.WorkerMiniatureIntegrationTests()
            checkpoint, base_inputs, loaded = helper.fixture(root)
            original_dir = root/'original'/'outputs'
            prepare = dict(point_policy('direct_fresh'), checkpoint=str(checkpoint), inputs=base_inputs,
                protocol_sha256='f'*64, output=str(original_dir), record_ids=['a','b'], deleted_ids=[])
            original = helper.invoke(root, prepare, loaded, 'original')
            cold_dir = root/'cold'/'outputs'
            cold = dict(point_policy('model_only_fresh'), checkpoint=str(checkpoint), inputs=base_inputs,
                protocol_sha256='f'*64, output=str(cold_dir), expected_target=original['fixed_target_sha256'])
            expected = helper.invoke(root, cold, loaded, 'cold')
            def bound(path):return dict(path=str(path), sha256=digest(path.read_bytes()))
            inputs = dict(records=base_inputs['records'], lossless_state=bound(original_dir/'state.bin'),
                lossless_model=bound(original_dir/'model.bin'), lossless_completion=bound(original_dir/'completion.json'))
            conversion_dir = root/'conversion'/'outputs'
            conversion_plan = dict(policy('convert_lossless'), decoder_backend=decoder_backend,
                inputs=inputs, protocol_sha256='f'*64,
                output=str(conversion_dir), expected_target=original['fixed_target_sha256'])
            conversion = self.invoke(root, conversion_plan, loaded, 'conversion')
            self.assertEqual(conversion['model_artifact'], original['model_artifact'])
            self.assertEqual(conversion['diagnostics']['checked_enclosures'], 48)
            self.assertGreater(conversion['conversion_elapsed_ns'], 0)
            self.assertIn('external_lossless_preparation', conversion)
            repair_inputs = dict(base_inputs, prior_state=bound(conversion_dir/'state.bin'),
                compressed_preparation_completion=bound(conversion_dir/'completion.json'),
                reference_completion=bound(cold_dir/'completion.json'))
            outcomes = []
            for method in ('repair', 'indexed_fresh'):
                plan = dict(policy(method), decoder_backend=decoder_backend, checkpoint=str(checkpoint), inputs=repair_inputs,
                    protocol_sha256='f'*64, output=str(root/method/'outputs'),
                    expected_target=original['fixed_target_sha256'], expected_model_sha256=expected['model_artifact']['sha256'])
                outcome = self.invoke(root, plan, loaded, method)
                self.assertEqual(outcome['model_artifact'], expected['model_artifact'])
                self.assertTrue(outcome['retained_reference_model_byte_equal'])
                self.assertEqual(outcome['diagnostics']['neural_stage_record_pairs'], 0)
                self.assertEqual(outcome['diagnostics']['model_seed_source'], 'none')
                self.assertIn('external_compressed_conversion', outcome)
                outcomes.append(outcome)
            self.assertEqual(outcomes[0]['state_artifact'], outcomes[1]['state_artifact'])
            if decoder_backend == 'ordered':
                # Force complete ordered fallback through the worker's explicit caps.
                fallback_plan = dict(plan, method='repair', max_certificate_work_units=0,
                    output=str(root/'ordered-fallback'/'outputs'))
                fallback = self.invoke(root, fallback_plan, loaded, 'ordered-fallback')
                self.assertEqual(fallback['model_artifact'], expected['model_artifact'])
                self.assertEqual(fallback['state_artifact'], outcomes[0]['state_artifact'])
                self.assertEqual(fallback['diagnostics']['neural_stage_record_pairs'], 24)
                self.assertEqual(fallback['diagnostics']['certificate_work_units_reserved'], 0)
                from src.ordered_compressed_service_v30 import NeuralBudgetExceeded
                refused = dict(fallback_plan, max_neural_stage_record_pairs=0,
                    output=str(root/'neural-refused'/'outputs'))
                with self.assertRaises(NeuralBudgetExceeded):
                    self.invoke(root, refused, loaded, 'neural-refused')
                failure = strict_json((root/'neural-refused'/'outputs'/'progress.json').read_bytes())
                self.assertEqual(failure['failure_diagnostics']['neural_stage_record_pairs'], 0)
                self.assertFalse((root/'neural-refused'/'outputs'/'completion.json').exists())
            # Full deletion commits the empty source state and the exact prior-only model.
            empty_cold = dict(cold, record_ids=[], deleted_ids=['a', 'b'], output=str(root/'empty-cold'/'outputs'))
            empty_reference = helper.invoke(root, empty_cold, loaded, 'empty-cold')
            empty_inputs = dict(repair_inputs,
                reference_completion=bound(root/'empty-cold'/'outputs'/'completion.json'))
            empty_plan = dict(plan, method='repair', record_ids=[], deleted_ids=['a', 'b'], inputs=empty_inputs,
                output=str(root/'empty-repair'/'outputs'), expected_model_sha256=empty_reference['model_artifact']['sha256'])
            empty = self.invoke(root, empty_plan, loaded, 'empty-repair')
            self.assertEqual(empty['committed_record_ids'], [])
            self.assertEqual(empty['retained_token_count'], 0)
            self.assertEqual(empty['diagnostics']['neural_stage_record_pairs'], 0)
            self.assertEqual(empty['model_artifact'], empty_reference['model_artifact'])
            # Admission failure must happen before construction or neural replay.
            blocked = dict(plan, max_point_work_units=1, output=str(root/'blocked'/'outputs'))
            service_path = ('src.ordered_compressed_service_v30.OrderedCompressedService' if decoder_backend == 'ordered'
                else 'src.adaptive_compressed_service_v30.AdaptiveCompressedService')
            with patch.object(worker, 'validate_original_metadata'), patch.object(worker, 'validate_reference'), \
                 patch(service_path,
                       side_effect=AssertionError('service must not be constructed')):
                with self.assertRaises(CalibrationWorkRefused):
                    self.invoke(root, blocked, loaded, 'blocked')
            failure = strict_json((root/'blocked'/'outputs'/'progress.json').read_bytes())
            self.assertFalse(failure['failure_admission']['neural_work_started'])
            self.assertFalse((root/'blocked'/'outputs'/'completion.json').exists())

    def test_scalar_conversion_repair_indexed_and_full_deletion(self):
        self.check_backend('scalar')

    def test_ordered_conversion_repair_indexed_and_full_deletion(self):
        self.check_backend('ordered')


if __name__ == '__main__':
    unittest.main()
