"""Compressed service software fixtures. These are not empirical datasets."""
from dataclasses import replace
from fractions import Fraction as Q
import unittest
from unittest.mock import patch

import numpy as np

from src.certified_transformer import CertifiedDecoder
from src.compact_service import model_digest
from src.compact_state import StageCodes
from src.dyadic_box_certificate import certify_dyadic_box
from src.dyadic_row_target import build_dyadic_row_target
from src.exact_core import sequential_oracle
from src.fixed_anchor_service import FixedAnchorService
from src.fixed_compressed_service import FixedCompressedService, NeuralBudgetExceeded
from src.fixed_compressed_state import from_factor_state, parse, serialize
from src.fixed_factor_codec import encode_factor
from src.native_ball_quantizer import native_quantize_dyadic_rows
from src.target_manifest import TargetRecipe
from src.token_box_certificate import TokenBoxUnresolved
from src.transformer_backend import DeterministicDecoder
from tests.test_transformer_backend import decoder_fixture


RECORDS = ({'id': 'a', 'tokens': [0, 1]}, {'id': 'b', 'tokens': [2, 1]},
           {'id': 'c', 'tokens': [0, 2]})
CERTIFICATE = 'src.fixed_compressed_service.certify_dyadic_box'
PRECONDITIONED = 'src.fixed_compressed_service.certify_preconditioned_dyadic_box'
STREAM = 'src.fixed_compressed_service.sequential_features'


def reject(*args, **kwargs):
    raise TokenBoxUnresolved('forced software-fixture rejection')


class FixedCompressedServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decoder = CertifiedDecoder(decoder_fixture(block_count=2), primitive_backend='mpfr_enclosure')
        cls.base = build_dyadic_row_target(cls.decoder,
            TargetRecipe(original_token_count=6, bits=3, group_count=1, ridge=Q(1, 10)))
        cls.service = FixedCompressedService(cls.decoder, cls.base)
        cls.original = cls.service.run(RECORDS)
        cls.exact = FixedAnchorService(cls.decoder, cls.base, state_backend='factors').run(RECORDS[1:])
        cls.expected = from_factor_state(cls.exact.state)
        cls.count = len(cls.base.stages)

    def repair(self, **kwargs):
        return self.service.run(RECORDS[1:], method='repair', prior=self.original.state,
                                deleted_ids=('a',), **kwargs)

    def test_real_certification_accepts_without_replay_and_preserves_target(self):
        with patch(STREAM, side_effect=AssertionError('accepted boxes must not replay')):
            result = self.repair()
        self.assertEqual(result.state.target_sha256, self.exact.state.target_sha256)
        self.assertEqual(serialize(result.state), serialize(self.expected))
        self.assertEqual(result.diagnostics['certificate_accepted_stages'], self.count)
        self.assertEqual(result.diagnostics['certificate_rejected_stages'], 0)
        self.assertEqual(result.diagnostics['neural_stage_record_pairs'], 0)
        self.assertEqual(result.diagnostics['avoided_neural_stage_record_pairs'], 2*self.count)
        self.assertTrue(any(d['solver_diagnostics']['uncertain_features']
                            for d in result.diagnostics['stages']))
        self.assertEqual(result.diagnostics['model_seed_source'], 'none')

    def test_all_rejected_stages_use_shared_exact_fallback_once_per_source(self):
        before = serialize(self.original.state)
        with patch(CERTIFICATE, side_effect=reject):
            result = self.repair()
        self.assertEqual(serialize(result.state), serialize(self.expected))
        self.assertEqual(result.diagnostics['certificate_rejected_stages'], self.count)
        self.assertEqual(result.diagnostics['point_solver_stages'], self.count)
        self.assertEqual(result.diagnostics['neural_stage_record_pairs'], 2*self.count)
        self.assertEqual(result.diagnostics['replay_verified_stage_record_pairs'], 2*self.count)
        self.assertEqual(result.diagnostics['neural_stage_record_pairs_by_source'], {'b': self.count, 'c': self.count})
        self.assertEqual(result.diagnostics['avoided_neural_stage_record_pairs'], 0)
        self.assertEqual(serialize(self.original.state), before)

    def test_late_rejection_charges_the_complete_accepted_ancestor_closure(self):
        calls = 0

        def last_rejects(*args, **kwargs):
            nonlocal calls
            calls += 1
            return reject() if calls == self.count else certify_dyadic_box(*args, **kwargs)

        with patch(CERTIFICATE, side_effect=last_rejects):
            result = self.repair()
        self.assertEqual(serialize(result.state), serialize(self.expected))
        self.assertEqual(result.diagnostics['certificate_accepted_stages'], self.count-1)
        self.assertEqual(result.diagnostics['point_solver_stages'], 1)
        self.assertEqual(result.diagnostics['neural_stage_record_pairs'], 2*self.count)
        self.assertEqual(result.diagnostics['stages'][-1]['neural_stage_record_pairs'], 2*self.count)
        self.assertEqual(result.diagnostics['descriptor_decodes'], 2*self.count+2*(self.count-1))

    def test_nonconsecutive_rejection_reuses_each_live_generator(self):
        calls = 0

        def sparse_rejects(*args, **kwargs):
            nonlocal calls
            calls += 1
            return reject() if calls in (2, self.count-1) else certify_dyadic_box(*args, **kwargs)

        with patch(CERTIFICATE, side_effect=sparse_rejects):
            result = self.repair()
        self.assertEqual(serialize(result.state), serialize(self.expected))
        self.assertEqual(result.diagnostics['neural_stage_record_pairs'], 2*(self.count-1))
        self.assertEqual(result.diagnostics['avoided_neural_stage_record_pairs'], 2)
        self.assertEqual(result.diagnostics['point_solver_stages'], 2)

    def test_canonical_histories_indexed_noop_empty_and_codec_precisions(self):
        for bits in (16, 24):
            service = FixedCompressedService(self.decoder, self.base, bits=bits, block_size=3)
            original = service.run(RECORDS)
            fresh = service.run(RECORDS[1:])
            repaired = service.run(RECORDS[1:], method='repair', prior=original.state, deleted_ids=('a',))
            indexed = service.run(RECORDS[1:], method='indexed_fresh', prior=original.state, deleted_ids=('a',))
            self.assertEqual(serialize(fresh.state), serialize(repaired.state))
            self.assertEqual(serialize(fresh.state), serialize(indexed.state))
            self.assertIs(repaired.state.anchors[0], original.state.anchors[1])
            sequential = service.run(RECORDS[2:], method='repair', prior=repaired.state, deleted_ids=('b',))
            combined = service.run(RECORDS[2:], method='repair', prior=original.state, deleted_ids=('a', 'b'))
            self.assertEqual(serialize(sequential.state), serialize(combined.state))
            self.assertEqual(serialize(combined.state), serialize(service.run(RECORDS[2:]).state))
            noop = service.run(RECORDS, method='repair', prior=original.state)
            self.assertEqual(serialize(noop.state), serialize(original.state))
            empty = service.run([], method='repair', prior=original.state, deleted_ids=('a', 'b', 'c'))
            self.assertEqual(serialize(empty.state), serialize(service.run([]).state))
            self.assertEqual(empty.state.anchors, ())
            self.assertEqual(empty.diagnostics['neural_stage_record_pairs'], 0)
            self.assertEqual(serialize(parse(serialize(repaired.state), expected_sha256=repaired.state.digest)),
                             serialize(repaired.state))

    def test_budget_abort_reports_actual_prefix_work_and_preserves_prior(self):
        before = serialize(self.original.state)
        for cap in (0, 3):
            service = FixedCompressedService(self.decoder, self.base, max_neural_stage_record_pairs=cap)
            with patch(CERTIFICATE, side_effect=reject), self.assertRaises(NeuralBudgetExceeded) as caught:
                service.run(RECORDS[1:], method='repair', prior=self.original.state, deleted_ids=('a',))
            self.assertEqual(caught.exception.diagnostics['neural_stage_record_pairs'], cap)
            self.assertTrue(caught.exception.diagnostics['aborted'])
            self.assertEqual(serialize(self.original.state), before)
        service = FixedCompressedService(self.decoder, self.base, max_neural_stage_record_pairs=0)
        self.assertEqual(service.run(RECORDS[1:], method='repair', prior=self.original.state,
                                    deleted_ids=('a',)).diagnostics['neural_stage_record_pairs'], 0)
        with self.assertRaises(NeuralBudgetExceeded) as caught:
            service.run(RECORDS)
        self.assertEqual(caught.exception.diagnostics['neural_stage_record_pairs'], 0)

    def test_only_explicit_unresolved_certificate_causes_fallback(self):
        for error in (ValueError('malformed'), ArithmeticError('unexpected'), RuntimeError('runtime')):
            with patch(CERTIFICATE, side_effect=error), patch(STREAM, side_effect=AssertionError('must not replay')):
                with self.assertRaises(type(error)):
                    self.repair()

    def test_current_provenance_settings_and_membership_are_mandatory(self):
        for field in ('decoder_sha256', 'provider_sha256', 'anchor_sha256', 'preparer_sha256'):
            prior = replace(self.original.state, **{field: '0'*64})
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.service.run(RECORDS, method='repair', prior=prior)
        stale = replace(self.original.state, codec_sha256='0'*64,
            anchors=tuple(replace(a, descriptors=tuple(replace(d, codec_sha256='0'*64)
                for d in a.descriptors)) for a in self.original.state.anchors))
        with self.assertRaisesRegex(ValueError, 'codec binding'):
            self.service.run(RECORDS, method='repair', prior=stale)
        with self.assertRaisesRegex(ValueError, 'settings'):
            FixedCompressedService(self.decoder, self.base, bits=24).run(
                RECORDS, method='repair', prior=self.original.state)
        for records, deleted in ((RECORDS[1:], ()), (RECORDS[1:], ('a', 'unknown')),
                                 (RECORDS[1:], ('a', 'a'))):
            with self.assertRaises(ValueError):
                self.service.run(records, method='repair', prior=self.original.state, deleted_ids=deleted)
        changed = ({'id': 'b', 'tokens': [0, 1]}, RECORDS[2])
        with self.assertRaisesRegex(ValueError, 'contents changed'):
            self.service.run(changed, method='repair', prior=self.original.state, deleted_ids=('a',))
        with self.assertRaises(TypeError):
            self.service.run(RECORDS[1:], method='repair', prior=self.exact.state)

    def test_replay_checks_source_hashes_and_containment(self):
        anchor = self.original.state.anchors[1]
        first = anchor.descriptors[0]
        false_hash = replace(first, source_sha256='0'*64)
        outside = encode_factor(np.full(first.shape, 1000.), target_sha256=first.target_sha256,
            anchor_target_sha256=first.anchor_target_sha256, record_id=first.record_id,
            token_sha256=first.token_sha256, stage_id=first.stage_id,
            bits=first.bits, block_size=first.block_size)
        outside = replace(outside, source_sha256=first.source_sha256)
        for descriptor, message in ((false_hash, 'source hash'), (outside, 'enclosure')):
            forged = replace(anchor, descriptors=(descriptor, *anchor.descriptors[1:]))
            prior = replace(self.original.state, anchors=(self.original.state.anchors[0], forged,
                                                         self.original.state.anchors[2]))
            with patch(CERTIFICATE, side_effect=reject), self.assertRaisesRegex(ArithmeticError, message):
                self.service.run(RECORDS[1:], method='repair', prior=prior, deleted_ids=('a',))

    def test_late_replay_checks_previously_accepted_ancestor_hashes(self):
        anchor = self.original.state.anchors[1]
        forged = replace(anchor, descriptors=(replace(anchor.descriptors[0], source_sha256='0'*64),
                                               *anchor.descriptors[1:]))
        prior = replace(self.original.state, anchors=(self.original.state.anchors[0], forged,
                                                     self.original.state.anchors[2]))
        calls = 0

        def late_failure(*args, **kwargs):
            nonlocal calls
            calls += 1
            return reject() if calls == self.count else certify_dyadic_box(*args, **kwargs)

        with patch(CERTIFICATE, side_effect=late_failure), self.assertRaisesRegex(ArithmeticError, 'source hash'):
            self.service.run(RECORDS[1:], method='repair', prior=prior, deleted_ids=('a',))
        self.assertEqual(calls, self.count)

    def test_prior_model_values_are_not_hidden_candidates(self):
        stages = tuple(StageCodes.from_array(stage.stage_id, np.zeros(stage.shape),
            grid_axis=stage.grid_axis, bits=stage.bits, scale_values=stage.scale_values)
            for stage in self.original.state.stages)
        prior = replace(self.original.state, stages=stages)
        result = self.service.run(RECORDS[1:], method='repair', prior=prior, deleted_ids=('a',))
        self.assertEqual(serialize(result.state), serialize(self.expected))
        self.assertEqual(result.diagnostics['model_seed_source'], 'none')

    def test_reference_fallback_and_independent_dense_rational_oracle(self):
        reference = FixedCompressedService(self.decoder, self.base, solver_backend='reference')
        with patch(CERTIFICATE, side_effect=reject):
            result = reference.run(RECORDS[1:], method='repair', prior=self.original.state, deleted_ids=('a',))
        self.assertEqual(serialize(result.state), serialize(self.expected))
        self.assertIsNone(result.diagnostics['native_build_manifest'])
        for i, (stage, actual) in enumerate(zip(self.base.stages, result.stages)):
            values = np.concatenate([a.blocks[i].array() for a in self.exact.state.anchors], axis=0).T
            features = [[Q.from_float(float(x)) for x in row] for row in values]
            metric = [[sum((x*y for x, y in zip(left, right)), Q(0))/stage.normalization
                       +(stage.ridge if j == k else 0)
                       for k, right in enumerate(features)] for j, left in enumerate(features)]
            half = 1 << (stage.bits-1)
            for j, (row, scale) in enumerate(zip(stage.weights, stage.scale_values)):
                grid = tuple(k*Q.from_float(scale) for k in range(-half, half))
                expected = sequential_oracle([row], metric, [grid]*stage.width).codes[0]
                self.assertEqual(tuple(Q.from_float(float(x)) for x in actual.array()[j]), expected)

    def test_direct_fresh_counts_preparation_and_progress(self):
        reports = []
        service = FixedCompressedService(self.decoder, self.base, progress=reports.append)
        result = service.run(RECORDS[1:])
        self.assertEqual(len(reports), self.count)
        self.assertEqual(result.diagnostics['neural_stage_record_pairs'], 2*self.count)
        self.assertEqual(result.diagnostics['prepared_records'], 2)
        self.assertEqual(result.diagnostics['certificate_attempted_stages'], 0)
        self.assertGreater(result.diagnostics['compression_elapsed_ns'], 0)
        self.assertEqual(model_digest(result.stages), model_digest(self.exact.stages))

    def test_preconditioned_backend_accepts_and_matches_indexed_without_target_changes(self):
        service = FixedCompressedService(self.decoder, self.base, certificate_backend='preconditioned')
        with (patch(CERTIFICATE, side_effect=AssertionError('wrong selected verifier')),
              patch(STREAM, side_effect=AssertionError('accepted boxes must not replay'))):
            repaired = service.run(RECORDS[1:], method='repair', prior=self.original.state, deleted_ids=('a',))
            indexed = service.run(RECORDS[1:], method='indexed_fresh', prior=self.original.state, deleted_ids=('a',))
        self.assertEqual(serialize(repaired.state), serialize(self.expected))
        self.assertEqual(serialize(indexed.state), serialize(self.expected))
        self.assertEqual(repaired.diagnostics['certificate_backend'], 'preconditioned')
        self.assertEqual(repaired.diagnostics['certificate_accepted_stages'], self.count)
        self.assertEqual(repaired.diagnostics['neural_stage_record_pairs'], 0)
        self.assertTrue(any(d['solver_diagnostics']['verified_preconditioner_coordinates'] > 0
                            for d in repaired.diagnostics['stages']))
        fresh = service.run(RECORDS[1:])
        self.assertEqual(serialize(fresh.state), serialize(self.expected))

    def test_preconditioned_rejection_uses_selected_point_fallback_and_keeps_budget(self):
        for backend in ('native_ball', 'reference'):
            service = FixedCompressedService(self.decoder, self.base, certificate_backend='preconditioned',
                                             solver_backend=backend)
            with patch(PRECONDITIONED, side_effect=reject):
                result = service.run(RECORDS[1:], method='repair', prior=self.original.state, deleted_ids=('a',))
            self.assertEqual(serialize(result.state), serialize(self.expected))
            self.assertEqual(result.diagnostics['certificate_rejected_stages'], self.count)
            self.assertEqual(result.diagnostics['point_solver_stages'], self.count)
            self.assertEqual(result.diagnostics['neural_stage_record_pairs'], 2*self.count)
        bounded = FixedCompressedService(self.decoder, self.base, certificate_backend='preconditioned',
                                          max_neural_stage_record_pairs=0)
        with patch(PRECONDITIONED, side_effect=reject), self.assertRaises(NeuralBudgetExceeded):
            bounded.run(RECORDS[1:], method='repair', prior=self.original.state, deleted_ids=('a',))
        with (patch(PRECONDITIONED, side_effect=ValueError('bad proof input')),
              patch(STREAM, side_effect=AssertionError('must not replay'))):
            with self.assertRaisesRegex(ValueError, 'bad proof input'):
                service.run(RECORDS[1:], method='repair', prior=self.original.state, deleted_ids=('a',))

    def test_nonempty_and_empty_singletons_use_the_selected_shared_native_solver(self):
        base = decoder_fixture()
        zero = DeterministicDecoder(base.config, token_embeddings=((0, 0),)*3,
            position_embeddings=((0, 0),)*5, blocks=base._blocks, lm_head=base._lm_head)
        decoder = CertifiedDecoder(zero, primitive_backend='mpfr_enclosure')
        target = build_dyadic_row_target(decoder,
            TargetRecipe(original_token_count=6, bits=3, group_count=1, ridge=Q(1, 10)))
        exact = FixedAnchorService(decoder, target, state_backend='factors').run(RECORDS[1:])
        expected = from_factor_state(exact.state)
        for certificate_backend in ('ridge_floor', 'preconditioned'):
            service = FixedCompressedService(decoder, target, certificate_backend=certificate_backend)
            prior = service.run(RECORDS).state
            self.assertTrue(all(d.box().singleton for a in prior.anchors for d in a.descriptors))
            for retained, deleted in ((RECORDS[1:], ('a',)), ((), ('a', 'b', 'c'))):
                with (patch(CERTIFICATE, side_effect=AssertionError('singleton should use shared point solver')),
                     patch(PRECONDITIONED, side_effect=AssertionError('singleton should use shared point solver')),
                     patch(STREAM, side_effect=AssertionError('singleton needs no replay')),
                     patch('src.fixed_compressed_service.quantize_dyadic_rows',
                           side_effect=AssertionError('native backend selected')),
                     patch('src.native_ball_quantizer.native_quantize_dyadic_rows',
                           wraps=native_quantize_dyadic_rows) as native):
                    result = service.run(retained, method='repair', prior=prior, deleted_ids=deleted)
                self.assertEqual(native.call_count, len(target.stages))
                self.assertEqual(result.diagnostics['singleton_point_stages'], len(target.stages))
                self.assertEqual(result.diagnostics['certificate_attempted_stages'], 0)
                self.assertEqual(result.diagnostics['point_solver_stages'], len(target.stages))
                self.assertEqual(result.diagnostics['neural_stage_record_pairs'], 0)
                self.assertTrue(all(d['route'] == 'singleton_exact_point' for d in result.diagnostics['stages']))
                self.assertEqual(serialize(result.state), serialize(expected if retained else service.run(()).state))
        reference = FixedCompressedService(decoder, target, solver_backend='reference')
        result = reference.run(RECORDS[1:], method='repair', prior=prior, deleted_ids=('a',))
        self.assertEqual(serialize(result.state), serialize(expected))
        self.assertIsNone(result.diagnostics['native_build_manifest'])

    def test_configuration_validation(self):
        for kwargs in ({'bits': True}, {'bits': 8}, {'block_size': 0}, {'block_size': 4097},
                       {'max_neural_stage_record_pairs': True}, {'max_neural_stage_record_pairs': -1},
                       {'solver_backend': 'unknown'}, {'certificate_backend': 'unknown'}, {'progress': 1}):
            with self.assertRaises((ValueError, TypeError)):
                FixedCompressedService(self.decoder, self.base, **kwargs)
        with self.assertRaises(ValueError):
            self.service.run(RECORDS, method='model_only_fresh')
        with self.assertRaises(ValueError):
            self.service.run(RECORDS, prior=self.original.state)


if __name__ == '__main__':
    unittest.main()
