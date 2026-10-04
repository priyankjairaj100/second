"""Integration checks for fixed boxes, resource counts, and control modes.

These are software fixtures. Their measurements are not research evidence.
"""
from dataclasses import replace
from fractions import Fraction as Q
import json
from pathlib import Path
import tempfile
import unittest

from src.box_response_provider import BoxResponseProvider, ParameterBox
from src.certified_transformer import CertifiedDecoder
from src.chart_construction import ChartRecipe, build_chart, make_service
from src.experiment_runner import run_comparison
from src.resource_preflight import inspect_local_config
from src.run_store import RunStore
from src.target_manifest import TargetRecipe, build_target
from tests.test_checkpoint_adapter import checkpoint_fixture
from tests import test_experiment_runner as runner_fixtures


class PreparationIntegrationTests(unittest.TestCase):
    def setup_target(self):
        config, _, base = checkpoint_fixture()
        decoder = CertifiedDecoder(base)
        target = build_target(decoder, TargetRecipe(6, group_count=1))
        return config, decoder, target

    def test_grid_box_contains_all_endpoint_prefixes_and_binds_domain(self):
        _, decoder, target = self.setup_target()
        construction = build_chart(decoder, target, ChartRecipe(mode="grid-box"))
        provider = BoxResponseProvider(decoder, construction.chart)
        for endpoint in (0, -1):
            prefix = {}
            for stage in target.stages:
                self.assertTrue(provider.contains_prefix(stage.stage_id, prefix))
                prefix[stage.stage_id] = tuple(tuple(stage.grids[j][endpoint] for j in range(stage.width))
                                              for _ in stage.weights)
        used = sum(len(s.weights)*s.width for s in target.stages[:-1])
        self.assertEqual(construction.preview.direction_entries, 2*used)
        self.assertEqual(construction.preview.rank, 0)
        self.assertEqual(construction.target_digest, target.digest)
        self.assertEqual(construction.payload()["preview"]["domain_storage_kind"], "box_endpoint_rationals")
        service = make_service(decoder, target, construction)
        self.assertIn(target.digest, service.job.numerical_contract)
        self.assertEqual(service.reference_weights, {
            s: tuple(tuple(Q.from_float(x) for x in row) for row in decoder.base._float_weights[s])
            for s in decoder.stage_ids})

    def test_changed_box_rejects_before_service_construction(self):
        _, decoder, target = self.setup_target()
        construction = build_chart(decoder, target, ChartRecipe(mode="grid-box"))
        altered = ParameterBox({}, construction.chart.provenance, construction.chart.precision_bits)
        with self.assertRaisesRegex(ValueError, "deterministic construction"):
            make_service(decoder, target, replace(construction, chart=altered))
        with self.assertRaisesRegex(ValueError, "radius must equal one"):
            ChartRecipe(mode="grid-box", radius=Q(2))

    def test_preflight_box_counts_match_constructed_domain(self):
        config, decoder, target = self.setup_target()
        recipe = ChartRecipe(mode="grid-box")
        construction = build_chart(decoder, target, recipe)
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "config.json").write_text(json.dumps(config))
            preflight = inspect_local_config(directory, recipe, target.recipe)
        self.assertEqual(preflight.direction_entries_upper, construction.preview.direction_entries)
        self.assertEqual(preflight.aggregate_rationals_upper, construction.preview.aggregate_rationals_all_groups)
        largest_stage = max(len(s.weights)*s.width for s in target.stages)
        self.assertEqual(preflight.temporary_jet_components_upper, 2*largest_stage)
        self.assertFalse(preflight.payload()["memory_bound_proved"])

    def test_runner_controls_match_oracle_and_keep_diagnostics_outside_state(self):
        decoder, service, records, heldout, metadata = runner_fixtures.ExperimentRunnerTests().fixture()
        for mode in ("identity_only", "fixed_reference"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                result = run_comparison(decoder, service, records, ["0"], heldout,
                                        RunStore(directory, {"control":mode}), metadata, service_mode=mode)
                self.assertEqual(result["status"], "complete", result.get("failure"))
                self.assertEqual(result["service_mode"], mode)
                for row in result["methods"].values():
                    self.assertTrue(row["exact_state_equal"])
                    self.assertLessEqual(row["service_telemetry"]["total_exclusive_ns"], row["complete_wall_time_ns"])
                    self.assertIn("artifact_output", row["service_telemetry"]["timings"])
                self.assertEqual(result["methods"]["repair"]["state_sha256"],
                                 result["methods"]["direct_fresh"]["state_sha256"])


if __name__ == "__main__":
    unittest.main()
