> Historical report through the V27 component screen.
> The complete result is in [EMPIRICAL_COMPRESSION_V25_V28.md](EMPIRICAL_COMPRESSION_V25_V28.md).

# Compressed evidence: implementation and registered development screens

Updated 8 October 2026, UTC.
These results concern the fixed nearest-feature target.
They do not establish faster repair of standard sequential GPTQ.
Every screen reuses one development request on DistilGPT2 and WikiText.
None is confirmation, a quality evaluation, or a complete compressed repair timing.

## 1. Implemented contracts

Version 25 stores complete calibrated codes and source-local compressed descriptors.
Trusted preparation proves that the original factors belong to their stored enclosures.
Hashes bind content; they cannot independently prove containment of unavailable factors.

Repair either certifies the complete stage or reconstructs exact retained factors.
Reconstruction traverses the fixed ancestor chain and verifies every regenerated factor.
Its ledger counts accepted ancestors traversed on the way to a rejected stage.
The service never installs repaired calibrated ancestors during this replay.
Persistent surviving descriptors remain unchanged.
Consequently, valid sequential and combined deletion histories produce the same canonical state.

The service exposes ridge-floor and preconditioned certificate backends.
Both repair and equally indexed reconstruction use the selected backend.
Singleton boxes share the selected exact point solver.
Budget exhaustion returns no completed model.

Independent source reviews found no blocking defect under the stated preparation premise.
These reviews establish implementation readiness, not empirical superiority or publication novelty.

## 2. Actual complete state sizes

The archive audit converted both saved exact factor states.
It performed no neural evaluation or quantization.

| State | Exact bytes | 16-bit bytes | 24-bit bytes |
|---|---:|---:|---:|
| Original, two sources | 30,458,753 | 24,570,153 | 25,602,345 |
| Retained, one source | 26,326,066 | 23,381,811 | 23,897,907 |

The retained reductions are 11.1838% and 9.2234%.
These totals include calibrated model codes, descriptors, indexing, and framing.
The base checkpoint remains required for uncalibrated parameters.

All 144 descriptors passed containment and canonical roundtrip checks.
All 48 retained descriptor comparisons matched byte-for-byte.
Filtering original descriptors and replacing model codes reproduced both independently encoded retained states.
The calibrated model bytes remained unchanged.

The archive process used 31.9198 CPU seconds and 31.8938 wall seconds through its checks.
Those costs exclude the final report write.
They are archive analysis costs, separate from empirical worker ledgers.
See `campaigns/compressed_state_audit_v25/summary.json` for exact timings and hashes.

## 3. Initial precision screen

The first registration was unstarted because an optional reader package was unavailable.
Its files remain under `campaigns/compressed_v25`.
No worker launched and no CPU charge arose there.
The replacement used the existing strict checkpoint reader.

The replacement examined every row and column of `block.0000.qkv`.
Its weight shape was 2,304 by 768.
Its retained factor had 16 tokens and 768 features.
The normalization remained 32 and the ridge remained 1/100.
The deployed weight grid remained four-bit with the saved dyadic row scales.

| Factor precision | Descriptor bytes | Endpoint code differences | Ridge certificate |
|---|---:|---:|---|
| 16 bits | 28,550 | 61 | Unresolved at column 1 |
| 24 bits | 40,838 | 0 | Unresolved at column 22 |

The uncompressed factor occupied 98,304 bytes.
At sixteen bits, valid box endpoints produce different exact model codes.
Therefore, this entire box cannot certify one constant model.
This witness does not reject all compressed representations or token-based recovery.
At twenty-four bits, endpoint agreement establishes no universal positive result.

The complete diagnostic worker took 6.048544091 seconds and charged seven CPU seconds.
See `campaigns/compressed_v25b/attempts/stage-screen-001`.

## 4. Verified preconditioning

For the represented suffix system, directed arithmetic bounds

\[
|I-RG|\le D,\qquad |R(x-Gp)|\le t.
\]

Strict contraction and a verified supersolution establish

\[
\|D\|_\infty<1,\quad t+De\le e
\quad\Longrightarrow\quad |G^{-1}x-p|\le e.
\]

The midpoint inverse supplies proposals only.
Every accepted bound requires the directed checks.
Each quantization decision can use either independently valid coefficient enclosure.
The target and lower-code tie convention remain unchanged.
This is a proved implementation improvement, not a claim of a new general numerical theorem.

On the same twenty-four-bit box, preconditioning advanced the first rejection from column 22 to column 398.
One row remained unresolved there: row 1,916, using zero-based indices.
The preconditioner passed its coefficient verification.
The complete stage remained uncertified.

