"""Complete dyadic-service software fixtures; these are not research data."""
from dataclasses import replace
from fractions import Fraction as Q
import unittest

from src.certified_transformer import CertifiedDecoder
from src.compact_service import CompactIdentityService, model_digest
from src.compact_state import parse, serialize
from src.dyadic_row_target import build_dyadic_row_target
from src.exact_core import sequential_oracle
from src.target_manifest import TargetRecipe
from tests.test_transformer_backend import decoder_fixture


RECORDS = (
    {'id': 'a', 'tokens': [0, 1]},
    {'id': 'b', 'tokens': [2, 1]},
    {'id': 'c', 'tokens': [0, 2]},
)


def exact(matrix):
    return tuple(tuple(Q.from_float(float(value)) for value in row) for row in matrix)


class DyadicCompactServiceTests(unittest.TestCase):
    def service(self, *, block_count=2, backend='batched'):
        decoder = CertifiedDecoder(decoder_fixture(block_count=block_count),
                                   primitive_backend='mpfr_enclosure')
        recipe = TargetRecipe(original_token_count=6, bits=3, group_count=1, ridge=Q(1, 10))
        target = build_dyadic_row_target(decoder, recipe)
        return CompactIdentityService(decoder, target, solver_backend=backend)

    def test_four_methods_and_nonempty_sequential_deletion_are_canonical(self):
        service = self.service()
        original = service.run(RECORDS)
        original_bytes = serialize(original.state)
        prior = parse(original_bytes)
        retained = RECORDS[1:]
        repaired = service.run(retained, method='repair', prior=prior, deleted_ids=['a'])
        indexed = service.run(retained, method='indexed_fresh', prior=prior, deleted_ids=['a'])
        direct = service.run(retained)
        only = service.run(retained, method='model_only_fresh')
        expected = serialize(direct.state)
        self.assertEqual(serialize(repaired.state), expected)
        self.assertEqual(serialize(indexed.state), expected)
        self.assertEqual(model_digest(only.stages), model_digest(direct.stages))
        self.assertIsNone(only.state)
        self.assertEqual(serialize(original.state), original_bytes)
        for result in (original, repaired, indexed, direct, only):
            self.assertEqual(result.diagnostics['effective_solver_backends'], ['dyadic_direct_grid'])
            self.assertEqual(result.diagnostics['changed_ancestor_pairs_avoided'], 0)
            for stage, target in zip(result.stages, service.target.stages):
                self.assertEqual(stage.grid_axis, 'dyadic_row')
                self.assertEqual(stage.scale_exponents, ())
                self.assertEqual(stage.scale_values, target.scale_values)
        sequential = service.run(RECORDS[2:], method='repair', prior=repaired.state, deleted_ids=['b'])
        combined = service.run(RECORDS[2:], method='repair', prior=prior, deleted_ids=['a', 'b'])
        fresh = service.run(RECORDS[2:])
        self.assertEqual(serialize(sequential.state), serialize(combined.state))
        self.assertEqual(serialize(sequential.state), serialize(fresh.state))
        self.assertEqual(sequential.state.record_ids, ('c',))

    def test_noop_and_empty_target_preserve_canonical_contract(self):
        service = self.service(block_count=1)
        original = service.run(RECORDS)
        noop = service.run(RECORDS, method='repair', prior=original.state)
        self.assertEqual(serialize(noop.state), serialize(original.state))
        self.assertEqual(noop.diagnostics['neural_stage_record_pairs'], 0)
        self.assertEqual(noop.diagnostics['cached_factor_reads'], len(RECORDS) * len(service.target.stages))
        empty = service.run([], method='repair', prior=noop.state, deleted_ids=['a', 'b', 'c'])
        fresh = service.run([])
        only = service.run([], method='model_only_fresh')
        self.assertEqual(serialize(empty.state), serialize(fresh.state))
        self.assertEqual(model_digest(empty.stages), model_digest(only.stages))
        self.assertEqual(empty.state.record_ids, ())
        self.assertEqual(empty.diagnostics['neural_stage_record_pairs'], 0)
        for stage in service.target.stages:
            self.assertEqual(stage.normalization, 6)

    def test_complete_model_and_current_factors_match_restarted_dense_exact_oracle(self):
        service = self.service(block_count=1)
        retained = RECORDS[1:]
        result = service.run(retained)
        prefix = {}
        for stage, packed in zip(service.target.stages, result.stages):
            # Restarted features do not use the incremental service stream.
            by_record = [service.decoder.stage_features(stage.stage_id, record['tokens'], prefix)
                         for record in retained]
            features = tuple(tuple(value for record in by_record for value in record[i])
                             for i in range(stage.width))
            covariance = tuple(tuple((stage.ridge if i == j else Q(0)) +
                sum((x*y for x, y in zip(left, right)), Q(0)) / stage.normalization
                for j, right in enumerate(features)) for i, left in enumerate(features))
            expected = []
            half = 1 << (stage.bits - 1)
            for weights, scale in zip(stage.weights, stage.scale_values):
                grid = tuple(code * Q.from_float(scale) for code in range(-half, half))
                expected.append(sequential_oracle([weights], covariance, [grid] * stage.width).codes[0])
            self.assertEqual(exact(packed.array()), tuple(expected))
            for record, source in zip(retained, by_record):
                factor = next(f for f in result.state.factors
                              if f.stage_id == stage.stage_id and f.record_id == record['id'])
                self.assertEqual(exact(factor.array()), tuple(zip(*source)))
            prefix[stage.stage_id] = tuple(expected)

    def test_requested_legacy_backend_does_not_change_dyadic_solver(self):
        reference = self.service(block_count=1, backend='reference')
        batched = CompactIdentityService(reference.decoder, reference.target, solver_backend='batched')
        expected = reference.run(RECORDS)
        got = batched.run(RECORDS)
        self.assertEqual(serialize(expected.state), serialize(got.state))
        self.assertEqual(expected.diagnostics['effective_solver_backends'], ['dyadic_direct_grid'])
        self.assertEqual(got.diagnostics['effective_solver_backends'], ['dyadic_direct_grid'])

    def test_grid_mismatch_and_retained_token_changes_are_rejected(self):
        service = self.service(block_count=1)
        state = service.run(RECORDS).state
        first = service.target.stages[0]
        changed_scales = (first.scale_values[0] * 2,) + first.scale_values[1:]
        # Deliberately preserve the claimed digest to test explicit grid checks.
        wrong = replace(service.target, stages=(replace(first, scale_values=changed_scales),)
                        + service.target.stages[1:])
        wrong_service = CompactIdentityService(service.decoder, wrong)
        with self.assertRaisesRegex(ValueError, 'grid or dimensions'):
            wrong_service.run(RECORDS, method='repair', prior=state)
        changed = [{'id': 'b', 'tokens': [1, 2]}, RECORDS[2]]
        with self.assertRaisesRegex(ValueError, 'contents changed'):
            service.run(changed, method='repair', prior=state, deleted_ids=['a'])
        with self.assertRaisesRegex(ValueError, 'membership'):
            service.run(RECORDS[1:], method='repair', prior=state)


if __name__ == '__main__':
    unittest.main()
