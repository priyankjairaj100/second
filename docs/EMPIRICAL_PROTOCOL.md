# Prospective empirical protocol

Version: 3. Date: 4 October 2026.

This document reconstructs the empirical plan from the current implementation.
It does not recover the missing earlier protocol.
No empirical observations accompany this document.
Experiments remain paused.
Software correctness fixtures remain separate from research evidence.

`configs/protocol_v3.json` stores the current numerical planning choices.
The version 1 and version 2 files preserve earlier preparation plans.
All three files retain the compatible `calibration-protocol-v1` schema.
The version field distinguishes their content.
These choices express project goals.
They are not universal standards or measured power calculations.
The final execution manifest must resolve every blocked field before confirmation.
The current protocol keeps `confirmation_configuration_ids` and `planned_inventory_sha256` unresolved.
Their absence prevents confirmation from becoming an executable plan.
Commit that manifest before observing confirmation results.
Record its hash in every run.

## 1. Questions and claims

The primary target is `V_cert`.
It holds the original weights fixed.
It recomputes sequential quantization after calibration deletion.
It includes changes to all later calibration features.

The correctness question concerns exact model output and canonical state.
The coverage question concerns accepted certificates after actual ancestor changes.
The performance question concerns the complete service under equal information.
The NLP question concerns useful model quality under this declared numerical target.

The primary performance baseline is equally indexed fresh quantization.
Direct fresh quantization remains the independent correctness control.
Report direct comparisons as gains from the combined indexing and repair system.
Attribute deletion-specific gains only against equally indexed fresh quantization.
A tie against that baseline requires a narrower claim.

## 2. Frozen numerical target

The target manifest must identify checkpoint tensors and architecture.
It must identify the decoder source and certified primitive source.
It must fix grids, order, ties, ridge, and normalization.
It must fix parameter conversion and all unchanged parameters.
It must identify chart directions, radii, precision, and construction rules.
It must record all data-independent preparation costs.
The new grid-box provider removes the affine-span membership restriction.
Its box contains every installed finite code from the frozen grids.
This property does not guarantee useful feature bounds or accepted certificates.
The box is a sound alternative, not a selected empirical configuration.
Its shared provider gives repair no inherent advantage over equally indexed fresh quantization.

The token manifest must fix token identifiers, ordering, masks, and positions.
Each record must preserve its boundaries after deletion.
Do not repack the remaining records after deletion.
Do not fit tokenization or preprocessing on the deletable corpus.
Any change to this rule requires a new target.

Native external kernels do not define the main target.
An architecture comparison cannot establish numerical identity with those kernels.
Use verified conversion before evaluating any alternate deployment representation.

## 3. Data and model selection

Use real text only.
Do not create synthetic empirical datasets.
Use `configs/source_catalog_v1.json` and `docs/SOURCE_SELECTION.md` for candidate metadata.
Metadata selection does not approve execution inputs.
The source catalog now pins the DistilGPT2, GPT-2, and WikiText repository revisions.
These pins identify public metadata only.
No local checkpoint, tokenizer, or corpus hashes are available.
The first candidates use the implemented GPT-2 architecture.
The first corpus candidate is WikiText-2 raw text.
A real C4 subset is a later domain extension.
English LAMBADA remains a possible task extension.
These candidates remain subject to architecture, licensing, and resource checks.
No candidate was acquired for this protocol.
Ordinary checkpoint dimensions exceed the current reference planning limits.

Every execution source needs a pinned revision and verified local content hashes.
Reserve C4 and LAMBADA sources remain incompletely pinned.
Record model licenses and dataset licenses separately.
Record download sizes before authorizing a download.
Preserve document identifiers through tokenization.
Identify WikiText article boundaries before selecting records.
Do not treat unrelated line numbers as independent articles.
Document any unavoidable boundary limitation.