The ridge verifier took 0.575067032 seconds.
The stronger verifier took 3.442453067 seconds.
These are individual in-worker calls, not independent latency comparisons.
The complete worker took 7.830826249 seconds and charged eight CPU seconds.
See `campaigns/compressed_v25c/attempts/preconditioned-screen-001`.

## 5. Targeted ambiguity diagnostic

A conditional decision gradient proposed two fixed corners for row 1,916 and column 398.
The candidate prefix remained fixed only while forming those proposals.
Each exact point solve retained all 768 weight columns and recomputed its complete row.
Both proposed factors used exact stored endpoints and belonged to the registered box.

Both complete exact rows matched the actual retained model.
Thus, these probes did not establish genuine twenty-four-bit ambiguity.
They also did not prove constancy over the remaining box.
The unresolved result may still reflect loose enclosures or another untested crossing.

The worker took 3.181215 seconds and charged four CPU seconds.
See `campaigns/compressed_v25d/attempts/corner-witness-001`.

## 6. Higher precision and native interval evaluation

The wider codec preserves the numerical target and changes only stored evidence precision.
Its separate format supports sixteen through forty-eight bits.
Independent review cleared its endpoint, center, nesting, and provenance properties.

A native interval implementation also preserves the universal certificate.
Preflight review caught an alignment defect before any empirical execution.
The unstarted registration remains under `campaigns/compressed_v26`.
The corrected replacement resides under `campaigns/compressed_v26b`.

| Evidence precision | Descriptor bytes | Ridge Python | Preconditioned Python | Native interval |
|---|---:|---:|---:|---:|
| 32 bits | 53,126 | Unresolved, 2.890 s | Exact, 5.000 s | Exact, 6.877 s |
| 40 bits | 65,414 | Exact, 3.724 s | Exact, 5.074 s | Exact, 2.853 s |

Every accepted result matched all 1,769,472 saved stage codes.
The thirty-two-bit native route repeated most decisions after its first bound failed.
The forty-bit native route needed one pass.
These call timings share one worker and are diagnostic comparisons.
The exact-factor oracle took 0.666721 seconds, including its initial native compilation.
The complete worker took 31.319159076 seconds and charged thirty-two CPU seconds.
Full-model speed did not follow from this acceptance result.

## 7. Fast ball certification

The next algorithm bounds uncertain-feature accumulation before entering the existing native kernel.
For each previous coordinate, a common bound covers every possible weight-to-grid difference.
A directed prefix sum bounds its product with feature uncertainty.
Adding that bound to the existing accumulator radius preserves both terms in the native proof.
The coefficient certificate still covers every factor inside the box.
The old native C kernel remains unchanged.

Independent review cleared the argument, implementation, and exact rational fixtures.
The forty-bit screen again matched all 1,769,472 stage codes.
It needed no exact point fallback and no Python universal fallback.

The ball call took **0.811531017 seconds**.
The interval call took **2.932714667 seconds** in the same worker.
The exact-factor oracle took **0.719629900 seconds**.
The oracle had already compiled the shared ball kernel, so the ball call paid no new compilation.
These figures justify a complete cold-process pilot, not a complete-model speed claim.
The worker took 7.712491204 seconds and charged eight CPU seconds.
See `campaigns/compressed_v27/attempts/ball-screen-001`.

Version 26 now also has a complete persistent state format.
Its original forty-bit state occupies 27,666,729 bytes, reducing exact-state storage by 9.1666%.
Its retained state occupies 24,930,099 bytes, reducing storage by 5.3026%.
All seventy-two descriptors passed containment checks.
All twenty-four surviving descriptors remained identical.
Complete calibrated model bytes and canonical retained state bytes also matched.
The archive audit used 18.6715 CPU seconds and 18.8033 wall seconds.
Its scope includes artifact writes and checks, but excludes the final report write.
See `campaigns/compressed_state_audit_v26/summary.json`.

## 8. Gates that remain

A single accepted stage can establish useful component correctness.
It cannot establish complete-model repair speedup.
Full repair must charge parsing, verification, compilation, fallback, ancestor replay, and complete output.
It must also beat compatible replay while explaining the comparison with equally indexed reconstruction.

Higher precision requires genuinely stored information.
A coarse descriptor cannot manufacture missing bits.
Version 26 therefore uses a separate format with finer source-local cells.
Version 26 integrates that evidence with persistent complete state.
Complete compressed repair performance remains a separate measurement requirement.

The quality, realistic calibration, lifetime cost, replication, and confirmation gates remain open.
All twelve previously evaluated articles remain excluded from future confirmation.
The paper is not submission-ready based on these development screens alone.
