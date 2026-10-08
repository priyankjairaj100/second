"""Fixed-feature target software fixtures. No quality or timing evidence."""
from dataclasses import replace
from fractions import Fraction as Q
import hashlib
import unittest
from unittest.mock import patch
import numpy as np

from src.anchor_service import AnchorService
from src.anchor_state import parse as parse_sequential_state
from src.anchor_transformer import encode_anchor, prepare_context
from src.certified_transformer import CertifiedDecoder
from src.compact_service import CompactIdentityService, model_digest
from src.compact_state import CompactState, StageCodes
from src.dyadic_row_quantizer import quantize_dyadic_rows
from src.dyadic_row_target import build_dyadic_row_target
from src.fixed_anchor_service import FixedAnchorService, FixedAnchorState, LoadLimits, parse, serialize
from src.ordered_finite import FiniteWeights
from src.target_manifest import TargetRecipe
from tests.test_transformer_backend import decoder_fixture

RECORDS = ({'id':'a','tokens':[0,1]}, {'id':'b','tokens':[2,1]}, {'id':'c','tokens':[0,2]})


class FixedAnchorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decoder = CertifiedDecoder(decoder_fixture(block_count=2), primitive_backend='mpfr_enclosure')
        cls.base_target = build_dyadic_row_target(cls.decoder,
            TargetRecipe(original_token_count=6, bits=3, group_count=1, ridge=Q(1,10)))
        cls.service = FixedAnchorService(cls.decoder, cls.base_target)
        cls.original = cls.service.run(RECORDS)

    def test_distinct_target_and_independent_fixed_prefix_oracle(self):
        self.assertNotEqual(self.service.target.digest, self.base_target.digest)
        context = prepare_context(self.decoder, self.base_target)
        oracle = []
        for i, stage in enumerate(self.base_target.stages):
            prefix = {code.stage_id:tuple(tuple(Q.from_float(float(v)) for v in row) for row in code.array())
                      for code in context.anchor_codes[:i]}
            columns = [np.array(self.decoder.stage_features(stage.stage_id, record['tokens'], prefix),
                                dtype=np.float64) for record in RECORDS]
            features = np.concatenate(columns, axis=1)
            quantized = quantize_dyadic_rows(FiniteWeights(stage.weights).array(), features,
                stage.scale_values, bits=stage.bits, ridge=stage.ridge, normalization=stage.normalization,
                max_exact_rank=64, max_exact_coordinates=16, max_refinement_coordinates=64)
            oracle.append(StageCodes.from_array(stage.stage_id, quantized.codes,
                grid_axis='dyadic_row', bits=stage.bits, scale_values=stage.scale_values))
        self.assertEqual(model_digest(self.original.stages), model_digest(oracle))
        # Different target laws can coincide on a fixture. Target identity must
        # remain distinct even when this particular model happens to coincide.
        self.assertEqual(self.original.state.target_sha256, self.service.target.digest)
        self.assertEqual(self.original.state.anchor_target_sha256, self.base_target.digest)

    def test_complete_canonical_deletion_and_strong_indexed_control(self):
        fresh = self.service.run(RECORDS[1:])
        repaired = self.service.run(RECORDS[1:], method='repair', prior=self.original.state, deleted_ids=('a',))
        indexed = self.service.run(RECORDS[1:], method='indexed_fresh', prior=self.original.state, deleted_ids=('a',))
        self.assertEqual(serialize(fresh.state), serialize(repaired.state))
        self.assertEqual(serialize(fresh.state), serialize(indexed.state))
        for result in (repaired, indexed):
            self.assertEqual(result.diagnostics['neural_stage_record_pairs'], 0)
            self.assertEqual(result.diagnostics['anchor_prepared_records'], 0)
            self.assertEqual(result.diagnostics['anchor_leaf_factor_reads'], 16)
        for key in ('fixed_feature_values_read', 'context_matrix_values', 'anchor_leaf_factor_reads'):
            self.assertEqual(repaired.diagnostics[key], indexed.diagnostics[key])

    def test_model_only_fresh_reference_native_and_warm_match(self):
        with patch('src.fixed_anchor_service.prepare_anchor', side_effect=AssertionError('hidden summary preparation')):
            native = self.service.run(RECORDS[1:], method='model_only_fresh')
            reference = FixedAnchorService(self.decoder, self.base_target, solver_backend='reference').run(
                RECORDS[1:], method='model_only_fresh')
            seed = CompactState(self.service.target.digest, self.original.stages, ())
            warm = FixedAnchorService(self.decoder, self.base_target, use_candidates=True).run(
                RECORDS[1:], method='model_only_fresh', initial_model=seed)
        expected = self.service.run(RECORDS[1:])
        for result in (native, reference, warm):
            self.assertEqual(model_digest(result.stages), model_digest(expected.stages))
            self.assertIsNone(result.state)
            self.assertEqual(result.diagnostics['neural_stage_record_pairs'], 16)
            self.assertEqual(result.diagnostics['anchor_leaf_factor_reads'], 0)

    def test_noop_sequential_combined_and_empty_are_canonical(self):
        before = serialize(self.original.state)
        noop = self.service.run(RECORDS, method='repair', prior=self.original.state)
        first = self.service.run(RECORDS[1:], method='repair', prior=noop.state, deleted_ids=('a',))
        second = self.service.run(RECORDS[2:], method='repair', prior=first.state, deleted_ids=('b',))
        combined = self.service.run(RECORDS[2:], method='repair', prior=self.original.state, deleted_ids=('a','b'))
        self.assertEqual(serialize(noop.state), before)
        self.assertEqual(serialize(second.state), serialize(combined.state))
        self.assertEqual(serialize(second.state), serialize(self.service.run(RECORDS[2:]).state))
        empty = self.service.run([], method='repair', prior=second.state, deleted_ids=('c',))
        self.assertEqual(serialize(empty.state), serialize(self.service.run([]).state))
        self.assertEqual(empty.state.anchors, ())
        self.assertEqual(serialize(self.original.state), before)

    def test_prepared_route_requires_and_preserves_external_cost(self):
        anchors = self.original.state.anchors[1:]
        receipt = dict(source='software fixture preparation',
            artifact_sha256=hashlib.sha256(b''.join(encode_anchor(a) for a in anchors)).hexdigest(), elapsed_ns=123)
        with patch('src.fixed_anchor_service.prepare_anchor', side_effect=AssertionError('unexpected preparation')):
            result = self.service.run_prepared(RECORDS[1:], anchors, preparation_receipt=receipt)
        self.assertEqual(serialize(result.state), serialize(self.service.run(RECORDS[1:]).state))
        self.assertEqual(result.diagnostics['external_preparation_elapsed_ns'], 123)
        self.assertEqual(result.diagnostics['external_preparation_receipt'], receipt)
        self.assertFalse(result.diagnostics['preparation_receipt_verified_by_service'])
        self.assertEqual(result.diagnostics['execution_route'], 'prepared_leaf_construction')
        with self.assertRaisesRegex(ValueError, 'provenance'):
            self.service.run_prepared(RECORDS[1:], anchors, preparation_receipt={})
        with self.assertRaisesRegex(ValueError, 'retained records'):
            self.service.run_prepared(RECORDS[2:], anchors, preparation_receipt=receipt)

    def test_formats_and_services_reject_cross_target_state(self):
        self.assertTrue(all(not stage.dependencies for stage in self.service.target.stages))
        self.assertTrue(self.service.target.anchor_target.stages[-1].dependencies)
        for constructor in (CompactIdentityService, AnchorService):
            with self.assertRaisesRegex(ValueError, 'sequential dependency|complete dyadic-row'):
                constructor(self.decoder, self.service.target)
        blob = serialize(self.original.state)
        with self.assertRaises(ValueError):
            parse_sequential_state(blob)
        with self.assertRaises(TypeError):
            AnchorService(self.decoder, self.base_target).run(RECORDS,
                method='repair', prior=self.original.state)
        wrong = replace(self.original.state, target_sha256='0'*64)
        with self.assertRaisesRegex(ValueError, 'fixed-feature target'):
            self.service.run(RECORDS, method='repair', prior=wrong)
        seed = CompactState(self.base_target.digest, self.original.stages, ())
        with self.assertRaisesRegex(ValueError, 'fixed-feature target'):
            FixedAnchorService(self.decoder, self.base_target, use_candidates=True).run(
                RECORDS, method='model_only_fresh', initial_model=seed)
        with self.assertRaisesRegex(ValueError, 'differ'):
            replace(self.original.state, target_sha256=self.base_target.digest)

    def test_parser_limits_hashes_and_membership(self):
        data = serialize(self.original.state)
        restored = parse(data, expected_sha256=self.original.state.digest)
        self.assertEqual(serialize(restored), data)
        for bad in (data[:-1], data+b'x', data[:30]+bytes([data[30]^1])+data[31:]):
            with self.assertRaises(ValueError):
                parse(bad)
        for limits in (LoadLimits(max_bytes=16), LoadLimits(max_records=1), LoadLimits(max_leaf_nodes=1)):
            with self.assertRaises(ValueError):
                parse(data, limits=limits)
        with self.assertRaisesRegex(ValueError, 'membership'):
            self.service.run(RECORDS[1:], method='repair', prior=restored)
        with self.assertRaisesRegex(ValueError, 'contents changed'):
            self.service.run(({'id':'a','tokens':[1,0]}, *RECORDS[1:]), method='repair', prior=restored)


if __name__ == '__main__':
    unittest.main()
