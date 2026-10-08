# Revision 25: compressed fixed-feature repair service

This service preserves the revision 21 fixed-anchor calibration target.
It implements complete canonical compressed states and bounded exact fallback.
It does not establish a practical speedup or broad empirical acceptance.

The numerical target remains different from sequential calibration.
Its stage features come from the fixed nearest-grid ancestor model.
Calibrated output codes never become that feature model's ancestor matrices.
Neither compressed centers nor box endpoints replace the defining exact features.

## API and storage

Implementation: [`src/fixed_compressed_service.py`](../src/fixed_compressed_service.py).
Canonical format: [`src/fixed_compressed_state.py`](../src/fixed_compressed_state.py).
Codec: [`src/fixed_factor_codec.py`](../src/fixed_factor_codec.py).

```python
service = FixedCompressedService(
    decoder, base_target,
    bits=16,                  # enclosure precision: 16 or 24
    block_size=256,
    solver_backend="native_ball",  # or "reference"
    certificate_backend="ridge_floor",  # or "preconditioned"
    max_neural_stage_record_pairs=None,
    progress=None,
)
prepared = service.run(original_records)
repaired = service.run(
    retained_records,
    method="repair",
    prior=prepared.state,
    deleted_ids=deleted_record_ids,
)
canonical_bytes = repaired.state.canonical_bytes()
```

`indexed_fresh` exposes the same retained descriptors and executes the same repair algorithm.
This equally informed comparator receives every compatible optimization.
Prior model codes are not proposals or solver inputs.
No candidate warm start is hidden in either route.

The result contains complete stage codes, compressed state, and diagnostics.
The state includes surviving tokens, descriptors, provenance, codec settings, and complete calibrated codes.
Base checkpoint parameters outside calibrated stages remain separately required.
Deleted leaves disappear from the returned state.
The caller must commit that state and manage any external copies.

Storage remains source-local.
Each stage descriptor depends only on its own source and fixed public settings.
Repair preserves surviving descriptor bytes exactly.
Temporary regenerated factors never replace those descriptors.

## Execution

Fresh preparation runs the existing exact-factor service with the shared point solver.
It then compresses the resulting factor state.
All exact preparation, calibration, and compression costs belong to this route.
This initial implementation temporarily materializes the complete exact-factor state.
It therefore makes no reduced peak-memory claim.

Repair first verifies the declared retained membership and unchanged source tokens.
It checks the numerical target, grids, codec settings, and current source bindings.
It also checks decoder, provider, fixed-anchor, and preparer provenance.

For each stage, repair decodes surviving descriptors into outward feature boxes.
The selected universal box verifier then attempts complete-stage certification.
`ridge_floor` selects the existing `certify_dyadic_box` verifier.
`preconditioned` selects `certify_preconditioned_dyadic_box` with verified componentwise coefficient bounds.
Both methods preserve the same exact target, and both can abstain.
Repair and equally indexed reconstruction receive the same selected method.
Successful certification supplies exact target codes for every factor matrix inside the box.
This includes the defining source features under trusted preparation.

Only `TokenBoxUnresolved` triggers exact fallback.
Malformed inputs, unsupported runtimes, and unexpected arithmetic failures abort instead.
Singleton boxes bypass interval verification and use the selected shared exact point solver.
This includes the empty-retained-corpus case.
The native backend therefore receives singleton work when `native_ball` is selected.
No retained traversal is required to evaluate a valid singleton box.

Fallback advances each retained source through its fixed nearest-anchor traversal.
It creates one generator per replayed source and advances each stage at most once.
Previously certified ancestors still require execution when a later rejected stage depends on them.
Every produced stage is checked against its descriptor's exact source hash and enclosure.
These checks include replayed ancestors whose codes were already certified.

The requested exact factors then reach the existing native or reference point solver.
Its grids, normalization, ridge, and exact-refinement limits match the ordinary fixed-factor service.
Failure to resolve that solver also aborts without a returned state.

The service reconstructs the complete canonical state only after every stage succeeds.
It never mutates the supplied prior state.
Partial progress reports are diagnostics, not a committed partial model.

## Conditional correctness and canonical deletion

Assume deterministic fixed-anchor evaluation and valid trusted source descriptors.
Assume the existing box verifier and exact point solver satisfy their documented contracts.

