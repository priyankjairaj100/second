"""Exact retained model construction without any deletion index.

This baseline shares the finite target and exact quantizer. Its output contains
only the target binding and stage codes. It cannot service a later deletion.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
import time

from .exact_core import sequential_oracle
from .repair_service import (CertifiedPrefix, JobSpec, Record, StageOutput,
    _Work, _zero, _matrix, _gram, _combine, _metric)
from .run_store import RunStore, canonical_json, digest
from .service_telemetry import operation, ServiceTelemetry


@dataclass(frozen=True)
class ModelOutput:
    target_manifest_digest: str
    model: tuple[StageOutput, ...]

    def canonical_bytes(self):
        return canonical_json({"schema": "quantized-target-model-v1",
            "target_manifest_sha256": self.target_manifest_digest,
            "stages": [stage._json() for stage in self.model]})

    @property
    def digest(self):
        return digest(self.canonical_bytes())


@dataclass(frozen=True)
class ModelFreshResult:
    output: ModelOutput
    ledger: object


def target_model_bytes(target_digest, model):
    """Compare common target/codes, without a family-specific state digest."""
    from .experiment_runner import _sha
    _sha(target_digest)
    return ModelOutput(target_digest, tuple(model)).canonical_bytes()


@operation
def fresh_model(job: JobSpec, evaluator, records, *, target_digest: str):
    """Run the complete retained sequential target and discard temporary Grams."""
    from .experiment_runner import _sha
    _sha(target_digest)
    if not isinstance(job, JobSpec) or not callable(evaluator):
        raise TypeError("a job and evaluator are required")
    work, data = _Work(), {}
    for record in records:
        if not isinstance(record, Record) or record.record_id in data:
            raise ValueError("records must be unique Record objects")
        data[record.record_id] = record
        work.add("fresh_input_records")
        work.add("fresh_input_payload_bytes", len(record.payload))
    outputs, ancestors = [], {}
    for stage in job.stages:
        closure = set(stage.dependencies)
        for dependency in stage.dependencies:
            closure.update(ancestors[dependency])
        ancestors[stage.stage_id] = closure
        prefix = CertifiedPrefix(job.manifest_digest,
            tuple(output for output in outputs if output.stage_id in closure))
        raw = _zero(stage.width)
        for rid in sorted(data):
            with _span("fresh_feature_evaluation"):
                features = _matrix(evaluator(data[rid], stage, prefix),
                                   "target features", stage.width, True)
            work.add("fresh_target_evaluator_calls")
            with _span("exact_gram"):
                raw = _combine(raw, _gram(features, work), 1, work)
        with _span("factor_rounding"):
            quantized = sequential_oracle(stage.weights, _metric(raw, stage, work), stage.grids)
        outputs.append(StageOutput(stage.stage_id, quantized.codes))
        work.add("exact_factorization_calls")
        work.add("rounding_decisions", len(stage.weights) * stage.width)
    return ModelFreshResult(ModelOutput(target_digest, tuple(outputs)), work.freeze())


def _span(category):
    # Use the public timing decorator through a context manager-free callback.
    from contextlib import nullcontext
    from .service_telemetry import _CURRENT
    collector = _CURRENT.get()
    return collector.span(category) if collector is not None else nullcontext()


def model_fresh_command(path, output, *, inventory_path=None, inventory_run_id=None,
                        plan_path=None, sequence_step=None, validate_only=False, execution_mode="clean"):
    """Construct the literal command used by exact live CPU admission."""
    if execution_mode not in (None, "clean", "diagnostic"):
        raise ValueError("unsupported model-only execution mode")
    values = (inventory_path, inventory_run_id, plan_path)
    if any(value is not None for value in values) and not all(value is not None for value in values):
        raise ValueError("model-only inventory evidence requires inventory, run ID, and plan")
    if sequence_step is not None and (inventory_path is None or type(sequence_step) is not int or sequence_step < -1):
        raise ValueError("sequence step requires verified inventory and an integer >= -1")
    command = [sys.executable, str(Path(__file__).resolve().parents[1] / "scripts/run_model_fresh.py"),
               str(Path(path).absolute()), "--output", str(Path(output).absolute())]
    if inventory_path is not None:
        if type(inventory_run_id) is not str or not inventory_run_id:
            raise ValueError("model-only inventory run ID must be nonempty")
        command += ["--inventory", str(Path(inventory_path).absolute()), "--inventory-run-id", inventory_run_id,
                    "--plan", str(Path(plan_path).absolute())]
    if sequence_step is not None:
        command += ["--sequence-step", str(sequence_step)]
    if validate_only:
        command += ["--validate-only"]
    if execution_mode is not None:
        command += ["--execution-mode", execution_mode]
    return command


def run_model_fresh(path, output, *, validate_only=False, inventory_path=None, inventory_run_id=None,
                    plan_path=None, sequence_step=None, execution_mode=None):
    from .instrumentation import instrumentation_scope
    with instrumentation_scope(execution_mode or "diagnostic"):
        return _run_model_fresh(path, output, validate_only=validate_only, inventory_path=inventory_path,
            inventory_run_id=inventory_run_id, plan_path=plan_path, sequence_step=sequence_step,
            execution_mode=execution_mode)


def _run_model_fresh(path, output, *, validate_only=False, inventory_path=None, inventory_run_id=None,
                    plan_path=None, sequence_step=None, execution_mode=None):
    """Verify membership and live admission before loading local model parameters."""
    from .experiment_runner import _read_json, _referenced_json, _run_manifest, _failure
    from .experiment_inventory import source_hashes
    manifest_path = Path(path).absolute()
    manifest, raw = _read_json(manifest_path)
    protocol, protocol_raw = _referenced_json(manifest_path.parent, manifest["protocol"])
    command = model_fresh_command(path, output, validate_only=validate_only, inventory_path=inventory_path,
        inventory_run_id=inventory_run_id, plan_path=plan_path, sequence_step=sequence_step, execution_mode=execution_mode)
    authorization = None
    if manifest.get("phase") == "confirmation" and inventory_path is None:
        raise ValueError("model-only confirmation requires a frozen inventory; standalone execution is blocked")
    if manifest.get("phase") != "software_test" and "experiments_paused" in str(protocol.get("status", "")):
        raise ValueError("the protocol keeps research experiments paused")
    if manifest.get("phase") != "software_test":
        from .transaction_timing import verify_command_admission
        verify_command_admission(digest(protocol_raw), manifest["phase"], command)
    if inventory_path is not None:
        from .measured_inventory import verify_model_manifest
        authorization = verify_model_manifest(inventory_path, inventory_run_id, plan_path, manifest_path,
                                               sequence_step=sequence_step, execute=not validate_only)
        if authorization["execution_mode"] != (execution_mode or "diagnostic"):
            raise ValueError("model-only instrumentation differs from frozen inventory")
        if authorization["protocol_sha256"] != digest(protocol_raw) or authorization["manifest_sha256"] != digest(raw):
            raise ValueError("model-only inventory binds different manifest or protocol bytes")
    root = Path(__file__).resolve().parents[1]
    sources = source_hashes(root)
    identity = {"schema": "model-fresh-identity-v1", "manifest_sha256": digest(raw),
                "protocol_sha256": digest(protocol_raw), "source_sha256": sources,
                "output_contract": "model_only"}
    identity["execution_mode"] = execution_mode or "diagnostic"
    if authorization is not None:
        identity["inventory"] = authorization
    # Loading on resume verifies all used local inputs before reusing a receipt.
    prepared = _run_manifest(path, output, prepare_only=True, model_only_prepare=True,
                             validate_only=validate_only)
    if validate_only:
        prepared["output_contract"] = "model_only"
        if authorization is not None and prepared.get("status") == "validated":
            if digest(canonical_json(prepared["target"])) != authorization["target_manifest_sha256"]:
                raise ValueError("constructed model-only target differs from inventory")
        return prepared
    decoder, target = prepared["decoder"], prepared["target"]
    if authorization is not None and target.digest != authorization["target_manifest_sha256"]:
        raise ValueError("constructed model-only target differs from inventory")
    store = RunStore(output, identity)
    completed = store.completed()
    if completed is not None:
        return completed
    store.claim()
    telemetry = ServiceTelemetry()
    started = time.perf_counter_ns()
    result = {"schema": "calibration-model-fresh-v1", "status": "running",
              "output_contract": "model_only", "identity": identity,
              "execution_mode": execution_mode or "diagnostic",
              "target_manifest_sha256": target.digest, "preflight": prepared["preflight"],
              "cache_mode": "single_process_os_cache_uncontrolled",
              "canonical_deletion_state_returned": False,
              "reference_index_constructed": False,
              "outcome": {"status": "failed"}}
    from .instrumentation import instrumentation_state
    result["instrumentation_state"] = instrumentation_state()
    try:
        store.write_artifact("manifest.json", raw)
        deleted = set(manifest["deleted_ids"])
        retained = tuple(record for record in prepared["records"] if record.record_id not in deleted)
        job = target.make_job("model-only-exact-fresh-v1")
        def evaluate(record, stage, prefix):
            if prefix.manifest_digest != job.manifest_digest or stage not in job.stages:
                raise ValueError("foreign model-only evaluator input")
            return decoder.stage_features(stage.stage_id, decoder.decode_payload(record.payload), prefix.as_mapping())
        constructed = fresh_model(job, evaluate, retained, target_digest=target.digest, telemetry=telemetry)
        with telemetry.span("artifact_output"):
            with telemetry.span("serialization"):
                model = constructed.output.canonical_bytes()
            with telemetry.span("durable_output"):
                result["model_artifact"] = store.write_artifact("model.json", model)
        result.update(ledger=dict(constructed.ledger.as_mapping()), retained_records=len(retained),
                      service_telemetry=telemetry.payload(), outcome={"status": "complete"})
        if source_hashes(root) != sources or _read_json(manifest_path)[1] != raw:
            raise ValueError("model-only source or manifest changed during execution")
        if _referenced_json(manifest_path.parent, manifest["protocol"])[1] != protocol_raw:
            raise ValueError("model-only protocol changed during execution")
        if authorization is not None:
            if verify_model_manifest(inventory_path, inventory_run_id, plan_path, manifest_path,
                                     sequence_step=sequence_step, execute=True) != authorization:
                raise ValueError("model-only inventory authorization changed during execution")
    except BaseException as exc:
        result.update(outcome={"status": "failed", "failure": _failure(exc)},
                      service_telemetry=telemetry.payload())
    finally:
        result.update(status="complete", internal_wall_ns_before_commit=time.perf_counter_ns()-started,
                      clock_scope="diagnostic only; use the measured process wrapper for the complete child transaction")
        try:
            result = store.finish(result)
        finally:
            store.close()
    return result
