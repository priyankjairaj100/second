# Research decision: continue a bounded validation round

Updated 9 October 2026. This is a scientific assessment, not a claim of publication readiness.

The direction is worth further targeted testing.
It is not yet strong enough for a broad ACL empirical claim.
Prioritize tests that could disprove the central advantage before expanding the experiment matrix.

## What the current evidence establishes

The completed WikiText program uses DistilGPT2, two 128-token calibration records, and two alternative source deletions.
It quantizes all 24 calibrated stages, containing 42,467,328 integer codes.
The target uses fixed nearest-anchor features, with original normalization retained.
It differs from sequential GPTQ-style calibration.

| WikiText request | Repair seconds | Matched cold seconds | Observed cold/repair |
|---|---:|---:|---:|
| Lossless, deletion 0 | 76.827684 | 143.550496 | 1.868474 |
| Lossless, deletion 1 | 81.747090 | 146.184273 | 1.788250 |
| Compressed, deletion 0 | 133.959649 | 143.550496 | 1.071595 |

`campaigns/independent_wikitext_v32/analysis-v33.json` verifies the actual complete output bytes against paired cold models.
Both deletion directions change millions of original codes: 3,476,274 and 3,517,787, respectively.
Thus these are not unchanged-output shortcuts.
Lossless repair avoids every retained neural traversal.

The second cold trial uses one independently reviewed terminal-copy recovery.
Its original strict three-copy guard remains failed and disclosed.
Excluding that entire pair leaves the first lossless ratio of 1.868474.
It does not affect the compressed comparison, which uses the first cold trial.
The two requests share one original state; their geometric mean of 1.827922 is descriptive only.
One timing per method and request does not establish a latency confidence interval.

Compressed repair stores 48,054,254 bytes, versus 50,892,156 bytes for lossless repair.
That saves 5.5763% of service state, or about 0.70% after including the shared base checkpoint.
It remains substantially slower than lossless repair.
Its 23 accepted stage certificates leave one stage requiring eight retained neural traversals.
That explains why the earlier 1.5509-fold compressed pilot advantage shrank on this request.
It does not establish that the implementation is optimal or that all latency variation is caused by replay.

Reported times use the registered controller boundary.
They exclude prerequisite/bootstrap checks and post-receipt agreement, gate, and archive analysis.
Preparation costs 287.716526 seconds; conversion adds 59.740614 seconds.
No new first-request or changing-state lifetime advantage follows from these request timings.
The historical first compressed-request lifetime comparison loses.

## Strongest defensible positioning

**Certified exact calibration-code recovery from compressed feature enclosures, with bounded exact fallback.**

The interesting contribution is recovering exact discrete outputs from uncertain stored features.
Frozen features, additive statistics, and caching provide supporting machinery.
They cannot alone support a strong novelty claim.
The current method offers a storage–latency tradeoff, rather than dominating every comparator.

The theory is conditional on valid feature containment, sound universal certificates, and exact fallback within budget.
It does not guarantee unconditional wall-time speedup.
It does not erase knowledge learned during pretraining.
The original sequential-target repair remains slower than cold reconstruction.
The fixed-target results do not resolve that negative result.

Held-out quality gates passed on 40 previously selected articles.
That supports bounded-pool quality preservation, not superiority or broad corpus generalization.
All 60 exposed quality articles remain excluded from prospective confirmation.

## Tests that should decide further investment

1. Finish the already registered C4 root without changing samples, precision, budgets, or thresholds.
2. Implement the exact pooled-Gram comparator under the same target and explicit data-access contract.
3. Run one materially larger complete-model calibration workload with paired repetitions and full preparation costs.
4. If those results justify expansion, add another model and a changing-state deletion sequence.
5. Freeze the method before independent prospective confirmation and finalize direct comparisons with closest prior work.

These are ordered research priorities, not newly registered statistical acceptance thresholds.
Any future thresholds must be fixed before the corresponding outcomes are observed.
Do not choose a threshold retrospectively to preserve a positive narrative.

If compressed certification loses to stronger compatible controls, reconsider the systems-speed claim.
A narrower certificate/theory paper may remain viable if its theorem is distinct and empirically informative.
If practical workloads repeatedly trigger expensive replay, broadening datasets alone will not resolve the mechanism.
Keep the negative cases: they identify the boundary that the theory and algorithm must explain.

## Current completion boundary

WikiText has seven settled successful transactions, charging 927 CPU seconds.
C4 has two successful numerical transactions and one infrastructure failure, charging 429 CPU seconds in total.
The resumed first repair stopped before model computation because `/proc/self/maps` is unavailable.
Its four later trials remain unstarted; no C4 repair speed result exists.
The preceding terminal-copy discrepancy and its reviewed recovery remain disclosed separately.
The runtime failure does not count as scientific evidence against the algorithm.
It also does not permit claiming that C4 experiments completed.

The current execution surface cannot provide the required deep runtime manifest.
Continue numerical work in a correctly preflighted Linux environment with a fresh registration.
Preserve all earlier failed and successful attempts.
The full research program and ACL submission are incomplete.