Select development, confirmation, and evaluation documents before method tuning.
Keep those three document pools disjoint.
Check overlap by document identifiers, normalized text hashes, record IDs, and prepared token hashes.
Record duplicate handling before sampling.
Use held-out source documents for quality evaluation.
Do not tune the chart on evaluation text.
Use at most one fixed chunk per source document in the first workload.
Preserve source document IDs and fixed token offsets.
Do not combine documents or repack retained records after deletion.
Freeze normalization, BOS, EOS, positions, and masks before selection.
Source document withdrawal must include every associated prepared chunk.
`docs/WORKLOAD_CONTRACT.md` gives the full record and withdrawal contract.

## 4. Research units and separation

A calibration root contains one independently sampled calibration corpus.
Draw each root independently from the fixed phase pool.
Sample without replacement inside each root.
Independent roots may overlap because each root uses a separate draw.
`sample_roots` uses separate domains of a versioned SHA256 stream.
Uniformity refers to its ideal independent-stream model.
The implemented generator is deterministic pseudorandom computation.
Save pool hashes, seeds, and every root membership before observing method outcomes.
Record all seeds and selected document identifiers.
The inference scope remains conditional on the fixed source pool.

Requests from one root share calibration state.
Treat those requests as a statistical cluster.
Timing repeats also share the same request.
They do not increase the independent sample size.

Development uses separate roots and documents from confirmation.
Use development results for chart design and performance changes.
Freeze all choices before confirmation.
Do not select confirmation requests after observing their repair outcomes.
Any confirmation-driven change creates a new method version.
Test that version on new confirmation roots.
Keep earlier results in the release history.

## 5. Staged workload and resource limits

The local plan uses CPU execution only.
It does not authorize paid jobs or another project's hardware.
The observed environment has an 8 GiB container limit.
The proposed worker address-space limit is 6 GiB.
`RLIMIT_AS` limits virtual address space, not physical memory.
Record observed physical memory separately.
The parent controller also requires resources.
`src/worker_control.py` now enforces explicit limits before each comparison process starts.
It applies CPU limits, address-space limits, file limits, CPU affinity, and thread environment settings.
The parent enforces a wall deadline and stops ordinary process-group descendants.
`src/phase_budget.py` now provides a durable CPU admission ledger.
The campaign binds one ledger to the protocol hash.
Workers reserve their CPU limit plus two seconds before launch.
Admission fails when the complete allowance exceeds the remaining phase allowance.
Settled charges use rounded-up CPU usage reported by `wait4`, with a one-second minimum.
Unknown or interrupted reservations keep their complete charge.
Observed overruns remain charged and prevent later admission when the ledger exceeds its cap.
This mechanism controls trusted worker admission within one protocol ledger.
It does not contain all descendant CPU use or cap the physical machine.
Separate protocol ledgers do not provide a shared global cap.
Controller CPU and unrelated processes remain outside this worker ledger.

| Stage | Planned roots | Records per root | Tokens per record | Purpose |
| --- | ---: | ---: | ---: | --- |
| Preflight | 1 development root | 2 | 16 | Validate real tensors and finite execution |
| Feasibility | 2 development roots | 8 | 32 | Test changed-prefix coverage and complete costs |
| Development | 4 development roots | 32 | 64 | Select one target-preserving method configuration |
| Confirmation | 12 new roots | 64 | 128 | Evaluate the frozen primary configuration |

These sizes are prospective targets.
They do not establish feasible memory or runtime.
Use one primary checkpoint before expanding the model matrix.
The preflight comparison has a 15-minute wall deadline.
Later comparisons have a 60-minute wall deadline.
For the current campaign, these deadlines cover preparation and all methods inside one comparison process.
The separate method-process runner applies explicit limits to each worker.
Its preparation worker and method workers require separate reservations.
Choose and freeze this execution mode before collecting timing data.
The proposed CPU limits are 900 and 3,600 seconds per comparison process.
The proposed file limit is 512 MiB per written file.
The proposed thread setting is one.
Resolve supported CPU affinity identifiers before freezing the inventory.
The feasibility stage permits at most three CPU-hours.
Development permits at most twelve CPU-hours.
Confirmation permits at most sixty-four CPU-hours.
Stop admission when the next complete worker allowance does not fit.
The campaign now applies this rule for its supported phase labels.
Those labels are development, confirmation, and software test.
Feasibility remains a planning stage without a distinct supported inventory phase.
Its separate three-hour cap therefore needs explicit dispatch support before use.
The protocol retains that limitation as a preparation blocker.
Keep every unstarted planned run in the result inventory.

