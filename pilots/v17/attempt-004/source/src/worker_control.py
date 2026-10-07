"""Bound local POSIX workers without a shell or remote execution.

Each control record seals the observed outcome, including worker failures.
Process groups provide cleanup, not containment for hostile child programs.
"""
from __future__ import annotations

from dataclasses import dataclass
import argparse
import json
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import tempfile
import time

from .run_store import RunStore, atomic_write, canonical_json, digest, strict_json
from .phase_budget import BudgetExhausted, PhaseBudget

THREAD_VARIABLES = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                    "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
                    "RAYON_NUM_THREADS")


@dataclass(frozen=True)
class WorkerLimits:
    wall_seconds: int
    cpu_seconds: int
    address_space_bytes: int
    threads: int
    affinity_cpus: tuple[int, ...]
    termination_grace_seconds: int = 1
    file_size_bytes: int = 512 * 1024 * 1024

    def __post_init__(self):
        for name in ("wall_seconds", "cpu_seconds", "address_space_bytes", "threads", "file_size_bytes"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} requires a positive integer")
        if type(self.termination_grace_seconds) is not int or not 0 <= self.termination_grace_seconds <= 10:
            raise ValueError("termination grace must be an integer between zero and ten")
        cpus = self.affinity_cpus
        if not isinstance(cpus, tuple) or not cpus or any(type(x) is not int or x < 0 for x in cpus):
            raise ValueError("affinity requires a nonempty tuple of CPU integers")
        if tuple(sorted(set(cpus))) != cpus:
            raise ValueError("affinity CPUs must be sorted and unique")

    def payload(self):
        return {name: list(value) if name == "affinity_cpus" else value
                for name, value in self.__dict__.items()}

    @classmethod
    def from_payload(cls, value):
        fields = set(cls.__dataclass_fields__)
        if not isinstance(value, dict) or set(value) != fields:
            raise ValueError("invalid worker limit fields")
        if not isinstance(value["affinity_cpus"], list):
            raise ValueError("affinity_cpus must be a JSON list")
        return cls(**dict(value, affinity_cpus=tuple(value["affinity_cpus"])))

    def check_host(self):
        if os.name != "posix" or not hasattr(os, "sched_setaffinity"):
            raise RuntimeError("worker limits require POSIX resource limits and Linux CPU affinity")
        if not set(self.affinity_cpus) <= set(os.sched_getaffinity(0)):
            raise ValueError("requested CPU affinity is unavailable in this process")
        for key, hard in ((resource.RLIMIT_AS, self.address_space_bytes),
                          (resource.RLIMIT_CPU, self.cpu_seconds + 1),
                          (resource.RLIMIT_FSIZE, self.file_size_bytes)):
            inherited = resource.getrlimit(key)[1]
            if inherited != resource.RLIM_INFINITY and hard > inherited:
                raise ValueError("requested resource limit exceeds an inherited hard limit")


def _apply_limits(limits):
    limits.check_host()
    resource.setrlimit(resource.RLIMIT_AS, (limits.address_space_bytes, limits.address_space_bytes))
    resource.setrlimit(resource.RLIMIT_CPU, (limits.cpu_seconds, limits.cpu_seconds + 1))
    resource.setrlimit(resource.RLIMIT_FSIZE, (limits.file_size_bytes, limits.file_size_bytes))
    os.sched_setaffinity(0, set(limits.affinity_cpus))
    return {"address_space": list(resource.getrlimit(resource.RLIMIT_AS)),
            "cpu_seconds": list(resource.getrlimit(resource.RLIMIT_CPU)),
            "file_size": list(resource.getrlimit(resource.RLIMIT_FSIZE)),
            "affinity_cpus": sorted(os.sched_getaffinity(0)),
            "thread_environment": {name: os.environ.get(name) for name in THREAD_VARIABLES},
            "pid": os.getpid(), "process_group": os.getpgrp()}


def _group_signal(pid, signum):
    try:
        os.killpg(pid, signum)
    except ProcessLookupError:
        pass


def _wait_worker(process, timeout=None):
    """Reap with wait4 exactly once. Avoid Popen.wait losing rusage."""
    if process.returncode is not None:
        return process.returncode
    deadline = None if timeout is None else time.monotonic() + timeout
    while True:
        pid, status, usage = os.wait4(process.pid, os.WNOHANG)
        if pid:
            process.returncode = os.waitstatus_to_exitcode(status)
            # Round each reported component upward. This is observed accounting,
            # not a containment guarantee for untrusted child process trees.
            process.worker_rusage = {
                "user_cpu_ns": math.ceil(usage.ru_utime * 1_000_000_000),
                "system_cpu_ns": math.ceil(usage.ru_stime * 1_000_000_000),
                "max_rss_kib": usage.ru_maxrss,
                "scope": "wait4_reaped_worker_including_waited_for_descendants_as_reported_by_os"}
            process.worker_rusage["total_cpu_ns"] = (process.worker_rusage["user_cpu_ns"] +
                                                    process.worker_rusage["system_cpu_ns"])
            return process.returncode
        if deadline is not None and time.monotonic() >= deadline:
            raise subprocess.TimeoutExpired(process.args, timeout)
        time.sleep(0.01)


