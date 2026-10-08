# Reevaluation of repair feasibility

Date: 8 October 2026.
Scope: revisions 17, 20, and the completed revision 21 quality screen.
Revision 22 optimizations remain pending validation.

## Conclusion

The audit found useful implementation fixes, but they do not explain away the earlier loss.
The current identity service performs all retained feature work after an early ancestor changes.
The fixed-anchor box route also has a verified obstruction on the checked real record.

The next implemented route therefore changes the calibration target explicitly.
It makes each record's calibration features independent of other records.
This change permits exact retained feature reuse.
The new target passed its small revision 21 quality gate.
Broader model quality and complete repair time still need evidence.

## 1. Revision 17: a real improvement and a remaining loss

The native certificate reduced common quantization cost while preserving exact outputs.
Matched complete reconstruction improved from 194.774 seconds to 71.860 seconds.
Both reconstruction and repair received that kernel.

| Complete transaction | Worker seconds |
|---|---:|
| Native repair | 84.225 |
| Native cold model reconstruction | 71.860 |
| Native warm model reconstruction | 86.100 |
| Native retained model and state reconstruction | 65.853 |

These are single observations, not reliable population timing estimates.
The warm near-tie does not establish repair superiority.
The faster state-producing observation does not establish negative state cost.

All compared revision 17 workers used the same recorded processor and runtime.
The runtime digest was `51af8d7f6901c220fd3e9c0222a60d67b7e12006c81d19fb714adcb906bac553`.
The later processor change cannot explain their original comparison.
The loss audit also verified common solver access and preserved all adverse observations.

Repair executed all 24 retained neural stage-record pairs.
It also read one earlier cached factor.
Its first changed ancestor invalidated every later prefix binding.
The source stream then started from the model input.
Thus, earlier cache reuse did not avoid the final complete traversal.

About 95 percent of candidate codes agreed with the repaired result.
Candidate checks still performed the accumulator recurrence and dot products.
High agreement therefore did not imply saved computation.

Evidence: `pilots/v20/loss-audit.json` and `docs/EMPIRICAL_PILOT_V17.md`.

## 2. Bugs and accounting issues addressed

The revision 20 review corrected five issues before the successful screen admission:

- The caller now supplies a complete ancestor-code tuple.
- The service now retains and sums every record's work counters.
- Singleton boxes now use the selected native or reference solver.
- The provider omits an unnecessary square-root primitive call.
- Affine summaries again check bias shape, finiteness, and binding.

The final focused revision 20 regression passed 42 software tests.
This was not a complete project test-suite run.
These fixes improve correctness and accounting for the new route.
They do not alter the archived revision 17 algorithms or timings.

A separate runtime issue stopped revision 20 attempt 001 before method execution.
The target identity included an earlier Intel processor binding.
The current processor was an AMD EPYC 9V74.
The guard correctly rejected the mismatch.

Attempt 002 used a new runtime-bound target.
It recomputed the first stage, second-stage factors, and second-stage codes.
Those checked values matched the archived values.
This is a bridge for the checked values, not complete target-identity equality.
The program did not bypass the guard.

Evidence: `docs/ANCHOR_REVIEW_V20.md` and `pilots/v20/runtime-change.json`.
Both attempts remain archived.

## 3. Revision 20: the real-data obstruction

The screen used pinned DistilGPT2 and one retained WikiText record with sixteen tokens.
The record was `wikitext2:train:article-row-5326`.
The changed stage was `block.0000.attn_out`.
Its feature bounds used a calibration-independent nearest-grid anchor.

| Screen result | Observed value |
|---|---:|
| Anchor preparation | 22.458859389 seconds |
| Serialized anchor leaf | 31,913,767 bytes |
| First unchanged factor | Exact agreement |
| First changed-stage provider call | Rejected |
| Rejection reason | Primitive result bound overflow |
| Endpoint rows checked | 16 |
| Endpoint code values checked | 12,288 |
| Unequal endpoint codes | 252 |

The provider rejected after approximately 0.135 seconds.
The registered endpoint comparison then completed in approximately 0.224 seconds.
The subset certificate and complete-stage certificate remained unstarted under the stop rule.
No complete repair timing or quality measurement occurred.

The first differing output appeared at row zero, coordinate 148.
The anchor-point code was `0x1.2b32680000000p-2`.
The retained-prefix code was `0x1.c0cb9c0000000p-2`.

This establishes a precise structural result.
Any set containing both checked feature matrices requires at least two quantizer outputs.
Therefore, no sound certificate can prove one constant output throughout that set.
A valid symmetric box centered on the anchor contains both points.
Tightening its radii cannot resolve this contradiction while retaining both points.

This conclusion is separate from the provider's overflow rejection.
Fixing that conservative overflow could improve bound construction.
It cannot remove the two-point contradiction.
The witness does not reject shifted centers or correlated sets that exclude the anchor point.
It also does not establish failure on every record, stage, or deletion size.

Attempt 001 charged 11 CPU seconds before its binding rejection.
Attempt 002 charged 35 CPU seconds and completed its registered screen.
The inherited allowance then had 245 CPU seconds remaining.
No allowance was reset.

Evidence: `pilots/v20/attempt-002/outputs/progress.json` and its worker receipt.

## 4. Revision 21 changes the target

The original target computes later calibration features under earlier calibrated output codes.
Deleting a source can change those codes and every later feature.
The new target instead computes every feature under one fixed nearest-grid anchor.
Calibration records do not determine that anchor.

