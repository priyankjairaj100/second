# Independent ordered worker review

The ordered complete-service worker passed this independent review after one policy correction.
No numerical or provenance blocker remains at the source hashes below.

| File | SHA256 |
|---|---|
| `scripts/run_ordered_service_v30.py` | `c147f5b536a3618cb7003c380fa69bd4db979f4899dabfe5e17e6c512c2e9151` |
| `tests/test_ordered_worker_v30.py` | `837fae45af29b73549f182158811bc82baefa250c6d2826f616c75bbeb4151de` |

## Numerical and target scope

The worker replaces the scalar decoder with the explicit ordered decoder.
Every comparison receives that same decoder implementation and the same adaptive point solver.
The underlying exact fixed-feature target remains unchanged.
Its identity remains distinct from the sequential target.

Original normalization remains the complete original token count.
Retained selection cannot silently change that normalization.
The worker validates original record membership and each token sequence before feature execution.

The decoder review establishes finite-value equivalence under its stated runtime premises.
This worker review does not independently reprove the numerical kernels.
Complete model equality against a registered artifact uses the full serialized model digest.
The internal stage-code digest remains a separate diagnostic field.

## Preparation and state

Preparation requires the new ordered worker schema and current ordered preparer binding.
It also binds source files, checkpoint files, record contents, solver policy, and original normalization.
The implementation manifest must match its digest and the current decoder's complete manifest.
Historical preparation therefore cannot be silently reused as newly executed preparation.

The prior state's reconstructed model must match the preparation model artifact.
Prior state and output state must carry the new preparer identity.
Model and state outputs undergo canonical round trips before successful completion.
Written output hashes are checked again.

Matching old and new models does not imply matching their provenance-bearing states.
The worker records this distinction explicitly.
Repair and indexed reconstruction retain compatible complete-state obligations.
Model-only reconstruction emits no auxiliary state.

## Resource and input policy

Live phase admission binds the exact worker command before model loading.
Source bindings are checked before execution and before terminal success.
Input hashes, file limits, and method-specific input sets are enforced.
Model-only reconstruction cannot receive a prior-state input or preparation receipt.

Every stage and the cumulative point schedule receive structural admission before neural execution.
These estimates do not guarantee memory fit, wall time, or certificate completion.
The outer controller remains responsible for process limits and complete transaction accounting.
Runtime affinity and thread settings are recorded as execution evidence.

The worker records nested service and phase clocks without adding them to complete latency.
Prior preparation cost remains lifetime provenance, rather than new request speedup credit.
Failed gates leave failure progress without a successful terminal record.

## Corrected policy hole

The initial worker accepted an expected state digest for model-only reconstruction.
Its state-free output path would then ignore that impossible gate.
The final worker rejects any non-null state expectation for this method before execution.
Stateful methods retain the registered state gate.

## Verification

The independent review reran eleven software fixtures successfully in a reported 1.634 seconds.
The fixtures cover preparation, repair, indexed reconstruction, model-only reconstruction, and complete miniature model equality.
They also cover provenance rejection, registered hash failures, malformed inputs, and early resource refusal.

These fixtures do not constitute empirical workloads or timing evidence.
No empirical worker ran during this review.
The reviewer changed no worker source or historical campaign artifact.
