"""Frozen isolated comparison inventories and durable local campaign execution."""
from __future__ import annotations

from pathlib import Path, PurePosixPath
import time

from .experiment_campaign import _phase_caps, _validate_confirmation_product
from .experiment_inventory import (EXECUTION_MODE as WARM_EXECUTION_MODE, _relative,
    analysis_plan as warm_analysis_plan, build_campaign, source_hashes, validate_campaign)
from .experiment_runner import METHODS, _failure, _local, _read_json
from .isolated_comparison import (BOUNDARY, CACHE_MODE, _verify_completed,
    _verify_unfinished_artifacts, isolated_source_hashes, run_isolated, validate_isolated_plan)
from .phase_budget import PhaseBudget
from .run_store import RunStore, canonical_json, digest, strict_json
from .worker_control import WorkerLimits

EXTRA_FIELDS = {"isolated_plan_path", "isolated_plan_sha256", "isolated_plan_payload"}


def _base_inventory(inventory):
    """Reuse membership validators without adopting their warm execution path."""
    if not isinstance(inventory, dict) or inventory.get("schema") != "calibration-isolated-campaign-v1":
        raise ValueError("invalid isolated campaign schema")
    base = strict_json(canonical_json(inventory))
    base["schema"] = "calibration-campaign-v1"
    if base.get("execution_mode") != CACHE_MODE:
        raise ValueError("invalid isolated campaign execution mode")
    base["execution_mode"] = WARM_EXECUTION_MODE
    if not isinstance(base.get("entries"), list):
        raise ValueError("isolated campaign entries require a list")
    for entry in base["entries"]:
        if not isinstance(entry, dict) or not EXTRA_FIELDS <= set(entry):
            raise ValueError("isolated campaign entry lacks plan bindings")
        for field in EXTRA_FIELDS:
            del entry[field]
    return validate_campaign(base)


def validate_isolated_inventory(inventory):
    base = _base_inventory(inventory)
    paths = set()
    configurations = {}
    for entry in inventory["entries"]:
        if type(entry["analysis_group"]) is not str or not entry["analysis_group"]:
            raise ValueError("analysis groups require nonempty strings")
        plan_path = _relative(entry["isolated_plan_path"])
        if plan_path in paths:
            raise ValueError("duplicate isolated plan path")
        paths.add(plan_path)
        plan = entry["isolated_plan_payload"]
        fields = {"schema", "manifest_path", "manifest_payload", "manifest_binding_sha256",
                  "target_manifest_sha256", "worker_limits", "source_sha256"}
        if (not isinstance(plan, dict) or not fields <= set(plan) or set(plan) - fields - {"quality"}
                or plan["schema"] != "calibration-isolated-plan-v1"
                or ("quality" in plan and plan["quality"] != "heldout_nll")):
            raise ValueError("invalid bound isolated plan")
        if digest(canonical_json(plan)) != entry["isolated_plan_sha256"]:
            raise ValueError("isolated plan hash differs from payload")
        manifest_path = str(PurePosixPath(plan_path).parent / _relative(plan["manifest_path"]))
        if _relative(manifest_path) != entry["manifest_path"]:
            raise ValueError("isolated plan resolves to a different manifest")
        for field in ("manifest_payload", "manifest_binding_sha256", "target_manifest_sha256"):
            if plan[field] != entry[field]:
                raise ValueError("isolated plan and entry bindings differ")
        if plan["worker_limits"] != base["worker_limits"] or plan["source_sha256"] != base["source_sha256"]:
            raise ValueError("isolated plan limits or sources differ from campaign")
        manifest = entry["manifest_payload"]
        settings = {"target": entry["target_manifest_sha256"], "chart": manifest.get("chart"),
                    "service_mode": manifest.get("service_mode", "certified"),
                    "service_family": manifest.get("service_family", "response"),
                    "verifier_policy": manifest.get("verifier_policy", "spectral"),
                    "quality": plan.get("quality")}
        key = (entry["configuration_id"], entry["phase"])
        if key in configurations and configurations[key] != settings:
            raise ValueError("one isolated configuration mixes target or service settings")
        configurations[key] = settings
    return strict_json(canonical_json(inventory))


