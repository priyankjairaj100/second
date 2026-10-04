# Complete transaction timing with an external observer

Revision 8 supplies an executable measurement boundary.
It does not supply empirical timing results.
Research remains paused.

## What the clock includes

`src/transaction_timing.py` starts a clock in the observer process.
It then verifies pinned sources and declared input hashes.
It launches the requested local CLI in a fresh limited process.
That CLI completes its own source checks, work, artifact writes, and final controller receipt.
The observer waits for exit and descendant cleanup.
It verifies the root transaction receipt and its declared artifacts.
It hashes the complete output tree and worker diagnostics.
It rechecks pinned sources and inputs.
Only then does it stop the clock.

The exact boundary label is:

`observer_source_validation_through_child_exit_controller_commits_cleanup_and_output_validation`

The enclosing interval includes worker outcome commits and lock release.
It therefore includes costs missing from the older worker elapsed field.
That older field retains its previous meaning for compatibility.

The observer writes its final timing receipt after the stop timestamp.
Those final observer writes and observer lock release are explicitly excluded.
Observer bootstrap, manifest parsing, and an existing-receipt lookup also precede the measured interval.
The reported quantity is a declared local transaction boundary.
It is not total physical latency from an external user's request.

## Disjoint accounting

The receipt partitions its enclosing interval into these spans:

1. Observer preflight.
2. Worker preparation before the older elapsed boundary.
3. Worker execution and ordinary process-group cleanup.
4. Worker finalization, commits, and adopted-descendant cleanup.
5. Observer postflight and output verification.

Their boundaries are ordered integers from the same observer monotonic clock.
Their durations sum exactly to `observed_wall_ns`.
Adjacent intervals share an endpoint and never overlap.
The worker execution span equals the existing `elapsed_wall_ns` exactly.
Do not add that nested elapsed field to the enclosing total.
Internal model or service timers remain nested diagnostic quantities.

If a worker fails before publishing its boundaries, its enclosing call remains one explicitly unpartitioned span.
Incomplete observations still retain disjoint elapsed accounting.
They never receive a successful complete-transaction latency.

## Distinguish output contracts

Every measured manifest declares an output contract.
The receipt binds that contract and the exact command.

| Contract | Meaning | Suitable interpretation |
| --- | --- | --- |
| `model_only` | Complete sequential requantization with target codes only | Plain fresh-model construction |
| `canonical_state` | One method returns the exact model and canonical deletion state | A complete repair or full-state construction transaction |
| `comparison` | Setup, all comparison arms, and shared research verification | Whole experimental comparison cost |
| `sequence` | A declared sequence of transactions and its executor outputs | Sequence execution cost |

A whole comparison clock includes setup and all its method arms.
It cannot become a per-method latency by dividing or allocating shared costs arbitrarily.
A model-only fresh baseline does not construct a deletion index.
Its output contract differs from full-state fresh construction.
Any cross-contract comparison must state that difference explicitly.
The wrapper itself computes no latency ratio.

Known receipt schemas establish the expected contract.
An isolated child supports `setup`, `repair`, `indexed_fresh`, and `direct_fresh` as canonical-state roles.
A quality-only isolated child is rejected as a canonical-state transaction.
An unknown, unlabeled child receipt has an unverified output contract.
Its elapsed time remains diagnostic and cannot become an eligible fresh transaction observation.

The observer validates structural completion, source bindings, and artifact bytes.
For a single role, it does not independently prove model equality against another method.
Run the exact oracle comparison separately and charge that research validation separately.
A whole comparison CLI includes its equality verification inside its broader measured boundary.

## Measure one method without shared research work

`build_role_measurement(request_path, limits)` wraps one supported isolated-child request.
Its command invokes `src.isolated_comparison --child` in a new process.
The child loads its own model, inputs, and original state where required.
It performs exactly one requested method and commits its complete output.
No other arm or shared oracle comparison runs in that transaction.

Use a new absolute output directory in the isolated-child request.
Keep its original-state reference and pinned manifest bindings unchanged.
Write the resulting request as canonical JSON.
Then build and save the measured manifest:

```python
from pathlib import Path
from src.transaction_timing import build_role_measurement
from src.run_store import canonical_json

measured = build_role_measurement(Path(request_path), limits)
Path(measured_manifest_path).write_bytes(canonical_json(measured))
```

Run the observer:

```bash
python scripts/run_measured.py /absolute/measured.json --receipt /absolute/timing-receipt
```

The helper binds the request, run manifest, and protocol by hash.
It derives a phase budget for every non-software request.
The child independently checks its frozen sources and inventory requirements.
Existing completed child outputs cannot be relabeled as a new fresh transaction.

The model-only CLI uses the same observer with `output_contract="model_only"`.
For admitted research, its exact command must have this argument order:

```text
ABSOLUTE_PYTHON ABSOLUTE_REPOSITORY/scripts/run_model_fresh.py ABSOLUTE_MANIFEST --output ABSOLUTE_OUTPUT
```

Absolute paths and literal arguments bind the admitted command.
No shell processes or remote jobs are introduced by the observer.

