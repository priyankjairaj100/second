# Revision 28: compressed repair with selective row verification

This separate service uses the version 28 ball-box verifier.
It preserves the measured version 27 source and the version 26 compressed state format.
The defining fixed-anchor numerical target remains unchanged.

Source: [`src/fixed_compressed_service_v28.py`](../src/fixed_compressed_service_v28.py).
Tests: [`tests/test_fixed_compressed_service_v28.py`](../tests/test_fixed_compressed_service_v28.py).
Verifier: [`src/ball_box_certificate_v28.py`](../src/ball_box_certificate_v28.py).

The service changes only its ball-verifier import and diagnostic schema relative to version 27.
Its defaults remain forty-bit descriptors, block size 256, and the native exact point solver.
The alternative ridge-floor, preconditioned, and native-interval backends remain available.

```python
from src.fixed_compressed_service_v28 import FixedCompressedService

service = FixedCompressedService(
    decoder, base_target,
    bits=40,
    certificate_backend="ball",
    solver_backend="native_ball",
    max_neural_stage_record_pairs=None,
)
repaired = service.run(
    retained_records,
    method="repair",
    prior=trusted_compressed_state,
    deleted_ids=deleted_ids,
)
```

## Why the verifier changes

A failed row need not force successful rows through every later certificate pass.
The new verifier retains rows already certified by the first complete ball pass.
It sends unresolved rows through directed interval checks using the same coefficient bounds.
It builds shared preconditioned bounds only when unresolved rows remain.
Its optional Python universal fallback also receives only the remaining rows.

Each quantizer row has its own rounding feedback and output codes.
The feature box, normalization, and ridge determine coefficient bounds shared across rows.
Consequently, certified rows may be assembled without changing any row's defining quantization problem.
Every row certificate must still cover that row's complete coordinate sequence and supplied feature box.
An uncertified row cannot be filled from a midpoint-only proposal.

The service accepts a stage only after the selected verifier returns all exact row codes.
If the verifier remains unresolved, the existing complete-stage source replay policy applies.
This implementation does not introduce selective source replay or partial committed stage outputs.

These changes target repeated verification work.
They do not establish a service speedup before complete transaction measurements.
The adverse version 27 result remains evidence for its unchanged implementation.

## Unchanged exactness and state contract

The detailed contract remains in [the version 27 service documentation](FIXED_COMPRESSED_SERVICE_V27.md).
Both revisions accept the same trusted version 26 state type and source-local descriptors.
No state conversion, recompression, or preparation is required merely to select this service implementation.

Fresh preparation still runs the exact fixed-factor service and then compresses its state.
Repair and equally indexed reconstruction receive the same selected verifier and point solver.
Their outputs must match fresh retained-only calibration and canonical state bytes.
Prior calibrated codes remain unused as solver candidates.

Singleton boxes use the selected shared exact point solver.
An unresolved uncertain box triggers exact retained replay only through `TokenBoxUnresolved`.
All required earlier neural stages are counted, including previously certified ancestors.
Regenerated factors must match both source hashes and descriptor enclosures.
Transient factors never modify surviving persistent descriptors.

No-op, complete, sequential, and combined deletions preserve the existing canonical contract.
The returned state contains only surviving source leaves and complete exact calibrated codes.
The prior object remains unchanged, and external copies remain the caller's responsibility.

The neural budget still limits actual source-stage traversal.
It does not limit verification, hashing, compilation, serialization, or exact solver time.
Budget aborts retain the current rejection and native receipts under `pending_stage`.
No incomplete model or state is returned.

## Provenance and cost reporting

The service checks current codec, source preparer, decoder, anchor provider, target, and grid bindings.
Trusted preparation must establish containment before compressed boxes are accepted.
Hash checks and canonical parsing do not independently establish that premise.

The service records the new verifier's full dataclass diagnostics for each completed stage.
Rejected native receipts remain available through `certificate_failure_diagnostics`.
The verifier's row subsets, retries, and shared coefficient work belong to the request's certificate cost.
Those costs must not be omitted because some rows succeeded earlier.

`service_elapsed_ns` remains an in-memory clock.
Complete empirical clocks must also cover construction, loading, output serialization, and writing.
Prior preparation and retained state bytes still belong in lifetime and storage comparisons.
This service does not claim lower peak preparation memory.

## Software verification

The focused suite retains version 27's twenty-one service checks.
It adds cross-version preparation and repair tests using identical state bytes.
This includes both directions: version 28 repairing a version 27 state, and the reverse.

The suite covers all codec precisions and verifier choices, shared singleton dispatch, and exact row-oracle comparisons.
It also covers full replay closure, budget aborts, source contradictions, canonical histories, and rejected native receipts.
The verifier has its own numerical tests for row selection and coefficient reuse.

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
python -m unittest tests.test_fixed_compressed_service_v28 -v
```

These are small deterministic software fixtures, not empirical research datasets.
No research-data run was performed by this service implementation task.
Practical speed, broad acceptance, and quality remain separate measured claims.
