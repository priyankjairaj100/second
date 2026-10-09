Current work: read `docs/ACTIVE_SESSION_V35.md` first.
The exact pooled-Gram component is registered; full C4 remains blocked.
Fresh local component commands: `docs/LOCAL_GRAM_PILOT_V35.md`.

---

Current checkpoint: read `docs/ACTIVE_SESSION_V34.md` and `docs/RESEARCH_DECISION_V34.md` first.
WikiText is complete; C4 execution is blocked by a missing required `/proc` runtime interface. Historical status below retains its original cutoff.

---

# Exact calibration-data unlearning for quantized language models

**Resume here:** [START_HERE.md](START_HERE.md).
The V32 recovery handoff contains the current commands, evidence boundary, and remaining work.

This project studies exact calibration removal for a declared fixed-feature quantizer.
The base weights stay fixed. Its target differs from ordinary sequential GPTQ.
The intended venue is ACL 2027; the paper is not submission-ready.

## Current evidence: revisions 30–31

| Result | Verified observation | Scope |
|---|---|---|
| Optimized lossless repair | 1.946–2.213× faster than cold; geometric mean 2.039× | Three timing pairs on one deletion request |
| 48-bit compressed repair | 90.62s versus fastest cold 140.55s; 1.551× | One adaptive pilot; all 24 stages certify without replay |
| 48-bit compressed state | 48,054,240 bytes versus 50,888,817 lossless bytes | 5.570% smaller; shared base checkpoint still required |
| Matched development quality | Perplexity 51.50 versus sequential 52.46 | Eight previously exposed development articles |
| Held-out quality | Perplexity 65.69 versus sequential 66.44 | Forty previously unexposed articles; 5,080 predictions/model |

Complete retained models match across 24 stages and 42,467,328 codes.
The held-out fixed/sequential ratio is 0.9886702.
Its registered one-sided bootstrap guard is 1.0018592, below the 1.05 threshold.
All registered quality guards pass, but quality superiority is not established.
The full-precision held-out perplexity is 57.08; that remaining quality gap stays visible.
All 60 evaluation articles are now excluded from future confirmation.

The smaller compressed state has a cost: lossless repair remains faster at 70.64s.
Fresh 48-bit conversion adds 73.20s to original preparation.
An earlier 40-bit pilot took 312.33s despite a 13.68% state reduction.
Two failed certificates caused full retained replay; its negative result is preserved.
The 48-bit follow-up changes both precision and coefficient execution, so it does not isolate either causal effect.

Read the [current restart guide](docs/LOCAL_LLM_RESUME_V32.md), [evidence status](docs/EMPIRICAL_STATUS_V32.md),
[manuscript](docs/MANUSCRIPT_V30.md), and [novelty audit](docs/NOVELTY_AUDIT_V30.md).
The reviewed V32 recovery controller runs the preserved independent WikiText and C4 programs.
Their actual receipts determine completion; the current status report records the evidence boundary.
Broader models, realistic full-model token scales, changing-state lifetime experiments,
and the pooled exact-Gram baseline remain open.

These results support a narrow storage–latency tradeoff under a fixed-feature target.
They do not establish general sequential unlearning speed or dominance over every baseline.

<details>
<summary>Historical checkpoint text, preserved unchanged</summary>

# Exact calibration-data unlearning for quantized language models

This project targets an ACL 2027 paper.
It removes calibration records while keeping the base model weights fixed.
Each target reruns its complete declared quantizer on retained records.
The original sequential target and the later fixed-feature target are distinct.
The implementation defines a certified numerical target.
It does not claim native GPTQ or CUDA equivalence.

## Current state

Revision 29 adds a complete lossless storage control using the unchanged exact point solver.
All three registered transactions completed with agreeing live progress, sealed receipts, and immutable artifacts.

| Complete transaction | Time | Neural stage-record traversals |
| --- | ---: | ---: |
| Lossless indexed reconstruction | 44.067929996 s | 0 |
| Lossless repair | 49.062973723 s | 0 |
| Cold model reconstruction | 54.443484033 s | 24 |

The observed speedup over cold reconstruction is 1.1096653933× on one adaptive development request.
It does not establish reliable superiority.
Repair and indexed reconstruction share the same algorithm; their observed timings differ, so this is not an empirical tie.
All 24 stages and 42,467,328 model codes match exactly.
The shared model hash starts `d27c8243`, and the successor lossless state hash starts `55a131c6`.
Read the [V29 report](docs/EMPIRICAL_LOSSLESS_V29.md) and [bound summary](campaigns/lossless_summary_v29.json) for complete hashes and receipts.

