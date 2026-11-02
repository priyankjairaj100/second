"""Tiny software fixtures for the distinct full-precision-anchor contract.

No real checkpoint, empirical corpus, quality input, or campaign is executed.
Finite-decoder and certificate fixtures are intended for the pinned Linux
runtime; source parsing alone is suitable for an unsupported editing host.
"""
from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from research_v43.dispatcher import ResourcePolicy
from research_v50.neighbors import enabled
from research_v55 import sequential
from research_v59 import anchor
from src.dyadic_row_target import build_dyadic_row_target
from src.fixed_anchor_target import build_fixed_anchor_target
from src.ordered_finite import FiniteWeights
from src.ordered_finite_decoder_v30 import OrderedFiniteDecoder
from src.run_store import canonical_json, digest
from src.target_manifest import TargetRecipe
from tests.test_checkpoint_adapter import checkpoint_fixture
from tests.test_transformer_backend import decoder_fixture


RECORDS = [dict(id='a', tokens=[0, 1]), dict(id='b', tokens=[2, 1])]


def context(base=None):
    decoder = OrderedFiniteDecoder(base or decoder_fixture(), primitive_backend='mpfr_enclosure')
    return decoder, build_dyadic_row_target(decoder, TargetRecipe(original_token_count=4, group_count=1))


def fake_solver(captured=None, code=0):
    """Return deliberate fixture codes to test isolation, not certification."""
    def solve(spec, weights, blocks, **options):
        pieces = list(blocks)
        if captured is not None:
            captured.append((spec.stage_id, [lo.copy() for lo, hi in pieces]))
        values = np.broadcast_to(np.asarray(spec.scale_values)[:, None]*code, weights.shape).copy()
        return SimpleNamespace(codes=values, route='fixture', solver_result=dict(fixture_only=True))
    return solve


def direct_feature_words(decoder, stage_id, tokens):
    # The direct ordered evaluator restarts at the original checkpoint for each
    # stage. Inspect finite words before the rational feature API erases -0.
    rows = decoder._eval(tokens, None, stage_id)
    return np.asarray([[cell.value for cell in row] for row in rows], dtype=np.float64).T


