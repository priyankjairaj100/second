# Bounded adaptive compressed service, V30

`src/adaptive_compressed_service_v30.py` implements `AdaptiveCompressedService`.
It preserves the historical compressed state format and fixed-feature target.
It changes numerical dispatch and resource controls only.

The service uses these public options.

```python
service = AdaptiveCompressedService(
    decoder, base_target,
    bits=40,
    block_size=256,
    solver_backend='auto',       # auto, token, or primal
    certificate_backend='auto', # auto, sparse, or primal
    coefficient_budget=AdaptiveBudget(),
    sparse_budget=SparseCertificateBudget(),
    max_certificate_work_units=6_000_000_000,
    max_point_work_units=48_000_000_000,
    max_neural_stage_record_pairs=None,
)
```

The current adaptive point policy requires four-bit model grids.
The `bits` constructor option selects descriptor precision, not model grid precision.
`direct_fresh`, `repair`, and `indexed_fresh` retain their previous membership contracts.
No prior model values enter the numerical solver as hidden candidates.

## Dispatch and resource limits

Every stage receives an allocation-free plan before descriptor decoding.
`assess_compressed_routes` compares two explicitly bounded certificate routes.
The sparse route uses requested-coordinate checks.
The primal route uses verified feature-space coefficients.
Automatic selection uses the smallest admitted structural work reservation.
This policy does not claim an optimal timing crossover.

The service has separate cumulative certificate and point-work limits.
It also retains the separate neural traversal limit.
These limits do not reset between stages.
Reservations describe permitted structural work, not observed CPU time.
A failed or early-completing attempt retains its full reservation.
The service never refunds a reservation based on guessed work.

For sparse certification, let \(r\) denote the possible adaptive round count.
Let \(K\) denote the distinct-coordinate limit.
Let \(R=md(2T+b+1)\) denote one complete row sweep.
Let \(I=dT^2+R+dT+m2^b\) denote initial work.
The service computes

\[
W_{\mathrm{sparse}}^{\mathrm{ceiling}}
=I+(1+r)R+rdT^2+KT^3.
\]

It reserves the minimum of this ceiling and applicable per-stage and cumulative limits.
The route can start only when that reservation covers its initial work.
The sparse backend then enforces its own actual schedule reservations.
Later budget exhaustion remains a valid certificate refusal.
The ceiling does not guarantee numerical acceptance.

The primal route reserves the backend's declared complete structural schedule.
Its own workspace and work checks remain active.
No automatic cross-certificate retry occurs.

A refused certificate can trigger exact retained replay.
The service first admits and reserves the complete point solve.
A point refusal therefore starts no fallback neural replay.
A numerical point failure returns no model or state.
Its diagnostics preserve reservations, attempted solve counts, and replay work.

Fresh preparation preflights every point stage before feature extraction.
It uses the same `AdaptiveFixedAnchorService` and point policy as compatible reconstruction.
Singleton boxes use that same admitted point dispatch.
Empty deletion histories retain normal provenance checks.

The service checks a separate box-assembly allowance before descriptor decoding.
The allowance includes multiple decoded and assembled feature arrays.
It does not establish a whole-process memory bound.
Decoder context, allocator behavior, compiler memory, and resident state require an external process cap.
Work proxies do not replace an external CPU or wall-time cap.

## Preserved evidence and state

The service retains all V28 checks for these properties.

- Model target, grid, order, and canonical scales.
- Codec precision, block size, and current codec binding.
- Decoder, provider, anchor, and preparer identities.
- Retained membership and record tokens.
- Source hashes and containment during replay.
- Complete ancestor traversal when a late stage needs replay.
- Canonical retained descriptors and serialized state.

Replay checks ancestors even when their earlier certificates passed.
Replay scratch never changes retained descriptors.
Repair and indexed reconstruction use identical information and numerical routes.
Each accepted result contains every calibrated stage.
A partial result never becomes a returned model.

## Verification

```bash
python -m unittest tests.test_adaptive_compressed_v30 -v
```

Twenty-one software fixtures cover state equality, every route, fresh preparation, fallback, and canonical deletion histories.
They also cover cumulative limits, early refusal, source hashes, containment, and full-deletion provenance.
They verify that malformed certificates cannot trigger fallback.
They verify that point failures preserve their spent-work diagnostics.
Fresh numerical failures retain cumulative reservations and nested exact-service receipts.
Missing receipts leave observed work unknown.

The fixtures use small exact decoder constructions.
They are software tests, not empirical datasets.
The service has no new full-model timing result in this document.
Model quality, reliable speed, and realistic workload scale still require registered experiments.