| Complete retained state | Bytes | Comparison |
| --- | ---: | --- |
| Exact factors | 26,326,066 | Uncompressed reference |
| Lossless factors | 25,832,592 | 1.874469% below exact factors |
| V28 forty-bit enclosures | 24,930,099 | 3.493622% below lossless factors |

Base checkpoint parameters remain required.
V28's earlier 51.232-second timing lies outside this new comparison and supports no causal cross-version speed claim.
V23 retains its earlier repeated 1.298–1.331× exact-factor speedups on the tiny request.
The fixed nearest-grid feature target remains distinct from the original sequential calibration target.

The [model-response lower bound](docs/RESPONSE_LOWER_BOUND_V29.md) separates actual canonical four-bit outputs with positive margins and conditioning at most three.
It proves \(b\ge\lceil\log_2\binom N{N/2}\rceil\) under its declared access contract and also bounds cumulative probes.
It establishes no NLP speed guarantee.
The [scaling audit](docs/SCALING_AUDIT_V29.md) exposes quadratic token storage and potentially cubic preconditioning.
The admission helper rejects a 262,144-token plan requiring a single 512-GiB array.
All eight helper tests pass.
Passing admission does not prove memory fit; the primal certificate is unimplemented.

Thirty-five new V29 fixtures passed.
Next steps include scaling backends, stronger FPC/ALP/Zstandard controls, untouched quality, additional models/corpora, independent requests, and lifetime costs.
The [novelty audit](docs/NOVELTY_AUDIT_V29.md) and [remaining tasks](docs/RESEARCH_TODO.md) define the outstanding research work.
Quality remains two articles and thirty predictions; all twelve evaluated articles remain excluded from confirmation.
The paper is not ACL-ready, and the empirical program remains incomplete.

The latest continuation permitted a separate 240-second phase: 148 used and 92 remaining.
Three registered trials finished; no further trials are registered or active.
Older ledgers remain 10,775 / 10,800 and 898 / 900, including 122 unknown reserved seconds.
Combined charged or reserved usage is 11,821 seconds; no old ledger was reset or pooled.
Older progress discrepancies remain preserved and disclosed.
This checkpoint supersedes older execution and budget language below.
Start with [RESUME.md](RESUME.md).

<details>
<summary>Preserved revision 28 checkpoint</summary>

Revision 28 implements exact complete repair from compressed source-local evidence.
It uses the explicit fixed nearest-grid feature target.
It does not establish faster repair of the original sequential target.

| Complete transaction | Time | Result |
| --- | ---: | --- |
| V27 compressed repair | 90.496 s | Exact model and complete state |
| V28 compressed repair | 51.232 s | Exact model and complete state |
| Matched cold reconstruction | 51.180 s | Exact model only |

Selective verification retries six unresolved rows instead of repeating whole-stage work.
All 24 stages and 42,467,328 model codes match the retained reference.
Repair executes zero neural stage-record traversals.
The retained complete state is 24,930,099 bytes, 5.3026% smaller than exact-factor state.
The common base checkpoint remains required for uncalibrated parameters.

This is a latency tie, not a demonstrated compressed-repair speed advantage.
It is one adaptive development retiming against an earlier same-session cold comparator.
The cold run has contradictory live progress metadata.
Its sealed receipt, completion logs, and verified model support completion; the discrepancy remains disclosed.
Read the [complete report](docs/EMPIRICAL_COMPRESSION_V25_V28.md) and [bound summary](campaigns/compressed_summary_v25_v28.json).

The exact-factor V23 route retains its three observed 1.298–1.331× cold-reconstruction speedups.
Equally indexed reconstruction ties repair because it shares the same information and algorithm.
Those results use a larger saved state and the same tiny DistilGPT2/WikiText request.
They do not establish broad superiority, lifetime benefit, or a compressed-service win.
See the [earlier timing report](docs/EMPIRICAL_TIMING_V23_V24.md).

The [theory stack](docs/FIXED_COST_THEORY_V23.md) states conditional correctness, information, state-output, and lifetime bounds.
The [novelty audit](docs/NOVELTY_AUDIT_V23.md) rules out claiming fixed features or caching alone as new.
The compressed service now supplies universal output certificates and bounded replay fallback.
The [sparse verification argument](docs/BALL_BOX_V28.md) preserves exactness when combining complete certified rows.

Quality evidence still contains only two articles and thirty predictions.
Broader quality, realistic calibration sizes, additional models, independent requests, lifetime costs, and confirmation remain open.
All twelve evaluated articles remain excluded from future confirmation.
The paper and empirical program are not complete.

