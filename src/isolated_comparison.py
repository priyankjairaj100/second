"""Separate-process comparison over local, hash-bound inputs.

Each method runs in a fresh limited process. OS caches remain uncontrolled.
The parent verifies complete output bytes outside the worker timing boundary.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
import time

from .experiment_campaign import _phase_caps
from .experiment_inventory import manifest_binding, manifest_payload, source_hashes
from .experiment_runner import (METHODS, _commit_state, _failure, _integer, _local,
    _read_json, _referenced_json, _run_manifest, _sha, _text)
from .phase_budget import PhaseBudget
from .result_analysis import validate_run
from .run_store import RunStore, atomic_write, canonical_json, digest, strict_json
from .service_telemetry import ServiceTelemetry
from .worker_control import WorkerLimits, run_limited

CACHE_MODE = "isolated_method_processes_os_cache_uncontrolled"
BOUNDARY = "limited_worker_startup_inputs_service_artifacts_child_commit_and_cleanup"


def isolated_source_hashes(repository=None):
    root = Path(repository or Path(__file__).resolve().parents[1])
    hashes = source_hashes(root)
    path = root / "scripts" / "run_isolated.py"
    if path.is_symlink() or not path.is_file():
        raise ValueError("isolated CLI source is missing or symbolic")
    hashes["scripts/run_isolated.py"] = digest(path.read_bytes())
    return hashes


def build_isolated_plan(*, manifest_path, manifest, target_manifest_sha256, worker_limits, sources):
    """Construct a protocol-cycle-free plan without loading model parameters."""
    return {"schema": "calibration-isolated-plan-v1", "manifest_path": manifest_path,
            "manifest_payload": manifest_payload(manifest),
            "manifest_binding_sha256": manifest_binding(manifest),
            "target_manifest_sha256": _sha(target_manifest_sha256),
            "worker_limits": WorkerLimits.from_payload(worker_limits).payload(),
            "source_sha256": sources}


def validate_isolated_plan(path, *, execute=False):
    plan_path = Path(path).absolute()
    plan, raw = _read_json(plan_path)
    fields = {"schema", "manifest_path", "manifest_payload", "manifest_binding_sha256",
              "target_manifest_sha256", "worker_limits", "source_sha256"}
    if not isinstance(plan, dict) or set(plan) != fields or plan["schema"] != "calibration-isolated-plan-v1":
        raise ValueError("invalid isolated plan schema or fields")
    if raw != canonical_json(plan):
        raise ValueError("isolated plan requires canonical JSON")
    _sha(plan["target_manifest_sha256"])
    if plan["source_sha256"] != isolated_source_hashes():
        raise ValueError("isolated source hashes differ from the frozen plan")
    bound = plan["manifest_payload"]
    if manifest_payload(bound) != bound or manifest_binding(bound) != _sha(plan["manifest_binding_sha256"]):
        raise ValueError("isolated manifest binding is invalid")
    manifest_path = _local(plan_path.parent, plan["manifest_path"])
    manifest, manifest_raw = _read_json(manifest_path)
    if manifest_binding(manifest) != plan["manifest_binding_sha256"]:
        raise ValueError("run manifest differs from isolated plan")
    for field in ("root_id", "request_id", "configuration_id"):
        _text(manifest.get(field), field)
    _integer(manifest.get("repeat_index"), "repeat_index")
    if manifest.get("phase") not in ("development", "confirmation", "software_test"):
        raise ValueError("invalid isolated execution phase")
    if not isinstance(manifest.get("method_order"), list) or sorted(manifest["method_order"]) != sorted(METHODS):
        raise ValueError("isolated plan requires all three methods exactly once")
    protocol, protocol_raw = _referenced_json(manifest_path.parent, manifest["protocol"])
    if not isinstance(protocol, dict):
        raise ValueError("protocol requires an object")
    if execute and manifest["phase"] != "software_test" and "experiments_paused" in str(protocol.get("status", "")):
        raise ValueError("the protocol keeps research experiments paused")
    if execute and manifest["phase"] == "confirmation":
        raise ValueError("isolated confirmation requires a supported frozen campaign inventory; this path remains blocked")
    limits = WorkerLimits.from_payload(plan["worker_limits"])
    limits.check_host()
    caps = _phase_caps({"entries": [{"phase": manifest["phase"]}] * 4}, protocol, limits)
    return {"plan": plan, "raw": raw, "plan_path": plan_path, "plan_sha256": digest(raw),
            "manifest": manifest, "manifest_path": manifest_path, "manifest_sha256": digest(manifest_raw),
            "protocol": protocol, "protocol_path": _local(manifest_path.parent, manifest["protocol"]["path"]),
            "protocol_sha256": digest(protocol_raw), "limits": limits, "phase_cpu_seconds": caps}


def _child_identity(request):
    return {"schema": "isolated-child-identity-v1", "request_sha256": digest(canonical_json(request))}


def _verify_sources(request):
    if request["source_sha256"] != isolated_source_hashes():
        raise ValueError("isolated child source hashes differ")
    if digest(_read_json(Path(request["manifest_path"]))[1]) != request["manifest_sha256"]:
        raise ValueError("isolated child run manifest hash differs")


def _child(request_path):
    request, _ = _read_json(Path(request_path))
    fields = {"schema", "role", "manifest_path", "manifest_sha256", "source_sha256",
              "target_manifest_sha256", "plan_sha256", "output", "original_state"}
    if (not isinstance(request, dict) or set(request) != fields
            or request["schema"] != "isolated-child-request-v1"
            or request["role"] not in ("setup", *METHODS)):
        raise ValueError("invalid isolated child request")
    store = RunStore(request["output"], _child_identity(request))
    previous = store.completed()
    if previous is not None:
        _verify_sources(request)
        # A terminal worker receipt already resumes in run_limited. Reaching
        # this branch means the original outer timing was never sealed.
        # Returning the old output would fabricate a very short method time.
        raise ValueError("isolated child already sealed; original complete worker timing is unavailable")
    store.claim()
    telemetry = ServiceTelemetry()
    record = {"schema": "isolated-child-result-v1", "status": "running", "role": request["role"],
              "plan_sha256": request["plan_sha256"], "manifest_sha256": request["manifest_sha256"],
              "outcome": {"status": "failed", "failure": {"kind": "not_started"}}}
    try:
        store.write_artifact("request.json", canonical_json(request))
        _verify_sources(request)
        prepared = _run_manifest(request["manifest_path"], request["output"], prepare_only=True)
        service, records = prepared["service"], prepared["records"]
        if prepared["metadata"]["target_manifest_sha256"] != request["target_manifest_sha256"]:
            raise ValueError("isolated child target differs from the declared target")
        record.update(metadata=prepared["metadata"], preflight=prepared["preflight"],
                      service_manifest_sha256=service.manifest_digest,
                      service_family=getattr(service, "service_family", "response"),
                      response_tier=getattr(service, "response_tier", "linear"),
                      verifier_policy=getattr(service, "verifier_policy", "spectral"))
        manifest, _ = _read_json(Path(request["manifest_path"]))
        role = request["role"]
        if role == "setup":
            if request["original_state"] is not None:
                raise ValueError("setup must not receive an earlier state")
            output = service.fresh(records, telemetry=telemetry)
            with telemetry.span("artifact_output"):
                info = _commit_state(store, "original", output)
            # Validate exactly what this worker has durably saved.
            with telemetry.span("persisted_state_reload"):
                service.load_state((store.attempt / "original-state.json").read_bytes(),
                                   expected_digest=info["state_sha256"])
        else:
            original = request["original_state"]
            if not isinstance(original, dict) or set(original) != {"path", "sha256"}:
                raise ValueError("method requires the original canonical state reference")
            _sha(original["sha256"])
            record["original_state_used"] = role != "direct_fresh"
            if role != "direct_fresh":
                with telemetry.span("persisted_state_reload"):
                    _, state_raw = _read_json(_local(Path(request_path).parent, original["path"]))
                    old = service.load_state(state_raw, expected_digest=original["sha256"])
                if {r.record_id: r.content_digest for r in old.records} != {r.record_id: r.content_digest for r in records}:
                    raise ValueError("original state records differ from the calibration manifest")
            deleted_set = set(manifest["deleted_ids"])
            by_id = {record.record_id: record for record in records}
            with telemetry.span("deleted_payload_lookup"):
                deleted = tuple(by_id[rid] for rid in manifest["deleted_ids"])
            retained = tuple(record for record in records if record.record_id not in deleted_set)
            source = {record.record_id: record for record in retained}.__getitem__
            mode = prepared["service_mode"]
            if role == "repair":
                output = service.repair(old, deleted, source, mode=mode, telemetry=telemetry)
            elif role == "indexed_fresh":
                index = service.prepare_index(old, deleted, telemetry=telemetry)
                record["index_preparation_ledger"] = dict(index.ledger.as_mapping())
                output = service.indexed_fresh(index.index, source, mode=mode, telemetry=telemetry)
            else:
                output = service.fresh(retained, telemetry=telemetry)
            with telemetry.span("artifact_output"):
                info = _commit_state(store, role, output)
        record.update(artifact=info, service_telemetry=telemetry.payload(), outcome={"status": "complete"})
        _verify_sources(request)
    except BaseException as exc:
        record.update(outcome={"status": "failed", "failure": _failure(exc)},
                      service_telemetry=telemetry.payload())
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            record["interrupted"] = True
    finally:
        record["status"] = "complete"
        record["controller_completion_means"] = "child receipt is sealed; inspect outcome.status"
        try:
            store.finish(record)
        finally:
            store.close()
    return record["outcome"]["status"] == "complete"


def _saved_child(directory, request, worker):
    child_store = RunStore(directory, _child_identity(request))
    record = child_store.completed()
    if record is None:
        path = Path(directory) / "result.json"
        if path.exists():
            unfinished, _ = _read_json(path)
            _verify_unfinished_artifacts(Path(directory), unfinished)
        return None
    if (record.get("schema") != "isolated-child-result-v1" or record.get("role") != request["role"]
            or record.get("manifest_sha256") != request["manifest_sha256"]
            or record.get("plan_sha256") != request["plan_sha256"]):
        raise ValueError("child receipt differs from its request")
    return record


def _verify_unfinished_artifacts(directory, record):
    """Verify every committed artifact even when a killed child has no seal."""
    name = record.get("attempt")
    if type(name) is not str or not re.fullmatch(r"attempt-[0-9]{4,}", name):
        raise ValueError("invalid incomplete child attempt")
    attempt = directory / name
    if attempt.is_symlink() or not attempt.is_dir() or not isinstance(record.get("artifacts"), dict):
        raise ValueError("invalid incomplete child artifact manifest")
    for filename, expected in record["artifacts"].items():
        if type(filename) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", filename):
            raise ValueError("invalid incomplete child artifact name")
        path = attempt / filename
        if path.is_symlink() or not path.is_file():
            raise ValueError("missing incomplete child artifact")
        raw = path.read_bytes()
        if expected != {"bytes": len(raw), "sha256": digest(raw)}:
            raise ValueError("incomplete child artifact hash mismatch")


def _request_path(root, role, request):
    directory = root / "requests"
    if directory.is_symlink():
        raise ValueError("symlink request directory")
    directory.mkdir(exist_ok=True)
    path = directory / (role + ".json")
    raw = canonical_json(request)
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != raw:
            raise ValueError("isolated request changed across attempts")
    else:
        atomic_write(path, raw)
    return path


def _verify_completed(root, result, budget):
    for role, saved in result.get("children", {}).items():
        request = saved["request"]
        _, request_raw = _read_json(root / "requests" / (role + ".json"))
        if request_raw != canonical_json(request):
            raise ValueError("saved isolated request changed")
        for label, directory, identity in (
                ("worker", root / "workers" / role, None),
                ("child", root / "children" / role, _child_identity(request))):
            expected = saved.get(label + "_result_sha256")
            path = directory / "result.json"
            if expected is None:
                if path.exists():
                    raise ValueError("completed comparison acquired an unrecorded child receipt")
                continue
            data, raw = _read_json(path)
            if digest(raw) != expected:
                raise ValueError("isolated completion references a changed receipt")
            if identity is None:
                identity, _ = _read_json(directory / "identity.json")
            verified = RunStore(directory, identity).completed()
            if verified is None:
                # Killed workers may leave an incomplete child record.
                if label != "child" or data.get("status") == "complete":
                    raise ValueError("saved isolated receipt is not sealed")
                _verify_unfinished_artifacts(directory, data)
            if label == "worker":
                attempt = verified.get("budget_attempt_id")
                if attempt is not None and budget.snapshot()["attempts"].get(attempt) != verified.get("budget_debit"):
                    raise ValueError("isolated worker budget differs from ledger")


def run_isolated(path, output, *, validate_only=False):
    checked = validate_isolated_plan(path, execute=not validate_only)
    if validate_only:
        return {"schema": "isolated-plan-validation-v1", "status": "validated",
                "plan_sha256": checked["plan_sha256"], "empirical_work_executed": False,
                "checkpoint_parameters_loaded": False, "phase_cpu_seconds": checked["phase_cpu_seconds"],
                "confirmation_supported": False}
    manifest, plan = checked["manifest"], checked["plan"]
    budget = PhaseBudget(checked["protocol_path"].parent / ("phase-cpu-budget-" + checked["protocol_sha256"]),
        identity={"protocol_sha256": checked["protocol_sha256"],
                  "source_sha256": source_hashes(Path(__file__).resolve().parents[1])},
        phase_cpu_seconds=checked["phase_cpu_seconds"])
    identity = {"schema": "isolated-comparison-identity-v1", "plan_sha256": checked["plan_sha256"],
                "manifest_sha256": checked["manifest_sha256"], "protocol_sha256": checked["protocol_sha256"],
                "source_sha256": plan["source_sha256"], "phase_budget_binding_sha256": budget.identity_digest}
    parent = RunStore(output, identity)
    previous = parent.completed()
    if previous is not None:
        _verify_completed(parent.root, previous, budget)
        return previous
    parent.claim()
    result = {key: manifest[key] for key in ("root_id", "request_id", "configuration_id", "repeat_index", "phase")}
    result.update(schema="calibration-experiment-v1", status="running", cache_mode=CACHE_MODE,
        service_boundary=BOUNDARY, planned_methods=list(METHODS), method_order=manifest["method_order"],
        service_mode=manifest.get("service_mode", "certified"), service_family=manifest.get("service_family", "response"),
        response_tier=manifest["chart"].get("response_tier", "linear"), verifier_policy=manifest.get("verifier_policy", "spectral"),
        target_manifest_sha256=plan["target_manifest_sha256"], protocol_sha256=checked["protocol_sha256"],
        run_manifest_sha256=checked["manifest_sha256"], isolated_plan_sha256=checked["plan_sha256"],
        source_sha256=plan["source_sha256"], children={},
        methods={name: {"status": "not_started", "failure": {"kind": "setup_unavailable"}} for name in METHODS},
        measurement_contract={"execution": "separate fresh process for setup and each method; OS caches uncontrolled",
            "method_boundary": "limited worker request and budget admission, process startup, input loading, one method, artifacts, child receipt commit, exit and cleanup",
            "excluded_from_method": "parent source and plan verification, parent equality verification, post-cleanup CPU settlement, worker logs/control receipt, parent receipt commit, and heldout evaluation",
            "quality": "heldout records validated; NLP quality not measured by this executor",
            "memory": "wait4 process peak RSS; RLIMIT_AS controls virtual address space",
            "storage_contract": "external research archive retains original state and attempts; canonical live-state guarantee only"},
        phase_cpu_budget={"directory": str(budget.root), "binding_sha256": budget.identity_digest},
        confirmation_supported=False)
    original = None
    started = time.perf_counter_ns()
    try:
        parent.write_artifact("plan.json", checked["raw"])
        for role in ("setup", *manifest["method_order"]):
            current = validate_isolated_plan(path, execute=True)
            if any(current[key] != checked[key] for key in ("plan_sha256", "manifest_sha256", "protocol_sha256")):
                raise ValueError("isolated inputs changed before dispatch")
            if role != "setup" and original is None:
                break
            request = {"schema": "isolated-child-request-v1", "role": role,
                "manifest_path": str(checked["manifest_path"]), "manifest_sha256": checked["manifest_sha256"],
                "source_sha256": plan["source_sha256"], "target_manifest_sha256": plan["target_manifest_sha256"],
                "plan_sha256": checked["plan_sha256"], "output": str(parent.root / "children" / role),
                "original_state": None if role == "setup" else original}
            parent.write_artifact(role + "-request.json", canonical_json(request))
            request_path = _request_path(parent.root, role, request)
            worker = run_limited([sys.executable, "-m", "src.isolated_comparison", "--child",
                str(request_path)], parent.root / "workers" / role,
                checked["limits"], identity={"isolated_request_sha256": digest(canonical_json(request))},
                phase_budget=budget, phase=manifest["phase"])
            worker_path = parent.root / "workers" / role / "result.json"
            child_path = Path(request["output"]) / "result.json"
            child = _saved_child(request["output"], request, worker)
            saved = {"request": request, "worker_result_sha256": digest(worker_path.read_bytes()),
                     "child_result_sha256": digest(child_path.read_bytes()) if child_path.is_file() else None,
                     "worker_outcome": worker["outcome"]}
            result["children"][role] = saved
            success = worker["outcome"]["status"] == "complete" and child is not None and child["outcome"]["status"] == "complete"
            clock = {"complete_wall_time_ns": worker["outcome"]["elapsed_wall_ns"],
                     "wall_time_ns": worker["outcome"]["elapsed_wall_ns"],
                     "worker_resource_usage": worker.get("resource_usage"), "worker_pid": worker.get("worker_pid")}
            if role == "setup":
                result["setup"] = dict(clock, status="complete" if success else "failed",
                                       worker_outcome=worker["outcome"])
                if success:
                    info = child["artifact"]
                    original = {"path": str(Path(request["output"]) / child["attempt"] / "original-state.json"),
                                "sha256": info["state_sha256"]}
                    result["setup"].update(info, service_telemetry=child["service_telemetry"])
                    result.update(service_manifest_sha256=child["service_manifest_sha256"],
                                  chart_sha256=child["metadata"]["chart_sha256"], declared_target_verified=True)
            elif success:
                if (child["service_manifest_sha256"] != result["service_manifest_sha256"]
                        or child["metadata"]["chart_sha256"] != result["chart_sha256"]):
                    raise ValueError("isolated method service differs from setup")
                result["methods"][role] = dict(child["artifact"], **clock, status="pending_verification",
                    service_telemetry=child["service_telemetry"], exact_state_equal=None, exact_model_equal=None)
            else:
                failure = (child["outcome"].get("failure") if child and child["outcome"]["status"] != "complete"
                           else {"kind": worker["outcome"]["kind"]})
                result["methods"][role] = dict(clock, status="failed", failure=failure,
                                               exact_state_equal=None, exact_model_equal=None)
            parent.write_status(result)
        verification = time.perf_counter_ns()
        oracle = result["methods"]["direct_fresh"]
        for method, row in result["methods"].items():
            if row["status"] != "pending_verification":
                continue
            if oracle["status"] not in ("pending_verification", "complete"):
                row.update(status="failed", failure={"kind": "oracle_unavailable"})
                continue
            equal = []
            for suffix in ("state", "model"):
                pieces = []
                for name in (method, "direct_fresh"):
                    request = result["children"][name]["request"]
                    child = RunStore(request["output"], _child_identity(request)).completed()
                    pieces.append((Path(request["output"]) / child["attempt"] / (name + "-" + suffix + ".json")).read_bytes())
                equal.append(pieces[0] == pieces[1])
            row.update(exact_state_equal=equal[0], exact_model_equal=equal[1],
                       status="complete" if all(equal) else "failed")
            if not all(equal):
                row["failure"] = {"kind": "mismatch", "message": "complete state or model differs from direct retained oracle"}
        result["equality_verification_ns"] = time.perf_counter_ns() - verification
        result.update(status="complete", outcome="complete" if all(row["status"] == "complete" for row in result["methods"].values()) else "failed",
            controller_wall_ns_before_commit=time.perf_counter_ns() - started,
            controller_completion_means="all attainable outcomes are sealed; inspect outcome and method status",
            phase_cpu_budget_at_completion=budget.snapshot())
        validate_run(result)
        parent.write_artifact("analysis.json", canonical_json(result))
        return parent.finish(result)
    except BaseException as exc:
        result.update(status="failed", failure=_failure(exc))
        parent.write_status(result)
        raise
    finally:
        parent.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child", required=True, type=Path)
    args = parser.parse_args()
    return 0 if _child(args.child) else 1


if __name__ == "__main__":
    raise SystemExit(main())