Use one timing repeat during preflight and feasibility.
Use three paired repeats for development and confirmation.
Use a saved seeded method permutation with cyclic rotations.
Each three-repeat block places every method once in each position.
The next block reverses orientation.
A partial block does not guarantee exact position balance.
Record CPU affinity, thread settings, runtime versions, and system load.
No final matrix expansion follows automatically from passing an early gate.

## 6. Deletion requests

All fractions use the original root size.
Round positive request sizes upward.
The primary matrix contains six independently reset request types.

| Type | Selection rule |
| --- | --- |
| Uniform singleton | Sample one identifier uniformly |
| Uniform small | Sample 1/16 of identifiers without replacement |
| Uniform large | Sample 1/4 of identifiers without replacement |
| Contiguous | Remove 1/16 from a uniformly selected original-order interval |
| Concentrated | Select 1/16 using a fixed original-prefix feature norm score |
| Difficult | Select 1/16 using a frozen original-state margin and contribution score |

The score equations and tie rules are now implemented in `src/request_workload.py`.
`docs/WORKLOAD_CONTRACT.md` fixes all edge cases.
Concentration uses the largest stage share of original feature energy.
Difficulty uses the largest squared original leverage multiplied by stage margin sensitivity.
The producer reconstructs exact original Grams and complete decision traces.
It verifies those traces against the stored original model.
A zero-energy decision contributes zero sensitivity.
A positive-energy midpoint gives infinite sensitivity.
Zero leverage contributes zero, including at infinite sensitivity.
Score ties use ascending record IDs.
These equations define a stress proxy, not guaranteed difficult repair.
Do not choose requests by observed repair speed or acceptance.
Charge every original feature pass, factorization, verification, and score artifact write to workload preparation.
The score artifact binds the original state, prepared records, target, and producer sources.
No real score artifact exists yet.
These selectors represent stress conditions.
Do not interpret their outcomes as uniform-request probabilities.

Add a separate sequence of three disjoint small deletions per root.
Each step must start from the previous committed state.
Compare each step with fresh construction on the remaining records.
Also compare the final sequence with the combined deletion.
A separate uniform permutation defines three disjoint batches of the original small-request size.
A root must contain enough records for all three batches.
The workload marks insufficient roots blocked.
`src/sequence_runner.py` now implements execution from each preceding committed repair state.
It prepares the original state once and persists an ordered lineage.
Restart verifies the saved original state and every completed child artifact.
A failed step preserves its attempt and every later planned request.
Independent cumulative resets do not replace that sequence.
Bulk campaign sequence dispatch remains open.
Run empty deletion and complete deletion as correctness controls.
Both controls now have working local execution paths.
Complete deletion uses zero retained data contributions under the original fixed normalization and ridge.
Later empty requests remain valid, while heldout data must remain nonempty.
Keep these controls outside the primary latency average.
Primary requests that remove the entire root remain excluded from primary ratio analysis.

Source withdrawal requires a corpus with documented distinct sources.
Hash the complete record-to-source mapping before selection.
Sort eligible source IDs and select one uniformly from its separate stream domain.
An eligible source contains records and leaves at least one record after withdrawal.
Delete every record assigned to the selected source.
`source_withdrawal_request` implements this law.
The extension remains blocked until actual documented source metadata exists.
Do not create artificial source labels to fill this row.

## 7. Methods and information parity

The primary methods are repair, equally indexed fresh, and direct fresh.
Each method must produce the same declared model and state.
Use the same target manifest and retained identifiers.
Give equally indexed fresh the same valid summaries and storage allowance.
Record any unavoidable information difference.

