"""Restartable ordered deletion studies over the fixed finite target.

This module only executes caller-supplied local data. Each step compares the
preceding committed repair state with independent retained-data fresh oracles.
Research archives retain old states. No physical erasure claim follows.
"""
from __future__ import annotations

from pathlib import Path
import time

from .experiment_runner import (
    METHODS, CACHE_MODE, _commit_state, _failure, _integer, _read_json,
    _run_manifest, _text, measure, run_comparison,
)
from .run_store import RunStore, canonical_json, digest, strict_json
from .service_telemetry import ServiceTelemetry


def validate_requests(requests, record_ids):
    """Validate an incremental, ordered request schedule before any evaluation."""
    if not isinstance(requests, (list, tuple)) or not requests:
        raise ValueError("sequence requires a nonempty ordered request list")
    live = set(record_ids)
    seen, result = set(), []
    for request in requests:
        if not isinstance(request, dict) or set(request) != {"request_id", "deleted_ids"}:
            raise ValueError("each sequence request requires request_id and deleted_ids")
        rid = _text(request["request_id"], "request ID")
        if rid in seen:
            raise ValueError("sequence request IDs must be unique")
        seen.add(rid)
        deleted = request["deleted_ids"]
        if (not isinstance(deleted, (list, tuple)) or any(type(x) is not str or not x for x in deleted)
                or len(set(deleted)) != len(deleted) or not set(deleted) <= live):
            raise ValueError("each request may delete each live record at most once")
        result.append({"request_id": rid, "deleted_ids": list(deleted)})
        live.difference_update(deleted)
    return result


def _load_saved_state(service, store, completion, name):
    # completed() verifies every artifact, including failed comparison controls.
    if store.completed() != completion:
        raise ValueError("saved completion changed while loading its state")
    raw = (store.root / completion["attempt"] / name).read_bytes()
    expected = completion["artifacts"][name]["sha256"]
    return service.load_state(raw, expected_digest=expected)


def _initial_state(service, records, directory, identity, *, require_complete=False):
    store = RunStore(directory, identity)
    complete = store.completed()
    if complete is None:
        if require_complete:
            raise ValueError("completed sequence lost its original committed state")
        store.claim()
        telemetry = ServiceTelemetry()
        try:
            def prepare():
                original = service.fresh(records, telemetry=telemetry)
                with telemetry.span("artifact_output"):
                    return _commit_state(store, "original", original)
            info, metrics = measure(prepare)
            complete = store.finish(dict(schema="calibration-sequence-initial-v1", status="complete",
                setup=dict(info, **metrics, service_telemetry=telemetry.payload())))
        except BaseException as exc:
            store.write_status({"schema": "calibration-sequence-initial-v1", "status": "failed",
                                "failure": _failure(exc), "service_telemetry": telemetry.payload(),
                                "measurement": getattr(exc, "runner_metrics", {})})
            raise
        finally:
            store.close()
    return _load_saved_state(service, store, complete, "original-state.json"), complete


