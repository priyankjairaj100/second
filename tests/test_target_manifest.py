"""Contract tests use small arrays, without empirical data or timing claims."""
from dataclasses import replace
from fractions import Fraction as Q
import unittest
from unittest.mock import patch

from src.chart_construction import ChartBudgetError, ChartRecipe, build_chart, make_service, preview_chart
from src.certified_transformer import AutomaticResponseProvider, CertifiedDecoder
from src.target_manifest import TargetRecipe, build_target
from src.transformer_backend import DecoderConfig, DeterministicDecoder
from tests.test_transformer_backend import decoder_fixture


def tiny_weights(value):
    return CertifiedDecoder(DeterministicDecoder(
        DecoderConfig(2, 1, 1, 1, 1, 2), token_embeddings=((0,), (1,)),
        position_embeddings=((0,), (0,)), blocks=({"qkv": ((value,),) * 3,
        "attn_out": ((value,),), "mlp_up": ((value,),), "mlp_down": ((value,),)},),
        lm_head=((0,), (1,))))


class TargetManifestTests(unittest.TestCase):
    def setUp(self):
        self.decoder = CertifiedDecoder(decoder_fixture())
        self.recipe = TargetRecipe(12, group_count=2)
        self.target = build_target(self.decoder, self.recipe)

    def test_exact_bit_count_coverage_and_power_two_steps(self):
        for bits in (2, 3, 4, 8):
            target = build_target(self.decoder, replace(self.recipe, bits=bits))
            for stage in target.stages:
                for j, grid in enumerate(stage.grids):
                    self.assertEqual(len(grid), 1 << bits)
                    self.assertIn(Q(0), grid)
                    step = grid[1] - grid[0]
                    self.assertTrue(step.numerator & (step.numerator - 1) == 0)
                    self.assertTrue(step.denominator & (step.denominator - 1) == 0)
                    self.assertTrue(all(b - a == step for a, b in zip(grid, grid[1:])))
                    self.assertLessEqual(grid[0], min(row[j] for row in stage.weights))
                    self.assertGreaterEqual(grid[-1], max(row[j] for row in stage.weights))
                    self.assertTrue(all(Q.from_float(float(q)) == q for q in grid))

    def test_zero_and_subnormal_columns(self):
        zero = build_target(tiny_weights(0), self.recipe)
        self.assertTrue(all(exponent == 0 for row in zero.scale_exponents for exponent in row))
        tiny = Q(1, 1 << 1074)
        subnormal = build_target(tiny_weights(tiny), self.recipe)
        self.assertTrue(all(exponent == -1074 for row in subnormal.scale_exponents for exponent in row))
        self.assertTrue(all(len(set(float(x) for x in grid)) == 16
                            for stage in subnormal.stages for grid in stage.grids))

    def test_unrepresentable_inputs_and_extreme_grid_reject(self):
        with self.assertRaisesRegex(ValueError, "base weights"):
            build_target(tiny_weights(Q(1, 3)), self.recipe)
        with self.assertRaisesRegex(ValueError, "grid code"):
            build_target(tiny_weights(Q.from_float(float.fromhex("0x1.fffffffffffffp+1023"))),
                         replace(self.recipe, bits=2))

    def test_strict_recipe_roundtrip(self):
        self.assertEqual(TargetRecipe.from_payload(self.recipe.payload()), self.recipe)
        chart = ChartRecipe()
        self.assertEqual(ChartRecipe.from_payload(chart.payload()), chart)
        for kwargs in ({"original_token_count": True}, {"original_token_count": 0},
                       {"original_token_count": 12, "bits": 4.0},
                       {"original_token_count": 12, "ridge": 0.1},
                       {"original_token_count": 12, "ridge": Q(0)},
                       {"original_token_count": 12, "group_count": True}):
            with self.assertRaises((TypeError, ValueError)):
                TargetRecipe(**kwargs)
        for kwargs in ({"radius": 1.0}, {"precision_bits": True}, {"max_rank": 1.0},
                       {"max_direction_entries": True}, {"mode": "fitted"}):
            with self.assertRaises((TypeError, ValueError)):
                ChartRecipe(**kwargs)
        payload = self.recipe.payload()
        payload["unexpected"] = 1
        with self.assertRaises(ValueError):
            TargetRecipe.from_payload(payload)
        payload = self.recipe.payload()
        payload["ridge"] = [2, 200]
        with self.assertRaises(ValueError):
            TargetRecipe.from_payload(payload)

    def test_target_digests_bind_numeric_target_and_source(self):
        self.assertEqual(self.target.digest, build_target(self.decoder, self.recipe).digest)
        for recipe in (replace(self.recipe, bits=3), replace(self.recipe, original_token_count=13),
                       replace(self.recipe, ridge=Q(1, 50)), replace(self.recipe, group_count=3)):
            self.assertNotEqual(self.target.digest, build_target(self.decoder, recipe).digest)
        job = self.target.make_job("reference")
        self.assertIn("V_cert", job.numerical_contract)
        self.assertIn(self.target.digest, job.numerical_contract)
        altered = replace(self.target, exact_core_source_sha256="a" * 64)
        self.assertNotEqual(job.manifest_digest, altered.make_job("reference").manifest_digest)
        self.assertTrue(all(s.normalization == 12 and s.ridge == Q(1, 100) for s in job.stages))

    def test_grid_budget_precedes_materialization(self):
        with self.assertRaisesRegex(ValueError, "grid budget"):
            build_target(self.decoder, replace(self.recipe, max_grid_entries=1))

    def test_stage_rtn_is_deterministic_and_fits_complete_rtn_prefix(self):
        recipe = ChartRecipe()
        built = build_chart(self.decoder, self.target, recipe)
        again = build_chart(self.decoder, self.target, recipe)
        self.assertEqual(built.canonical_bytes(), again.canonical_bytes())
        provider = AutomaticResponseProvider(self.decoder, built.chart)
        prefix = {}
        for stage in self.target.stages:
            coefficients = provider.coefficients(stage.stage_id, prefix)
            self.assertIsNotNone(coefficients)
            prefix[stage.stage_id] = tuple(tuple(min(stage.grids[j], key=lambda q: (abs(q - w), q))
                                                   for j, w in enumerate(row)) for row in stage.weights)
        first = self.target.stages[0]
        self.assertEqual(prefix[first.stage_id][0][0], Q(1, 4))  # 3/8 is a lower tie.
        self.assertNotIn(self.target.stages[-1].stage_id,
                         {s for direction in built.chart.directions for s in direction})

    def test_rtn_chart_rejects_unrepresented_prefix(self):
        built = build_chart(self.decoder, self.target, ChartRecipe())
        provider = AutomaticResponseProvider(self.decoder, built.chart)
        first, second = self.target.stages[:2]
        changed = [list(row) for row in first.weights]
        changed[1][0] += first.grids[0][1] - first.grids[0][0]
        self.assertIsNone(provider.coefficients(second.stage_id, {first.stage_id: changed}))

    def test_coordinate_chart_contains_all_grid_prefixes(self):
        built = build_chart(self.decoder, self.target, ChartRecipe(mode="coordinate"))
        provider = AutomaticResponseProvider(self.decoder, built.chart)
        for endpoint in (0, -1):
            prefix = {}
            for stage in self.target.stages:
                self.assertIsNotNone(provider.coefficients(stage.stage_id, prefix))
                prefix[stage.stage_id] = tuple(tuple(stage.grids[j][endpoint]
                                                     for j in range(stage.width)) for _ in stage.weights)
        used_parameters = sum(len(s.weights) * s.width for s in self.target.stages[:-1])
        self.assertEqual(built.preview.rank, used_parameters)
        self.assertEqual(len(built.chart.directions), used_parameters)

    def test_preview_matches_actual_aggregate_slots(self):
        from src.linear_response import LinearResponseIndex
        from src.response_moments import ResponseIndex
        built = build_chart(self.decoder, self.target, ChartRecipe())
        provider = AutomaticResponseProvider(self.decoder, built.chart)
        actual = 0
        for contract in provider.contracts.values():
            linear = LinearResponseIndex.from_records(contract.response_basis, ())
            error = ResponseIndex.from_records(contract.error_basis, ())
            actual += linear.stored_rational_count
            actual += sum(len(matrix) * len(matrix[0]) for matrix in error.cross_moments)
        self.assertEqual(actual, built.preview.aggregate_rationals_per_group)
        self.assertEqual(actual * 2, built.preview.aggregate_rationals_all_groups)
        actual_directions = sum(len(row) for direction in built.chart.directions for matrix in direction.values() for row in matrix)
        self.assertEqual(actual_directions, built.preview.direction_entries)

    def test_preview_reports_failure_before_directions_are_allocated(self):
        recipe = ChartRecipe(mode="coordinate", max_rank=1, max_direction_entries=1,
                             max_aggregate_rationals=1)
        preview = preview_chart(self.decoder, self.target, recipe)
        self.assertFalse(preview.feasible)
        self.assertEqual(set(preview.over_budget), {"rank", "direction_entries", "aggregate_rationals"})
        with patch("src.chart_construction.AffineChart", side_effect=AssertionError("allocation forbidden")):
            with self.assertRaises(ChartBudgetError):
                build_chart(self.decoder, self.target, recipe)

    def test_manifest_rejects_manual_target_or_chart_changes(self):
        construction = build_chart(self.decoder, self.target, ChartRecipe())
        changed_stage = replace(self.target.stages[0], ridge=Q(2))
        changed_target = replace(self.target, stages=(changed_stage,) + self.target.stages[1:])
        with self.assertRaisesRegex(ValueError, "target does not match"):
            build_chart(self.decoder, changed_target, ChartRecipe())
        changed_chart = replace(construction.chart, precision_bits=128)
        with self.assertRaisesRegex(ValueError, "chart does not match"):
            make_service(self.decoder, self.target, replace(construction, chart=changed_chart))
        service = make_service(self.decoder, self.target, construction)
        self.assertEqual(service.job.numerical_contract, self.target.make_job("unused").numerical_contract)

    def test_none_chart_has_zero_rank(self):
        built = build_chart(self.decoder, self.target, ChartRecipe(mode="none"))
        self.assertEqual(built.preview.rank, 0)
        self.assertEqual(built.chart.directions, ())
        self.assertEqual(built.chart.radii, ())


if __name__ == "__main__":
    unittest.main()
