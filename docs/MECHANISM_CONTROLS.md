# Matched controls and service diagnostics

Revision 6 adds policy controls within one declared service.
Each control uses the same target, intrinsic statistics, manifest, and canonical state.
Each control constructs every stage from the newly certified ancestor outputs.
No control uses an old quantized model as a proposal.

| Mode | Proposal | Eligibility |
| --- | --- | --- |
| `certified` | Shifted linear response Gram | Valid query and response bound |
| `fixed_reference` | Constant reference Gram | Valid query and reference bound |
| `identity_only` | Constant reference Gram | Equal reference ancestors and valid reference bound |
| `full_replay` | Exact retained Gram | Successful retained feature evaluation |

All modes retain exact replay as the fallback.
Finite evaluation failure aborts the operation.
The service returns no approximate model after that failure.

## Base-reference identity control

Supply `reference_weights` when constructing `AggregateRepairService`.
This mapping must contain immutable exact matrices for every stage.
It must describe the fixed reference used by the intrinsic extractor.
This association belongs to the trusted callback contract.
The service cannot prove an arbitrary extractor's meaning.

The control compares every transitive ancestor against this mapping.
It compares newly installed outputs, including outputs computed after deletion.
Equality with the original quantized model does not establish reference equality.
An absent mapping causes replay.
A changed reference ancestor causes replay.

The comparison uses exact rational equality.
This test is sufficient for finite installation equality.
It can reject distinct rational values that produce equal finite values.
Such rejection only increases replay.

The reference Gram can contain midpoint features from a smooth ideal evaluator.
It need not contain the exact finite features.
Therefore, identity eligibility does not remove the numerical error bound.
The control still verifies rounding decisions using the full reference bound.

This control does not implement cached original-model Grams.
Such a cache would require separate construction, storage, maintenance, and comparison costs.
No cache was added to canonical state.

## Fixed reference bound

Let `Z0` contain the retained reference features.
Let `D(a)` contain the linear feature response.
The provider proves `||X - Z0 - D(a)||_F <= e`.
The intrinsic tangent Gram gives `||D(a)||_F <= t`.
Then the triangle inequality gives:

\[
\|X-Z_0\|_F\le e+t=E.
\]

The fixed proposal uses `S0 = Z0 Z0^T`.
Its symmetric error bound is:

\[
-\delta I\preceq XX^T-S_0\preceq\delta I,
\qquad
\delta=2\|Z_0\|_F E+E^2.
\]

The implementation uses exact rational arithmetic and outward square roots.
It keeps the existing finite error, derivative error, curvature, and residual terms.
It does not replace the sequential target with a fixed-teacher target.
Both the proposal and bound use retained aggregate statistics.
The control removes the linear proposal update while retaining the same evidence.

Revision 7 implements the full quadratic response tier with separate state and index schemas.
It records extraction products, storage slots, and serialized state costs.
See `docs/QUADRATIC_CONTROL.md` for its unwhitened error bound and remaining stronger-certificate extension.
The fixed reference control remains a distinct mechanism.
The original-model cache is also a distinct service family; see `docs/IDENTITY_CACHE.md`.

## Diagnostic telemetry

```python
from src.service_telemetry import ServiceTelemetry

telemetry = ServiceTelemetry()
try:
    result = service.repair(
        state, deleted_records, retained_source,
        mode="fixed_reference", telemetry=telemetry,
    )
finally:
    diagnostics = telemetry.payload()
```

The optional `telemetry` keyword also works with `fresh`, `prepare_index`, `indexed_fresh`, and `load_state`.
The collector remains outside canonical state.
It survives failed operations and records the exception class.
Use one collector for each measured arm.
Read its payload after the operation finishes.

| Timing category | Included work |
| --- | --- |
| `extraction` | Intrinsic extraction, contribution checks, and contribution digest construction |
| `bound_query` | Query binding, chart checks, contractions, and proposal bounds |
| `fresh_feature_evaluation` | Finite features during direct fresh construction |
| `replay_feature_evaluation` | Finite features during retained replay |
| `gram_accumulation` | Gram products, matrix updates, and metric normalization |
| `factor_rounding` | Exact factors, rounding, and certificate predicates |
| `validation_metadata` | State validation, membership operations, deletion checks, and PSD checks |
| `serialization` | Canonical state or index serialization |
| `source_access` | Retained source retrieval and source digest checks |
| `service_overhead` | Remaining instrumented service work |

Nested spans subtract all child time from their parent.
This rule also applies when nested spans share a category.
Therefore, the sum of exclusive categories does not double-count nested intervals.
Clock and event bookkeeping still add instrumentation overhead.
These timings describe instrumented diagnostic execution.
They do not establish clean service latency or cold-cache behavior.

The outer runner must separately measure loading, durable writes, and other work outside the service call.
It must not add diagnostic categories to an already inclusive arm duration.

## Coverage events

The collector records these visible events:

- Available and unavailable intrinsic extraction.
- Available response bounds and unavailable aggregate evidence.
- Missing reference mappings and unequal reference ancestors.
- Query abstention, including the provider's stated reason.
- Chart-radius rejection.
- Nonpositive lower scales.
- Accepted and rejected stage certificates.
- Rejected rounding predicates, including their existing reasons.
- Replayed groups and forced replay stages.
- Completed or failed feature evaluations.
- Completed or failed service operations.

Event counts are operation counts, not independent observations.
The denominator for empirical reliability remains the frozen request inventory.
The automatic extractor currently returns only unavailable evidence after several proof failures.
Telemetry cannot recover a hidden primitive failure reason from that return value.

## Software validation

Correctness fixtures compare all controls against complete retained fresh state.
A certified finite decoder fixture also checks control parity.
An unchanged old model fixture rejects invalid reference-identity reuse.
A nonzero error fixture verifies the preserved numerical floor.
A direct Gram check verifies both sides of the fixed reference bound.
A deterministic clock fixture verifies nested timing and exception cleanup.
These fixtures establish software properties only.
They do not establish real-model coverage, useful quality, or speedup.
