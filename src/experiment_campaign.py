"""Execute a frozen local campaign with durable outcomes for every entry.

Workers start in separate processes. Methods within each comparison remain warm.
The campaign never downloads inputs or changes the research pause flag.
"""
from __future__ import annotations

from pathlib import Path
import sys
import time

from .experiment_inventory import manifest_binding, source_hashes, validate_campaign
from .experiment_runner import METHODS, _integer, _local, _read_json, _sha
from .run_store import RunStore, canonical_json, digest, strict_json
from .worker_control import WorkerLimits, run_limited


EXECUTION_MODE = "isolated_comparison_warm_arms_os_cache_uncontrolled"


def _validate_confirmation_product(campaign, protocol):
    """Reject partial confirmatory comparisons before any worker starts."""
    entries = [entry for entry in campaign["entries"] if entry["phase"] == "confirmation"]
    if not entries and protocol.get("status") != "frozen_confirmation":
        return
    configurations = protocol.get("confirmation_configuration_ids")
    if (not isinstance(configurations, list) or not configurations or
            any(type(value) is not str or not value for value in configurations) or
            len(set(configurations)) != len(configurations)):
        raise ValueError("confirmation requires explicit unique confirmation_configuration_ids")
    try:
        stage = protocol["stages"]["confirmation"]
        root_count = _integer(stage["independent_roots"], "confirmation root count", 1)
        repeats = _integer(stage["timing_repeats"], "confirmation repeat count", 1)
        requests = protocol["sampling"]["requests"]
    except (KeyError, TypeError) as exc:
        raise ValueError("confirmation requires root, repetition, and request declarations") from exc
    if (not isinstance(requests, list) or not requests or
            any(type(value) is not str or not value for value in requests) or len(set(requests)) != len(requests)):
        raise ValueError("confirmation request IDs must form a unique nonempty list")
    primary = [entry for entry in entries if entry["analysis_group"] == "primary"]
    roots = {entry["root_id"] for entry in primary}
    if len(roots) != root_count:
        raise ValueError("confirmation has a different number of calibration roots")
    expected = {(configuration, root, request, repeat) for configuration in configurations
                for root in roots for request in requests for repeat in range(repeats)}
    actual = {(entry["configuration_id"], entry["root_id"], entry["request_id"], entry["repeat_index"])
              for entry in primary}
    if actual != expected or len(actual) != len(primary):
        raise ValueError("confirmation inventory does not contain the complete declared comparison product")


def validate_campaign_files(path, *, execute=False):
    """Check membership and every hash before starting any worker."""
    inventory_path = Path(path).absolute()
    campaign, raw = _read_json(inventory_path)
    validate_campaign(campaign)
    if raw != canonical_json(campaign):
        raise ValueError("campaign inventory must use canonical JSON bytes")
    inventory_sha256 = digest(raw)
    base = inventory_path.parent
    repository = Path(__file__).resolve().parents[1]
    expected_sources = source_hashes(repository)
    if campaign["source_sha256"] != expected_sources:
        raise ValueError("campaign source hashes differ from current executable sources")
    limits = WorkerLimits.from_payload(campaign["worker_limits"])
    limits.check_host()
    protocol_path = _local(base, campaign["protocol_path"])
    protocol, protocol_raw = _read_json(protocol_path)
    if not isinstance(protocol, dict) or protocol.get("planned_inventory_sha256") != inventory_sha256:
        raise ValueError("protocol does not bind the exact campaign inventory")
    protocol_sha256 = digest(protocol_raw)
    _validate_confirmation_product(campaign, protocol)
    checked = []
    seen_paths = set()
    for entry in campaign["entries"]:
        manifest_path = _local(base, entry["manifest_path"])
        if manifest_path in seen_paths:
            raise ValueError("campaign entries share a run manifest path")
        seen_paths.add(manifest_path)
        manifest, manifest_raw = _read_json(manifest_path)
        if manifest_binding(manifest) != entry["manifest_binding_sha256"]:
            raise ValueError("run manifest differs from the frozen inventory")
        reference = manifest.get("protocol")
        if not isinstance(reference, dict) or set(reference) != {"path", "sha256"}:
            raise ValueError("run manifest protocol reference is invalid")
        if _local(manifest_path.parent, reference["path"]) != protocol_path:
            raise ValueError("run manifest refers to a different protocol path")
        if _sha(reference["sha256"]) != protocol_sha256:
            raise ValueError("run manifest protocol hash differs from current bytes")
        if execute and entry["phase"] != "software_test" and "experiments_paused" in str(protocol.get("status", "")):
            raise ValueError("the protocol keeps research experiments paused")
        if entry["phase"] == "confirmation":
            if (protocol.get("schema") != "calibration-protocol-v1" or
                    protocol.get("status") != "frozen_confirmation" or protocol.get("blocked_fields") != []):
                raise ValueError("confirmation requires a frozen protocol without blocked fields")
        checked.append({"entry": entry, "manifest_path": manifest_path,
                        "manifest_sha256": digest(manifest_raw)})
    return {"campaign": campaign, "raw": raw, "inventory_sha256": inventory_sha256,
            "protocol_sha256": protocol_sha256, "protocol_path": protocol_path,
            "sources": expected_sources, "limits": limits, "checked": checked}


