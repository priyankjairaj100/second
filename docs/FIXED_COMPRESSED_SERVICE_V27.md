# Revision 27: extended-precision compressed repair

This implementation preserves the existing fixed-anchor numerical target.
It adds a separate service using version 26 compressed states and version 27 ball certificates.
The version 25 service remains unchanged.

Source: [`src/fixed_compressed_service_v27.py`](../src/fixed_compressed_service_v27.py).
Tests: [`tests/test_fixed_compressed_service_v27.py`](../tests/test_fixed_compressed_service_v27.py).
State: [`src/fixed_compressed_state_v26.py`](../src/fixed_compressed_state_v26.py).

The service passes twenty-one focused software tests.
This implementation task ran no research-data evaluation or empirical worker.
The tests establish neither practical certificate acceptance nor speed.

## Public interface

```python
from src.fixed_compressed_service_v27 import FixedCompressedService

service = FixedCompressedService(
    decoder, base_target,
    bits=40,
    block_size=256,
    solver_backend="native_ball",          # or "reference"
    certificate_backend="ball",
    max_neural_stage_record_pairs=None,
    progress=None,
)
original = service.run(original_records)
repaired = service.run(
    retained_records,
    method="repair",
    prior=original.state,
    deleted_ids=deleted_ids,
)
output = repaired.state.canonical_bytes()
```

The supported precision values are 16, 24, 32, 40, and 48 bits.
Precision controls the stored enclosure, not the defining feature values or model grids.
The default is forty bits.

| Certificate backend | Implementation | Behavior |
|---|---|---|
| `ball` | `ball_box_certificate_v27.certify_ball_dyadic_box` | Uses verified feature-error bounds and the shared native ball kernel |
| `ridge_floor` | `dyadic_box_certificate.certify_dyadic_box` | Uses the baseline universal box certificate |
| `preconditioned` | `preconditioned_box_certificate.certify_preconditioned_dyadic_box` | Adds verified componentwise coefficient bounds |
| `native_interval` | `native_box_certificate.certify_native_dyadic_box` | Uses native directed interval decisions |

The native verifier wrappers retain their documented Python universal fallback policies.
Those extra passes and their costs remain visible in stage diagnostics.
They do not substitute an uncertified center-point model for an uncertain box.
`certificate_backend` selects box verification independently of the exact `solver_backend`.

Singleton boxes bypass interval verification and use the selected shared exact point solver.
This optimization applies to every certificate backend and the empty-source case.
The selected point solver also handles exact retained replay after rejection.

`indexed_fresh` runs the same algorithm with the same retained descriptors and backend.
Fresh preparation delegates to the existing exact-factor service, then compresses its complete state.
This route includes its complete factor preparation and exact calibration costs.
It temporarily materializes exact factors and makes no reduced peak-memory claim.

## Target, trust, and canonical state

The fixed-anchor target is unchanged.
Each source's defining features use the calibration-independent nearest-grid ancestor matrices.
Calibrated outputs never replace those fixed ancestors during feature preparation or replay.

Version 26 descriptors and states use distinct serialization schemas and magic values.
The service rejects version 25 state objects.
It checks current codec dependencies, preparer, decoder, provider, fixed anchor, and model target bindings.
It also checks complete grids, source membership, and unchanged token sequences.

Changing storage precision does not change the numerical model target.
However, refinement cannot recover narrower descriptors from coarse descriptors alone.
It requires trusted exact factors or exact source replay.
This service accepts states with matching declared precision and block size.
It performs no automatic state migration or precision conversion.

Each descriptor's contents depend only on that source and fixed public settings.
Repair retains surviving descriptor bytes exactly and removes deleted leaves from its returned state.
Complete calibrated codes and surviving token sequences remain part of that state.
Other base checkpoint parameters remain separately required.

Trusted preparation must establish every descriptor's source-containment premise.
Hashes and structural parsing do not prove containment without the source factors.
An external state digest must come from a trusted preparation record.
Accepted, unevaluated boxes still rely on that premise.

## Exact fallback and closure accounting

