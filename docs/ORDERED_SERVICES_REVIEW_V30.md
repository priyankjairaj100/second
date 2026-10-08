# Independent ordered service review

The reviewed services have no remaining blocker within this review scope.
The review compares the new services with their reviewed adaptive equivalents.
It also checks the lossless wrapper against its historical implementation.

| Source | Reviewed SHA-256 |
|---|---|
| `src/ordered_fixed_service_v30.py` | `b9d7509392fab8cc78952af1329ba37bf3254a90a6e73dd542e8f01db9a91c0d` |
| `src/ordered_lossless_service_v30.py` | `20f804381cefdaf55a9fff125de696bba188d8436478e15824eae2071712329c` |

The decoder's separate numerical review appears in `ORDERED_DECODER_REVIEW_V30.md`.
No empirical worker ran during this service review.

## Preserved target and new preparation identity

The fixed service requires the explicit ordered decoder type.
Preparation and model-only reconstruction use its ordered feature generator.
Both install the fixed nearest-grid ancestor matrices from the same context.
They do not install newly calibrated ancestor outputs.
The mathematical target therefore remains the existing fixed-feature target.

The shared adaptive point dispatcher retains target weights, scales, ridge, and original normalization.
It receives the same canonical retained record order.
The independent fixtures compare its actual feature bytes and arguments across fresh preparation, cold reconstruction, and decoded repair.
All comparisons match exactly.

The new preparer binding identifies the executed preparation sources under a distinct schema.
It includes the ordered decoder and attention sources.
Historical state retains its historical binding and is rejected by the new service.
The ordered binding does not claim that the historical preparation executed.

The state formats remain unchanged.
Within the ordered family, fresh, repaired, and indexed successor states retain canonical equality.
Across implementation families, state bytes can differ because preparation provenance differs.
Complete model equality remains the required cross-implementation comparison.

## State validation

The fixed path validates target, stage order, dimensions, scales, and code grids.
It checks decoder, provider, anchor, and preparer identities.
It requires retained membership to equal the declared deletion result.
Retained token contents cannot change.

The prepared-leaf path requires exact factor leaves and an explicit preparation receipt.
Its envelope checks each leaf's provenance against the current preparation family.
The receipt's external elapsed time is recorded, not authenticated by this service.
Trusted preparation remains a premise.

The lossless path additionally validates the codec binding.
It rejects historical preparer bindings before descriptor decoding.
This check remains active after deleting every record and for an already-empty prior state.
Decoder, provider, and anchor comparisons also remain active for full deletion.
Some comparisons occur after exact reconstruction; failure still prevents any returned state.

Retained descriptor payloads are reused unchanged.
Deleted descriptors are not decoded inside the service.
Canonical input parsing can still inspect all supplied descriptors outside the service timer.
Complete transaction accounting must include that parsing.

## Admission and failure evidence

Every point stage receives structural admission before context preparation or feature traversal.
The selected stage allowances accumulate under one request limit.
The lossless wrapper performs this admission before descriptor decoding.
Empty retained sets still reserve nonzero model work.
The shared dispatcher retains bounded refinement and prohibits cross-route retries after refusal.

One diagnostic gap was found and fixed before source freeze.
The first failed point stage previously left aggregate feature and weight clocks at zero.
Those aggregates covered only completed stages, although the failed stage had already prepared its inputs.

The revised receipt explicitly labels the completed-stage aggregates.
It separately records failed-stage feature, weight, candidate, attempted solver, and whole-stage durations.
It also preserves existing nested solver diagnostics.
The lossless wrapper retains completed decoding and the nested exact-service receipt.
No partial model is returned on numerical refusal.

Preparation exceptions can lack inner service receipts.
Those unavailable details remain unknown rather than measured zeros.
The outer transaction remains authoritative for complete elapsed and CPU accounting.
Structural allowances are not observed CPU use or whole-process memory guarantees.
External process limits remain necessary.

## Independent verification

Four new independent fixtures accompany the fifteen existing service fixtures.
All nineteen passed in a reported 1.225 seconds.
That duration is software test output, not an empirical performance result.

The independent fixtures verify:

- Identical actual solver inputs across fresh preparation, cold reconstruction, and retained-factor repair.
- Upfront admission for empty requests before context construction or descriptor decoding.
- Separate completed-stage and failed-stage accounting after a later numerical refusal.
- Rejection of an already-empty historical state before decoding.

Run the focused checks with:

```bash
python -m unittest tests.test_ordered_services_review_v30 tests.test_ordered_services_v30 -q
```

These checks establish software contracts within the documented premises.
They do not establish model-scale speed, broad model quality, or a sequential-target repair advantage.
The registered real-model identity pilot remains necessary before timing promotion.
