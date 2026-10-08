# Revision 29: exact lossless-state control

This control stores every original feature bit and uses the unchanged fixed-factor point service.
It provides the mandatory full-information lossless storage control for compressed-enclosure repair.
The numerical target, model grids, source features, and point solvers remain unchanged.

Sources:

- [`src/fixed_lossless_state_v29.py`](../src/fixed_lossless_state_v29.py)
- [`src/fixed_lossless_service_v29.py`](../src/fixed_lossless_service_v29.py)
- [`src/fixed_lossless_codec_v29.py`](../src/fixed_lossless_codec_v29.py)

## Interface and exact state

```python
from src.fixed_lossless_service_v29 import FixedLosslessService
from src.fixed_lossless_state_v29 import from_factor_state, parse, serialize

service = FixedLosslessService(decoder, base_target, solver_backend="native_ball", progress=callback)
original = service.run(original_records)
repaired = service.run(
    retained_records, method="repair",
    prior=original.state, deleted_ids=deleted_ids,
)
indexed = service.run(
    retained_records, method="indexed_fresh",
    prior=original.state, deleted_ids=deleted_ids,
)
```

Convenience methods `repair(prior, deleted_ids)` and `indexed_fresh(prior, deleted_ids)` derive records from stored tokens.
`.target` exposes the existing fixed-anchor model target.
Progress callbacks pass directly to the unchanged point service.

`LosslessFactorState` contains complete calibrated model codes, source leaves, tokens, and current provenance bindings.
Each leaf stores complete ordered `LosslessFactorDescriptor` objects.
The codec deterministically selects raw, zlib, or byte-shuffled zlib for each individual factor.
Selection depends only on that factor and the bound compressor implementation.
Every binary64 source bit survives, including signed zero.

The storage schema is `source_local_lossless_factors_v1`, with a distinct `VCLS` version-one magic.
It rejects other state formats.
`from_factor_state(exact_state)` creates the complete lossless state.
`to_factor_state(lossless_state)` reconstructs the complete exact-factor state byte-for-byte.
`decode_anchors(state, record_ids)` decodes only the selected source leaves.

Base checkpoint parameters outside calibrated stages remain separately required.
Report the serialized complete state size, including model codes and metadata.
Descriptor payload ratios alone do not measure the complete storage advantage.

## Repair without repeated compression

The wrapper validates target, grids, membership, tokens, codec, and preparer bindings.
It decodes the retained descriptors and verifies their exact source hashes.
The unchanged point service then validates their decoder, provider, and anchor provenance.
It recomputes the exact model from those retained factors.
An explicit comparison with the current result bindings also protects full deletion, when no source leaf survives.

The wrapper uses `FixedAnchorService.run_prepared` with an explicit decoded-source manifest and receipt.
That receipt describes decoding inside the current request.
It does not pretend that the previous model was trained on a different source set.
It also does not represent the original feature-preparation cost.

After calibration, repair retains the original surviving lossless payloads.
It therefore performs no unnecessary recompression.
Equally indexed reconstruction receives exactly the same optimization and numerical route.
Fresh construction encodes every new source factor.
Prior model codes never act as hidden candidates or warm starts.

The codec is deterministic and source-local.
Reusing a surviving descriptor therefore matches encoding that same exact factor during independent fresh construction.
Combined with exact point calibration, this gives complete canonical state equality.
The fixtures cover sequential, combined, no-op, and full deletion histories.

The immutable prior remains unchanged.
The caller must commit the returned state and manage external archival copies.

## Provenance and parser limits

The state binds the fixed model target, anchor target, decoder, provider, anchor, preparer, and lossless codec.
The codec additionally binds its source dependencies and compressor runtime.
Canonical compressor choices are scoped to that bound implementation.

The parser checks complete model metadata, ordered factor dimensions, source IDs, token digests, hashes, and canonical framing.
It preflights each leaf's aggregate values and payload bytes before decoding that leaf's descriptors.
The codec separately bounds each decoded factor and rejects trailing, incomplete, oversized, or invalid streams.
Caller-supplied `LoadLimits` can tighten the state, model, source, and token caps.

Exact decompression proves recovery of the stored source bytes.
Trusted provenance still establishes that the declared feature extractor produced those bytes.
Content hashes cannot establish that origin independently.

## Complete cost accounting

Strict input parsing decodes and checks every supplied descriptor.
Canonical validation also recompresses those factors, including factors from later-deleted sources.
Those costs belong to the outer input-loading phase.
They must not disappear from comparisons because the service receives an already parsed object.

Inside `run`, repair decodes only retained descriptors once more.
`decoded_descriptors`, `decoded_source_bytes`, and `decoded_payload_bytes` record that request work.
`decoded_deleted_descriptors` is zero within this service scope.
It does not assert that external parsing avoided deleted descriptors.

`encoded_descriptors` counts actual fresh encoding calls.
`reused_descriptors` and `reused_payload_bytes` identify unchanged payload reuse during repair and indexed reconstruction.
No recompression time is invented for that reuse.
Fresh encoding selects a codec once, without repeating its own already established canonical choice.

`lossless_decode_elapsed_ns`, `decode_receipt_elapsed_ns`, and `exact_service_elapsed_ns` report separate wrapper phases.
Fresh output encoding and indexed output-state assembly have separate fields.
Copied point-solver fields are breakdowns inside `exact_service_elapsed_ns`, not additional disjoint costs.
The nested prepared-service receipt also reports the decode time already charged by the wrapper.
Do not add that recorded receipt time again.

Top-level neural counts include actual fresh feature preparation or model-only replay.
Indexed lossless methods execute zero neural feature traversals.
They still read exact retained factors and recompute every model stage with the shared point solver.

`service_elapsed_ns` excludes constructor work, input parsing, and output serialization or writing.
Complete empirical workers must include those phases in their outer clocks.
Original feature preparation and persistent raw information remain separate lifetime costs.
Fresh state creation temporarily materializes exact factors and makes no lower peak-memory claim.

The wrapper supports `model_only_fresh` without reading a prior state or consulting the codec.
The strongest cold comparator may call the unchanged `FixedAnchorService` directly.
That avoids wrapper-specific setup while preserving exactly the same numerical target and solver.

## Validation and claim limits

Fourteen focused state/service tests pass.
They cover complete exact-state byte roundtrips, signed zero, immutable arrays, parser limits, and malformed metadata.
They also cover canonical deletion histories, source provenance, retained-only request decoding, payload reuse, and model-only isolation.
Both point backends return identical models, and progress remains forwarded.

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
python -m unittest tests.test_fixed_lossless_v29 -v
```

These are small software fixtures, not empirical datasets.
This implementation task performed no research-data execution.
Actual complete-state sizes belong to the separate archive audit.
Speed, lifetime cost, and quality require their own matched empirical evidence.
