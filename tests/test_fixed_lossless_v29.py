"""Lossless state and service fixtures; no empirical model evaluation."""
from dataclasses import replace
from fractions import Fraction as Q
import hashlib
import json
import struct
import unittest
from unittest.mock import patch

import numpy as np

from src.certified_transformer import CertifiedDecoder
from src.compact_service import model_digest
from src.compact_state import StageCodes, _json
from src.dyadic_row_target import build_dyadic_row_target
from src.fixed_anchor_service import FixedAnchorService
from src.fixed_factor_state import FactorBlock, serialize as exact_bytes
from src.fixed_lossless_codec_v29 import LosslessFactorDescriptor, codec_binding
from src.fixed_lossless_service_v29 import FixedLosslessService
from src.fixed_lossless_state_v29 import (
    LosslessFactorState, LoadLimits, decode_anchors, from_factor_state, to_factor_state, parse, serialize,
)
from src.target_manifest import TargetRecipe
from tests.test_transformer_backend import decoder_fixture


RECORDS = ({'id': 'a', 'tokens': [0, 1]}, {'id': 'b', 'tokens': [2, 1]},
           {'id': 'c', 'tokens': [0, 2]})


def alter_header(data, edit):
    size = struct.unpack_from('<Q', data, 8)[0]
    header = json.loads(data[16:16+size])
    edit(header)
    raw = _json(header)
    return data[:8]+struct.pack('<Q', len(raw))+raw+data[16+size:]


class FixedLosslessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decoder = CertifiedDecoder(decoder_fixture(block_count=2), primitive_backend='mpfr_enclosure')
        cls.base = build_dyadic_row_target(cls.decoder,
            TargetRecipe(original_token_count=6, bits=3, group_count=1, ridge=Q(1, 10)))
        cls.exact = FixedAnchorService(cls.decoder, cls.base, state_backend='factors')
        cls.service = FixedLosslessService(cls.decoder, cls.base)
        cls.original_exact = cls.exact.run(RECORDS)
        cls.original = cls.service.run(RECORDS)
        cls.fresh = cls.service.run(RECORDS[1:])
        cls.stage_count = len(cls.base.stages)

    def test_state_roundtrip_preserves_complete_exact_factor_state_bytes(self):
        state = from_factor_state(self.original_exact.state)
        raw = serialize(state)
        restored = parse(raw, expected_sha256=hashlib.sha256(raw).hexdigest())
        self.assertEqual(raw, serialize(restored))
        self.assertEqual(raw, serialize(self.original.state))
        self.assertEqual(exact_bytes(to_factor_state(restored)), exact_bytes(self.original_exact.state))
        self.assertEqual(state.target_sha256, self.original_exact.state.target_sha256)
        self.assertEqual(state.codec_sha256, codec_binding())

    def test_fresh_repair_indexed_histories_noop_and_full_deletion_are_canonical(self):
        original_bytes = serialize(self.original.state)
        repaired = self.service.repair(self.original.state, ('a',))
        indexed = self.service.indexed_fresh(self.original.state, ('a',))
        self.assertEqual(serialize(repaired.state), serialize(self.fresh.state))
        self.assertEqual(serialize(indexed.state), serialize(self.fresh.state))
        for result in (repaired, indexed):
            self.assertIs(result.state.anchors[0], self.original.state.anchors[1])
            self.assertEqual(result.diagnostics['neural_stage_record_pairs'], 0)
            self.assertEqual(result.diagnostics['avoided_neural_stage_record_pairs'], 2*self.stage_count)
            self.assertEqual(result.diagnostics['encoded_descriptors'], 0)
            self.assertEqual(result.diagnostics['reused_descriptors'], 2*self.stage_count)
        sequential = self.service.repair(repaired.state, ('b',))
        combined = self.service.repair(self.original.state, ('a', 'b'))
        self.assertEqual(serialize(sequential.state), serialize(combined.state))
        self.assertEqual(serialize(combined.state), serialize(self.service.run(RECORDS[2:]).state))
        self.assertEqual(serialize(self.service.repair(self.original.state).state), original_bytes)
        empty = self.service.repair(self.original.state, ('a', 'b', 'c'))
        self.assertEqual(serialize(empty.state), serialize(self.service.run(()).state))
        self.assertEqual(empty.state.anchors, ())
        self.assertEqual(serialize(self.original.state), original_bytes)

    def test_repair_decodes_only_retained_payloads_and_never_reencodes_or_runs_neural_features(self):
        seen = []
        real_decode = LosslessFactorDescriptor.binary64

        def checked(descriptor):
            seen.append((descriptor.record_id, descriptor.stage_id))
            self.assertNotEqual(descriptor.record_id, 'a')
            return real_decode(descriptor)

        with (patch.object(LosslessFactorDescriptor, 'binary64', checked),
              patch('src.fixed_lossless_state_v29.encode_factor', side_effect=AssertionError('unneeded recompression')),
              patch('src.fixed_anchor_service.prepare_leaf', side_effect=AssertionError('unneeded preparation')),
              patch('src.fixed_anchor_service.sequential_features', side_effect=AssertionError('unneeded replay'))):
            result = self.service.repair(self.original.state, ('a',))
        self.assertEqual(len(seen), 2*self.stage_count)
        self.assertEqual(len(set(seen)), len(seen))
        self.assertEqual(result.diagnostics['decoded_descriptors'], len(seen))
        self.assertEqual(result.diagnostics['decoded_deleted_descriptors'], 0)
        self.assertEqual(serialize(result.state), serialize(self.fresh.state))

    def test_current_request_decode_and_lifetime_scope_are_distinct(self):
        result = self.service.repair(self.original.state, ('a',))
        diag = result.diagnostics
        receipt = diag['decoded_source_receipt']
        self.assertEqual(receipt['source'], 'current-request retained lossless decode')
        self.assertEqual(receipt['elapsed_ns'], diag['lossless_decode_elapsed_ns'])
        self.assertEqual(receipt['artifact_sha256'], hashlib.sha256(_json(diag['decoded_source_manifest'])).hexdigest())
        self.assertEqual(diag['exact_service_diagnostics']['external_preparation_receipt'], receipt)
        self.assertIn('including deleted leaves', diag['input_parser_decode_scope'])
        self.assertGreater(diag['decoded_source_bytes'], 0)
        self.assertGreaterEqual(diag['service_elapsed_ns'], diag['exact_service_elapsed_ns']+diag['lossless_decode_elapsed_ns'])

    def test_model_only_receives_no_prior_state_or_codec_work(self):
        expected = self.exact.run(RECORDS[1:], method='model_only_fresh')
        with (patch('src.fixed_lossless_service_v29.decode_anchors', side_effect=AssertionError('cold decoded a prior')),
              patch('src.fixed_lossless_service_v29.from_factor_state', side_effect=AssertionError('cold encoded state')),
              patch('src.fixed_lossless_service_v29.codec_binding', side_effect=AssertionError('cold consulted codec'))):
            result = self.service.run(RECORDS[1:], method='model_only_fresh')
        self.assertEqual(model_digest(result.stages), model_digest(expected.stages))
        self.assertIsNone(result.state)
        self.assertEqual(result.diagnostics['decoded_descriptors'], 0)
        self.assertEqual(result.diagnostics['encoded_descriptors'], 0)
        self.assertEqual(result.diagnostics['neural_stage_record_pairs'], 2*self.stage_count)
        for method in ('direct_fresh', 'model_only_fresh'):
            with self.assertRaises(ValueError):
                self.service.run(RECORDS, method=method, prior=self.original.state)

    def test_reference_native_progress_and_fresh_preparation_counts(self):
        reports = []
        reference = FixedLosslessService(self.decoder, self.base, solver_backend='reference', progress=reports.append)
        result = reference.repair(self.original.state, ('a',))
        self.assertEqual(serialize(result.state), serialize(self.fresh.state))
        self.assertEqual(len(reports), self.stage_count)
        self.assertEqual(tuple(d['stage_id'] for d in reports), tuple(s.stage_id for s in self.base.stages))
        self.assertIsNone(result.diagnostics['native_build_manifest'])
        self.assertEqual(self.original.diagnostics['neural_stage_record_pairs'], 3*self.stage_count)
        self.assertEqual(self.original.diagnostics['encoded_descriptors'], 3*self.stage_count)
        self.assertEqual(self.original.diagnostics['reused_descriptors'], 0)

    def test_prior_model_codes_are_never_candidates(self):
        stages = tuple(StageCodes.from_array(s.stage_id, np.zeros(s.shape),
            grid_axis=s.grid_axis, bits=s.bits, scale_values=s.scale_values) for s in self.original.state.stages)
        prior = replace(self.original.state, stages=stages)
        result = self.service.repair(prior, ('a',))
        self.assertEqual(serialize(result.state), serialize(self.fresh.state))
        self.assertEqual(result.diagnostics['model_seed_source'], 'none')

    def test_provenance_model_and_membership_fail_closed(self):
        for field in ('decoder_sha256', 'provider_sha256', 'anchor_sha256', 'preparer_sha256'):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.service.repair(replace(self.original.state, **{field: '0'*64}), ('a',))
        with self.assertRaises(ValueError):
            self.service.repair(self.original.state, ('unknown',))
        with self.assertRaises(ValueError):
            self.service.repair(self.original.state, ('a', 'a'))
        with self.assertRaises(ValueError):
            self.service.run(RECORDS[1:], method='repair', prior=self.original.state)
        changed = ({'id': 'b', 'tokens': [0, 1]}, RECORDS[2])
        with self.assertRaisesRegex(ValueError, 'contents changed'):
            self.service.run(changed, method='repair', prior=self.original.state, deleted_ids=('a',))
        with self.assertRaises(TypeError):
            self.service.repair(self.original_exact.state, ('a',))

    def test_full_deletion_checks_current_provenance_without_surviving_leaves(self):
        for field in ('decoder_sha256', 'provider_sha256', 'anchor_sha256'):
            prior = replace(self.original.state, **{field: '0'*64})
            for method in ('repair', 'indexed_fresh'):
                with self.subTest(field=field, method=method), self.assertRaisesRegex(ValueError, 'provenance'):
                    self.service.run((), method=method, prior=prior, deleted_ids=('a', 'b', 'c'))

    def test_parser_limits_corruption_and_untrusted_digest(self):
        raw = serialize(self.original.state)
        for bad in (raw+b'x', raw[:-1], raw[:30]+bytes([raw[30]^1])+raw[31:]):
            with self.assertRaises(ValueError):
                parse(bad)
        for limits in (LoadLimits(max_bytes=16), LoadLimits(max_records=1), LoadLimits(max_leaf_tokens=1),
                       LoadLimits(max_leaf_values=1), LoadLimits(max_leaf_bytes=1), LoadLimits(max_code_elements=1)):
            with self.assertRaises(ValueError):
                parse(raw, limits=limits)
        with self.assertRaises(ValueError):
            parse(raw, expected_sha256='0'*64)
        with self.assertRaises(ValueError):
            parse(exact_bytes(self.original_exact.state))

    def test_parser_preflights_dimensions_before_decoding_source_payloads(self):
        raw = serialize(self.original.state)
        bad = alter_header(raw, lambda h: h['leaves'][0]['descriptors'][-1].update(shape=[2, 100000000]))
        with patch('src.fixed_lossless_state_v29.decode_descriptor', side_effect=AssertionError('decoded before preflight')):
            with self.assertRaisesRegex(ValueError, 'dimensions'):
                parse(bad)

    def test_state_structure_binds_source_tokens_stage_order_and_codec(self):
        anchor = self.original.state.anchors[0]
        for change in (dict(tokens=(1, 0)), dict(descriptors=anchor.descriptors[::-1])):
            with self.assertRaises(ValueError):
                replace(self.original.state, anchors=(replace(anchor, **change),))
        with self.assertRaises(ValueError):
            replace(self.original.state, anchors=(anchor, anchor))
        with self.assertRaises(ValueError):
            replace(self.original.state, codec_sha256='0'*64)
        with self.assertRaises(ValueError):
            replace(self.original.state, anchors=(replace(anchor, descriptors=anchor.descriptors[:-1]),))
        with self.assertRaises(ValueError):
            decode_anchors(self.original.state, ('unknown',))
        with self.assertRaises(ValueError):
            decode_anchors(self.original.state, ('a', 'a'))

    def test_exact_conversion_preserves_signed_zero_and_immutable_raw_bytes(self):
        anchor = self.original_exact.state.anchors[0]
        block = anchor.blocks[0]
        values = np.zeros((block.token_count, block.width), dtype=np.float64)
        values[0, 0] = -0.
        altered = replace(anchor, blocks=(FactorBlock.from_array(block.stage_id, values), *anchor.blocks[1:]))
        exact = replace(self.original_exact.state, anchors=(altered,))
        converted = from_factor_state(exact)
        self.assertEqual(exact_bytes(to_factor_state(converted)), exact_bytes(exact))
        array = converted.anchors[0].descriptors[0].array()
        self.assertTrue(np.signbit(array[0, 0]))
        with self.assertRaises(ValueError):
            array.setflags(write=True)

    def test_configuration_validation(self):
        with self.assertRaises(ValueError):
            FixedLosslessService(self.decoder, self.base, solver_backend='unknown')
        with self.assertRaises(TypeError):
            FixedLosslessService(self.decoder, self.base, progress=False)
        with self.assertRaises(ValueError):
            self.service.run(RECORDS, method='unknown')


if __name__ == '__main__':
    unittest.main()