def _comparison_outcome(output, entry, manifest_sha256, protocol_sha256):
    """Validate successful runner commits before accepting them."""
    result_path = output / "result.json"
    if not result_path.is_file() or result_path.is_symlink():
        return {"status": "failed", "failure": {"kind": "missing_worker_result"}}
    try:
        data, raw = _read_json(result_path)
        if not isinstance(data, dict):
            raise ValueError("worker result must be a JSON object")
        if data.get("status") != "complete":
            return {"status": "failed", "failure": data.get("failure", {"kind": "incomplete_worker_result"}),
                    "result_path": str(result_path), "result_sha256": digest(raw),
                    "recorded_status": data.get("status")}
        identity, _ = _read_json(output / "identity.json")
        verified = RunStore(output, identity).completed()
        if verified != data:
            raise ValueError("completed worker result failed artifact verification")
        for name in ("root_id", "request_id", "configuration_id", "repeat_index", "phase", "method_order"):
            if data.get(name) != entry[name]:
                raise ValueError("completed worker result differs from the frozen entry")
        if data.get("run_manifest_sha256") != manifest_sha256 or data.get("protocol_sha256") != protocol_sha256:
            raise ValueError("completed worker result has different input hashes")
        if data.get("target_manifest_sha256") != entry["target_manifest_sha256"]:
            raise ValueError("completed worker result has a different target hash")
        if data.get("cache_mode") != "warm_sequential_os_cache_uncontrolled":
            raise ValueError("worker result has an unexpected comparison cache mode")
        if data.get("schema") != "calibration-experiment-v1" or data.get("planned_methods") != list(METHODS):
            raise ValueError("worker result does not contain the declared comparison schema")
        from .result_analysis import outcome, validate_run
        validate_run(data)
        if any(outcome(data.get("methods", {}).get(method), data["status"]) != "exact_complete" for method in METHODS):
            raise ValueError("worker completion lacks exact complete method outcomes")
        return {"status": "complete", "result_path": str(result_path), "result_sha256": digest(raw)}
    except (ValueError, OSError, KeyError, TypeError) as exc:
        return {"status": "failed", "failure": {"kind": "invalid_worker_result", "type": type(exc).__name__, "message": str(exc)}}


def _existing_campaign(directory, identity):
    store = RunStore(directory, identity)
    result = store.completed()
    if result is None:
        return None
    for row in result.get("runs", []):
        for prefix in ("worker_record", "result"):
            path_value = row.get(prefix + "_path")
            expected = row.get(prefix + "_sha256")
            if path_value is None:
                continue
            path = Path(path_value)
            if path.is_symlink() or not path.is_file() or digest(path.read_bytes()) != expected:
                raise ValueError("saved campaign references changed or missing worker records")
            if prefix == "worker_record":
                worker_identity, _ = _read_json(path.parent / "identity.json")
                RunStore(path.parent, worker_identity).completed()
        if row.get("status") == "complete":
            path = Path(row["result_path"])
            worker_identity, _ = _read_json(path.parent / "identity.json")
            RunStore(path.parent, worker_identity).completed()
    return result


