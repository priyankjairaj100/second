"""Independent v9 contract attacks. Software fixtures, never research evidence."""
import sys
import tracemalloc
import unittest
from copy import deepcopy
from pathlib import Path
import tempfile
from unittest.mock import patch

from src.instrumentation import instrumentation_scope, instrumentation_state


class AdversarialCleanInstrumentationTests(unittest.TestCase):
    def test_local_monitoring_cannot_evade_clean_scope_by_leaving_global_events_zero(self):
        monitoring = getattr(sys, "monitoring", None)
        if monitoring is None:
            self.skipTest("requires CPython monitoring support")
        available = [tool for tool in range(6) if monitoring.get_tool(tool) is None]
        if not available:
            self.skipTest("no free monitoring tool slot")
        tool = available[-1]
        monitoring.use_tool_id(tool, "independent-review-fixture")
        calls = []

        def candidate():
            value = 1
            return value + 1

        try:
            monitoring.register_callback(tool, monitoring.events.LINE, lambda *args: calls.append(1))
            monitoring.set_local_events(tool, candidate.__code__, monitoring.events.LINE)
            self.assertEqual(monitoring.get_events(tool), 0)
            candidate()
            self.assertGreater(len(calls), 0)
            with self.assertRaisesRegex(RuntimeError, "instrumentation"):
                with instrumentation_scope("clean"):
                    self.fail("local monitoring entered a clean scope")
        finally:
            monitoring.set_local_events(tool, candidate.__code__, 0)
            monitoring.register_callback(tool, monitoring.events.LINE, None)
            monitoring.free_tool_id(tool)

    def test_profiler_activated_during_success_cannot_leave_clean_scope_successfully(self):
        previous = sys.getprofile()
        if previous is not None:
            self.skipTest("test requires no existing profiler")
        try:
            with self.assertRaisesRegex(RuntimeError, "instrumentation"):
                with instrumentation_scope("clean"):
                    sys.setprofile(lambda *args: None)
            self.assertEqual(instrumentation_state()["mode"], "diagnostic")
        finally:
            sys.setprofile(previous)

    def test_instrumentation_failure_does_not_hide_original_failed_work(self):
        previous = sys.getprofile()
        if previous is not None:
            self.skipTest("test requires no existing profiler")
        failure = ArithmeticError("finite evaluator failed")
        try:
            with self.assertRaises(ArithmeticError) as caught:
                with instrumentation_scope("clean"):
                    sys.setprofile(lambda *args: None)
                    raise failure
            self.assertIs(caught.exception, failure)
            self.assertTrue(any("postcheck failed" in item for item in failure.__notes__))
            self.assertEqual(instrumentation_state()["mode"], "diagnostic")
        finally:
            sys.setprofile(previous)

    def test_clean_measurement_disables_optional_collectors_and_allocation_tracking(self):
        from src.experiment_runner import measure
        from src.service_telemetry import ServiceTelemetry, diagnostic, operation

        @operation
        def operation_with_diagnostics():
            diagnostic("stage", "large-bound", build=lambda _: self.fail("diagnostic callback executed"))
            self.assertFalse(tracemalloc.is_tracing())
            return "exact-output"

        with instrumentation_scope("clean"):
            collector = ServiceTelemetry()
            output, metrics = measure(lambda: operation_with_diagnostics(telemetry=collector))
        self.assertEqual(output, "exact-output")
        self.assertFalse(collector.payload()["instrumented"])
        self.assertFalse(metrics["allocation_tracking"])
        self.assertIsNone(metrics["peak_python_bytes"])


