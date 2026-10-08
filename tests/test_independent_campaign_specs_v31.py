"""Prospective metadata contracts. No empirical worker or checkpoint is invoked."""
import copy
import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import prepare_independent_campaigns_v31 as prepare
from src.run_store import canonical_json


class IndependentCampaignSpecV31Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.specs = prepare.build()
        cls.draft = json.loads((prepare.ROOT/'campaigns/independent_requests_v30_draft/specification.json').read_bytes())
        cls.selection = json.loads((prepare.ROOT/'campaigns/independent_requests_v30_draft/selection.json').read_bytes())

    def test_ready_files_reproduce_exactly_without_pending_output_reads(self):
        with patch.object(prepare, 'checked_json', wraps=prepare.checked_json) as reads:
            rebuilt = prepare.build()
        self.assertEqual(len(reads.call_args_list), 5)
        self.assertTrue(all('/attempts/' not in str(call.args[0]) for call in reads.call_args_list))
        for corpus, spec in rebuilt.items():
            path = prepare.ROOT/'campaigns/independent_requests_v31_ready'/(corpus+'.spec.json')
            self.assertEqual(path.read_bytes(), canonical_json(spec))
            self.assertEqual(spec['status'], 'draft_unregistered')
            self.assertNotIn('source_sha256', spec)
            self.assertNotIn('proposed_source_inventory', spec)

    def test_all_point_trials_are_preserved_exactly(self):
        for root in self.draft['roots']:
            spec = self.specs[root['corpus']]
            self.assertEqual(spec['trials'][:5], root['point_trials'])
            self.assertEqual(spec['requests'], root['requests'])
            self.assertEqual(spec['source_ids'], root['source_ids'])
            self.assertEqual(spec['execution_order'], [t['id'] for t in spec['trials']])
        orders = [request['method_order'] for spec in self.specs.values() for request in spec['requests']]
        self.assertEqual(orders.count(['repair', 'cold']), 2)
        self.assertEqual(orders.count(['cold', 'repair']), 2)

    def test_selection_tokens_and_all_provenance_descriptors_are_bound(self):
        for corpus, spec in self.specs.items():
            descriptors = spec['prerequisite_files']
            self.assertEqual(set(descriptors), {'draft', 'selection', 'records', 'compressed_policy'})
            for name, entry in descriptors.items():
                self.assertEqual(prepare.descriptor(entry['path']), entry)
            self.assertEqual(descriptors['records'], self.selection['token_inputs'][corpus])
            self.assertEqual(descriptors['selection']['sha256'], prepare.DRAFT_HASHES['selection.json'])
            self.assertEqual(descriptors['draft']['sha256'], prepare.DRAFT_HASHES['specification.json'])
            self.assertEqual(descriptors['records']['sha256'], prepare.DRAFT_HASHES[corpus+'-records.json'])
            rows = json.loads(Path(descriptors['records']['path']).read_bytes())['records']
            self.assertEqual([row['id'] for row in rows], spec['source_ids'])
            self.assertEqual([len(row['tokens']) for row in rows], [128, 128])
            self.assertEqual(spec['trials'][-1]['plan']['deleted_ids'], [spec['source_ids'][0]])

    def test_seven_complete_reservations_fit_each_separate_cap(self):
        for spec in self.specs.values():
            self.assertEqual(len(spec['trials']), 7)
            self.assertEqual(sum(t['cpu_seconds']+2 for t in spec['trials']), 1844)
            self.assertEqual(spec['phase_cpu_cap_seconds'], 1900)
            self.assertEqual(spec['maximum_complete_reservations_seconds'], 1844)
            conversion, repair = spec['trials'][-2:]
            self.assertEqual((conversion['cpu_seconds'], conversion['wall_seconds']), (120, 180))
            self.assertEqual((repair['cpu_seconds'], repair['wall_seconds']), (300, 420))
            self.assertEqual(spec['registration_sequence'], ['independent_wikitext_v31', 'independent_c4_v31'])

    def test_every_worker_accepts_exact_prospective_input_capabilities(self):
        from scripts import run_ordered_service_v30 as ordered
        from scripts import run_compressed_service_v31 as compressed
        for spec in self.specs.values():
            for trial in spec['trials']:
                worker = compressed if trial['script'] == 'run_compressed_service_v31.py' else ordered
                worker.validate_policy(trial['plan'])
                now = set(trial['plan']['inputs'])
                later = set(trial.get('inputs_from_trial', {}))
                self.assertFalse(now & later)
                self.assertEqual(now | later, worker.required_inputs(trial['plan']['method']))
                payload = json.loads(Path(trial['plan']['inputs']['records']['path']).read_bytes())
                original, retained = worker.select_records(trial['plan'], payload)
                self.assertEqual(sum(len(row['tokens']) for row in original), 256)
                self.assertEqual(sum(len(row['tokens']) for row in retained),
                    256 if trial['plan']['method'] in ('direct_fresh', 'convert_lossless') else 128)
                if trial['plan']['method'] == 'model_only_fresh':
                    self.assertFalse(later)
                    self.assertEqual(now, {'records', 'config', 'weights'})

    def test_appended_compressed_control_uses_matching_zero_deletion_references(self):
        for spec in self.specs.values():
            conversion, repair = spec['trials'][-2:]
            original = spec['trials'][0]['id']
            request = spec['requests'][0]
            self.assertEqual({v['trial'] for v in conversion['inputs_from_trial'].values()}, {original})
            self.assertEqual(repair['inputs_from_trial']['reference_completion'],
                dict(trial=request['cold_trial'], completion=True))
            self.assertEqual(repair['storage_gate'],
                dict(artifact='state', trial=request['repair_trial'], strictly_smaller=True))
            self.assertEqual(repair['latency_gate'], dict(trials=[request['cold_trial']],
                aggregation='minimum_recorded_controller_elapsed_ns', strictly_faster=True))
            self.assertEqual(repair['compare_to'], [dict(trial=request['cold_trial'], artifacts=['model'])])
            self.assertEqual(conversion['compare_to'], [dict(trial=original, artifacts=['model'])])
            known = set()
            for trial in spec['trials']:
                bindings = list(trial.get('inputs_from_trial', {}).values())
                bindings += trial.get('depends', []) + trial.get('compare_to', [])
                self.assertTrue(all(binding['trial'] in known for binding in bindings))
                known.add(trial['id'])

    def test_reviewed_numerical_policy_is_copied_without_retuning(self):
        reference = json.loads((prepare.ROOT/'campaigns/compressed_service_v31.spec.json').read_bytes())
        policy = prepare.checked_policy(reference)
        for spec in self.specs.values():
            self.assertEqual({k: spec['trials'][-1]['plan'][k] for k in prepare.POLICY_FIELDS}, policy)
            converted = {k: spec['trials'][-2]['plan'][k] for k in prepare.POLICY_FIELDS}
            self.assertEqual(converted, dict(policy, max_neural_stage_record_pairs=0))
            self.assertEqual(spec['prerequisite_policy']['fields'], list(prepare.POLICY_FIELDS))
            self.assertEqual(spec['prerequisite_policy']['trial'], 'repair-128-48')
        for field, replacement in [('max_certificate_workspace_bytes', 536870912),
                                    ('codec_bits', 40), ('use_candidates', True)]:
            changed = copy.deepcopy(reference)
            changed['trials'][1]['plan'][field] = replacement
            with self.subTest(field=field), self.assertRaises(ValueError):
                prepare.checked_policy(changed)

    def test_all_ordered_models_and_quality_flags_are_required_before_registration(self):
        expected_trials = {'prepare-256', 'original-model-256', 'repair-001', 'cold-001', 'indexed-001',
                           'cold-002', 'repair-002', 'repair-003', 'cold-003'}
        for spec in self.specs.values():
            external = spec['external_attempts']
            self.assertEqual({k.removeprefix('ordered-') for k in external if k.startswith('ordered-')},
                expected_trials)
            self.assertEqual(spec['resource_shape_reference'], 'ordered-prepare-256')
            for key, entry in external.items():
                self.assertTrue(Path(entry['attempt']).is_absolute())
                self.assertEqual(entry['equals']['status'], 'complete')
                self.assertNotIn('evidence', entry)
                if key.startswith('ordered-'):
                    self.assertEqual(entry['equals']['model_artifact.sha256'], prepare.ORIGINAL_MODEL
                        if key in ('ordered-prepare-256', 'ordered-original-model-256') else prepare.RETAINED_MODEL)
            quality = external['matched-quality']['equals']
            for field in ('matched_quality_gate_pass', 'development_safety_gate_pass',
                          'historical_control_parity_pass', 'provenance.new_generation_sources_verified'):
                self.assertIs(quality[field], True)
            self.assertEqual(quality['provenance.new_model_sha256'], prepare.RETAINED_MODEL)
            self.assertEqual(len(spec['external_equalities']), 9)
            self.assertEqual({row['left'].removeprefix('ordered-') for row in spec['external_equalities']},
                expected_trials)
            prerequisite = spec['prerequisite_scientific_gate']
            self.assertEqual(prerequisite['trial'], 'repair-128-48')
            self.assertIs(prerequisite['all_passed'], True)
            self.assertEqual(Path(prerequisite['campaign']).name, 'compressed_service_v31')

    def test_changed_metadata_or_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'changed.json'
            path.write_bytes(b'{"different":true}')
            with self.assertRaises(ValueError):
                prepare.checked_json(path, prepare.DRAFT_HASHES['selection.json'])
            link = Path(folder)/'link.json'
            link.symlink_to(path)
            with self.assertRaises(ValueError):
                prepare.descriptor(link)

    def test_selected_root_cannot_change_requests_tokens_or_normalization(self):
        original = copy.deepcopy(self.draft['roots'][0])
        payload = json.loads(Path(original['records']['path']).read_bytes())
        changed = copy.deepcopy(original)
        changed['compressed_request_id'] = 'wikitext-delete-1'
        with self.assertRaises(ValueError):
            prepare.validate_root(changed, self.selection, payload)
        changed = copy.deepcopy(original)
        changed['point_trials'][0]['plan']['original_token_count'] = 128
        with self.assertRaises(ValueError):
            prepare.validate_root(changed, self.selection, payload)
        short = copy.deepcopy(payload)
        short['records'][0]['tokens'].pop()
        with self.assertRaises(ValueError):
            prepare.validate_root(original, self.selection, short)

    def test_spec_writer_never_overwrites_existing_output(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder)/'ready'
            prepare.write_specs(destination, self.specs)
            before = {p.name: p.read_bytes() for p in destination.iterdir()}
            with self.assertRaises(ValueError):
                prepare.write_specs(destination, self.specs)
            self.assertEqual(before, {p.name: p.read_bytes() for p in destination.iterdir()})


    def test_v30_original_files_remain_byte_identical(self):
        expected = {
            'scripts/prepare_independent_campaigns_v30.py': 'd2441e792789d1acea1e3d464ec5b43347bc93a2314d5f8347f5acf49666795f',
            'scripts/launch_independent_requests_v30.py': 'b3b3c130634d229c8d8a78ed273f31a80552ec88335f762d454782dd50145a07',
            'campaigns/independent_requests_v30_ready/wikitext.spec.json': 'a93e8dc014f9d2af1a5ac6947ee3dbfd63bd7a12333c617d8bf81ab77d8baa5f',
            'campaigns/independent_requests_v30_ready/c4.spec.json': 'd0d087fb978c2a55fe8d137c4b29b888095c635236f4685ea0c39ebeda5104ec',
            'tests/test_independent_campaign_specs_v30.py': 'ae8fa8e8a13da6ba5a11d50530e208e60939e038117e6be76f2207b707da4f54',
            'campaigns/independent_requests_v30_draft/specification.json': 'aadb20d91622dcb1f0bd902bdca095012f9afc11a703f626dd0d12887c9767fb',
            'campaigns/independent_requests_v30_draft/selection.json': '734f39a6ba9eced308c881c1a42469951d48ae58798097850de0eb03567f1ba2',
            'campaigns/independent_requests_v30_draft/wikitext-records.json': '3ac30626b5d8aafb67b594c97795caee755609cd2a1623a7f6fd576cc14921fa',
            'campaigns/independent_requests_v30_draft/c4-records.json': 'd3f140c3baea09990c5432529906d601d5b572bfe2caeb2670ae89445a51a54c',
        }
        for relative, digest in expected.items():
            with self.subTest(path=relative):
                self.assertEqual(hashlib.sha256((prepare.ROOT/relative).read_bytes()).hexdigest(), digest)

    def test_48_bit_native_policy_binds_exact_reviewed_derivative(self):
        policy_sha = '94442128d5610386af241da2e68d25968ed3ec85faec7aaa77e6606af652e024'
        path = prepare.ROOT/'campaigns/compressed_service_v31.spec.json'
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), policy_sha)
        self.assertEqual(prepare.COMPRESSED_POLICY_SHA256, policy_sha)
        for corpus, spec in self.specs.items():
            self.assertEqual(Path(spec['campaign']).name, 'independent_'+corpus+'_v31')
            self.assertEqual(spec['prerequisite_files']['compressed_policy']['sha256'], policy_sha)
            self.assertEqual(spec['prerequisite_files']['compressed_policy']['path'], str(path))
            for key in ('prerequisite_policy', 'prerequisite_scientific_gate'):
                self.assertEqual(Path(spec[key]['campaign']).name, 'compressed_service_v31')
                self.assertEqual(spec[key]['trial'], 'repair-128-48')
            for trial in spec['trials'][-2:]:
                self.assertEqual(trial['script'], 'run_compressed_service_v31.py')
                self.assertEqual(trial['plan']['codec_bits'], 48)
                self.assertEqual(trial['plan']['block_size'], 256)
                self.assertEqual(trial['plan']['decoder_backend'], 'ordered')

    def test_each_root_requires_new_conversion_from_its_original_lossless_state(self):
        for spec in self.specs.values():
            original, conversion, repair = spec['trials'][0], spec['trials'][-2], spec['trials'][-1]
            self.assertEqual(conversion['plan']['method'], 'convert_lossless')
            self.assertEqual(set(conversion['plan']['inputs']), {'records'})
            self.assertNotIn('inputs_from_external', conversion)
            self.assertEqual(conversion['inputs_from_trial'], {
                'lossless_completion': dict(trial=original['id'], completion=True),
                'lossless_model': dict(trial=original['id'], artifact='model'),
                'lossless_state': dict(trial=original['id'], artifact='state'),
            })
            self.assertEqual(conversion['plan']['record_ids'], original['plan']['record_ids'])
            self.assertEqual(conversion['plan']['deleted_ids'], [])
            self.assertEqual(conversion['plan']['original_token_count'], 256)
            self.assertNotIn('inputs_from_external', repair)
            self.assertEqual(repair['inputs_from_trial']['prior_state'],
                dict(trial=conversion['id'], artifact='state'))
            self.assertEqual(repair['inputs_from_trial']['compressed_preparation_completion'],
                dict(trial=conversion['id'], completion=True))
            self.assertIn(conversion['id'], [entry['trial'] for entry in repair['depends']])
            self.assertLess(spec['execution_order'].index(conversion['id']),
                spec['execution_order'].index(repair['id']))


if __name__ == '__main__':
    unittest.main()

