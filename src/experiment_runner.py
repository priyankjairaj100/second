"""Local, serial experiment infrastructure. Importing this module runs nothing.

Timing covers declared method boundaries. It does not estimate callback costs.
Only the warm sequential mode is supported. Operating-system caches are uncontrolled.
"""
from __future__ import annotations

from dataclasses import dataclass
import gc
from hashlib import sha256
import math
from pathlib import Path
import platform
import resource
import sys
import time
import tracemalloc
from typing import Callable

from .repair_service import Record
from .run_store import RunStore, canonical_json, digest, strict_json
from .service_telemetry import ServiceTelemetry

METHODS = ("repair", "indexed_fresh", "direct_fresh")
CACHE_MODE = "warm_sequential_os_cache_uncontrolled"


class ComparisonMismatch(RuntimeError):
    pass


def _integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} requires an integer >= {minimum}")
    return value


def _text(value, name):
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} requires a nonempty string")
    return value


def _sha(value):
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("invalid SHA256")
    return value


def _read_json(path: Path, maximum=64 * 1024 * 1024):
    if path.is_symlink() or not path.is_file():
        raise ValueError("input must be a regular local file")
    if path.stat().st_size > maximum:
        raise ValueError("input JSON exceeds its size limit")
    raw = path.read_bytes()
    return strict_json(raw), raw


def _local(base: Path, value: str) -> Path:
    text = _text(value, "local path")
    if "://" in text:
        raise ValueError("URLs are not accepted")
    raw = Path(text)
    path = raw if raw.is_absolute() else base / raw
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError("symlink input paths are not supported")
    return path.resolve()


def _referenced_json(base, reference):
    if not isinstance(reference, dict) or set(reference) != {"path", "sha256"}:
        raise ValueError("JSON reference requires path and sha256")
    data, raw = _read_json(_local(base, reference["path"]))
    if digest(raw) != _sha(reference["sha256"]):
        raise ValueError("referenced JSON hash mismatch")
    return data, raw


def prepared_records(payload: dict, decoder, *, heldout=False) -> tuple[Record, ...]:
    """Validate prepared IDs. No tokenization or text loading occurs here."""
    if not isinstance(payload, dict) or set(payload) != {"schema", "provenance", "records"}:
        raise ValueError("invalid prepared token manifest fields")
    if payload["schema"] != "prepared-token-records-v1":
        raise ValueError("unknown prepared token schema")
    provenance = payload["provenance"]
    required = {"dataset_id", "dataset_revision", "split", "license", "tokenizer_id", "tokenizer_revision"}
    if not isinstance(provenance, dict) or not required <= set(provenance):
        raise ValueError("record provenance is incomplete")
    for key in required:
        _text(provenance[key], key)
    if not isinstance(payload["records"], list) or not payload["records"]:
        raise ValueError("records must be a nonempty list")
    seen, records = set(), []
    for row in payload["records"]:
        if not isinstance(row, dict) or set(row) != {"id", "tokens"}:
            raise ValueError("invalid prepared record")
        rid = _text(row["id"], "record ID")
        if rid in seen:
            raise ValueError("duplicate record ID")
        seen.add(rid)
        tokens = row["tokens"]
        minimum = 2 if heldout else 1
        if not isinstance(tokens, list) or not minimum <= len(tokens) <= decoder.config.max_sequence_length:
            raise ValueError("invalid record length")
        if any(type(t) is not int or not 0 <= t < decoder.config.vocabulary_size for t in tokens):
            raise ValueError("token IDs must be integers within the vocabulary")
        records.append(Record(rid, decoder.record_payload(tuple(tokens))))
    return tuple(records)


def _rss() -> int:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(rss if sys.platform == "darwin" else rss * 1024)


