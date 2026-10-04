"""Storage and factory contracts for the new complete baseline paths."""
from dataclasses import replace
from fractions import Fraction as Q
import json
from pathlib import Path
import tempfile
import unittest

from src.certified_transformer import CertifiedDecoder
from src.chart_construction import ChartRecipe, build_chart, make_service, make_identity_service, identity_preview
from src.resource_preflight import inspect_local_config
from src.target_manifest import TargetRecipe, build_target
from src.repair_service import Record
from tests.test_checkpoint_adapter import checkpoint_fixture


class PreparationIntegrationV7Tests(unittest.TestCase):
    def fixture(self):
        config, _, base = checkpoint_fixture()
        decoder = CertifiedDecoder(base)
        target = build_target(decoder, TargetRecipe(4, group_count=1))
        return config, decoder, target

    def test_quadratic_storage_plan_matches_exact_dense_recipe(self):
        config, decoder, target = self.fixture()
        recipe = ChartRecipe(mode="coordinate", response_tier="quadratic")
        construction = build_chart(decoder, target, recipe)
        r = construction.preview.rank
        expected = sum((r+1)*(r+2)//2 * stage.width**2 + (r+3)*(r+4)//2
                       for stage in target.stages)
        self.assertEqual(construction.preview.aggregate_rationals_per_group, expected)
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "config.json").write_text(json.dumps(config))
            plan = inspect_local_config(directory, recipe, target.recipe)
        self.assertEqual(plan.aggregate_rationals_upper, expected)
        self.assertEqual(plan.response_tier, "quadratic")
        linear = build_chart(decoder, target, replace(recipe, response_tier="linear"))
        self.assertEqual(linear.target_digest, construction.target_digest)
        self.assertNotEqual(linear.digest, construction.digest)
        self.assertLess(linear.preview.aggregate_rationals_per_group, expected)

    def test_old_recipe_and_policy_preserve_defined_interfaces(self):
        _, decoder, target = self.fixture()
        recipe = ChartRecipe(mode="grid-box")
        old = recipe.payload()
        old.pop("response_tier")
        self.assertEqual(ChartRecipe.from_payload(old), recipe)
        bad = dict(old, response_tier="unknown")
        with self.assertRaises(ValueError):
            ChartRecipe.from_payload(bad)
        construction = build_chart(decoder, target, recipe)
        spectral = make_service(decoder, target, construction)
        portfolio = make_service(decoder, target, construction, verifier_policy="spectral_or_interval")
        self.assertEqual(spectral.manifest_digest, portfolio.manifest_digest)
        self.assertEqual(spectral.response_tier, portfolio.response_tier)
        self.assertEqual(portfolio.verifier_policy, "spectral_or_interval")

    def test_identity_factory_charges_canonical_cache_and_full_deletion(self):
        _, decoder, target = self.fixture()
        service = make_identity_service(decoder, target)
        records = (Record("a", decoder.record_payload((0, 1))),
                   Record("b", decoder.record_payload((1, 0))))
        original = service.fresh(records).state
        preview = identity_preview(decoder, target)
        self.assertEqual(preview["cache_gram_rational_slots"], original.stored_aggregate_rational_count)
        result = service.repair(original, records, lambda _: self.fail("complete deletion read retained data"))
        oracle = service.fresh(()).state
        self.assertEqual(result.state.canonical_bytes(), oracle.canonical_bytes())
        self.assertEqual(service.service_family, "identity_cache")
        self.assertIn(target.digest, service.job.numerical_contract)


if __name__ == "__main__":
    unittest.main()
