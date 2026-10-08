# Compressed evidence: exact complete repair and sparse verification

Updated 8 October 2026, UTC.
These results concern the fixed nearest-feature target.
They do not establish faster repair of standard sequential GPTQ.
Every screen reuses one development request on DistilGPT2 and WikiText.
These are adaptive development results, not confirmation or a quality evaluation.
Versions 27 and 28 include complete compressed repair timings.

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

Separate-agent internal source reviews found no blocking defect under the stated preparation premise.
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
Separate-agent internal review cleared its endpoint, center, nesting, and provenance properties.

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

Separate-agent internal review cleared the argument, implementation, and exact rational fixtures.
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

## 8. Complete V27 repair: exact but slower

The registered complete worker loaded and checked its inputs in a fresh process.
It charged checkpoint loading, prior-state parsing, certificate construction, compilation, output, and verification.
The primary clock covers the controller transaction through its sealed receipt and receipt hash.
Input acquisition and controller bootstrap gates precede that clock for both methods.
Worker-body clocks are secondary diagnostics.

| Complete transaction | Seconds | Output |
|---|---:|---|
| V27 compressed repair | 90.496015787 | Model and complete retained state |
| Matched V27 cold reconstruction | 51.180300526 | Model only |
| V28 compressed repair | 51.231991286 | Model and complete retained state |

V27 certified all twenty-four stages without neural replay.
All 42,467,328 calibrated model codes matched the retained reference.
The complete model file and canonical retained state also matched their expected bytes.
However, V27 lost the complete timing comparison.

The expensive fallback repeated whole-stage work for six unresolved rows across four stages.
The affected stages were `block.0000.mlp_up`, `block.0001.mlp_down`, `block.0003.mlp_up`, and `block.0005.attn_out`.
Their unresolved row counts were one, three, one, and one.
V27 spent 65.5925 seconds in certificates, including 27.204 seconds in Python universal fallback.
This finding motivated V28 before any larger experiment.

## 9. Sparse verification without changing the target

V28 keeps every complete row certified by the first ball pass.
It discards every partial output from an unresolved row.
It then retries only unresolved complete rows using cached ridge coefficient evidence.
Each retry preserves the original grid, row identity, and all weight columns.
Preconditioned proposals are built only if those retries still leave unresolved rows.
Python universal verification applies only to the remaining rows.

Rows share feature evidence, but their quantization recurrences remain independent.
Each accepted row certificate holds for every feature matrix inside the same enclosure.
Their conjunction therefore certifies the complete stage on that enclosure.
No union bound or statistical independence assumption is required.
The argument does not permit assembling partial prefixes from failed rows.

Separate-agent internal review checked this composition and the service integration.
Fixtures cover poisoned partial rows, exact rational corners, grid preservation, and global row indexing.
The original native kernels and measured V27 sources remain unchanged.
The V27 and V28 services produce compatible canonical state bytes.
The numerical target, compression cells, and trusted-preparation premise remain unchanged.

A prospectively registered screen selected the previously slowest stage, `block.0001.mlp_down`.
It checked all 768 rows and all 3,072 columns against the validated saved model.
The certificate took 2.369089164 seconds, including coefficient construction and native compilation.
The ball pass certified 765 rows; cached ridge interval verification certified the remaining three.
It needed no preconditioned retry or Python universal fallback.
The complete screen took 4.811922082 seconds and charged five CPU seconds.
This adaptive diagnostic is not an independent timing replication.

## 10. Complete V28 result and limits

The full V28 transaction took **51.231991286 seconds**.
It certified all twenty-four stages and matched the complete retained model and state.
It performed zero neural stage-record traversals, avoiding all twenty-four possible traversals.
Six rows used sparse ridge interval retries.
No row required preconditioning or Python universal fallback.

Certificate time fell to 25.922828312 seconds.
Total service time was 33.294713848 seconds.
Complete transaction time fell by a factor of **1.766396611** compared with V27 repair.
These component clocks do not replace the complete transaction clock.

The cold/V28 time ratio is **0.998991045**.
Repair was 0.051690760 seconds, or 0.101%, slower in this single comparison.
The times are practically close; this is not a statistical equivalence result.
It has no demonstrated complete-model speed advantage.
The comparison uses one adaptive V28 retiming against an earlier same-session cold run.
There are no randomized repetitions or independent requests for this variant.
Repair additionally writes complete retained state; cold reconstruction writes the model only.
We do not subtract that output cost or infer an unmeasured speedup.

