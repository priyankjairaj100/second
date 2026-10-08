# Fixed-feature complete-model timing protocol

Status: prospective design and implementation review, before any revision 23 timing outcome.
This is an internal review of the current service and proposed experiment.
The executable program must freeze its final choices before its first empirical worker.

## Question and limits

Does the minimal factor service reduce complete deletion latency against optimized retained-record replay?
The numerical target is the explicit fixed-nearest-feature target from revision 21.
This experiment cannot establish speed for the original sequential calibration target.
It also cannot establish novelty, broad quality, or reliable population superiority.

Revision 21's quality screen passed on thirty predictions.
That screen permits this small engineering pilot, not a broad scientific campaign.
Revision 22 preserved exact feature and model bytes while reducing stored state.
Neither revision measured matched complete deletion transactions for the minimal backend.

The existing indexed comparator has the same information and numerical path as repair.
Their expected tie is a fairness control.
Strict superiority over this comparator is not a promotion requirement.
Advantage over optimized replay remains the useful open question.

## Independent budget and frozen inputs

Register a new local feasibility phase with a 900 CPU-second ceiling.
The earlier allowance remains 10,775 charged seconds out of 10,800.
Its remaining twenty-five seconds are not transferred, replenished, or silently consumed.
Record each phase's spending separately and report their sum when reporting total research spending.

Use a single phase ledger outside the historical scanner's per-attempt directory pattern.
The current `inherited_allowance` scans `pilots/v*/attempt-*/phase-cpu-budget/ledger.json` implicitly through its glob.
Putting new-phase ledgers there would incorrectly charge the original allowance.
The new controller must preserve the shared serial research-worker lock.
It must reject live reservations, insufficient allowance, duplicate output paths, and overwritten attempts.

Each worker has one CPU, one numerical thread, and a declared memory ceiling.
Original preparation has a 160 CPU-second and 160 wall-second ceiling.
Each retained worker has a 120 CPU-second and 120 wall-second ceiling.
Admission requires the remaining phase allowance to cover its reservation and settlement policy.
Use actual settled charges for later admission.
Do not expand the phase automatically after a timeout or failed comparison.
Software fixtures and controller preparation remain separately reported non-model work.

Freeze these existing WikiText inputs:

| Item | Value |
| --- | --- |
| Records file | `pilots/v10/wikitext2/preflight-records.json` |
| File SHA-256 | `4073c3352786f3a3fd85ae4e385bc7cb1cefec1a56c5598d9c69bf1976267541` |
| Deleted record | `wikitext2:train:article-row-27113` |
| Retained record | `wikitext2:train:article-row-5326` |
| Original calibration | Two records, sixteen tokens each |
| Request | Delete exactly the first record above |
| Retained calibration | One record, sixteen tokens |
| Model | Pinned local DistilGPT2 checkpoint |
| Arithmetic | Current bound finite decoder and exact native ball solver |
| Grids | Four-bit dyadic rows, twenty-four significant bits |
| Normalization | Original thirty-two tokens, unchanged after deletion |
| Ridge | Exact rational `1/100` |
| State backend | `factors` |

Freeze checkpoint hashes, source hashes, runtime identity, and the complete target recipe.
All compared workers must compute the same current fixed-feature target digest.
Archived target equality is neither assumed nor required.
CPU changes invalidate a matched comparison until a new protocol is registered.
The previous twelve quality exclusions remain unchanged.
This timing phase uses no new quality records.

## Required transactions

Run original preparation first.
It must construct both source leaves directly from tokens.
Do not reuse revision 20's anchor or revision 21's prepared route.
Every subsequent transaction runs in its own fresh process.
All six retained arms start from the same frozen original model and request.

| Arm | Service call | Inputs beyond checkpoint and retained tokens | Returned contract |
| --- | --- | --- | --- |
| Original preparation | `direct_fresh`, two records | None | Original model and complete minimal state |
| Cold replay | `model_only_fresh`, candidates disabled | None | Retained model only |
| Repair | `repair`, candidates disabled | Original minimal state and deleted ID | Retained model and complete minimal state |
| Indexed reconstruction | `indexed_fresh`, candidates disabled | Same original state and deleted ID | Retained model and complete minimal state |
| Complete fresh | `direct_fresh`, candidates disabled | None | Retained model and complete minimal state |
| Warm replay | `model_only_fresh`, candidates enabled | Original factor-free `CompactState` model | Retained model only |
| Warm repair | `repair`, candidates enabled | Original minimal state and deleted ID | Retained model and complete minimal state |

Freeze the first-block arm order in the machine-readable program before launch.
The registered order is repair, cold replay, indexed reconstruction, complete fresh, warm replay, then warm repair.
The warm seed contains no factors or retained feature index.
Its model decoding and loading belong inside its transaction clock.
The exact native solver and compatible optimizations reach every arm.

