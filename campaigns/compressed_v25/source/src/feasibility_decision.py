"""Pure, fail-closed assessment of the frozen feasibility policy.

This module validates evidence structure and arithmetic, not the truth of input
JSON. A positive result is conditional on independently verified archives and
scientific provenance. It never authorizes execution or establishes an empirical
result. Read docs/FEASIBILITY_DECISION.md before constructing evidence.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import math

from .run_store import canonical_json, digest
from .transaction_timing import BOUNDARY

POLICY_PAYLOAD_SHA256 = "92af4f2ae5d9b01b51f469830a35ccb4b2521f6351ad286cbdc0e40ce64ac5a2"
SCHEMA = "calibration-feasibility-evidence-v1"
METHODS = ("repair", "indexed_fresh", "model_only_fresh")
ORACLES = METHODS + ("direct_fresh",)
FRESH_CACHE = "fresh_transaction_os_cache_uncontrolled"
NS = 1_000_000_000


class EvidenceError(ValueError):
    """Malformed, contradictory, or unsupported conditional evidence."""


class _VerifiedMismatch(EvidenceError):
    pass


def _fields(value, fields, name):
    if type(value) is not dict or set(value) != set(fields):
        raise EvidenceError(name + " has missing or unexpected fields")
    return value


def _int(value, name, minimum=0):
    if type(value) is not int or value < minimum or value.bit_length() > 128:
        raise EvidenceError(name + " must be a bounded nonnegative integer")
    return value


def _bool(value, name):
    if type(value) is not bool:
        raise EvidenceError(name + " must be a boolean")
    return value


def _text(value, name):
    if type(value) is not str or not value or len(value) > 256:
        raise EvidenceError(name + " must be bounded nonempty text")
    return value


def _sha(value):
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise EvidenceError("invalid SHA256")
    return value


def _list(value, name, maximum=65536):
    if type(value) is not list or len(value) > maximum:
        raise EvidenceError(name + " must be a bounded list")
    return value


def _ids(value, name):
    values = [_text(x, name) for x in _list(value, name)]
    if len(set(values)) != len(values):
        raise EvidenceError("duplicate " + name)
    return values


def _q(value):
    return {"numerator": value.numerator, "denominator": value.denominator}


def log_ratio_enclosure(numerator=6, denominator=5, terms=32):
    """Exact positive-series enclosure; no host-log accuracy premise is used."""
    _int(numerator, "ratio numerator", 1)
    _int(denominator, "ratio denominator", 1)
    _int(terms, "series terms", 1)
    if numerator < denominator or terms > 256:
        raise EvidenceError("unsupported log enclosure")
    x = Fraction(numerator - denominator, numerator + denominator)
    lower = 2 * sum((x ** (2*k+1) / (2*k+1) for k in range(terms)), Fraction())
    tail = 2 * x ** (2*terms+1) / ((2*terms+1)*(1-x*x))
    return lower, lower + tail


def _finite_score(value):
    if type(value) not in (int, float) or (type(value) is float and not math.isfinite(value)):
        return None
    if type(value) is int and value.bit_length() > 128:
        return None
    result = Fraction(value)
    return result if result >= 0 else None


def _stage_map(value, stages, name):
    if type(value) is not dict or set(value) - set(stages):
        raise EvidenceError(name + " has unexpected stages")
    for item in value.values():
        _sha(item)
    return value if set(value) == set(stages) else None


def _assess(policy, evidence):
    if digest(canonical_json(policy)) != POLICY_PAYLOAD_SHA256:
        raise EvidenceError("unsupported policy; a prospective revision needs an explicit evaluator update")
    _fields(evidence, ("schema", "policy_payload_sha256", "target_manifest_sha256",
        "configuration_sha256", "protocol_sha256", "inventory_sha256", "source_sha256", "evidence_kind",
        "provenance", "target", "measurement_contract", "roots", "resources"), "evidence")
    if evidence["schema"] != SCHEMA or evidence["policy_payload_sha256"] != POLICY_PAYLOAD_SHA256:
        raise EvidenceError("wrong evidence schema or policy binding")
    for name in ("target_manifest_sha256", "configuration_sha256", "protocol_sha256", "inventory_sha256"):
        _sha(evidence[name])
    sources = evidence["source_sha256"]
    if type(sources) is not dict or not sources or len(sources) > 4096:
        raise EvidenceError("missing or oversized source bindings")
    for name, sha in sources.items():
        _text(name, "source path"); _sha(sha)
    if evidence["evidence_kind"] not in ("research", "software_test"):
        raise EvidenceError("unknown evidence kind")
    provenance = _fields(evidence["provenance"], ("producer_sha256", "artifacts",
        "archive_validation", "scientific_provenance"), "provenance")
    _sha(provenance["producer_sha256"])
    if provenance["archive_validation"] not in ("verified", "unverified"):
        raise EvidenceError("invalid archive validation disposition")
    if provenance["scientific_provenance"] not in ("verified_real_workload", "unverified", "software_fixture"):
        raise EvidenceError("invalid scientific provenance disposition")
    artifacts = _list(provenance["artifacts"], "artifact bindings")
    roles = set()
    for artifact in artifacts:
        _fields(artifact, ("role", "sha256"), "artifact binding")
        role = _text(artifact["role"], "artifact role"); _sha(artifact["sha256"])
        if role in roles:
            raise EvidenceError("duplicate artifact role")
        roles.add(role)
    required_roles = {"measured_lifetime", "coverage", "quality", "resource_ledger", "workload_provenance", "exactness"}
    if not required_roles <= roles:
        raise EvidenceError("missing required evidence artifact binding")

    target = _fields(evidence["target"], ("stage_order", "parents"), "target")
    stages = _ids(target["stage_order"], "stage ID")
    if not stages or len(stages) > 4096 or type(target["parents"]) is not dict or set(target["parents"]) != set(stages):
        raise EvidenceError("incomplete target DAG")
    ancestors = {}
    for stage in stages:
        parents = _ids(target["parents"][stage], "parent stage")
        if any(parent not in ancestors for parent in parents):
            raise EvidenceError("stage order is not a topological DAG order")
        ancestors[stage] = set(parents)
        for parent in parents:
            ancestors[stage].update(ancestors[parent])

    contract = _fields(evidence["measurement_contract"], ("boundary", "required_costs",
        "external_oracle_accounting", "observer_receipt_excluded", "method_costs_disjoint"), "measurement contract")
    missing, mismatches, resource_failures, quality_failures = [], [], [], []
    if contract["boundary"] != BOUNDARY or contract["required_costs"] != policy["cost"]["required_costs"]:
        missing.append("unsupported_complete_cost_boundary")
    if contract["external_oracle_accounting"] != "separate_symmetric":
        missing.append("research_oracle_costs_not_separate_and_symmetric")
    for name in ("observer_receipt_excluded", "method_costs_disjoint"):
        if not _bool(contract[name], name):
            missing.append(name)
    if provenance["archive_validation"] != "verified":
        missing.append("independent_archive_validation_required")
    if evidence["evidence_kind"] == "research" and provenance["scientific_provenance"] != "verified_real_workload":
        missing.append("real_workload_provenance_required")

    receipts, timing_workers, diagnostic_workers = set(), {}, {}
    def timing(row, method, retained, label):
        if row is None:
            missing.append(label + ":missing_timing"); return None
        _fields(row, ("status", "wall_ns", "receipt_sha256", "output_contract", "boundary",
            "cache_mode", "profiler_active", "new_latency_observation", "source_inputs_unchanged",
            "execution_mode", "instrumentation_disabled", "worker_id", "worker_receipt_sha256",
            "target_manifest_sha256", "configuration_sha256", "retained_ids_sha256"), "transaction timing")
        receipt = _sha(row["receipt_sha256"])
        if receipt in receipts:
            raise EvidenceError("one transaction receipt reused for distinct lifetime terms")
        receipts.add(receipt)
        worker_id = _text(row["worker_id"], "timing worker ID")
        worker_receipt = _sha(row["worker_receipt_sha256"])
        if worker_id in timing_workers:
            raise EvidenceError("one worker reused for distinct complete transaction terms")
        timing_workers[worker_id] = {"receipt_sha256": worker_receipt, "wall_ns": None}
        _sha(row["target_manifest_sha256"]); _sha(row["retained_ids_sha256"])
        if row["target_manifest_sha256"] != evidence["target_manifest_sha256"]:
            raise EvidenceError("transaction target differs")
        if _sha(row["configuration_sha256"]) != evidence["configuration_sha256"]:
            raise EvidenceError("transaction configuration differs")
        if row["retained_ids_sha256"] != digest(canonical_json(sorted(retained))):
            raise EvidenceError("transaction retained membership differs")
        expected_contract = "model_only" if method == "model_only_fresh" else "canonical_state"
        valid = (row["status"] == "complete" and row["output_contract"] == expected_contract
            and row["boundary"] == BOUNDARY and row["cache_mode"] == FRESH_CACHE
            and row["execution_mode"] == "clean"
            and _bool(row["instrumentation_disabled"], "instrumentation_disabled")
            and not _bool(row["profiler_active"], "profiler_active")
            and _bool(row["new_latency_observation"], "new_latency_observation")
            and _bool(row["source_inputs_unchanged"], "source_inputs_unchanged"))
        if row["wall_ns"] is None or not valid:
            missing.append(label + ":ineligible_timing"); return None
        elapsed = _int(row["wall_ns"], "complete transaction wall_ns", 1)
        timing_workers[worker_id]["wall_ns"] = elapsed
        return elapsed

    def diagnostic_worker(value):
        wid = _text(value["worker_id"], "diagnostic worker ID")
        receipt = _sha(value["worker_receipt_sha256"])
        if wid in timing_workers:
            raise EvidenceError("diagnostic worker cannot supply a clean timing")
        if wid in diagnostic_workers and diagnostic_workers[wid] != receipt:
            raise EvidenceError("diagnostic worker has conflicting receipts")
        diagnostic_workers[wid] = receipt

    roots = _list(evidence["roots"], "roots", 64)
    if len(roots) != policy["roots"]:
        missing.append("incomplete_planned_root_count")
    seen_roots, reports = set(), []
    threshold_lo, threshold_hi = log_ratio_enclosure()
    for root in roots:
        _fields(root, ("root_id", "records", "record_groups", "initial_stage_codes", "preparation",
            "planned_request_ids", "requests"), "root")
        rid = _text(root["root_id"], "root ID")
        if rid in seen_roots:
            raise EvidenceError("duplicate root")
        seen_roots.add(rid)
        record_rows = _list(root["records"], "records", 65536)
        records = []
        for record in record_rows:
            _fields(record, ("record_id", "tokens"), "record")
            records.append(_text(record["record_id"], "record ID"))
            if _int(record["tokens"], "tokens", 1) != policy["tokens_per_record"]:
                missing.append(rid + ":wrong_record_token_count")
        if len(set(records)) != len(records):
            raise EvidenceError("duplicate record")
        if len(records) != policy["calibration_records_per_root"]:
            missing.append(rid + ":wrong_calibration_size")
        groups = root["record_groups"]
        if type(groups) is not dict or set(groups) != set(stages):
            raise EvidenceError("group inventory lacks complete target stages")
        for stage in stages:
            if type(groups[stage]) is not dict or set(groups[stage]) != set(records):
                raise EvidenceError("group inventory differs from root records")
            for group in groups[stage].values():
                _text(group, "group ID")
        previous = _stage_map(root["initial_stage_codes"], stages, "initial model")
        if previous is None:
            missing.append(rid + ":incomplete_initial_model")
        prep = _fields(root["preparation"], METHODS, "preparation")
        if prep["repair"] != prep["indexed_fresh"]:
            raise EvidenceError("equal-information comparator must receive the same prepared index")
        retained = set(records)
        repair_prep = timing(prep["repair"], "repair", retained, rid + ":repair_preparation")
        fresh_prep = timing(prep["model_only_fresh"], "model_only_fresh", retained, rid + ":model_preparation")
        totals = {"repair": repair_prep, "indexed_fresh": repair_prep, "model_only_fresh": fresh_prep}
        for value in (repair_prep, fresh_prep):
            if value is not None and value > policy["resources"]["complete_original_preparation_wall_seconds_maximum"]*NS:
                resource_failures.append(rid + ":preparation_limit")
        planned = _ids(root["planned_request_ids"], "planned request ID")
        requests = _list(root["requests"], "requests", 65536)
        schedule_matches = (len(planned) == policy["sequential_requests_per_root"]
            and [q.get("request_id") for q in requests if type(q) is dict] == planned)
        if not schedule_matches:
            missing.append(rid + ":incomplete_or_reordered_requests")
        numerator = denominator = 0
        coverage_complete = schedule_matches
        request_reports = []
        for request in requests:
            _fields(request, ("request_id", "deleted_ids", "models", "states", "coverage", "quality", "timings"), "request")
            qid = _text(request["request_id"], "request ID"); label = rid + ":" + qid
            deleted = set(_ids(request["deleted_ids"], "deleted record ID"))
            if not deleted <= retained:
                raise EvidenceError("deletion includes missing or already deleted records")
            retained -= deleted
            models = _fields(request["models"], ORACLES, "model comparisons")
            complete_models = {}
            for method in ORACLES:
                value = models[method]
                if value is None:
                    missing.append(label + ":missing_model:" + method)
                else:
                    complete_models[method] = _stage_map(value, stages, method)
                    if complete_models[method] is None:
                        missing.append(label + ":incomplete_stage_map:" + method)
            for stage in stages:
                observed = {model[stage] for model in models.values() if type(model) is dict and stage in model}
                if len(observed) > 1:
                    mismatches.append(label + ":model:" + stage)
            state = _fields(request["states"], ("repair", "indexed_fresh", "direct_fresh"), "state comparisons")
            state_hashes = [_sha(value) for value in state.values() if value is not None]
            if len(state_hashes) != 3:
                missing.append(label + ":missing_canonical_state")
            if len(set(state_hashes)) > 1:
                mismatches.append(label + ":canonical_state")
            current = complete_models.get("repair")
            changed = None if previous is None or current is None else {stage for stage in stages if current[stage] != previous[stage]}
            expected = {(stage, groups[stage][record]) for stage in stages for record in retained}
            eligible = None if changed is None else {(stage, group) for stage, group in expected if ancestors[stage] & changed}
            coverage = _fields(request["coverage"], ("complete", "omitted_events", "capped", "counter_saturated", "groups", "replicate"), "coverage")
            replicate = coverage["replicate"]
            parity = False
            if replicate is not None:
                _fields(replicate, ("receipt_sha256", "worker_id", "worker_receipt_sha256",
                    "target_manifest_sha256", "configuration_sha256", "source_bindings_sha256",
                    "root_id", "request_id", "retained_ids_sha256", "predecessor_stage_map_sha256",
                    "stage_codes", "canonical_state_sha256", "execution_mode"), "coverage replicate")
                _sha(replicate["receipt_sha256"]); diagnostic_worker(replicate)
                codes = _stage_map(replicate["stage_codes"], stages, "diagnostic model")
                for key in ("target_manifest_sha256", "configuration_sha256", "source_bindings_sha256",
                        "retained_ids_sha256", "predecessor_stage_map_sha256", "canonical_state_sha256"):
                    _sha(replicate[key])
                parity = (replicate["target_manifest_sha256"] == evidence["target_manifest_sha256"]
                    and replicate["configuration_sha256"] == evidence["configuration_sha256"]
                    and replicate["source_bindings_sha256"] == digest(canonical_json(sources))
                    and replicate["root_id"] == rid and replicate["request_id"] == qid
                    and replicate["retained_ids_sha256"] == digest(canonical_json(sorted(retained)))
                    and previous is not None and replicate["predecessor_stage_map_sha256"] == digest(canonical_json(previous))
                    and current is not None and codes == current
                    and replicate["canonical_state_sha256"] == state["repair"]
                    and replicate["execution_mode"] == "diagnostic")
            if not parity:
                missing.append(label + ":unmatched_diagnostic_coverage_replicate")
            observed_groups = {}
            for row in _list(coverage["groups"], "coverage groups"):
                _fields(row, ("stage_id", "group_id", "retained_target_feature_evaluations"), "coverage group")
                key = (_text(row["stage_id"], "stage ID"), _text(row["group_id"], "group ID"))
                if key in observed_groups or key not in expected:
                    raise EvidenceError("duplicate, empty, or unexpected coverage group")
                observed_groups[key] = _int(row["retained_target_feature_evaluations"], "feature evaluations")
            clean = (_bool(coverage["complete"], "coverage completeness")
                and _int(coverage["omitted_events"], "omitted events") == 0
                and not _bool(coverage["capped"], "coverage capped")
                and not _bool(coverage["counter_saturated"], "coverage saturation")
                and set(observed_groups) == expected and eligible is not None and parity)
            if not clean:
                coverage_complete = False
                missing.append(label + ":incomplete_coverage_evidence")
            else:
                denominator += len(eligible)
                numerator += sum(observed_groups[key] == 0 for key in eligible)
            quality = _fields(request["quality"], ("base", "retained_fresh", "binding"), "quality")
            quality_binding = quality["binding"]
            quality_parity = False
            if quality_binding is not None:
                _fields(quality_binding, ("receipt_sha256", "worker_id", "worker_receipt_sha256",
                    "target_manifest_sha256", "root_id", "request_id", "retained_model_stage_map_sha256"), "quality binding")
                _sha(quality_binding["receipt_sha256"]); diagnostic_worker(quality_binding)
                _sha(quality_binding["target_manifest_sha256"]); _sha(quality_binding["retained_model_stage_map_sha256"])
                fresh_model = complete_models.get("model_only_fresh")
                quality_parity = (quality_binding["target_manifest_sha256"] == evidence["target_manifest_sha256"]
                    and quality_binding["root_id"] == rid and quality_binding["request_id"] == qid
                    and fresh_model is not None and quality_binding["retained_model_stage_map_sha256"] == digest(canonical_json(fresh_model)))
            if not quality_parity:
                missing.append(label + ":unmatched_quality_model")
            samples = []
            for method in ("base", "retained_fresh"):
                sample = quality[method]
                if sample is None:
                    samples.append(None); continue
                _fields(sample, ("heldout_sha256", "evaluator_sha256", "scored_tokens", "nll_sum"), "quality sample")
                _sha(sample["heldout_sha256"]); _sha(sample["evaluator_sha256"])
                count = _int(sample["scored_tokens"], "scored tokens")
                score = _finite_score(sample["nll_sum"])
                samples.append(None if count == 0 or score is None else (sample, score/count))
            quality_status = "inconclusive"
            if any(sample is None for sample in samples):
                missing.append(label + ":missing_nonfinite_or_empty_quality")
            else:
                base, fresh = samples
                keys = ("heldout_sha256", "evaluator_sha256", "scored_tokens")
                if any(base[0][key] != fresh[0][key] for key in keys):
                    missing.append(label + ":mismatched_quality_inputs_or_counts")
                else:
                    gap = fresh[1]-base[1]
                    if gap <= threshold_lo:
                        quality_status = "pass" if quality_parity else "inconclusive"
                    elif gap > threshold_hi:
                        quality_status = "fail"; quality_failures.append(label)
                    else:
                        missing.append(label + ":quality_threshold_enclosure_overlap")
            timings = _fields(request["timings"], METHODS, "method timings")
            for method in METHODS:
                elapsed = timing(timings[method], method, retained, label + ":" + method)
                totals[method] = None if totals[method] is None or elapsed is None else totals[method]+elapsed
            request_reports.append({"request_id": qid, "retained_records": len(retained),
                "changed_ancestor_groups": None if not clean else len(eligible), "quality": quality_status})
            previous = current
        if len(requests) != len(planned):
            totals = {method: None for method in METHODS}
        for method, value in totals.items():
            if value is not None and value > policy["resources"]["complete_three_request_lifetime_wall_seconds_maximum"]*NS:
                resource_failures.append(rid + ":lifetime_limit:" + method)
        root_report = {"root_id": rid, "requests": request_reports, "coverage_numerator": numerator,
            "coverage_denominator": denominator, "coverage_complete": coverage_complete,
            "lifetime_wall_ns": totals, "lifetime_gain_ns": None,
            "equal_information_gain_ns": None}
        if all(value is not None for value in totals.values()):
            root_report["lifetime_gain_ns"] = totals["model_only_fresh"]-totals["repair"]
            root_report["equal_information_gain_ns"] = totals["indexed_fresh"]-totals["repair"]
        reports.append(root_report)

    resources = _fields(evidence["resources"], ("planned_worker_ids", "workers", "complete",
        "unsettled_reservations", "phase_cpu_charge_seconds", "phase_ledger_sha256"), "resources")
    planned_workers = _ids(resources["planned_worker_ids"], "worker ID")
    _sha(resources["phase_ledger_sha256"])
    if not _bool(resources["complete"], "resource completeness") or _int(resources["unsettled_reservations"], "unsettled reservations"):
        missing.append("incomplete_worker_resource_accounting")
    if not planned_workers:
        missing.append("empty_worker_inventory")
    workers = _list(resources["workers"], "workers")
    seen_workers, worker_receipts, measured_cpu, minimum_charge = set(), set(), 0, 0
    limits = policy["resources"]
    for worker in workers:
        _fields(worker, ("worker_id", "receipt_sha256", "status", "wall_ns", "cpu_ns",
            "wall_limit_seconds", "cpu_limit_seconds", "file_size_limit_bytes",
            "address_space_limit_bytes", "peak_rss_bytes", "max_artifact_bytes"), "worker resource")
        wid = _text(worker["worker_id"], "worker ID"); receipt = _sha(worker["receipt_sha256"])
        if wid in seen_workers or wid not in planned_workers:
            raise EvidenceError("duplicate or unplanned worker resource")
        seen_workers.add(wid)
        if receipt in worker_receipts:
            raise EvidenceError("worker receipt duplicated across distinct worker IDs")
        worker_receipts.add(receipt)
        if ((wid in timing_workers and timing_workers[wid]["receipt_sha256"] != receipt)
                or (wid in diagnostic_workers and diagnostic_workers[wid] != receipt)):
            raise EvidenceError("timing worker and resource receipt disagree")
        configured_wall = _int(worker["wall_limit_seconds"], "configured wall limit", 1)
        configured_cpu = _int(worker["cpu_limit_seconds"], "configured CPU limit", 1)
        configured_file = _int(worker["file_size_limit_bytes"], "configured file limit", 1)
        address = _int(worker["address_space_limit_bytes"], "address space", 1)
        if (configured_wall > limits["worker_wall_seconds"]
                or configured_cpu > limits["worker_cpu_seconds"]
                or configured_file > limits["artifact_file_size_bytes_maximum"]
                or address > limits["worker_address_space_bytes"]):
            resource_failures.append(wid + ":configured_limit")
        if worker["status"] != "complete" or any(worker[name] is None for name in ("wall_ns", "cpu_ns", "peak_rss_bytes", "max_artifact_bytes")):
            missing.append(wid + ":incomplete_worker_resource"); continue
        observed = {name: _int(worker[name], name) for name in ("wall_ns", "cpu_ns", "peak_rss_bytes", "max_artifact_bytes")}
        if (wid in timing_workers and timing_workers[wid]["wall_ns"] is not None
                and observed["wall_ns"] > timing_workers[wid]["wall_ns"]):
            raise EvidenceError("worker elapsed exceeds its complete enclosing transaction")
        measured_cpu += observed["cpu_ns"]
        minimum_charge += max(1, (observed["cpu_ns"]+NS-1)//NS)
        if (observed["wall_ns"] > limits["worker_wall_seconds"]*NS
                or observed["cpu_ns"] > limits["worker_cpu_seconds"]*NS
                or address > limits["worker_address_space_bytes"]
                or observed["peak_rss_bytes"] > limits["worker_peak_rss_bytes_maximum"]
                or observed["max_artifact_bytes"] > limits["artifact_file_size_bytes_maximum"]):
            resource_failures.append(wid)
    if seen_workers != set(planned_workers):
        missing.append("missing_planned_worker_resources")
    if not set(timing_workers) <= seen_workers:
        missing.append("timing_worker_missing_from_resource_inventory")
    if not set(diagnostic_workers) <= seen_workers:
        missing.append("diagnostic_worker_missing_from_resource_inventory")
    if set(timing_workers) & set(diagnostic_workers):
        raise EvidenceError("clean and diagnostic work share one worker")
    charge = _int(resources["phase_cpu_charge_seconds"], "phase CPU charge")
    if charge*NS < measured_cpu or charge < minimum_charge:
        raise EvidenceError("phase CPU charge is smaller than observed worker CPU")
    if charge > limits["feasibility_worker_CPU_hour_cap"]*3600:
        resource_failures.append("feasibility_phase_CPU_cap")

    zero = [r["root_id"] for r in reports if r["coverage_denominator"] == 0]
    coverage = [r["root_id"] for r in reports if r["coverage_numerator"]*4 < r["coverage_denominator"]]
    lifetime = [r["root_id"] for r in reports if r["lifetime_gain_ns"] is not None and r["lifetime_gain_ns"] <= 0]
    if mismatches:
        decision = "stop_and_repair_implementation"
    elif missing:
        decision = "inconclusive_missing_required_evidence"
    elif resource_failures:
        decision = "redesign_resources_or_narrow"
    elif quality_failures:
        decision = "revise_quality_configuration_prospectively_or_narrow"
    elif zero:
        decision = "inconclusive_mechanism_not_demonstrated"
    elif coverage:
        decision = "redesign_certificate_or_narrow"
    elif lifetime:
        decision = "redesign_cost_or_narrow"
    else:
        decision = "conditional_promote_to_development"
    return {"decision": decision, "conditions_satisfied": decision == "conditional_promote_to_development",
        "mismatches": mismatches, "missing_evidence": missing, "resource_failures": resource_failures,
        "quality_failures": quality_failures, "zero_denominator_roots": zero,
        "coverage_failure_roots": coverage, "lifetime_failure_roots": lifetime,
        "deletion_exclusive_solver_claim_supported": False,
        "equal_information_cost_condition_all_roots": bool(reports) and not missing and all(
            r["equal_information_gain_ns"] is not None and r["equal_information_gain_ns"] > 0 for r in reports),
        "roots": reports, "quality_log_threshold_enclosure": {"lower": _q(threshold_lo), "upper": _q(threshold_hi)}}


def evaluate_feasibility(policy, evidence):
    """Return a conditional decision; malformed or incomplete facts cannot pass.

    File loading, receipt verification, actual source independence, truthful
    instrumentation, and research authorization are deliberately outside this
    pure function. Provenance fields are requirements, not authentication.
    """
    result = {"schema": "calibration-feasibility-decision-v1",
        "scope": "conditional_on_independently_verified_bound_evidence",
        "empirical_attainment_established": False, "research_execution_authorized": False,
        "confirmation_authorized": False, "population_speedup_established": False}
    try:
        result.update(_assess(policy, evidence))
        try:
            result["evidence_payload_sha256"] = digest(canonical_json(evidence))
        except (ValueError, TypeError, OverflowError):
            # Nonfinite diagnostic inputs cannot be hashed as canonical JSON.
            # Keep an already observed exactness mismatch above missing evidence.
            result["evidence_payload_sha256"] = None
            result["missing_evidence"].append("evidence_has_no_canonical_JSON_encoding")
            if not result["mismatches"]:
                result["decision"] = "inconclusive_missing_required_evidence"
                result["conditions_satisfied"] = False
        result["evidence_kind"] = evidence["evidence_kind"]
        result["policy_payload_sha256"] = POLICY_PAYLOAD_SHA256
    except (EvidenceError, ValueError, TypeError, OverflowError) as error:
        result.update({"decision": "inconclusive_invalid_evidence", "conditions_satisfied": False,
            "error": str(error)[:256]})
    return result


def evaluate_verified_feasibility(policy, evidence, measured):
    """Cross-check loader-issued measured sequences before conditional policy use.

    Timing, preparation, stage maps, model/state agreement, membership, and
    measured worker resources are projected from verified artifacts. Coverage,
    quality, resource-ledger completeness, and scientific-provenance supplements
    still require their independent archive verifiers. No claim of their truth
    follows from this adapter. It performs no new I/O.
    """
    from .measured_analysis import VerifiedMeasuredEvidence, _clean

    def rejected(message):
        return {"schema": "calibration-feasibility-decision-v1",
            "decision": "inconclusive_unmatched_verified_measurements", "conditions_satisfied": False,
            "scope": "conditional_on_independently_verified_bound_evidence", "error": str(message)[:256],
            "empirical_attainment_established": False, "research_execution_authorized": False,
            "confirmation_authorized": False, "population_speedup_established": False,
            "measured_sequence_archive_verified": False,
            "supplement_archive_verification_performed": False}

    if type(measured) is not VerifiedMeasuredEvidence:
        return rejected("use loader-issued VerifiedMeasuredEvidence, not supplied JSON")
    try:
        verified = measured.payload()
        if verified.get("schema") != "verified-measured-evidence-v1" or verified.get("kind") != "sequence_lifetime":
            raise EvidenceError("a complete measured sequence evidence object is required")
        assembled = deepcopy(evidence)
        for key in ("inventory_sha256", "protocol_sha256"):
            if assembled[key] != verified[key]:
                raise EvidenceError("verified " + key + " differs")
        root_map = {root["root_id"]: root for root in assembled["roots"]}
        if len(root_map) != len(assembled["roots"]):
            raise EvidenceError("duplicate evidence root")
        slots = verified["slots"]
        if len(slots) != len(root_map) or {slot["root_id"] for slot in slots} != set(root_map):
            raise EvidenceError("verified root inventory differs; no roots or repetitions may be dropped")
        resources = {row["worker_id"]: row for row in assembled["resources"]["workers"]}
        if len(resources) != len(assembled["resources"]["workers"]):
            raise EvidenceError("duplicate worker evidence")
        seen_workers = set()

        def project(row, slot, method):
            if row.get("outcome") == "mismatch" or row.get("exact_model") is False or row.get("exact_state") is False:
                raise _VerifiedMismatch("verified complete artifacts disagree")
            if row.get("outcome") != "exact_complete" or row.get("exact_model") is not True:
                raise EvidenceError("incomplete or non-exact verified method remains inconclusive")
            if row.get("source_sha256") != assembled["source_sha256"]:
                raise EvidenceError("verified transaction source set differs")
            if not _clean(row.get("instrumentation_state")) or not _clean(row.get("observer_instrumentation_state")):
                raise EvidenceError("verified observation lacks clean supported instrumentation")
            wid = row["worker_id"]
            if wid in seen_workers:
                raise EvidenceError("verified worker reused across distinct original observations")
            seen_workers.add(wid)
            if wid not in resources:
                raise EvidenceError("verified worker missing from declared complete resource inventory")
            usage, limits, outcome = row["worker_resource_usage"], row["worker_limits"], row["worker_outcome"]
            expected_resources = {"worker_id": wid, "receipt_sha256": row["worker_receipt_sha256"],
                "status": "complete", "wall_ns": outcome["elapsed_wall_ns"],
                "cpu_ns": usage["total_cpu_ns"], "wall_limit_seconds": limits["wall_seconds"],
                "cpu_limit_seconds": limits["cpu_seconds"], "file_size_limit_bytes": limits["file_size_bytes"],
                "address_space_limit_bytes": limits["address_space_bytes"],
                "peak_rss_bytes": usage["max_rss_kib"]*1024, "max_artifact_bytes": row["max_artifact_bytes"]}
            if resources[wid] != expected_resources:
                raise EvidenceError("resource summary differs from verified measured worker")
            expected_contract = "model_only" if method == "model_only_fresh" else "canonical_state"
            if row["output_contract"] != expected_contract:
                raise EvidenceError("verified output contract differs")
            return {"status": "complete", "wall_ns": row["wall_ns"], "receipt_sha256": row["receipt_sha256"],
                "output_contract": expected_contract, "boundary": row["boundary"], "cache_mode": row["cache_mode"],
                "execution_mode": row["execution_mode"], "instrumentation_disabled": True,
                "profiler_active": False, "new_latency_observation": True, "source_inputs_unchanged": True,
                "worker_id": wid, "worker_receipt_sha256": row["worker_receipt_sha256"],
                "target_manifest_sha256": row["target_manifest_sha256"],
                "configuration_sha256": slot["configuration_sha256"], "retained_ids_sha256": row["retained_ids_sha256"]}

        for slot in slots:
            root = root_map[slot["root_id"]]
            for key in ("target_manifest_sha256", "configuration_sha256", "source_sha256", "protocol_sha256"):
                if slot[key] != assembled[key]:
                    raise EvidenceError("verified sequence " + key + " differs")
            expected_phase = "software_test" if assembled["evidence_kind"] == "software_test" else "feasibility"
            if (slot.get("phase") != expected_phase or slot.get("repeat_index") != 0
                    or slot.get("execution_mode") != "clean" or slot.get("archive_status") != "sealed"):
                raise EvidenceError("verified sequence is not the complete declared feasibility slot")
            prep = slot["preparation"]
            original_ids = sorted(record["record_id"] for record in root["records"])
            for method in ("repair", "model_only_fresh"):
                if sorted(prep[method]["record_ids"]) != original_ids:
                    raise EvidenceError("verified original preparation membership differs")
            if prep["repair"]["stage_code_sha256"] != prep["model_only_fresh"]["stage_code_sha256"]:
                raise _VerifiedMismatch("original preparation models disagree")
            root["initial_stage_codes"] = deepcopy(prep["repair"]["stage_code_sha256"])
            p_repair = project(prep["repair"], slot, "repair")
            p_fresh = project(prep["model_only_fresh"], slot, "model_only_fresh")
            expected_prep = {"repair": p_repair, "indexed_fresh": deepcopy(p_repair), "model_only_fresh": p_fresh}
            if root["preparation"] != expected_prep:
                raise EvidenceError("supplied preparation terms differ from verified transactions")
            steps = slot["steps"]
            if ([step["request_id"] for step in steps] != root["planned_request_ids"]
                    or len(steps) != len(root["requests"])):
                raise EvidenceError("verified complete request schedule differs")
            retained = set(original_ids)
            for step, request in zip(steps, root["requests"]):
                if step["request_id"] != request["request_id"] or step["newly_deleted_ids"] != request["deleted_ids"]:
                    raise EvidenceError("verified deletion request differs")
                retained -= set(step["newly_deleted_ids"])
                for method in ORACLES:
                    row = step["methods"][method]
                    if sorted(row["record_ids"]) != sorted(retained):
                        raise EvidenceError("verified retained request membership differs")
                    projected = project(row, slot, method)
                    if method in METHODS and request["timings"][method] != projected:
                        raise EvidenceError("supplied timing term differs from verified transaction")
                    if request["models"][method] != row["stage_code_sha256"]:
                        raise EvidenceError("supplied stage map differs from verified model")
                    if method != "model_only_fresh" and request["states"][method] != row["state_sha256"]:
                        raise EvidenceError("supplied canonical state differs from verified artifact")
            for method in METHODS:
                total = root["preparation"][method]["wall_ns"] + sum(q["timings"][method]["wall_ns"] for q in root["requests"])
                if slot["methods"][method].get("outcome") != "exact_complete" or slot["methods"][method].get("wall_ns") != total:
                    raise EvidenceError("verified full lifetime differs from component transactions")
        result = evaluate_feasibility(policy, assembled)
        result.update(measured_sequence_archive_verified=True, measured_evidence_sha256=measured.sha256,
            supplement_archive_verification_performed=False,
            remaining_trust_premises=["coverage diagnostic archives and completeness", "quality archives",
                "phase-ledger and all-worker completeness", "actual scientific workload provenance", "actual target graph and group assignments"])
        return result
    except _VerifiedMismatch as error:
        result = rejected(error)
        result.update(decision="stop_and_repair_implementation", measured_sequence_archive_verified=True)
        return result
    except (KeyError, EvidenceError, ValueError, TypeError, OverflowError) as error:
        return rejected(error)


def lifetime_break_even(preparation_repair_ns, preparation_fresh_ns, paired_request_ns):
    """Exact deterministic lifetime arithmetic, not a timing or probability proof."""
    pr = _int(preparation_repair_ns, "repair preparation")
    pf = _int(preparation_fresh_ns, "fresh preparation")
    debt = pr-pf
    prefixes = []
    repair, fresh = pr, pf
    for index, pair in enumerate(paired_request_ns, 1):
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            raise EvidenceError("each pair contains repair and fresh request costs")
        r, f = (_int(value, "request cost") for value in pair)
        repair += r; fresh += f; debt -= f-r
        prefixes.append({"requests": index, "repair_minus_fresh_ns": debt, "strict_gain": debt < 0})
    return {"repair_lifetime_ns": repair, "fresh_lifetime_ns": fresh,
        "repair_minus_fresh_ns": debt, "strict_gain": debt < 0, "prefixes": prefixes}


def remaining_cost_decision(current_debt_ns, future_saving_bounds_ns):
    """Conditional fixed-horizon cost screen using justified future intervals.

    Each interval bounds fresh minus repair cost for one remaining request. It
    says nothing about completion, exactness, quality, or statistical stopping.
    Missing future bounds give an inconclusive screen.
    """
    if type(current_debt_ns) is not int or current_debt_ns.bit_length() > 128:
        raise EvidenceError("bounded signed integer debt required")
    lower = upper = 0
    for pair in future_saving_bounds_ns:
        if pair is None:
            return {"decision": "inconclusive_missing_future_bound"}
        if (not isinstance(pair, (tuple, list)) or len(pair) != 2
                or any(type(x) is not int or x.bit_length() > 128 for x in pair)
                or pair[0] > pair[1]):
            raise EvidenceError("invalid future saving interval")
        lower += pair[0]; upper += pair[1]
    decision = ("strict_gain_impossible" if upper <= current_debt_ns else
        "strict_gain_guaranteed_if_all_other_assumptions_hold" if lower > current_debt_ns else
        "inconclusive_cost_interval")
    return {"decision": decision, "future_savings_lower_ns": lower, "future_savings_upper_ns": upper}