def run_sequence(decoder, service, records, requests, heldout, output, metadata, *,
                 method_order=METHODS, service_mode="certified", preflight=None):
    """Consume one committed state per request; preserve complete planned lineage.

    ``metadata`` requires sequence_id, root_id, configuration_id, repeat_index,
    and phase. Request IDs are supplied by ``requests``. Empty deletion is legal.
    After complete deletion, only subsequent empty requests are legal.
    """
    records, heldout = tuple(records), tuple(heldout)
    if len({r.record_id for r in records}) != len(records) or not records:
        raise ValueError("initial calibration records must be nonempty and unique")
    if not heldout:
        raise ValueError("heldout records are required")
    for key in ("sequence_id", "root_id", "configuration_id"):
        _text(metadata.get(key), key)
    _integer(metadata.get("repeat_index"), "repeat index")
    if metadata.get("phase") not in ("development", "confirmation", "software_test"):
        raise ValueError("invalid experiment phase")
    if tuple(sorted(method_order)) != tuple(sorted(METHODS)):
        raise ValueError("method order must contain all three methods")
    if service_mode not in ("certified", "identity_only", "fixed_reference", "full_replay"):
        raise ValueError("unsupported service mechanism control")
    schedule = validate_requests(requests, (r.record_id for r in records))
    identity = {"schema": "calibration-sequence-identity-v1", "metadata": metadata,
                "service_manifest_sha256": service.manifest_digest,
                "records": [[r.record_id, r.content_digest] for r in records],
                "heldout": [[r.record_id, r.content_digest] for r in heldout],
                "requests": schedule, "method_order": list(method_order), "service_mode": service_mode}
    sequence_digest = digest(canonical_json(identity))
    parent = RunStore(output, identity)
    previous_completion = parent.completed()
    if previous_completion is None:
        parent.claim()
    result = dict(schema="calibration-sequence-v1", status="running", sequence_sha256=sequence_digest,
                  metadata=metadata, requests=schedule, service_manifest_sha256=service.manifest_digest,
                  cache_mode=CACHE_MODE, preflight=preflight,
                  execution_contract="one original preparation; incrementally committed repair state; fixed target; independent fresh oracle per step",
                  timing_contract="warm shared-process comparisons; initial preparation reported separately; reload and lineage commit excluded from method clocks",
                  steps=[{"step_index": i, "request_id": r["request_id"], "status": "not_started",
                          "failure": {"kind": "not_started"}} for i, r in enumerate(schedule)])
    start = time.perf_counter_ns()
    active = "initial_state"
    try:
        if previous_completion is None:
            parent.write_artifact("plan.json", canonical_json(identity))
        state, initial = _initial_state(service, records, parent.root / "initial", {
            "sequence_sha256": sequence_digest, "purpose": "original_preparation"},
            require_complete=previous_completion is not None)
        result["initial"] = {"result_sha256": digest(canonical_json(initial)),
                             "state_sha256": state.digest, "setup": initial["setup"]}
        live = records
        predecessor_result = result["initial"]["result_sha256"]
        lineage = []
        for i, request in enumerate(schedule):
            active = request["request_id"]
            step_identity = {"sequence_sha256": sequence_digest, "step_index": i,
                             "request_id": request["request_id"], "predecessor_state_sha256": state.digest,
                             "predecessor_result_sha256": predecessor_result}
            store = RunStore(parent.root / f"step-{i:04d}", step_identity)
            if previous_completion is not None and store.completed() is None:
                raise ValueError("completed sequence lost a committed step")
            step_metadata = dict(metadata, request_id=request["request_id"])
            step_result = run_comparison(decoder, service, live, request["deleted_ids"], heldout,
                                        store, step_metadata, method_order=method_order,
                                        service_mode=service_mode, initial_state=state,
                                        sequence_lineage=step_identity, preflight=preflight)
            row = {"step_index": i, "request_id": request["request_id"], "status": step_result["status"],
                   "result_sha256": digest(canonical_json(step_result)),
                   "predecessor_state_sha256": state.digest,
                   "predecessor_result_sha256": predecessor_result,
                   "result_path": f"step-{i:04d}/result.json"}
            result["steps"][i] = row
            if step_result["status"] != "complete":
                row["failure"] = step_result.get("failure", {"kind": "step_failed"})
                result.update(status="failed", failure={"kind": "step_failed", "step_index": i,
                                                       "request_id": request["request_id"]})
                break
            state = _load_saved_state(service, store, step_result, "repair-state.json")
            row["state_sha256"] = state.digest
            row["retained_ids"] = list(state.retained_ids)
            predecessor_result = row["result_sha256"]
            deleted = set(request["deleted_ids"])
            live = tuple(r for r in live if r.record_id not in deleted)
            if set(state.retained_ids) != {r.record_id for r in live}:
                raise ValueError("committed step has incorrect retained membership")
            lineage.append(row)
            if previous_completion is None:
                parent.write_status(result)
        else:
            result.update(status="complete", final_state_sha256=state.digest,
                          final_retained_ids=list(state.retained_ids), lineage_sha256=digest(canonical_json(lineage)))
        if previous_completion is not None:
            # Recheck all child completions before returning the saved parent.
            for key in ("initial", "steps", "lineage_sha256", "final_state_sha256", "final_retained_ids"):
                if result.get(key) != previous_completion.get(key):
                    raise ValueError("completed sequence lineage differs from its child artifacts")
            return previous_completion
        result["sequence_wall_ns_before_result_commit"] = time.perf_counter_ns() - start
        parent.write_artifact("lineage.json", canonical_json(result["steps"]))
        if result["status"] == "complete":
            return parent.finish(result)
        parent.write_status(result)
        return strict_json((parent.root / "result.json").read_bytes())
    except BaseException as exc:
        if previous_completion is not None:
            raise
        result.update(status="failed", failure=dict(_failure(exc), stage=active),
                      sequence_wall_ns_before_result_commit=time.perf_counter_ns() - start)
        parent.write_status(result)
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        return strict_json((parent.root / "result.json").read_bytes())
    finally:
        parent.close()