## Fresh, resumed, and reused work

`fresh_transaction_os_cache_uncontrolled` requires an absent transaction output directory.
Even an empty preexisting directory causes rejection.
The observer starts a new child process.
It makes no claim about operating-system caches.

`resumed_transaction_os_cache_uncontrolled` requires existing transaction output.
The observer records a hash snapshot before execution.
Its clock measures only the work performed during that resumed invocation.
It is never an eligible fresh transaction latency.
A child may independently reject resuming a previously sealed output.

A repeated completed observer call returns a verified archival receipt.
It sets `reused_receipt=true` and `new_latency_observation=false`.
It does not launch the command or fabricate a new elapsed value.
The stored original observation remains attached to its original attempt.
Reusing it in multiple independent repetitions is invalid.

A fresh attempt interrupted after producing partial outputs cannot resume under the fresh label.
Create an explicitly resumed observation or choose a new independent output directory.
Missing completion, nonzero exit, interruption, and invalid output all yield an incomplete observation.
For these cases, `complete_transaction_wall_ns` is null.
An abrupt observer death can leave only a running receipt.
Such a receipt is incomplete and contains no admissible completed latency.

## Phase CPU admission

The measured manifest has a `budget` field.
Use null when the invoked complete executor already owns the relevant worker admissions.
Otherwise specify `protocol_path`, `protocol_sha256`, and `phase`.
The wrapper uses the same protocol/source-bound `PhaseBudget` identity as other executors.
It reserves an allowance before launching the measured child.
It settles observed child CPU usage through the existing worker controller.

`run_limited` exports `CALIBRATION_PHASE_CPU_ADMISSION` only after successful reservation.
It removes any inherited admission before launching a different worker.
The descriptor binds a live allowance, exact command, phase, and ledger identity.
`verify_command_admission` checks that descriptor against the trusted local ledger.
`verify_phase_admission` additionally fixes the model-only CLI argument structure.

Non-software model-only and direct isolated-child paths require active exact-command admission before loading model parameters.
The role helper derives its admission from the hash-bound protocol.
A manual unbudgeted measured command does not bypass the child's admission check.
The pause and frozen-inventory requirements remain independent execution gates.
Model-only standalone confirmation remains blocked until its inventory path exists.

Wrapping an already budgeted comparison with another admission can double-charge nested CPU usage.
The receipt states this possibility explicitly.
Do not interpret overlapping ledger charges as independent CPU work.
Observer CPU and final observer receipt costs are outside the child allowance.
They remain part of the stated wall boundary where applicable.
Adopted-descendant resource observations are reported separately.
No process-tree CPU containment guarantee is claimed.

These descriptors establish trusted-local consistency.
They do not authenticate hostile code, hostile storage, or a malicious environment.

## Nested worker cleanup

An isolated comparison can create inner workers in separate process sessions.
Ordinary cleanup of the outer process group cannot stop those sessions after an outer timeout.
The observer therefore temporarily enables Linux child-subreaper behavior.
It requires one observer thread and no preexisting child processes.
These restrictions prevent adopting unrelated concurrent work.

After the main child exits, orphan descendants become observer children.
The observer kills and reaps those descendants before stopping its clock.
It records their observed resource usage separately.
It restores the prior subreaper setting afterward.
Cleanup has a finite deadline.
A failure to complete cleanup marks the transaction incomplete.
This controls trusted local executor descendants, not adversarial process behavior.

## Manifest and API

`measured-transaction-v1` contains exactly these fields:

- `schema`
- `command`
- `transaction_root`
- `cwd`
- `cache_mode`
- `output_contract`
- `limits`
- `source_sha256`
- `input_sha256`
- `budget`
- `identity`

Manifest paths and command executable paths must be absolute.
The transaction and observer directory trees must be disjoint.
All bound inputs, outputs, and sources must avoid symlinks.
The observer verifies recorded output and worker trees again before returning a saved receipt.

Public entry points are `measure_command`, `run_measured_manifest`, and `build_role_measurement`.
`transaction_source_hashes` covers Python source and CLI scripts.
`accounting_partition` verifies the exact no-overlap timing identity.

## Correctness evidence and remaining scope

The dedicated tests cover enclosing commits, cleanup, accounting, immutable reuse, source binding, output contracts, and interrupted transactions.
They also cover separate-session descendant cleanup, admission consistency, and phase-budget settlement.
Existing worker tests still pass with their original elapsed semantics.
All tests are software fixtures rather than empirical timing studies.
The dedicated module has 14 passing correctness tests.
All seven existing worker-control tests also pass.
Independent review additionally checks missing admission before model loading, changed resume inputs, and invalid quality-role labels.
The reviewer found no further blocker under the declared trusted-local scope.

This implementation closes the declared complete local transaction boundary at its stated scope.
Real artifacts, executed schedules, resource feasibility, precision, and useful latency remain separate empirical requirements.
D04 remains open for complete-clock integration into primary campaign and lifetime analysis.
D05 separately covers arithmetic-size diagnostics.
C05 separately covers unavailable numerical rejection details.
