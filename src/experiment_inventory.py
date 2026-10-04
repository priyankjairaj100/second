"""Immutable campaign planning without empirical execution.

The inventory binds manifests with only protocol.sha256 cleared. This removes
the protocol/inventory hash cycle. Final dispatch must verify both raw hashes.
"""
from __future__ import annotations

from pathlib import Path, PurePosixPath

from .request_workload import METHODS, counterbalanced_orders, _sha, _text, _integer
from .run_store import canonical_json, digest, strict_json

EXECUTION_MODE = "isolated_comparison_warm_arms_os_cache_uncontrolled"
CACHE_MODE = "warm_sequential_os_cache_uncontrolled"
SERVICE_BOUNDARY = "service_through_atomic_artifact_fsync"
LIMIT_FIELDS = {"wall_seconds", "cpu_seconds", "address_space_bytes", "threads",
                "affinity_cpus", "termination_grace_seconds", "file_size_bytes"}
META_FIELDS = ("root_id", "request_id", "configuration_id", "repeat_index", "phase", "method_order")


def _relative(path):
    _text(path, "relative path")
    value = PurePosixPath(path)
    if value.is_absolute() or any(part in (".", "..") for part in value.parts) or "\\" in path or str(value) != path:
        raise ValueError("path must be a normalized relative POSIX path")
    return path


def manifest_payload(manifest):
    """Bind every field except the final protocol digest."""
    if not isinstance(manifest, dict) or manifest.get("schema") != "calibration-run-v1":
        raise ValueError("unsupported run manifest")
    result = strict_json(canonical_json(manifest))
    reference = result.get("protocol")
    if not isinstance(reference, dict) or set(reference) != {"path", "sha256"}:
        raise ValueError("manifest must reference one protocol")
    _text(reference["path"], "protocol path")
    if reference["sha256"] is not None:
        _sha(reference["sha256"])
    reference["sha256"] = None
    return result


def manifest_binding(manifest):
    return digest(canonical_json(manifest_payload(manifest)))


def source_hashes(repository):
    """Hash current dispatch code. The executor must compare the same complete set."""
    root = Path(repository).resolve()
    paths = sorted((root / "src").glob("*.py"))
    paths += [root / "scripts" / name for name in (
        "run_experiment.py", "run_campaign.py", "run_sequence.py", "run_isolated.py")]
    if not paths or any(path.is_symlink() or not path.is_file() for path in paths):
        raise ValueError("campaign source files are missing or symbolic links")
    return {str(path.relative_to(root)): digest(path.read_bytes()) for path in paths}


def _limits(value):
    if not isinstance(value, dict) or set(value) != LIMIT_FIELDS:
        raise ValueError("invalid worker limit fields")
    for key in LIMIT_FIELDS - {"affinity_cpus"}:
        _integer(value[key], key, 0 if key == "termination_grace_seconds" else 1)
    cpus = value["affinity_cpus"]
    if not isinstance(cpus, list) or not cpus or len(set(cpus)) != len(cpus):
        raise ValueError("CPU affinity must be a unique nonempty list")
    for cpu in cpus:
        _integer(cpu, "CPU ID")


def _workload_map(workloads):
    if not isinstance(workloads, list) or not workloads:
        raise ValueError("workloads are required")
    result = {}
    for workload in workloads:
        if not isinstance(workload, dict) or workload.get("schema") != "calibration-workload-v1":
            raise ValueError("unsupported workload")
        rid = _text(workload.get("root_id"), "root ID")
        if rid in result:
            raise ValueError("duplicate root workload")
        _integer(workload.get("seed"), "workload seed")
        for field in ("prepared_records_sha256", "original_state_sha256", "scores_sha256"):
            _sha(workload.get(field))
        ids = workload.get("original_record_ids")
        if not isinstance(ids, list) or not ids or len(set(ids)) != len(ids):
            raise ValueError("invalid original workload records")
        for value in ids:
            _text(value)
        requests = workload.get("requests")
        if not isinstance(requests, list) or not requests:
            raise ValueError("workload requests are required")
        by_request = {}
        for request in requests:
            if not isinstance(request, dict):
                raise ValueError("invalid workload request")
            request_id = _text(request.get("request_id"), "request ID")
            if request_id in by_request:
                raise ValueError("duplicate workload request")
            deleted = request.get("deleted_ids")
            if not isinstance(deleted, list) or len(set(deleted)) != len(deleted) or not set(deleted) <= set(ids):
                raise ValueError("invalid workload deletion membership")
            by_request[request_id] = request
        result[rid] = (workload, by_request)
    return result