The service now implements `certified`, `fixed_reference`, `identity_only`, and `full_replay` modes.
All modes preserve the same numerical target and canonical state.
The response-family identity control uses equality with the intrinsic reference.
The separate identity-cache family now stores exact original-model sequential Grams.
It reuses them only when the required original quantized ancestors remain identical.
Changed dependencies require retained replay.
Its indexed-fresh arm receives the same original cache and solver information.
Its returned state uses a separate canonical schema.

The response family now provides linear and full quadratic response-Gram tiers.
The quadratic tier retains the complete Gram of the affine feature surrogate.
Its certified remainder still covers feature approximation and finite arithmetic.
The tier changes storage and certificate tightness without changing the numerical target.
The two tiers use distinct canonical state schemas.
Practical memory and runtime remain unmeasured.
Do not pool a restricted quadratic subset with the complete primary matrix.

The fixed-reference control retains the complete finite feature error bound.
The verifier policy can use the spectral certificate alone.
The alternative tries exact interval triangular solves after spectral rejection.
This policy preserves the numerical target and canonical state.
Interval rejection still permits replay.
Neither policy guarantees useful acceptance.

Give every family, tier, mode, and verifier combination a distinct configuration ID.
The analyzer rejects mixed labels within one configuration.
Require byte equality of canonical state within one family and tier.
Across different state schemas, compare full quantized model output and account for all stored state.
Compare replay selection only after fixing the certificate configuration.
Each ablation must identify the changed factor.

Report preparation time and storage beside each method.
Do not hide repair preparation inside a shared setup category.
The current direct control rebuilds the full canonical state.
Its required index construction belongs inside that cost.
Equally indexed fresh receives the valid retained summaries.
An artifact-only control needs a separate output contract and timing row.
Amortize preparation only in the separately declared lifetime analysis.

## 8. Timing boundaries and cache conditions

The complete request starts before required state and deleted-content reads.
It ends after canonical output and the transaction commit.
Include required loading, extraction, proof, replay, arithmetic, metadata, serialization, output, and cleanup.
Count each interval once.
Nested timers cannot be added to their parent timer.
Record unclassified time as an explicit remainder.
Optional service telemetry now records exclusive categories and coverage events.
Nested spans subtract child time from parent time.
The categories include extraction, feature evaluation, Gram work, bounds, factors, validation, serialization, and source access.
The collector records remaining instrumented service time separately.
These timers add measurement overhead.
They support diagnostic analysis, not an automatic claim about clean service latency.
Some failed extractors expose unavailable evidence without a detailed primitive reason.

An experiment's equality check can remain outside the service boundary.
Keep that validation cost in the experiment ledger.
Separate held-out quality evaluation from the service timing.
Neither exclusion permits required service verification to become free.

The current runner records `service_through_atomic_artifact_fsync`.
It includes the service call and durable state output.
Its warm boundary excludes checkpoint loading and original preparation.
It also excludes independent comparison, quality evaluation, and the final experiment-result commit.
Keep those costs in the outer experiment ledger.
Confirm that durable artifact output satisfies the selected service contract.
Complete-service claims require the same boundary for every method.

Warm conditions may retain only declared reusable objects.
The campaign now starts each complete comparison in a new process.
Its three methods still share warm objects and process history.
The campaign mode is `isolated_comparison_warm_arms_os_cache_uncontrolled`.
The method mode remains `warm_sequential_os_cache_uncontrolled`.
A separate runner now starts preparation and each method in independent worker processes.
It loads the same saved original state for methods that need it.
Its process receipt and timing contract require separate analysis from warm-arm timings.
`src/isolated_comparison.py` executes a `calibration-isolated-plan-v1` plan.
The plan binds the normalized run manifest, target, source hashes, and worker limits.
It starts one setup worker, then one worker for each declared method.
Its cache mode is `isolated_method_processes_os_cache_uncontrolled`.
Its timing boundary is `limited_worker_startup_inputs_service_artifacts_child_commit_and_cleanup`.
The boundary includes CPU admission, process startup, input loading, and service work.
It also includes artifact writes, child receipt commit, process exit, and cleanup.
It excludes parent verification, worker-control receipt commit, parent receipt commit, and heldout evaluation.
The worker controller settles the phase CPU charge after stopping the elapsed timer.
Original preparation is charged separately.
The isolated path does not yet execute heldout quality evaluation.
Its durable child receipt does not establish complete external service latency.
Its confirmation route remains blocked until compatible inventory dispatch exists.
Process separation does not establish cold filesystem caches.
Any claimed disk-cold condition requires additional validated controls.
Operating-system page caches need separate control or a precise uncontrolled label.
Never label process-cold timing as disk-cold without evidence.
Use identical output durability for compared methods.
Do not pool different cache conditions.
The worker timer covers dispatch through process cleanup.
It excludes the final controller commit and later log summaries.
That timer is not one method's request latency.
Do not add nested method times to the worker total.

