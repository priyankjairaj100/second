# V38 execution checkpoint

Updated 9 October 2026.
This file supersedes earlier execution-status notes.
Actual registrations, receipts, ledgers, and published analyses remain authoritative.

The local workspace was removed during maintenance.
We restored the full repository from published commit `42d842f758e7bc6935215cf88c9235ea14cc9987`.
We also restored and verified the pinned DistilGPT2 checkpoint.
Read `validation/checkpoint_recovery_v38.json` for its hashes.
All previous manifest entries verified, except the intentionally updated `.gitignore`.
No historical numerical file or ledger changed.

## Fresh C4 execution

The local runtime lacks `/proc/self/maps` and `/proc/cpuinfo`.
The original backend requires those real interfaces.
V38 therefore prepares a fresh campaign on a standard public GitHub Linux runner.
The workflow uses the unchanged numerical backend.
It does not invent runtime facts or reuse historical runtime identities.

Read `CI_C4_PROTOCOL_V38.md` before executing anything.
The workflow is `.github/workflows/c4-v38.yml`.
Its one-use trigger is `.github/ci/c4-v38-trigger.json`.
The wrapper is `scripts/execute_ci_c4_v38.py`.
Its evidence prefix is `campaigns/ci_v38`.

The first publication was `1cf45ff1861b7e347bcef6308b3eddbb1e5e6534`.
GitHub rejected its YAML before allocating any job.
The dependency command contained an unquoted colon followed by a space.
Read `validation/workflow_yaml_rejection_v38.json` for the preserved platform evidence.
The syntax amendment uses a block scalar without changing the command.
The amended trigger requests the first actual runner execution.
No claim, bootstrap, ledger, or model worker existed in the rejected run.
This correction repeats no registered empirical attempt.
Check GitHub Actions and the evidence prefix for subsequent activity.
Do not interpret this preregistration note as evidence of success.

The job publishes a durable claim before downloading dependencies.
It constructs a fresh target identity using the actual Linux runtime.
That bounded construction performs no neural inference or quantization.
The bootstrap has a separate 122-second CPU allowance.
The seven C4 trials retain their separate 1,900-second CPU allowance.
Allowances are not observed usage.

The workflow accepts the published WikiText analysis as a disclosed development prerequisite.
It verifies all 699 bound evidence files.
It does not rerun WikiText or reverify its missing historical binaries.
Every C4 trial uses fresh preparation and the same newly bound target.
Actual binary audits occur before the temporary runner ends.
GitHub receives text evidence, source snapshots, receipts, and binary hashes.

The job publishes each settled trial before starting the next trial.
No failed attempt receives an automatic retry.
A scientific latency loss does not suppress later registered trials.
An execution or integrity failure stops dependent work.
Never push unrelated changes while the workflow runs.
Its publication guard requires an unchanged remote parent.
Never use GitHub's rerun button for this job.

## Portable runtime implementation

V38 also adds an explicit portable backend under `research_v38`.
It obtains live library, CPU, floating-control, and dependency evidence.
It creates new evaluator identities.
It cannot continue a historical prepared state under its old identity.
Read `LIVE_RUNTIME_COLLECTOR_V38.md` and `PORTABLE_BACKEND_V38.md`.
Read `RUNTIME_REVIEW_V38.md` for the independent review and remaining gate.

Local software fixtures passed for the collector and backend.
An earlier concurrent source-change refusal remains disclosed.
The hosted job can compare both collectors against genuine Linux interfaces.
A successful metadata comparison alone does not prove empirical speed or model compatibility.
C4 continues to use the original backend.

## Scientific status

The direction remains worth bounded investigation.
The full paper remains incomplete.
No V38 empirical result exists at this amended preregistration checkpoint.

The complete WikiText model matched all 42,467,328 codes across 24 stages.
Two lossless repair ratios were 1.8685 and 1.7883 versus cold reconstruction.
Those measurements use one small model and two alternative deletions.
One cold result required a disclosed, reviewed recovery.

V37 strengthened the complete first-stage Gram control.
All three arms matched 1,769,472 codes using the same native row kernel.
Pooled-Gram deletion took 17.724627 seconds.
Cached-feature reconstruction took 1.216621 seconds.
The 14.5687 ratio describes one exposed, low-token development request.
It does not establish a complete-model or large-token Gram ranking.

Compressed repair still trades latency for modest storage savings.
It has not defeated the lossless cache on latency.
The original sequential target still lacks a demonstrated complete-model speed advantage.
The positive target uses fixed nearest-anchor features.
No result establishes pretraining erasure or unconditional wall-time speedup.

Next priorities remain larger real workloads, complete service controls, successive deletions, another model, and prospective confirmation.
The closest-work comparison and final claim audit also remain open.
Read `RESEARCH_DECISION_V37.md` and `handoff/program_v38.json`.
