"""Tiny software fixtures for frozen confirmation dispatch, never research evidence."""
from copy import deepcopy
from pathlib import Path
import os
import tempfile
import unittest

from src.isolated_comparison import build_isolated_plan, isolated_source_hashes, run_isolated
from src.isolated_inventory import (build_isolated_campaign, isolated_analysis_plan,
    run_isolated_campaign, validate_isolated_campaign_files, validate_isolated_inventory)
from src.result_analysis import analyze_runs
from src.run_store import canonical_json, digest, strict_json
from tests import test_worker_control as fixtures


@unittest.skipUnless(hasattr(os, "wait4") and hasattr(os, "sched_setaffinity"), "Linux workers required")
class IsolatedCampaignTests(unittest.TestCase):
    def fixture(self, root, *, phase="software_test", paused=False, bad_target=False, budget_hours=1, quality=False):
        old_inventory, manifest = fixtures.CampaignControlTests().fixture(root)
        old = strict_json(old_inventory.read_bytes())
        manifest["phase"] = phase
        protocol = {"schema": "calibration-protocol-v1", "status": "experiments_paused" if paused else
                    "frozen_confirmation" if phase == "confirmation" else "development",
                    "blocked_fields": [], "confirmation_configuration_ids": ["fixture"],
                    "stages": {"confirmation": {"independent_roots": 1, "timing_repeats": 1}},
                    "sampling": {"requests": ["delete-one"]},
                    "resources": {"phase_cpu_hour_caps": {phase: budget_hours}}}
        plan = build_isolated_plan(manifest_path="run.json", manifest=manifest,
            target_manifest_sha256="f" * 64 if bad_target else old["entries"][0]["target_manifest_sha256"],
            worker_limits=old["worker_limits"], sources=isolated_source_hashes(), quality=quality)
        inventory = build_isolated_campaign(campaign_id="fixture", protocol_path="protocol.json",
            worker_limits=old["worker_limits"], plans=[{"plan_path": "plan.json", "plan": plan}],
            workloads=old["workloads"], sources=isolated_source_hashes())
        raw = canonical_json(inventory)
        inventory_path = root / "isolated-campaign.json"
        inventory_path.write_bytes(raw)
        protocol["planned_inventory_sha256"] = digest(raw)
        protocol_raw = canonical_json(protocol)
        (root / "protocol.json").write_bytes(protocol_raw)
        manifest["protocol"]["sha256"] = digest(protocol_raw)
        (root / "run.json").write_bytes(canonical_json(manifest))
        (root / "plan.json").write_bytes(canonical_json(plan))
        return inventory_path, inventory

    def test_dispatch_analysis_budget_and_verified_resume(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, inventory = self.fixture(root)
            validation = run_isolated_campaign(path, root / "results", validate_only=True)
            self.assertFalse(validation["checkpoint_parameters_loaded"])
            self.assertFalse((root / "results").exists())
            result = run_isolated_campaign(path, root / "results")
            self.assertEqual(result["outcome"], "complete", result["runs"])
            analysis = isolated_analysis_plan(inventory, protocol_sha256=result["protocol_sha256"])
            summary = analyze_runs([row["analysis"] for row in result["runs"]], planned_runs=analysis["planned_runs"])
            self.assertTrue(summary)
            self.assertEqual(len(result["phase_cpu_budget_at_completion"]["attempts"]), 4)
            self.assertEqual(run_isolated_campaign(path, root / "results"), result)

    def test_confirmation_requires_actual_complete_inventory_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, _ = self.fixture(root, phase="confirmation")
            with self.assertRaisesRegex(ValueError, "frozen campaign inventory"):
                run_isolated(root / "plan.json", root / "standalone")
            with self.assertRaisesRegex(ValueError, "absent"):
                run_isolated(root / "plan.json", root / "forged", inventory_path=path, inventory_run_id="missing")
            self.assertFalse((root / "forged").exists())
            result = run_isolated_campaign(path, root / "results")
            self.assertEqual(result["outcome"], "complete", result["runs"])
            child_request = result["runs"][0]["analysis"]["children"]["repair"]["request"]
            self.assertEqual(child_request["inventory"]["sha256"], result["inventory_sha256"])

    def test_partial_confirmation_product_rejected_before_dispatch(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, _ = self.fixture(root, phase="confirmation")
            protocol_path = root / "protocol.json"
            protocol = strict_json(protocol_path.read_bytes())
            protocol["confirmation_configuration_ids"].append("missing-configuration")
            raw = canonical_json(protocol)
            protocol_path.write_bytes(raw)
            manifest = strict_json((root / "run.json").read_bytes())
            manifest["protocol"]["sha256"] = digest(raw)
            (root / "run.json").write_bytes(canonical_json(manifest))
            with self.assertRaisesRegex(ValueError, "complete declared comparison product"):
                run_isolated_campaign(path, root / "results")
            self.assertFalse((root / "results").exists())

    def test_pause_and_changed_plan_fail_before_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, _ = self.fixture(root, phase="development", paused=True)
            with self.assertRaisesRegex(ValueError, "paused"):
                run_isolated_campaign(path, root / "results")
            self.assertFalse((root / "results").exists())
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, _ = self.fixture(root)
            plan = strict_json((root / "plan.json").read_bytes())
            plan["target_manifest_sha256"] = "f" * 64
            (root / "plan.json").write_bytes(canonical_json(plan))
            with self.assertRaisesRegex(ValueError, "differs from inventory"):
                run_isolated_campaign(path, root / "results")
            self.assertFalse((root / "results").exists())

    def test_failed_setup_preserves_arms_and_nested_artifact_checks(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, inventory = self.fixture(root, bad_target=True)
            result = run_isolated_campaign(path, root / "results")
            self.assertEqual(result["outcome"], "failed")
            self.assertEqual(result["failed_runs"], 1)
            self.assertEqual(set(result["runs"][0]["analysis"]["methods"]), {"repair", "indexed_fresh", "direct_fresh"})
            self.assertEqual(run_isolated_campaign(path, root / "results"), result)
            child = root / "results" / "runs" / inventory["entries"][0]["run_id"] / "children" / "setup"
            record = strict_json((child / "result.json").read_bytes())
            artifact = child / record["attempt"] / "request.json"
            artifact.write_bytes(artifact.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "artifact hash mismatch"):
                run_isolated_campaign(path, root / "results")

    def test_bindings_reject_limits_target_and_path_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _, inventory = self.fixture(root)
            for field, replacement in (("worker_limits", dict(inventory["worker_limits"], cpu_seconds=1)),
                                       ("target_manifest_sha256", "f" * 64),
                                       ("manifest_path", "another.json")):
                modified = deepcopy(inventory)
                plan = modified["entries"][0]["isolated_plan_payload"]
                plan[field] = replacement
                modified["entries"][0]["isolated_plan_sha256"] = digest(canonical_json(plan))
                with self.assertRaises(ValueError):
                    validate_isolated_inventory(modified)

    def test_optional_quality_has_a_fifth_budgeted_process_outside_method_clocks(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, _ = self.fixture(root, quality=True)
            result = run_isolated_campaign(path, root / "results")
            self.assertEqual(result["outcome"], "complete", result["runs"])
            comparison = result["runs"][0]["analysis"]
            quality = comparison["quality_evaluation"]
            self.assertTrue(quality["outside_method_clocks"])
            self.assertEqual(quality["status"], "complete")
            self.assertEqual(comparison["quality"]["direct_fresh"], comparison["quality"]["repair"])
            self.assertEqual(set(comparison["quality"]), {"base", "original", "direct_fresh", "repair"})
            pids = {comparison["setup"]["worker_pid"], quality["worker_pid"]}
            pids.update(row["worker_pid"] for row in comparison["methods"].values())
            self.assertEqual(len(pids), 5)
            self.assertEqual(len(result["phase_cpu_budget_at_completion"]["attempts"]), 5)
            self.assertEqual(run_isolated_campaign(path, root / "results"), result)

    def test_feasibility_is_paused_and_requires_its_own_cap(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path, _ = self.fixture(root, phase="feasibility", paused=True, budget_hours=3)
            validation = run_isolated_campaign(path, root / "results", validate_only=True)
            self.assertEqual(validation["phase_cpu_seconds"]["feasibility"], 3 * 3600)
            with self.assertRaisesRegex(ValueError, "paused"):
                run_isolated_campaign(path, root / "results")
            self.assertFalse((root / "results").exists())
            protocol = strict_json((root / "protocol.json").read_bytes())
            protocol["resources"]["phase_cpu_hour_caps"] = {}
            raw = canonical_json(protocol)
            (root / "protocol.json").write_bytes(raw)
            manifest = strict_json((root / "run.json").read_bytes())
            manifest["protocol"]["sha256"] = digest(raw)
            (root / "run.json").write_bytes(canonical_json(manifest))
            with self.assertRaisesRegex(ValueError, "explicit CPU-hour cap"):
                run_isolated_campaign(path, root / "results", validate_only=True)


if __name__ == "__main__":
    unittest.main()
