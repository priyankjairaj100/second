# Native Gram and streamed scale results: V40

Updated 10 October 2026, after successful workflow completion and local metadata audit.

All twelve complete-stage outputs match exactly.
Native exact accumulation passes all thirteen source archive comparisons against the Python reference.
Both 40-bit streamed certificates accept without retained neural replay or fallback.
The strongest representation depends on the workload.
This closes the native-control and streamed-stage pilot, not the complete research program.

## Evidence

- Workflow: https://github.com/priyankjairaj100/second/actions/runs/38025361543
- Source commit: `2ba58fcb4e7c8f9e81441f4d2b445bd92e6db717`.
- Registration publication: `43dad849eb61b53b43a6f0c47d58b1babd27ad93`.
- Final workflow evidence: `6a7ba25e1a2c11f39377b7a60e492834475ffcd7`.
- Campaign: `campaigns/ci_native_scale_v40`.
- Analysis: `campaigns/ci_native_scale_v40/analysis.json`.
- Local metadata audit: `validation/native_scale_metadata_audit_v41.json`.

The run finished successfully at 04:58:36 UTC.
All four workers and both new ledgers are settled.
No empirical worker remains active at this checkpoint.
Do not rerun the workflow or reuse any registered attempt.

## Design and exactness

The pinned DistilGPT2 checkpoint and real WikiText development selection match V39.
Thirteen articles contribute 128 tokens each.
Two alternative requests retain six or twelve records, giving 768 or 1,536 tokens.
Original normalization stays 1,664, ridge stays 1/100, and fixed base-only grids have four bits.
The target remains fixed nearest-anchor calibration.
The experiment covers the complete first QKV stage and all 1,769,472 codes.
It does not cover all 24 stages or ordinary sequential GPTQ.

All six arms at each size emit identical actual packed codes.
The three retained Gram archives also match byte-for-byte at each size.
Native and Python source archives match for every one of the thirteen source records.
Lossless roundtrips and compressed containment pass during preparation.
The local audit also matches code commitments against the same-target V39 results.
That cross-run commitment check does not turn timing differences into controlled treatment estimates.

## Complete outcomes

Every row below is certified, exact, and complete for the declared stage.
Neither compressed arm invokes fallback.

| Retained tokens | Arm | Elapsed seconds | Representation bytes | Replayed stage-record pairs |
|---:|---|---:|---:|---:|
| 768 | `gram_delete_python` | 54.093523 | 6,255,273 | 7 |
| 768 | `gram_delete_native` | 30.136403 | 6,255,273 | 7 |
| 768 | `gram_fresh_native` | 28.041308 | 6,255,272 | 6 |
| 768 | `cached_primal` | 23.020064 | 5,071,731 | 0 |
| 768 | `streamed_primal` | 23.571555 | 5,071,731 | 0 |
| 768 | `streamed_compressed_40` | 25.387995 | 4,045,355 | 0 |
| 1,536 | `gram_delete_python` | 22.515107 | 6,256,852 | 1 |
| 1,536 | `gram_delete_native` | 18.835432 | 6,256,852 | 1 |
| 1,536 | `gram_fresh_native` | 40.863567 | 6,256,851 | 12 |
| 1,536 | `cached_primal` | 34.310553 | 9,205,544 | 0 |
| 1,536 | `streamed_primal` | 34.576271 | 9,205,544 | 0 |
| 1,536 | `streamed_compressed_40` | 36.965634 | 7,152,668 | 0 |

Each arm includes loading, replay, accumulation, certification, diagnostics, and output.
Shared checkpoint and target construction and native builds are separately recorded.
Actual cross-arm comparisons, receipt processing, and publication are outside arm clocks.
No ratio in this table is a complete-service or lifetime speedup.

Representation bytes include retained descriptors or the exact Gram, stage metadata, and packed codes.
They exclude the base checkpoint, raw tokens, audit files, and temporary working storage.
They are not total persistent service state.
The one-byte difference between Gram deletion and fresh construction comes from metadata filename lengths.
Every arm has the registered raw-input and checkpoint access.
Gram deletion regenerates deleted contributions; cached arms read retained descriptors.
Future comparisons must keep this access contract explicit.

## What improved

Across preparation, native source accumulation takes 9.397484 seconds versus the reference's 54.821483 seconds.
Their ratio is 5.833634.
This component ratio does not measure complete repair or preparation speedup.
Preparation also runs both implementations and compares archives as a verification cost.
Its complete worker time is 106.692581 seconds.

Native deletion beats Python deletion by 1.794956 times at 768 retained tokens.
At 1,536 tokens, the ratio is 1.195359 because only one source is deleted.
The smaller benefit is consistent with less deleted-source accumulation, but the single observation does not identify causal components.
The optimized control must remain in all compatible future comparisons.

The streamed primal path reproduces exact codes at both sizes.
Its latency is 2.3957% higher than concatenation at 768 tokens and 0.7744% higher at 1,536 tokens.
Its value is the bounded-block working-set construction, not a demonstrated speed improvement.
Its explicit workspace envelope does not grow with total tokens when block size and stage shape are fixed.
This does not prove a complete-service memory saving.

## Compression frontier

At 768 tokens, 40-bit compression saves 20.2372% of payload versus cached primal.
Its latency is 10.2864% higher.
Against native Gram deletion, it has 15.7564% lower latency and 35.3289% smaller payload.
Cached primal is still the fastest measured arm.
Thus compression offers a payload/latency tradeoff against the fastest control.

At 1,536 tokens, native Gram deletion is the fastest measured arm.
It takes 18.835432 seconds versus compressed repair's 36.965634 seconds.
Compressed repair takes 1.962558 times as long and has 14.3174% larger payload.
Native Gram therefore dominates this compressed arm on both declared axes.
Against cached primal alone, compression saves 22.3004% payload with 7.7384% higher latency.
That narrower comparison cannot replace the stronger Gram control.

These observations reject a universal compression speedup claim.
They motivate a stage-specific representation policy, with the same choices available to every comparator.
A hybrid policy alone would be an engineering improvement, not an established novel contribution.
The remaining candidate is exact discrete-code recovery from uncertain evidence with useful complete costs.

## Accounting and audit limits

The data phase charges 4 of 122 CPU seconds.
The model phase charges 506 of 1,700 CPU seconds.
Preparation charges 108 seconds; the two requests charge 197 and 201 seconds.
These charges include measured child CPU and the registered settlement rule.
Setup, software fixtures, publication, and read-only analysis remain outside empirical ledgers.
Historical sources, ledgers, unresolved holds, and all sixty quality exclusions remain unchanged.

The temporary CI runner audits actual output files before shutdown.
The local audit verifies 132 published text files and 193 registered source/control files.
It also checks receipts, command bindings, terminal copies, ledgers, payload byte accounting, and derived ratios.
Forty-six derived binary artifacts are absent locally.
The local audit therefore reports binary re-verification as incomplete.
Published hashes and recorded CI comparisons are not a substitute for a fresh numerical reproduction.

There is one development observation per arm and retained size.
There are no population confidence intervals, independent experiment roots, or quality results from this pilot.
The requests are alternatives from one original state, not a successive sequence.
Canonical complete successor states and lifetime benefits remain unmeasured.

Read `RESEARCH_DECISION_V41.md`, `FULL_MODEL_ADMISSION_V41.md`, and `CLAIM_BOUNDARIES_V41.md` before expansion.
