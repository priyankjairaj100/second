"""Separate-process correctness fixtures; these are not research measurements."""
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from src.isolated_comparison import (build_isolated_plan, isolated_source_hashes, run_isolated,
                                    validate_isolated_plan)
from src.result_analysis import outcome, validate_run
from src.run_store import canonical_json, digest, strict_json
from tests import test_worker_control as fixtures


@unittest.skipUnless(hasattr(os, "wait4") and hasattr(os, "sched_setaffinity"), "Linux workers required")
class IsolatedComparisonTests(unittest.TestCase):
    def fixture(self, root, *, manifest_changes=None, protocol_changes=None, target=None):
        inventory, manifest = fixtures.CampaignControlTests().fixture(root)
        campaign = strict_json(inventory.read_bytes())
        if protocol_changes:
            protocol_path = root / "protocol.json"
            protocol = strict_json(protocol_path.read_bytes())
            protocol.update(protocol_changes)
            raw = canonical_json(protocol)
            protocol_path.write_bytes(raw)
            manifest["protocol"]["sha256"] = digest(raw)
        if manifest_changes:
            manifest.update(manifest_changes)
        (root / "run.json").write_bytes(canonical_json(manifest))
        plan = build_isolated_plan(manifest_path="run.json", manifest=manifest,
            target_manifest_sha256=target or campaign["entries"][0]["target_manifest_sha256"],
            worker_limits=campaign["worker_limits"], sources=isolated_source_hashes())
        path = root / "isolated.json"
        path.write_bytes(canonical_json(plan))
        return path, manifest

    def test_four_processes_exact_outputs_sealed_timing_and_resume(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            plan, _ = self.fixture(root)
            validation = run_isolated(plan, root / "result", validate_only=True)
            self.assertFalse(validation["checkpoint_parameters_loaded"])
            self.assertFalse((root / "result").exists())
            result = run_isolated(plan, root / "result")
            self.assertEqual(result["outcome"], "complete", result)
            validate_run(result)
            pids = {result["setup"]["worker_pid"]}
            for name, arm in result["methods"].items():
                self.assertEqual(outcome(arm, result["status"]), "exact_complete")
                self.assertGreater(arm["complete_wall_time_ns"], 0)
                pids.add(arm["worker_pid"])
                child_root = root / "result" / "children" / name
                child = strict_json((child_root / "result.json").read_bytes())
                artifacts = set(child["artifacts"])
                self.assertEqual(artifacts, {"request.json", name + "-state.json", name + "-model.json"})
                self.assertGreater(arm["complete_wall_time_ns"], child["preflight"]["preflight_wall_ns"])
            self.assertEqual(len(pids), 4)
            self.assertEqual(len(result["phase_cpu_budget_at_completion"]["attempts"]), 4)
            ledger = Path(result["phase_cpu_budget"]["directory"]) / "ledger.json"
            before = ledger.read_bytes()
            self.assertEqual(run_isolated(plan, root / "result"), result)
            self.assertEqual(ledger.read_bytes(), before)

    def test_pause_and_confirmation_fail_before_creating_outputs(self):
        for confirmation in (False, True):
            with self.subTest(confirmation=confirmation), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                plan, _ = self.fixture(root,
                    manifest_changes={"phase": "confirmation" if confirmation else "development"},
                    protocol_changes={"status": "frozen_confirmation"} if confirmation else None)
                expected = "frozen campaign inventory" if confirmation else "paused"
                with self.assertRaisesRegex(ValueError, expected):
                    run_isolated(plan, root / "result")
                self.assertFalse((root / "result").exists())
                self.assertEqual(list(root.glob("phase-cpu-budget-*")), [])

    def test_budget_denial_is_immutable_and_keeps_planned_arms(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            plan, _ = self.fixture(root, protocol_changes={"resources": {
                "phase_cpu_hour_caps": {"software_test": 0.001}}})
            result = run_isolated(plan, root / "result")
            self.assertEqual(result["outcome"], "failed")
            self.assertEqual(result["setup"]["worker_outcome"]["kind"], "phase_cpu_budget_exhausted")
            self.assertEqual(set(result["methods"]), {"repair", "indexed_fresh", "direct_fresh"})
            self.assertTrue(all(row["status"] == "not_started" for row in result["methods"].values()))
            self.assertEqual(run_isolated(plan, root / "result"), result)

    def test_failed_child_is_sealed_and_its_artifacts_are_verified_on_resume(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            plan, _ = self.fixture(root, target="f" * 64)
            result = run_isolated(plan, root / "result")
            self.assertEqual(result["outcome"], "failed")
            child_root = root / "result" / "children" / "setup"
            child = strict_json((child_root / "result.json").read_bytes())
            self.assertEqual(child["outcome"]["status"], "failed")
            self.assertEqual(run_isolated(plan, root / "result"), result)
            request = child_root / child["attempt"] / "request.json"
            request.write_bytes(request.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "artifact hash mismatch"):
                run_isolated(plan, root / "result")

    def test_parent_restart_reuses_already_sealed_worker(self):
        from src import isolated_comparison
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            plan, _ = self.fixture(root)
            real = isolated_comparison.run_limited
            calls = []
            def stop_after_setup(*args, **kwargs):
                worker = real(*args, **kwargs)
                calls.append(worker)
                raise KeyboardInterrupt("parent fixture after worker commit")
            with patch("src.isolated_comparison.run_limited", side_effect=stop_after_setup):
                with self.assertRaises(KeyboardInterrupt):
                    run_isolated(plan, root / "result")
            worker_result = root / "result" / "workers" / "setup" / "result.json"
            saved = worker_result.read_bytes()
            result = run_isolated(plan, root / "result")
            self.assertEqual(result["outcome"], "complete", result)
            self.assertEqual(worker_result.read_bytes(), saved)
            self.assertEqual(len(result["phase_cpu_budget_at_completion"]["attempts"]), 4)
            self.assertEqual(len(list((root / "result" / "workers" / "setup").glob("attempt-*"))), 1)

    def test_sealed_child_without_worker_timing_cannot_become_a_fast_success(self):
        from src import isolated_comparison
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            plan, _ = self.fixture(root)
            real = isolated_comparison.run_limited
            def lose_outer_receipt(*args, **kwargs):
                worker = real(*args, **kwargs)
                path = Path(args[1]) / "result.json"
                unfinished = strict_json(path.read_bytes())
                unfinished["status"] = "running"
                path.write_bytes(canonical_json(unfinished))
                raise KeyboardInterrupt("fixture loses terminal outer receipt")
            with patch("src.isolated_comparison.run_limited", side_effect=lose_outer_receipt):
                with self.assertRaises(KeyboardInterrupt):
                    run_isolated(plan, root / "result")
            result = run_isolated(plan, root / "result")
            self.assertEqual(result["outcome"], "failed")
            self.assertEqual(result["setup"]["status"], "failed")
            self.assertTrue(all(row["status"] == "not_started" for row in result["methods"].values()))


if __name__ == "__main__":
    unittest.main()
