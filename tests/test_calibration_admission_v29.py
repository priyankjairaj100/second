"""Allocation-free structural size checks; not empirical model tests."""
from dataclasses import FrozenInstanceError, asdict
import json
import unittest

from src.calibration_admission_v29 import StageShape, assess_calibration_admission


class CalibrationAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.stage = StageShape('representative.mlp_down', width=3072, rows=768)
        self.cap = 6 * 2**30

    def assess(self, tokens, cap=None):
        return assess_calibration_admission((self.stage,), retained_tokens=tokens,
                                            process_cap_bytes=self.cap if cap is None else cap)

    def test_requested_static_sizes_are_exact(self):
        for tokens in (16, 128, 512, 2048, 262144):
            result = self.assess(tokens)
            stage = result.stages[0]
            self.assertEqual(stage.token_matrix_bytes, 8*tokens*tokens)
            self.assertEqual(stage.feature_matrix_bytes, 8*3072*tokens)
            self.assertEqual(stage.coefficient_table_bytes, 8*3072*tokens)
            self.assertEqual(stage.weight_matrix_bytes, 8*3072*768)
            self.assertEqual(stage.alternative_primal_matrix_bytes, 8*3072*3072)
            self.assertEqual(result.raw_full_factor_storage_bytes, 8*3072*tokens)
            self.assertEqual(result.ruled_out, tokens == 262144)
            self.assertFalse(result.fit_guaranteed)
            self.assertFalse(result.speed_guaranteed)
            self.assertFalse(result.completion_guaranteed)
            self.assertFalse(result.actual_arrays_allocated)
            self.assertFalse(result.alternative_primal_certificate_implemented)

    def test_one_dense_matrix_rejects_even_when_primal_size_is_small(self):
        result = self.assess(262144)
        self.assertEqual(result.stages[0].token_matrix_bytes, 512 * 2**30)
        self.assertEqual(result.stages[0].alternative_primal_matrix_bytes, 72 * 2**20)
        self.assertEqual(result.status, 'ruled_out_by_lower_bound')
        self.assertIn(('representative.mlp_down', 'dense_token_matrix', 512*2**30), result.lower_bound_witnesses)

    def test_equality_does_not_claim_fit_or_force_rejection(self):
        result = self.assess(2048, cap=8*3072*2048)
        self.assertFalse(result.ruled_out)
        self.assertEqual(result.status, 'not_ruled_out_by_lower_bound')
        self.assertFalse(result.fit_guaranteed)
        rejected = self.assess(2048, cap=8*3072*2048-1)
        self.assertTrue(rejected.ruled_out)

    def test_multiple_stage_storage_is_sum_but_admission_is_maximum(self):
        stages = (self.stage, StageShape('another.stage', width=768, rows=2304))
        result = assess_calibration_admission(stages, retained_tokens=128, process_cap_bytes=self.cap)
        self.assertEqual(result.raw_full_factor_values, 128*(3072+768))
        self.assertEqual(result.single_array_lower_bound_bytes,
                         max(stage.single_array_lower_bound_bytes for stage in result.stages))
        self.assertLessEqual(result.single_array_lower_bound_bytes, result.process_cap_bytes)

    def test_zero_tokens_keep_weight_requirement_only(self):
        result = self.assess(0)
        self.assertEqual(result.raw_full_factor_storage_bytes, 0)
        self.assertEqual(result.stages[0].token_matrix_bytes, 0)
        self.assertEqual(result.single_array_lower_bound_bytes, 8*3072*768)

    def test_arbitrarily_large_integer_dimensions_do_not_allocate_arrays(self):
        tokens = 10**100
        result = self.assess(tokens)
        self.assertEqual(result.stages[0].token_matrix_bytes, 8*tokens*tokens)
        self.assertTrue(result.ruled_out)
        self.assertFalse(result.actual_arrays_allocated)

    def test_contracts_reject_bool_negative_float_and_ambiguous_stages(self):
        for value in (True, -1, 1.0, '16', None):
            with self.assertRaises(ValueError):
                self.assess(value)
        for cap in (True, 0, -1, 6.0):
            with self.assertRaises(ValueError):
                self.assess(16, cap)
        for stages in ([], (), [self.stage], (self.stage, self.stage), (object(),)):
            with self.assertRaises(ValueError):
                assess_calibration_admission(stages, retained_tokens=16, process_cap_bytes=self.cap)
        for width, rows in ((0, 1), (1, 0), (True, 1), (1, -1), (1.0, 1)):
            with self.assertRaises(ValueError):
                StageShape('stage', width, rows)
        for name in ('', ' stage', 'stage ', None):
            with self.assertRaises(ValueError):
                StageShape(name, 1, 1)

    def test_reports_are_immutable_and_json_serializable(self):
        result = self.assess(16)
        with self.assertRaises(FrozenInstanceError):
            result.ruled_out = True
        encoded = json.loads(json.dumps(asdict(result)))
        self.assertEqual(encoded['status'], 'not_ruled_out_by_lower_bound')
        self.assertFalse(encoded['alternative_primal_certificate_implemented'])


if __name__ == '__main__':
    unittest.main()