class AdversarialFeasibilityTests(unittest.TestCase):
    def test_changed_leaf_outputs_do_not_create_changed_ancestor_coverage(self):
        from src.feasibility_decision import evaluate_feasibility
        from src.run_store import canonical_json, digest
        from tests import test_feasibility_decision_v9 as fixtures
        policy, evidence = fixtures.fixture()
        for root in evidence["roots"]:
            previous = root["initial_stage_codes"]
            for index, request in enumerate(root["requests"]):
                codes = dict(root["initial_stage_codes"])
                codes["c"] = fixtures.sha(root["root_id"] + "leaf-only" + str(index))
                request["models"] = {method: deepcopy(codes) for method in fixtures.ORACLES}
                request["coverage"]["replicate"].update(stage_codes=dict(codes),
                    predecessor_stage_map_sha256=digest(canonical_json(previous)))
                request["quality"]["binding"]["retained_model_stage_map_sha256"] = digest(canonical_json(codes))
                previous = codes
        result = evaluate_feasibility(policy, evidence)
        self.assertEqual(result["decision"], "inconclusive_mechanism_not_demonstrated", result)
        self.assertTrue(all(root["coverage_denominator"] == 0 for root in result["roots"]))
        self.assertFalse(result["conditions_satisfied"])

    def test_enclosing_lifetime_term_cannot_be_shorter_than_its_bound_worker(self):
        from src.feasibility_decision import evaluate_feasibility
        from tests import test_feasibility_decision_v9 as fixtures
        policy, evidence = fixtures.fixture()
        evidence["resources"]["workers"][0]["wall_ns"] = 899_000_000_000
        result = evaluate_feasibility(policy, evidence)
        self.assertEqual(result["decision"], "inconclusive_invalid_evidence", result)
        self.assertFalse(result["conditions_satisfied"])

    def test_extra_diagnostic_slots_cannot_disappear_from_assembled_program(self):
        from src import measured_analysis
        from src.feasibility_archive import assemble_feasibility_evidence
        from src.feasibility_decision import EvidenceError
        from tests import test_feasibility_decision_v9 as fixtures

        policy, evidence = fixtures.fixture()
        clean = fixtures.issued_fixture(evidence)
        diagnostic = clean.payload()
        for slot in diagnostic["slots"]:
            slot["execution_mode"] = "diagnostic"
        extra = deepcopy(diagnostic["slots"][0])
        extra.update(root_id="extra-unpaired-root", run_id="extra-unpaired-run")
        diagnostic["slots"].append(extra)
        # Structural white-box fixture, not a public route to verified archives.
        diagnostic = measured_analysis.VerifiedMeasuredEvidence(diagnostic, _issuer=measured_analysis._ISSUER)
        with self.assertRaises(EvidenceError):
            assemble_feasibility_evidence(policy, clean, diagnostic)


class AdversarialMeasuredAnalysisTests(unittest.TestCase):
    def test_one_registered_comparison_cannot_promote_two_configuration_strata(self):
        from src import measured_analysis as analysis
        from tests.test_measured_analysis_v9 import fixture_evidence, issued

        evidence = fixture_evidence()
        extra = deepcopy(evidence["slots"])
        for row in extra:
            row["configuration_id"] = "unselected-second-configuration"
            row["run_id"] += "-second"
        evidence["slots"] += extra
        report = analysis.analyze_verified_evidence(issued(evidence))
        self.assertTrue(all(not row["confirmation_timing_eligible"] for row in report["results"]))
        self.assertTrue(all(not row["confirmation_speed_rule_met"] for row in report["results"]))
        self.assertTrue(all(row["conditional_ratio"] is not None for row in report["results"]))

    def test_interrupted_parent_preserves_leaf_costs_without_promoting_them_before_seal(self):
        from src.measured_analysis import load_measured_campaign_evidence, analyze_verified_evidence
        from src.measured_comparison import run_measured_comparison, verify_role_slot
        from src.run_store import strict_json, digest
        from tests.test_measured_campaign_v9 import fixture

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory, payload = fixture(root)
            run_id = payload["entries"][0]["run_id"]
            output = root / "out" / "runs" / run_id
            with patch("src.measured_comparison._finalize_methods", side_effect=KeyboardInterrupt("after all leaves")):
                with self.assertRaises(KeyboardInterrupt):
                    run_measured_comparison(root / "plan.json", output,
                        inventory_path=inventory, inventory_run_id=run_id)
            observations = {path: path.read_bytes() for path in (output / "observations").glob("*/result.json")}
            self.assertEqual(len(observations), 5)
            evidence = load_measured_campaign_evidence(inventory, root / "out")
            slot = evidence.payload()["slots"][0]
            self.assertEqual(slot["archive_status"], "unsealed")
            self.assertTrue(all(row["outcome"] == "unsealed_parent" for row in slot["methods"].values()))
            self.assertTrue(all(row["observed_wall_ns"] > 0 and row["wall_ns"] is None
                                for row in slot["methods"].values()))
            self.assertTrue(all(row["conditional_ratio"] is None
                                for row in analyze_verified_evidence(evidence)["results"]))
            result = run_measured_comparison(root / "plan.json", output,
                inventory_path=inventory, inventory_run_id=run_id)
            self.assertEqual(result["outcome"], {"status": "complete"})
            for path, original in observations.items():
                self.assertEqual(path.read_bytes(), original)
                receipt = strict_json(original)
                self.assertEqual(len(list(path.parent.glob("attempt-*"))), 1)
                role = path.parent.name
                row = result["setup"] if role == "setup" else result["methods"][role]
                self.assertEqual(row["complete_wall_time_ns"], receipt["complete_transaction_wall_ns"])
                bindings = dict(root=output, plan_sha256=result["plan_sha256"],
                    manifest_path=root / "run.json", manifest_sha256=digest((root / "run.json").read_bytes()), role=role)
                verify_role_slot(row, **bindings)
                for changed in (dict(bindings, root=root / "other-parent"),
                                dict(bindings, plan_sha256="0" * 64),
                                dict(bindings, manifest_sha256="0" * 64)):
                    with self.assertRaisesRegex(ValueError, "parent"):
                        verify_role_slot(row, **changed)


