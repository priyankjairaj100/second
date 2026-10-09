# Revision 37: stronger full-stage pooled-Gram control

This is an adaptive development experiment following the revision 36 timing diagnosis.
Revision 36 remains preserved, including its slower generic interval row verifier.
No previous registration, numerical source, result, or CPU ledger is changed.

## Fixed scientific scope

Use the same two archived WikiText records, with 128 tokens per record.
Delete article-row-17380 and retain article-row-22925.
Use all 2,304 output rows and all 768 coordinates of `block.0000.qkv`.
Each successful arm must reproduce all 1,769,472 archived four-bit codes exactly.
The original normalization remains 256 and ridge remains 1/100.
The features use the established fixed nearest-anchor target, rather than sequential GPTQ calibration.
No neural feature generation is rerun or newly attested.

The input is the existing revision 36 sharded capsule.
It includes complete first-stage weights and retained reference codes.
Its descriptor inputs are the authenticated revision 35 feature capsule.
The registration binds the complete file dependency closure.
A fresh clone can reproduce this stage without downloading the complete checkpoint.

## Compatible algorithm change

Exact Gram formation, source commitments, subtraction, and coefficient enclosures remain unchanged.
The direct-Gram solver uses the RN ball row verifier already available to cached-feature reconstruction.
The new adapter represents its coefficient proof using identity features and conservative norm bounds.
An unresolved ball row receives the existing interval row verifier using the same coefficient enclosures.
Every conversion, bound, row attempt, and fallback remains charged.
An approximate or partially certified code array is never committed.

This change strengthens the comparator before interpreting earlier latency differences.
It is not an independent confirmation study or a new novelty claim for RN arithmetic.
The numerical proof and focused fixtures accompany `research_v37/direct_gram_ball.py`.

## Registered arm order and clocks

The single worker runs the following fixed sequence:

1. Prepare and serialize the original pooled exact Gram.
2. Load that Gram, decode deleted features, accumulate their contribution, subtract, serialize, solve, and write codes.
3. Decode retained features, independently accumulate and serialize the retained Gram, solve, and write codes.
4. Decode retained features and run the established native token-space quantizer.

Every arm decodes its required feature descriptor anew.
Common input verification, capsule parsing, and native compilation are measured separately.
Arm totals include code verification, diagnostic dataclass conversion, and durable output writes.
These boundaries match revision 36; revision 35 excluded diagnostic conversion from arm totals.
OS cache state is uncontrolled, and one fixed-order observation provides no latency confidence interval.
Descriptive within-run ratios are permitted only for completed arms.
No complete-model, neural-replay, lifetime, population, or generalized superiority conclusion follows.

## Failure and admission rules

A new phase permits at most 900 charged or reserved worker CPU seconds.
Its one worker has an 880-second CPU limit, 1,100-second wall limit, and 3-GiB address-space limit.
The old allowances remain separate and unchanged.
The exact-Gram budget and direct solver budgets are checked before numerical work.
The direct budget includes the extra RN-bound representation and possible interval fallback.

Known numerical certificate refusals produce no codes and do not suppress independent arms.
Execution completion is distinct from passing the all-arm exactness gate.
Refusal timing is an incomplete certificate attempt, not complete reconstruction latency.
No speed ratio is defined using a refusal time.
Unknown, integrity, compilation, runtime, allocation, and resource failures stop the worker.
No automatic retry, data replacement, or outcome-dependent expansion is allowed.

Terminal verification checks actual packed output bytes against the archived full-stage reference.
It independently verifies the declared refusal class and message.
Repaired and independently reconstructed exact Gram bytes must also agree.
The complete attempt, failed outcomes, source inventory, and CPU receipt remain archived.

## Reproduction commands

Run these only after the numerical review and source freeze:

```bash
.venv/bin/python scripts/launch_gram_ball_stage_v37.py --register
.venv/bin/python scripts/launch_gram_ball_stage_v37.py --execute
.venv/bin/python scripts/launch_gram_ball_stage_v37.py --status
```

For a fresh local reproduction, add a new `--campaign local_runs/gram-ball-stage-001` to every command.
Never reuse a campaign containing an attempted worker.
