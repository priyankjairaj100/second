"""Exact implementation-equivalence and provenance fixtures for ordered services."""
from dataclasses import replace
from fractions import Fraction as Q
import unittest
from unittest.mock import patch

import numpy as np

import src.ordered_fixed_service_v30 as fixed
import src.ordered_lossless_service_v30 as lossless
import src.certified_transformer as reference_decoder
import src.sequential_finite as reference_stream
from src.adaptive_calibration_v30 import AdaptiveBudget, CalibrationWorkRefused
from src.anchor_transformer import prepare_context
from src.compact_service import model_digest
from src.compact_state import StageCodes
from src.dyadic_row_target import build_dyadic_row_target
from src.fixed_anchor_service import FixedAnchorService
from src.fixed_factor_state import parse as parse_factors, serialize as encode_factors, preparer_binding
from src.fixed_lossless_state_v29 import from_factor_state, parse, serialize
from src.low_rank_certified import LowRankUnresolved
from src.ordered_finite_decoder_v30 import OrderedFiniteDecoder
from src.target_manifest import TargetRecipe
from tests.test_transformer_backend import decoder_fixture


RECORDS = ({'id': 'a', 'tokens': [0, 1]}, {'id': 'b', 'tokens': [2, 1]},
           {'id': 'c', 'tokens': [0, 2]})


class OrderedServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = decoder_fixture(block_count=2)
        cls.reference = reference_decoder.CertifiedDecoder(base, primitive_backend='mpfr_enclosure')
        cls.decoder = OrderedFiniteDecoder(base, primitive_backend='mpfr_enclosure')
        recipe = TargetRecipe(original_token_count=6, bits=4, group_count=1, ridge=Q(1, 10))
        cls.base = build_dyadic_row_target(cls.decoder, recipe)
        cls.old_base = build_dyadic_row_target(cls.reference, recipe)
        cls.old_full = FixedAnchorService(cls.reference, cls.old_base, state_backend='factors').run(RECORDS)
        cls.old_retained = FixedAnchorService(cls.reference, cls.old_base, state_backend='factors').run(RECORDS[1:])
        cls.fixed = fixed.OrderedFixedAnchorService(cls.decoder, cls.base)
        cls.lossless = lossless.OrderedLosslessService(cls.decoder, cls.base)
        cls.full = cls.fixed.run(RECORDS)
        cls.retained = cls.fixed.run(RECORDS[1:])
        cls.lossless_full = cls.lossless.run(RECORDS)
        cls.lossless_retained = from_factor_state(cls.retained.state)
        cls.count = len(cls.base.stages)

    def test_target_model_and_every_factor_bit_match_historical_reference(self):
        self.assertEqual(self.base.digest, self.old_base.digest)
        self.assertEqual(self.decoder.evaluator_id, self.reference.evaluator_id)
        self.assertEqual(self.decoder.kernel_manifest, self.reference.kernel_manifest)
        self.assertEqual(model_digest(self.full.stages), model_digest(self.old_full.stages))
        self.assertEqual(model_digest(self.retained.stages), model_digest(self.old_retained.stages))
        self.assertEqual(self.full.state.target_sha256, self.old_full.state.target_sha256)
        for new, old in zip(self.full.state.anchors, self.old_full.state.anchors):
            self.assertEqual(new.record_id, old.record_id)
            self.assertEqual(new.tokens, old.tokens)
            for a, b in zip(new.blocks, old.blocks):
                self.assertEqual(a.stage_id, b.stage_id)
                self.assertEqual(a.binary64, b.binary64)
        self.assertNotEqual(self.full.state.preparer_sha256, self.old_full.state.preparer_sha256)
        self.assertEqual(self.full.state.preparer_sha256, fixed.ordered_preparer_binding())
        self.assertNotEqual(fixed.ordered_preparer_binding(), preparer_binding())
        self.assertNotEqual(encode_factors(self.full.state), encode_factors(self.old_full.state))

    def test_all_fixed_routes_share_ordered_features_and_exact_models(self):
        for point in ('auto', 'token', 'primal'):
            service = fixed.OrderedFixedAnchorService(self.decoder, self.base, solver_backend=point)
            with patch.object(reference_stream, 'sequential_features', side_effect=AssertionError('old traversal unused')):
                fresh = service.run(RECORDS[1:])
                cold = service.run(RECORDS[1:], method='model_only_fresh')
                repaired = service.run(RECORDS[1:], method='repair', prior=self.full.state, deleted_ids=('a',))
                indexed = service.run(RECORDS[1:], method='indexed_fresh', prior=self.full.state, deleted_ids=('a',))
            for result in (fresh, cold, repaired, indexed):
                self.assertEqual(model_digest(result.stages), model_digest(self.old_retained.stages))
                self.assertEqual(result.diagnostics['decoder_implementation_manifest'], self.decoder.implementation_manifest)
                self.assertEqual(result.diagnostics['preparer_sha256'], fixed.ordered_preparer_binding())
                self.assertEqual(result.diagnostics['model_seed_source'], 'none')
            self.assertIsNone(cold.state)
            self.assertEqual(cold.diagnostics['neural_stage_record_pairs'], 2*self.count)
            self.assertEqual(repaired.diagnostics['neural_stage_record_pairs'], 0)
            self.assertEqual(repaired.diagnostics['anchor_preparation_stage_record_pairs'], 0)
            self.assertEqual(encode_factors(fresh.state), encode_factors(repaired.state))
            self.assertEqual(encode_factors(fresh.state), encode_factors(indexed.state))

    def test_lossless_routes_preserve_canonical_descriptors_and_new_preparer(self):
        prior_bytes = serialize(self.lossless_full.state)
        for method in ('repair', 'indexed_fresh'):
            with patch.object(fixed, 'ordered_sequential_features', side_effect=AssertionError('indexed sources must decode')):
                result = self.lossless.run(RECORDS[1:], method=method,
                                          prior=self.lossless_full.state, deleted_ids=('a',))
            self.assertEqual(serialize(result.state), serialize(self.lossless_retained))
            self.assertEqual(result.state.preparer_sha256, fixed.ordered_preparer_binding())
            self.assertEqual(result.diagnostics['neural_stage_record_pairs'], 0)
            self.assertEqual(result.diagnostics['decoded_deleted_descriptors'], 0)
            self.assertEqual(result.diagnostics['encoded_descriptors'], 0)
            self.assertEqual(result.diagnostics['reused_descriptors'], 2*self.count)
        cold = self.lossless.run(RECORDS[1:], method='model_only_fresh')
        self.assertIsNone(cold.state)
        self.assertEqual(model_digest(cold.stages), model_digest(self.old_retained.stages))
        self.assertEqual(serialize(self.lossless_full.state), prior_bytes)

    def test_old_preparation_is_rejected_even_when_its_values_match(self):
        old_lossless = from_factor_state(self.old_full.state)
        for records, deleted in ((RECORDS[1:], ('a',)), ((), ('a', 'b', 'c'))):
            with self.assertRaisesRegex(ValueError, 'preparer'):
                self.fixed.run(records, method='repair', prior=self.old_full.state, deleted_ids=deleted)
            with patch.object(lossless, 'decode_anchors', side_effect=AssertionError('reject before old decode')):
                with self.assertRaisesRegex(ValueError, 'preparer'):
                    self.lossless.run(records, method='repair', prior=old_lossless, deleted_ids=deleted)
        receipt = dict(source='old fixture archive', artifact_sha256='0'*64, elapsed_ns=1)
        with self.assertRaisesRegex(ValueError, 'provenance'):
            self.fixed.run_prepared(RECORDS, self.old_full.state.anchors, preparation_receipt=receipt)

    def test_prepared_route_requires_new_leaf_provenance_and_explicit_receipt(self):
        receipt = dict(source='current fixture decode', artifact_sha256='0'*64, elapsed_ns=17)
        result = self.fixed.run_prepared(RECORDS, self.full.state.anchors, preparation_receipt=receipt)
        self.assertEqual(encode_factors(result.state), encode_factors(self.full.state))
        self.assertEqual(result.diagnostics['external_preparation_elapsed_ns'], 17)
        self.assertEqual(result.diagnostics['anchor_preparation_stage_record_pairs'], 0)
        with self.assertRaises(ValueError):
            self.fixed.run(RECORDS, prepared_anchors=self.full.state.anchors)
        with self.assertRaises(TypeError):
            self.fixed.run_prepared(RECORDS, (object(),), preparation_receipt=receipt)

    def test_full_deletion_and_multiple_histories_are_canonical(self):
        first = self.lossless.repair(self.lossless_full.state, ('a',))
        sequence = self.lossless.repair(first.state, ('b',))
        together = self.lossless.repair(self.lossless_full.state, ('a', 'b'))
        fresh = self.lossless.run(RECORDS[2:])
        self.assertEqual(serialize(sequence.state), serialize(together.state))
        self.assertEqual(serialize(sequence.state), serialize(fresh.state))
        empty = self.lossless.repair(sequence.state, ('c',))
        self.assertEqual(serialize(empty.state), serialize(self.lossless.run(()).state))
        self.assertEqual(empty.state.anchors, ())
        self.assertEqual(empty.state.preparer_sha256, fixed.ordered_preparer_binding())
        unchanged = self.lossless.repair(self.lossless_full.state)
        self.assertEqual(serialize(unchanged.state), serialize(self.lossless_full.state))

    def test_state_formats_roundtrip_without_mutating_historical_code(self):
        self.assertEqual(encode_factors(parse_factors(encode_factors(self.full.state))), encode_factors(self.full.state))
        self.assertEqual(serialize(parse(serialize(self.lossless_full.state))), serialize(self.lossless_full.state))
        self.assertEqual(self.lossless_full.state.target_sha256, self.old_full.state.target_sha256)

    def test_point_admission_precedes_preparation_traversal_and_lossless_decode(self):
        budget = AdaptiveBudget(max_work_units=1)
        bounded = fixed.OrderedFixedAnchorService(self.decoder, self.base, coefficient_budget=budget)
        with patch.object(fixed, 'prepare_ordered_leaf', side_effect=AssertionError('unadmitted preparation')):
            with self.assertRaises(CalibrationWorkRefused):
                bounded.run(RECORDS)
        with patch.object(fixed, 'ordered_sequential_features', side_effect=AssertionError('unadmitted traversal')):
            with self.assertRaises(CalibrationWorkRefused):
                bounded.run(RECORDS, method='model_only_fresh')
        bounded_lossless = lossless.OrderedLosslessService(self.decoder, self.base, coefficient_budget=budget)
        with patch.object(lossless, 'decode_anchors', side_effect=AssertionError('unadmitted decode')):
            with self.assertRaises(CalibrationWorkRefused):
                bounded_lossless.repair(self.lossless_full.state, ('a',))

    def test_cumulative_point_limit_does_not_reset(self):
        rows = tuple((r['id'], tuple(r['tokens'])) for r in RECORDS)
        admission = self.fixed.admit_records(rows)
        total = admission['reserved_work_units']
        self.assertGreater(total, 0)
        bounded = fixed.OrderedFixedAnchorService(self.decoder, self.base, max_point_work_units=total-1)
        with patch.object(fixed, 'prepare_context', side_effect=AssertionError('admission precedes context')):
            with self.assertRaises(CalibrationWorkRefused):
                bounded.run(RECORDS)
        bounded_lossless = lossless.OrderedLosslessService(self.decoder, self.base, max_point_work_units=0)
        with self.assertRaises(CalibrationWorkRefused):
            bounded_lossless.run(RECORDS)

    def test_numerical_refusal_preserves_nested_work_without_output(self):
        with patch.object(fixed, 'quantize_adaptive_dyadic_rows', side_effect=LowRankUnresolved('fixture refusal')):
            with self.assertRaises(LowRankUnresolved) as caught:
                self.lossless.repair(self.lossless_full.state, ('a',))
        metrics = caught.exception.diagnostics
        self.assertTrue(metrics['aborted'])
        self.assertGreater(metrics['decoded_descriptors'], 0)
        self.assertGreater(metrics['exact_service_elapsed_ns'], 0)
        self.assertTrue(metrics['exact_service_diagnostics']['aborted'])
        self.assertGreater(metrics['exact_service_diagnostics']['point_admission']['reserved_work_units'], 0)
        failed = metrics['exact_service_diagnostics']['failed_stage_diagnostics']
        self.assertEqual(failed['stage_id'], self.base.stages[0].stage_id)
        for name in ('feature_elapsed_ns', 'weights_elapsed_ns', 'candidate_elapsed_ns',
                     'attempted_solver_elapsed_ns', 'elapsed_ns'):
            self.assertGreater(failed[name], 0)
        self.assertEqual(metrics['exact_service_diagnostics']['feature_elapsed_ns'], 0)
        self.assertIn('completed stages only', metrics['exact_service_diagnostics']['aggregate_stage_timing_scope'])
        self.assertEqual(metrics['exact_service_rejection'], 'fixture refusal')

    def test_full_deletion_preserves_decoder_provider_and_anchor_checks(self):
        for field in ('decoder_sha256', 'provider_sha256', 'anchor_sha256'):
            prior = replace(self.lossless_full.state, **{field: '0'*64})
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'provenance'):
                self.lossless.repair(prior, ('a', 'b', 'c'))

    def test_record_contents_membership_and_hidden_candidates_are_checked(self):
        changed = ({'id': 'b', 'tokens': [0, 1]}, RECORDS[2])
        with self.assertRaisesRegex(ValueError, 'contents changed'):
            self.lossless.run(changed, method='repair', prior=self.lossless_full.state, deleted_ids=('a',))
        with self.assertRaisesRegex(ValueError, 'membership'):
            self.fixed.run(RECORDS[1:], method='repair', prior=self.full.state)
        stages = tuple(StageCodes.from_array(s.stage_id, np.zeros(s.shape), grid_axis=s.grid_axis,
                                            bits=s.bits, scale_values=s.scale_values) for s in self.full.stages)
        altered = replace(self.full.state, stages=stages)
        result = self.fixed.run(RECORDS[1:], method='repair', prior=altered, deleted_ids=('a',))
        self.assertEqual(encode_factors(result.state), encode_factors(self.retained.state))
        self.assertEqual(result.diagnostics['model_seed_source'], 'none')

    def test_ordered_leaf_rejects_changed_context(self):
        context = prepare_context(self.decoder, self.base)
        with self.assertRaisesRegex(ValueError, 'context binding'):
            fixed.prepare_ordered_leaf(self.decoder, self.base, RECORDS[0],
                                       context=replace(context, provider_sha256='0'*64))

    def test_implementation_manifest_does_not_change_global_functions(self):
        old_attention = reference_decoder._attention
        old_stream = reference_stream.sequential_features
        result = self.fixed.run(RECORDS[1:], method='model_only_fresh')
        self.assertIs(reference_decoder._attention, old_attention)
        self.assertIs(reference_stream.sequential_features, old_stream)
        manifest = result.diagnostics['decoder_implementation_manifest']
        self.assertFalse(manifest['global_mutation'])
        self.assertIn('ordered_attention_v30.py', manifest['source_sha256'])
        manifest['source_sha256'].clear()
        self.assertTrue(self.decoder.implementation_manifest['source_sha256'])

    def test_configuration_validation(self):
        with self.assertRaises(TypeError):
            fixed.OrderedFixedAnchorService(self.reference, self.base)
        with self.assertRaises(TypeError):
            lossless.OrderedLosslessService(self.reference, self.base)
        for kwargs in ({'state_backend': 'anchors'}, {'use_candidates': True},
                       {'max_point_work_units': -1}, {'progress': 1}, {'solver_backend': 'reference'}):
            with self.assertRaises((TypeError, ValueError)):
                fixed.OrderedFixedAnchorService(self.decoder, self.base, **kwargs)
        three = build_dyadic_row_target(self.decoder,
            TargetRecipe(original_token_count=6, bits=3, group_count=1, ridge=Q(1, 10)))
        with self.assertRaises(ValueError):
            fixed.OrderedFixedAnchorService(self.decoder, three)


if __name__ == '__main__':
    unittest.main()
