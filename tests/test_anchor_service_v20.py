"""Complete source-local anchor service fixtures. These are not empirical data."""
from dataclasses import replace
from fractions import Fraction as Q
import unittest
from unittest.mock import patch

import numpy as np

from src.anchor_service import AnchorService
from src.anchor_state import AnchorState, LoadLimits, parse, serialize
from src.certified_transformer import CertifiedDecoder
from src.compact_service import CompactIdentityService, model_digest
from src.compact_state import CompactState
from src.dyadic_row_target import build_dyadic_row_target
from src.finite_feature_boxes import FloatBox
from src.target_manifest import TargetRecipe
from src.token_box_certificate import TokenBoxUnresolved
from tests.test_transformer_backend import decoder_fixture

RECORDS = ({'id':'a','tokens':[0,1]}, {'id':'b','tokens':[2,1]}, {'id':'c','tokens':[0,2]})


class AnchorServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decoder = CertifiedDecoder(decoder_fixture(), primitive_backend='mpfr_enclosure')
        cls.target = build_dyadic_row_target(cls.decoder,
            TargetRecipe(original_token_count=6, bits=3, group_count=1, ridge=Q(1,10)))
        cls.service = AnchorService(cls.decoder, cls.target)
        cls.original = cls.service.run(RECORDS)

    def test_fresh_repair_indexed_and_warm_match_complete_reference(self):
        expected = CompactIdentityService(self.decoder, self.target).run(RECORDS[1:])
        fresh = self.service.run(RECORDS[1:])
        repaired = self.service.run(RECORDS[1:], method='repair', prior=self.original.state, deleted_ids=('a',))
        indexed = self.service.run(RECORDS[1:], method='indexed_fresh', prior=self.original.state, deleted_ids=('a',))
        cold = self.service.run(RECORDS[1:], method='model_only_fresh')
        warm_service = AnchorService(self.decoder, self.target, use_candidates=True)
        seed = CompactState(self.target.digest, self.original.stages, ())
        with patch('src.anchor_transformer.prepare_anchor', side_effect=AssertionError('hidden anchor preparation')):
            warm = warm_service.run(RECORDS[1:], method='model_only_fresh', initial_model=seed)
        for result in (fresh, repaired, indexed, cold, warm):
            self.assertEqual(model_digest(result.stages), model_digest(expected.stages))
            self.assertGreaterEqual(result.diagnostics['service_elapsed_ns'],
                                    sum(s['elapsed_ns'] for s in result.diagnostics['stages']))
        self.assertEqual(serialize(fresh.state), serialize(repaired.state))
        self.assertEqual(serialize(fresh.state), serialize(indexed.state))
        self.assertEqual(repaired.diagnostics['anchor_prepared_records'], 0)
        self.assertEqual(repaired.diagnostics['anchor_reused_records'], 2)
        self.assertEqual(repaired.diagnostics['model_seed_source'], 'none')
        self.assertEqual(fresh.diagnostics['anchor_preparation_stage_record_pairs'], 8)
        for stage in repaired.diagnostics['stages']:
            for key, total in stage['bound_diagnostics'].items():
                self.assertEqual(total, sum(record.get(key, 0) for record in stage['bound_record_diagnostics']))
        self.assertIsNone(cold.state)
        self.assertIsNone(warm.state)

    def test_sequential_empty_and_noop_state_are_canonical(self):
        before = serialize(self.original.state)
        noop = self.service.run(RECORDS, method='repair', prior=self.original.state)
        first = self.service.run(RECORDS[1:], method='repair', prior=noop.state, deleted_ids=('a',))
        second = self.service.run(RECORDS[2:], method='repair', prior=first.state, deleted_ids=('b',))
        direct = self.service.run(RECORDS[2:], method='repair', prior=self.original.state, deleted_ids=('a','b'))
        independent = self.service.run(RECORDS[2:])
        self.assertEqual(before, serialize(noop.state))
        self.assertEqual(serialize(second.state), serialize(direct.state))
        self.assertEqual(serialize(second.state), serialize(independent.state))
        empty = self.service.run([], method='repair', prior=second.state, deleted_ids=('c',))
        empty_fresh = self.service.run([])
        reference = CompactIdentityService(self.decoder, self.target).run([])
        self.assertEqual(serialize(empty.state), serialize(empty_fresh.state))
        self.assertEqual(model_digest(empty.stages), model_digest(reference.stages))
        self.assertEqual(empty.state.anchors, ())
        self.assertEqual(serialize(self.original.state), before)

    def test_zero_budget_replay_and_reference_backend_match(self):
        replay = AnchorService(self.decoder, self.target, max_box_stage_attempts=0)
        result = replay.run(RECORDS[1:], method='repair', prior=self.original.state, deleted_ids=('a',))
        reference = AnchorService(self.decoder, self.target, solver_backend='reference', use_bounds=False)
        fresh = reference.run(RECORDS[1:])
        self.assertEqual(serialize(result.state), serialize(fresh.state))
        self.assertEqual(result.diagnostics['box_stage_attempts'], 0)
        self.assertEqual(result.diagnostics['neural_stage_record_pairs'], 8)
        self.assertEqual(result.diagnostics['changed_prefix_pairs_avoided'], 0)

    def test_native_baseline_parity_and_model_seed_validation(self):
        compact = CompactIdentityService(self.decoder, self.target, solver_backend='native_ball')
        result = self.service.run(RECORDS, method='model_only_fresh')
        self.assertEqual(model_digest(result.stages), model_digest(compact.run(RECORDS).stages))
        self.assertEqual(result.diagnostics['anchor_prepared_records'], 0)
        self.assertEqual(result.diagnostics['context_elapsed_ns'], 0)
        with self.assertRaisesRegex(ValueError, 'use_candidates'):
            self.service.run(RECORDS, method='model_only_fresh',
                             initial_model=CompactState(self.target.digest, self.original.stages, ()))
        with self.assertRaisesRegex(ValueError, 'no factors'):
            AnchorService(self.decoder, self.target, use_candidates=True).run(RECORDS,
                method='model_only_fresh', initial_model=compact.run(RECORDS).state)

    def test_membership_tokens_and_target_bindings_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'membership'):
            self.service.run(RECORDS[1:], method='repair', prior=self.original.state)
        with self.assertRaisesRegex(ValueError, 'contents changed'):
            self.service.run(({'id':'b','tokens':[0,1]}, RECORDS[2]), method='repair',
                             prior=self.original.state, deleted_ids=('a',))
        bad = replace(self.original.state, target_sha256='0'*64, anchors=())
        with self.assertRaisesRegex(ValueError, 'target'):
            self.service.run([], method='repair', prior=bad)
        with self.assertRaisesRegex(ValueError, 'binding'):
            replace(self.original.state, decoder_sha256='0'*64)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            replace(self.original.state, anchors=self.original.state.anchors*2)

    def test_state_roundtrip_digest_corruption_and_limits(self):
        data = serialize(self.original.state)
        restored = parse(data, expected_sha256=self.original.state.digest)
        self.assertEqual(serialize(restored), data)
        repaired = self.service.run(RECORDS[1:], method='repair', prior=restored, deleted_ids=('a',))
        self.assertEqual(serialize(repaired.state), serialize(self.service.run(RECORDS[1:]).state))
        for changed in (data+b'x', data[:-1], data[:30]+bytes([data[30]^1])+data[31:]):
            with self.assertRaises(ValueError):
                parse(changed)
        for limits in (LoadLimits(max_bytes=16), LoadLimits(max_records=1),
                       LoadLimits(max_leaf_tokens=1), LoadLimits(max_leaf_nodes=1),
                       LoadLimits(max_code_elements=1), LoadLimits(max_leaf_bytes=1)):
            with self.assertRaises(ValueError):
                parse(data, limits=limits)
        with self.assertRaisesRegex(ValueError, 'trusted digest'):
            parse(data, expected_sha256='0'*64)

    def test_failed_box_work_and_replayed_pairs_are_counted(self):
        from src.anchor_transformer import bound_stage
        def expanded(*args, **kwargs):
            box = bound_stage(*args, **kwargs)
            return FloatBox(box.lower-1e-10, box.upper+1e-10)
        with patch('src.anchor_transformer.bound_stage', side_effect=expanded), patch(
                'src.anchor_service.certify_dyadic_box', side_effect=TokenBoxUnresolved('forced software fixture')):
            result = self.service.run(RECORDS[1:], method='repair', prior=self.original.state, deleted_ids=('a',))
        self.assertEqual(result.diagnostics['neural_stage_record_pairs'], 8)
        self.assertEqual(result.diagnostics['changed_prefix_pairs_avoided'], 0)
        self.assertGreater(result.diagnostics['box_stage_attempts'], 0)
        self.assertGreater(result.diagnostics['bound_elapsed_ns'], 0)
        self.assertGreater(result.diagnostics['box_certificate_elapsed_ns'], 0)
        self.assertEqual(result.diagnostics['certified_stages'], 0)

    def test_replay_rejects_contradictory_provider_box(self):
        def wrong(decoder, target, anchor, prefix, stage_id, **options):
            width = target.stages[len(prefix)].width
            lower = np.full((len(anchor.tokens), width), 100., dtype=np.float64)
            return FloatBox(lower, lower+1.)
        with patch('src.anchor_transformer.bound_stage', side_effect=wrong), patch(
                'src.anchor_service.certify_dyadic_box', side_effect=TokenBoxUnresolved('force exact check')):
            with self.assertRaisesRegex(ValueError, 'contradict'):
                self.service.run(RECORDS[1:], method='repair', prior=self.original.state, deleted_ids=('a',))

    def test_two_blocks_accept_canonical_dependency_sets(self):
        decoder = CertifiedDecoder(decoder_fixture(block_count=2), primitive_backend='mpfr_enclosure')
        target = build_dyadic_row_target(decoder,
            TargetRecipe(original_token_count=2, bits=3, group_count=1, ridge=Q(1,10)))
        service = AnchorService(decoder, target, max_box_stage_attempts=0)
        result = service.run(RECORDS[:1])
        expected = CompactIdentityService(decoder, target, solver_backend='native_ball').run(RECORDS[:1])
        self.assertEqual(len(result.stages), 8)
        self.assertEqual(model_digest(result.stages), model_digest(expected.stages))


if __name__ == '__main__':
    unittest.main()