Each accepted stage equals the exact fixed-feature target by universal box certification.
Each rejected stage equals that target after checked exact replay and point quantization.
The stage targets are independent once the fixed feature law is specified.
Thus every returned complete model equals fresh retained-only calibration.

The descriptor encoder is deterministic and source-local.
Deleting other sources cannot change a surviving descriptor.
Fresh retained preparation and successful repair therefore produce identical descriptors, tokens, metadata, and stage codes.
Canonical serialization consequently produces identical bytes.
This also covers no-op requests, full deletion, and different deletion orders.

This conclusion is conditional on valid preparation.
Hashes and parser checks cannot establish containment for unavailable source factors.
Accepted stages are not replayed merely to re-establish that premise.
Untrusted descriptor fabrication lies outside this service's trust model.
Externally stored state should be verified against a digest from trusted preparation.
Replay can detect contradictions in factors it actually regenerates.
It cannot authenticate every accepted, unevaluated descriptor independently.

## Work bounds and accounting

Let the service contain S stages and n retained sources.
Let j be the largest rejected stage index, counting the first stage as one.
For this full-stage fallback policy, successful repair performs exactly n*j neural stage-record traversals.
If every certificate accepts, j is zero.
If the final stage rejects, every retained stage is traversed.

An early accepted certificate therefore does not necessarily avoid neural work.
The diagnostics report final avoided work as n*S minus actual traversals.
They also expose per-source counts and each stage's newly required prefix work.

`max_neural_stage_record_pairs` bounds actual replay advancement.
Budget exhaustion raises `NeuralBudgetExceeded` with accumulated diagnostics.
Fresh preparation checks its known n*S traversal requirement before starting.
The budget does not cap certificate, solver, decoding, hashing, or serialization work.
An external CPU controller remains necessary for empirical resource limits.

Reported work includes descriptor decoding, rejected certificates, prefix replay, and replay checks.
It also includes point solving, context preparation, code packing, and state construction.
Repeated descriptor decoding during ancestor validation is explicitly counted.
`singleton_point_stages` records exact singleton proofs separately from uncertain-box certificate attempts.
`point_solver_stages` includes both singleton proofs and exact replay fallback.
Singleton point time is charged once, inside `point_solver_elapsed_ns`.

`service_elapsed_ns` covers the in-memory call.
It excludes constructor work, external loading, and serialization or writing of returned artifacts.
Empirical workers must retain complete outer clocks covering those omitted phases.
The fresh route's `exact_preparation_elapsed_ns` includes its entire underlying exact-service call.
The nested exact-service diagnostics and copied phase fields are breakdowns of that time.
They must not be added again as disjoint costs.

## Validation and limits

The focused service suite uses tiny deterministic software fixtures.
It covers both codec precisions, both point backends, and independent dense rational row oracles.
Actual non-singleton certificates accept the fixture without neural replay.
Forced rejections verify fallback correctness without assuming practical certificate acceptance.

Additional tests cover complete ancestor closure, nonconsecutive rejection, budgets, provenance, and source contradictions.
They verify canonical equality across fresh, indexed, sequential, combined, no-op, and empty deletion histories.
They also verify that prior output values cannot act as hidden solver candidates.
Additional route tests cover preconditioned acceptance, rejection, and bounded exact fallback.
Nonempty zero-factor fixtures verify singleton dispatch without mocking the stored feature boxes.
Empty-corpus fixtures verify the same route and complete canonical output.
Both selected point backends reproduce the reference output.

The initial reviewed service had SHA256
`4191c20617921df3406f449181d96eb9f3a9c067f46fbf1532ebfde7784b6ad0`.
That version used the ridge-floor verifier alone and routed singleton work through its reference point path.
The present revision adds selectable verification and shared singleton dispatch.
It does not modify the target digest, codec, persistent state format, or source descriptors.
The updated focused service suite contains seventeen passing tests.

Run:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
python -m unittest tests.test_fixed_compressed_service_v25 -v
```

No real-model worker ran for this implementation task.
No result here demonstrates certificate acceptance, speed, or quality on research data.
The revision 24 archive sizes remain projections under their recorded framing assumptions.
They are not measurements of this new complete state format.

The initial policy replays every retained source when a stage rejects.
It does not implement selective source refinement or certificate-driven precision escalation.
Both remain separate algorithmic possibilities requiring fresh correctness and accounting review.
