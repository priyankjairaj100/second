"""Independent ordered service contract fixtures, without empirical workloads."""
from fractions import Fraction as Q
import unittest
from unittest.mock import patch

import src.ordered_fixed_service_v30 as fixed
import src.ordered_lossless_service_v30 as lossless
from src.adaptive_calibration_v30 import CalibrationWorkRefused
from src.certified_transformer import CertifiedDecoder
from src.compact_service import model_digest
from src.dyadic_row_target import build_dyadic_row_target
from src.fixed_anchor_service import FixedAnchorService
from src.fixed_lossless_state_v29 import from_factor_state
from src.low_rank_certified import LowRankUnresolved
from src.ordered_finite_decoder_v30 import OrderedFiniteDecoder
from src.target_manifest import TargetRecipe
from tests.test_transformer_backend import decoder_fixture


RECORDS = ({'id': 'a', 'tokens': [0, 1]}, {'id': 'b', 'tokens': [2, 1]})


class OrderedServicesReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = decoder_fixture()
        cls.decoder = OrderedFiniteDecoder(base, primitive_backend='mpfr_enclosure')
        recipe = TargetRecipe(original_token_count=4, bits=4, group_count=1, ridge=Q(1, 10))
        cls.target = build_dyadic_row_target(cls.decoder, recipe)
        cls.fixed = fixed.OrderedFixedAnchorService(cls.decoder, cls.target)
        cls.lossless = lossless.OrderedLosslessService(cls.decoder, cls.target)
        cls.full = cls.lossless.run(RECORDS)
        reference = CertifiedDecoder(base, primitive_backend='mpfr_enclosure')
        old_target = build_dyadic_row_target(reference, recipe)
        cls.old_empty = from_factor_state(
            FixedAnchorService(reference, old_target, state_backend='factors').run(()).state)

    def test_fresh_cold_and_decoded_repair_supply_identical_solver_inputs(self):
        original = fixed.quantize_adaptive_dyadic_rows
        captured = []
        def capture(weights, features, scales, **kwargs):
            captured.append((features.shape, features.tobytes(order='C'),
                             weights.shape, weights.tobytes(order='C'), tuple(scales),
                             kwargs['ridge'], kwargs['normalization'], kwargs['route']))
            return original(weights, features, scales, **kwargs)
        histories, outputs = [], []
        operations = (
            lambda: self.lossless.run(RECORDS[1:]),
            lambda: self.lossless.run(RECORDS[1:], method='model_only_fresh'),
            lambda: self.lossless.repair(self.full.state, ('a',)),
        )
        with patch.object(fixed, 'quantize_adaptive_dyadic_rows', side_effect=capture):
            for operation in operations:
                captured.clear()
                outputs.append(operation())
                histories.append(tuple(captured))
        self.assertEqual(len(histories[0]), len(self.target.stages))
        self.assertEqual(histories[0], histories[1])
        self.assertEqual(histories[0], histories[2])
        self.assertEqual(len({model_digest(result.stages) for result in outputs}), 1)

    def test_zero_token_request_still_reserves_work_before_context_or_decode(self):
        exact = fixed.OrderedFixedAnchorService(self.decoder, self.target, max_point_work_units=0)
        stored = lossless.OrderedLosslessService(self.decoder, self.target, max_point_work_units=0)
        with patch.object(fixed, 'prepare_context', side_effect=AssertionError('unadmitted context')), \
             patch.object(lossless, 'decode_anchors', side_effect=AssertionError('unadmitted decode')):
            for operation in (lambda: exact.run(()),
                              lambda: stored.repair(self.full.state, ('a', 'b'))):
                with self.assertRaises(CalibrationWorkRefused) as caught:
                    operation()
                self.assertGreater(caught.exception.admission['reserved_work_units'], 0)

    def test_later_solver_refusal_keeps_completed_and_attempted_work_distinct(self):
        original = fixed.quantize_adaptive_dyadic_rows
        calls = 0
        marker = {'known_attempted_native_work': 19}
        def refuse_second(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                error = LowRankUnresolved('independent second-stage refusal')
                error.diagnostics = marker
                raise error
            return original(*args, **kwargs)
        with patch.object(fixed, 'quantize_adaptive_dyadic_rows', side_effect=refuse_second):
            with self.assertRaises(LowRankUnresolved) as caught:
                self.lossless.repair(self.full.state, ('a',))
        outer = caught.exception.diagnostics
        inner = outer['exact_service_diagnostics']
        failed = inner['failed_stage_diagnostics']
        self.assertEqual(len(inner['stages']), 1)
        self.assertEqual(failed['stage_id'], self.target.stages[1].stage_id)
        self.assertEqual(failed['solver_diagnostics'], marker)
        self.assertGreater(failed['feature_elapsed_ns'], 0)
        self.assertGreater(failed['attempted_solver_elapsed_ns'], 0)
        self.assertEqual(inner['feature_elapsed_ns'], inner['stages'][0]['feature_elapsed_ns'])
        self.assertIn('completed stages only', inner['aggregate_stage_timing_scope'])
        self.assertGreater(outer['decoded_descriptors'], 0)
        self.assertGreaterEqual(outer['service_elapsed_ns'], inner['service_elapsed_ns'])

    def test_historical_empty_state_cannot_bypass_preparer_validation(self):
        self.assertEqual(self.old_empty.anchors, ())
        with patch.object(lossless, 'decode_anchors', side_effect=AssertionError('old state decoded')):
            with self.assertRaisesRegex(ValueError, 'preparer'):
                self.lossless.repair(self.old_empty)


if __name__ == '__main__':
    unittest.main()