| Property | Original sequential target | New fixed-feature target |
|---|---|---|
| Ancestors used for calibration | Current calibrated codes | Fixed nearest-grid codes |
| Surviving feature after other records leave | Can change | Unchanged |
| Retained transformer replay | Usually required by current service | Avoided when trusted leaves exist |
| Quantization decisions after deletion | Recomputed | Recomputed |
| Required output equality | Sequential retained rerun | Fixed-feature retained rerun |
| Quality evidence transfers between targets | No | No |

The new service uses a distinct target digest, state type, and state format.
It must not label its output as the original sequential quantizer's result.
Source-local leaves make repeated deletion canonical under the new target.
The numerical solver still computes every stage's retained-data codes.

The first implementation keeps complete anchor leaves.
These include summaries unnecessary for fixed-feature calibration.
Their current preparation and storage costs remain charged.
A smaller factor-only state is a possible optimization, not a current measurement.

An equally indexed reconstruction receives the same trusted retained leaves.
It can run the same algorithm and obtain the same saving.
This expected tie does not invalidate a measured benefit over replay.
It prevents a claim of exclusive superiority over identical access and operations.

Evidence: `docs/FIXED_ANCHOR_V21.md`.
The target-preserving alternative appears in `docs/SHIFTED_TRANSPORT_V21.md`.

## 5. Revision 21 quality screen passed

The registered single variant completed all evaluations without interruption.
It constructed the complete fixed-feature model and complete canonical state.
The model artifact contains 22,192,646 bytes.
The state artifact contains 54,107,392 bytes.
The worker verified the external anchor preparation receipt.

Both models used the same evaluation procedure on two previously unused development articles.
Each model produced thirty predicted tokens across those articles.
The program alternated model order between articles.
The observed perplexity ratios were:

| Evaluation | Fixed-feature / sequential perplexity | Declared maximum | Result |
|---|---:|---:|---|
| Article row 1415 | 0.8828194453522271 | 1.20 | Pass |
| Article row 2188 | 1.091587366682615 | 1.20 | Pass |
| Both articles | 0.9816692689537777 | 1.05 | Pass |

The aggregate ratio uses total matched token loss.
It is not the arithmetic mean of article perplexities.
The fixed-feature model improved the first article and worsened the second.
Its aggregate perplexity was approximately 1.83 percent lower on these thirty predictions.
This is a favorable development observation, not a broad superiority result.
The likelihood calculation itself is not a certified numerical interval.

No variant was retuned using these records.
The two article identifiers remain excluded from future confirmation.
The complete exclusion list now contains twelve identifiers.

The screen reused the revision 20 anchor.
Its prior preparation cost remains 22.458859389 seconds.
The prepared-leaf construction clock excludes that earlier cost.
This route is not an ordinary fresh transaction or a repair timing experiment.

The worker completed in 219.525659611 wall seconds.
It used 219.486291 CPU seconds and charged 220 CPU seconds.
The unchanged 10,800-second allowance then had 25 CPU seconds remaining.
The complete worker included model construction, artifact checks, evaluator setup, and four article evaluations.
Its total cannot establish a repair speed comparison.

The fixed-feature target digest is:
`883ad1f0fae2d361c76e10fba96c240d83b75bf2b38d360e6d3f329a9f675ef6`.
The model artifact digest is:
`d27c824322d0399f99a78c2b9d7e369e6b9a547085fa1cc25f92703536962927`.
The state artifact digest is:
`1e2937e09e9a20f8a3536b6a27620842d13c448928205d9c915959f4f01da142`.

Evidence: `pilots/v21/attempt-001/outputs/progress.json` and its worker receipt.
The result binds plan `524fd91075a40adf32434c63ebc04044d02c433f6ea759dc641fd1a6b372050b`.
The progress digest is `e723525d418280f2fa53381ee3887a1ec9307b50103188e2930781c9f1045d6c`.
The receipt digest is `475e9c418aa03476e5cef439be0b1486a9f1926389cd63f0cee9527d81685d49`.

## 6. Revision 22 optimizations verified in software and archive analysis

The trace exposes substantial setup work unrelated to a measured repair transaction.
The model and state were complete at 46.879306418 elapsed seconds.
The first article evaluation started at 134.660737558 elapsed seconds.
The intervening interval was 87.781431140 seconds.
It included comparator parsing, code conversion, and both prepared evaluator constructions.
The trace does not separate every operation inside that interval.
No controller interrupted the completed worker.

The shared evaluator now skips redundant scalar scans of already validated compact matrices.
Stage and shape checks remain active.
Other representations and subclasses retain the original value validation.
Eight evaluator tests compare exact output bits and validate the shortcut's boundaries.
Every compatible comparator receives the same optimization.

A separate optional backend now stores exact fixed factors without scalar summaries.
The archived complete state shrank from 54,107,392 to 26,326,066 bytes.
That saves 27,781,326 bytes, or approximately 51.34 percent.
All 24 factor byte sequences and every packed model code remained equal.
The target digest remained unchanged.
Fresh minimal preparation also avoids building the unused scalar tape.
Seven focused tests verify its outputs, canonical deletion, and parser boundaries.
The combined final regression passed 49 tests.

The archive audit measures representation size, not repair time.
Neither optimization has new complete-model timing evidence.
See `docs/FIXED_FACTOR_V22.md`, `docs/EVALUATOR_SETUP_V22.md`, and `docs/FIXED_FACTOR_REVIEW_V22.md`.

The small quality gate justifies continuing the fixed-feature track.
It does not justify the full scientific campaign yet.
The next empirical gate needs complete transactions under the new target.
Include cold replay, indexed reconstruction, preparation, state storage, and repeated deletion costs.
Do not compare a partial solver clock with a complete baseline clock.

Broader quality, reliable complete repair speed, and novelty remain open.
The paper needs a useful contribution beyond cached fixed-feature reconstruction.
The present redesign gives a testable route toward that result.
It does not complete the empirical program.