Candidates are disabled in the primary repair and indexed methods.
Enabling warm replay therefore supplies an additional strong reconstruction control.
It does not permit dropping a faster cold replay result.
Warm repair supplies a prespecified symmetric candidate-enabled comparison.
Report that secondary arm separately from the candidate-disabled primary repair.
Do not select the faster repair variant after seeing results.

The original preparation worker also saves a factor-free model for warm replay.
Report this extra export's cost and bytes.
For a stricter production preparation contract, save it separately and account for that export explicitly.
A duplicated model payload cannot disappear from storage accounting.

A separately registered optional transaction could construct the original model without persistent state.
That transaction estimates the reconstruction system's initial preparation cost.
Without it, report measured index preparation and conditional request savings only.
Do not claim measured lifetime superiority from incomplete preparation accounting.

## Complete timing boundary

The registered primary clock is the outer controller transaction interval.
It starts after campaign loading, launcher binding checks, and prerequisite checks.
It includes frozen-source verification, budget admission setup, required input hashing, plan writes, and runtime capture.
It also includes worker dispatch, complete model/state execution, output verification, child exit, and sealed worker-receipt publication.
The complete model and required state must both be committed and verified by that worker.
The worker receipt's elapsed wall time remains a nested secondary clock.

Initial campaign registration and source snapshots remain outside individual method transactions.
Launcher bootstrap and prerequisite comparison checks also precede each transaction clock.
Final transaction marker publication follows the stop timestamp.
Receipt hashing occurs before the stop timestamp.
Final marker construction and publication follow it.
Do not claim these excluded costs are zero.
This boundary differs from the existing general external transaction observer contract.
It is a declared local controller transaction, not end-user latency.
Never add the nested worker clock to its enclosing controller interval.

The method clock includes these costs:

1. Source checks, record validation, checkpoint loading, and target construction.
2. Prior model or state loading, parsing, hashes, and provenance checks when required.
3. Common nearest-anchor context construction.
4. Direct factor preparation or retained factor reads.
5. Exact quantization, unresolved-case fallback, and model packing.
6. Canonical state construction when required.
7. Complete artifact serialization, writes, roundtrip validation, and receipt publication.

Internal service timers are nested diagnostics.
Do not add them to the enclosing clock.
Do not rename `service_elapsed_ns` as complete transaction latency.
Research cross-arm equality checking is a separate recorded analysis cost.
The worker's own parse, roundtrip, and written-byte validation remain inside each method clock.
The output contract differs between model-only replay and state-returning methods.
State-returning methods may still beat the lighter replay contract; disclose that asymmetry.

Each arm validates only inputs required by its contract.
Cold replay must not hash, read, or parse the original state merely because another arm needs it.
Shared program metadata may bind those files without forcing irrelevant arm-specific input work.
Record any unavoidable extra validation consistently and disclose it.

Use absent output directories and fresh worker processes.
OS caches and other machine activity remain uncontrolled.
The word cold means no model seed or calibration index.
It does not mean cold hardware caches.
Do not evict caches selectively or keep contexts alive for only one method.
Record native build provenance and whether compilation occurred.
The current implementation compiles the native kernel in each fresh process.
Charge that common compilation inside every method clock.
Do not introduce a persistent compiled cache for only one comparator.

## Correctness and actual deletion gates

Every completed arm must return all twenty-four calibrated stages.
Require the fixed target digest, grids, dimensions, and complete model code bytes to match across retained arms.
Require repair, indexed, and complete-fresh canonical state bytes to match.
Hashes identify artifacts; compare trusted canonical bytes when establishing equality.
Roundtrip the model and state through their bounded parsers.
Verify that the original artifact is unchanged after all requests.

Require two original leaves and exactly one retained leaf.
Require the removed ID and tokens to be absent from the returned leaf set.
Verify every retained factor against complete fresh preparation.
Factor provenance remains a trusted preparation premise.
This experiment does not authenticate fabricated or hostile leaves.

Count original-versus-retained changed model codes.
A nonempty deletion is required even if model codes happen to remain equal.
If no code changes, label the result as an unchanged-output request.
Such a result cannot establish performance for changed-output deletion.
Do not choose replacement records after seeing this result.

The work ledger must distinguish preparation from per-stage replay:

- Original preparation: forty-eight prepared stage-record pairs.
- Complete retained fresh: twenty-four prepared stage-record pairs.
- Model-only replay: twenty-four neural stage-record pairs.
- Repair and indexed reconstruction: zero prepared or replayed neural pairs.
- Repair and indexed reconstruction: twenty-four retained factor reads.

The existing stateful counter `neural_stage_record_pairs` excludes leaf preparation.
Add `anchor_preparation_stage_record_pairs` when reporting total transformer work.
Otherwise complete fresh could be incorrectly described as replay-free.
The service validates retained tokens even during repair.
Do not claim that repair reads no retained tokens.

