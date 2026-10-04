# Prospective empirical protocol

Version: 1. Date: 4 October 2026.

This document reconstructs the empirical plan from the current implementation.
It does not recover the missing earlier protocol.
No empirical observations accompany this document.
Experiments remain paused.
Software correctness fixtures remain separate from research evidence.

`configs/protocol_v1.json` stores the numerical planning choices.
These choices express project goals.
They are not universal standards or measured power calculations.
The final execution manifest must resolve every blocked field before confirmation.
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
Metadata selection does not approve or pin execution inputs.
The first candidates use the implemented GPT-2 architecture.
The first corpus candidate is WikiText-2 raw text.
A real C4 subset is a later domain extension.
English LAMBADA remains a possible task extension.
These candidates remain subject to architecture, licensing, and resource checks.
No candidate was acquired for this protocol.
Ordinary checkpoint dimensions exceed the current reference planning limits.

Every source needs a pinned revision and content hashes.
Record model licenses and dataset licenses separately.
Record download sizes before authorizing a download.
Preserve document identifiers through tokenization.
Identify WikiText article boundaries before selecting records.
Do not treat unrelated line numbers as independent articles.
Document any unavoidable boundary limitation.

Select development, confirmation, and evaluation documents before method tuning.
Keep those three document pools disjoint.
Check overlap by document identifiers and normalized text hashes.
Record duplicate handling before sampling.
Use held-out source documents for quality evaluation.
Do not tune the chart on evaluation text.

## 4. Research units and separation

A calibration root contains one independently sampled calibration corpus.
Draw each root independently from the fixed phase pool.
Sample without replacement inside each root.
Independent roots may overlap because each root uses a separate draw.
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
The process target is at most 6 GiB.
The remaining memory supports monitoring and output.
These limits require enforcement before empirical execution.
A configuration field alone does not enforce a limit.

| Stage | Planned roots | Records per root | Tokens per record | Purpose |
| --- | ---: | ---: | ---: | --- |
| Preflight | 1 development root | 2 | 16 | Validate real tensors and finite execution |
| Feasibility | 2 development roots | 8 | 32 | Test changed-prefix coverage and complete costs |
| Development | 4 development roots | 32 | 64 | Select one target-preserving method configuration |
| Confirmation | 12 new roots | 64 | 128 | Evaluate the frozen primary configuration |

These sizes are prospective targets.
They do not establish feasible memory or runtime.
Use one primary checkpoint before expanding the model matrix.
The preflight arm has a 15-minute deadline.
Later arms have a 60-minute deadline.
The feasibility stage permits at most three CPU-hours.
Development permits at most twelve CPU-hours.
Confirmation permits at most sixty-four CPU-hours.
Stop when a phase reaches its declared budget.
Keep every unstarted planned run in the result inventory.

Use one timing repeat during preflight and feasibility.
Use three paired repeats for development and confirmation.
Balance method order with a saved random permutation.
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

Freeze the exact score equations and tie rules in the request manifest.
The last two selectors remain blocked until those equations are specified.
Do not choose requests by observed repair speed or acceptance.
Charge any required score construction to preparation.
These selectors represent stress conditions.
Do not interpret their outcomes as uniform-request probabilities.

Add a separate sequence of three disjoint small deletions per root.
Each step must start from the previous committed state.
Compare each step with fresh construction on the remaining records.
Also compare the final sequence with the combined deletion.
Run empty deletion and complete deletion as correctness controls.
Keep those controls outside the primary latency average.

Source withdrawal requires a corpus with documented distinct sources.
It remains a planned extension until that corpus exists.
Do not create artificial source labels to fill this row.

## 7. Methods and information parity

The primary methods are repair, equally indexed fresh, and direct fresh.
Each method must produce the same declared model and state.
Use the same target manifest and retained identifiers.
Give equally indexed fresh the same valid summaries and storage allowance.
Record any unavoidable information difference.

Add identity-only repair as the first mechanism control.
Compare fixed-reference and compact linear response where implemented.
Run full quadratic response only on an affordable declared subset.
Do not pool that subset with the complete primary matrix.
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
Cold conditions start a new process and load the declared state.
Operating-system page caches need separate control or a precise uncontrolled label.
Never label process-cold timing as disk-cold without evidence.
Use identical output durability for compared methods.
Do not pool different cache conditions.

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
It also contains target and protocol hashes.
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
| Resources | At most 6 GiB peak memory; all phase limits respected | Reduce the declared workload before confirmation |
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
Keep resource failures and tracebacks with sensitive paths removed where necessary.
Do not publish model weights or text against their license conditions.

`scripts/summarize_results.py` creates JSON, CSV, Markdown, and optional standard plots.
It reads recorded observations only.
It records hashes of every input result file.
Its tests use labeled software fixtures.
Those fixtures are not paper results.

Before confirmation, resolve these remaining protocol blockers:

- Pin the model and dataset revisions in the source catalog.
- Freeze tokenizer behavior and document boundary rules.
- Freeze concentration and difficult-request score equations.
- Freeze chart construction and primary quantization settings.
- Enforce resource limits outside the worker process.
- Validate the selected service boundary and add process-cold execution where claimed.
- Generate and hash the complete planned-run inventory.
- Confirm the independent root sampling and expected precision.

The repository retains this protocol before any new empirical run.
Its existence does not mean the program has passed the experiment-ready gate.