def _run_sequence_manifest(path, output, *, validate_only=False):
    """Load the regular local model contract and an ordered sequence manifest."""
    path = Path(path).absolute()
    manifest, raw = _read_json(path)
    if not isinstance(manifest, dict) or manifest.get("schema") != "calibration-sequence-v1":
        raise ValueError("invalid sequence manifest schema")
    if "request_id" in manifest or "deleted_ids" in manifest:
        raise ValueError("sequence manifest uses sequence_id and requests")
    sequence_id = _text(manifest.get("sequence_id"), "sequence ID")
    requests = manifest.get("requests")
    # The common loader verifies all local hashes, original normalization, and pause guards.
    common = {k: v for k, v in manifest.items() if k not in ("sequence_id", "requests")}
    common.update(schema="calibration-run-v1", request_id=sequence_id, deleted_ids=[])
    loaded = _run_manifest(path, output, validate_only=validate_only, prepare_only=not validate_only,
                           _manifest_override=(common, raw))
    if validate_only:
        # Validation loaded token IDs without invoking the finite feature evaluator.
        from .experiment_runner import _referenced_json
        calibration, _ = _referenced_json(path.parent, common["calibration"])
        validate_requests(requests, (r["id"] for r in calibration["records"]))
        return dict(loaded, sequence_manifest_sha256=digest(raw), requests=len(requests))
    metadata = dict(loaded["metadata"], sequence_id=sequence_id)
    metadata.pop("request_id")
    return run_sequence(loaded["decoder"], loaded["service"], loaded["records"], requests,
                        loaded["heldout"], output, metadata, method_order=loaded["method_order"],
                        service_mode=loaded["service_mode"], preflight=loaded["preflight"])


def run_sequence_manifest(path, output, *, validate_only=False):
    """Keep a durable preparation failure without replacing completed results."""
    try:
        return _run_sequence_manifest(path, output, validate_only=validate_only)
    except BaseException as exc:
        from .run_store import atomic_write
        directory = Path(output).absolute()
        if directory.is_symlink() or any(p.is_symlink() for p in directory.parents):
            raise
        directory.mkdir(parents=True, exist_ok=True)
        failure = {"schema": "calibration-sequence-preflight-failure-v1", "status": "failed",
                   "failure": _failure(exc), "execution_may_have_started": True}
        source = Path(path)
        if source.is_file() and not source.is_symlink():
            raw = source.read_bytes()
            failure["sequence_manifest_sha256"] = digest(raw)
            try:
                data = strict_json(raw)
                if isinstance(data, dict) and isinstance(data.get("requests"), list):
                    failure["planned_requests"] = data["requests"]
            except ValueError:
                pass
        atomic_write(directory / ("preflight-failure-" + str(time.time_ns()) + ".json"), canonical_json(failure))
        raise
