# Revision 16: exact speculative repair fails the CPU pilot

Date: 7 October 2026.

## Decision

Do not promote either speculative backend into the empirical campaign.
Every completed comparison matched its exact sequential reference.
Every completed speculative comparison was slower than that reference.
The block successor reduced sequential continuation, but its verification cost outweighed that saving.
The current reference backend remains the default.

This closes the implementation and diagnostic questions for these two CPU variants.
It does not close the research requirement for useful full-model repair.
No reliable speedup, lifetime advantage, or scientific confirmation is established.

## Methods and provenance

Both pilots used the pinned DistilGPT2 checkpoint and the unchanged fine dyadic target.
Each input contained two real records of sixteen tokens.
Each request deleted the first sorted record identifier.
The measured stage was the first attention input projection, containing 1,769,472 codes.
Its features have no changed ancestors.
Consequently, this experiment does not test downstream feature transport.

WikiText inputs came from the frozen training pilot.
C4 inputs came from the bounded shard-zero prefix.
That prefix does not represent the planned four-shard frame.
No synthetic empirical data or new quality articles were used.

The first program compared one, two, four, and eight whole-row speculative passes.
The successor used one pass within blocks of sixteen, thirty-two, or sixty-four coordinates.
Both methods shared coefficients, certificates, grids, limits, and exact fallback.
Fresh candidates used nearest rounding.
Warm candidates used the original calibrated stage codes.
Original candidate preparation and feature costs appear separately in each progress file.

The second design was registered after observing poor whole-row verification costs.
It remains an adaptive development experiment.
Neither program supplies confirmation evidence.

## Complete outcome table

Ratios divide sequential reference time by speculative solver time.
A ratio below one means speculation lost.
Clocks cover solver calls, including their validation and coefficient construction.
They exclude checkpoint loading, neural features, complete state, and service output.
These are single in-process observations with uncontrolled cache and machine activity.

| Attempt | Dataset | Candidate | Passes | Block width | Status | Seconds | Reference/variant | Verified decisions |
|---|---|---|---:|---:|---|---:|---:|---:|
| attempt-001 | wikitext2 | nearest | 1 | whole | complete | 14.820 | 0.354 | 13.65% |
| attempt-001 | wikitext2 | prior_codes | 1 | whole | complete | 15.009 | 0.349 | 14.33% |
| attempt-001 | wikitext2 | prior_codes | 2 | whole | complete | 26.336 | 0.199 | 31.31% |
| attempt-001 | wikitext2 | nearest | 2 | whole | complete | 35.045 | 0.150 | 29.05% |
| attempt-001 | wikitext2 | nearest | 4 | whole | complete | 44.942 | 0.117 | 55.35% |
| attempt-001 | wikitext2 | prior_codes | 4 | whole | complete | 42.636 | 0.123 | 57.28% |
| attempt-001 | wikitext2 | prior_codes | 8 | whole | complete | 110.102 | 0.048 | 84.93% |
| attempt-001 | wikitext2 | nearest | 8 | whole | complete | 102.224 | 0.051 | 83.88% |
| attempt-001 | c4 | prior_codes | 1 | whole | unstarted | — | — | — |
| attempt-001 | c4 | nearest | 1 | whole | unstarted | — | — | — |
| attempt-001 | c4 | nearest | 2 | whole | unstarted | — | — | — |
| attempt-001 | c4 | prior_codes | 2 | whole | unstarted | — | — | — |
| attempt-001 | c4 | prior_codes | 4 | whole | unstarted | — | — | — |
| attempt-001 | c4 | nearest | 4 | whole | unstarted | — | — | — |
| attempt-001 | c4 | nearest | 8 | whole | unstarted | — | — | — |
| attempt-001 | c4 | prior_codes | 8 | whole | unstarted | — | — | — |
| attempt-002 | wikitext2 | nearest | 1 | 16 | complete | 15.705 | 0.375 | 74.68% |
| attempt-002 | wikitext2 | prior_codes | 1 | 16 | complete | 14.073 | 0.418 | 72.17% |
| attempt-002 | wikitext2 | prior_codes | 1 | 32 | complete | 13.685 | 0.430 | 58.72% |
| attempt-002 | wikitext2 | nearest | 1 | 32 | complete | 12.865 | 0.457 | 60.89% |
| attempt-002 | wikitext2 | nearest | 1 | 64 | complete | 16.509 | 0.356 | 45.28% |
| attempt-002 | wikitext2 | prior_codes | 1 | 64 | complete | 13.937 | 0.422 | 44.06% |
| attempt-002 | c4 | prior_codes | 1 | 16 | complete | 17.871 | 0.314 | 72.15% |
| attempt-002 | c4 | nearest | 1 | 16 | complete | 11.810 | 0.475 | 75.15% |
| attempt-002 | c4 | nearest | 1 | 32 | complete | 12.244 | 0.458 | 61.57% |
| attempt-002 | c4 | prior_codes | 1 | 32 | complete | 12.320 | 0.455 | 58.72% |
| attempt-002 | c4 | prior_codes | 1 | 64 | complete | 21.022 | 0.267 | 43.75% |
| attempt-002 | c4 | nearest | 1 | 64 | complete | 22.495 | 0.249 | 46.25% |