def run_campaign(path, output, *, validate_only=False):
    """Execute every frozen entry serially. Terminal failures remain in the denominator."""
    validated = validate_campaign_files(path, execute=not validate_only)
    campaign = validated["campaign"]
    if validate_only:
        return {"schema": "calibration-campaign-validation-v1", "status": "validated",
                "campaign_id": campaign["campaign_id"], "inventory_sha256": validated["inventory_sha256"],
                "planned_runs": len(campaign["entries"]), "empirical_work_executed": False,
                "validation_scope": "inventory, source hashes, run manifest bindings, protocol hashes, and available worker limits; no checkpoint tensors loaded"}
    root = Path(output).absolute()
    identity = {"campaign_sha256": validated["inventory_sha256"],
                "protocol_sha256": validated["protocol_sha256"], "source_sha256": validated["sources"],
                "execution_mode": EXECUTION_MODE}
    completed = _existing_campaign(root, identity)
    if completed is not None:
        return completed
    store = RunStore(root, identity)
    store.claim()
    rows = [{"run_id": e["run_id"], "status": "not_started", "failure": {"kind": "not_started"}}
            for e in campaign["entries"]]
    result = {"schema": "calibration-campaign-result-v1", "status": "running",
              "campaign_id": campaign["campaign_id"], "inventory_sha256": validated["inventory_sha256"],
              "protocol_sha256": validated["protocol_sha256"], "execution_mode": EXECUTION_MODE,
              "cache_contract": "new process for each comparison; warm methods within each process; OS caches uncontrolled",
              "planned_runs": len(rows), "runs": rows}
    started = time.perf_counter_ns()
    try:
        store.write_artifact("inventory.json", validated["raw"])
        store.write_status(result)
        for index, item in enumerate(validated["checked"]):
            entry = item["entry"]
            run_root = root / "workers" / entry["run_id"]
            comparison_root = root / "comparisons" / entry["run_id"]
            rows[index] = {"run_id": entry["run_id"], "status": "running",
                           "manifest_sha256": item["manifest_sha256"],
                           "manifest_binding_sha256": entry["manifest_binding_sha256"],
                           "method_order": entry["method_order"]}
            store.write_status(result)
            # Detect input or source changes between validation and this dispatch.
            current = validate_campaign_files(path, execute=True)
            if current["inventory_sha256"] != validated["inventory_sha256"]:
                raise ValueError("campaign inventory changed during execution")
            if current["protocol_sha256"] != validated["protocol_sha256"]:
                raise ValueError("campaign protocol changed during execution")
            if current["checked"][index]["manifest_sha256"] != item["manifest_sha256"]:
                raise ValueError("run manifest changed during execution")
            command = [sys.executable, str(Path(__file__).resolve().parents[1] / "scripts" / "run_experiment.py"),
                       str(item["manifest_path"]), "--output", str(comparison_root)]
            worker = run_limited(command, run_root, validated["limits"], identity={
                "campaign_sha256": validated["inventory_sha256"], "run_id": entry["run_id"],
                "manifest_sha256": item["manifest_sha256"], "source_sha256": validated["sources"]})
            record_path = run_root / "result.json"
            rows[index].update(worker_record_path=str(record_path), worker_record_sha256=digest(record_path.read_bytes()),
                               worker_outcome=worker["outcome"])
            observed = _comparison_outcome(comparison_root, entry, item["manifest_sha256"], validated["protocol_sha256"])
            rows[index].update(observed)
            if worker["outcome"]["status"] != "complete":
                rows[index].update(status="failed", failure={"kind": worker["outcome"]["kind"]})
            store.write_artifact(entry["run_id"] + "-outcome.json", canonical_json(rows[index]))
            store.write_status(result)
        result.update(status="complete", completed_runs=sum(row["status"] == "complete" for row in rows),
                      failed_runs=sum(row["status"] != "complete" for row in rows),
                      outcome="complete" if all(row["status"] == "complete" for row in rows) else "failed",
                      controller_wall_ns_before_commit=time.perf_counter_ns() - started,
                      controller_completion_means="all frozen entries have terminal records; outcome reports campaign success")
        return store.finish(result)
    except BaseException as exc:
        result.update(status="failed", failure={"kind": "campaign_interrupted" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else "campaign_exception",
                                               "type": type(exc).__name__, "message": str(exc)},
                      controller_wall_ns_before_commit=time.perf_counter_ns() - started)
        store.write_status(result)
        raise
    finally:
        store.close()
