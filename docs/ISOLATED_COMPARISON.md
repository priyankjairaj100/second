# Separate-process comparison

Revision 7 provides an isolated executor for local prepared inputs.
It does not download data or resume paused research.
Correctness fixtures establish implementation behavior only.

## Execution contract

One limited setup process constructs and persists the complete original canonical state.
That process exits before the first method starts.
Three further limited processes run repair, indexed fresh, and direct fresh separately.
The plan declares their order.
Every worker reloads its checkpoint and prepared input manifests.
No Python model, service, activation, or allocator state passes between processes.

Repair and indexed fresh read the same persisted original state.
Direct fresh constructs its result from retained records without reading that state.
This avoids charging direct fresh for unnecessary index loading.
The reference remains the complete sequential finite target.
The executor supports the declared service family, response tier, and verifier policy.

Each method writes its complete model and canonical state.
It synchronizes those artifacts and seals its child receipt before exit.
The parent verifies artifact hashes and compares full state and model bytes against direct fresh.
Missing or failed direct output makes other outputs unverified failures.
Every planned method remains in the result.

The cache label is `isolated_method_processes_os_cache_uncontrolled`.
Operating-system caches remain uncontrolled.
Process separation does not establish disk-cold execution.

## Timing boundary

The primary method time comes from the enclosing limited worker's wall clock.
Its boundary is `limited_worker_startup_inputs_service_artifacts_child_commit_and_cleanup`.

The interval includes:

- Worker request preparation and CPU admission.
- Process startup and limit installation.
- Checkpoint, token, protocol, chart, and service loading.
- Original-state loading when the method requires it.
- Exactly one requested method.
- Model and state serialization, hashing, atomic writes, and synchronization.
- Child receipt synchronization, process exit, and cleanup.

The interval excludes parent source validation, parent equality verification, and final parent receipt commitment.
It also excludes post-cleanup CPU settlement, log summaries, and the enclosing worker-control receipt commitment.
These exclusions remain explicit in every result.
Therefore this is a complete declared worker boundary, not a complete parent-orchestrated transaction.
Setup has a separate measured worker cost.
No speed claim can omit setup from its relevant lifetime accounting.

Internal telemetry remains diagnostic.
Checkpoint loading uses the existing instrumented reference loader.
These timings do not establish production latency.
Linux `wait4` CPU and peak RSS accompany each worker observation.

The executor validates heldout inputs but does not compute NLP quality.
Quality evaluation remains a separate program requirement.

## Plans and source bindings

`build_isolated_plan` constructs schema `calibration-isolated-plan-v1`.
Its fields are:

| Field | Meaning |
| --- | --- |
| `manifest_path` | Local standard run manifest path |
| `manifest_payload` | Manifest with only `protocol.sha256` cleared |
| `manifest_binding_sha256` | Digest of that normalized payload |
| `target_manifest_sha256` | Expected complete target identity |
| `source_sha256` | Exact executable source bindings |
| `worker_limits` | Strict `WorkerLimits` payload |

The normalized manifest avoids a future protocol-plan digest cycle.
Runtime receipts also bind the final raw manifest and protocol hashes.
The expected target remains a declaration until setup verifies the constructed target.
Source and raw manifest checks run before dispatch and inside each worker.
Workers repeat these checks before successful commitment.

The CLI is:

```bash
python scripts/run_isolated.py isolated-plan.json --output isolated-results
```

Add `--validate-only` to inspect the plan without loading checkpoint parameters.
Validation still checks local metadata, source bindings, limits, and protocol references.

The protocol pause blocks research execution.
Software correctness fixtures remain allowed.
Confirmation execution fails closed until a supported frozen isolated campaign inventory exists.
Standalone development support does not close that confirmation gate.

## CPU admission

Setup and all three methods share the same protocol-scoped CPU ledger.
Each process requires its own reservation before launch.
The ledger charges setup separately from request methods.
Changing output directories cannot reset the same frozen protocol ledger.
Explicit research caps come from `resources.phase_cpu_hour_caps`.

The accounting scope matches `EXECUTION_BUDGETS.md`.
It limits admission allowances, not absolute physical CPU or hostile descendant trees.
Unknown attempts retain their reservation.
Observed overruns remain fully charged.
Controller CPU remains outside the worker ledger.

## Failure and restart

Worker outcomes remain immutable, including failures and budget denials.
The parent seals its result after all attainable outcomes terminate.
Top-level `status=complete` means the controller receipt is sealed.
Top-level `outcome` and individual method statuses determine scientific success.
The standard analysis code uses those method outcomes and exact-equality flags.

Parent interruption after a worker commits preserves its original observation.
Restart verifies and reuses that sealed worker receipt without another reservation.
Stable request paths keep the worker command identity unchanged across parent attempts.

Sometimes a child commits before the outer worker timing record becomes durable.
Such output cannot receive a new short successful timing through cached-child reuse.
The child refuses that restart path, and the comparison records a failure.
This conservative policy preserves the measurement boundary.

Resume checks successful and failed child receipts, their committed artifacts, and budget debits.
The external archive retains original and failed states.
No physical erasure or hostile-storage authentication claim follows.

## Validation scope

Tests check four distinct worker PIDs, complete output equality, and method-specific artifact sets.
They check pause and confirmation guards before output creation.
They also check budget denial, failed-child integrity, parent interruption, and missing outer timing.
Independent review checks direct-fresh state independence and lock cleanup after failed commitment.
