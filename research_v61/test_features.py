"""Tiny finite-decoder contracts, for the pinned Linux runtime only.

No checkpoint, empirical corpus, quality sample, or campaign is evaluated.
The independent direct evaluator checks words before rational conversion can
erase signed zero; solver outputs are deliberately irrelevant to this provider.
"""
from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from research_v59.test_anchor import context, direct_feature_words, RECORDS
from research_v61 import features
from research_v61.target import build_service_target
from src.run_store import canonical_json, digest
from tests.test_checkpoint_adapter import checkpoint_fixture
from tests.test_transformer_backend import decoder_fixture


class FeatureTests(unittest.TestCase):
    def test_every_word_matches_independent_direct_original_teacher(self):
        fixtures = [decoder_fixture(block_count=2, head_count=2)]
        fixtures.extend(checkpoint_fixture(kind)[2] for kind in ('gelu', 'gelu_new'))
        for fixture in fixtures:
            decoder, base = context(fixture)
            target = build_service_target(decoder, base)
            for source in RECORDS:
                actual = list(features.iter_source_features(decoder, target, source))
                self.assertEqual(tuple(sid for sid, words in actual), decoder.stage_ids)
                for (sid, words), stage in zip(actual, target.stages):
                    expected = direct_feature_words(decoder, sid, source['tokens']).T.copy()
                    self.assertEqual(words.shape, (len(source['tokens']), stage.width))
                    np.testing.assert_array_equal(words.view(np.uint64), expected.view(np.uint64))
                    self.assertFalse(words.flags.writeable)
                    with self.assertRaises(ValueError):
                        words.setflags(write=True)

    def test_complete_twenty_four_stage_source_extent(self):
        decoder, base = context(decoder_fixture(block_count=6))
        target = build_service_target(decoder, base)
        actual = list(features.iter_source_features(decoder, target, RECORDS[0]))
        self.assertEqual(len(actual), 24)
        self.assertEqual(tuple(sid for sid, words in actual), decoder.stage_ids)
        for (sid, words), stage in zip(actual, target.stages):
            self.assertEqual(words.shape, (2, stage.width))
            np.testing.assert_array_equal(words.view(np.uint64),
                direct_feature_words(decoder, sid, RECORDS[0]['tokens']).T.copy().view(np.uint64))

    def test_membership_and_source_order_do_not_change_any_feature_word(self):
        decoder, base = context()
        target = build_service_target(decoder, base)
        def collect(rows):
            return {(r['id'], sid): words.tobytes() for r in rows
                    for sid, words in features.iter_source_features(decoder, target, r)}
        original = collect(RECORDS)
        self.assertEqual(original, collect(list(reversed(RECORDS))))
        self.assertEqual({k: v for k, v in original.items() if k[0] == 'b'}, collect(RECORDS[1:]))

    def test_sent_calibrated_matrices_cannot_enter_original_teacher_stream(self):
        decoder, base = context(decoder_fixture(block_count=2))
        target = build_service_target(decoder, base)
        installed, closed = [], []
        original = features.ordered_sequential_features
        def tracked(d, tokens):
            stream = original(d, tokens)
            try:
                sid, value = next(stream)
                while True:
                    teacher = yield sid, value
                    installed.append(teacher)
                    sid, value = stream.send(teacher)
            except StopIteration:
                return
            finally:
                stream.close()
                closed.append(True)
        with patch.object(features, 'ordered_sequential_features', side_effect=tracked):
            stream = features.iter_source_features(decoder, target, RECORDS[0])
            actual = [next(stream)]
            while True:
                try:
                    actual.append(stream.send(np.full((1, 1), 987.0)))
                except StopIteration:
                    break
        self.assertEqual(closed, [True])
        self.assertEqual(len(installed), len(target.stages)-1)
        for words, teacher in zip(installed, target.calibration_target.payload()['teacher_stages']):
            self.assertFalse(words.flags.writeable)
            self.assertEqual(features._immutable_teacher(decoder, teacher['stage_id'],
                teacher['weights_sha256']).tobytes(), words.tobytes())
        for sid, words in actual:
            self.assertEqual(words.tobytes(), direct_feature_words(decoder, sid, RECORDS[0]['tokens']).T.copy().tobytes())

    def test_early_close_also_closes_underlying_finite_stream(self):
        decoder, base = context()
        target = build_service_target(decoder, base)
        original, closed = features.ordered_sequential_features, []
        def tracked(d, tokens):
            try:
                yield from original(d, tokens)
            finally:
                closed.append(True)
        with patch.object(features, 'ordered_sequential_features', side_effect=tracked):
            stream = features.iter_source_features(decoder, target, RECORDS[0])
            next(stream)
            stream.close()
        self.assertEqual(closed, [True])

    def test_invalid_stage_shape_nonfinite_and_incomplete_stream_close_and_refuse(self):
        decoder, base = context()
        target = build_service_target(decoder, base)
        sid, width = target.stages[0].stage_id, target.stages[0].width
        cases = [('wrong', np.zeros((2, width))), (sid, np.zeros((1, width))),
                 (sid, np.full((2, width), np.nan)), (sid, np.zeros((2, width)))]
        for first in cases:
            closed = []
            def invalid(d, tokens):
                try:
                    yield first
                finally:
                    closed.append(True)
            with patch.object(features, 'ordered_sequential_features', side_effect=invalid):
                with self.assertRaises(ValueError):
                    list(features.iter_source_features(decoder, target, RECORDS[0]))
            self.assertEqual(closed, [True])

    def test_foreign_provider_or_calibration_binding_refuses_before_open(self):
        decoder, base = context()
        target = build_service_target(decoder, base)
        for field in ('provider_sha256', 'calibration_target_sha256', 'anchor_target_sha256'):
            payload = target.payload()
            payload[field] = '0'*64
            changed = replace(target, payload_bytes=canonical_json(payload))
            with patch.object(features, 'ordered_sequential_features') as opening:
                with self.assertRaises(ValueError):
                    list(features.iter_source_features(decoder, changed, RECORDS[0]))
                opening.assert_not_called()

    def test_wrong_original_teacher_commitment_refuses_before_install(self):
        decoder, base = context()
        target = build_service_target(decoder, base)
        calibration = target.calibration_target.payload()
        calibration['teacher_stages'][0]['weights_sha256'] = '0'*64
        changed_calibration = replace(target.calibration_target, payload_bytes=canonical_json(calibration))
        payload = target.payload()
        payload['calibration_target'] = calibration
        payload['calibration_target_sha256'] = digest(canonical_json(calibration))
        changed = replace(target, calibration_target=changed_calibration, payload_bytes=canonical_json(payload))
        stream = features.iter_source_features(decoder, changed, RECORDS[0])
        next(stream)
        with self.assertRaisesRegex(ValueError, 'Teacher'):
            next(stream)


if __name__ == '__main__':
    unittest.main()
