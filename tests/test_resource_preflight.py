"""Config-only checks. No checkpoint weights or empirical records are read."""
import json
from pathlib import Path
import tempfile
import unittest

from src.chart_construction import ChartRecipe, preview_chart
from src.certified_transformer import CertifiedDecoder
from src.resource_preflight import ResourcePlanError, inspect_local_config
from src.target_manifest import TargetRecipe, build_target
from tests.test_checkpoint_adapter import checkpoint_fixture


class ResourcePreflightTests(unittest.TestCase):
    def test_config_counts_bound_actual_chart_without_weights(self):
        config, _, base = checkpoint_fixture()
        decoder = CertifiedDecoder(base)
        recipe = TargetRecipe(6, group_count=2)
        chart = ChartRecipe()
        actual = preview_chart(decoder, build_target(decoder, recipe), chart)
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'config.json').write_text(json.dumps(config))
            result = inspect_local_config(directory, chart, recipe)
        self.assertEqual(result.quantized_parameters, actual.quantized_parameters)
        self.assertGreaterEqual(result.chart_rank_upper, actual.rank)
        self.assertGreaterEqual(result.aggregate_rationals_upper, actual.aggregate_rationals_all_groups)
        self.assertEqual(result.grid_entries, actual.grid_entries)
        self.assertFalse(result.payload()['measured'])
        self.assertFalse(result.payload()['memory_bound_proved'])

    def test_large_metadata_rejects_before_tensor_loading(self):
        config, _, _ = checkpoint_fixture()
        config.update(n_embd=768, n_head=12, n_inner=3072, n_layer=6,
                      vocab_size=50257, n_positions=1024)
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'config.json').write_text(json.dumps(config))
            result = inspect_local_config(directory, ChartRecipe(), TargetRecipe(128))
        self.assertFalse(result.allowed_by_plan)
        self.assertIn('planning_bytes', result.rejected_limits)
        with self.assertRaises(ResourcePlanError):
            result.require_allowed()

    def test_coordinate_counts_and_zero_chart(self):
        config, _, base = checkpoint_fixture()
        decoder = CertifiedDecoder(base)
        recipe = TargetRecipe(6, group_count=1)
        target = build_target(decoder, recipe)
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'config.json').write_text(json.dumps(config))
            for mode in ('coordinate', 'none'):
                chart = ChartRecipe(mode=mode, max_rank=10000, max_direction_entries=100000)
                result = inspect_local_config(directory, chart, recipe)
                actual = preview_chart(decoder, target, chart)
                self.assertEqual(result.chart_rank_upper, actual.rank)
                self.assertEqual(result.direction_entries_upper, actual.direction_entries)
                self.assertEqual(result.aggregate_rationals_upper, actual.aggregate_rationals_all_groups)

    def test_invalid_metadata_and_budget_fail_closed(self):
        config, _, _ = checkpoint_fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, 'config.json')
            path.write_text(json.dumps(config))
            with self.assertRaises(ValueError):
                inspect_local_config(directory, ChartRecipe(), TargetRecipe(1), memory_budget_bytes=True)
            path.write_text('{"model_type":"gpt2","model_type":"gpt_neo"}')
            with self.assertRaises(ValueError):
                inspect_local_config(directory, ChartRecipe(), TargetRecipe(1))

    def test_huge_layer_count_uses_constant_space_formulas(self):
        config, _, _ = checkpoint_fixture()
        config['n_layer'] = 10**12
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'config.json').write_text(json.dumps(config))
            result = inspect_local_config(directory, ChartRecipe(), TargetRecipe(1))
        self.assertEqual(result.stage_count, 4*10**12)
        self.assertFalse(result.allowed_by_plan)


if __name__ == '__main__':
    unittest.main()
