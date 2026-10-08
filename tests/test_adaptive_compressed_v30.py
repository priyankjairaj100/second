"""Bounded service and canonical-state fixtures, not empirical model experiments."""
from dataclasses import replace
from fractions import Fraction as Q
import unittest
from unittest.mock import patch

import numpy as np

import src.adaptive_compressed_service_v30 as module
from src.adaptive_calibration_v30 import AdaptiveBudget, CalibrationWorkRefused
from src.certified_transformer import CertifiedDecoder
from src.compact_state import StageCodes
from src.dyadic_row_target import build_dyadic_row_target
from src.fixed_anchor_service import FixedAnchorService
from src.fixed_compressed_state_v26 import from_factor_state, parse, serialize
from src.fixed_factor_codec_v26 import encode_factor
from src.target_manifest import TargetRecipe
from src.token_box_certificate import TokenBoxUnresolved
from src.low_rank_certified import LowRankUnresolved
from tests.test_transformer_backend import decoder_fixture


RECORDS = ({'id': 'a', 'tokens': [0, 1]}, {'id': 'b', 'tokens': [2, 1]},
           {'id': 'c', 'tokens': [0, 2]})


def reject(*args, **kwargs):
    error = TokenBoxUnresolved('forced software certificate refusal')
    error.native_diagnostics = {'software_fixture': True, 'attempted_decisions': 3}
    raise error


class AdaptiveCompressedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decoder = CertifiedDecoder(decoder_fixture(block_count=2), primitive_backend='mpfr_enclosure')
        cls.base = build_dyadic_row_target(cls.decoder,
            TargetRecipe(original_token_count=6, bits=4, group_count=1, ridge=Q(1, 10)))
        cls.exact_service = FixedAnchorService(cls.decoder, cls.base, state_backend='factors')
        cls.original = from_factor_state(cls.exact_service.run(RECORDS).state)
        cls.expected = from_factor_state(cls.exact_service.run(RECORDS[1:]).state)
        cls.count = len(cls.base.stages)

    def service(self, **kwargs):
        return module.AdaptiveCompressedService(self.decoder, self.base, **kwargs)

    def repair(self, service=None, prior=None):
        return (service or self.service()).run(RECORDS[1:], method='repair',
            prior=self.original if prior is None else prior, deleted_ids=('a',))

    def test_all_box_routes_match_canonical_state_without_replay(self):
        before = serialize(self.original)
        for backend in ('auto', 'sparse', 'primal'):
            service = self.service(certificate_backend=backend)
            for method in ('repair', 'indexed_fresh'):
                with patch.object(module, 'sequential_features', side_effect=AssertionError('no replay')):
                    result = service.run(RECORDS[1:], method=method, prior=self.original, deleted_ids=('a',))
                self.assertEqual(serialize(result.state), serialize(self.expected))
                self.assertEqual(result.diagnostics['certificate_accepted_stages'], self.count)
                self.assertEqual(result.diagnostics['neural_stage_record_pairs'], 0)
                self.assertEqual(result.diagnostics['point_work_units_reserved'], 0)
                self.assertGreater(result.diagnostics['certificate_work_units_reserved'], 0)
                self.assertEqual(result.diagnostics['model_seed_source'], 'none')
                self.assertTrue(all(row['certificate_route'] in ('sparse', 'primal')
                                    for row in result.diagnostics['stages']))
        self.assertEqual(serialize(self.original), before)

    def test_fresh_uses_shared_adaptive_point_routes_and_preserves_storage(self):
        for point in ('auto', 'token', 'primal'):
            reports = []
            result = self.service(solver_backend=point, progress=reports.append).run(RECORDS[1:])
            self.assertEqual(serialize(result.state), serialize(self.expected))
            self.assertEqual(len(reports), self.count)
            self.assertEqual(result.diagnostics['neural_stage_record_pairs'], 2*self.count)
            self.assertEqual(result.diagnostics['certificate_work_units_reserved'], 0)
            self.assertGreater(result.diagnostics['point_work_units_reserved'], 0)
            self.assertEqual(result.diagnostics['point_solver_stages'], self.count)

    def test_all_rejections_use_bounded_point_fallback_and_live_generators(self):
        before = serialize(self.original)
        for point in ('auto', 'token', 'primal'):
            with patch.object(module, 'certify_primal_dyadic_box', side_effect=reject), \
                 patch.object(module, 'quantize_adaptive_dyadic_rows', wraps=module.quantize_adaptive_dyadic_rows) as solve:
                result = self.repair(self.service(certificate_backend='primal', solver_backend=point))
            self.assertEqual(serialize(result.state), serialize(self.expected))
            self.assertEqual(solve.call_count, self.count)
            self.assertTrue(all(call.kwargs['budget'] == AdaptiveBudget() for call in solve.call_args_list))
            self.assertEqual(result.diagnostics['neural_stage_record_pairs'], 2*self.count)
            self.assertEqual(result.diagnostics['replay_verified_stage_record_pairs'], 2*self.count)
            self.assertEqual(result.diagnostics['certificate_rejected_stages'], self.count)
            self.assertGreater(result.diagnostics['point_work_units_reserved'], 0)
            self.assertGreater(result.diagnostics['certificate_work_units_reserved'], 0)
            self.assertTrue(all(row['certificate_failure_diagnostics']['native_diagnostics']['software_fixture']
                                for row in result.diagnostics['stages']))
        self.assertEqual(serialize(self.original), before)

    def test_point_budget_refuses_before_fallback_neural_work(self):
        with patch.object(module, 'certify_primal_dyadic_box', side_effect=reject), \
             patch.object(module, 'sequential_features', side_effect=AssertionError('point refusal precedes replay')):
            with self.assertRaises(CalibrationWorkRefused) as caught:
                self.repair(self.service(certificate_backend='primal', max_point_work_units=0))
        metrics = caught.exception.diagnostics
        self.assertTrue(metrics['aborted'])
        self.assertEqual(metrics['neural_stage_record_pairs'], 0)
        self.assertEqual(metrics['point_work_units_reserved'], 0)
        self.assertGreater(metrics['certificate_work_units_reserved'], 0)
        self.assertEqual(metrics['pending_stage']['route'], 'exact_retained_replay')
        self.assertTrue(metrics['pending_stage']['certificate_failure_diagnostics']['native_diagnostics']['software_fixture'])

    def test_zero_certificate_budget_skips_certification_and_uses_admitted_point_fallback(self):
        with patch.object(module, 'certify_sparse_ball_dyadic_box', side_effect=AssertionError('not admitted')), \
             patch.object(module, 'certify_primal_dyadic_box', side_effect=AssertionError('not admitted')):
            result = self.repair(self.service(max_certificate_work_units=0))
        self.assertEqual(serialize(result.state), serialize(self.expected))
        self.assertEqual(result.diagnostics['certificate_work_units_reserved'], 0)
        self.assertEqual(result.diagnostics['certificate_attempted_stages'], 0)
        self.assertEqual(result.diagnostics['certificate_admission_refused_stages'], self.count)
        self.assertEqual(result.diagnostics['neural_stage_record_pairs'], 2*self.count)

    def test_cumulative_certificate_cap_does_not_reset_at_each_stage(self):
        result = self.repair(self.service(certificate_backend='primal', max_certificate_work_units=500))
        self.assertEqual(serialize(result.state), serialize(self.expected))
        metrics = result.diagnostics
        self.assertLessEqual(metrics['certificate_work_units_reserved'], 500)
        self.assertGreater(metrics['certificate_accepted_stages'], 0)
        self.assertGreater(metrics['certificate_admission_refused_stages'], 0)
        self.assertGreater(metrics['point_work_units_reserved'], 0)
        self.assertEqual(metrics['certificate_work_units_reserved'],
                         sum(row['work_units'] for row in metrics['coefficient_reservations'] if row['kind'] == 'certificate'))

    def test_fresh_point_admission_precedes_feature_preparation(self):
        with patch.object(module.AdaptiveFixedAnchorService, 'run', side_effect=AssertionError('no feature work')):
            with self.assertRaises(CalibrationWorkRefused) as caught:
                self.service(max_point_work_units=0).run(RECORDS)
        self.assertEqual(caught.exception.diagnostics['neural_stage_record_pairs'], 0)

    def test_point_numerical_failure_keeps_spent_work_and_returns_no_state(self):
        with patch.object(module, 'certify_primal_dyadic_box', side_effect=reject), \
             patch.object(module, 'quantize_adaptive_dyadic_rows', side_effect=LowRankUnresolved('point fixture refusal')):
            with self.assertRaises(LowRankUnresolved) as caught:
                self.repair(self.service(certificate_backend='primal'))
        metrics = caught.exception.diagnostics
        self.assertTrue(metrics['aborted'])
        self.assertEqual(metrics['point_solver_attempted_stages'], 1)
        self.assertEqual(metrics['point_solver_stages'], 0)
        self.assertGreater(metrics['point_solver_elapsed_ns'], 0)
        self.assertGreater(metrics['point_work_units_reserved'], 0)
        self.assertEqual(metrics['neural_stage_record_pairs'], 2)
        self.assertEqual(metrics['pending_stage']['point_rejection'], 'point fixture refusal')

    def test_fresh_numerical_refusal_keeps_reservations_and_nested_evidence(self):
        with patch('src.adaptive_fixed_service_v30.quantize_adaptive_dyadic_rows',
                   side_effect=LowRankUnresolved('fresh point fixture refusal')):
            with self.assertRaises(LowRankUnresolved) as caught:
                self.service().run(RECORDS)
        metrics = caught.exception.diagnostics
        self.assertTrue(metrics['aborted'])
        self.assertGreater(metrics['point_work_units_reserved'], 0)
        self.assertEqual(metrics['neural_stage_record_pairs'], 3*self.count)
        self.assertEqual(metrics['point_solver_attempted_stages'], 1)
        self.assertEqual(metrics['point_solver_stages'], 0)
        self.assertGreater(metrics['point_solver_elapsed_ns'], 0)
        self.assertGreater(metrics['exact_preparation_elapsed_ns'], 0)
        self.assertTrue(metrics['exact_service_diagnostics']['aborted'])
        self.assertEqual(metrics['exact_preparation_rejection'], 'fresh point fixture refusal')

    def test_missing_fresh_failure_receipt_leaves_observed_work_unknown(self):
        with patch.object(module.AdaptiveFixedAnchorService, 'run', side_effect=LowRankUnresolved('missing fixture receipt')):
            with self.assertRaises(LowRankUnresolved) as caught:
                self.service().run(RECORDS)
        metrics = caught.exception.diagnostics
        self.assertIsNone(metrics['neural_stage_record_pairs'])
        self.assertIsNone(metrics['point_solver_stages'])
        self.assertIsNone(metrics['point_solver_attempted_stages'])
        self.assertIsNone(metrics['point_solver_elapsed_ns'])
        self.assertIsNone(metrics['exact_service_diagnostics'])
        self.assertGreater(metrics['point_work_units_reserved'], 0)

    def test_cumulative_point_limit_reaches_both_exact_service_instances(self):
        cap = 48_000_000_123
        service = self.service(max_point_work_units=cap)
        self.assertEqual(service.exact.max_point_work_units, cap)
        actual = module.AdaptiveFixedAnchorService
        with patch.object(module, 'AdaptiveFixedAnchorService', wraps=actual) as constructor:
            result = service.run(RECORDS[1:])
        self.assertEqual(constructor.call_args.kwargs['max_point_work_units'], cap)
        self.assertEqual(serialize(result.state), serialize(self.expected))

    def test_stage_admission_precedes_descriptor_decode(self):
        descriptor_type = type(self.original.anchors[0].descriptors[0])
        for settings in (dict(coefficient_budget=AdaptiveBudget(max_workspace_bytes=1)),
                         dict(max_certificate_work_units=0, max_point_work_units=0)):
            with patch.object(descriptor_type, 'box', side_effect=AssertionError('no descriptor decode')):
                with self.assertRaises(CalibrationWorkRefused) as caught:
                    self.repair(self.service(**settings))
            self.assertEqual(caught.exception.diagnostics['descriptor_decodes'], 0)
            self.assertEqual(caught.exception.diagnostics['neural_stage_record_pairs'], 0)

    def test_late_refusal_replays_and_validates_complete_ancestor_closure(self):
        actual = module.certify_primal_dyadic_box
        calls = 0
        def late(*args, **kwargs):
            nonlocal calls
            calls += 1
            return reject() if calls == self.count else actual(*args, **kwargs)
        with patch.object(module, 'certify_primal_dyadic_box', side_effect=late):
            result = self.repair(self.service(certificate_backend='primal'))
        self.assertEqual(serialize(result.state), serialize(self.expected))
        self.assertEqual(result.diagnostics['certificate_accepted_stages'], self.count-1)
        self.assertEqual(result.diagnostics['point_solver_stages'], 1)
        self.assertEqual(result.diagnostics['neural_stage_record_pairs'], 2*self.count)
        self.assertEqual(result.diagnostics['stages'][-1]['neural_stage_record_pairs'], 2*self.count)

    def test_stale_provenance_fails_even_after_full_deletion(self):
        for field in ('decoder_sha256', 'provider_sha256', 'anchor_sha256', 'preparer_sha256'):
            stale = replace(self.original, **{field: '0'*64})
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.service().run((), method='repair', prior=stale, deleted_ids=('a', 'b', 'c'))
        with self.assertRaisesRegex(ValueError, 'contents changed'):
            self.service().run(({'id': 'b', 'tokens': [0, 1]}, RECORDS[2]), method='repair',
                               prior=self.original, deleted_ids=('a',))
        with self.assertRaisesRegex(ValueError, 'membership'):
            self.service().run(RECORDS[1:], method='repair', prior=self.original)

    def test_singleton_empty_history_uses_shared_point_dispatch(self):
        service = self.service()
        first = self.repair(service)
        empty = service.run((), method='repair', prior=first.state, deleted_ids=('b', 'c'))
        fresh = service.run(())
        self.assertEqual(serialize(empty.state), serialize(fresh.state))
        self.assertEqual(empty.state.anchors, ())
        self.assertEqual(empty.diagnostics['singleton_point_stages'], self.count)
        self.assertEqual(empty.diagnostics['certificate_attempted_stages'], 0)
        self.assertEqual(empty.diagnostics['neural_stage_record_pairs'], 0)
        unchanged = service.run(RECORDS[1:], method='repair', prior=first.state)
        self.assertEqual(serialize(unchanged.state), serialize(first.state))
        self.assertEqual(serialize(parse(serialize(first.state))), serialize(first.state))

    def test_neural_budget_remains_separate_and_preserves_rejection_receipt(self):
        for cap in (0, 3):
            with patch.object(module, 'certify_primal_dyadic_box', side_effect=reject):
                with self.assertRaises(module.NeuralBudgetExceeded) as caught:
                    self.repair(self.service(certificate_backend='primal', max_neural_stage_record_pairs=cap))
            metrics = caught.exception.diagnostics
            self.assertEqual(metrics['neural_stage_record_pairs'], cap)
            self.assertGreater(metrics['point_work_units_reserved'], 0)
            self.assertTrue(metrics['pending_stage']['certificate_failure_diagnostics']['native_diagnostics']['software_fixture'])

    def test_unexpected_certificate_errors_do_not_trigger_fallback(self):
        for error in (ValueError('malformed'), ArithmeticError('unexpected'), RuntimeError('runtime')):
            with patch.object(module, 'certify_primal_dyadic_box', side_effect=error), \
                 patch.object(module, 'sequential_features', side_effect=AssertionError('must not replay')):
                with self.assertRaises(type(error)):
                    self.repair(self.service(certificate_backend='primal'))

    def test_prior_model_values_are_not_hidden_candidates(self):
        stages = tuple(StageCodes.from_array(stage.stage_id, np.zeros(stage.shape),
            grid_axis=stage.grid_axis, bits=stage.bits, scale_values=stage.scale_values)
            for stage in self.original.stages)
        result = self.repair(prior=replace(self.original, stages=stages))
        self.assertEqual(serialize(result.state), serialize(self.expected))
        self.assertEqual(result.diagnostics['model_seed_source'], 'none')

    def test_replay_checks_source_hash_and_feature_containment(self):
        anchor = self.original.anchors[1]
        first = anchor.descriptors[0]
        false_hash = replace(first, source_sha256='0'*64)
        outside = encode_factor(np.full(first.shape, 1000.), target_sha256=first.target_sha256,
            anchor_target_sha256=first.anchor_target_sha256, record_id=first.record_id,
            token_sha256=first.token_sha256, stage_id=first.stage_id, bits=first.bits, block_size=first.block_size)
        outside = replace(outside, source_sha256=first.source_sha256)
        for descriptor, message in ((false_hash, 'source hash'), (outside, 'enclosure')):
            forged = replace(anchor, descriptors=(descriptor, *anchor.descriptors[1:]))
            prior = replace(self.original, anchors=(self.original.anchors[0], forged, self.original.anchors[2]))
            with patch.object(module, 'certify_primal_dyadic_box', side_effect=reject):
                with self.assertRaisesRegex(ArithmeticError, message):
                    self.repair(self.service(certificate_backend='primal'), prior=prior)

    def test_resource_assessment_is_allocation_free_and_not_a_success_claim(self):
        with patch.object(module, '_workspace_allowance', wraps=module._workspace_allowance) as memory:
            report = module.assess_compressed_routes(768, 3072, 262144)
        self.assertEqual(memory.call_count, 1)
        self.assertIsNone(report['selected'])
        self.assertFalse(report['whole_process_memory_guaranteed'])
        self.assertFalse(report['wall_time_guaranteed'])
        self.assertTrue(all(not row['complete_path_guaranteed'] for row in report['routes'].values()))

    def test_configuration_and_method_validation(self):
        for kwargs in ({'max_certificate_work_units': -1}, {'max_point_work_units': True},
                       {'coefficient_budget': {}}, {'sparse_budget': {}}, {'bits': 8},
                       {'certificate_backend': 'ball'}, {'solver_backend': 'native_ball'},
                       {'max_neural_stage_record_pairs': -1}, {'progress': 1}):
            with self.assertRaises((TypeError, ValueError)):
                self.service(**kwargs)
        with self.assertRaises(ValueError):
            self.service().run(RECORDS, method='model_only_fresh')
        with self.assertRaises(ValueError):
            self.service().run(RECORDS, prior=self.original)


if __name__ == '__main__':
    unittest.main()
