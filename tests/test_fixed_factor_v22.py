"""Minimal factor state fixtures. No model benchmark or empirical timing."""
from dataclasses import replace
from fractions import Fraction as Q
import hashlib
import unittest
from unittest.mock import patch
import numpy as np

from src.anchor_transformer import prepare_anchor, prepare_context
from src.certified_transformer import CertifiedDecoder
from src.compact_service import model_digest
from src.dyadic_row_target import build_dyadic_row_target
from src.fixed_anchor_service import FixedAnchorService, FixedAnchorState, LoadLimits, parse, serialize
from src.fixed_factor_state import (FixedFactorState, FactorBlock, prepare_leaf, from_anchor,
                                    preparer_binding, parse as parse_factors)
from src.target_manifest import TargetRecipe
from tests.test_transformer_backend import decoder_fixture

RECORDS = ({'id':'a','tokens':[0,1]}, {'id':'b','tokens':[2,1]}, {'id':'c','tokens':[0,2]})


class FixedFactorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decoder = CertifiedDecoder(decoder_fixture(block_count=2), primitive_backend='mpfr_enclosure')
        cls.base = build_dyadic_row_target(cls.decoder,
            TargetRecipe(original_token_count=6, bits=3, group_count=1, ridge=Q(1,10)))
        cls.full_service = FixedAnchorService(cls.decoder, cls.base)
        cls.service = FixedAnchorService(cls.decoder, cls.base, state_backend='factors')
        cls.full = cls.full_service.run(RECORDS)
        cls.original = cls.service.run(RECORDS)

    def test_fresh_preparation_matches_all_archived_factor_bytes(self):
        self.assertEqual(self.full_service.target.digest, self.service.target.digest)
        self.assertEqual(model_digest(self.full.stages), model_digest(self.original.stages))
        for full, light in zip(self.full.state.anchors, self.original.state.anchors):
            converted = from_anchor(full)
            self.assertEqual(converted, light)
            for (_, _, array), block in zip(full.factors, light.blocks):
                self.assertEqual(array.astype('<f8', copy=False).tobytes(), block.binary64)
        self.assertEqual(self.original.diagnostics['stored_anchor_nodes'], 0)
        self.assertLess(len(serialize(self.original.state)), len(serialize(self.full.state)))

    def test_canonical_fresh_repair_indexed_sequential_noop_empty(self):
        before = serialize(self.original.state)
        fresh = self.service.run(RECORDS[1:])
        repair = self.service.run(RECORDS[1:], method='repair', prior=self.original.state, deleted_ids=('a',))
        indexed = self.service.run(RECORDS[1:], method='indexed_fresh', prior=self.original.state, deleted_ids=('a',))
        for result in (repair, indexed):
            self.assertEqual(serialize(result.state), serialize(fresh.state))
            self.assertEqual(result.state.record_ids, ('b','c'))
            self.assertEqual(result.diagnostics['neural_stage_record_pairs'], 0)
            self.assertEqual(result.diagnostics['anchor_prepared_records'], 0)
        sequential = self.service.run(RECORDS[2:], method='repair', prior=repair.state, deleted_ids=('b',))
        combined = self.service.run(RECORDS[2:], method='repair', prior=self.original.state, deleted_ids=('a','b'))
        self.assertEqual(serialize(sequential.state), serialize(combined.state))
        self.assertEqual(serialize(combined.state), serialize(self.service.run(RECORDS[2:]).state))
        noop = self.service.run(RECORDS, method='repair', prior=self.original.state)
        self.assertEqual(serialize(noop.state), before)
        empty = self.service.run([], method='repair', prior=sequential.state, deleted_ids=('c',))
        self.assertEqual(serialize(empty.state), serialize(self.service.run([]).state))
        self.assertEqual(empty.state.anchors, ())
        self.assertEqual(serialize(self.original.state), before)

    def test_shared_native_reference_model_only_paths(self):
        with patch('src.fixed_anchor_service.prepare_anchor', side_effect=AssertionError('unused scalar tape')):
            fresh = self.service.run(RECORDS[1:])
            model_only = self.service.run(RECORDS[1:], method='model_only_fresh')
            reference = FixedAnchorService(self.decoder, self.base, state_backend='factors', solver_backend='reference').run(RECORDS[1:])
        self.assertEqual(serialize(reference.state), serialize(fresh.state))
        self.assertEqual(model_digest(model_only.stages), model_digest(fresh.stages))
        self.assertIsNone(model_only.state)
        self.assertEqual(model_only.diagnostics['anchor_leaf_factor_reads'], 0)

    def test_prepared_conversion_keeps_external_cost_and_exact_output(self):
        receipt = dict(source='fixture archive', artifact_sha256='1'*64, elapsed_ns=456)
        converted = self.service.run_prepared(RECORDS, self.full.state.anchors, preparation_receipt=receipt)
        reused = self.service.run_prepared(RECORDS, self.original.state.anchors, preparation_receipt=receipt)
        self.assertEqual(serialize(converted.state), serialize(self.original.state))
        self.assertEqual(serialize(reused.state), serialize(self.original.state))
        self.assertEqual(converted.diagnostics['anchor_converted_records'], 3)
        self.assertEqual(reused.diagnostics['anchor_converted_records'], 0)
        self.assertEqual(converted.diagnostics['external_preparation_elapsed_ns'], 456)
        self.assertEqual(converted.diagnostics['anchor_prepared_records'], 0)

    def test_parser_limits_corruption_and_foreign_state(self):
        raw = serialize(self.original.state)
        restored = parse(raw, expected_sha256=self.original.state.digest)
        self.assertIs(type(restored), FixedFactorState)
        self.assertEqual(serialize(restored), raw)
        for bad in (raw+b'x', raw[:-1], raw[:30]+bytes([raw[30]^1])+raw[31:]):
            with self.assertRaises(ValueError):
                parse(bad)
        for limits in (LoadLimits(max_bytes=16), LoadLimits(max_records=1),
                       LoadLimits(max_leaf_tokens=1), LoadLimits(max_leaf_values=1),
                       LoadLimits(max_leaf_bytes=1), LoadLimits(max_code_elements=1)):
            with self.assertRaises(ValueError):
                parse(raw, limits=limits)
        with self.assertRaises(ValueError):
            parse_factors(serialize(self.full.state))
        with self.assertRaises(TypeError):
            self.service.run(RECORDS, method='repair', prior=self.full.state)
        with self.assertRaises(TypeError):
            self.full_service.run(RECORDS, method='repair', prior=self.original.state)

    def test_preparer_binding_and_complete_factor_membership(self):
        leaf = self.original.state.anchors[0]
        with self.assertRaisesRegex(ValueError, 'every ordered model stage'):
            replace(self.original.state, anchors=(replace(leaf, blocks=leaf.blocks[:-1]),))
        stale = replace(self.original.state, preparer_sha256='0'*64,
            anchors=tuple(replace(a, preparer_sha256='0'*64) for a in self.original.state.anchors))
        with self.assertRaisesRegex(ValueError, 'preparer'):
            self.service.run(RECORDS, method='repair', prior=stale)
        with self.assertRaisesRegex(ValueError, 'provenance'):
            replace(self.original.state, anchors=(replace(leaf, preparer_sha256='0'*64),))
        self.assertEqual(self.original.state.preparer_sha256, preparer_binding())

    def test_signed_zero_bytes_and_immutable_factors(self):
        array = np.array([[0., -0.], [1., -1.]], dtype=np.float64)
        block = FactorBlock.from_array('test', array)
        self.assertEqual(block.binary64, array.astype('<f8').tobytes())
        self.assertTrue(np.signbit(block.array()[0,1]))
        with self.assertRaises(ValueError):
            block.array().setflags(write=True)
        with self.assertRaises(ValueError):
            FactorBlock('test', 2, 2, np.full((2,2), np.nan).astype('<f8').tobytes())


if __name__ == '__main__':
    unittest.main()
