# Fixed-feature complete-model deletion: first repeated speed advantage

Updated 8 October 2026, UTC.
This report distinguishes measured outcomes, reviewed theory, and unfinished contributions.

## Supported result

Exact fixed-feature repair beats optimized retained-record replay on one small, changed-output DistilGPT2 request.
Three matched complete transactions show speedups from **1.298× to 1.331×**.
Their geometric mean is **1.318978×**.
This establishes pilot repeatability, not population reliability.

The numerical target deliberately differs from sequential GPTQ-style calibration.
All calibration features use calibration-independent nearest-grid ancestor weights.
Retained source features therefore remain unchanged after another source disappears.
The sequential-target losses remain valid and preserved.

## Complete measurements

| Repetition | Repair seconds | Cold replay seconds | Replay / repair |
| --- | ---: | ---: | ---: |
| 1 | 37.156317112 | 49.446033936 | 1.330757 |
| 2 | 37.641630920 | 48.866008389 | 1.298191 |
| 3 | 37.090320491 | 49.264695938 | 1.328236 |

Every repair returns the retained model and complete canonical factor state.
Cold replay returns the retained model only.
Repair wins despite this heavier output contract.
Both methods receive the same native solver and common setup optimizations.

| Control | Complete seconds | Meaning |
| --- | ---: | --- |
| Original preparation | 76.243941018 | Two source leaves, original model, complete state |
| Equally indexed reconstruction | 37.111963761 | Expected tie with repair |
| Complete retained fresh | 50.966114856 | Rebuild retained factors, model, and complete state |
| Warm model-only replay | 52.440547245 | Prior model proposals; no factor index |
| Warm repair | 39.510083006 | Prior model proposals and factor index |

The conservative first-block denominator uses the faster cold/warm replay.
That value is 49.446033936 seconds.
Repair is 24.855% faster on that comparison, passing the registered ten-percent gate.
The indexed/repair ratio is 0.998806.
This expected tie prevents attributing caching benefits to a uniquely superior deletion algorithm.

## Exactness and observed work

- All ten completed retained model artifacts match byte-for-byte.
- All six completed retained state artifacts match byte-for-byte.
- Deletion changes 1,906,485 of 42,467,328 calibrated model codes.
- Repair and indexed reconstruction perform zero retained neural stage-record traversals.
- Model-only replay and complete retained fresh perform twenty-four.
- Original preparation performs forty-eight.
- Every retained model contains all twenty-four calibrated stages.

The compact calibrated model artifact is 22,192,646 bytes.
Original complete state is 30,458,753 bytes.
Retained complete state is 26,326,066 bytes.
State includes its own model payload.
Each stateful worker also exports a separate model; both writes remain charged.
The unchanged base checkpoint supplies noncalibrated parameters.
These artifact sizes do not describe an independently deployable checkpoint containing every base parameter.

Original calibration contains two WikiText articles, sixteen tokens each.
The request deletes one article and retains one.
Normalization remains the original thirty-two tokens.
The grid is four-bit dyadic, with twenty-four significant scale bits and ridge 1/100.
This is a development root, not a representative workload sample.

## Timing scope and reproducibility

The primary clock includes input/source checks, loading, setup, feature work, quantization, and output validation.
It also includes state/model writes, worker exit, receipt publication, and receipt hashing.
Campaign registration, controller bootstrap, prerequisite comparison, and final observer-marker publication are excluded.
Native compilation occurs within every fresh worker process and remains charged.
OS caches and other machine activity are uncontrolled.
One CPU, one requested numerical thread, and six GiB address space were registered.

The first pair used the original controller.
The remaining pairs used an amended controller that archives extra exit evidence before settlement.
Both methods within each repeated pair use the same controller.
No numerical worker code changed.
All frozen numerical sources remain under `campaigns/fixed_feature_v23/source`.

Inspect:

- `campaigns/fixed_feature_v23/program.json`
- `campaigns/fixed_feature_v23/continuation-v24/program.json`
- `campaigns/fixed_feature_v23/summary.json`
- Every attempt's plan, progress, receipt, transaction, and budget entry.
- `scripts/analyze_fixed_timing_v23.py`