class AdversarialDiagnosticTimingTests(unittest.TestCase):
    @staticmethod
    def records():
        from src.diagnostic_breakdown import CLOCK
        observer = {
            "observer_clock": {"clock": CLOCK, "start_ns": 100, "end_ns": 200, "wall_ns": 100},
            "observed_wall_ns": 100, "outcome": {"status": "complete"},
            "adopted_cleanup_windows": [],
            "timing_detail_spans": [dict(name=name, start_offset_ns=start, end_offset_ns=end, wall_ns=end-start)
                for name, start, end in (("controller_preparation", 0, 10),
                    ("worker_execution_until_cleanup", 10, 90), ("ordinary_process_cleanup", 90, 95),
                    ("output_validation", 95, 100))],
        }
        def metric(start, end):
            return {"wall_time_ns": end-start, "timing_window": {
                "clock": CLOCK, "start_ns": start, "end_ns": end, "wall_ns": end-start}}
        child = {"execution_mode": "diagnostic", "outcome": {"status": "complete"},
            "service_telemetry": {"instrumented": True, "timing_clock": CLOCK,
                "timing_windows_omitted": 0, "timing_windows": [{"start_ns": 120, "end_ns": 140, "wall_ns": 20}],
                "timings": {"factor_rounding": {"exclusive_ns": 5, "calls": 1},
                    "proof_verification": {"exclusive_ns": 15, "calls": 1}}, "total_exclusive_ns": 20},
            "preflight": {"loading_measurement": metric(112, 118), "chart_construction_measurement": metric(142, 148)}}
        return observer, child

    def test_exact_total_with_unclassified_work_does_not_claim_complete_named_attribution(self):
        from src.diagnostic_breakdown import decompose_records
        result = decompose_records(*self.records())
        self.assertEqual(result["accounting_sum_ns"], 100)
        self.assertEqual(result["residual_ns"], 48)
        self.assertEqual(result["categories_ns"]["proof_verification"], 15)
        self.assertEqual(result["categories_ns"]["factorization_rounding"], 5)
        self.assertFalse(result["named_attribution_complete"])
        self.assertFalse(result["verified_artifacts"])

    def test_nested_preflight_and_service_root_windows_cannot_be_counted_twice(self):
        from src.diagnostic_breakdown import decompose_records
        observer, child = self.records()
        metric = child["preflight"]["loading_measurement"]
        metric["timing_window"].update(start_ns=125, end_ns=131)
        with self.assertRaisesRegex(ValueError, "overlap"):
            decompose_records(observer, child)

    def test_omitted_windows_leave_service_cost_unclassified(self):
        from src.diagnostic_breakdown import decompose_records
        observer, child = self.records()
        child["service_telemetry"]["timing_windows_omitted"] = 1
        result = decompose_records(observer, child)
        self.assertEqual(result["accounting_sum_ns"], 100)
        self.assertEqual(result["residual_ns"], 68)
        self.assertEqual(result["categories_ns"]["proof_verification"], 0)
        self.assertFalse(result["named_attribution_complete"])
        self.assertTrue(result["unavailable_components"])

    def test_failed_observer_retains_diagnostics_without_complete_attribution_claim(self):
        from src.diagnostic_breakdown import decompose_records
        observer, child = self.records()
        observer["outcome"]["status"] = "incomplete"
        result = decompose_records(observer, child)
        self.assertEqual(result["accounting_sum_ns"], 100)
        self.assertEqual(result["categories_ns"]["proof_verification"], 15)
        self.assertFalse(result["named_attribution_complete"])
        self.assertEqual(result["status"], "partial")


if __name__ == "__main__":
    unittest.main()