def build_isolated_campaign(*, campaign_id, protocol_path, worker_limits, plans, workloads, sources):
    """Freeze declared inputs without loading checkpoints or executing methods."""
    if not isinstance(plans, list) or not plans:
        raise ValueError("isolated plans are required")
    manifests = []
    for item in plans:
        if not isinstance(item, dict) or set(item) != {"plan_path", "plan"}:
            raise ValueError("each isolated plan requires plan_path and plan")
        plan = item["plan"]
        path = _relative(item["plan_path"])
        manifests.append({"manifest_path": str(PurePosixPath(path).parent / _relative(plan["manifest_path"])),
                          "manifest": plan["manifest_payload"],
                          "target_manifest_sha256": plan["target_manifest_sha256"]})
    result = build_campaign(campaign_id=campaign_id, protocol_path=protocol_path, worker_limits=worker_limits,
                            manifests=manifests, workloads=workloads, source_sha256=sources)
    result.update(schema="calibration-isolated-campaign-v1", execution_mode=CACHE_MODE)
    for entry, item in zip(result["entries"], plans):
        entry.update(isolated_plan_path=item["plan_path"], isolated_plan_payload=item["plan"],
                     isolated_plan_sha256=digest(canonical_json(item["plan"])))
    return validate_isolated_inventory(result)


def validate_isolated_campaign_files(path, *, execute=False):
    inventory_path = Path(path).absolute()
    inventory, raw = _read_json(inventory_path)
    validate_isolated_inventory(inventory)
    if raw != canonical_json(inventory):
        raise ValueError("isolated inventory requires canonical JSON")
    if inventory["source_sha256"] != isolated_source_hashes():
        raise ValueError("isolated inventory sources differ from executable sources")
    protocol_path = _local(inventory_path.parent, inventory["protocol_path"])
    protocol, protocol_raw = _read_json(protocol_path)
    if not isinstance(protocol, dict) or protocol.get("planned_inventory_sha256") != digest(raw):
        raise ValueError("protocol does not bind the exact isolated inventory")
    _validate_confirmation_product(inventory, protocol)
    if any(entry["phase"] == "confirmation" for entry in inventory["entries"]):
        if (protocol.get("schema") != "calibration-protocol-v1" or protocol.get("status") != "frozen_confirmation"
                or protocol.get("blocked_fields") != []):
            raise ValueError("isolated confirmation requires a frozen protocol without blocked fields")
    limits = WorkerLimits.from_payload(inventory["worker_limits"])
    limits.check_host()
    checked = []
    for entry in inventory["entries"]:
        if execute and entry["phase"] != "software_test" and "experiments_paused" in str(protocol.get("status", "")):
            raise ValueError("the protocol keeps research experiments paused")
        plan_path = _local(inventory_path.parent, entry["isolated_plan_path"])
        plan = validate_isolated_plan(plan_path, execute=False)
        if plan["plan_sha256"] != entry["isolated_plan_sha256"] or plan["plan"] != entry["isolated_plan_payload"]:
            raise ValueError("isolated plan file differs from inventory")
        if plan["protocol_path"] != protocol_path or plan["protocol_sha256"] != digest(protocol_raw):
            raise ValueError("isolated plan refers to another protocol")
        if plan["manifest_path"] != _local(inventory_path.parent, entry["manifest_path"]):
            raise ValueError("isolated plan refers to another manifest")
        checked.append({"entry": entry, "plan_path": plan_path, "manifest_sha256": plan["manifest_sha256"]})
    phase_caps = _phase_caps({"entries": [entry for entry in inventory["entries"]
        for _ in range(5 if "quality" in entry["isolated_plan_payload"] else 4)]}, protocol, limits)
    return {"inventory": inventory, "raw": raw, "inventory_path": inventory_path,
            "inventory_sha256": digest(raw), "protocol": protocol, "protocol_path": protocol_path,
            "protocol_sha256": digest(protocol_raw), "phase_cpu_seconds": phase_caps,
            "limits": limits, "checked": checked}


def verify_isolated_membership(inventory_path, run_id, plan_path, *, execute):
    """Read and verify the complete inventory; a caller flag never grants membership."""
    checked = validate_isolated_campaign_files(inventory_path, execute=execute)
    matches = [item for item in checked["checked"] if item["entry"]["run_id"] == run_id]
    if len(matches) != 1 or matches[0]["plan_path"] != Path(plan_path).absolute().resolve():
        raise ValueError("isolated plan is absent from the verified inventory entry")
    return checked, matches[0]


def isolated_analysis_plan(inventory, *, protocol_sha256, analysis_group="primary"):
    validate_isolated_inventory(inventory)
    result = warm_analysis_plan(_base_inventory(inventory), protocol_sha256=protocol_sha256,
                                analysis_group=analysis_group)
    result["campaign_sha256"] = digest(canonical_json(inventory))
    for row in result["planned_runs"]:
        row.update(cache_mode=CACHE_MODE, service_boundary=BOUNDARY)
    return result


def _budget(checked):
    return PhaseBudget(checked["protocol_path"].parent / ("phase-cpu-budget-" + checked["protocol_sha256"]),
        identity={"protocol_sha256": checked["protocol_sha256"],
                  "source_sha256": source_hashes(Path(__file__).resolve().parents[1])},
        phase_cpu_seconds=checked["phase_cpu_seconds"])


