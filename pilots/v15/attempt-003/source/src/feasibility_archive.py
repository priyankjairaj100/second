"""Read-only assembly from loader-issued clean and diagnostic sequence evidence.

The current measured archives do not establish scientific provenance. This
bridge reports missing premises and consumes bounded protocol-ledger snapshots;
it never upgrades an assertion in supplied JSON into verified evidence.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy

from .feasibility_decision import (POLICY_PAYLOAD_SHA256, METHODS, ORACLES, NS,
    EvidenceError, _int, _ids, _q, _finite_score, log_ratio_enclosure)
from .run_store import canonical_json, digest


def _graph(value):
    if type(value) is not dict or set(value) != {"stage_order", "parents"}:
        raise EvidenceError("target_graph_not_exported")
    order = _ids(value["stage_order"], "stage ID")
    if not order or type(value["parents"]) is not dict or set(value["parents"]) != set(order):
        raise EvidenceError("incomplete_target_graph")
    ancestors = {}
    for stage in order:
        parents = _ids(value["parents"][stage], "parent stage")
        if any(parent not in ancestors for parent in parents):
            raise EvidenceError("invalid_target_graph_order")
        ancestors[stage] = set(parents)
        for parent in parents:
            ancestors[stage].update(ancestors[parent])
    return order, ancestors


def _group(value):
    if type(value) is int and value >= 0:
        return str(value)
    if type(value) is str and value:
        return value
    raise EvidenceError("invalid_group_identifier")


def derive_complete_group_coverage(row):
    """Derive evaluations only from completed source-bound response diagnostics.

    Full StageAudit replay membership is cross-checked against independent
    replay and actual target-call counters. First/last event samples alone are
    never treated as the complete replay list.
    """
    order, _ = _graph(row.get("target_graph"))
    groups = row.get("record_groups")
    if type(groups) is not dict or set(groups) != set(row.get("record_ids", ())):
        raise EvidenceError("complete_retained_group_membership_not_exported")
    if not any(key.endswith("aggregate_response_service.py") for key in row.get("source_sha256", {})):
        raise EvidenceError("response_service_source_binding_missing")
    counts = Counter(_group(value) for value in groups.values())
    telemetry = row.get("service_telemetry")
    if type(telemetry) is not dict or telemetry.get("instrumented") is not True:
        raise EvidenceError("detailed_diagnostic_funnel_unavailable")
    funnel = telemetry.get("certificate_funnel", {})
    if funnel.get("schema") != "certificate-funnel-v1":
        raise EvidenceError("unsupported_diagnostic_funnel")
    counters = funnel.get("counters")
    if type(counters) is not dict:
        raise EvidenceError("diagnostic_completeness_counters_missing")
    for name, value in counters.items():
        _int(value, "diagnostic counter")
        if name not in ("observations", "observations_recorded", "large_values_summarized") and value:
            raise EvidenceError("diagnostic_incomplete:" + name)
    if counters.get("observations", 0) != counters.get("observations_recorded", 0):
        raise EvidenceError("diagnostic_observation_count_mismatch")
    operations = [op for op in funnel.get("operations", []) if op.get("operation") == "repair"]
    if (len(operations) != 1 or operations[0].get("status") != "complete"
            or operations[0].get("produced_complete_model") is not True):
        raise EvidenceError("complete_repair_operation_not_observed")
    op_index = operations[0]["operation_index"]
    stages = [stage for stage in funnel.get("stages", []) if stage.get("operation_index") == op_index]
    if len(stages) != len(order) or {stage.get("stage_id") for stage in stages} != set(order):
        raise EvidenceError("complete_stage_funnel_not_observed")
    audits = row.get("stage_audits")
    if type(audits) is not list or len(audits) != len(order) or [a.get("stage_id") for a in audits] != order:
        raise EvidenceError("complete_ordered_replay_audit_not_exported")
    by_stage = {stage["stage_id"]: stage for stage in stages}
    result, evaluated_total = [], 0
    for audit in audits:
        stage = by_stage[audit["stage_id"]]
        if stage.get("status") != "complete" or stage.get("failure_type") is not None:
            raise EvidenceError("stage_did_not_complete")
        if stage.get("stage_id_sha256") != digest(stage["stage_id"].encode()):
            raise EvidenceError("truncated_or_inconsistent_stage_identity")
        dispositions, totals, events = stage.get("dispositions", {}), stage.get("totals", {}), stage.get("events", {})
        if "__other__" in dispositions or "__other__" in totals or "__other__" in events:
            raise EvidenceError("diagnostic_counter_overflow_bucket")
        for mapping in (dispositions, totals):
            if type(mapping) is not dict:
                raise EvidenceError("invalid_stage_counter_map")
            for value in mapping.values():
                _int(value, "stage counter")
        replayed = audit.get("replayed_groups")
        if type(replayed) is not list:
            raise EvidenceError("replay_membership_missing")
        replayed = [_group(group) for group in replayed]
        if len(set(replayed)) != len(replayed) or not set(replayed) <= set(counts):
            raise EvidenceError("invalid_replayed_group_membership")
        expected = sum(counts[group] for group in replayed)
        def event_count(name):
            value = events.get(name)
            return 0 if value is None else _int(value.get("count"), name)
        for name in ("stage_started", "stage_completed"):
            if event_count(name) != 1:
                raise EvidenceError("stage_boundary_event_missing_or_repeated")
        for name in ("group_replay_started", "group_replay_completed"):
            if event_count(name) != len(replayed):
                raise EvidenceError("replay_audit_and_event_count_disagree")
        for name in ("feature_evaluation_attempted", "feature_evaluation_completed"):
            if (event_count(name) != expected
                    or dispositions.get(name+":role=retained_replay_evaluator_calls", 0) != expected):
                raise EvidenceError("actual_target_feature_counter_disagrees")
        if event_count("feature_evaluation_failed") or totals.get("group_replay_completed:feature_evaluations", 0) != expected:
            raise EvidenceError("replay_feature_total_incomplete")
        completed = events["stage_completed"]["last"]
        started = events["stage_started"]["last"]
        if (completed.get("replayed_groups") != len(replayed) or completed.get("route") != audit.get("route")
                or started.get("retained_records") != len(groups) or started.get("groups") != len(counts)):
            raise EvidenceError("stage_summary_and_membership_disagree")
        evaluated_total += expected
        for group in sorted(counts):
            result.append({"stage_id": stage["stage_id"], "group_id": group,
                "retained_target_feature_evaluations": counts[group] if group in replayed else 0})
    ledger = row.get("ledger")
    if type(ledger) is not dict or ledger.get("retained_replay_evaluator_calls", 0) != evaluated_total:
        raise EvidenceError("complete_replay_ledger_disagrees")
    return result


def _resource(row):
    required = ("worker_id", "worker_receipt_sha256", "worker_resource_usage", "worker_limits", "worker_outcome", "max_artifact_bytes")
    if any(row.get(key) is None for key in required):
        raise EvidenceError("worker_resource_receipt_incomplete")
    usage, limits, outcome = row["worker_resource_usage"], row["worker_limits"], row["worker_outcome"]
    return {"worker_id": row["worker_id"], "receipt_sha256": row["worker_receipt_sha256"],
        "wall_ns": _int(outcome.get("elapsed_wall_ns"), "worker wall"),
        "cpu_ns": _int(usage.get("total_cpu_ns"), "worker CPU"),
        "peak_rss_bytes": _int(usage.get("max_rss_kib"), "RSS")*1024,
        "max_transaction_artifact_bytes": _int(row["max_artifact_bytes"], "artifact size"),
        "configured_limits": deepcopy(limits)}


def _quality(row):
    if type(row) is not dict or row.get("outcome") != "complete_quality":
        raise EvidenceError("verified_quality_worker_missing_or_incomplete")
    metrics = row.get("quality_payload", {})
    base, fresh = metrics.get("base", {}), metrics.get("direct_fresh", {})
    count = _int(row.get("heldout_target_tokens"), "heldout target count", 1)
    if row.get("heldout_reference") is None or row.get("quality_state_references") is None:
        raise EvidenceError("quality_input_or_state_bindings_missing")
    if (base.get("target_tokens") != count or fresh.get("target_tokens") != count
            or type(base.get("target_tokens")) is not int or type(fresh.get("target_tokens")) is not int
            or not base.get("metric_contract") or base.get("metric_contract") != fresh.get("metric_contract")):
        raise EvidenceError("quality_token_or_evaluator_contract_differs")
    b, f = _finite_score(base.get("nll_sum")), _finite_score(fresh.get("nll_sum"))
    if b is None or f is None:
        raise EvidenceError("quality_nonfinite_or_negative_score")
    gap = (f-b)/count
    lo, hi = log_ratio_enclosure()
    status = "pass" if gap <= lo else "fail" if gap > hi else "inconclusive_threshold_overlap"
    return {"status": status, "finite_mean_NLL_difference": _q(gap), "scored_tokens": count,
        "heldout_reference": deepcopy(row["heldout_reference"]),
        "quality_artifact_reference": deepcopy(row.get("quality_artifact_reference")),
        "quality_state_references": deepcopy(row["quality_state_references"]),
        "worker_id": row.get("worker_id"), "receipt_sha256": row.get("child_receipt_sha256")}


def _resource_snapshots(payloads, policy, workers, missing, failures):
    """Account for all supplied archive workers and the whole trusted ledger.

    Snapshot scope is deliberately narrower than project/global resource use.
    Filtered clean/diagnostic projections of the same archive are counted once.
    Unknown reservations remain charged and cannot prove worker completeness.
    """
    ledgers, archives = {}, {}
    ceiling = policy["resources"]
    for payload in payloads:
        ledger = payload.get("phase_budget_snapshot")
        if type(ledger) is not dict or ledger.get("status") != "verified":
            missing.append("complete_shared_phase_ledger_unavailable")
        else:
            path = ledger["path"]
            archive_links = {"linked_archived_attempt_ids", "attempts_without_worker_in_this_archive"}
            core = {key: value for key, value in ledger.items() if key not in archive_links}
            if path in ledgers and ledgers[path] != core:
                raise EvidenceError("shared phase ledger changed between verified snapshots")
            ledgers[path] = deepcopy(core)
        archive = payload.get("archive_storage_snapshot")
        if type(archive) is not dict or archive.get("status") != "verified_at_read":
            missing.append("nontransaction_archive_storage_snapshot_unavailable")
            continue
        path = archive["root"]
        if path in archives and archives[path] != archive:
            raise EvidenceError("archive storage changed between verified snapshots")
        archives[path] = archive
    all_archived = {}
    linked_attempts = set()
    for archive in archives.values():
        for name, item in archive["files"].items():
            if _int(item["bytes"], "archived file bytes") > ceiling["artifact_file_size_bytes_maximum"]:
                failures.append("archive_file_size:"+archive["root"]+"/"+name)
        for row in archive["workers"]:
            wid = row["worker_id"]
            if wid in all_archived and all_archived[wid] != row:
                raise EvidenceError("conflicting complete archived worker snapshots")
            all_archived[wid] = row
            if row.get("budget_attempt_id") is not None:
                linked_attempts.add(row["budget_attempt_id"])
            if row.get("budget_attempt_id") is None or row.get("phase_budget_binding") is None:
                missing.append("archived_worker_not_bound_to_protocol_CPU_ledger:"+wid)
            if row.get("status") != "complete":
                missing.append("archived_worker_receipt_incomplete:"+wid)
                continue
            usage, limits, outcome = row.get("resource_usage"), row.get("limits"), row.get("outcome")
            if not all(type(value) is dict for value in (usage, limits, outcome)):
                missing.append("archived_worker_resource_usage_incomplete:"+wid)
                continue
            actual = {"worker_id": wid, "receipt_sha256": row["worker_receipt_sha256"],
                "wall_ns": _int(outcome.get("elapsed_wall_ns"), "archived worker wall"),
                "cpu_ns": _int(usage.get("total_cpu_ns"), "archived worker CPU"),
                "peak_rss_bytes": _int(usage.get("max_rss_kib"), "archived RSS")*1024,
                "configured_limits": deepcopy(limits)}
            if wid in workers:
                if any(workers[wid].get(key) != value for key, value in actual.items()):
                    raise EvidenceError("role resource projection differs from whole-archive worker")
            else:
                workers[wid] = dict(actual, max_transaction_artifact_bytes=None)
            if (actual["wall_ns"] > ceiling["worker_wall_seconds"]*NS
                    or actual["cpu_ns"] > ceiling["worker_cpu_seconds"]*NS
                    or actual["peak_rss_bytes"] > ceiling["worker_peak_rss_bytes_maximum"]
                    or limits["wall_seconds"] > ceiling["worker_wall_seconds"]
                    or limits["cpu_seconds"] > ceiling["worker_cpu_seconds"]
                    or limits["address_space_bytes"] > ceiling["worker_address_space_bytes"]
                    or limits["file_size_bytes"] > ceiling["artifact_file_size_bytes_maximum"]):
                failures.append(wid)
    if set(workers)-set(all_archived):
        missing.append("measured_role_workers_absent_from_complete_archive_inventory")
    for ledger in ledgers.values():
        ledger["linked_supplied_archived_attempt_ids"] = sorted(set(ledger["attempts"]) & linked_attempts)
        ledger["attempts_without_worker_in_supplied_archives"] = sorted(set(ledger["attempts"])-linked_attempts)
        if ledger.get("reserved_unknown_attempts"):
            missing.append("unsettled_protocol_reservations_remain_fully_charged")
        if set(ledger["attempts"])-linked_attempts:
            missing.append("protocol_attempt_workers_outside_supplied_archives")
        if any(ledger["over_cap"].values()):
            failures.append("trusted_protocol_phase_cap_exceeded")
        cap = ceiling["feasibility_worker_CPU_hour_cap"]*3600
        if (ledger["phase_cpu_seconds"].get("feasibility", cap) > cap
                or ledger["charged_cpu_seconds"].get("feasibility", 0) > cap):
            failures.append("feasibility_protocol_CPU_allowance_exceeded")
    return {"phase_budget_snapshots": list(ledgers.values()),
        "archive_storage_snapshots": list(archives.values()),
        "all_supplied_archived_worker_ids": sorted(all_archived),
        "scope": "trusted protocol ledgers and supplied campaign output roots at read time; not project/global accounting"}


def assemble_feasibility_evidence(policy, clean, diagnostic=None):
    """Assemble verified available facts and exact missing reasons; no assertions.

    Only loader-issued complete sequence evidence objects are accepted. The
    output is a partial evidence package, never a fabricated complete policy
    input. Scientific provenance needs additional verified sources, so this
    bridge intentionally cannot promote.
    """
    from .measured_analysis import VerifiedMeasuredEvidence
    if digest(canonical_json(policy)) != POLICY_PAYLOAD_SHA256:
        raise EvidenceError("unsupported frozen feasibility policy")
    if type(clean) is not VerifiedMeasuredEvidence or (diagnostic is not None and type(diagnostic) is not VerifiedMeasuredEvidence):
        raise EvidenceError("loader-issued clean and diagnostic evidence required")
    c = clean.payload(); d = None if diagnostic is None else diagnostic.payload()
    if c.get("kind") != "sequence_lifetime" or (d is not None and d.get("kind") != "sequence_lifetime"):
        raise EvidenceError("feasibility requires measured sequence archives")
    missing = ["scientific_workload_provenance_not_established_by_archives"]
    mismatches, resource_failures, quality_failures, roots, workers = [], [], [], [], {}
    if len(c["slots"]) != policy["roots"]:
        missing.append("frozen_root_count_differs_from_feasibility_policy")
    keys = lambda slot: (slot["root_id"], slot["request_id"], slot["repeat_index"])
    diagnostic_slots = {} if d is None else {keys(slot): slot for slot in d["slots"]}
    if d is not None and len(diagnostic_slots) != len(d["slots"]):
        raise EvidenceError("duplicate diagnostic sequence")
    if not set(diagnostic_slots) <= {keys(slot) for slot in c["slots"]}:
        raise EvidenceError("unmatched planned diagnostic sequences cannot be dropped")
    if d is not None and d["protocol_sha256"] != c["protocol_sha256"]:
        raise EvidenceError("clean and diagnostic protocol bindings differ")
    seen_roots = set()
    for slot in c["slots"]:
        rid = slot["root_id"]
        if rid in seen_roots:
            raise EvidenceError("multiple configurations or repetitions per feasibility root require a new prospective policy")
        seen_roots.add(rid)
        if slot.get("execution_mode") != "clean" or slot.get("phase") not in ("feasibility", "software_test") or slot.get("repeat_index") != 0:
            missing.append(rid+":ineligible_phase_or_clean_profile")
        if slot.get("archive_status") != "sealed":
            missing.append(rid+":sequence_archive_incomplete")
        diag = diagnostic_slots.get(keys(slot))
        if diag is None:
            missing.append(rid+":matched_diagnostic_sequence_missing")
        else:
            for key in ("target_manifest_sha256", "configuration_sha256", "source_sha256", "protocol_sha256"):
                if diag.get(key) != slot.get(key):
                    raise EvidenceError("diagnostic sequence differs in " + key)
            if diag.get("execution_mode") != "diagnostic" or diag.get("archive_status") != "sealed":
                missing.append(rid+":diagnostic_sequence_not_complete")
        prep = slot.get("preparation", {})
        initial = prep.get("repair", {})
        records = initial.get("record_ids")
        tokens = slot.get("record_token_counts")
        if records is None or len(records) != policy["calibration_records_per_root"]:
            missing.append(rid+":calibration_record_count_missing_or_different")
        if (type(tokens) is not dict or records is None or set(tokens) != set(records)
                or any(type(value) is not int or value != policy["tokens_per_record"] for value in tokens.values())):
            missing.append(rid+":record_token_counts_missing_or_different")
        try:
            order, ancestors = _graph(initial.get("target_graph"))
        except EvidenceError as error:
            missing.append(rid+":"+str(error)); order, ancestors = [], {}
        previous = initial.get("stage_code_sha256")
        if previous is None or set(previous) != set(order):
            missing.append(rid+":original_stage_map_incomplete")
        if initial.get("model_sha256") is not None and initial.get("model_sha256") != prep.get("model_only_fresh", {}).get("model_sha256"):
            mismatches.append(rid+":original_model_disagreement")
        root = {"root_id": rid, "target_manifest_sha256": slot["target_manifest_sha256"],
            "configuration_sha256": slot["configuration_sha256"], "original_record_ids": records,
            "record_token_counts": tokens, "target_graph": initial.get("target_graph"),
            "preparation": deepcopy(prep), "requests": [], "coverage_numerator": 0,
            "coverage_denominator": 0, "coverage_complete": True, "lifetime": {}}
        steps = slot.get("steps", [])
        if len(steps) != policy["sequential_requests_per_root"]:
            missing.append(rid+":ordered_request_count_differs")
            root["coverage_complete"] = False
        if diag is not None and [s["request_id"] for s in diag.get("steps", [])] != [s["request_id"] for s in steps]:
            raise EvidenceError("diagnostic ordered request schedule differs")
        role_rows = list(prep.values())
        for index, step in enumerate(steps):
            label = rid+":"+step["request_id"]
            current = step["methods"].get("repair", {})
            q = {"request_id": step["request_id"], "newly_deleted_ids": step.get("newly_deleted_ids"),
                "methods": deepcopy(step["methods"]), "coverage_groups": None, "quality": None}
            role_rows.extend(step["methods"].values())
            for name in ORACLES:
                row = step["methods"].get(name, {})
                if row.get("exact_model") is False or row.get("exact_state") is False:
                    mismatches.append(label+":"+name)
                elif row.get("outcome") != "exact_complete":
                    missing.append(label+":incomplete_clean_method:"+name)
            diag_step = None if diag is None else diag["steps"][index]
            parity = False
            if diag_step is not None:
                if diag_step.get("newly_deleted_ids") != step.get("newly_deleted_ids"):
                    raise EvidenceError("diagnostic deletion membership differs")
                row = diag_step["methods"].get("repair", {})
                role_rows.extend(diag_step["methods"].values())
                prev_diag = (diag["preparation"]["repair"] if index == 0 else diag["steps"][index-1]["methods"]["repair"])
                parity = (row.get("exact_model") is True and row.get("exact_state") is True
                    and row.get("stage_code_sha256") == current.get("stage_code_sha256")
                    and row.get("state_sha256") == current.get("state_sha256")
                    and row.get("record_ids") == current.get("record_ids")
                    and row.get("target_graph") == initial.get("target_graph")
                    and type(initial.get("record_groups")) is dict
                    and row.get("record_groups") == {key: initial["record_groups"][key]
                        for key in row.get("record_ids", ()) if key in initial["record_groups"]}
                    and prev_diag.get("stage_code_sha256") == previous)
                if parity and previous is not None and order:
                    try:
                        coverage = derive_complete_group_coverage(row)
                        changed = {stage for stage in order if previous[stage] != current["stage_code_sha256"][stage]}
                        eligible = [g for g in coverage if ancestors[g["stage_id"]] & changed]
                        q.update(coverage_groups=coverage, diagnostic_receipt_sha256=row.get("child_receipt_sha256"),
                            coverage_denominator=len(eligible), coverage_numerator=sum(g["retained_target_feature_evaluations"] == 0 for g in eligible))
                        root["coverage_denominator"] += q["coverage_denominator"]
                        root["coverage_numerator"] += q["coverage_numerator"]
                    except (EvidenceError, KeyError, TypeError) as error:
                        missing.append(label+":coverage:"+str(error)); root["coverage_complete"] = False
                else:
                    missing.append(label+":diagnostic_code_state_prefix_parity_unavailable"); root["coverage_complete"] = False
            else:
                root["coverage_complete"] = False
            quality = step.get("quality")
            if type(quality) is not dict or quality.get("outcome") != "complete_quality":
                quality = None if diag_step is None or not parity else diag_step.get("quality")
            try:
                q["quality"] = _quality(quality)
                if q["quality"]["status"] == "fail":
                    quality_failures.append(label)
                elif q["quality"]["status"] != "pass":
                    missing.append(label+":quality_threshold_enclosure_overlap")
            except (EvidenceError, KeyError, TypeError) as error:
                missing.append(label+":quality:"+str(error))
            for quality_worker in (step.get("quality"), None if diag_step is None else diag_step.get("quality")):
                if type(quality_worker) is dict and quality_worker.get("receipt_sha256"):
                    role_rows.append(quality_worker)
            root["requests"].append(q)
            previous = current.get("stage_code_sha256")
        if diag is not None:
            role_rows.extend(diag.get("preparation", {}).values())
        for method in METHODS:
            preparation = prep.get("model_only_fresh" if method == "model_only_fresh" else "repair", {})
            terms = [preparation]+[step["methods"].get(method, {}) for step in steps]
            complete = all(row.get("outcome") == "exact_complete" and type(row.get("wall_ns")) is int
                           and row["wall_ns"] > 0 for row in terms)
            total = sum(row["wall_ns"] for row in terms) if complete else None
            if total is not None and slot["methods"][method].get("wall_ns") != total:
                raise EvidenceError("exported lifetime differs from its verified terms")
            root["lifetime"][method] = {"complete": complete and len(steps) == policy["cost"]["lifetime_horizon"],
                "wall_ns": total, "preparation_wall_ns": preparation.get("wall_ns")}
            if not complete:
                missing.append(rid+":incomplete_lifetime:"+method)
            elif (preparation["wall_ns"] > policy["resources"]["complete_original_preparation_wall_seconds_maximum"]*NS
                    or total > policy["resources"]["complete_three_request_lifetime_wall_seconds_maximum"]*NS):
                resource_failures.append(rid+":preparation_or_lifetime_limit:"+method)
        if all(root["lifetime"][method]["complete"] for method in METHODS):
            root["model_only_lifetime_gain_ns"] = root["lifetime"]["model_only_fresh"]["wall_ns"]-root["lifetime"]["repair"]["wall_ns"]
            root["equal_information_lifetime_gain_ns"] = root["lifetime"]["indexed_fresh"]["wall_ns"]-root["lifetime"]["repair"]["wall_ns"]
        for row in role_rows:
            try:
                resource = _resource(row)
                enclosing = row.get("observed_wall_ns", row.get("wall_ns"))
                if type(enclosing) is int and resource["wall_ns"] > enclosing:
                    raise EvidenceError("worker_exceeds_enclosing_transaction")
                wid = resource["worker_id"]
                if wid in workers and workers[wid] != resource:
                    raise EvidenceError("conflicting observed worker")
                workers[wid] = resource
                limits = resource["configured_limits"]
                ceiling = policy["resources"]
                if (resource["wall_ns"] > ceiling["worker_wall_seconds"]*NS
                        or resource["cpu_ns"] > ceiling["worker_cpu_seconds"]*NS
                        or resource["peak_rss_bytes"] > ceiling["worker_peak_rss_bytes_maximum"]
                        or resource["max_transaction_artifact_bytes"] > ceiling["artifact_file_size_bytes_maximum"]
                        or limits["wall_seconds"] > ceiling["worker_wall_seconds"]
                        or limits["cpu_seconds"] > ceiling["worker_cpu_seconds"]
                        or limits["address_space_bytes"] > ceiling["worker_address_space_bytes"]
                        or limits["file_size_bytes"] > ceiling["artifact_file_size_bytes_maximum"]):
                    resource_failures.append(wid)
            except (EvidenceError, KeyError, TypeError) as error:
                missing.append(rid+":resources:"+str(error))
        roots.append(root)
    snapshots = _resource_snapshots([c] if d is None else [c, d], policy, workers, missing, resource_failures)
    known_charge = sum(max(1, (row["cpu_ns"]+NS-1)//NS) for row in workers.values())
    if known_charge > policy["resources"]["feasibility_worker_CPU_hour_cap"]*3600:
        resource_failures.append("observed_workers_already_exceed_feasibility_CPU_allowance")
    return {"schema": "assembled-feasibility-evidence-v1", "status": "incomplete",
        "policy_payload_sha256": POLICY_PAYLOAD_SHA256, "clean_evidence_sha256": clean.sha256,
        "diagnostic_evidence_sha256": None if diagnostic is None else diagnostic.sha256,
        "inventory_sha256": c["inventory_sha256"], "protocol_sha256": c["protocol_sha256"],
        "roots": roots, "observed_workers": list(workers.values()),
        "resource_accounting": snapshots,
        "observed_minimum_worker_settlement_seconds": known_charge,
        "known_mismatches": sorted(set(mismatches)), "resource_failures": sorted(set(resource_failures)),
        "quality_failures": sorted(set(quality_failures)),
        "missing_evidence": sorted(set(missing)), "empirical_attainment_established": False}


def evaluate_archive_feasibility(policy, clean, diagnostic=None):
    """Public archive-to-policy bridge; current unexported premises stay open."""
    result = {"schema": "calibration-feasibility-decision-v1", "conditions_satisfied": False,
        "empirical_attainment_established": False, "research_execution_authorized": False,
        "confirmation_authorized": False, "population_speedup_established": False}
    try:
        assembled = assemble_feasibility_evidence(policy, clean, diagnostic)
        result.update(decision="stop_and_repair_implementation" if assembled["known_mismatches"] else
            "inconclusive_missing_required_evidence", assembled_evidence=assembled,
            missing_evidence=assembled["missing_evidence"], measured_sequence_archive_verified=True)
    except (EvidenceError, ValueError, KeyError, TypeError, OverflowError) as error:
        result.update(decision="inconclusive_unmatched_verified_measurements", error=str(error)[:256],
            measured_sequence_archive_verified=False)
    return result