No empirical worker is running. No further empirical run fits the remaining phase allowance.
The original ledger remains 10,775 / 10,800 CPU seconds.
The separate phase holds 898 / 900 seconds: 776 recorded and 122 unknown reserved.
The allowances are not pooled or reset.
The final focused suite passed all [140 software tests](campaigns/compressed_software_check_v28.json).
Start with [RESUME.md](RESUME.md) and [remaining tasks](docs/RESEARCH_TODO.md).

</details>

## Current implementations

- [Exact lossless state and repair control](docs/FIXED_LOSSLESS_SERVICE_V29.md)
- [Model-response information bound](docs/RESPONSE_LOWER_BOUND_V29.md)
- [Scaling audit and admission limits](docs/SCALING_AUDIT_V29.md)

- [Compressed complete repair with sparse verification](docs/FIXED_COMPRESSED_SERVICE_V28.md)
- [Canonical compressed state](docs/FIXED_COMPRESSED_STATE_V26.md)
- [Wider dyadic enclosure codec](docs/FIXED_FACTOR_CODEC_V26.md)
- [Sparse row certificate and proof](docs/BALL_BOX_V28.md)

- [Complete sequential anchor provider](docs/ANCHOR_TRANSFORMER_V20.md)
- [Canonical sequential anchor service](docs/ANCHOR_SERVICE_V20.md)
- [Explicit fixed-feature target and service](docs/FIXED_ANCHOR_V21.md)
- [Minimal fixed-factor state](docs/FIXED_FACTOR_V22.md)
- [Shared evaluator setup](docs/EVALUATOR_SETUP_V22.md)

- [Canonical compact state](docs/COMPACT_STATE_V13.md)
- [Exact dyadic state encoding](docs/COMPACT_DYADIC_STATE_V15.md)
- [Complete dyadic identity service](docs/DYADIC_COMPACT_SERVICE_V15.md)
- [Complete repair and four comparison methods](docs/COMPACT_SERVICE_V13.md)
- [Finite transformer boxes](docs/FINITE_FEATURE_BOXES_V13.md)
- [Exact codes over feature boxes](docs/TOKEN_BOX_CERTIFICATE_V13.md)
- [Common solver batching](docs/BATCHED_TOKEN_SOLVER_V13.md)
- [Original token-space solver](docs/TOKEN_SPACE_SOLVER_V12.md)
- [Fixed output-row grids](docs/ROW_SCALED_TARGET_V12.md)
- [Fine dyadic row grids](docs/DYADIC_ROW_TARGET_V14.md)
- [Revision 12 diagnostic report](docs/EMPIRICAL_PILOT_V12.md)

## Reproduction

Install `requirements-local.txt` and restore pinned inputs with `scripts/acquire_pilot_inputs.py`.
These certified workers currently use CPU execution.
The commands show dependency order; admission remains subject to the inherited allowance.
Use fresh attempt IDs.
Never overwrite published attempts or reuse their clocks as new observations.
Later validation guards changed source-bound target hashes.
Regenerate preparation and comparators under one source version, or use the exact archived snapshots.

```bash
python scripts/launch_compact_service_pilot.py --revision v15 --grid-axis dyadic_row --solver-backend batched --id replica-001 --method direct_fresh
python scripts/launch_compact_service_pilot.py --revision v15 --grid-axis dyadic_row --solver-backend batched --id replica-002 --method repair --delete-index 0 --prior-attempt replica-001
python scripts/launch_compact_service_pilot.py --revision v15 --grid-axis dyadic_row --solver-backend batched --id replica-003 --method model_only_fresh --delete-index 0
python scripts/launch_compact_service_pilot.py --revision v15 --grid-axis dyadic_row --solver-backend batched --id replica-004 --method indexed_fresh --delete-index 0 --prior-attempt replica-001
python scripts/launch_compact_service_pilot.py --revision v15 --grid-axis dyadic_row --solver-backend batched --id replica-005 --method direct_fresh --delete-index 0
```

Use `--solver-backend batched` equally for every compatible method when comparing that implementation.
The inherited CPU allowance applies across later revision directories.
The launcher rejects overlapping workers and unsettled prior reservations.
Model arrays and complete state arrays remain local.
Published hashes bind those reproducible artifacts.
A fresh clone must regenerate them before using a previous state.

The forty-cell scientific program and its original gates remain in [the empirical plan](docs/LOCAL_EMPIRICAL_PROGRAM.md).
The user authorized execution here after that older local handoff.
Large campaigns require the remaining scientific conditions.
The current identity cache cannot satisfy the changed-ancestor avoidance condition.

</details>