def validate_campaign(payload):
    """Validate frozen membership. Input paths are resolved by the executor."""
    required = {"schema", "campaign_id", "protocol_path", "worker_limits", "entries", "execution_mode",
                "source_sha256", "workload_sha256", "workloads"}
    if not isinstance(payload, dict) or set(payload) != required or payload["schema"] != "calibration-campaign-v1":
        raise ValueError("invalid campaign schema or fields")
    _text(payload["campaign_id"], "campaign ID")
    _text(payload["protocol_path"], "protocol path")
    if payload["execution_mode"] != EXECUTION_MODE:
        raise ValueError("unsupported campaign execution mode")
    _limits(payload["worker_limits"])
    sources = payload["source_sha256"]
    if not isinstance(sources, dict) or not sources:
        raise ValueError("campaign source hashes are required")
    for path, value in sources.items():
        _relative(path)
        _sha(value)
    if _sha(payload["workload_sha256"]) != digest(canonical_json(payload["workloads"])):
        raise ValueError("workload hash differs")
    workloads = _workload_map(payload["workloads"])
    entries = payload["entries"]
    if not isinstance(entries, list) or not entries:
        raise ValueError("campaign requires planned entries")
    identities, run_ids, paths, repetitions = set(), set(), set(), {}
    fields = {"run_id", "manifest_path", "manifest_binding_sha256", "manifest_payload",
              "target_manifest_sha256", "analysis_group", "request_membership_sha256", *META_FIELDS}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != fields:
            raise ValueError("invalid inventory entry fields")
        run_id = _text(entry["run_id"], "run ID")
        if not all(c.isalnum() or c in "_-" for c in run_id) or run_id in run_ids:
            raise ValueError("run ID must be unique and filename-safe")
        run_ids.add(run_id)
        path = _relative(entry["manifest_path"])
        if path in paths:
            raise ValueError("duplicate run manifest path")
        paths.add(path)
        for field in ("root_id", "request_id", "configuration_id"):
            _text(entry[field], field)
        _integer(entry["repeat_index"], "repeat index")
        if entry["phase"] not in ("development", "confirmation", "software_test"):
            raise ValueError("unsupported experiment phase")
        if not isinstance(entry["method_order"], list) or sorted(entry["method_order"]) != sorted(METHODS):
            raise ValueError("invalid method order")
        manifest = entry["manifest_payload"]
        if manifest_payload(manifest) != manifest:
            raise ValueError("bound manifest must clear only protocol.sha256")
        if _sha(entry["manifest_binding_sha256"]) != manifest_binding(manifest):
            raise ValueError("manifest binding differs")
        if any(entry[field] != manifest.get(field) for field in META_FIELDS):
            raise ValueError("inventory metadata differs from bound manifest")
        _sha(entry["target_manifest_sha256"])
        root = entry["root_id"]
        if root not in workloads or entry["request_id"] not in workloads[root][1]:
            raise ValueError("run is absent from the frozen workload")
        workload, requests = workloads[root]
        request = requests[entry["request_id"]]
        if request.get("blocked_reason") is not None or request.get("execution_requirement") != "independent_reset":
            raise ValueError("request requires an unsupported execution path")
        if entry["analysis_group"] != request.get("analysis_group"):
            raise ValueError("request analysis group differs")
        if entry["request_membership_sha256"] != digest(canonical_json(request)):
            raise ValueError("request binding differs")
        if manifest.get("deleted_ids") != request["deleted_ids"]:
            raise ValueError("manifest changes planned deletion membership")
        calibration = manifest.get("calibration")
        if not isinstance(calibration, dict) or calibration.get("sha256") != workload["prepared_records_sha256"]:
            raise ValueError("manifest changes calibration source")
        expected = counterbalanced_orders(seed=workload["seed"], root_id=root, request_id=entry["request_id"],
                                         repeats=entry["repeat_index"]+1)[-1]
        if expected != entry["method_order"]:
            raise ValueError("method order violates the frozen counterbalance")
        identity = tuple(entry[field] for field in META_FIELDS[:-1])
        if identity in identities:
            raise ValueError("duplicate planned run identity")
        identities.add(identity)
        key = (entry["configuration_id"], entry["phase"], root, entry["request_id"])
        repetitions.setdefault(key, []).append(entry["repeat_index"])
    for indices in repetitions.values():
        if sorted(indices) != list(range(len(indices))):
            raise ValueError("planned repeat indices must start at zero without gaps")
    return strict_json(canonical_json(payload))


