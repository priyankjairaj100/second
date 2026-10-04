"""Software fixtures verify analysis rules. These are not benchmark observations."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from src.result_analysis import AnalysisError, analyze_runs, lifetime_costs, projected_break_even
from scripts.summarize_results import main


def record(root="r0", request="q0", repeat=0, baseline=200, repair=100):
    def arm(value):
        return {"status": "complete", "wall_time_ns": value, "complete_wall_time_ns": value,
                "exact_state_equal": True, "exact_model_equal": True}
    return {"schema": "calibration-experiment-v1", "configuration_id": "software_fixture",
            "phase": "software_test", "cache_mode": "fixture", "root_id": root,
            "request_id": request, "repeat_index": repeat, "status": "complete",
            "service_boundary": "fixture_boundary", "target_manifest_sha256": "a" * 64,
            "protocol_sha256": "b" * 64, "planned_methods": ["indexed_fresh", "repair"],
            "methods": {"indexed_fresh": arm(baseline), "repair": arm(repair)}}


class AnalysisTests(unittest.TestCase):
    def test_roots_not_repeats_control_estimate_and_interval(self):
        rows = [record("r0", repeat=i, baseline=400) for i in range(9)] + [record("r1", baseline=100)]
        result = analyze_runs(rows, draws=200)["strata"][0]
        self.assertEqual(result["independent_root_count"], 2)
        self.assertAlmostEqual(result["conditional_ratio"]["estimate"], 2.0)
        one_root = analyze_runs(rows[:-1], draws=200)["strata"][0]
        self.assertIsNone(one_root["conditional_ratio"]["root_interval"])

    def test_failures_keep_denominator_and_leave_conditional_ratio(self):
        good, failed = record("r0"), record("r1")
        failed["status"] = "failed"
        failed["methods"]["repair"] = {"status": "failed", "failure_kind": "timeout", "wall_time_ns": 300}
        result = analyze_runs([good, failed], draws=100)["strata"][0]
        self.assertEqual(result["methods"]["repair"]["outcomes"], {"exact_complete": 1, "timeout": 1})
        self.assertEqual(result["paired_request_outcomes"]["baseline_only_exact_complete"], 1)
        self.assertEqual(result["conditional_ratio"]["eligible_roots"], 1)
        self.assertEqual(result["methods"]["repair"]["observed_elapsed_ns_sum"], 400)

    def test_plan_materializes_missing_attempt_and_blocks_confirmation_without_plan(self):
        row = record()
        row["phase"] = "confirmation"
        planned = copy.deepcopy(row)
        missing = copy.deepcopy(row)
        missing["root_id"] = "r1"
        with self.assertRaises(AnalysisError):
            analyze_runs([row])
        result = analyze_runs([row], planned_runs=[planned, missing], draws=100)["strata"][0]
        self.assertEqual(result["planned_attempt_count"], 2)
        self.assertEqual(result["methods"]["repair"]["outcomes"]["missing_run"], 1)
        self.assertEqual(result["paired_request_outcomes"]["neither_exact_complete"], 1)

    def test_one_failed_repeat_removes_whole_request_from_ratio(self):
        a, b = record(repeat=0), record(repeat=1)
        b["methods"]["repair"]["exact_model_equal"] = False
        result = analyze_runs([a, b])["strata"][0]
        self.assertIsNone(result["conditional_ratio"]["estimate"])
        self.assertEqual(result["methods"]["repair"]["outcomes"]["mismatch"], 1)

    def test_incomplete_exactness_is_not_success(self):
        row = record()
        del row["methods"]["repair"]["exact_state_equal"]
        result = analyze_runs([row])["strata"][0]
        self.assertEqual(result["methods"]["repair"]["outcomes"], {"not_verified": 1})

    def test_duplicate_unplanned_mixed_targets_and_bad_times_reject(self):
        with self.assertRaises(AnalysisError):
            analyze_runs([record(), record()])
        with self.assertRaises(AnalysisError):
            analyze_runs([record()], planned_runs=[])
        different = record("r1")
        different["target_manifest_sha256"] = "c" * 64
        with self.assertRaises(AnalysisError):
            analyze_runs([record(), different])
        for value in (-1, True, float("nan"), "100"):
            row = record()
            row["methods"]["repair"]["wall_time_ns"] = value
            with self.assertRaises(AnalysisError):
                analyze_runs([row])

    def test_bootstrap_is_deterministic_and_validated(self):
        rows = [record("r0"), record("r1", baseline=300)]
        self.assertEqual(analyze_runs(rows, draws=100), analyze_runs(reversed(rows), draws=100))
        with self.assertRaises(AnalysisError):
            analyze_runs([], draws=True)

    def test_lifetime_crossing_can_reverse(self):
        result = lifetime_costs(100, [(100, 40), (100, 40), (100, 200)])
        self.assertEqual(result["cumulative_net_savings_ns"], [-40, 20, -80])
        self.assertEqual(result["first_observed_nonnegative_request"], 2)
        self.assertEqual(projected_break_even(100, 60), 2)
        self.assertIsNone(projected_break_even(100, -1))

    def test_cli_emits_traceable_deterministic_tables(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            source = directory / "fixture.json"
            source.write_text(json.dumps(record()), encoding="utf-8")
            output = directory / "analysis"
            main([str(source), "--output", str(output), "--bootstrap-draws", "20"])
            first = (output / "summary.json").read_bytes()
            main([str(source), "--output", str(output), "--bootstrap-draws", "20"])
            self.assertEqual(first, (output / "summary.json").read_bytes())
            self.assertTrue((output / "outcomes.csv").exists())
            self.assertTrue((output / "paired_requests.csv").exists())
            self.assertIn("input_sha256", json.loads(first))


if __name__ == "__main__":
    unittest.main()