Binary models, complete states, and model caches remain untracked.
Their exact hashes and reconstruction recipes are preserved.

## Evidence incidents and accounting

Two evidence inconsistencies interrupted the original campaign.
Their cause remains unknown.
Do not attribute them to numerical code, a collaborator, or the execution platform without evidence.

First, cold-001 progress reverted to an earlier phase after successful completion.
Its sealed stdout retained both terminal events and matched the complete model hash.
A reviewed sidecar recovers terminal metadata without overwriting the raw progress.
Its original outer clock remains available and unchanged.

Second, warm-cold-001 completed numerical output but lost its ledger reservation before settlement.
Its full transaction clock and wait4 CPU measurement are unavailable.
The raw attempt remains controller-incomplete and contributes no timing ratio.
Its complete numerical output matches the retained model.
Its worker-body timer remains a diagnostic only.

The exact evidenced 122-second reservation was restored explicitly.
Observed CPU stays null; that reservation remains permanently charged.
It must never be described as measured usage.
A prospective continuation registered one replacement and the remaining controls/repeats.
No original trial was overwritten or reclassified as complete.

The amended controller saves reservation, logs, and exit measurements before settlement.
Agent filesystem calls were paused during resumed timing as a precaution.
All six resumed attempts retained intact evidence.
This observation does not establish the cause of earlier inconsistencies.

Accounting at closure:

| Scope | Recorded CPU seconds | Unknown reserved seconds | Remaining allowance |
| --- | ---: | ---: | ---: |
| Original pilot allowance | 10,775 | 0 | 25 of 10,800 |
| Separate fixed-feature phase | 517 | 122 | 261 of 900 |
| Combined charged or reserved | 11,292 | 122 | Separate caps remain intact |

The combined charge is 11,414 seconds, including unknown usage conservatively.
Software fixtures, controller work, and archive analysis are outside worker CPU accounting.
Their separate timing reports must not be mistaken for measured model-worker charges.
No paid cloud compute ran.

## Theory and novelty

`FIXED_COST_THEORY_V23.md` gives seven conditional results and an explicit cost model.
An independent review found no remaining blocking algebraic defect under its assumptions.
It does not prove wall-clock superiority, global GPTQ optimality, or broad model quality.

`NOVELTY_AUDIT_V23.md` narrows the paper claim substantially.
Fixed calibration features, summation-form deletion, and generic quantization stability already have close precedents.
Fixed features and caching alone are insufficient central novelty.

The strongest next contribution is compressed, source-local factor evidence with exact output certification.
Its guarantee must include canonical state, fallback ancestor closure, storage, and complete repair cost.
The V24 codec implements only a prerequisite for that direction.
Its passing edge tests do not establish certificate acceptance or repair speed.

The saved-factor audit encoded 144 descriptors across seventy-two source-stage factors.
Containment, nested precision, roundtrips, and forty-eight retained descriptor identities passed.
Actual retained descriptor sizes are 1,184,682 bytes at sixteen bits and 1,700,778 bytes at twenty-four bits.
The raw retained factors occupy 4,128,768 bytes.
Including model, explicit index, and framing gives projected complete states of 23,381,328 and 23,897,424 bytes.
Those are 11.19% and 9.23% below exact state, respectively.
The corresponding zlib-six projection is 26,146,713 bytes.
These are storage projections for an unimplemented service envelope, not measured compressed repair.
The completed archive analysis used 19.741 CPU seconds, outside worker accounting.
Its initial path error remains separately recorded.

## Unclosed gates

The quality screen still contains only two articles and thirty predictions.
Twelve previously evaluated articles remain excluded from future confirmation.
One previous article improved and one worsened; neither result is hidden.

Still required:

1. Integrate compressed descriptors with sound output certificates and exact fallback.
2. Measure acceptance, fallback ancestor closure, and complete costs against exact cached factors.
3. Expand quality using fresh inputs and matched fixed/sequential/nearest/full-precision baselines.
4. Measure index preparation against an original model-only baseline and actual request sequences.
5. Replicate on another corpus, model, calibration scale, precision, and deletion workload.
6. Freeze the final contribution and confirmation design before expanding the forty-cell program.

The research program and ACL paper remain unfinished.