def build_campaign(*, campaign_id: str, protocol_path: str, worker_limits: dict,
                   manifests: list[dict], workloads: list[dict], source_sha256: dict):
    """Bind already prepared manifests. This builder runs no models or requests."""
    by_root = _workload_map(workloads)
    entries = []
    for index, item in enumerate(manifests):
        if not isinstance(item, dict) or set(item) != {"manifest_path", "manifest", "target_manifest_sha256"}:
            raise ValueError("manifest inputs require path, payload, and target digest")
        manifest = manifest_payload(item["manifest"])
        try:
            request = by_root[manifest["root_id"]][1][manifest["request_id"]]
        except KeyError as exc:
            raise ValueError("manifest is absent from workload") from exc
        entry = {key: manifest[key] for key in META_FIELDS}
        entry.update(run_id=f"run-{index:08d}", manifest_path=item["manifest_path"],
                     manifest_payload=manifest, manifest_binding_sha256=manifest_binding(manifest),
                     target_manifest_sha256=item["target_manifest_sha256"],
                     analysis_group=request["analysis_group"],
                     request_membership_sha256=digest(canonical_json(request)))
        entries.append(entry)
    return validate_campaign({"schema": "calibration-campaign-v1", "campaign_id": campaign_id,
                              "protocol_path": protocol_path, "worker_limits": worker_limits,
                              "execution_mode": EXECUTION_MODE, "source_sha256": source_sha256,
                              "workload_sha256": digest(canonical_json(workloads)),
                              "workloads": workloads, "entries": entries})


def analysis_plan(payload, *, protocol_sha256: str, analysis_group="primary"):
    """Resolve final hashes after freezing. Keep controls outside primary ratios."""
    campaign = validate_campaign(payload)
    _sha(protocol_sha256)
    return {"schema": "calibration-analysis-plan-v1",
            "campaign_sha256": digest(canonical_json(campaign)), "analysis_group": analysis_group,
            "planned_runs": [{key: entry[key] for key in ("configuration_id", "phase", "root_id", "request_id", "repeat_index")}
                             | {"cache_mode": CACHE_MODE, "planned_methods": list(METHODS),
                                "service_boundary": SERVICE_BOUNDARY,
                                "service_mode": entry["manifest_payload"].get("service_mode", "certified"),
                                "service_family": entry["manifest_payload"].get("service_family", "response"),
                                "response_tier": entry["manifest_payload"].get("chart", {}).get("response_tier", "linear"),
                                "verifier_policy": entry["manifest_payload"].get("verifier_policy", "spectral"),
                                "protocol_sha256": protocol_sha256,
                                "target_manifest_sha256": entry["target_manifest_sha256"]}
                             for entry in campaign["entries"] if entry["analysis_group"] == analysis_group]}
