# Empirical pilot report, revision 10

Date: 5 October 2026.

The user resumed local empirical pilots.
The current full-model implementation did not pass its resource admission gate.
No full-model repair comparison completed.
The diagnostic kernel improved first-block feature execution on two real corpora.

## Results

| Pilot | Scalar worker | Improved worker | Observed ratio | Exact feature agreement |
| --- | ---: | ---: | ---: | ---: |
| wikitext2 | 251.492 s | 56.253 s | 4.471x | 172,032/172,032 |
| c4_bounded_english | 248.524 s | 55.116 s | 4.509x | 172,032/172,032 |

Each method had one observation per corpus.
Each corpus supplied two records with sixteen tokens each.
The diagnostic measured four stage inputs from the first DistilGPT2 block.
The model remained unquantized throughout these diagnostics.
The worker included source checks, selected parameter loading, feature execution, and output.
The worker clock is narrower than the complete repair transaction.
These ratios do not measure repair speed, complete quantization, quality, or lifetime.
No confidence interval or population claim follows from these observations.

All four workers completed within their fixed limits.
Charged worker CPU totaled 614 seconds against the existing 10,800-second allowance.
The scalar workers used approximately 508 MiB peak RSS.
The improved workers used approximately 558 MiB peak RSS.
The improvement therefore has a measured memory cost.

## Diagnosed execution issue

The scalar linear kernel creates Python objects for each product and addition.
The prototype batches independent outputs with NumPy.
It preserves the coordinate order and separates multiplication from addition.
All 344,064 paired feature values matched bit for bit across both corpora.
Certified nonlinear primitives remained unchanged.
The production implementation remains unchanged.
The prototype still needs integration and complete cost evaluation.
See PILOT_KERNEL_ARGUMENT_V10.md for the arithmetic argument and its assumptions.

## Full-model admission failures

Both model configurations failed every tested chart plan.
The plans used four-bit grids, one group, and 32 original tokens.
The chart modes were none, stage-rtn, grid-box, and coordinate.
Even the no-chart reference plan estimated 23.01 GiB for DistilGPT2.
The corresponding GPT-2 estimate was 36.16 GiB.
The worker allowance remains 6 GiB.
These values are planning estimates, not measured allocation or memory lower bounds.
The no-chart estimate still includes reference aggregate storage.
It is not a measured model-only memory requirement.
Other rejected limits include aggregate counts, directions, and GPT-2 grid entries.
No limit was raised to turn these failures into successful runs.
No full-model execution bypassed the existing admission guard.

## Data and scoring checks

WikiText inputs use the pinned raw WikiText-2 repository.
The parser preserves article boundaries and nested headings.
The prepared pools contain 500 development, 110 confirmation, and 60 evaluation articles.
These counts follow fixed length and duplicate filters.
No model result determined the partitions.
The diagnostic roots use a fixed hash order, not a population sampling claim.
The first pilot uses two development articles.
The WikiText source card has conflicting license fields.
The repository contains hashes and short prepared inputs, not the downloaded source corpus.

C4 acquisition used a fixed two-MiB compressed prefix from English training shard zero.
The range contained 2,278 complete records.
Length and duplicate checks retained 1,678 eligible records.
The observed prefix contained no repeated source URLs.
This frame does not represent uniform sampling from all C4.
Final independent C4 pools remain unfrozen.

The English LAMBADA file contains 5,153 examples.
Sixteen fixed examples passed context-target token alignment checks.
Five answers require more than one token.
A last-token-only evaluator would therefore implement the wrong accuracy contract.
The prototype scores every target token and uses complete-word correctness.
Four software tests check this scoring contract.
No model accuracy or likelihood result exists yet.
The pilot identifiers remain excluded from final evaluation.
Underlying book-text permissions remain an explicit release obligation.

## Experiment decisions

Every planned dataset and experiment has a row in pilots/v10/program.json.
All full-model cells remain blocked by the shared execution prerequisite.
The register preserves the admission failures and missing results.
Input checks do not count as scientific wins.
The kernel wins justify further backend development only.
No experiment advances to confirmation.
No certificate coverage, repair gain, quality gate, or lifetime gate passed.

## Required next implementation

1. Replace eager Fraction storage with a bounded representation that preserves exact values.
2. Stream parameter hashing and target serialization without large duplicate structures.
3. Bound exact Gram storage and factorization before attempting a complete model.
4. Integrate the validated linear schedule into all compared methods equally.
5. Recheck complete model outputs and state under the original resource policy.
6. Run deletion pilots, then quality, coverage, complete cost, and lifetime pilots.
7. Freeze new confirmation roots only after the method passes development gates.

The existing conditional theory does not establish that this engineering work will succeed.
The kernel change itself is an implementation improvement, not a novelty claim.

## Reproduction and preservation

Run scripts/acquire_pilot_inputs.py to acquire the pinned inputs.
Use scripts/prepare_wikitext_pilot.py and scripts/prepare_reserve_pilots.py to prepare inputs.
Use the frozen plans with the bounded worker and shared phase ledger.
Never execute the diagnostic worker without its exact command admission.
Run scripts/summarize_pilot_v10.py to verify matching features and recover the diagnostic table.
Plans and receipts contain the original absolute execution paths.
A new location requires new plans and observations.
Archived observations must never become additional timing repetitions.
The worker launcher recipe is recorded in pilots/v10/README.md.

Ten new software tests passed in validation/software_tests_v10.txt.
The previous 524-test result remains historical validation.
The production source files did not change in this revision.
No cloud job or external GPU ran.
