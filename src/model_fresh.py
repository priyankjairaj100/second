"""Exact retained model construction without any deletion index.

This baseline shares the finite target and exact quantizer. Its output contains
only the target binding and stage codes. It cannot service a later deletion.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
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


def run_model_fresh(path, output, *, validate_only=False):
    """Use local manifest inputs. Standalone confirmation remains blocked."""
    from .experiment_runner import _read_json, _referenced_json, _run_manifest, _failure
    from .experiment_inventory import source_hashes
    manifest_path = Path(path).absolute()
    manifest, raw = _read_json(manifest_path)
    protocol, protocol_raw = _referenced_json(manifest_path.parent, manifest["protocol"])
    if manifest.get("phase") == "confirmation":
        raise ValueError("model-only confirmation requires a frozen inventory; standalone execution is blocked")
    if manifest.get("phase") != "software_test" and "experiments_paused" in str(protocol.get("status", "")):
        raise ValueError("the protocol keeps research experiments paused")
    if manifest.get("phase") != "software_test":
        from .transaction_timing import verify_phase_admission
        verify_phase_admission(digest(protocol_raw), manifest["phase"], manifest_path, output)
    root = Path(__file__).resolve().parents[1]
    sources = source_hashes(root)
    identity = {"schema": "model-fresh-identity-v1", "manifest_sha256": digest(raw),
                "protocol_sha256": digest(protocol_raw), "source_sha256": sources,
                "output_contract": "model_only"}
    # Loading on resume verifies all used local inputs before reusing a receipt.
    prepared = _run_manifest(path, output, prepare_only=True, model_only_prepare=True,
                             validate_only=validate_only)
    if validate_only:
        prepared["output_contract"] = "model_only"
        return prepared
    decoder, target = prepared["decoder"], prepared["target"]
    store = RunStore(output, identity)
    completed = store.completed()
    if completed is not None:
        return completed
    store.claim()
    telemetry = ServiceTelemetry()
    started = time.perf_counter_ns()
    result = {"schema": "calibration-model-fresh-v1", "status": "running",
              "output_contract": "model_only", "identity": identity,
              "target_manifest_sha256": target.digest, "preflight": prepared["preflight"],
              "cache_mode": "single_process_os_cache_uncontrolled",
              "canonical_deletion_state_returned": False,
              "reference_index_constructed": False,
              "outcome": {"status": "failed"}}
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
            model = constructed.output.canonical_bytes()
            result["model_artifact"] = store.write_artifact("model.json", model)
        result.update(ledger=dict(constructed.ledger.as_mapping()), retained_records=len(retained),
                      service_telemetry=telemetry.payload(), outcome={"status": "complete"})
        if source_hashes(root) != sources or _read_json(manifest_path)[1] != raw:
            raise ValueError("model-only source or manifest changed during execution")
        if _referenced_json(manifest_path.parent, manifest["protocol"])[1] != protocol_raw:
            raise ValueError("model-only protocol changed during execution")
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
