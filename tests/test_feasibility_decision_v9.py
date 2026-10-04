"""Decision-engine correctness fixtures; none is empirical feasibility evidence."""
from copy import deepcopy
from pathlib import Path
import unittest

from src.feasibility_decision import (BOUNDARY, FRESH_CACHE, METHODS, ORACLES,
    POLICY_PAYLOAD_SHA256, SCHEMA, EvidenceError, evaluate_feasibility,
    evaluate_verified_feasibility, lifetime_break_even, log_ratio_enclosure, remaining_cost_decision)
from src.run_store import canonical_json, digest, strict_json


def sha(value):
    return digest(str(value).encode())


def fixture():
    policy = strict_json((Path(__file__).resolve().parents[1]/"configs/feasibility_gates_v1.json").read_bytes())
    evidence = {"schema": SCHEMA, "policy_payload_sha256": POLICY_PAYLOAD_SHA256,
        "target_manifest_sha256": sha("target"), "protocol_sha256": sha("protocol"),
        "configuration_sha256": sha("configuration_without_profile"),
        "inventory_sha256": sha("inventory"), "source_sha256": {"fixture": sha("source")},
        "evidence_kind": "software_test",
        "provenance": {"producer_sha256": sha("producer"), "archive_validation": "verified",
            "scientific_provenance": "software_fixture", "artifacts": [
                {"role": role, "sha256": sha(role)} for role in
                ("measured_lifetime", "coverage", "quality", "resource_ledger", "workload_provenance", "exactness")]},
        "target": {"stage_order": ["a", "b", "c"], "parents": {"a": [], "b": ["a"], "c": ["b"]}},
        "measurement_contract": {"boundary": BOUNDARY, "required_costs": policy["cost"]["required_costs"],
            "external_oracle_accounting": "separate_symmetric", "observer_receipt_excluded": True,
            "method_costs_disjoint": True}, "roots": [],
        "resources": {"planned_worker_ids": [], "workers": [], "complete": True,
            "unsettled_reservations": 0, "phase_cpu_charge_seconds": 0, "phase_ledger_sha256": sha("ledger")}}

    def clock(method, ids, label, wall_ns):
        evidence["resources"]["planned_worker_ids"].append(label)
        evidence["resources"]["workers"].append({"worker_id": label, "receipt_sha256": sha(label+"worker"),
            "status": "complete", "wall_ns": wall_ns, "cpu_ns": 1_000_000,
            "wall_limit_seconds": 900, "cpu_limit_seconds": 900,
            "file_size_limit_bytes": 512*1024**2,
            "address_space_limit_bytes": 6*1024**3, "peak_rss_bytes": 102400,
            "max_artifact_bytes": 10000})
        evidence["resources"]["phase_cpu_charge_seconds"] += 1
        return {"status": "complete", "wall_ns": wall_ns, "receipt_sha256": sha(label),
            "output_contract": "model_only" if method == "model_only_fresh" else "canonical_state",
            "boundary": BOUNDARY, "cache_mode": FRESH_CACHE, "profiler_active": False,
            "execution_mode": "clean", "instrumentation_disabled": True,
            "worker_id": label, "worker_receipt_sha256": sha(label+"worker"),
            "new_latency_observation": True, "source_inputs_unchanged": True,
            "target_manifest_sha256": evidence["target_manifest_sha256"],
            "configuration_sha256": evidence["configuration_sha256"],
            "retained_ids_sha256": digest(canonical_json(sorted(ids)))}

    for ri in range(2):
        rid = "root"+str(ri)
        ids = [rid+"-"+str(i) for i in range(8)]
        initial = {stage: sha(rid+stage+"initial") for stage in ("a", "b", "c")}
        prep = clock("repair", ids, rid+"-prep-index", 4_000_000)
        root = {"root_id": rid, "records": [{"record_id": key, "tokens": 32} for key in ids],
            "record_groups": {stage: {key: "g"+str(i % 2) for i, key in enumerate(ids)} for stage in initial},
            "initial_stage_codes": initial, "preparation": {"repair": prep, "indexed_fresh": deepcopy(prep),
                "model_only_fresh": clock("model_only_fresh", ids, rid+"-prep-model", 1_000_000)},
            "planned_request_ids": ["q0", "q1", "q2"], "requests": []}
        retained = set(ids)
        previous = initial
        for qi in range(3):
            qid = "q"+str(qi); retained.remove(ids[qi])
            current = dict(previous); current["b" if qi == 1 else "a"] = sha(rid+qid)
            quality = {"heldout_sha256": sha(rid+"heldout"), "evaluator_sha256": sha("eval"),
                "scored_tokens": 10, "nll_sum": 20.0}
            diagnostic = clock("repair", retained, rid+qid+"diagnostic", 1_000_000)
            replicate = {"receipt_sha256": diagnostic["receipt_sha256"],
                "worker_id": diagnostic["worker_id"], "worker_receipt_sha256": diagnostic["worker_receipt_sha256"],
                "target_manifest_sha256": evidence["target_manifest_sha256"],
                "configuration_sha256": evidence["configuration_sha256"],
                "source_bindings_sha256": digest(canonical_json(evidence["source_sha256"])),
                "root_id": rid, "request_id": qid,
                "retained_ids_sha256": digest(canonical_json(sorted(retained))),
                "predecessor_stage_map_sha256": digest(canonical_json(previous)),
                "stage_codes": dict(current), "canonical_state_sha256": sha(rid+qid+"state"),
                "execution_mode": "diagnostic"}
            request = {"request_id": qid, "deleted_ids": [ids[qi]],
                "models": {method: dict(current) for method in ORACLES},
                "states": {method: sha(rid+qid+"state") for method in ("repair", "indexed_fresh", "direct_fresh")},
                "coverage": {"complete": True, "omitted_events": 0, "capped": False,
                    "counter_saturated": False, "replicate": replicate, "groups": [{"stage_id": stage, "group_id": group,
                        "retained_target_feature_evaluations": 0} for stage in initial for group in ("g0", "g1")]},
                "quality": {"base": quality, "retained_fresh": deepcopy(quality),
                    "binding": {"receipt_sha256": diagnostic["receipt_sha256"],
                        "worker_id": diagnostic["worker_id"], "worker_receipt_sha256": diagnostic["worker_receipt_sha256"],
                        "target_manifest_sha256": evidence["target_manifest_sha256"], "root_id": rid,
                        "request_id": qid, "retained_model_stage_map_sha256": digest(canonical_json(current))}},
                "timings": {method: clock(method, retained, rid+qid+method,
                    {"repair": 1_000_000, "indexed_fresh": 1_000_000, "model_only_fresh": 3_000_000}[method])
                    for method in METHODS}}
            root["requests"].append(request); previous = current
        evidence["roots"].append(root)
    return policy, evidence