def _verify_saved_run(root, row, budget):
    path = root / "runs" / row["run_id"] / "result.json"
    expected = row.get("result_sha256")
    if expected is None:
        if path.exists():
            raise ValueError("isolated campaign acquired an unrecorded result")
        return
    record, raw = _read_json(path)
    if digest(raw) != expected:
        raise ValueError("isolated campaign result receipt changed")
    identity, _ = _read_json(path.parent / "identity.json")
    completed = RunStore(path.parent, identity).completed()
    if completed is None:
        _verify_unfinished_artifacts(path.parent, record)
        _verify_completed(path.parent, record, budget)
    else:
        _verify_completed(path.parent, completed, budget)


def run_isolated_campaign(path, output, *, validate_only=False):
    checked = validate_isolated_campaign_files(path, execute=not validate_only)
    inventory = checked["inventory"]
    if validate_only:
        return {"schema": "isolated-campaign-validation-v1", "status": "validated",
                "inventory_sha256": checked["inventory_sha256"], "planned_runs": len(inventory["entries"]),
                "empirical_work_executed": False, "checkpoint_parameters_loaded": False,
                "phase_cpu_seconds": checked["phase_cpu_seconds"]}
    budget = _budget(checked)
    store = RunStore(output, {"inventory_sha256": checked["inventory_sha256"],
        "protocol_sha256": checked["protocol_sha256"], "source_sha256": inventory["source_sha256"],
        "phase_budget_binding_sha256": budget.identity_digest})
    previous = store.completed()
    if previous is not None:
        for row in previous["runs"]:
            _verify_saved_run(store.root, row, budget)
        return previous
    store.claim()
    result = {"schema": "isolated-campaign-result-v1", "status": "running", "campaign_id": inventory["campaign_id"],
              "inventory_sha256": checked["inventory_sha256"], "protocol_sha256": checked["protocol_sha256"],
              "cache_mode": CACHE_MODE, "planned_runs": len(inventory["entries"]),
              "runs": [{"run_id": entry["run_id"], "status": "not_started"} for entry in inventory["entries"]]}
    started = time.perf_counter_ns()
    try:
        store.write_artifact("inventory.json", checked["raw"])
        plans = {group: isolated_analysis_plan(inventory, protocol_sha256=checked["protocol_sha256"], analysis_group=group)
                 for group in {entry["analysis_group"] for entry in inventory["entries"]}}
        for group, analysis in sorted(plans.items()):
            # Analysis group labels are data, never filenames.
            store.write_artifact("analysis-plan-" + digest(group.encode()) + ".json", canonical_json(analysis))
        for index, item in enumerate(checked["checked"]):
            entry = item["entry"]
            current = validate_isolated_campaign_files(path, execute=True)
            if any(current[key] != checked[key] for key in ("inventory_sha256", "protocol_sha256")):
                raise ValueError("isolated campaign changed during execution")
            directory = store.root / "runs" / entry["run_id"]
            row = {"run_id": entry["run_id"], "analysis_group": entry["analysis_group"], "status": "running"}
            result["runs"][index] = row
            store.write_status(result)
            try:
                comparison = run_isolated(item["plan_path"], directory, inventory_path=checked["inventory_path"],
                                          inventory_run_id=entry["run_id"])
                row.update(status="complete" if comparison["outcome"] == "complete" else "failed", analysis=comparison)
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as exc:
                plan_rows = plans[entry["analysis_group"]]["planned_runs"]
                planned = next(value for value in plan_rows if all(value[field] == entry[field]
                    for field in ("configuration_id", "phase", "root_id", "request_id", "repeat_index")))
                failure = _failure(exc)
                row.update(status="failed", failure=failure, analysis=dict(planned,
                    schema="calibration-experiment-v1", status="failed", methods={method: {
                        "status": "not_started", "failure": dict(failure, kind="comparison_failed")}
                        for method in METHODS}))
            receipt = directory / "result.json"
            row["result_sha256"] = digest(receipt.read_bytes()) if receipt.is_file() else None
            store.write_artifact(entry["run_id"] + "-outcome.json", canonical_json(row))
            store.write_status(result)
        result.update(status="complete", outcome="complete" if all(row["status"] == "complete" for row in result["runs"]) else "failed",
                      completed_runs=sum(row["status"] == "complete" for row in result["runs"]),
                      failed_runs=sum(row["status"] != "complete" for row in result["runs"]),
                      controller_wall_ns_before_commit=time.perf_counter_ns() - started,
                      phase_cpu_budget_at_completion=budget.snapshot(),
                      controller_completion_means="planned outcomes are sealed; inspect outcome and per-run status")
        return store.finish(result)
    except BaseException as exc:
        store.write_status(dict(result, status="failed", failure=_failure(exc)))
        raise
    finally:
        store.close()
