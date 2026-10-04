"""Verified-artifact bridge and actual diagnostic correctness fixtures only."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from src.feasibility_archive import (derive_complete_group_coverage,
    assemble_feasibility_evidence, evaluate_archive_feasibility, _resource_snapshots)
from src.feasibility_decision import EvidenceError
from src.repair_service import Record
from src.run_store import canonical_json, digest, strict_json
from src.service_telemetry import DiagnosticLimits, ServiceTelemetry
from tests import test_aggregate_response_service as aggregate_fixture
from tests.test_feasibility_decision_v9 import fixture


def combined_fixture(root):
    """One actual frozen inventory/protocol with two explicitly different profiles."""
    from tests.test_measured_sequence_v9 import fixture as sequence_fixture
    from src.measured_sequence import build_measured_sequence_plan, build_measured_sequence_campaign
    plan_path, path, manifest = sequence_fixture(root,
        requests=[{"request_id": "one", "deleted_ids": ["a"]}], quality=True)
    plan, inventory = strict_json(plan_path.read_bytes()), strict_json(path.read_bytes())
    diagnostic = deepcopy(manifest)
    diagnostic["configuration_id"] += "-diagnostic"
    diagnostic_plan = build_measured_sequence_plan(manifest_path="sequence-diagnostic.json", manifest=diagnostic,
        target_manifest_sha256=plan["target_manifest_sha256"], worker_limits=plan["worker_limits"],
        sources=plan["source_sha256"], method_order=plan["method_order"],
        preparation_order=plan["preparation_order"], execution_mode="diagnostic", quality=False)
    runs = [dict(run_id="run0", manifest_path="sequence0.json", manifest=manifest,
        target_manifest_sha256=plan["target_manifest_sha256"], plan_path="plan.json", plan=plan),
        dict(run_id="run1", manifest_path="sequence-diagnostic.json", manifest=diagnostic,
        target_manifest_sha256=diagnostic_plan["target_manifest_sha256"],
        plan_path="plan-diagnostic.json", plan=diagnostic_plan)]
    combined = build_measured_sequence_campaign(campaign_id="combined-software-fixture", protocol_path="protocol.json",
        workloads=inventory["ordered_inventory"]["workloads"], runs=runs,
        worker_limits=plan["worker_limits"], sources=plan["source_sha256"])
    path.write_bytes(canonical_json(combined))
    protocol = strict_json((root/"protocol.json").read_bytes())
    protocol["planned_inventory_sha256"] = digest(path.read_bytes())
    (root/"protocol.json").write_bytes(canonical_json(protocol))
    for run in runs:
        run["manifest"]["protocol"]["sha256"] = digest(canonical_json(protocol))
        (root/run["manifest_path"]).write_bytes(canonical_json(run["manifest"]))
        (root/run["plan_path"]).write_bytes(canonical_json(run["plan"]))
    return path


def diagnostic_row(*, full_replay=False, limits=None):
    helper = aggregate_fixture.AggregateServiceTests()
    service, _, _, _ = helper.build(groups=16 if full_replay else 1)
    records = [Record("r"+str(i), b"[1,1]") for i in range(20)] if full_replay else helper.records()[:2]
    original = service.fresh(records).state
    collector = ServiceTelemetry(diagnostic_limits=limits)
    source = {r.record_id: r for r in records[1:]}.__getitem__
    result = service.repair(original, records[:1], source, mode="full_replay" if full_replay else "certified", telemetry=collector)
    return {"target_graph": {"stage_order": [s.stage_id for s in service.job.stages],
                "parents": {s.stage_id: list(s.dependencies) for s in service.job.stages}},
        "record_groups": {r.record_id: str(r.group_id) for r in result.state.records},
        "record_ids": list(result.state.retained_ids),
        "source_sha256": {"src/aggregate_response_service.py": digest(Path("src/aggregate_response_service.py").read_bytes())},
        "service_telemetry": collector.payload(), "ledger": dict(result.ledger.as_mapping()),
        "stage_audits": [{"stage_id": s.stage_id, "route": s.route, "replayed_groups": list(s.replayed_groups)} for s in result.stages]}


class FeasibilityArchiveTests(unittest.TestCase):
    def test_actual_complete_replay_audit_recovers_groups_beyond_first_last_samples(self):
        row = diagnostic_row(full_replay=True)
        groups = derive_complete_group_coverage(row)
        self.assertGreater(len(row["stage_audits"][0]["replayed_groups"]), 2)
        self.assertEqual(sum(g["retained_target_feature_evaluations"] for g in groups), 38)
        self.assertTrue(all(g["retained_target_feature_evaluations"] > 0 for g in groups))
        zero = derive_complete_group_coverage(diagnostic_row())
        self.assertTrue(all(g["retained_target_feature_evaluations"] == 0 for g in zero))

    def test_omitted_stage_overflow_and_counter_disagreement_never_become_zero(self):
        row = diagnostic_row(limits=DiagnosticLimits(max_stage_records=1))
        with self.assertRaises(EvidenceError):
            derive_complete_group_coverage(row)
        for change in (
            lambda r: r["service_telemetry"]["certificate_funnel"]["counters"].update(counter_values_saturated=1),
            lambda r: r["stage_audits"][0]["replayed_groups"].pop(),
            lambda r: r["service_telemetry"]["certificate_funnel"]["stages"][0]["dispositions"].update(__other__=1),
            lambda r: r["ledger"].update(retained_replay_evaluator_calls=0)):
            row = diagnostic_row(full_replay=True); change(row)
            with self.assertRaises(EvidenceError):
                derive_complete_group_coverage(row)

    def test_plain_json_cannot_enter_public_archive_bridge(self):
        policy, _ = fixture()
        result = evaluate_archive_feasibility(policy, {"archive_verified": True})
        self.assertFalse(result["conditions_satisfied"])
        self.assertFalse(result["measured_sequence_archive_verified"])
        self.assertFalse(result["empirical_attainment_established"])

    def test_resource_snapshot_reconciliation_never_discards_later_charge_or_unknown_work(self):
        policy, _ = fixture()
        ledger = {"status": "verified", "path": "/budget/ledger.json", "binding_sha256": "a"*64,
            "ledger_sha256": "b"*64, "attempts": {"unsettled": {}},
            "reserved_unknown_attempts": 1, "over_cap": {"feasibility": False},
            "phase_cpu_seconds": {"feasibility": 10800}, "charged_cpu_seconds": {"feasibility": 900},
            "linked_archived_attempt_ids": [], "attempts_without_worker_in_this_archive": ["unsettled"]}
        storage = {"status": "verified_at_read", "root": "/archive", "files": {}, "workers": []}
        first = {"phase_budget_snapshot": ledger, "archive_storage_snapshot": storage}
        missing, failures = [], []
        snapshots = _resource_snapshots([first, deepcopy(first)], policy, {}, missing, failures)
        self.assertEqual(len(snapshots["phase_budget_snapshots"]), 1)
        self.assertIn("unsettled_protocol_reservations_remain_fully_charged", missing)
        self.assertIn("protocol_attempt_workers_outside_supplied_archives", missing)
        second = deepcopy(first)
        second["phase_budget_snapshot"]["charged_cpu_seconds"]["feasibility"] = 901
        with self.assertRaisesRegex(EvidenceError, "ledger changed"):
            _resource_snapshots([first, second], policy, {}, [], [])
        second = deepcopy(first); second["archive_storage_snapshot"]["files"]["unknown"] = {"bytes": 1}
        with self.assertRaisesRegex(EvidenceError, "storage changed"):
            _resource_snapshots([first, second], policy, {}, [], [])
        large = deepcopy(first)
        large["archive_storage_snapshot"]["files"]["oversized"] = {"bytes": policy["resources"]["artifact_file_size_bytes_maximum"]+1}
        failures = []; _resource_snapshots([large], policy, {}, [], failures)
        self.assertTrue(failures)

    def test_actual_measured_archive_yields_facts_and_precise_missing_premises(self):
        from tests.test_measured_sequence_v9 import fixture as sequence_fixture
        from src.measured_sequence import run_measured_sequence_campaign
        from src.measured_analysis import load_measured_sequence_evidence
        policy, _ = fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, inventory, _ = sequence_fixture(root, requests=[{"request_id": "one", "deleted_ids": ["a"]}], quality=True)
            completed = run_measured_sequence_campaign(inventory, root/"out")
            self.assertEqual(completed["outcome"], "complete", completed)
            verified = load_measured_sequence_evidence(inventory, root/"out")
            assembled = assemble_feasibility_evidence(policy, verified)
            self.assertEqual(assembled["roots"][0]["record_token_counts"], {"a": 2, "b": 2, "c": 2})
            self.assertTrue(assembled["roots"][0]["requests"][0]["quality"])
            self.assertTrue(assembled["observed_workers"])
            self.assertTrue(assembled["resource_accounting"]["phase_budget_snapshots"])
            self.assertTrue(assembled["resource_accounting"]["archive_storage_snapshots"])
            self.assertIn("root0:matched_diagnostic_sequence_missing", assembled["missing_evidence"])
            result = evaluate_archive_feasibility(policy, verified)
            self.assertEqual(result["decision"], "inconclusive_missing_required_evidence")
            self.assertFalse(result["conditions_satisfied"])
            self.assertTrue(result["measured_sequence_archive_verified"])
            self.assertFalse(result["empirical_attainment_established"])

    def test_combined_actual_profiles_pair_coverage_and_cli_keeps_archives_immutable(self):
        from src.measured_sequence import run_measured_sequence_campaign
        from src.measured_analysis import load_measured_sequence_evidence
        from scripts.evaluate_feasibility import main
        policy, _ = fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); inventory = combined_fixture(root)
            result = run_measured_sequence_campaign(inventory, root/"out")
            self.assertEqual(result["outcome"], "complete", result)
            clean = load_measured_sequence_evidence(inventory, root/"out", execution_mode="clean")
            diagnostic = load_measured_sequence_evidence(inventory, root/"out", execution_mode="diagnostic")
            self.assertEqual(len(clean.payload()["slots"]), 1)
            self.assertEqual(len(diagnostic.payload()["slots"]), 1)
            self.assertEqual(clean.payload()["protocol_sha256"], diagnostic.payload()["protocol_sha256"])
            assembled = assemble_feasibility_evidence(policy, clean, diagnostic)
            request = assembled["roots"][0]["requests"][0]
            self.assertIsNotNone(request["coverage_groups"], assembled["missing_evidence"])
            self.assertTrue(request["quality"])
            self.assertFalse(any("matched_diagnostic" in item or "parity_unavailable" in item for item in assembled["missing_evidence"]))
            self.assertEqual(len(assembled["resource_accounting"]["archive_storage_snapshots"]), 1)
            snapshot = assembled["resource_accounting"]["phase_budget_snapshots"][0]
            self.assertEqual(snapshot["status"], "verified")
            self.assertEqual(set(assembled["resource_accounting"]["all_supplied_archived_worker_ids"]),
                {row["worker_id"] for row in assembled["observed_workers"]})
            args = ["--clean-inventory", str(inventory), "--clean-output", str(root/"out"),
                "--diagnostic-inventory", str(inventory), "--diagnostic-output", str(root/"out")]
            self.assertEqual(main(args+["--output", str(root/"decision.json")]), 0)
            report = strict_json((root/"decision.json").read_bytes())
            self.assertFalse(report["empirical_attainment_established"])
            self.assertIn("scientific_workload_provenance_not_established_by_archives", report["missing_evidence"])
            before = digest((root/"out"/"result.json").read_bytes())
            with self.assertRaisesRegex(ValueError, "outside immutable"):
                main(args+["--output", str(root/"alias"/".."/"out"/"forbidden.json")])
            self.assertFalse((root/"out"/"forbidden.json").exists())
            self.assertEqual(digest((root/"out"/"result.json").read_bytes()), before)


if __name__ == "__main__":
    unittest.main()