def _cleanup(process, grace):
    """Stop ordinary descendants, then reap the direct child."""
    if process.returncode is None:
        _group_signal(process.pid, signal.SIGTERM)
        try:
            _wait_worker(process, timeout=grace)
        except subprocess.TimeoutExpired:
            pass
    _group_signal(process.pid, signal.SIGKILL)
    _wait_worker(process)


def _log_summary(stream):
    stream.flush()
    stream.seek(0)
    from hashlib import sha256
    h = sha256()
    length = 0
    tail = b""
    while chunk := stream.read(65536):
        length += len(chunk)
        h.update(chunk)
        tail = (tail + chunk)[-32768:]
    return {"bytes": length, "sha256": h.hexdigest(),
            "tail_utf8": tail.decode("utf-8", errors="replace"), "tail_max_bytes": 32768}


def run_limited(command, directory, limits: WorkerLimits, *, identity, cwd=None,
                phase_budget: PhaseBudget | None = None, phase=None):
    """Execute once and preserve terminal outcomes, including killed workers."""
    if not isinstance(command, (list, tuple)) or not command:
        raise ValueError("command must be a nonempty argument sequence")
    if any(type(x) is not str or not x or "\0" in x for x in command):
        raise ValueError("command arguments must be nonempty strings")
    if not Path(command[0]).is_absolute():
        raise ValueError("the executable must have an absolute local path")
    limits.check_host()
    work = Path(cwd or Path.cwd()).absolute()
    if not work.is_dir() or work.is_symlink() or any(p.is_symlink() for p in work.parents):
        raise ValueError("worker directory must be a regular local directory")
    binding = {"schema": "limited-worker-identity-v1", "identity": identity,
               "command": list(command), "cwd": str(work), "limits": limits.payload()}
    if phase_budget is not None:
        if type(phase) is not str or phase not in phase_budget.caps:
            raise ValueError("worker requires a declared budget phase")
        binding["phase_budget"] = {"binding_sha256": phase_budget.identity_digest, "phase": phase,
                                   "directory": str(phase_budget.root)}
    elif phase is not None:
        raise ValueError("a budget phase requires a phase budget")
    store = RunStore(directory, binding)
    previous = store.completed()
    if previous is not None:
        if phase_budget is not None and previous.get("budget_attempt_id") is not None:
            saved = phase_budget.snapshot()["attempts"].get(previous["budget_attempt_id"])
            if saved != previous.get("budget_debit"):
                raise ValueError("completed worker budget debit differs from the ledger")
        return previous
    store.claim()
    process = None
    caught = None
    budget_attempt = None
    started = time.perf_counter_ns()
    outcome = {"status": "failed", "kind": "launch_failed"}
    record = {"schema": "limited-worker-record-v1", "status": "running", "outcome": outcome,
              "limits": limits.payload(), "worker_identity": identity,
              "execution": "isolated_process_os_cache_uncontrolled", "no_shell": True,
              "limit_scope": "address space and CPU per process; wall limit and cleanup for ordinary process-group descendants",
              "memory_scope": "RLIMIT_AS limits virtual address space, not physical RSS",
              "thread_scope": "library thread environment requests; CPU affinity also applies"}
    try:
        request = {"command": list(command), "cwd": str(work), "limits": limits.payload(),
                   "ack_path": str(store.attempt / "limits-ack.pending.json")}
        store.write_artifact("request.json", canonical_json(request))
        environment = os.environ.copy()
        # Never pass an ancestor's allowance as this worker's own admission.
        environment.pop('CALIBRATION_PHASE_CPU_ADMISSION', None)
        environment.update({name: str(limits.threads) for name in THREAD_VARIABLES})
        environment["PYTHONHASHSEED"] = "0"
        # Module discovery uses the repository root. This does not modify checkpoint execution policy.
        repository = Path(__file__).resolve().parents[1]
        environment["PYTHONPATH"] = str(repository)
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            try:
                if phase_budget is not None:
                    proposed_attempt = digest(canonical_json({"worker": binding, "attempt": str(store.attempt)}))
                    # RLIMIT_CPU hard allowance plus one conservative second.
                    # Kernel overshoot is observable, never silently truncated.
                    debit = phase_budget.reserve(phase, proposed_attempt, limits.cpu_seconds + 2)
                    budget_attempt = proposed_attempt
                    record.update(budget_attempt_id=budget_attempt, budget_debit=debit,
                                  budget_scope="CPU admission allowance; trusted comparison worker; controller CPU excluded")
                    environment['CALIBRATION_PHASE_CPU_ADMISSION'] = canonical_json({
                        'phase_budget_root': str(phase_budget.root),
                        'phase_budget_binding_sha256': phase_budget.identity_digest,
                        'attempt_id': budget_attempt, 'phase': phase,
                        'command': list(command), 'cwd': str(work)}).decode('ascii')
                process = subprocess.Popen(
                    [sys.executable, "-m", "src.worker_control", "--child", str(store.attempt / "request.json")],
                    cwd=repository, env=environment, stdin=subprocess.DEVNULL,
                    stdout=stdout, stderr=stderr, start_new_session=True)
                record["worker_pid"] = process.pid
                store.write_status(record)
                try:
                    returncode = _wait_worker(process, timeout=limits.wall_seconds)
                    outcome = {"status": "complete" if returncode == 0 else "failed",
                               "kind": "exited" if returncode == 0 else "nonzero_exit", "returncode": returncode}
                    if returncode < 0:
                        signum = -returncode
                        kind = ("cpu_limit" if signum == signal.SIGXCPU else
                                "file_size_limit" if signum == signal.SIGXFSZ else "killed_unknown")
                        outcome.update(kind=kind, signal=signum)
                except subprocess.TimeoutExpired:
                    outcome = {"status": "failed", "kind": "wall_timeout"}
            except BaseException as exc:
                caught = exc
                outcome = {"status": "failed", "kind": "phase_cpu_budget_exhausted" if isinstance(exc, BudgetExhausted) else
                           "interrupted" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else "launch_failed",
                           "type": type(exc).__name__, "message": str(exc)}
            finally:
                cleanup_start = time.perf_counter_ns()
                if process is not None:
                    _cleanup(process, limits.termination_grace_seconds)
                cleanup_end = time.perf_counter_ns()
                outcome["elapsed_wall_ns"] = cleanup_end - started
                # Same-process monotonic coordinates allow an enclosing observer
                # to partition controller overhead without adding nested times.
                record["timing_boundary"] = {
                    "clock": "time.perf_counter_ns_same_controller_process",
                    "start_ns": started, "cleanup_start_ns": cleanup_start, "cleanup_end_ns": cleanup_end,
                    "excluded_tail": "CPU settlement, log summaries, acknowledgment validation, receipt commit and store close"}
                if process is not None:
                    outcome["returncode"] = process.returncode
                    record["resource_usage"] = getattr(process, "worker_rusage", None)
                    if budget_attempt is not None and record["resource_usage"] is not None:
                        record["budget_debit"] = phase_budget.settle(budget_attempt, record["resource_usage"]["total_cpu_ns"])
                        record["budget_reservation_overrun"] = (record["budget_debit"]["charged_cpu_seconds"] >
                                                                record["budget_debit"]["reserved_cpu_seconds"])
                store.write_artifact("stdout-summary.json", canonical_json(_log_summary(stdout)))
                store.write_artifact("stderr-summary.json", canonical_json(_log_summary(stderr)))
        ack = store.attempt / "limits-ack.pending.json"
        record["limits_applied"] = None
        try:
            if ack.is_symlink() or not ack.is_file() or ack.stat().st_size > 65536:
                raise ValueError("limits acknowledgment is missing or invalid")
            raw = ack.read_bytes()
            limits_applied = strict_json(raw)
            expected = {"address_space": [limits.address_space_bytes] * 2,
                        "cpu_seconds": [limits.cpu_seconds, limits.cpu_seconds + 1],
                        "file_size": [limits.file_size_bytes] * 2,
                        "affinity_cpus": list(limits.affinity_cpus),
                        "thread_environment": {name: str(limits.threads) for name in THREAD_VARIABLES},
                        "pid": process.pid if process else None,
                        "process_group": process.pid if process else None,
                        "request_sha256": digest(canonical_json(request))}
            if limits_applied != expected:
                raise ValueError("limits acknowledgment does not match the worker request")
            store.write_artifact("limits-applied.json", raw)
            ack.unlink()
            record["limits_applied"] = limits_applied
        except (ValueError, OSError, TypeError) as exc:
            record["limits_ack_failure"] = {"type": type(exc).__name__, "message": str(exc)}
            if outcome["status"] == "complete":
                outcome.update(status="failed", kind="limits_ack_invalid")
        record.update(status="complete", outcome=outcome,
                      controller_completion_means="the outcome is sealed; inspect outcome.status for worker success")
        complete = store.finish(record)
        if caught is not None and isinstance(caught, (KeyboardInterrupt, SystemExit)):
            raise caught
        return complete
    finally:
        if process is not None and process.returncode is None:
            _cleanup(process, limits.termination_grace_seconds)
        store.close()


def _child(path):
    raw = Path(path).read_bytes()
    request = strict_json(raw)
    if not isinstance(request, dict) or set(request) != {"command", "cwd", "limits", "ack_path"}:
        raise ValueError("invalid worker request")
    applied = _apply_limits(WorkerLimits.from_payload(request["limits"]))
    applied["request_sha256"] = digest(raw)
    atomic_write(Path(request["ack_path"]), canonical_json(applied))
    os.chdir(request["cwd"])
    os.execvpe(request["command"][0], request["command"], os.environ)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child", type=Path, required=True)
    args = parser.parse_args()
    _child(args.child)


if __name__ == "__main__":
    main()