def issued_fixture(evidence):
    """White-box adapter fixture; this does not verify or represent real files."""
    from src import measured_analysis as analysis
    from src.instrumentation import instrumentation_scope, instrumentation_state
    with instrumentation_scope("clean"):
        clean = instrumentation_state()
    resources = {row["worker_id"]: row for row in evidence["resources"]["workers"]}

    def role(clock, codes, state, ids):
        resource = resources[clock["worker_id"]]
        return {"outcome": "exact_complete", "exact_model": True,
            "exact_state": True if state is not None else None, "wall_ns": clock["wall_ns"],
            "receipt_sha256": clock["receipt_sha256"], "output_contract": clock["output_contract"],
            "boundary": clock["boundary"], "cache_mode": clock["cache_mode"], "execution_mode": "clean",
            "target_manifest_sha256": evidence["target_manifest_sha256"],
            "source_sha256": evidence["source_sha256"], "instrumentation_state": clean,
            "observer_instrumentation_state": clean, "worker_id": clock["worker_id"],
            "worker_receipt_sha256": clock["worker_receipt_sha256"],
            "worker_resource_usage": {"total_cpu_ns": resource["cpu_ns"], "max_rss_kib": resource["peak_rss_bytes"]//1024},
            "worker_outcome": {"elapsed_wall_ns": resource["wall_ns"]},
            "worker_limits": {"wall_seconds": resource["wall_limit_seconds"], "cpu_seconds": resource["cpu_limit_seconds"],
                "file_size_bytes": resource["file_size_limit_bytes"], "address_space_bytes": resource["address_space_limit_bytes"]},
            "max_artifact_bytes": resource["max_artifact_bytes"], "record_ids": sorted(ids),
            "retained_ids_sha256": digest(canonical_json(sorted(ids))), "stage_code_sha256": codes,
            "state_sha256": state}

    slots = []
    for root in evidence["roots"]:
        retained = {r["record_id"] for r in root["records"]}
        prep = {method: role(root["preparation"][method], root["initial_stage_codes"],
            sha("initial-state") if method == "repair" else None, retained) for method in ("repair", "model_only_fresh")}
        steps = []
        for request in root["requests"]:
            retained -= set(request["deleted_ids"])
            rows = {method: role(request["timings"][method], request["models"][method],
                request["states"].get(method), retained) for method in METHODS}
            oracle = deepcopy(request["timings"]["repair"])
            oracle.update(worker_id=oracle["worker_id"]+"oracle", receipt_sha256=sha(oracle["receipt_sha256"]+"oracle"),
                worker_receipt_sha256=sha(oracle["worker_receipt_sha256"]+"oracle"))
            resource = deepcopy(resources[request["timings"]["repair"]["worker_id"]])
            resource.update(worker_id=oracle["worker_id"], receipt_sha256=oracle["worker_receipt_sha256"])
            evidence["resources"]["workers"].append(resource)
            evidence["resources"]["planned_worker_ids"].append(resource["worker_id"])
            evidence["resources"]["phase_cpu_charge_seconds"] += 1
            resources[resource["worker_id"]] = resource
            rows["direct_fresh"] = role(oracle, request["models"]["direct_fresh"], request["states"]["direct_fresh"], retained)
            steps.append({"request_id": request["request_id"], "newly_deleted_ids": request["deleted_ids"], "methods": rows})
        slot = {"root_id": root["root_id"], "run_id": root["root_id"]+"-run", "configuration_id": "fixture",
            "request_id": "sequence", "phase": "software_test", "repeat_index": 0,
            "execution_mode": "clean", "archive_status": "sealed", "preparation": prep, "steps": steps,
            **{key: evidence[key] for key in ("target_manifest_sha256", "configuration_sha256", "source_sha256", "protocol_sha256")}}
        slot["methods"] = {method: {"outcome": "exact_complete", "wall_ns": root["preparation"][method]["wall_ns"]+
            sum(request["timings"][method]["wall_ns"] for request in root["requests"])} for method in METHODS}
        slots.append(slot)
    payload = {"schema": "verified-measured-evidence-v1", "kind": "sequence_lifetime", "slots": slots,
        **{key: evidence[key] for key in ("inventory_sha256", "protocol_sha256")}}
    return analysis.VerifiedMeasuredEvidence(payload, _issuer=analysis._ISSUER)


class FeasibilityDecisionTests(unittest.TestCase):
    def test_conditional_success_does_not_create_empirical_or_solver_claim(self):
        policy, evidence = fixture(); original = deepcopy(evidence)
        result = evaluate_feasibility(policy, evidence)
        self.assertEqual(result["decision"], "conditional_promote_to_development", result)
        self.assertEqual(evidence, original)
        self.assertEqual(result["roots"][0]["coverage_denominator"], 10)
        self.assertEqual(result["roots"][0]["coverage_numerator"], 10)
        self.assertEqual(result["roots"][0]["lifetime_gain_ns"], 3_000_000)
        self.assertFalse(result["equal_information_cost_condition_all_roots"])
        for flag in ("empirical_attainment_established", "research_execution_authorized",
                "confirmation_authorized", "population_speedup_established", "deletion_exclusive_solver_claim_supported"):
            self.assertFalse(result[flag])

    def test_transitive_ancestors_and_feature_evaluations_determine_coverage(self):
        policy, evidence = fixture()
        for root in evidence["roots"]:
            for request in root["requests"]:
                for group in request["coverage"]["groups"]:
                    group["retained_target_feature_evaluations"] = 1
        result = evaluate_feasibility(policy, evidence)
        self.assertEqual(result["decision"], "redesign_certificate_or_narrow")
        self.assertEqual(result["roots"][0]["coverage_denominator"], 10)
        self.assertEqual(result["roots"][0]["coverage_numerator"], 0)
        # Source reads are deliberately absent: caches do not imply feature avoidance.

    def test_missing_capped_saturated_and_omitted_counts_are_inconclusive(self):
        for field, value in (("complete", False), ("capped", True), ("counter_saturated", True), ("omitted_events", 1)):
            with self.subTest(field=field):
                policy, evidence = fixture(); evidence["roots"][0]["requests"][0]["coverage"][field] = value
                result = evaluate_feasibility(policy, evidence)
                self.assertFalse(result["conditions_satisfied"])
                self.assertEqual(result["decision"], "inconclusive_missing_required_evidence")
        policy, evidence = fixture(); evidence["roots"][0]["requests"][0]["coverage"]["groups"].pop()
        self.assertEqual(evaluate_feasibility(policy, evidence)["decision"], "inconclusive_missing_required_evidence")

    def test_unexpected_empty_duplicate_boolean_and_negative_group_counts_rejected(self):
        for change in (lambda rows: rows.append(deepcopy(rows[0])),
                lambda rows: rows[0].update(group_id="empty"),
                lambda rows: rows[0].update(retained_target_feature_evaluations=True),
                lambda rows: rows[0].update(retained_target_feature_evaluations=-1)):
            policy, evidence = fixture(); change(evidence["roots"][0]["requests"][0]["coverage"]["groups"])
            self.assertEqual(evaluate_feasibility(policy, evidence)["decision"], "inconclusive_invalid_evidence")

    def test_known_mismatch_precedes_missing_evidence(self):
        policy, evidence = fixture(); request = evidence["roots"][0]["requests"][0]
        request["models"]["direct_fresh"]["b"] = sha("wrong")
        request["quality"]["base"] = None
        result = evaluate_feasibility(policy, evidence)
        self.assertEqual(result["decision"], "stop_and_repair_implementation")
        self.assertTrue(result["mismatches"])

    def test_all_planned_roots_requests_stages_and_memberships_required(self):
        cases = (lambda e: e["roots"].pop(), lambda e: e["roots"][0]["requests"].pop(),
            lambda e: e["roots"][0]["requests"][1]["models"]["repair"].pop("c"),
            lambda e: e["roots"][0]["record_groups"]["b"].pop("root0-0"),
            lambda e: e["target"]["parents"].update(a=["c"]))
        for change in cases:
            policy, evidence = fixture(); change(evidence)
            self.assertFalse(evaluate_feasibility(policy, evidence)["conditions_satisfied"])

    def test_quality_checks_each_request_inputs_counts_and_nonfinite(self):
        for change in (lambda q: q.update(scored_tokens=0), lambda q: q.update(scored_tokens=11),
                lambda q: q.update(heldout_sha256=sha("different")),
                lambda q: q.update(evaluator_sha256=sha("different")), lambda q: q.update(nll_sum=float("inf"))):
            policy, evidence = fixture(); change(evidence["roots"][1]["requests"][2]["quality"]["retained_fresh"])
            self.assertFalse(evaluate_feasibility(policy, evidence)["conditions_satisfied"])
        policy, evidence = fixture(); evidence["roots"][1]["requests"][2]["quality"]["retained_fresh"]["nll_sum"] = 30.0
        self.assertEqual(evaluate_feasibility(policy, evidence)["decision"], "revise_quality_configuration_prospectively_or_narrow")
        lo, hi = log_ratio_enclosure()
        self.assertGreater(hi, lo)
        self.assertLess(hi-lo, 1/10**60)

    def test_nonpositive_preparation_and_wrong_model_only_original_membership_rejected(self):
        for change in (lambda p: p.update(wall_ns=0), lambda p: p.update(wall_ns=None),
                lambda p: p.update(retained_ids_sha256=sha("already-deleted"))):
            policy, evidence = fixture(); change(evidence["roots"][0]["preparation"]["model_only_fresh"])
            self.assertFalse(evaluate_feasibility(policy, evidence)["conditions_satisfied"])

    def test_every_root_needs_strict_complete_lifetime_gain(self):
        policy, evidence = fixture()
        for request in evidence["roots"][1]["requests"]:
            request["timings"]["repair"]["wall_ns"] = 4_000_000
        result = evaluate_feasibility(policy, evidence)
        self.assertEqual(result["decision"], "redesign_cost_or_narrow")
        self.assertEqual(result["lifetime_failure_roots"], ["root1"])

    def test_profiled_resumed_reused_or_wrong_contract_timings_cannot_pass(self):
        for field, value in (("profiler_active", True), ("new_latency_observation", False),
                ("execution_mode", "diagnostic"), ("instrumentation_disabled", False),
                ("cache_mode", "resumed_transaction_os_cache_uncontrolled"),
                ("output_contract", "comparison"), ("boundary", "service_only"),
                ("source_inputs_unchanged", False)):
            policy, evidence = fixture(); evidence["roots"][0]["requests"][0]["timings"]["repair"][field] = value
            self.assertFalse(evaluate_feasibility(policy, evidence)["conditions_satisfied"])
        policy, evidence = fixture()
        evidence["roots"][1]["requests"][0]["timings"]["repair"]["receipt_sha256"] = evidence["roots"][0]["requests"][0]["timings"]["repair"]["receipt_sha256"]
        self.assertEqual(evaluate_feasibility(policy, evidence)["decision"], "inconclusive_invalid_evidence")

    def test_resource_limits_unknown_workers_and_phase_debits(self):
        for field, value in (("wall_ns", 901*10**9), ("cpu_ns", 901*10**9),
                ("wall_limit_seconds", 10000), ("cpu_limit_seconds", 10000),
                ("file_size_limit_bytes", 513*1024**2),
                ("peak_rss_bytes", 7*1024**3), ("max_artifact_bytes", 513*1024**2),
                ("address_space_limit_bytes", 7*1024**3)):
            policy, evidence = fixture(); evidence["resources"]["workers"][0][field] = value
            if field == "wall_ns":
                evidence["roots"][0]["preparation"]["repair"]["wall_ns"] = value
                evidence["roots"][0]["preparation"]["indexed_fresh"]["wall_ns"] = value
            evidence["resources"]["phase_cpu_charge_seconds"] = 1000
            self.assertEqual(evaluate_feasibility(policy, evidence)["decision"], "redesign_resources_or_narrow")
        for change in (lambda r: r["workers"].pop(), lambda r: r.update(unsettled_reservations=1),
                lambda r: r["workers"][0].update(peak_rss_bytes=None)):
            policy, evidence = fixture(); change(evidence["resources"])
            self.assertEqual(evaluate_feasibility(policy, evidence)["decision"], "inconclusive_missing_required_evidence")
        policy, evidence = fixture(); evidence["resources"]["phase_cpu_charge_seconds"] = 10801
        self.assertEqual(evaluate_feasibility(policy, evidence)["decision"], "redesign_resources_or_narrow")

    def test_timing_workers_must_match_complete_bound_resource_inventory(self):
        policy, evidence = fixture()
        evidence["resources"]["planned_worker_ids"].pop()
        evidence["resources"]["workers"].pop()
        self.assertEqual(evaluate_feasibility(policy, evidence)["decision"], "inconclusive_missing_required_evidence")
        policy, evidence = fixture()
        evidence["roots"][0]["requests"][0]["timings"]["repair"]["worker_receipt_sha256"] = sha("wrong-worker")
        self.assertEqual(evaluate_feasibility(policy, evidence)["decision"], "inconclusive_invalid_evidence")
        policy, evidence = fixture(); evidence["resources"]["workers"][0]["wall_ns"] = 899_000_000_000
        self.assertEqual(evaluate_feasibility(policy, evidence)["decision"], "inconclusive_invalid_evidence")

    def test_diagnostic_replicate_requires_clean_code_state_and_input_parity(self):
        for field, value in (("root_id", "another-root"), ("request_id", "another-request"),
                ("retained_ids_sha256", sha("wrong-records")), ("configuration_sha256", sha("changed-chart")),
                ("source_bindings_sha256", sha("wrong-source")), ("predecessor_stage_map_sha256", sha("wrong-prefix")),
                ("canonical_state_sha256", sha("wrong-state")), ("execution_mode", "clean")):
            policy, evidence = fixture()
            evidence["roots"][0]["requests"][0]["coverage"]["replicate"][field] = value
            self.assertEqual(evaluate_feasibility(policy, evidence)["decision"], "inconclusive_missing_required_evidence")
        policy, evidence = fixture()
        evidence["roots"][0]["requests"][0]["coverage"]["replicate"]["stage_codes"]["a"] = sha("different-code")
        self.assertFalse(evaluate_feasibility(policy, evidence)["conditions_satisfied"])

    def test_policy_and_provenance_cannot_be_relaxed_by_json(self):
        policy, evidence = fixture(); policy["coverage"]["minimum_per_root"]["denominator"] = 100
        self.assertEqual(evaluate_feasibility(policy, evidence)["decision"], "inconclusive_invalid_evidence")
        policy, evidence = fixture(); evidence["evidence_kind"] = "research"
        self.assertEqual(evaluate_feasibility(policy, evidence)["decision"], "inconclusive_missing_required_evidence")
        evidence["provenance"]["scientific_provenance"] = "verified_real_workload"
        result = evaluate_feasibility(policy, evidence)
        self.assertTrue(result["conditions_satisfied"])
        self.assertFalse(result["empirical_attainment_established"])

    def test_artifact_adapter_requires_typed_evidence_and_exact_projection(self):
        policy, evidence = fixture()
        self.assertFalse(evaluate_verified_feasibility(policy, evidence, {"verified": True})["conditions_satisfied"])
        measured = issued_fixture(evidence)
        result = evaluate_verified_feasibility(policy, evidence, measured)
        self.assertTrue(result["conditions_satisfied"], result)
        self.assertTrue(result["measured_sequence_archive_verified"])
        self.assertFalse(result["supplement_archive_verification_performed"])
        self.assertFalse(result["empirical_attainment_established"])
        changed = deepcopy(evidence); changed["roots"][0]["requests"][0]["timings"]["repair"]["wall_ns"] += 1
        self.assertFalse(evaluate_verified_feasibility(policy, changed, measured)["conditions_satisfied"])
        changed = deepcopy(evidence); changed["resources"]["workers"][0]["peak_rss_bytes"] += 1024
        self.assertFalse(evaluate_verified_feasibility(policy, changed, measured)["conditions_satisfied"])

    def test_no_actual_ancestor_change_is_inconclusive_not_perfect_coverage(self):
        policy, evidence = fixture()
        for root in evidence["roots"]:
            for request in root["requests"]:
                current = deepcopy(root["initial_stage_codes"])
                request["models"] = {method: deepcopy(current) for method in ORACLES}
                request["coverage"]["replicate"]["stage_codes"] = deepcopy(current)
                request["coverage"]["replicate"]["predecessor_stage_map_sha256"] = digest(canonical_json(current))
                request["quality"]["binding"]["retained_model_stage_map_sha256"] = digest(canonical_json(current))
        result = evaluate_feasibility(policy, evidence)
        self.assertEqual(result["decision"], "inconclusive_mechanism_not_demonstrated")
        self.assertEqual(result["roots"][0]["coverage_denominator"], 0)

    def test_prefix_crossing_can_reverse_and_future_cost_stop_is_conditional(self):
        result = lifetime_break_even(10, 0, [(0, 11), (100, 0)])
        self.assertTrue(result["prefixes"][0]["strict_gain"])
        self.assertFalse(result["strict_gain"])
        self.assertEqual(remaining_cost_decision(5, [(0, 5)])["decision"], "strict_gain_impossible")
        self.assertEqual(remaining_cost_decision(5, [(6, 8)])["decision"], "strict_gain_guaranteed_if_all_other_assumptions_hold")
        self.assertEqual(remaining_cost_decision(5, [None])["decision"], "inconclusive_missing_future_bound")
        with self.assertRaises(EvidenceError):
            remaining_cost_decision(5, [(8, 6)])


if __name__ == "__main__":
    unittest.main()
