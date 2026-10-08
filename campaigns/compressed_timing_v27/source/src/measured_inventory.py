"""Frozen measured four-method comparison inventories and durable local campaign execution."""
from __future__ import annotations

from pathlib import Path, PurePosixPath
import time

from .experiment_campaign import _phase_caps, _validate_confirmation_product
from .experiment_inventory import (EXECUTION_MODE as WARM_EXECUTION_MODE, _relative,
    analysis_plan as warm_analysis_plan, build_campaign, source_hashes, validate_campaign)
from .experiment_runner import _failure, _local, _read_json, _integer, _text
from .measured_comparison import (BOUNDARY, CACHE_MODE,
    measured_source_hashes, run_measured_comparison, validate_measured_plan, verify_measured_archive)
from .phase_budget import PhaseBudget
from .run_store import RunStore, canonical_json, digest, strict_json
from .worker_control import WorkerLimits
from .request_workload import SeedStream
from .runtime_contract import capture_runtime_contract, validate_runtime_contract, verify_runtime_contract

METHODS = ("model_only_fresh", "repair", "indexed_fresh", "direct_fresh")
EXTRA_FIELDS = {"measured_plan_path", "measured_plan_sha256", "measured_plan_payload", "measured_method_order"}


def measured_counterbalanced_orders(*, seed, root_id, request_id, repeats):
    """Four-position blocks; reversal changes orientation after each block."""
    _integer(seed, "seed")
    _integer(repeats, "repeats", 1)
    _text(root_id, "root ID")
    _text(request_id, "request ID")
    first = SeedStream(seed, root_id + "/" + request_id + "/measured-method-order-v1").permutation(METHODS)
    result = []
    for index in range(repeats):
        order = first if (index // 4) % 2 == 0 else list(reversed(first))
        shift = index % 4
        result.append(order[shift:] + order[:shift])
    return result


def _base_inventory(inventory):
    """Reuse membership validators without adopting their warm execution path."""
    if not isinstance(inventory, dict) or inventory.get("schema") != "calibration-measured-campaign-v1":
        raise ValueError("invalid measured campaign schema")
    base = strict_json(canonical_json(inventory))
    validate_runtime_contract(base.pop("runtime_contract", None))
    base["schema"] = "calibration-campaign-v1"
    if base.get("execution_mode") != CACHE_MODE:
        raise ValueError("invalid measured campaign execution mode")
    base["execution_mode"] = WARM_EXECUTION_MODE
    if not isinstance(base.get("entries"), list):
        raise ValueError("measured campaign entries require a list")
    for entry in base["entries"]:
        if not isinstance(entry, dict) or not EXTRA_FIELDS <= set(entry):
            raise ValueError("measured campaign entry lacks plan bindings")
        for field in EXTRA_FIELDS:
            del entry[field]
    return validate_campaign(base)


def validate_measured_inventory(inventory):
    base = _base_inventory(inventory)
    paths = set()
    configurations = {}
    seeds = {workload["root_id"]: workload["seed"] for workload in base["workloads"]}
    for entry in inventory["entries"]:
        if type(entry["analysis_group"]) is not str or not entry["analysis_group"]:
            raise ValueError("analysis groups require nonempty strings")
        plan_path = _relative(entry["measured_plan_path"])
        if plan_path in paths:
            raise ValueError("duplicate measured plan path")
        paths.add(plan_path)
        plan = entry["measured_plan_payload"]
        fields = {"schema", "manifest_path", "manifest_payload", "manifest_binding_sha256",
                  "target_manifest_sha256", "worker_limits", "source_sha256", "quality", "method_order", "execution_mode"}
        if (not isinstance(plan, dict) or set(plan) != fields
                or plan["schema"] != "calibration-measured-plan-v1"
                or plan["quality"] not in ("none", "heldout_nll")
                or plan["execution_mode"] not in ("clean", "diagnostic")):
            raise ValueError("invalid bound measured plan")
        expected_order = measured_counterbalanced_orders(seed=seeds[entry["root_id"]], root_id=entry["root_id"],
            request_id=entry["request_id"], repeats=entry["repeat_index"] + 1)[-1]
        if plan["method_order"] != expected_order or entry["measured_method_order"] != expected_order:
            raise ValueError("measured method order violates the frozen four-arm counterbalance")
        if digest(canonical_json(plan)) != entry["measured_plan_sha256"]:
            raise ValueError("measured plan hash differs from payload")
        manifest_path = str(PurePosixPath(plan_path).parent / _relative(plan["manifest_path"]))
        if _relative(manifest_path) != entry["manifest_path"]:
            raise ValueError("measured plan resolves to a different manifest")
        for field in ("manifest_payload", "manifest_binding_sha256", "target_manifest_sha256"):
            if plan[field] != entry[field]:
                raise ValueError("measured plan and entry bindings differ")
        if plan["worker_limits"] != base["worker_limits"] or plan["source_sha256"] != base["source_sha256"]:
            raise ValueError("measured plan limits or sources differ from campaign")
        manifest = entry["manifest_payload"]
        settings = {"target": entry["target_manifest_sha256"], "chart": manifest.get("chart"),
                    "service_mode": manifest.get("service_mode", "certified"),
                    "service_family": manifest.get("service_family", "response"),
                    "verifier_policy": manifest.get("verifier_policy", "spectral"),
                    "quality": plan["quality"], "execution_mode": plan["execution_mode"]}
        key = (entry["configuration_id"], entry["phase"])
        if key in configurations and configurations[key] != settings:
            raise ValueError("one measured configuration mixes target or service settings")
        configurations[key] = settings
    return strict_json(canonical_json(inventory))


def build_measured_campaign(*, campaign_id, protocol_path, worker_limits, plans, workloads, sources, runtime_contract=None):
    """Freeze declared inputs without loading checkpoints or executing methods."""
    if not isinstance(plans, list) or not plans:
        raise ValueError("measured plans are required")
    manifests = []
    for item in plans:
        if not isinstance(item, dict) or set(item) != {"plan_path", "plan"}:
            raise ValueError("each measured plan requires plan_path and plan")
        plan = item["plan"]
        path = _relative(item["plan_path"])
        manifests.append({"manifest_path": str(PurePosixPath(path).parent / _relative(plan["manifest_path"])),
                          "manifest": plan["manifest_payload"],
                          "target_manifest_sha256": plan["target_manifest_sha256"]})
    result = build_campaign(campaign_id=campaign_id, protocol_path=protocol_path, worker_limits=worker_limits,
                            manifests=manifests, workloads=workloads, source_sha256=sources)
    result.update(schema="calibration-measured-campaign-v1", execution_mode=CACHE_MODE,
                  runtime_contract=validate_runtime_contract(capture_runtime_contract() if runtime_contract is None else runtime_contract))
    for entry, item in zip(result["entries"], plans):
        entry.update(measured_plan_path=item["plan_path"], measured_plan_payload=item["plan"],
                     measured_plan_sha256=digest(canonical_json(item["plan"])),
                     measured_method_order=item["plan"]["method_order"])
    return validate_measured_inventory(result)


def validate_measured_campaign_files(path, *, execute=False):
    inventory_path = Path(path).absolute()
    inventory, raw = _read_json(inventory_path)
    validate_measured_inventory(inventory)
    if raw != canonical_json(inventory):
        raise ValueError("measured inventory requires canonical JSON")
    if inventory["source_sha256"] != measured_source_hashes():
        raise ValueError("measured inventory sources differ from executable sources")
    verify_runtime_contract(inventory["runtime_contract"])
    protocol_path = _local(inventory_path.parent, inventory["protocol_path"])
    protocol, protocol_raw = _read_json(protocol_path)
    if not isinstance(protocol, dict) or protocol.get("planned_inventory_sha256") != digest(raw):
        raise ValueError("protocol does not bind the exact measured inventory")
    _validate_confirmation_product(inventory, protocol)
    if any(entry["phase"] == "confirmation" for entry in inventory["entries"]):
        if (protocol.get("schema") != "calibration-protocol-v1" or protocol.get("status") != "frozen_confirmation"
                or protocol.get("blocked_fields") != []):
            raise ValueError("measured confirmation requires a frozen protocol without blocked fields")
        if any(entry["phase"] == "confirmation" and entry["measured_plan_payload"]["execution_mode"] != "clean"
               for entry in inventory["entries"]):
            raise ValueError("confirmation primary timing requires clean instrumentation")
    limits = WorkerLimits.from_payload(inventory["worker_limits"])
    limits.check_host()
    checked = []
    for entry in inventory["entries"]:
        if execute and entry["phase"] != "software_test" and "experiments_paused" in str(protocol.get("status", "")):
            raise ValueError("the protocol keeps research experiments paused")
        plan_path = _local(inventory_path.parent, entry["measured_plan_path"])
        plan = validate_measured_plan(plan_path, execute=False)
        if plan["plan_sha256"] != entry["measured_plan_sha256"] or plan["plan"] != entry["measured_plan_payload"]:
            raise ValueError("measured plan file differs from inventory")
        if plan["protocol_path"] != protocol_path or plan["protocol_sha256"] != digest(protocol_raw):
            raise ValueError("measured plan refers to another protocol")
        if plan["manifest_path"] != _local(inventory_path.parent, entry["manifest_path"]):
            raise ValueError("measured plan refers to another manifest")
        checked.append({"entry": entry, "plan_path": plan_path, "manifest_sha256": plan["manifest_sha256"]})
    phase_caps = _phase_caps({"entries": [entry for entry in inventory["entries"]
        for _ in range(6 if entry["measured_plan_payload"]["quality"] == "heldout_nll" else 5)]}, protocol, limits)
    return {"inventory": inventory, "raw": raw, "inventory_path": inventory_path,
            "inventory_sha256": digest(raw), "protocol": protocol, "protocol_path": protocol_path,
            "protocol_sha256": digest(protocol_raw), "phase_cpu_seconds": phase_caps,
            "limits": limits, "checked": checked}


def verify_measured_membership(inventory_path, run_id, plan_path, *, execute):
    """Read and verify the complete inventory; a caller flag never grants membership."""
    checked = validate_measured_campaign_files(inventory_path, execute=execute)
    matches = [item for item in checked["checked"] if item["entry"]["run_id"] == run_id]
    if len(matches) != 1 or matches[0]["plan_path"] != Path(plan_path).absolute().resolve():
        raise ValueError("measured plan is absent from the verified inventory entry")
    return checked, matches[0]


def verify_model_manifest(inventory_path, run_id, plan_path, manifest_path, *, sequence_step=None, execute=True):
    """Authorize a leaf from actual frozen inventory contents, never a Boolean grant.

    Sequence inventories additionally verify the derived cumulative manifest
    against the exact ordered step. Returned values are JSON-safe and can be
    included in a durable child identity without depending on Python objects.
    """
    payload, _ = _read_json(Path(inventory_path).absolute())
    if payload.get("schema") == "calibration-measured-sequence-campaign-v1":
        from .measured_sequence import verify_measured_sequence_manifest
        return verify_measured_sequence_manifest(inventory_path, run_id, plan_path, manifest_path,
                                                  sequence_step=sequence_step, execute=execute)
    if payload.get("schema") != "calibration-measured-campaign-v1":
        raise ValueError("model leaf requires a supported measured inventory")
    if sequence_step is not None:
        raise ValueError("single-request inventory cannot authorize a sequence step")
    checked, item = verify_measured_membership(inventory_path, run_id, plan_path, execute=execute)
    expected_path = _local(checked["inventory_path"].parent, item["entry"]["manifest_path"])
    if Path(manifest_path).absolute().resolve() != expected_path:
        raise ValueError("model leaf manifest path differs from verified inventory")
    _, raw = _read_json(expected_path)
    if digest(raw) != item["manifest_sha256"]:
        raise ValueError("model leaf manifest changed during inventory verification")
    return {"inventory_sha256": checked["inventory_sha256"], "protocol_sha256": checked["protocol_sha256"],
            "source_sha256": checked["inventory"]["source_sha256"],
            "target_manifest_sha256": item["entry"]["target_manifest_sha256"],
            "manifest_sha256": item["manifest_sha256"], "manifest_path": str(expected_path),
            "plan_sha256": item["entry"]["measured_plan_sha256"],
            "execution_mode": item["entry"]["measured_plan_payload"]["execution_mode"],
            "quality": item["entry"]["measured_plan_payload"]["quality"],
            "runtime_contract_sha256": digest(canonical_json(checked["inventory"]["runtime_contract"]))}


def measured_analysis_plan(inventory, *, protocol_sha256, analysis_group="primary"):
    validate_measured_inventory(inventory)
    result = warm_analysis_plan(_base_inventory(inventory), protocol_sha256=protocol_sha256,
                                analysis_group=analysis_group)
    result["campaign_sha256"] = digest(canonical_json(inventory))
    selected = [entry for entry in inventory["entries"] if entry["analysis_group"] == analysis_group]
    for row, entry in zip(result["planned_runs"], selected):
        row.update(cache_mode=CACHE_MODE, service_boundary=BOUNDARY, planned_methods=list(METHODS),
                   method_order=entry["measured_method_order"], execution_mode=entry["measured_plan_payload"]["execution_mode"],
                   measured_plan_sha256=entry["measured_plan_sha256"], run_id=entry["run_id"],
                   runtime_contract_sha256=digest(canonical_json(inventory["runtime_contract"])))
    return result


def _budget(checked):
    return PhaseBudget(checked["protocol_path"].parent / ("phase-cpu-budget-" + checked["protocol_sha256"]),
        identity={"protocol_sha256": checked["protocol_sha256"],
                  "source_sha256": source_hashes(Path(__file__).resolve().parents[1])},
        phase_cpu_seconds=checked["phase_cpu_seconds"])


def _archive_files(directory):
    """Bind partial failed trees too; later files must not turn failure into success."""
    root = Path(directory)
    if not root.exists():
        return None
    if root.is_symlink() or not root.is_dir() or any(parent.is_symlink() for parent in root.parents):
        raise ValueError("invalid measured run archive path")
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("symbolic measured run archive member")
        if path.is_file():
            result[str(path.relative_to(root))] = digest(path.read_bytes())
        elif not path.is_dir():
            raise ValueError("nonregular measured run archive member")
    return result


def _verify_saved_run(root, row, budget):
    path = root / "runs" / row["run_id"] / "result.json"
    if _archive_files(path.parent) != row["archive_sha256"]:
        raise ValueError("measured campaign run archive changed")
    expected = row.get("result_sha256")
    if expected is None:
        if path.exists():
            raise ValueError("measured campaign acquired an unrecorded result")
        return
    record, raw = _read_json(path)
    if digest(raw) != expected:
        raise ValueError("measured campaign result receipt changed")
    verify_measured_archive(path.parent, record)


def run_measured_campaign(path, output, *, validate_only=False):
    checked = validate_measured_campaign_files(path, execute=not validate_only)
    inventory = checked["inventory"]
    if validate_only:
        return {"schema": "measured-campaign-validation-v1", "status": "validated",
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
    result = {"schema": "measured-campaign-result-v1", "status": "running", "campaign_id": inventory["campaign_id"],
              "inventory_sha256": checked["inventory_sha256"], "protocol_sha256": checked["protocol_sha256"],
              "cache_mode": CACHE_MODE, "planned_runs": len(inventory["entries"]),
              "runs": [{"run_id": entry["run_id"], "status": "not_started"} for entry in inventory["entries"]]}
    started = time.perf_counter_ns()
    try:
        store.write_artifact("inventory.json", checked["raw"])
        plans = {group: measured_analysis_plan(inventory, protocol_sha256=checked["protocol_sha256"], analysis_group=group)
                 for group in {entry["analysis_group"] for entry in inventory["entries"]}}
        for group, analysis in sorted(plans.items()):
            # Analysis group labels are data, never filenames.
            store.write_artifact("analysis-plan-" + digest(group.encode()) + ".json", canonical_json(analysis))
        for index, item in enumerate(checked["checked"]):
            entry = item["entry"]
            current = validate_measured_campaign_files(path, execute=True)
            if any(current[key] != checked[key] for key in ("inventory_sha256", "protocol_sha256")):
                raise ValueError("measured campaign changed during execution")
            directory = store.root / "runs" / entry["run_id"]
            row = {"run_id": entry["run_id"], "analysis_group": entry["analysis_group"], "status": "running"}
            result["runs"][index] = row
            store.write_status(result)
            try:
                comparison = run_measured_comparison(item["plan_path"], directory, inventory_path=checked["inventory_path"],
                                          inventory_run_id=entry["run_id"])
                row.update(status="complete" if comparison["outcome"]["status"] == "complete" else "failed", analysis=comparison)
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as exc:
                plan_rows = plans[entry["analysis_group"]]["planned_runs"]
                planned = next(value for value in plan_rows if all(value[field] == entry[field]
                    for field in ("configuration_id", "phase", "root_id", "request_id", "repeat_index")))
                failure = _failure(exc)
                row.update(status="failed", failure=failure, analysis=dict(planned,
                    schema="calibration-measured-comparison-v1", status="failed", methods={method: {
                        "status": "not_started", "failure": dict(failure, kind="comparison_failed")}
                        for method in METHODS}))
            receipt = directory / "result.json"
            row["result_sha256"] = digest(receipt.read_bytes()) if receipt.is_file() else None
            row["archive_sha256"] = _archive_files(directory)
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
