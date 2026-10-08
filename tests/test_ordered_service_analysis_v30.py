"""Adversarial read-only analysis fixtures. No research workers execute."""
import ast
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import analyze_ordered_service_v30 as audit
from src.run_store import canonical_json,digest


class OrderedServiceAnalysisTests(unittest.TestCase):
    def timings(self):
        return {name:(300 if name=='prepare-256' else 250 if name=='original-model-256'
            else 100 if name.startswith('cold') else 75 if name.startswith('repair') else 74)*10**9
            for name in audit.TRIAL_IDS}

    def implementation(self):
        source = {'src/'+name:digest(name.encode()) for name in audit.PREPARER_SOURCES}
        manifest = dict(schema='ordered-equivalent-finite-decoder-v30',
            source_sha256={name:source['src/'+name] for name in audit.DECODER_SOURCES},
            numpy_version='fixture',global_mutation=False,same_resource_or_refusal_behavior_claimed=False)
        preparer = digest(canonical_json(dict(schema='ordered-fixed-factor-preparer-v30',
            source_sha256={name:source['src/'+name] for name in audit.PREPARER_SOURCES})))
        result = dict(preparer_sha256=preparer,decoder_implementation_manifest=manifest,
            decoder_implementation_sha256=digest(canonical_json(manifest)),
            diagnostics=dict(preparer_sha256=preparer,decoder_implementation_manifest=copy.deepcopy(manifest)))
        return result,dict(source_sha256=source)

    def test_audit_uses_explicit_checks(self):
        tree = ast.parse(Path(audit.__file__).read_text())
        self.assertFalse(any(isinstance(node,ast.Assert) for node in ast.walk(tree)))

    def test_repeated_costs_use_prep_increment_and_strict_integer_crossing(self):
        result = audit.summarize_timings(self.timings())
        self.assertAlmostEqual(result['geometric_mean_cold_over_repair'],4/3)
        self.assertEqual(result['preparation_incremental_overhead_seconds'],50)
        illustration = result['illustrative_repeated_same_request']
        self.assertEqual(illustration['strict_break_even_repetitions'],3)
        self.assertFalse(illustration['changing_state_lifetime_benefit_established'])
        self.assertEqual(illustration['first_three_observed_repetition_totals'][1]['replay_minus_prepared_seconds'],0)
        self.assertEqual(illustration['first_three_observed_repetition_totals'][2]['replay_minus_prepared_seconds'],25)
        self.assertEqual(result['observed_pair_count'],3)

    def test_losses_and_zero_savings_remain_visible(self):
        for cold in (74,75):
            times = self.timings()
            for i in range(1,4): times[f'cold-{i:03}'] = cold*10**9
            result = audit.summarize_timings(times)
            self.assertFalse(result['all_observed_pairs_favor_repair'])
            self.assertIsNone(result['illustrative_repeated_same_request']['strict_break_even_repetitions'])
            self.assertFalse(result['illustrative_repeated_same_request']['break_even_exists_for_positive_savings'])
        times = self.timings();times['prepare-256'] = 249*10**9
        self.assertEqual(audit.summarize_timings(times)['illustrative_repeated_same_request']['strict_break_even_repetitions'],0)

    def test_missing_pair_or_invalid_time_cannot_produce_estimator(self):
        times = self.timings();times.pop('cold-003')
        with self.assertRaises(ValueError):audit.summarize_timings(times)
        for value in (0,-1,True,1.5):
            times = self.timings();times['cold-003'] = value
            with self.assertRaises(ValueError):audit.summarize_timings(times)

    def test_initial_preparation_win_does_not_require_positive_request_savings(self):
        for cold in (74,75):
            times = self.timings()
            times['prepare-256'] = 249*10**9
            for i in range(1,4):
                times[f'cold-{i:03}'] = cold*10**9
            report = audit.summarize_timings(times)
            repeated = report['illustrative_repeated_same_request']
            self.assertEqual(repeated['strict_break_even_repetitions'],0)
            self.assertFalse(repeated['break_even_exists_for_positive_savings'])
            self.assertEqual(repeated['first_three_observed_repetition_totals'][0]
                ['replay_minus_prepared_seconds'],1 if cold == 75 else 0)
            if cold == 74:
                self.assertLess(repeated['first_three_observed_repetition_totals'][1]
                    ['replay_minus_prepared_seconds'],0)
        times['prepare-256'] = times['original-model-256']
        self.assertIsNone(audit.summarize_timings(times)['illustrative_repeated_same_request']
            ['strict_break_even_repetitions'])

    def test_preparer_and_decoder_bind_frozen_sources_and_actual_service(self):
        result,program = self.implementation()
        audit.verify_implementation(result,program)
        for mutate in (
            lambda x:x.update(preparer_sha256='0'*64),
            lambda x:x.update(decoder_implementation_sha256='0'*64),
            lambda x:x['decoder_implementation_manifest']['source_sha256'].update({'ordered_attention_v30.py':'0'*64}),
            lambda x:x['diagnostics'].update(preparer_sha256='0'*64),
            lambda x:x['decoder_implementation_manifest'].update(global_mutation=True),
        ):
            bad = copy.deepcopy(result);mutate(bad)
            with self.assertRaises(ValueError):audit.verify_implementation(bad,program)

    def test_all_registered_comparisons_include_scalar_gate(self):
        artifact = dict(file='model.bin',bytes=12,sha256='a'*64)
        state = dict(file='state.bin',bytes=14,sha256='b'*64)
        result = dict(artifacts=dict(model=artifact,state=state))
        trial = dict(id='repair-002',compare_to=[dict(trial='repair-001',artifacts=['model','state'])],
            compare_external=[dict(external='old_retained',artifacts=['model'])])
        external = {'old_retained':result}
        audit.verify_registered_comparisons(trial,result,{'repair-001':result},external)
        bad = copy.deepcopy(result);bad['artifacts']['state']['sha256'] = 'c'*64
        with self.assertRaises(ValueError):audit.verify_registered_comparisons(trial,bad,{'repair-001':result},external)
        with self.assertRaises(ValueError):audit.verify_registered_comparisons(dict(trial,compare_external=[]),result,{'repair-001':result},external)
        with self.assertRaises(ValueError):audit.verify_registered_comparisons(trial,result,{},external)

    def test_external_evidence_cannot_be_rebound_or_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);registry = {};results = {}
            for label in ('old_original','old_retained'):
                attempt = root/label
                evidence = {}
                for filename in audit.EXTERNAL_FILES:
                    path = attempt/filename;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(filename.encode())
                    evidence[filename] = dict(bytes=path.stat().st_size,sha256=audit.hashed(path))
                result = dict(schema='adaptive-complete-service-transaction-v30',complete_model=True,
                    artifacts=dict(model=dict(file='model.bin',bytes=1,sha256='a'*64)))
                results[attempt] = result
                registry[label] = dict(attempt=str(attempt),evidence=evidence,
                    completion_sha256=evidence['outputs/completion.json']['sha256'],verified_artifacts=result['artifacts'])
            program = dict(external_attempts=registry,external_equality_checks=[])
            with patch.object(audit,'verify_completed',side_effect=lambda p:results[p]):
                audit.verify_external_records(program,lambda p:None)
                bad = copy.deepcopy(program);bad['external_attempts']['old_original']['verified_artifacts']['model']['bytes'] = 2
                with self.assertRaises(ValueError):audit.verify_external_records(bad,lambda p:None)
                (root/'old_retained/plan.json').write_bytes(b'changed')
                with self.assertRaises(ValueError):audit.verify_external_records(program,lambda p:None)

    def test_feature_identity_is_recomputed_and_never_trusted_by_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            saved = dict(schema='ordered-real-feature-identity-v30',status='complete',neural_evaluation_performed=False,
                descriptor_count=48,descriptors=[dict(index=i) for i in range(48)],preparation_identities=['old','new'],
                analysis_cpu_ns=5,total_binary64_bytes=20,input_evidence=[],all_feature_words_equal=True)
            path = root/'feature-identity.json';path.write_bytes(canonical_json(saved))
            regenerated = dict(saved,analysis_cpu_ns=10)
            external = {'old_original':dict(attempt='/fixture/scalar')}
            results = {'prepare-256':dict(preparer_sha256='new')}
            with patch.object(audit,'compare_features',return_value=regenerated) as comparison:
                report = audit.verify_feature_identity(root,external,results,lambda p:None)
                self.assertEqual(report['current_revalidation_cpu_ns'],10)
                comparison.assert_called_once_with(Path('/fixture/scalar'),root/'attempts/prepare-256')
            altered = copy.deepcopy(regenerated);altered['descriptors'][0]['index'] = -1
            with patch.object(audit,'compare_features',return_value=altered):
                with self.assertRaises(ValueError):audit.verify_feature_identity(root,external,results,lambda p:None)


if __name__=='__main__':
    unittest.main()