class FullPrecisionAnchorTests(unittest.TestCase):
    def test_distinct_target_inherits_recipe_grids_and_empty_dependencies(self):
        decoder, base = context()
        target = anchor.build_full_precision_anchor_target(decoder, base)
        nearest = build_fixed_anchor_target(decoder, base)
        self.assertEqual(len({target.digest, base.digest, nearest.digest}), 3)
        self.assertIs(target.recipe, base.recipe)
        self.assertEqual(target.payload()['base_target_sha256'], base.digest)
        self.assertEqual(target.payload()['original_normalization'], 4)
        self.assertEqual(target.payload()['anchor_rule'], anchor.ANCHOR_RULE)
        for actual, original, teacher in zip(target.stages, base.stages, target.payload()['teacher_stages']):
            self.assertEqual(actual.dependencies, ())
            self.assertEqual(replace(actual, dependencies=original.dependencies), original)
            self.assertEqual(teacher['weights_sha256'], anchor.dispatch._weight_digest(
                FiniteWeights(decoder.base._float_weights[original.stage_id]).array()))
        payload = target.payload()
        payload['feature_rule'] = 'changed'
        self.assertEqual(target.payload()['feature_rule'], anchor.FEATURE_RULE)
        with self.assertRaises(AttributeError):
            target.payload_bytes = b'{}'

    def test_target_rejects_nearest_foreign_or_mutated_base(self):
        decoder, base = context()
        with self.assertRaises(ValueError):
            anchor.build_full_precision_anchor_target(decoder, build_fixed_anchor_target(decoder, base))
        other, _ = context(checkpoint_fixture()[2])
        with self.assertRaises(ValueError):
            anchor.build_full_precision_anchor_target(other, base)
        changed = replace(base.stages[0], normalization=3)
        with self.assertRaises(ValueError):
            anchor.build_full_precision_anchor_target(decoder, replace(base, stages=(changed, *base.stages[1:])))
        payload = base.payload()
        payload['stages'][0]['weights_sha256'] = '0'*64
        with self.assertRaises(ValueError):
            anchor.build_full_precision_anchor_target(decoder, replace(base, payload_bytes=canonical_json(payload)))

    def test_every_feature_word_matches_direct_original_checkpoint_rule(self):
        fixtures = [decoder_fixture(block_count=2, head_count=2)]
        fixtures.extend(checkpoint_fixture(kind)[2] for kind in ('gelu', 'gelu_new'))
        for fixture in fixtures:
            with self.subTest(blocks=fixture.config.block_count, activation=fixture.config.activation):
                decoder, base = context(fixture)
                captured = []
                with patch.object(anchor.dispatch, 'solve_blocks', side_effect=fake_solver(captured)):
                    outputs, metrics = anchor.calibrate(decoder, base, RECORDS)
                self.assertEqual(len(outputs), len(base.stages))
                self.assertEqual(metrics['neural_stage_record_pairs'], len(base.stages)*len(RECORDS))
                for (sid, blocks), stage in zip(captured, base.stages):
                    self.assertEqual(sid, stage.stage_id)
                    for block, record in zip(blocks, RECORDS):
                        expected = direct_feature_words(decoder, sid, record['tokens'])
                        np.testing.assert_array_equal(block.view(np.uint64), expected.view(np.uint64))

    def test_calibrated_outputs_cannot_change_any_feature_or_teacher_parent(self):
        decoder, base = context(decoder_fixture(block_count=2, head_count=2))
        observed, models = [], []
        for code in (0, 7):
            captured = []
            with patch.object(anchor.dispatch, 'solve_blocks', side_effect=fake_solver(captured, code)):
                model, metrics = anchor.calibrate(decoder, base, RECORDS)
            observed.append(captured)
            models.append(model)
            for i, row in enumerate(metrics['stages']):
                self.assertEqual(row['teacher_parent_stage_id'], base.stages[i-1].stage_id if i else None)
                expected = (anchor.dispatch._weight_digest(FiniteWeights(base.stages[i-1].weights).array())
                    if i else None)
                self.assertEqual(row['teacher_parent_weights_sha256'], expected)
                self.assertEqual(row['output_code_sha256'], digest(model[i].packed_indices))
        self.assertNotEqual(models[0], models[1])
        for (sa, aa), (sb, bb) in zip(*observed):
            self.assertEqual(sa, sb)
            for a, b in zip(aa, bb):
                np.testing.assert_array_equal(a.view(np.uint64), b.view(np.uint64))
        parent = anchor._immutable_teacher(decoder, base.stages[0].stage_id,
            anchor.dispatch._weight_digest(FiniteWeights(base.stages[0].weights).array()))
        self.assertFalse(parent.flags.writeable)
        with self.assertRaises(ValueError):
            parent.setflags(write=True)

    def test_complete_twenty_four_stage_fixture_extents_grids_and_hashes(self):
        decoder, base = context(decoder_fixture(block_count=6))
        progress = []
        with patch.object(anchor.dispatch, 'solve_blocks', side_effect=fake_solver(code=-8)):
            model, metrics = anchor.calibrate(decoder, base, RECORDS, progress=progress.append)
        self.assertEqual(len(model), 24)
        self.assertEqual(tuple(s.stage_id for s in model), decoder.stage_ids)
        self.assertEqual(metrics['target_sha256'], anchor.build_full_precision_anchor_target(decoder, base).digest)
        self.assertEqual(progress, metrics['stages'])
        for code, stage in zip(model, base.stages):
            self.assertEqual(code.shape, (len(stage.weights), stage.width))
            self.assertEqual(code.scale_values, stage.scale_values)
            self.assertEqual(code.bits, 4)
            self.assertEqual(code.grid_axis, 'dyadic_row')
            self.assertTrue(np.all(code.indices_array() == 0))

    def test_stage_and_request_refusal_precede_all_feature_execution(self):
        decoder, base = context()
        for policy in (replace(ResourcePolicy(), max_stage_work_units=1),
                       replace(ResourcePolicy(), max_request_work_units=1)):
            with patch.object(anchor, 'ordered_sequential_features', side_effect=AssertionError('no feature work')) as spy:
                with self.assertRaises(ValueError):
                    anchor.calibrate(decoder, base, RECORDS, policy=policy)
                spy.assert_not_called()

    def test_source_local_features_survive_reordering_and_membership_changes(self):
        decoder, base = context()
        captured = []
        with patch.object(anchor.dispatch, 'solve_blocks', side_effect=fake_solver(captured)):
            original, _ = anchor.calibrate(decoder, base, RECORDS)
            reordered, _ = anchor.calibrate(decoder, base, list(reversed(RECORDS)))
            singleton, metrics = anchor.calibrate(decoder, base, RECORDS[1:])
        n = len(base.stages)
        self.assertEqual(original, reordered)
        self.assertEqual(metrics['retained_tokens'], 2)
        self.assertEqual(metrics['original_normalization'], 4)
        for i in range(n):
            np.testing.assert_array_equal(captured[i][1][1].view(np.uint64), captured[2*n+i][1][0].view(np.uint64))
        for records in ([], [RECORDS[0], RECORDS[0]]):
            with patch.object(anchor, 'ordered_sequential_features', side_effect=AssertionError('no feature work')):
                with self.assertRaises(ValueError):
                    anchor.calibrate(decoder, base, records)

    def test_solver_failure_exposes_completed_prefix_and_closes_streams(self):
        decoder, base = context()
        closed, calls = [], []
        stream = anchor.ordered_sequential_features
        def tracked(d, tokens):
            try:
                yield from stream(d, tokens)
            finally:
                closed.append(tuple(tokens))
        def fail(*args, **kwargs):
            calls.append(1)
            if len(calls) == 2:
                raise ArithmeticError('fixture refusal')
            return fake_solver()(*args, **kwargs)
        with patch.object(anchor, 'ordered_sequential_features', side_effect=tracked), \
             patch.object(anchor.dispatch, 'solve_blocks', side_effect=fail):
            with self.assertRaises(ArithmeticError) as caught:
                anchor.calibrate(decoder, base, RECORDS)
        self.assertEqual(caught.exception.diagnostics['completed_stages'], 1)
        self.assertIs(caught.exception.diagnostics, caught.exception.service_diagnostics)
        self.assertCountEqual(closed, [tuple(r['tokens']) for r in RECORDS])

    def test_wrong_stream_stage_refuses_and_closes(self):
        decoder, base = context()
        closed = []
        def wrong(d, tokens):
            try:
                yield 'foreign-stage', np.zeros((len(tokens), base.stages[0].width))
            finally:
                closed.append(True)
        with patch.object(anchor, 'ordered_sequential_features', side_effect=wrong):
            with self.assertRaises(ValueError) as caught:
                anchor.calibrate(decoder, base, RECORDS)
        self.assertEqual(caught.exception.diagnostics['completed_stages'], 0)
        self.assertEqual(closed, [True])

    def test_real_fixture_certification_first_stage_matches_sequential(self):
        decoder, base = context(checkpoint_fixture()[2])
        with enabled():
            full, metrics = anchor.calibrate(decoder, base, RECORDS)
            sequential_codes, _ = sequential.calibrate(decoder, base, RECORDS)
        self.assertEqual(full[0], sequential_codes[0])
        self.assertEqual(len(full), len(base.stages))
        for code, row in zip(full, metrics['stages']):
            self.assertEqual(row['output_code_sha256'], digest(code.packed_indices))


if __name__ == '__main__':
    unittest.main()
