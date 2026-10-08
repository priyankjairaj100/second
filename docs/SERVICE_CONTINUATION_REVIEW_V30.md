# Service evidence adapter and continuation review

The completed preparation remains valid under the new evidence adapter.
The original controller rejected its artifact field names after the worker finished successfully.
The repair changes controller interpretation only.
It does not repeat preparation or change original evidence.

The independent review found one additional comparison-check gap.
The continuation now closes that gap.
No blocker remains within this review scope.

## Adapter checks

`src/service_terminal_evidence_v30.py` preserves every original verification step.
It verifies receipt bindings, settled CPU use, plan identity, and all receipt artifacts first.
It then checks the three terminal copies and the receipt-bound stdout commitment.

Only after those checks can it derive an artifact mapping.
The mapping uses the original `model_artifact` and `state_artifact` fields.
It accepts only the explicitly supported service schemas.
A derived model entry requires `complete_model=True`.
A complete state requires its valid state entry.
Every derived entry still passes filename, hash, and byte-count checks.

The adapter returns an augmented dictionary in memory.
It does not rewrite the original terminal bytes or their commitment.
Unknown schemas and incomplete models cannot use this adapter.

The real `prepare-128` record passes these checks.
It reports `direct_fresh`, a complete model, and a complete state.
Its original plan, transaction, receipt, and three terminal hashes remain unchanged.

## Continuation controls

`scripts/continue_full_service_v30.py` uses the original registered program and protocol.
Its run path checks their original registration bindings.
It checks all 142 frozen source files before execution.
It also checks the original runtime and historical ledgers.

The continuation binds its controller files and the adapter code.
Every new worker plan binds the continuation manifest hash.
The original launcher and original evidence helper remain unchanged.

The worker still runs from the original frozen source directory.
The controller obtains trials, samples, thresholds, dependencies, and limits from the original program.
It does not add scientific trials or change their order.
The existing attempt directory prevents repeated execution of a completed trial.

The original phase cap remains 3,600 CPU seconds.
The continuation opens the same phase ledger with the same protocol and source identity.
It does not reset or combine allowances.
Unsettled work blocks admission.
Each next trial still needs its complete registered reservation.

Late inputs come from verified earlier outputs.
Their exact hashes enter the worker plan.
The original preparation remains the input source for all registered repair trials.

## Comparison gap and fix

The initial continuation trusted an existing `all_equal` flag.
It also accepted a missing comparison sidecar.
An interruption before sidecar creation could therefore skip a registered comparison on the next dependency read.

The final `completed()` implementation recomputes every declared comparison.
It obtains both artifact entries from independently verified terminal records.
It compares both hashes and byte counts.
A missing sidecar cannot skip this comparison.
An existing sidecar must exactly match the recomputed result.

Comparison references must name earlier registered trials.
The verifier reads those records directly and does not recurse.
This rejects forward references and cycles.
The verification step writes no sidecar or original record.

## Verification

Seven focused fixtures pass in `tests/test_service_terminal_adapter_review_v30.py`.
They cover named artifacts, receipt order, unchanged files, incomplete states, missing sidecars, misleading sidecars, and cyclic comparisons.
No empirical worker ran during this review.
No registration or frozen original changed.

```bash
python -m unittest discover -s tests -p 'test_service_terminal_adapter_review_v30.py' -v
```

The review also verified these original bindings:

| Record | SHA256 |
|---|---|
| Original program | `1f51f676de36090650d36368065ef95daef734b62c569ea2869abb0c024ef2ff` |
| Original protocol | `622ad05d5d06b9255ecf50ad3f8ecdef53037ad0a6284b4a9ce5f6b10ced79c9` |

Reviewed source snapshots:

| File | SHA256 |
|---|---|
| `src/service_terminal_evidence_v30.py` | `a45bd76bd86905471b5dc212046c70fbd78516e1c33334c7bad4a5ef15479d4f` |
| `scripts/continue_full_service_v30.py` | `c897c8de18c5145ab42df111fde255cb07d4d883f5f1624e9a9ca56c17a2a670` |
| `tests/test_service_terminal_adapter_review_v30.py` | `0fbb0f90630926ae95aa169340312df9bb44c5f006e0be3efc8de8eed18ae1c3` |

These checks establish consistency within trusted local evidence.
They do not authenticate hostile storage or prove scientific conclusions from artifact hashes.
