"""Deterministic analysis of recorded runs, including unsuccessful requests.

Timing repeats are not independent research units. Intervals resample roots.
This module does not run a model or create empirical observations.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import math
import random
import re
import statistics
from typing import Any, Iterable, Mapping, Sequence


class AnalysisError(ValueError):
    """The records cannot support the requested analysis."""


RUN_SCHEMA = "calibration-experiment-v1"
ANALYSIS_SCHEMA = "calibration-analysis-v1"
KEY_FIELDS = ("configuration_id", "phase", "cache_mode", "root_id", "request_id", "repeat_index")
MODES = {"certified", "identity_only", "fixed_reference", "full_replay"}
OPTIONAL_BINDINGS = ("chart_sha256", "service_manifest_sha256")


def _key(run: Mapping[str, Any]) -> tuple[Any, ...]:
    values = []
    for name in KEY_FIELDS:
        value = run.get(name)
        if name == "repeat_index":
            if type(value) is not int or value < 0:
                raise AnalysisError("repeat_index must be a nonnegative integer")
        elif not isinstance(value, str) or not value:
            raise AnalysisError(f"{name} must be a nonempty string")
        values.append(value)
    return tuple(values)


def _time(value: Any, name: str, *, positive: bool = False) -> int:
    if type(value) is not int or value < int(positive):
        raise AnalysisError(f"{name} must be an integer with valid nanosecond units")
    return value


def _methods(run: Mapping[str, Any]) -> tuple[str, ...]:
    names = run.get("planned_methods")
    if not isinstance(names, list) or not names or len(set(names)) != len(names):
        raise AnalysisError("planned_methods must contain unique method names")
    if not all(isinstance(name, str) and name for name in names):
        raise AnalysisError("planned_methods contains an invalid name")
    return tuple(names)


def _hashes(run: Mapping[str, Any]) -> None:
    for field in ("target_manifest_sha256", "protocol_sha256"):
        if not isinstance(run.get(field), str) or not re.fullmatch(r"[0-9a-f]{64}", run[field]):
            raise AnalysisError(f"{field} must be a lowercase SHA256 digest")
    for field in OPTIONAL_BINDINGS:
        if field in run and (not isinstance(run[field], str) or not re.fullmatch(r"[0-9a-f]{64}", run[field])):
            raise AnalysisError(f"{field} must be a lowercase SHA256 digest")
    mode = run.get("service_mode", "certified")
    if not isinstance(mode, str) or mode not in MODES:
        raise AnalysisError("invalid service_mode")


def validate_run(run: Mapping[str, Any]) -> None:
    """Validate the measured fields without guessing absent outcomes."""
    _key(run)
    _hashes(run)
    if run.get("schema") != RUN_SCHEMA:
        raise AnalysisError("unsupported run schema")
    names = _methods(run)
    if run.get("status") not in {"complete", "failed", "running", "missing"}:
        raise AnalysisError("invalid run status")
    methods = run.get("methods", {})
    if not isinstance(methods, dict) or set(methods) - set(names):
        raise AnalysisError("method outcomes do not match planned_methods")
    if not isinstance(run.get("service_boundary"), str) or not run["service_boundary"]:
        raise AnalysisError("service_boundary must describe the measured arm")
    for name, arm in methods.items():
        if not isinstance(arm, dict):
            raise AnalysisError(f"invalid outcome for {name}")
        if arm.get("status") not in {"complete", "failed", "running", "not_started", "pending_verification"}:
            raise AnalysisError(f"invalid arm status for {name}")
        for field in ("wall_time_ns", "complete_wall_time_ns", "index_preparation_ns"):
            if field in arm and arm[field] is not None:
                _time(arm[field], field)
        for field in ("exact_state_equal", "exact_model_equal"):
            if field in arm and arm[field] is not None and type(arm[field]) is not bool:
                raise AnalysisError(f"{field} must be Boolean or null")


def outcome(arm: Mapping[str, Any] | None, run_status: str) -> str:
    """Treat unverified completion and absent arms as explicit outcomes."""
    if arm is None:
        return "missing_run" if run_status == "missing" else "not_started"
    if arm.get("exact_state_equal") is False or arm.get("exact_model_equal") is False:
        return "mismatch"
    if arm.get("status") == "pending_verification":
        return "not_verified"
    if arm.get("status") != "complete":
        failure = arm.get("failure")
        reason = arm.get("failure_kind") or (failure.get("kind") if isinstance(failure, dict) else None)
        return str(reason) if reason else str(arm.get("status", "failed"))
    if arm.get("exact_state_equal") is not True or arm.get("exact_model_equal") is not True:
        return "not_verified"
    if arm.get("complete_wall_time_ns") is None:
        return "missing_time"
    _time(arm["complete_wall_time_ns"], "complete_wall_time_ns", positive=True)
    return "exact_complete"


def percentile(values: Sequence[float], probability: float) -> float:
    if not values or not 0 <= probability <= 1:
        raise AnalysisError("invalid percentile input")
    ordered = sorted(values)
    place = probability * (len(ordered) - 1)
    low = math.floor(place)
    high = math.ceil(place)
    return ordered[low] + (place - low) * (ordered[high] - ordered[low])


def root_interval(values: Sequence[float], *, seed: int, draws: int, confidence: float) -> list[float] | None:
    """Percentile interval for an equal-root mean, conditional on observed roots."""
    if type(seed) is not int or type(draws) is not int or draws < 1 or type(confidence) not in (float, int) or not 0 < confidence < 1:
        raise AnalysisError("invalid bootstrap settings")
    if len(values) < 2:
        return None
    rng = random.Random(seed)
    estimates = [statistics.fmean(rng.choices(values, k=len(values))) for _ in range(draws)]
    alpha = (1 - confidence) / 2
    return [percentile(estimates, alpha), percentile(estimates, 1 - alpha)]


def materialize_plan(runs: Iterable[Mapping[str, Any]], planned_runs: Iterable[Mapping[str, Any]] | None) -> list[dict]:
    """Add missing planned attempts. Reject duplicates and unplanned observations."""
    observed = {}
    for run in runs:
        validate_run(run)
        key = _key(run)
        if key in observed:
            raise AnalysisError("duplicate run identity")
        observed[key] = dict(run)
    if planned_runs is None:
        if any(run["phase"] == "confirmation" for run in observed.values()):
            raise AnalysisError("confirmation requires the frozen planned-run inventory")
        return [observed[key] for key in sorted(observed)]
    plan = {}
    for item in planned_runs:
        key = _key(item)
        _methods(item)
        _hashes(item)
        if key in plan:
            raise AnalysisError("duplicate planned run identity")
        if not item.get("service_boundary"):
            raise AnalysisError("plan lacks service_boundary")
        plan[key] = item
    if observed.keys() - plan.keys():
        raise AnalysisError("observed run is absent from the plan")
    output = []
    for key in sorted(plan):
        item = plan[key]
        if key in observed:
            run = observed[key]
            if item.get("service_mode", "certified") != run.get("service_mode", "certified"):
                raise AnalysisError("planned service_mode does not match the run")
            for field in ("planned_methods", "service_boundary", "target_manifest_sha256", "protocol_sha256", *OPTIONAL_BINDINGS):
                if field in item and item[field] != run.get(field):
                    raise AnalysisError(f"planned {field} does not match the run")
            output.append(run)
        else:
            output.append(dict(item, schema=RUN_SCHEMA, status="missing", methods={}))
    return output


def analyze_runs(
    runs: Iterable[Mapping[str, Any]], *, planned_runs: Iterable[Mapping[str, Any]] | None = None,
    baseline: str = "indexed_fresh", candidate: str = "repair", seed: int = 20261004,
    draws: int = 2000, confidence: float = 0.95,
) -> dict[str, Any]:
    """Analyze each configuration separately. All planned outcomes keep their denominators."""
    if baseline == candidate:
        raise AnalysisError("baseline and candidate must differ")
    root_interval([], seed=seed, draws=draws, confidence=confidence)
    rows = materialize_plan(runs, planned_runs)
    strata = defaultdict(list)
    for run in rows:
        label = (run["configuration_id"], run["phase"], run["cache_mode"], run["service_boundary"])
        strata[label].append(run)
    summaries = []
    for stratum, entries in sorted(strata.items()):
        for field in ("target_manifest_sha256", "protocol_sha256"):
            if len({run[field] for run in entries}) != 1:
                raise AnalysisError(f"one analysis stratum mixes different {field}")
        if len({run.get("service_mode", "certified") for run in entries}) != 1:
            raise AnalysisError("one analysis stratum mixes different service_mode")
        observed = [run for run in entries if run["status"] != "missing"]
        bindings = {}
        for field in OPTIONAL_BINDINGS:
            present = [run for run in observed if field in run]
            if present and len(present) != len(observed):
                raise AnalysisError(f"one analysis stratum has partial {field} bindings")
            values = {run[field] for run in entries if field in run}
            if len(values) > 1:
                raise AnalysisError(f"one analysis stratum mixes different {field}")
            if values:
                bindings[field] = next(iter(values))
        attempts = defaultdict(Counter)
        by_request = defaultdict(list)
        measured = defaultdict(list)
        for run in entries:
            by_request[(run["root_id"], run["request_id"])].append(run)
            for name in _methods(run):
                arm = run.get("methods", {}).get(name)
                attempts[name][outcome(arm, run["status"])] += 1
                if arm and arm.get("wall_time_ns") is not None:
                    measured[name].append(arm["wall_time_ns"])
        roots = sorted({root for root, _ in by_request})
        logs_by_root = defaultdict(list)
        success_by_method = defaultdict(lambda: defaultdict(list))
        paired_outcomes = Counter()
        request_rows = []
        for (root, request), repetitions in sorted(by_request.items()):
            names = sorted({name for run in repetitions for name in _methods(run)})
            complete, medians = {}, {}
            for name in names:
                arms = [(run.get("methods", {}).get(name), run["status"]) for run in repetitions]
                # Different method plans across repeats are not matched repetitions.
                planned_everywhere = all(name in _methods(run) for run in repetitions)
                complete[name] = planned_everywhere and all(outcome(arm, status) == "exact_complete" for arm, status in arms)
                success_by_method[name][root].append(float(complete[name]))
                if complete[name]:
                    medians[name] = statistics.median(arm["complete_wall_time_ns"] for arm, _ in arms)
            if not all(all(name in _methods(run) for name in (baseline, candidate)) for run in repetitions):
                pair_status = "not_jointly_planned"
            elif complete[baseline] and complete[candidate]:
                pair_status = "both_exact_complete"
                logs_by_root[root].append(math.log(medians[baseline]) - math.log(medians[candidate]))
            elif complete[baseline]:
                pair_status = "baseline_only_exact_complete"
            elif complete[candidate]:
                pair_status = "candidate_only_exact_complete"
            else:
                pair_status = "neither_exact_complete"
            paired_outcomes[pair_status] += 1
            request_rows.append({"root_id": root, "request_id": request, "repetitions": len(repetitions),
                                 "pair_outcome": pair_status, "median_time_ns": medians,
                                 "all_repetitions_exact_complete": complete})
        method_rows = {}
        for name in sorted(attempts):
            root_rates = [statistics.fmean(success_by_method[name][root]) for root in sorted(success_by_method[name])]
            method_rows[name] = {"attempts": sum(attempts[name].values()), "outcomes": dict(sorted(attempts[name].items())),
                                 "observed_elapsed_ns_sum": sum(measured[name]), "attempts_with_observed_elapsed": len(measured[name]),
                                 "all_repetitions_complete_rate_equal_root": statistics.fmean(root_rates),
                                 "complete_rate_root_interval": root_interval(root_rates, seed=seed, draws=draws, confidence=confidence)}
        root_logs = {root: statistics.fmean(logs) for root, logs in sorted(logs_by_root.items())}
        log_interval = root_interval(list(root_logs.values()), seed=seed, draws=draws, confidence=confidence)
        summary = dict(zip(("configuration_id", "phase", "cache_mode", "service_boundary"), stratum))
        summary.update({field: entries[0][field] for field in ("target_manifest_sha256", "protocol_sha256")})
        summary.update(bindings, service_mode=entries[0].get("service_mode", "certified"))
        summary.update({"independent_root_count": len(roots), "planned_request_count": len(by_request),
                        "planned_attempt_count": len(entries), "methods": method_rows,
                        "paired_request_outcomes": dict(sorted(paired_outcomes.items())), "requests": request_rows,
                        "conditional_ratio": {
                            "definition": "baseline/candidate; median repeats; mean request logs within root; equal-root mean",
                            "eligible_roots": len(root_logs), "omitted_roots": len(roots) - len(root_logs),
                            "eligible_requests": sum(len(values) for values in logs_by_root.values()),
                            "estimate": math.exp(statistics.fmean(root_logs.values())) if root_logs else None,
                            "root_interval": [math.exp(value) for value in log_interval] if log_interval else None,
                            "root_ratios": {root: math.exp(value) for root, value in root_logs.items()},
                            "scope": "Conditional on both methods completing every planned repeat exactly."}})
        summaries.append(summary)
    return {"schema": ANALYSIS_SCHEMA, "baseline": baseline, "candidate": candidate,
            "planned_inventory_supplied": planned_runs is not None,
            "interval": {"method": "percentile bootstrap of independent roots", "seed": seed,
                         "draws": draws, "confidence": confidence, "single_root_interval": None},
            "interpretation": ["Conditional speed ratios exclude unsuccessful pairs; outcome counts do not.",
                               "Elapsed failure costs are consumed resources, not time to an exact answer.",
                               "Timing repeats do not increase the independent root count.",
                               "The ratio covers only the declared service boundary.",
                               "Root intervals require the protocol's independence assumptions."],
            "strata": summaries}


def lifetime_costs(extra_preparation_ns: int, paired_costs_ns: Sequence[tuple[int, int]]) -> dict[str, Any]:
    """Return observed cumulative savings. Input order must follow the deletion sequence."""
    _time(extra_preparation_ns, "extra_preparation_ns")
    balance = -extra_preparation_ns
    trajectory = []
    first = None
    for index, (baseline_cost, candidate_cost) in enumerate(paired_costs_ns, start=1):
        _time(baseline_cost, "baseline_cost")
        _time(candidate_cost, "candidate_cost")
        balance += baseline_cost - candidate_cost
        trajectory.append(balance)
        if balance >= 0 and first is None:
            first = index
    return {"extra_preparation_ns": extra_preparation_ns, "cumulative_net_savings_ns": trajectory,
            "first_observed_nonnegative_request": first, "last_observed_net_savings_ns": balance,
            "scope": "Observed paired sequence only; later requests can reverse a crossing."}


def projected_break_even(extra_preparation_ns: int, assumed_saving_per_request_ns: int) -> int | None:
    """Project a crossing under constant positive saving. This is not an observed result."""
    _time(extra_preparation_ns, "extra_preparation_ns")
    if type(assumed_saving_per_request_ns) is not int:
        raise AnalysisError("assumed saving must use integer nanoseconds")
    if extra_preparation_ns == 0:
        return 0
    if assumed_saving_per_request_ns <= 0:
        return None
    return (extra_preparation_ns + assumed_saving_per_request_ns - 1) // assumed_saving_per_request_ns