Record state bytes, model bytes, factor bytes, peak memory, and exact-solver fallback counts.
Current code recomputes quantization from retained factors at every stage.
It avoids neural feature extraction; it does not avoid all retained data or quantizer work.

## Sequential pilot and stop rules

Finish and validate the first tiny block before requesting more model runs.
Stop immediately on mismatched targets, models, factors, or canonical states.
Stop on unsettled workers, corrupted provenance, exceeded memory, or exhausted phase allowance.
Preserve failed and incomplete observations with their CPU charges.
Investigate correctness failures before changing a protocol or resuming experiments.

Let `R` be repair latency from the enclosing boundary.
Let `C`, `W`, and `F` be cold, warm, and complete-fresh latencies.
Report `C/R`, `W/R`, `F/R`, and indexed/repair separately.
The conservative replay comparison is `min(C, W)/R`.
Do not select a favorable reconstruction arm after seeing results.

Suggested first-block expansion gate:

1. Every required correctness and completeness check passes.
2. At least one calibrated code changes after deletion.
3. The expected neural-work avoidance is observed.
4. Repair is at least ten percent faster than the faster replay arm.
5. Repair is faster than complete fresh construction.
6. Enough registered allowance remains for a complete next comparison block.

The ten-percent threshold is an engineering screen, not statistical significance.
A smaller observed advantage remains an inconclusive development result.
An indexed/repair discrepancy exceeding twenty percent triggers an overhead audit.
It does not establish a numerical algorithm difference because those paths are identical.
Preserve the original observation after any audit.

After passing, run at most two additional independent repair/cold pairs in this phase.
Use a frozen alternating order: cold-repair, then repair-cold.
The first block's warm replay result remains a reported single-observation control.
No repeated warm-replay speed claim follows from cold-only repetition.
All arms reload their own required inputs and write complete outputs.
All repeated output hashes must match the initial complete comparison.
Do not treat copied receipts or repeated analysis as fresh timing observations.

For three completed repair/cold pairs, report all timings and all within-pair ratios.
Summarize their geometric-mean speedup and their minimum observed speedup.
Three pairs support repeatability against cold replay on this one request only.
They do not establish a population confidence bound or broad reliable speedup.
Do not run additional blocks solely until an attractive significance threshold appears.
If the phase cannot admit an entire next block, leave it explicitly unstarted.

## Before another corpus or larger experiment

A second corpus requires its own registered tiny pilot and frozen request.
First require exactness and the timing gates to pass on this WikiText request.
The existing bounded C4 frame may support a labeled development replication.
It does not become the intended scientific four-shard frame.
Do not silently spend leftover phase allowance on an unregistered corpus or new quality inputs.

Larger quality evidence remains a separate prerequisite for paper claims.
Compare the changed target with sequential calibration, nearest rounding, and full precision.
Preserve all previous quality exclusions and ordinary article-level losses.
Every new scientific cell requires its own small pilot before expansion.

## Preparation and repeated-request interpretation

Report measured original preparation even when the main ratio concerns request latency.
For a request sequence, each method needs its own initial preparation and subsequent states.
Sum each system's actual preparation and request clocks without shared-time subtraction.
Warm replay may receive its immediately preceding model, but never the repair system's hidden factors.

Repeated timing of one request is not a sequence of successive deletions.
The two-record calibration set provides only two successive nonempty deletions.
A useful lifetime study needs a larger prospectively frozen source set.
It must include no-op, combined, sequential, and full deletion semantics.
State loading, output, and storage remain charged after every request.

An estimated break-even count from constant per-request savings is a projection.
Label its constant-cost assumptions and report uncertainty.
It cannot replace a measured changing-state sequence.
No reliable full-model speed theorem follows from these timing pilots alone.

## Implementation audit conclusion

The reviewed service exposes the required matched methods and minimal-state backend.
No new numerical implementation is necessary for the first complete timing pilot.
The principal integration risks are budget mixing and incorrectly labeled transaction clocks.
The launcher now provides an enclosing controller clock and a separate bounded worker clock.
Other risks include irrelevant baseline input checks, uncharged warm-seed loading, and omitted factor-preparation counters.
The executable controller must resolve these before launch.

The final report must retain the old sequential-target losses and the centered-box rejection witness.
An explicit changed-target win can support a new research direction.
It cannot retroactively turn either earlier result into a success.

## Final pre-registration review

The final launcher enforces a separate campaign ledger and stable registered runtime.
Its repeat gate checks common fixed and base targets, changed model codes, state equality, and feature-work avoidance.
It also requires primary repair to beat complete fresh and the best cold/warm replay by ten percent.
Each repeat pair requires 244 available CPU seconds before its first worker.
The outer clock includes receipt hashing before its stop timestamp.
Both scripts compile, and sixteen worker plan/provenance fixtures pass without model execution.
The checkpoint provenance API and all inspected dependency paths match their current definitions.
No blocking implementation issue remained at this review.
This clearance permits the bounded development pilot; it asserts no empirical result.
