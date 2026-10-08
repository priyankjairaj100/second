# Ordered compressed service, revision 30

## Purpose

The ordered compressed service shares optimized finite neural execution with the ordered cold and lossless controls.
This closes a fallback implementation mismatch before measuring compressed repair.
It does not establish a measured speedup.

The numerical target remains fixed nearest-grid ancestor features.
The original sequential calibration target remains distinct.
Compression settings, exact quantization rules, certificate algorithms, and point resource policies remain unchanged.
Certificate arrays have a separately declared workspace allowance.

## Interface

```python
from src.ordered_compressed_service_v30 import OrderedCompressedService
from src.ordered_finite_decoder_v30 import OrderedFiniteDecoder

decoder = OrderedFiniteDecoder(base_decoder, primitive_backend="mpfr_enclosure")
service = OrderedCompressedService(
    decoder,
    base_target,
    bits=40,
    block_size=256,
    solver_backend="auto",
    certificate_backend="auto",
    max_neural_stage_record_pairs=0,
)
result = service.run(
    retained_records,
    method="repair",
    prior=ordered_compressed_state,
    deleted_ids=deleted_ids,
)
```

The constructor adds `max_certificate_workspace_bytes` to the parameters accepted by `AdaptiveCompressedService`.
Its default is 512 MiB.
The `run` parameters remain unchanged.
Supported methods are `direct_fresh`, `repair`, and `indexed_fresh`.
Fresh preparation calls `OrderedFixedAnchorService`.
Fallback calls explicit `ordered_sequential_features` with the same fixed ancestor matrices as ordered cold reconstruction.
The service requires an actual `OrderedFiniteDecoder`.
It never replaces global decoder or traversal functions.

The separate point, certificate, and neural budgets retain their prior meanings.
Zero neural allowance permits certificate-only repair and refuses requests requiring replay.
An admitted route can still refuse numerically.
No automatic unbounded solver or alternate-certificate retry exists.

`max_certificate_workspace_bytes` covers certificate route assessment, box assembly, and sparse/primal certificate calls.
The sparse backend also retains its own `SparseCertificateBudget.max_workspace_bytes` ceiling.
Both ceilings must admit a sparse request.
The existing per-stage coefficient work ceiling and cumulative certificate work ceiling still apply.
Point admission and point calls retain the original `coefficient_budget` without modification.

An allocation-free audit used all 24 recorded DistilGPT2 stage shapes and 128 retained tokens.
The 512 MiB certificate allowance admits only 12 sparse stages.
The MLP allowances are 636,551,680 and 690,815,488 bytes.
Explicitly setting both certificate and sparse ceilings to 1 GiB admits all 24 sparse stages under the pilot work limits.
Point policy remains 512 MiB, with a maximum assessed array allowance of 205,529,088 bytes.
Its complete structural reservation remains 21,233,418,240 work units.
These assessments execute no neural work and do not establish numerical acceptance, completion, or process memory fit.

## Preparation and conversion

The service accepts only states bound by `ordered_preparer_binding()`.
This binding identifies the actual ordered factor preparation sources.
The compressed service does not create a separate factor preparation identity.
Its fresh path delegates factor preparation to the existing ordered exact service.

Convert newly prepared ordered lossless state through exact decoded factors and the existing canonical compressed codec.
That conversion must retain the original ordered preparation binding.
The worker must verify every decoded source hash and actual enclosure containment.
Only a trusted conversion receipt establishes those numerical premises for later certificate-only repair.

Historical preparation states are rejected before descriptor decoding.
They remain rejected after complete deletion.
No state is relabeled to make it compatible.
Historical and ordered model codes can agree while their complete states retain different provenance.

The codec and descriptor bytes remain unchanged when source factors match.
Within the ordered preparation family, repair and indexed outputs match fresh canonical successor state.
Retained descriptors are reused without modification.

## Shared numerical controls

The service reuses the existing pure compressed-route assessment and result types.
Its explicit implementation preserves these checks:

- Certificate admission before uncertain descriptor computation.
- Separate cumulative certificate and point reservations.
- Point admission before fallback neural work.
- Per-pair neural allowance checks through the complete ancestor traversal.
- Source hash and enclosure validation for every replayed factor.
- Exact point dispatch for singleton feature boxes.
- Provenance, source membership, and retained-token equality.
- No prior model codes as hidden solver candidates.

Sparse and primal certificate algorithms are shared unchanged.
The adaptive point dispatcher is also shared with ordered exact and lossless controls.
All controls therefore receive the same applicable numerical optimizations.

Structural allowances do not certify process memory or execution time.
Empirical workers still require independent process and wall-time controls.

## Diagnostics and complete costs

Each receipt records the actual ordered decoder implementation manifest and factor preparation binding.
Failed point solves preserve nested solver evidence, current stage duration, and cumulative reservations.
Fresh failures preserve the exact service's receipt when available.
Missing observations remain unknown.

The in-memory timer includes decoding, certification, replay, validation, and output-state construction.
External input parsing, evidence-closure verification, serialization, and output verification remain worker costs.
The complete transaction clock remains authoritative.

Original ordered preparation and lossless-to-compressed conversion are separate lifetime costs.
Neither becomes free because a later request reuses its state.
The original-corpus model-only baseline is required for a lifetime comparison.

Worker plans must explicitly choose historical or ordered execution.
Ordered conversion must consume verified ordered preparation.
Reference cold and lossless comparisons must use the corresponding ordered execution policy.
Complete transaction comparisons must disclose any unequal evidence-verification work.

## Verification

```bash
python -m unittest tests.test_ordered_compressed_v30 -v
```

Twenty-seven focused tests passed on 8 October 2026.
They cover all point routes and both uncertain-box certificate routes.
They compare complete codes and descriptor bytes against the historical implementation.
They test ordered lossless conversion and canonical fresh, repaired, indexed, empty, and complete-deletion states.

Forced certificate refusal makes fallback execute and validate every required ancestor.
The complete fallback solver input bytes match the ordered cold control.
Tests also cover separate budgets, early admission, stale provenance, invalid containment, hidden candidates, and failure receipts.
Additional checks bind the separate certificate cap through both backends while preserving the original point policy.
The actual-shape audit preserves the 512 MiB refusal and verifies 1 GiB admission without neural execution.

These are software fixtures, not empirical datasets.
Real-model identity, speed, replay frequency, and lifetime cost remain empirical questions.
No empirical worker was executed during this implementation.