## 9. Correctness, failure, and outcome accounting

Validate every stage against direct fresh construction.
Check the final quantized model and canonical state bytes.
Retain the equality result and artifact hashes.
Any mismatch stops interpretation of speed.
Resolve it before continuing the affected method version.

Certificate rejection is an internal event.
Successful replay can still yield an exact completed request.
Finite evaluator failure is a failed request.
It must not commit a successful model.
Timeout, memory failure, interruption, and missing planned attempts remain visible.
Retain consumed time even when completion fails.
Consumed time is not latency to an exact answer.

Record the complete coverage path for each stage.
Include chart membership, descriptor availability, finite bounds, acceptance, replay, and completion.
Distinguish unchanged ancestors from genuinely changed ancestors.
Report retained reads and replayed groups beside elapsed time.

Do not exclude a request because it is slow or difficult.
Only predeclared malformed-source rules can exclude source records before sampling.
Record every exclusion with its reason.
Replace no confirmation request after observing its outcome.

## 10. Statistical analysis

The analyzer requires a frozen inventory for confirmation.
That inventory contains every planned root, request, repeat, and method.
It also contains target bindings and the final protocol binding.
`build_campaign` freezes supplied membership and deterministic method orders.
Write its output as exact canonical JSON bytes.
The inventory clears only `protocol.sha256` inside embedded run manifests.
The final protocol then binds the inventory hash.
External run manifests bind the final protocol hash.
The executor verifies this complete chain before dispatch and restart.
It also verifies every current source module and the campaign execution scripts.
The separate isolated plan additionally binds `scripts/run_isolated.py`.
Its standalone plan does not replace the complete confirmation inventory.
A changed source file prevents reuse of a previous campaign outcome.
Confirmation requires explicit `confirmation_configuration_ids`.
The executor checks the full configuration, root, request, and repeat product.
The current protocol leaves those configuration IDs unresolved.
No real confirmation inventory exists.
Missing outcomes become explicit missing attempts.
Reject duplicate identities, mixed targets, and unplanned observations.

First take the median timing across paired repeats for each request.
A request enters the conditional ratio only when both methods complete every repeat exactly.
Let these medians be B and R.
Compute log(B/R) for that request.
Average request log ratios within each root.
Average those root values with equal root weights.
Exponentiate the result.

Report this ratio as conditional on exact completion.
Report all request outcomes beside it.
The analysis plan keeps primary requests separate from controls and extensions.
It preserves service family, response tier, service mode, and verifier policy.
It also checks observed chart and service bindings.
Do not use a shared configuration ID for different algorithm settings.
Report eligible requests, eligible roots, and omitted roots.
Do not present a conditional ratio as an unconditional reliability result.

Use 2,000 deterministic bootstrap draws over independent roots.
Report the central 95% percentile interval.
Do not bootstrap individual timing repeats.
One observed root provides no reported interval.
Twelve roots are a planning choice.
They do not guarantee interval precision or coverage.
Use development variability to document the expected precision before confirmation.
If precision requires more roots, change the plan before confirmation.

The primary comparison uses equally indexed fresh and repair.
Other comparisons and sensitivity grids are secondary.
Report their complete matrix without selecting favorable cells.
Any multiple-comparison inference requires a separately specified correction.
No formal significance claim follows from uncorrected exploratory comparisons.

## 11. Lifetime cost