def measure(call: Callable):
    """Measure one nonnested operation, including its artifact writes."""
    if tracemalloc.is_tracing():
        raise RuntimeError("nested allocation measurement is not supported")
    tracemalloc.start()
    wall = time.perf_counter_ns()
    cpu = time.process_time_ns()
    try:
        result = call()
    except BaseException as exc:
        _, peak = tracemalloc.get_traced_memory()
        metrics = {"wall_time_ns": time.perf_counter_ns() - wall,
                   "cpu_time_ns": time.process_time_ns() - cpu,
                   "peak_python_bytes": peak, "process_peak_rss_bytes": _rss()}
        try:
            exc.runner_metrics = metrics
        except (AttributeError, TypeError):
            pass
        raise
    else:
        _, peak = tracemalloc.get_traced_memory()
        metrics = {"wall_time_ns": time.perf_counter_ns() - wall,
                   "cpu_time_ns": time.process_time_ns() - cpu,
                   "peak_python_bytes": peak, "process_peak_rss_bytes": _rss()}
        return result, metrics
    finally:
        tracemalloc.stop()


def _failure(exc):
    from .transformer_backend import FiniteTargetError
    from .certified_intervals import ArithmeticLimit, UnresolvedRounding
    kind = ("mismatch" if isinstance(exc, ComparisonMismatch) else
            "memory_limit" if isinstance(exc, MemoryError) else
            "timeout" if isinstance(exc, TimeoutError) else
            "evaluator_abort" if isinstance(exc, (FiniteTargetError, ArithmeticLimit, UnresolvedRounding)) else
            "interrupted" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else "exception")
    return {"kind": kind, "type": type(exc).__name__, "message": str(exc)}


def _model_bytes(state):
    return canonical_json({"schema": "quantized-stage-model-v1", "manifest": state.manifest_digest,
                           "stages": [stage._json() for stage in state.model]})


def _integer_sizes(value):
    """Describe exact serialized numbers without claiming a physical memory size."""
    if type(value) is int:
        return (1, abs(value).bit_length())
    if isinstance(value, list):
        parts = [_integer_sizes(x) for x in value]
    elif isinstance(value, dict):
        parts = [_integer_sizes(x) for x in value.values()]
    elif isinstance(value, str) and value.startswith('{'):
        try:
            return _integer_sizes(strict_json(value.encode('ascii')))
        except (ValueError, UnicodeError):
            return (0, 0)
    else:
        return (0, 0)
    return (sum(x[0] for x in parts), max((x[1] for x in parts), default=0))


def _commit_state(store, method, result):
    state = result.state
    raw = state.canonical_bytes()
    model = _model_bytes(state)
    state_meta = store.write_artifact(method + "-state.json", raw)
    model_meta = store.write_artifact(method + "-model.json", model)
    sizes = _integer_sizes(strict_json(raw))
    return {"state_sha256": state_meta["sha256"], "model_sha256": model_meta["sha256"],
            "state_bytes": len(raw), "model_bytes": len(model),
            "stored_aggregate_rationals": state.stored_aggregate_rational_count,
            "serialized_integer_count": sizes[0], "maximum_integer_bits": sizes[1],
            "ledger": dict(result.ledger.as_mapping()),
            "stages": [{"stage_id": s.stage_id, "route": s.route,
                        "certificate_attempts": s.certificate_attempts,
                        "replayed_groups": list(s.replayed_groups),
                        "unknown_groups": list(s.unknown_groups)} for s in result.stages]}


def heldout_nll(decoder, records, state=None):
    """Diagnostic next-token NLL. Its libm metric is not an exact certificate."""
    prefix = None if state is None else {s.stage_id: s.codes for s in state.model}
    total, count = 0.0, 0
    for record in records:
        tokens = decoder.decode_payload(record.payload)
        if len(tokens) < 2:
            raise ValueError("heldout records require at least two tokens")
        logits = decoder.logits(tokens, prefix)
        for position, target in enumerate(tokens[1:]):
            row = logits[position]
            maximum = max(row)
            loss = math.log(math.fsum(math.exp(x - maximum) for x in row)) + maximum - row[target]
            if not math.isfinite(loss):
                raise ValueError("nonfinite heldout loss")
            total += loss
            count += 1
    if count == 0:
        raise ValueError("heldout target count is zero")
    return {"nll_sum": total, "target_tokens": count, "mean_nll": total / count,
            "metric_contract": "binary64 logits; stable Python libm logsumexp; independent records; no cross-record targets"}


