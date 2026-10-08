"""Independent admission and failure-evidence fixtures. No empirical datasets."""
import unittest
from unittest.mock import patch

import src.adaptive_compressed_service_v30 as compressed
import src.adaptive_fixed_service_v30 as fixed
import src.fixed_lossless_service_v29 as lossless_parent
from src.adaptive_calibration_v30 import AdaptiveBudget, CalibrationWorkRefused
from src.adaptive_lossless_service_v30 import AdaptiveLosslessService
from src.fixed_lossless_state_v29 import from_factor_state
from src.low_rank_certified import LowRankUnresolved
from src.token_box_certificate import TokenBoxUnresolved
import tests.test_adaptive_compressed_v30 as reference_fixture


class AdaptiveServiceReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reference_fixture.AdaptiveCompressedTests.setUpClass()
        source = reference_fixture.AdaptiveCompressedTests
        cls.decoder, cls.base = source.decoder, source.base
        cls.original = source.original
        cls.records = reference_fixture.RECORDS
        cls.lossless = from_factor_state(source.exact_service.run(cls.records).state)

    def test_fixed_fresh_admission_precedes_retained_feature_preparation(self):
        service = fixed.AdaptiveFixedAnchorService(self.decoder, self.base,
            coefficient_budget=AdaptiveBudget(max_work_units=1))
        with patch.object(fixed, 'prepare_leaf', side_effect=AssertionError('unadmitted neural work')) as prepare:
            with self.assertRaises(CalibrationWorkRefused):
                service.run(self.records)
        prepare.assert_not_called()

    def test_fixed_model_only_admission_precedes_neural_traversal(self):
        service = fixed.AdaptiveFixedAnchorService(self.decoder, self.base,
            coefficient_budget=AdaptiveBudget(max_work_units=1))
        with patch.object(fixed, 'sequential_features', side_effect=AssertionError('unadmitted neural work')) as replay:
            with self.assertRaises(CalibrationWorkRefused):
                service.run(self.records, method='model_only_fresh')
        replay.assert_not_called()

    def test_lossless_admission_precedes_decoding(self):
        service = AdaptiveLosslessService(self.decoder, self.base,
            coefficient_budget=AdaptiveBudget(max_work_units=1))
        with patch.object(lossless_parent, 'decode_anchors', side_effect=AssertionError('unadmitted decode')) as decode:
            with self.assertRaises(CalibrationWorkRefused):
                service.repair(self.lossless, ('a',))
        decode.assert_not_called()

    def test_fixed_cumulative_cap_does_not_reset_between_stages(self):
        probe = fixed.AdaptiveFixedAnchorService(self.decoder, self.base)
        rows = tuple((row['id'], tuple(row['tokens'])) for row in self.records)
        admission = probe.admit_records(rows)
        total = admission['reserved_work_units']
        self.assertGreater(total, 0)
        self.assertEqual(total, sum(stage['routes'][stage['selected']]['work_units']
                                    for stage in admission['stages']))
        service = fixed.AdaptiveFixedAnchorService(self.decoder, self.base,
            max_point_work_units=total-1)
        with patch.object(fixed, 'prepare_leaf', side_effect=AssertionError('unadmitted neural work')) as prepare:
            with self.assertRaises(CalibrationWorkRefused) as caught:
                service.run(self.records)
        prepare.assert_not_called()
        self.assertEqual(caught.exception.admission['reserved_work_units'], total)

    def test_lossless_cumulative_zero_cap_precedes_decode(self):
        service = AdaptiveLosslessService(self.decoder, self.base, max_point_work_units=0)
        with patch.object(lossless_parent, 'decode_anchors', side_effect=AssertionError('unadmitted decode')) as decode:
            with self.assertRaises(CalibrationWorkRefused):
                service.repair(self.lossless, ('a',))
        decode.assert_not_called()

    def test_point_base_class_refusal_keeps_complete_spent_work_diagnostics(self):
        service = compressed.AdaptiveCompressedService(self.decoder, self.base,
            certificate_backend='primal')
        with patch.object(compressed, 'certify_primal_dyadic_box',
                          side_effect=TokenBoxUnresolved('review certificate refusal')), \
             patch.object(compressed, 'quantize_adaptive_dyadic_rows',
                          side_effect=LowRankUnresolved('review native point refusal')):
            with self.assertRaises(LowRankUnresolved) as caught:
                service.run(self.records[1:], method='repair', prior=self.original, deleted_ids=('a',))
        error = caught.exception
        self.assertTrue(hasattr(error, 'diagnostics'), 'base-class point refusal lost the service receipt')
        diagnostics = error.diagnostics
        self.assertTrue(diagnostics['aborted'])
        self.assertGreater(diagnostics['point_work_units_reserved'], 0)
        self.assertGreater(diagnostics['certificate_work_units_reserved'], 0)
        self.assertGreater(diagnostics['point_solver_elapsed_ns'], 0)
        self.assertEqual(diagnostics['point_solver_attempted_stages'], 1)
        self.assertEqual(diagnostics['point_solver_stages'], 0)
        self.assertEqual(diagnostics['neural_stage_record_pairs'], 2)
        self.assertEqual(diagnostics['pending_stage']['point_rejection'], 'review native point refusal')


if __name__ == '__main__':
    unittest.main()
