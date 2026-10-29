"""Reduce actual V89 terminal-bound metadata without running a model or job."""
from pathlib import Path
import hashlib
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reporting_v93.cost_scope import CELLS, comparisons, phase_partition
from research_v90.recovery_gate import validate


def identity(blob):
    return {"bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()}


def main(terminal_path, receipts_path, output_path):
    terminal_raw = Path(terminal_path).read_bytes()
    terminal = json.loads(terminal_raw)
    receipts = Path(receipts_path)
    retrieval = json.loads((receipts / "retrieval.json").read_bytes())
    assert retrieval["terminal_sha256"] == identity(terminal_raw)["sha256"]
    root = retrieval["root"]
    inputs = {}

    def read(name):
        raw = (receipts / name).read_bytes()
        expected = terminal["inputs"][root + name]
        assert identity(raw) == expected == retrieval["files"][root + name]
        inputs[name] = expected
        return json.loads(raw)

    primary = read("primary-audit.json")
    supplemental = read("supplemental-audit.json")
    program = read("program.json")
    gate = validate(terminal, primary, supplemental, program)
    rows = {}
    for cell in CELLS:
        for step in (1, 2):
            trial = f"{cell}-{step}"
            completion = read(trial + "/outputs/completion.json")
            host = read(trial + "-host.json")
            request = completion["request"]
            timing = primary["costs"]["timings"][cell]["requests"][step - 1]
            storage = primary["evidence"]["storage"][cell][step - 1]
            assert host["status"] == completion["status"] == "complete"
            assert host["elapsed_ns"] == timing["host_transaction_elapsed_ns"]
            assert request["request_elapsed_ns"] == timing["request_elapsed_ns"]
            assert request["live_state_bytes"] == storage["live_state_bytes"]
            assert len(request["retained_ids"]) == program["retained_counts"][step - 1]
            assert completion["slurm_job_id"] == terminal["costs"][trial]["job_id"]
            phases = phase_partition(host["elapsed_ns"], request, 24)
            assert sum(phases["disjoint_host_partition_ns"].values()) == host["elapsed_ns"]
            rows[cell, step] = dict(
                cell=cell, step=step, retained_records=len(request["retained_ids"]),
                job_id=completion["slurm_job_id"], host_elapsed_ns=host["elapsed_ns"],
                request_elapsed_ns=request["request_elapsed_ns"],
                max_rss_kib=completion["max_rss_kib"], **storage, **phases)
    result = dict(
        schema="v89-complete-screen-reduction-v98", status="verified_saved_scalar_reduction",
        actual_terminal=identity(terminal_raw), recovered_gate=gate, inputs=inputs,
        rows=list(rows.values()), comparisons=comparisons(rows),
        numerical_charged_cpu_seconds=primary["budget"]["charged_cpu_seconds"],
        old_unknown_cpu_seconds=12602,
        scheduler_cpu_lower_ns=sum(r["scheduler_cpu_ns"] for r in terminal["costs"].values()),
        scheduler_cpu_upper_ns=sum(r["scheduler_cpu_ns"] + r["scheduler_reporting_quantum_ns"]
                                   for r in terminal["costs"].values()),
        numerical_controller_upper_ns=sum(terminal["costs"][name]["nonnumerical_upper_cpu_ns"]
                                          for name in program["trial_order"]),
        attributed_lifetime={cell: {k: primary["costs"]["timings"][cell][k]
                                  for k in ("attributed_preparation_ns", "attributed_two_request_total_ns", "lifetime_scope")}
                             for cell in CELLS},
        single_observation_per_cell=True, os_cache_uncontrolled=True,
        stable_latency_established=False, transfer=False, new_quality_evaluation=False,
        individual_optimization_effect_identified=False, decoder_only_time_available=False,
        no_numerical_execution=True)
    with Path(output_path).open("x") as stream:
        json.dump(result, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
    for row in result["rows"]:
        print(row["cell"], row["step"], "host_s", round(row["host_elapsed_ns"] / 1e9, 6),
              "live_bytes", row["live_state_bytes"], "rss_kib", row["max_rss_kib"])
    for comparison in result["comparisons"]:
        print(json.dumps(comparison, sort_keys=True))
    print("scheduler_cpu_seconds", result["scheduler_cpu_lower_ns"] / 1e9,
          result["scheduler_cpu_upper_ns"] / 1e9)


if __name__ == "__main__":
    main(*sys.argv[1:])
