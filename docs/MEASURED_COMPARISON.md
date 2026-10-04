# Complete matched single-request transactions (v9)

This is an execution and evidence contract, not an empirical result. Research remains subject to the frozen protocol's pause guard and phase CPU allowances. The tests use tiny correctness fixtures and establish neither model-scale feasibility nor a speedup.

## Four distinct output contracts

`src/measured_comparison.py` executes each planned method in a fresh limited Python process, in the frozen four-arm order. Every leaf has the same enclosing `transaction_timing.BOUNDARY`:

- `model_only_fresh`: retained-corpus sequential quantization returning only the common target binding and exact stage codes. It builds no deletion index and is the plain requantization control.
- `repair`: loads the original canonical state, applies the deletion, and returns the exact retained model and canonical deletion state.
- `indexed_fresh`: updates the index, then reconstructs the retained model from the index; returns the same canonical output contract.
- `direct_fresh`: reconstructs the retained model and deletion state from the original input filtered by deletion. It does not read the original state. This is the within-family full-state oracle, not the plain requantization comparator.

The initial canonical `setup` transaction is separate. Optional heldout evaluation is a separate `quality_evaluation` transaction. A failed setup leaves repair and indexed reconstruction unavailable, but still permits the two independent fresh baselines to attempt their own resource-limited work. All four planned outcomes remain in the result.

All arms currently parse the original calibration input before filtering deleted records. This contract does not claim an optimal retained-only reader. Non-quality state arms omit heldout token loading. Model and input validation necessary for the declared transaction remains charged.

## Timing and instrumentation

Each arm's observer includes source/input validation, worker preparation and admission, process startup, target/input loading, its complete method, model/state serialization and commits, child controller receipt, exit, worker cleanup, worker accounting and receipt, and observer output/source validation. Disjoint spans sum exactly to its enclosing wall time. The observer runs in a clean instrumentation scope when the plan says `execution_mode="clean"`; its entry and exit markers are retained. Every child records the same frozen mode and instrumentation facts.

Clean mode disables optional service telemetry, Python allocation tracing, Python profile/trace hooks, and the optional canonical-state integer-size scan. Required exact arithmetic counters, validation, hashing and durable output remain charged. Native profiling is explicitly unobserved; OS caches and machine load are uncontrolled. A fresh process is not a cold-cache claim. Diagnostic execution remains separately labeled and cannot support a clean timing estimate.

The observer's final tree-snapshot files and receipt write necessarily follow the stop timestamp and are excluded. Plan validation, original setup, cross-method equality, common-model comparison copies, quality, and the parent comparison's receipts are outside every method clock and are reported separately. There is no physical end-to-end latency claim beyond this explicit boundary. The parent comparison wall time must not be divided into a per-method speed ratio.

Phase CPU admission reserves and settles the complete child process allowance, including child commits, through the shared protocol-bound ledger. The enclosing observer's CPU is not debited to that child allowance. The measurement records this scope explicitly. A software correctness fixture may omit the shared phase budget when the protocol declares no software cap; research leaves require admission. This is trusted-local consistency checking, not hostile authorization.

## Exactness and failures

The common comparison encoding binds `target_manifest_sha256` and every exact rational stage code. The two model encodings are normalized outside the production clock. A successful comparison requires all four common model byte strings to agree with both independent fresh controls. Canonical state byte equality, service manifest equality, and chart equality apply to repair, indexed fresh, and direct fresh only. Model-only state equality is `null`, never asserted.

A successful timer alone is insufficient. An invalid target, malformed output, missing oracle, unequal state, nonzero exit, timeout, denied allowance, or unfinished observer remains failed or unverified. Observed time is retained even when no complete eligible time exists. The complete outer controller receipt seals the planned outcomes: inspect `outcome.status`, not merely top-level `status="complete"`.

`invoke_role` deliberately returns `pending_verification` for successful method transactions. A comparison or sequence controller must derive its own exactness from artifacts before marking them complete. `verify_role` rederives immutable transaction facts while allowing the caller to own the cross-arm equality decision.

## Frozen inputs and resumption

`build_measured_plan` freezes the normalized run manifest, target, every `src/*.py` and `scripts/*.py` digest, worker limits, four-arm order, instrumentation mode, and quality policy. Actual manifest/protocol bytes and inventory evidence enter the role request and observer binding. Research confirmation requires real frozen inventory membership; a copied run ID is insufficient. The measured inventory separately pins the runtime contract.

The public runner is:

```text
python scripts/run_measured_comparison.py PLAN.json --output RESULTS
python scripts/run_measured_comparison.py PLAN.json --output RESULTS --validate-only
```

Confirmation additionally supplies `--inventory INVENTORY.json --inventory-run-id ID`.

Completed observers are immutable observations. Resumption verifies the original observer, worker diagnostics, child output tree, source/input bindings, and CPU ledger debit, then reuses the original time. It never times only a cache hit and presents that as a new full transaction. A child output with no complete observer receipt is not promoted into a short success. The observer's fresh mode refuses preexisting transaction output. A parent restart can still finish other planned methods while retaining the original already-sealed observations.

`verify_measured_archive(ROOT, result=None)` (aliases `verify_measured_comparison` and `verify_measured_comparison_archive`) is read-only. It verifies saved input bindings, committed comparison bytes, role receipts, auxiliary output-tree snapshots, exactness, and parent convenience fields. Interrupted parent records retain a partial tree snapshot and any completed original observations; verification never launches replacement work or invents a time. These hashes detect changes in a trusted local archive; they do not authenticate storage against an adversary able to rewrite every record and hash.

## Interfaces and analysis

The result schema is `calibration-measured-comparison-v1`. Its cache label is `measured_method_transactions_os_cache_uncontrolled`. Per-role references use absolute paths with SHA-256 digests. A role carries the original observer identity and attempt, observer and child receipt paths, exact output references, clocks, resource outcome, instrumentation mode, and equality applicability. The analysis loader independently reads those artifacts and must count one original observer only once across planned repetitions.

`invoke_role(checked, root, role, original_state=None, sequence_context=None, quality_states=None)` is shared by the measured lifetime controller. Cumulative deletion manifests and optional sequence evidence are bound before invocation. Independent fresh controls receive no preceding canonical state. The reusable role helper does not assert the sequence's lifetime equality or cost sum; those belong to its caller.

Validation: `tests/test_measured_comparison_v9.py` checks exact four-contract completion, separate diagnostic quality, budget failures preserving independent baselines, tamper rejection, interruption/resume retaining original times, and pause enforcement. The transaction timer's existing correctness tests continue to apply. No timing value from these fixtures is a research observation.

## Diagnostic decomposition extension

`diagnostic_breakdown.diagnostic_report` decomposes archived diagnostic transactions with the same original observer identity. It validates exclusive service durations against bounded root windows, verifies nonoverlapping loader/chart windows, separates proposal/exact quantization from certificate verification, and uses actual worker/observer cleanup coordinates. Serialization and durable artifact output now have separate explicit spans. The sum includes an explicit unclassified residual, never an estimated correction to clean time. See `DIAGNOSTIC_BREAKDOWN.md`; exhaustive named attribution remains partial whenever the residual or unavailable components persist.