def run_comparison(decoder, service, records, deleted_ids, heldout, store: RunStore,
                   metadata: dict, *, method_order=METHODS, preflight=None, overall_start_ns=None,
                   service_mode="certified", initial_state=None, sequence_lineage=None):
    """Run one request. This low-level API also supports tiny software fixtures."""
    if tuple(sorted(method_order)) != tuple(sorted(METHODS)):
        raise ValueError("method order must contain each supported method exactly once")
    if service_mode not in ("certified", "identity_only", "fixed_reference", "full_replay"):
        raise ValueError("unsupported service mechanism control")
    records = tuple(records)
    heldout = tuple(heldout)
    deleted_ids = tuple(deleted_ids)
    by_id = {r.record_id: r for r in records}
    if len(by_id) != len(records) or len(set(deleted_ids)) != len(deleted_ids) or not set(deleted_ids) <= set(by_id):
        raise ValueError("deletion IDs must be unique calibration IDs")
    if not heldout:
        raise ValueError("heldout records are required")
    remaining = tuple(r for r in records if r.record_id not in set(deleted_ids))
    if initial_state is not None:
        # Validate persisted finite-target state before relying on its record bindings.
        initial_state = service.load_state(initial_state.canonical_bytes(), expected_digest=initial_state.digest)
        if {r.record_id: r.content_digest for r in initial_state.records} != {
                r.record_id: r.content_digest for r in records}:
            raise ValueError("initial state records differ from the live calibration records")
    if sequence_lineage is not None:
        if initial_state is None or not isinstance(sequence_lineage, dict):
            raise ValueError("sequence lineage requires an initial state and an object")
        sequence_lineage = strict_json(canonical_json(sequence_lineage))
        if sequence_lineage.get("predecessor_state_sha256") != initial_state.digest:
            raise ValueError("sequence predecessor state differs from lineage")
    for key in ("root_id", "request_id", "configuration_id"):
        _text(metadata.get(key), key)
    _integer(metadata.get("repeat_index"), "repeat index")
    if metadata.get("phase") not in ("development", "confirmation", "software_test"):
        raise ValueError("invalid experiment phase")
    input_binding = {
        "service_manifest_sha256": service.manifest_digest, "metadata": metadata,
        "records": [[r.record_id, r.content_digest] for r in records],
        "deleted_ids": list(deleted_ids),
        "heldout": [[r.record_id, r.content_digest] for r in heldout],
        "method_order": list(method_order), "service_mode": service_mode}
    labels = {"service_family": getattr(service, "service_family", "response"),
              "response_tier": getattr(service, "response_tier", "linear"),
              "verifier_policy": getattr(service, "verifier_policy", "spectral")}
    if labels != {"service_family": "response", "response_tier": "linear", "verifier_policy": "spectral"}:
        input_binding["service_configuration"] = labels
    if initial_state is not None or sequence_lineage is not None:
        input_binding.update(initial_state_sha256=initial_state.digest, sequence_lineage=sequence_lineage)
    input_sha256 = digest(canonical_json(input_binding))
    complete = store.completed()
    if complete is not None:
        if complete.get("input_sha256") != input_sha256:
            raise ValueError("saved run binds different records or request settings")
        return complete
    start = time.perf_counter_ns()
    overall_start_ns = start if overall_start_ns is None else overall_start_ns
    store.claim()
    result = dict(metadata, schema="calibration-experiment-v1", status="running", input_sha256=input_sha256,
                  cache_mode=CACHE_MODE, planned_methods=list(METHODS), method_order=list(method_order),
                  service_mode=service_mode,
                  target_manifest_sha256=metadata.get("target_manifest_sha256", service.target_manifest_digest),
                  service_job_sha256=service.target_manifest_digest,
                  service_manifest_sha256=service.manifest_digest,
                  service_boundary="service_through_atomic_artifact_fsync",
                  methods={m: {"status": "not_started", "failure": {"kind": "not_started"}} for m in METHODS},
                  measurement_contract={
                      "method_boundary": "service call, canonical serialization, artifact hashing, atomic output writes and directory fsync",
                      "excluded_from_method": "checkpoint and input loading, original preparation, independent equality checks, heldout evaluation, final result commit",
                      "memory": "Python allocation peak during each measured scope; RSS is process lifetime high-water mark",
                      "execution": "serial shared process, warm objects, uncontrolled OS caches; method order is declared",
                      "timing_interpretation": "instrumented reference execution; exclusive internal diagnostic spans; not production latency",
                      "storage_contract": "external research archive retains original states and failed attempts; deletion guarantee covers returned canonical live state only"})
    result["preflight"] = preflight
    result.update(labels)
    result["initial_model_role"] = "original_preparation" if initial_state is None else "preceding_committed_state"
    if sequence_lineage is not None:
        result["sequence_lineage"] = sequence_lineage
    active = "initial_fresh"
    try:
        store.write_artifact("run-metadata.json", canonical_json(metadata))
        setup_telemetry = ServiceTelemetry()
        def initial():
            if initial_state is not None:
                with setup_telemetry.span("persisted_state_reload"):
                    loaded = service.load_state(initial_state.canonical_bytes(), expected_digest=initial_state.digest)
                return loaded, {"source": "preceding_committed_state", "state_sha256": loaded.digest,
                                "original_preparation_executed": False}
            fresh = service.fresh(records, telemetry=setup_telemetry)
            with setup_telemetry.span("artifact_output"):
                info = _commit_state(store, "original", fresh)
            # Validate the actual saved canonical bytes before later requests.
            saved_bytes = (store.attempt / "original-state.json").read_bytes()
            with setup_telemetry.span("persisted_state_reload"):
                loaded = service.load_state(saved_bytes, expected_digest=fresh.state.digest)
            return loaded, info
        (old_state, setup), setup_clock = measure(initial)
        result["setup"] = dict(setup, **setup_clock, service_telemetry=setup_telemetry.payload())
        retained_source = {r.record_id: r for r in remaining}.__getitem__
        states = {}
        for method in method_order:
            active = method
            result["methods"][method] = {"status": "running", "exact_state_equal": None, "exact_model_equal": None}
            store.write_status(result)
            gc.collect()  # Outside the declared method boundary, for every arm.
            preparation = {}
            telemetry = ServiceTelemetry()
            def arm():
                with telemetry.span("deleted_payload_lookup"):
                    deleted = tuple(by_id[rid] for rid in deleted_ids)
                if method == "repair":
                    output = service.repair(old_state, deleted, retained_source,
                                            mode=service_mode, telemetry=telemetry)
                elif method == "indexed_fresh":
                    stamp = time.perf_counter_ns()
                    prepared = service.prepare_index(old_state, deleted, telemetry=telemetry)
                    preparation["index_preparation_ns"] = time.perf_counter_ns() - stamp
                    preparation["index_preparation_ledger"] = dict(prepared.ledger.as_mapping())
                    output = service.indexed_fresh(prepared.index, retained_source,
                                                   mode=service_mode, telemetry=telemetry)
                else:
                    with telemetry.span("retained_payload_selection"):
                        deleted_set = set(deleted_ids)
                        retained = tuple(r for r in records if r.record_id not in deleted_set)
                    output = service.fresh(retained, telemetry=telemetry)
                with telemetry.span("artifact_output"):
                    info = _commit_state(store, method, output)
                return output.state, info
            try:
                (state, info), metrics = measure(arm)
                states[method] = state
                result["methods"][method] = dict(info, **metrics, **preparation,
                    complete_wall_time_ns=metrics["wall_time_ns"], status="running",
                    exact_state_equal=None, exact_model_equal=None)
            except Exception as exc:
                result["methods"][method] = dict(status="failed", failure=_failure(exc),
                    exact_state_equal=None, exact_model_equal=None, **getattr(exc, "runner_metrics", {}))
            result["methods"][method]["service_telemetry"] = telemetry.payload()
            store.write_status(result)
        active = "equality_verification"
        verification_start = time.perf_counter_ns()
        oracle = states.get("direct_fresh")
        if oracle is not None:
            for method, state in states.items():
                equal_state = state.canonical_bytes() == oracle.canonical_bytes()
                equal_model = _model_bytes(state) == _model_bytes(oracle)
                row = result["methods"][method]
                row.update(exact_state_equal=equal_state, exact_model_equal=equal_model,
                           status="complete" if equal_state and equal_model else "failed")
                if not (equal_state and equal_model):
                    row["failure"] = _failure(ComparisonMismatch("full model or canonical state differs from direct retained oracle"))
        else:
            for method in states:
                result["methods"][method].update(status="failed", failure={
                    "kind": "oracle_unavailable", "message": "direct retained oracle did not complete"})
        result["equality_verification_ns"] = time.perf_counter_ns() - verification_start
        active = "heldout_evaluation"
        if all(row["status"] == "complete" for row in result["methods"].values()):
            def quality():
                return {"base": heldout_nll(decoder, heldout),
                        "original_quantized": heldout_nll(decoder, heldout, old_state),
                        "retained_direct": heldout_nll(decoder, heldout, oracle),
                        "repaired": heldout_nll(decoder, heldout, states["repair"])}
            result["quality"], result["quality_measurement"] = measure(quality)
            if result["quality"]["retained_direct"] != result["quality"]["repaired"]:
                raise ComparisonMismatch("heldout metrics differ for exact model artifacts")
            result["status"] = "complete"
        else:
            result["status"] = "failed"
            result["failure"] = {"kind": "method_failed", "stage": "comparison", "message": "one or more planned methods failed"}
        result["full_run_wall_ns_before_result_commit"] = time.perf_counter_ns() - start
        result["complete_pipeline_wall_ns_before_result_commit"] = time.perf_counter_ns() - overall_start_ns
        if result["status"] == "complete":
            return store.finish(result)
        store.write_status(result)
        return strict_json((store.root / "result.json").read_bytes())
    except BaseException as exc:
        result.update(status="failed", failure=dict(_failure(exc), stage=active),
                      full_run_wall_ns_before_result_commit=time.perf_counter_ns() - start)
        store.write_status(result)
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        return strict_json((store.root / "result.json").read_bytes())
    finally:
        store.close()