Only `TokenBoxUnresolved` triggers source replay.
Other errors propagate without a committed result.
Each retained source gets one lazy generator.
It advances only when a rejected stage requires its factors.

Late replay executes all required earlier stages, including previously certified ancestors.
Every regenerated stage is checked against its exact source hash and descriptor enclosure.
The service counts these ancestor traversals as actual neural work.
Temporary replay factors do not enter the persistent state.

Let S denote the stage count and n the retained-source count.
Let j denote the final rejected stage, numbered from one.
If all stages are certified or singleton-resolved, set j to zero.
Successful repair performs n*j neural stage-record traversals under this complete-stage fallback policy.
The reported avoided count is n*S minus actual traversals.
Earlier acceptance provides no neural avoidance when the final stage requires replay.

The optional neural budget is checked before every traversal.
Exhaustion raises `NeuralBudgetExceeded` with accumulated diagnostics and no returned state.
Fresh preparation checks its known n*S traversal requirement before starting.
This budget does not bound certificate CPU time, storage, hashing, or exact solver work.
Empirical workers still require their own complete resource controller.

## Correctness contract

Assume valid trusted descriptors and deterministic fixed-anchor evaluation.
Assume the selected universal verifier and exact point solver satisfy their reviewed contracts.

A successful uncertain-box certificate returns the exact target codes for every enclosed factor matrix.
The defining source factors are enclosed by the preparation premise.
Singleton resolution uses those factors' unique numerical matrix and the exact point solver.
Rejected stages use checked source replay followed by that same point solver.
Every returned stage therefore equals fresh retained-only calibration.

Surviving descriptors are intrinsic to their sources.
Their unchanged bytes match direct fresh encoding under the same codec settings.
Complete output codes also match, and canonical state metadata contains no repair-history fields.
Consequently, fresh, repaired, and equally indexed states serialize identically.
The argument includes no-op requests, full deletion, and different deletion orders.

No state is returned until every stage resolves.
The immutable prior remains unchanged.
The caller remains responsible for committing the returned state and managing external archival copies.

## Cost receipts

Top-level diagnostics include actual traversal counts, descriptor decodes, verification, solving, context construction, and code packing.
Certificate elapsed time includes accepted and rejected attempts.
Successful native certificates expose kernel, coefficient, compilation, and universal-fallback receipts through `solver_diagnostics`.
Rejected native certificates preserve their attached receipts in `certificate_failure_diagnostics`.
If a neural budget aborts replay, `pending_stage` retains the current rejection and native receipts.
Its traversal count includes work completed before that abort.
Successful requests leave `pending_stage` empty.

`native_build_manifest` describes the point solver only.
Certificate kernel identities and build costs appear in their stage receipts.
The service does not perform an extra certificate compilation merely to request a manifest.

Singleton proofs increment `singleton_point_stages` and `point_solver_stages`.
They do not increment uncertain-box certificate attempts or acceptance counts.
Their time is charged once under `point_solver_elapsed_ns`.

`service_elapsed_ns` covers the in-memory call.
Constructor work, external loading, serialization, and writing require complete outer transaction clocks.
Fresh `exact_preparation_elapsed_ns` contains the underlying exact-service call.
Its nested diagnostics and copied phase fields are breakdowns, not additional disjoint costs.

## Software checks and remaining evidence

The twenty-one focused checks cover all five precisions and all four certificate backends.
They verify canonical histories, default ball acceptance, native interval acceptance, shared singleton dispatch, and bounded fallback.
They also check provenance, malformed membership, accepted-ancestor hashes, source containment, and rejected native receipts.
Both point backends reproduce independent dense rational row oracles.
Prior output codes remain unused as solver candidates.

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
python -m unittest tests.test_fixed_compressed_service_v27 -v
```

Research-data acceptance, complete transaction speed, lifetime costs, and quality remain separate empirical questions.
Previous archive storage projections must not be relabeled as measurements of this service.
Selective source refinement and adaptive persistent precision are not implemented here.
Both would require separate canonical-state and cost arguments.
