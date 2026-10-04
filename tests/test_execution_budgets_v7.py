"""Correctness fixtures for durable admission budgets, not empirical timing."""
from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

from src.phase_budget import BudgetExhausted, PhaseBudget
from src.worker_control import WorkerLimits, run_limited
from src.run_store import canonical_json, digest, strict_json
from tests import test_worker_control as fixtures


class PhaseBudgetTests(unittest.TestCase):
    def make(self, folder, cap=10):
        return PhaseBudget(folder, identity={"fixture": True}, phase_cpu_seconds={"software_test": cap})

    def test_unknown_attempt_remains_charged_across_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            first = self.make(folder)
            first.reserve("software_test", "lost-controller", 7)
            restarted = self.make(folder)
            with self.assertRaises(BudgetExhausted):
                restarted.reserve("software_test", "retry", 4)
            restarted.reserve("software_test", "small-other", 3)
            self.assertEqual(restarted.snapshot()["charged_cpu_seconds"]["software_test"], 10)

    def test_settlement_rounds_up_and_idempotent_replay_never_refunds_twice(self):
        with tempfile.TemporaryDirectory() as folder:
            budget = self.make(folder)
            budget.reserve("software_test", "a", 8)
            result = budget.settle("a", 1_000_000_001)
            self.assertEqual(result["charged_cpu_seconds"], 2)
            self.assertEqual(budget.settle("a", 1_000_000_001), result)
            with self.assertRaisesRegex(ValueError, "differs"):
                budget.settle("a", 0)
            with self.assertRaisesRegex(ValueError, "already exists"):
                budget.reserve("software_test", "a", 1)
            budget.reserve("software_test", "b", 8)
            self.assertEqual(budget.snapshot()["charged_cpu_seconds"]["software_test"], 10)

    def test_observed_overrun_is_charged_without_clipping(self):
        with tempfile.TemporaryDirectory() as folder:
            budget = self.make(folder, cap=3)
            budget.reserve("software_test", "a", 3)
            budget.settle("a", 4_000_000_001)
            self.assertEqual(budget.snapshot()["charged_cpu_seconds"]["software_test"], 5)
            self.assertTrue(budget.snapshot()["over_cap"]["software_test"])
            with self.assertRaises(BudgetExhausted):
                budget.reserve("software_test", "b", 1)

    def test_binding_change_and_malformed_debits_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            budget = self.make(folder)
            budget.reserve("software_test", "a", 3)
            with self.assertRaisesRegex(ValueError, "identity"):
                self.make(folder, cap=20)
            ledger_path = Path(folder) / "ledger.json"
            ledger = strict_json(ledger_path.read_bytes())
            ledger["attempts"]["a"]["charged_cpu_seconds"] = 1
            ledger_path.write_bytes(canonical_json(ledger))
            with self.assertRaisesRegex(ValueError, "pending budget debit"):
                budget.snapshot()


@unittest.skipUnless(hasattr(os, "wait4") and hasattr(os, "sched_setaffinity"), "Linux workers required")
class BudgetWorkerTests(unittest.TestCase):
    def limits(self):
        return WorkerLimits(wall_seconds=5, cpu_seconds=2, address_space_bytes=128*1024*1024,
                            threads=1, affinity_cpus=(min(os.sched_getaffinity(0)),),
                            termination_grace_seconds=0, file_size_bytes=4*1024*1024)

    def test_observed_cpu_and_resume_charge_exactly_once(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            budget = PhaseBudget(root / "budget", identity={}, phase_cpu_seconds={"software_test": 10})
            arguments = dict(identity={"fixture": True}, phase_budget=budget, phase="software_test")
            command = [sys.executable, "-c", "sum(range(10000))"]
            result = run_limited(command, root / "worker", self.limits(), **arguments)
            self.assertEqual(result["outcome"]["status"], "complete")
            self.assertGreater(result["resource_usage"]["total_cpu_ns"], 0)
            self.assertEqual(result["budget_debit"]["state"], "settled")
            snapshot = budget.snapshot()
            self.assertEqual(run_limited(command, root / "worker", self.limits(), **arguments), result)
            self.assertEqual(budget.snapshot(), snapshot)

    def test_admission_denial_is_durable_without_launch(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            budget = PhaseBudget(root / "budget", identity={}, phase_cpu_seconds={"software_test": 3})
            with patch("src.worker_control.subprocess.Popen") as launch:
                result = run_limited([sys.executable, "-c", "pass"], root / "worker", self.limits(),
                                     identity={}, phase_budget=budget, phase="software_test")
            launch.assert_not_called()
            self.assertEqual(result["outcome"]["kind"], "phase_cpu_budget_exhausted")
            self.assertEqual(budget.snapshot()["attempts"], {})

    def test_unknown_launch_failure_keeps_allowance(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            budget = PhaseBudget(root / "budget", identity={}, phase_cpu_seconds={"software_test": 4})
            with patch("src.worker_control.subprocess.Popen", side_effect=OSError("launch fixture")):
                result = run_limited([sys.executable, "-c", "pass"], root / "worker", self.limits(),
                                     identity={}, phase_budget=budget, phase="software_test")
            self.assertEqual(result["outcome"]["kind"], "launch_failed")
            self.assertEqual(result["budget_debit"]["state"], "reserved")
            self.assertEqual(budget.snapshot()["charged_cpu_seconds"]["software_test"], 4)


class CampaignBudgetTests(unittest.TestCase):
    def test_caps_require_research_declaration_and_round_down(self):
        from src.experiment_campaign import _phase_caps
        limits = BudgetWorkerTests().limits()
        campaign = {"entries": [{"phase": "development"}]}
        with self.assertRaisesRegex(ValueError, "explicit CPU"):
            _phase_caps(campaign, {}, limits)
        protocol = {"resources": {"phase_cpu_hour_caps": {"development": 0.001}}}
        self.assertEqual(_phase_caps(campaign, protocol, limits), {"development": 3})

    def test_same_protocol_other_output_cannot_reset_budget(self):
        from src.experiment_campaign import run_campaign
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            inventory, manifest = fixtures.CampaignControlTests().fixture(root)
            protocol_path = root / "protocol.json"
            protocol = strict_json(protocol_path.read_bytes())
            protocol["resources"] = {"phase_cpu_hour_caps": {"software_test": 0.0048}}
            raw = canonical_json(protocol)
            protocol_path.write_bytes(raw)
            manifest["protocol"]["sha256"] = digest(raw)
            (root / "run.json").write_bytes(canonical_json(manifest))
            first = run_campaign(inventory, root / "output-one")
            self.assertEqual(first["outcome"], "complete", first["runs"])
            second = run_campaign(inventory, root / "output-two")
            self.assertEqual(second["runs"][0]["worker_outcome"]["kind"], "phase_cpu_budget_exhausted")
            self.assertEqual(first["phase_cpu_budget"]["directory"], second["phase_cpu_budget"]["directory"])


if __name__ == "__main__":
    unittest.main()