Attempt 001 reached its declared 450-second wall limit.
Its eight WikiText comparisons completed exactly.
Its C4 comparison cells remained unstarted.
The C4 reference preparation was interrupted.
Those missing cells are preserved, not treated as successes or excluded silently.

Attempt 002 completed all twelve comparisons across both datasets.
All twelve outputs agreed exactly with their sequential references.
Across both attempts, twenty completed cells had zero code mismatches.

## Mechanism diagnosis

A verified prefix avoids sequential continuation only.
It does not avoid the candidate scan, certificate calculations, or retained neural features.
The block implementation can recover later correct spans after an earlier changed decision.
That improvement still incurs interval-scan and certificate work for every proposed decision.

For sixteen-coordinate WikiText blocks, the warm verifier took 11.257 seconds.
Its sequential continuation took another 2.173 seconds.
The complete sequential reference took 5.882 seconds.
Thus, even removing the remaining continuation would not make that observed verifier competitive.
This is a diagnosis of this run, not a universal lower bound.

Warm candidates certified fewer block-prefix decisions than nearest candidates in all six matched block settings.
Deleting half this tiny calibration set can make old codes a poor proposal.
That observation must not be generalized to smaller deletion fractions without a new pilot.

The best observed block variant took 12.865 seconds on WikiText.
Its sequential reference took 5.882 seconds.
The best observed C4 block variant took 11.810 seconds.
Its sequential reference took 5.611 seconds.
These descriptive minima are approximately 2.19 and 2.10 times slower.
They are selected development minima, not inferential estimates.

## Implementation completed

- Whole-row directed scans, certified prefixes, and global sequential continuation.
- Block-local scans with sound incoming accumulators and global fallback budgets.
- Common service backends with unchanged numerical target and canonical state.
- A warm model-only control that receives prior codes without calibration factors.
- Separate timing for validation, features, candidates, quantization, packing, and state construction.
- Bound launchers, complete source snapshots, all missing outcomes, and reproducible analysis.

The final focused regression passed 58 tests.
It covered both quantizers, service integration, state encoding, grids, and budget admission.
The log and tested-source hashes are in validation/software_tests_v16.txt and validation/tested_source_sha256_v16.json.
This was not a rerun of the historical full suite.
The new service options passed fixture-level model and canonical-state equality checks.
No complete real-model transaction used these speculative service backends.
Revision 15 remains the latest complete real-model repair result.

## Theory and novelty

Independent review found no remaining defect in the reviewed scan and continuation arguments.
This is mathematical and software review, not proof-assistant verification.
Read SPECULATIVE_QUANTIZER_PROOF_V16.md for arithmetic premises and bounded failure conditions.

The primary-source audit corrected a potential novelty overclaim.
QuIP and YAQA already establish triangular fixed-point formulations and parallel updates.
GPTQ-2D already establishes exact trajectory preservation under valid parallel scheduling.
Those principles are attributed background.
Potential contribution remains in finite-arithmetic deletion certification and complete state guarantees.
Its practical value and priority remain unsettled.

TRANSPORT_DESIGN_V16.md specifies a separate canonical anchor-state candidate.
It remains a design, not an implemented or empirically successful transport service.
It requires a cheap bound-width screen before costly integration.

## Accounting and next gate

Attempt 001 charged 448 CPU seconds.
Attempt 002 charged 235 CPU seconds.
The inherited debit is now 9,823 seconds under the unchanged 10,800-second cap.
The remaining allowance is 977 CPU seconds.
Every worker is settled.
Controller analysis and software tests are outside that worker ledger.

Do not spend the remainder on full-model repetitions of these losing CPU variants.
The next research step must establish a cheaper certificate or useful feature transport.
A new mechanism needs its own prospective small pilot and complete cost comparison.
Ordinary reconstruction must receive all compatible optimizations and a warm model-only control.
The registered feature-avoidance gate remains unmet.

Larger quality evaluation, the two-root deletion sequence, and confirmation remain blocked.
Broader source acquisition and the forty-cell program remain incomplete.
The project still lacks the empirical result needed for an ACL-ready speedup paper.

## Reproduction

Restore pinned files with `python scripts/acquire_pilot_inputs.py`.
Use a fresh attempt ID and the shared inherited budget.
Do not rerun these negative variants merely to generate another timing.

```bash
python scripts/launch_speculative_pilot.py --id NEW_ID
python scripts/launch_speculative_pilot.py --id NEW_ID --program block-program.json
python scripts/analyze_speculative_pilot.py pilots/v16/ATTEMPT_ID
```

Original sources, plans, runtime bindings, receipts, progress, and analysis are archived per attempt.
Large code arrays remain reproducible and excluded from git.
Their hashes and exact comparison outcomes remain published.