def _run_manifest(path: str | Path, output: str | Path, *, validate_only=False, prepare_only=False,
                  _manifest_override=None):
    """Load a local checkpoint and hash-bound prepared data. Never fetch data."""
    overall_start_ns = time.perf_counter_ns()
    from .checkpoint_adapter import load_gpt2_checkpoint
    from .certified_transformer import CertifiedDecoder
    from .target_manifest import TargetRecipe, build_target
    from .chart_construction import ChartRecipe, preview_chart, build_chart, make_service
    from .resource_preflight import inspect_local_config
    manifest_path = Path(path).absolute()
    manifest, raw = _read_json(manifest_path) if _manifest_override is None else _manifest_override
    required = {"schema", "root_id", "request_id", "configuration_id", "repeat_index", "phase",
                "checkpoint", "calibration", "heldout", "deleted_ids", "target", "chart", "method_order", "protocol"}
    if (not isinstance(manifest, dict) or not required <= set(manifest)
            or set(manifest) - required - {"service_mode", "verifier_policy", "service_family"}
            or manifest["schema"] != "calibration-run-v1"):
        raise ValueError("invalid run manifest fields or schema")
    service_mode = manifest.get("service_mode", "certified")
    if service_mode not in ("certified", "identity_only", "fixed_reference", "full_replay"):
        raise ValueError("unsupported service mechanism control")
    service_family = manifest.get("service_family", "response")
    if service_family not in ("response", "identity_cache"):
        raise ValueError("unsupported service family")
    verifier_policy = manifest.get("verifier_policy", "spectral")
    if verifier_policy not in ("spectral", "spectral_or_interval"):
        raise ValueError("unsupported verifier policy")
    if service_family == "identity_cache" and (verifier_policy != "spectral" or service_mode != "certified"):
        raise ValueError("identity cache requires its default verifier and certified mode")
    base = manifest_path.parent
    protocol, protocol_raw = _referenced_json(base, manifest["protocol"])
    for key in ("root_id", "request_id", "configuration_id"):
        _text(manifest[key], key)
    _integer(manifest["repeat_index"], "repeat_index")
    if manifest["phase"] not in ("development", "confirmation", "software_test"):
        raise ValueError("invalid experiment phase")
    if manifest["phase"] == "confirmation":
        if (not isinstance(protocol, dict) or protocol.get("schema") != "calibration-protocol-v1"
                or protocol.get("status") != "frozen_confirmation" or protocol.get("blocked_fields") != []):
            raise ValueError("confirmation requires a frozen protocol without blocked fields")
        _sha(protocol.get("planned_inventory_sha256"))
    if (not validate_only and manifest["phase"] != "software_test" and isinstance(protocol, dict)
            and "experiments_paused" in str(protocol.get("status", ""))):
        raise ValueError("the protocol keeps research experiments paused")
    if tuple(sorted(manifest["method_order"])) != tuple(sorted(METHODS)):
        raise ValueError("invalid method order")
    checkpoint = manifest["checkpoint"]
    if not isinstance(checkpoint, dict) or set(checkpoint) != {"path", "files_sha256", "max_parameter_elements"}:
        raise ValueError("checkpoint reference requires path, hashes, and element limit")
    _integer(checkpoint["max_parameter_elements"], "parameter limit", 1)
    if not isinstance(checkpoint["files_sha256"], dict) or not checkpoint["files_sha256"]:
        raise ValueError("checkpoint hashes are required")
    for value in checkpoint["files_sha256"].values():
        _sha(value)
    preflight_start = overall_start_ns
    recipe = TargetRecipe.from_payload(manifest["target"])
    chart_recipe = ChartRecipe.from_payload(manifest["chart"])
    if service_family == "identity_cache" and (chart_recipe.mode != "none" or chart_recipe.response_tier != "linear"
            or chart_recipe.radius != 1 or chart_recipe.precision_bits != 96):
        raise ValueError("identity cache requires the none chart, linear label, and default radius and precision")
    resource_plan = inspect_local_config(_local(base, checkpoint["path"]), chart_recipe, recipe)
    if not resource_plan.allowed_by_plan:
        if validate_only:
            return {"schema": "calibration-run-validation-v1", "status": "rejected",
                    "manifest_sha256": digest(raw), "resource_plan": resource_plan.payload(),
                    "empirical_work_executed": False, "checkpoint_parameters_loaded": False}
        resource_plan.require_allowed()
    def load():
        loaded = load_gpt2_checkpoint(_local(base, checkpoint["path"]),
                                      max_parameter_elements=checkpoint["max_parameter_elements"])
        if loaded.provenance["files_sha256"] != checkpoint["files_sha256"]:
            raise ValueError("checkpoint file hashes differ from run manifest")
        decoder = CertifiedDecoder(loaded.decoder)
        calibration, calibration_raw = _referenced_json(base, manifest["calibration"])
        heldout, heldout_raw = _referenced_json(base, manifest["heldout"])
        records = prepared_records(calibration, decoder)
        evaluation = prepared_records(heldout, decoder, heldout=True)
        if {r.record_id for r in records} & {r.record_id for r in evaluation}:
            raise ValueError("calibration and heldout record IDs overlap")
        if {r.content_digest for r in records} & {r.content_digest for r in evaluation}:
            raise ValueError("calibration and heldout token records overlap")
        if not isinstance(manifest["deleted_ids"], list) or len(set(manifest["deleted_ids"])) != len(manifest["deleted_ids"]):
            raise ValueError("deletion IDs must be a unique list")
        if not set(manifest["deleted_ids"]) <= {r.record_id for r in records}:
            raise ValueError("delete only calibration IDs")
        recipe = TargetRecipe.from_payload(manifest["target"])
        token_count = sum(len(decoder.decode_payload(r.payload)) for r in records)
        if recipe.original_token_count != token_count:
            raise ValueError("original normalization differs from calibration token count")
        target = build_target(decoder, recipe)
        chart_recipe = ChartRecipe.from_payload(manifest["chart"])
        if service_family == "identity_cache":
            from .chart_construction import identity_preview
            preview = identity_preview(decoder, target)
        else:
            preview = preview_chart(decoder, target, chart_recipe).payload()
        return decoder, records, evaluation, target, chart_recipe, preview, loaded.provenance
    (decoder, records, heldout, target, chart_recipe, preview, provenance), clock = measure(load)
    validation = {"schema": "calibration-run-validation-v1", "status": "validated",
                  "manifest_sha256": digest(raw), "target": target.payload(), "chart_preview": preview,
                  "checkpoint": provenance, "loading_measurement": clock, "resource_plan": resource_plan.payload(),
                  "calibration_records": len(records), "heldout_records": len(heldout),
                  "cache_mode": CACHE_MODE, "empirical_work_executed": False}
    if validate_only:
        return validation
    if service_family == "identity_cache":
        from .chart_construction import make_identity_service
        service = make_identity_service(decoder, target)
        construction_payload = {"schema": "identity-cache-construction-v1", "target_sha256": target.digest,
                                "service_manifest_sha256": service.manifest_digest}
        construction_digest = digest(canonical_json(construction_payload))
    else:
        construction = build_chart(decoder, target, chart_recipe)
        service = make_service(decoder, target, construction, verifier_policy=verifier_policy)
        construction_payload, construction_digest = construction.payload(), construction.digest
    metadata = {key: manifest[key] for key in ("root_id", "request_id", "configuration_id", "repeat_index", "phase")}
    metadata.update(run_manifest_sha256=digest(raw), protocol_sha256=digest(protocol_raw), service_mode=service_mode,
                    target_manifest_sha256=target.digest, chart_sha256=construction_digest,
                    source_sha256={p.name: digest(p.read_bytes()) for p in sorted(Path(__file__).parent.glob('*.py'))},
                    environment={"python": sys.version, "platform": platform.platform()})
    preflight = dict(validation, chart=construction_payload,
                    preflight_wall_ns=time.perf_counter_ns() - preflight_start)
    if prepare_only:
        return {"decoder": decoder, "service": service, "records": records, "heldout": heldout,
                "metadata": metadata, "preflight": preflight, "service_mode": service_mode,
                "method_order": manifest["method_order"], "overall_start_ns": overall_start_ns}
    store = RunStore(output, {"manifest_sha256": digest(raw), "metadata": metadata,
                              "service_manifest_sha256": service.manifest_digest})
    return run_comparison(decoder, service, records, manifest["deleted_ids"], heldout, store, metadata,
                          method_order=manifest["method_order"], preflight=preflight, overall_start_ns=overall_start_ns,
                          service_mode=service_mode)


def run_manifest(path: str | Path, output: str | Path, *, validate_only=False):
    """Preserve a separate failure record when input preparation aborts."""
    try:
        return _run_manifest(path, output, validate_only=validate_only)
    except BaseException as exc:
        from .run_store import atomic_write
        directory = Path(output).absolute()
        if directory.is_symlink() or any(p.is_symlink() for p in directory.parents):
            raise
        directory.mkdir(parents=True, exist_ok=True)
        failure = {"schema": "calibration-preflight-failure-v1", "status": "failed",
                   "stage": "preflight", "failure": _failure(exc),
                   "execution_may_have_started": True}
        manifest_path = Path(path)
        if manifest_path.is_file() and not manifest_path.is_symlink():
            failure["run_manifest_sha256"] = digest(manifest_path.read_bytes())
        filename = "preflight-failure-" + str(time.time_ns()) + ".json"
        atomic_write(directory / filename, canonical_json(failure))
        raise
