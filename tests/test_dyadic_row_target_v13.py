from fractions import Fraction as Q
import unittest

from src.certified_transformer import CertifiedDecoder
from src.dyadic_row_target import build_dyadic_row_target
from src.row_target_manifest import build_row_target
from src.target_manifest import TargetRecipe
from tests.test_transformer_backend import decoder_fixture


class DyadicRowTargetTests(unittest.TestCase):
    def test_grid_budget_counts_all_output_rows_for_both_constructors(self):
        decoder = CertifiedDecoder(decoder_fixture(block_count=2))
        widths = sum(len(decoder.stage_weights(stage)[0]) for stage in decoder.stage_ids)
        rows = sum(len(decoder.stage_weights(stage)) for stage in decoder.stage_ids)
        self.assertGreater(rows, widths)
        for constructor in (build_row_target, build_dyadic_row_target):
            with self.assertRaisesRegex(ValueError, "output-row grid budget"):
                constructor(decoder, TargetRecipe(original_token_count=6, group_count=1,
                                                  max_grid_entries=rows * 16 - 1))
            constructor(decoder, TargetRecipe(original_token_count=6, group_count=1,
                                               max_grid_entries=rows * 16))

    def test_distinct_target_complete_base_bindings_and_scale_metadata(self):
        decoder = CertifiedDecoder(decoder_fixture(block_count=2))
        recipe = TargetRecipe(original_token_count=6, group_count=1)
        power2 = build_row_target(decoder, recipe)
        target = build_dyadic_row_target(decoder, recipe)
        self.assertNotEqual(target.digest, power2.digest)
        payload = target.payload()
        self.assertIn("no canonical repair-state", payload["output_rule"])
        self.assertEqual(payload["significant_bits"], 24)
        self.assertEqual(payload["schema"], "fixed-v-cert-dyadic-row-grid-diagnostic-target-v1")
        self.assertNotIn("zero_column_scale_exponent", payload)
        self.assertEqual(len(payload["dyadic_solver_source_sha256"]), 64)
        self.assertEqual(len(payload["batched_solver_source_sha256"]), 64)
        for stage, old_stage, entry in zip(target.stages, power2.stages, payload["stages"]):
            self.assertFalse(hasattr(stage, "grids"))
            self.assertEqual(stage.weights, old_stage.weights)
            self.assertEqual(stage.dependencies, old_stage.dependencies)
            self.assertEqual(stage.ridge, old_stage.ridge)
            self.assertEqual(stage.normalization, old_stage.normalization)
            self.assertEqual(stage.bits, 4)
            self.assertEqual(len(stage.scale_values), len(stage.weights))
            self.assertEqual(entry["row_scale_hex"], [value.hex() for value in stage.scale_values])
            self.assertNotIn("grids_sha256", entry)
            self.assertNotIn("scale_exponents", entry)
            self.assertEqual(entry["shape"], [len(stage.weights), stage.width])
            for row, scale in zip(stage.weights, stage.scale_values):
                rational = Q.from_float(scale)
                self.assertTrue(all(-8*rational <= weight <= 7*rational for weight in row))
        before = target.digest
        payload["stages"][0]["row_scale_hex"][0] = "0x1p+100"
        self.assertEqual(target.digest, before)


if __name__ == "__main__":
    unittest.main()