| Artifact | Bytes | SHA256 |
|---|---:|---|
| Complete calibrated model | 22,192,646 | `d27c824322d0399f99a78c2b9d7e369e6b9a547085fa1cc25f92703536962927` |
| Complete retained compressed state | 24,930,099 | `6504eb947c23de439f6fd96f2f6b496e606f00032a124cd92bd744a1d8d2ac36` |

Both binary artifacts were reread and their hashes verified after completion.
The exact-factor complete state occupies 26,326,066 bytes.
The compressed complete state therefore saves **5.302603891%** for this retained corpus.
This denominator includes the calibrated model, descriptors, indexing, and framing.
It excludes the common base checkpoint required for uncalibrated parameters.
The percentage is not a total deployment storage reduction.

The earlier exact-factor service retains its repeated 1.298–1.331× advantage over matched cold reconstruction.
Those measurements concern the same tiny development request and a larger saved state.
Equally indexed reconstruction correctly ties repair because it shares the algorithm and information.
V28 does not establish superiority over that stronger comparator.

## 11. Evidence discrepancy and preservation

The V27 cold attempt has contradictory progress files.
Its live file ends at `model_write_started` with status `running`.
Its separately sealed progress reports completion.
The successful controller receipt, receipt-bound completion logs, and matching model bytes support completion and timing.
All six receipt artifact sizes and hashes were verified in a separate-agent internal review.

The discrepancy's cause is unknown.
The raw file remains unchanged, and no missing timing was reconstructed.
See `campaigns/compressed_timing_v27/attempts/cold-001/progress-discrepancy.json`.
This qualification accompanies every use of that comparator.
V28's live and sealed progress files agree.
Historical V23 evidence incidents retain their original disclosures and reserved charges.

Frozen registrations, source snapshots, unsuccessful screens, and unstarted registrations remain preserved.
New verification code uses separate versioned files.
Derived binary arrays stay outside Git; their hashes, generation code, and receipts are published.

## 12. Accounting and verification

The fixed-feature phase has a separate 900 CPU-second allowance.
Its child registrations delegate the remaining allowance; their ceilings are not additive budgets.

| Ledger | Recorded seconds | Unknown reserved seconds |
|---|---:|---:|
| Fixed-feature V23 | 517 | 122 |
| V25b initial screen | 7 | 0 |
| V25c preconditioned screen | 8 | 0 |
| V25d corner probes | 4 | 0 |
| V26b precision screen | 32 | 0 |
| V27 ball screen | 8 | 0 |
| V27 complete pair | 143 | 0 |
| V28 sparse screen | 5 | 0 |
| V28 complete repair | 52 | 0 |
| Total | 776 | 122 |

The phase holds 898 of 900 seconds, leaving two seconds.
The original allowance remains 10,775 of 10,800 seconds, leaving twenty-five seconds separately.
Combined charged or reserved usage is 11,673 seconds.
The allowances were not reset or pooled.
No further empirical worker should launch under this phase allowance.
Archive analysis and software verification have separate, disclosed costs.

The final focused software suite passed all 140 tests.
Unittest time was 5.395 seconds; measured child CPU was 5.601956 seconds.
See `campaigns/compressed_software_check_v28.json` for the exact command and source hashes.
These are software fixtures, not synthetic empirical datasets or quality evidence.

The machine-readable audit is `campaigns/compressed_summary_v25_v28.json`.
Run `python scripts/summarize_compressed_v28.py --verify-artifacts` to rebuild it with local binary verification.
Omit that flag when the ignored binaries are unavailable.
The resulting report explicitly records whether those binaries were reverified.
Neither command runs neural inference or a quantization experiment.

## 13. Research position and next gates

The implemented contribution is compressed source-local evidence with exact output certification and bounded replay fallback.
Sparse row verification makes complete repair practical on this development request.
The current empirical result is exact repair, zero neural replay, modest state savings, and a latency tie.
That combination establishes a useful prototype, not an established Pareto improvement or publication novelty.

The target uses fixed nearest-grid ancestor features.
It is explicitly different from ordinary sequential calibration and standard GPTQ retraining.
The original sequential repair target still lacks a demonstrated complete speed advantage.

Next experiments require a revised prospective protocol and an explicit compute allowance.
They must measure quality, realistic calibration sizes, independent requests, additional models, and additional corpora.
They must include preparation, common checkpoint storage, equally indexed reconstruction, output, fallback, and lifetime costs.
The appropriate scientific question is where compressed evidence improves the storage–latency tradeoff at fixed exactness.
The numerical precision should be selected on development data, then frozen before confirmation.
All twelve evaluated articles remain excluded from future confirmation.

The quality evidence remains two articles and thirty predictions.
It cannot establish preserved language-model quality.
The historical forty-cell program cannot be expanded unchanged after the target redesign.
The empirical program and ACL submission are not complete.
