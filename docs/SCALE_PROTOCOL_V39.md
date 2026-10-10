# Prospective real-data scale pilot

Registered design date: 10 October 2026.
No V39 empirical result existed when this protocol was written.
This is a development pilot, not prospective confirmation.

## Question and scope

Does the cached-feature advantage survive stronger controls when retained tokens approach or exceed the layer width?
Does a shared feature-space certificate improve the token-space solver?
Can lower descriptor precision provide useful storage savings after fallback costs?

The target uses fixed nearest-anchor features and the original normalization.
It differs from ordinary sequential calibration.
The pilot covers the first complete QKV stage of DistilGPT2.
That stage has 2,304 rows, width 768, and 1,769,472 four-bit codes.
First-stage inputs match the fixed target before any calibrated projection.
This experiment does not establish full-model speed, quality, or state correctness.

## Real inputs

Use the pinned DistilGPT2 checkpoint from the existing recovery helper.
Use the pinned WikiText-2 raw training parquet and tokenizer in `research_v39/data.py`.
Verify every download against its registered byte count and SHA-256 digest.
Never replace a conflicting local file.

Use the existing article parser and development partition.
Exclude articles whose `phase-v1` hash has residue zero modulo five.
Those articles remain reserved for confirmation.
Sort eligible articles by the existing `pilot-order-v1` hash.
Take the first thirteen distinct 128-token chunks.
Use published article-body concatenation, without BOS or EOS tokens.
Do not pad, repeat, or synthesize observations.
Publish exact selected token IDs before any model worker.
Some selected articles were exposed during earlier development.
Do not call these independent roots or untouched confirmation data.
All sixty exposed quality articles remain excluded from quality confirmation.

The original root contains 1,664 tokens.
Three alternative requests retain the first 1, 6, and 12 selected records.
The retained counts are 128, 768, and 1,536 tokens.
Normalization remains 1,664 for every request.
These requests do not form a successive deletion sequence.
The ridge is 1/100.
The grid uses the existing base-only dyadic scales and tie rule.

## Methods

| Arm | Inputs and work |
|---|---|
| `gram_delete` | Load the exact original Gram. Regenerate deleted features, subtract their exact Gram, and certify. |
| `gram_fresh` | Regenerate retained features, form their exact Gram, and certify. |
| `cached_token` | Decode retained lossless features and run the existing token-space solver. |
| `cached_primal` | Decode retained lossless features and run the new shared feature-space certificate. |
| `compressed_48` | Decode 48-bit boxes, certify, and use the registered point fallback on numerical refusal. |
| `compressed_32` | The same policy at 32 bits, only for the 768-token request. |
| `compressed_40` | The same policy at 40 bits, only for the 768-token request. |

All methods use the same native ball row kernel.
The Gram and primal methods also share the same residual coefficient verifier.
Unresolved Gram or primal rows receive the mandatory interval fallback.
Every required pass is included in admission and timing.
No partial code array qualifies as a completed arm.

The compression route uses token-space certification below width 768.
It uses feature-space certification at or above that width.
A declared numerical refusal triggers fresh retained-feature generation and point solving.
The point fallback uses the same fixed threshold.
Include certificate failure, replay, and point solving in that arm's latency.
Preserve failures even when a later registered arm succeeds.

The Gram deletion control may access deleted raw tokens before their removal.
The fresh control may access retained raw tokens.
This is a favorable access allowance for those controls.
Raw token access and checkpoint availability are external to the reported representation payload.
Do not call that payload the total persistent service state.

## Preparation and measurement

One preparation worker generates thirteen real first-stage feature blocks.
It verifies lossless roundtrips and containment for all three compressed precisions.
It constructs the exact pooled Gram with source commitments.
It preserves preparation times and representation byte counts.
Preparation does not quantize the original complete model.
Thus no preparation-inclusive lifetime advantage can follow from this pilot alone.

The arm order is fixed by the published SHA-256 seed.
There is one observation per arm and retained size.
There is no outcome-based order selection or retry.
The OS cache is uncontrolled.
All arms share one checkpoint load and native compilation within each request worker.
Record those shared costs separately.

Each arm clock includes input loading, decoding, replay, solving, verification, diagnostics, and output writes.
Output files and parent directories are flushed before the clock stops.
Cross-arm comparisons and worker receipts occur after the arm clocks.
Report their scope separately.
Do not sum overlapping clocks.

Representation payloads include every retained descriptor or exact Gram, stage codes, and stage metadata.
They exclude the common base checkpoint, raw input tokens, and audit files.
Report the exclusion beside every storage comparison.
Fallback does not silently replace the stored representation with a lossless cache.

## Verification and outcomes

Require identical actual bytes for the deleted and freshly formed retained Grams.
Require identical actual packed code bytes across all completed methods.
Audit the complete stage extent.
Audit descriptor hashes, source commitments, target identities, plans, receipts, and all terminal copies.
Audit actual binary files before the temporary runner ends.

A scientific refusal is an outcome, not a code match.
Return no speed ratio if either arm lacks complete certified output.
Runtime, allocation, compiler, identity, or integrity errors stop dependent work.
The classifier recognizes only explicitly registered numerical refusal messages.
Unknown exceptions remain fatal.

Preserve every arm's latency, status, replay count, certificate decision, fallback cost, and payload bytes.
Report prespecified Gram/token, Gram/primal, token/primal, and cache/compressed ratios.
No confidence interval or reliable population speed claim is supported by this pilot.
No automatic full-model expansion follows a favorable result.
An adverse result requires a new reviewed design before another empirical attempt.

## Resource and execution policy

Run once on a standard public GitHub `ubuntu-24.04` runner.
Use one pinned CPU and one numerical thread per worker.
Each worker has a 6-GiB address-space limit.
The workflow has a 60-minute wall limit.
Use no paid compute, paid artifact storage, or dependency cache.

Data selection has a separate 122-second CPU allowance.
Its worker limit is 120 seconds, with a 122-second reservation.
The model phase has a separate 2,400-second CPU allowance.
Preparation has a 240-second limit and a 242-second reservation.
Each of three request workers has a 700-second limit and a 702-second reservation.
The complete planned model reservations total 2,348 seconds.
Allowances are not observed usage.
Software fixtures, downloads, controller audits, and publication costs are outside those ledgers.
Record bounded fixture and audit costs separately where observed.
Do not claim total infrastructure cost.

Publish a one-use claim before setup.
Publish the runtime-bound registration before data selection.
Publish selected data and preparation results before dependent work.
Publish each settled request before starting the next request.
A failed push stops all later work.
No force-push, rerun button, automatic retry, or reused attempt path is allowed.
If settlement is lost, retain the full affected phase allowance as a hold.
Never infer observed CPU use from that hold.

Git preserves sources, selected tokens, registrations, receipts, diagnostic records, and binary hashes.
Derived binary files remain on the temporary runner and disappear when it ends.
Hashes alone cannot reconstruct historical binaries.
All earlier incidents, numerical results, and ledgers remain unchanged.

## Promotion rule

Treat this pilot as a mechanism and implementation gate.
Check whether shared primal solving improves the high-token regime.
Check whether exact Gram maintenance becomes competitive as deletion size falls.
Check whether compression savings justify complete fallback costs.
Use those results to select stronger full-model controls prospectively.
Full-model comparison, successive states, lifetime costs, another model, and independent confirmation remain mandatory.