Let P_R and P_B denote preparation costs.
Let R_t and B_t denote complete costs for request t.
Net savings after m requests equal sum(B_t - R_t) - (P_R - P_B).
Include state updates and failed attempts in their corresponding complete costs.
Preserve request order for repeated deletion.

Report the first observed nonnegative balance.
Report the final balance as well.
A later expensive request can reverse an earlier crossing.
Do not infer permanent break-even from the first crossing.

A projected crossing assumes constant positive saving s.
Its value is ceiling((P_R - P_B)/s), when the numerator is positive.
Label this calculation as a projection.
If saving is nonpositive, no finite projected crossing exists.
Storage cost remains a separate budget unless a price model is declared.

## 12. Prospective decision gates

| Gate | Planning criterion | Action after failure |
| --- | --- | --- |
| Exactness | Zero mismatches; no invalid successful commits | Stop affected method and correct it |
| Finite domain | All primary preflight requests evaluate successfully | Narrow the domain or revise the declared target |
| Coverage | At least 25% of changed-ancestor stage groups certify on both feasibility roots | Improve bounds or narrow the claim |
| Resources | Verified worker limits, measured memory, and protocol-scoped CPU admission | Reduce the workload or complete enforcement |
| Quality | Retained fresh perplexity at most 20% above base perplexity on fixed held-out text | Reconsider grids or supported use |
| Service value | Candidate saves complete measured cost against the declared baseline on development | Redesign or use an indexing-only claim |
| Confirmed speed | All planned requests finish exactly; lower ratio interval exceeds 1.05 | Report conditional results without a reliable-speed claim |

The coverage threshold is a research continuation rule.
It is not a correctness requirement.
The quality threshold is a planning tolerance.
Use identical tokenization and evaluation text for the quality ratio.
Perplexity alone does not establish downstream NLP value.
Add a task matched to the final supported application before submission.

The speed gate requires the complete committed boundary.
An arm-only timing cannot pass that gate.
No empirical pass has been recorded for any gate.

## 13. Artifacts and reproducibility

Save immutable input manifests and raw outcome files.
Keep unfinished transactions separate from committed results.
Record hashes for source, protocol, target, tokens, state, and output.
Record workload scores and their preparation costs separately.
Preserve failed worker outcomes and every unstarted inventory entry.
A controller commit records a terminal outcome, which can still report worker failure.
Keep resource failures and tracebacks with sensitive paths removed where necessary.
Do not publish model weights or text against their license conditions.

`scripts/summarize_results.py` creates JSON, CSV, Markdown, and optional standard plots.
It reads recorded observations only.
It records hashes of every input result file.
Its tests use labeled software fixtures.
Those fixtures are not paper results.

Before research execution, resolve these remaining preparation blockers:

- Validate a resource-feasible real checkpoint and its adapter path.
- Acquire and hash actual checkpoint, tokenizer, and corpus files within the authorized scope.
- Freeze document boundaries, fixed chunks, normalization, positions, masks, BOS, and EOS.
- Build disjoint source pools and save independently selected root membership.
- Produce original-state score artifacts and charge their complete preparation costs.
- Select and freeze the primary chart, quantization settings, and service configuration.
- Resolve worker affinity and add explicit feasibility-phase dispatch.
- Validate complete committed timing and clean measurement overhead.
- Integrate ordered sequences with bulk campaign scheduling.
- Integrate isolated method execution with frozen campaign inventories and confirmation.
- Declare confirmation configuration IDs and freeze the canonical complete inventory.
- Use development variability to justify planned confirmation precision.
- Obtain the user's instruction to resume research experiments.

The request laws, worker admission ledger, independent request inventory, and local sequence runner now have correctness tests.
Independent method processes provide another execution path, subject to their declared receipt boundary.
The identity-cache baseline, quadratic tier, and interval fallback are implemented controls.
Their implementation does not create real input artifacts or establish useful performance.
The grid-box alternative remains unselected for empirical use.
No empirical pass has been recorded for any gate.
The repository retains this protocol before any new empirical run.
Its existence does not mean the program has passed the experiment-ready gate.
