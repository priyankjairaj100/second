# Executable reference service

Revision 8. Date: 4 October 2026.

The primary certified path implements V_cert with explicit numerical contracts.
The legacy library-math V path remains available and distinct.
It prioritizes inspectable correctness.
It does not provide fast quantization for large checkpoints.
Exact rational values can require large numerators and denominators.
Event counters and software tests do not measure latency.
The current protocol is `configs/protocol_v4.json` and remains prospective and paused.
The 35-page revision 7 report PDF remains unchanged; `REVISION_8.md` records the new implementation scope.

## Modules

| Module | Responsibility | Explicit boundary |
| --- | --- | --- |
| `src/exact_core.py` | Exact factorization, rounding, and shape checks | The caller establishes the spectral premise |
| `src/sparse_repair.py` | Code-change injection and exact coordinate fallback | The target factor must be known |
| `src/response_moments.py` | Quadratic response totals and exact deletion | The extractor must be fixed and sound |
| `src/response_certificate.py` | Error contraction and rational Gram bounds | Descriptors must cover the actual finite evaluator |
| `src/linear_response.py` | Compact response totals and omitted-PSD bounds | It does not prove neural derivatives |
| `src/repair_service.py` | Original complete service with reference descriptors | Its callbacks have explicit trusted contracts |
| `src/response_service_adapter.py` | Original response bridge through individual descriptors | Proposal construction scans retained descriptors |
| `src/aggregate_response_service.py` | Linear or quadratic grouped state and complete exact repair | It trusts the fixed extractor and query theorem |
| `src/domain_refinement.py` | Exact covariance boxes, intersections, and interval decisions | Caller supplies sound bounds and the true ridge floor |
| `src/identity_cache.py` | Original-model true-Gram cache and canonical refresh | Reuse requires matching transitive ancestors and trusted cache origin |
| `src/model_fresh.py` | Complete sequential model-only construction | No deletion index; a different output contract from canonical-state construction |
| `src/box_response_provider.py` | Full-grid domains and rank-zero feature enclosures | Broad domains can cause proof rejection and replay |
| `src/transformer_backend.py` | Original deterministic scalar decoder | Its built-in proof establishes input identity only |
| `src/certified_intervals.py` | Rational intervals and certified scalar primitives | Resource limits can reject unsupported calculations |
| `src/certified_transformer.py` | Explicit decoder with automatic response bounds | The affine provider requires a supported parameter chart |
| `src/checkpoint_adapter.py` | Local GPT-2 parameter import | It does not reproduce external floating kernels |
| `src/work_scheduler.py` | Cooperative scheduling of two exact branches | Packet and cleanup costs require separate accounting |
| `src/target_manifest.py` | Fixed grids and complete target identity | Defines the project quantizer, not vendor GPTQ identity |
| `src/chart_construction.py` | Deterministic independent chart recipes | Construction does not establish practical coverage |
| `src/resource_preflight.py` | Config-only counts before eager loading | Planning bytes are not a proved memory bound |
| `src/experiment_runner.py` | Local three-method comparison and exactness checks | Warm diagnostic timing; no downloads |
| `src/sequence_runner.py` | Ordered requests, committed predecessors, and verified restart | Step methods share a warm sequence process |
| `src/sequence_campaign.py` | Frozen sequence dispatch and complete planned outcomes | Real schedules and matched model-only lifetime execution remain unmeasured |
| `src/isolated_comparison.py` | Separate setup and method workers; optional quality worker | Its legacy method clock excludes parent verification and final accounting commits |
| `src/isolated_inventory.py` | Frozen isolated campaigns and confirmation admission | Real inventories and complete-clock integration remain required |
| `src/transaction_timing.py` | External observer through child commits, cleanup, and output verification | Its own final receipt is excluded; whole comparisons are not single methods |
| `src/service_telemetry.py` | Exclusive spans and bounded external certificate funnel | Opaque provider causes and unsampled cell detail remain unavailable |
| `src/arithmetic_audit.py` | Constructed Fraction endpoint counts and bit lengths | Calling thread/process only; hidden intermediates and lifetimes are unobserved |
| `src/worker_control.py` | Applied process limits, cleanup, and durable worker outcomes | Per-process limits do not contain hostile descendants |
| `src/phase_budget.py` | Locked CPU admission and usage settlement | Scope is one protocol ledger, not the physical machine |
| `src/experiment_campaign.py` | Frozen independent-request dispatch and verified outcomes | Warm-arm path; separate isolated inventory supplies method-process dispatch |
| `src/run_store.py` | Atomic artifacts, sealed results, and verified restart | POSIX trusted-storage contract |
| `src/result_analysis.py` | Failure-aware paired analysis and lifetime accounting | No empirical result follows without real run records |

The original response adapter remains a useful correctness reference.
It stores individual response payloads inside canonical descriptors.
It scans those payloads when it constructs group totals.
This historical path has `O(N)` descriptor reads.
Its response matrices can require `O(N r² d²)` entries.

The aggregate service replaces that storage layout.
It stores response matrices only at group level.
Its proposal contracts group totals without scanning individual descriptors.
Read `docs/AGGREGATE_SERVICE.md` for the complete interface and ledger.
Read `docs/BASELINES.md` for bounded loading and equally indexed construction.
Read `docs/EXPERIMENT_RUNNER.md` and `docs/TRANSACTION_TIMING.md` for distinct measured boundaries.

## Original decoder usage

Construct `DecoderConfig` and `DeterministicDecoder` from explicit weights.
Then call `make_repair_service` with fixed grids, ridge, normalization, and group count.
Provide token IDs through `Record(id, decoder.record_payload(tokens))`.
The normalization and grids stay fixed across deletion.
The example downloads no tokenizer or checkpoint.

```python
service = decoder.make_repair_service(
    grids_by_stage=fixed_grids_by_stage,
    ridge=1,
    normalization=original_token_normalization,
    group_count=4,
)
initial = service.fresh(records)
removed = (records[0],)
retained_by_id = {r.record_id: r for r in records[1:]}
repaired = service.repair(initial.state, removed, retained_by_id.__getitem__)
fresh_retained = service.fresh(records[1:])
assert repaired.state.canonical_bytes() == fresh_retained.state.canonical_bytes()
installed = {stage.stage_id: stage.codes for stage in repaired.state.model}
logits = decoder.logits(evaluation_token_ids, installed)
```

`tests/test_transformer_backend.py` gives the complete original constructor.
The backend manifest binds frozen model configuration.
The output contains the quantized stages promised by the job.

## Compact aggregate usage

```python
service = AggregateRepairService(
    job,
    target_evaluator,
    intrinsic_moments,
    stage_contracts,
    response_query,
    provider_id="fixed-proof-version",
    extractor_id="fixed-extractor-version",
)
initial = service.fresh(records)
repaired = service.repair(initial.state, deleted_records, retained_source)
```

The intrinsic extractor returns compact response moments and scalar error moments.
It can return `None` when it cannot establish the required evidence.
The query receives aggregate totals and the new certified prefix.
It receives no individual retained descriptor or source payload.
It returns a bound query or `UnknownBound`.
Missing evidence causes exact replay of the affected group.

The automatic provider supplies concrete hooks for its supported decoder and chart.
The generic service still permits other explicitly trusted hooks.
A callback's declared identity does not prove its mathematics.

## Complete logical state

The original service returns `CanonicalState` with reference descriptors.
The aggregate service returns a distinct `AggregateState`.
Both states include the complete target model.
They do not have interchangeable schemas.

Aggregate state stores record IDs, content digests, group IDs, contribution digests, and availability flags.
The linear tier stores constant Grams, linear responses, tangent scalar Grams, and error moments at group level.
The quadratic tier stores every oriented cross-moment matrix for the affine feature surrogate.
Both tiers retain the same complete finite-error descriptors.
They use distinct canonical schemas.
It stores no individual matrix payload, response jet, or source content.
Its group membership lists contain retained IDs only.

With fixed occupied groups, matrix storage does not grow with record count.
The linear tier uses `O(r d² + r²)` rational entries for each stage and group.
The quadratic tier uses `O(r²d² + r²)` entries.
Exact counts include the constant response term and are documented in `QUADRATIC_CONTROL.md`.
Record metadata uses `O(N L)` bindings.
Group membership uses `O(N)` IDs.
Byte cost also depends on integer bit lengths.

Deletion checks supplied source content against its committed digest.
It regenerates intrinsic moments for deleted records only.
It checks each contribution digest before exact subtraction.
It rejects a changed extractor result or availability marker.
No individual retained moment must be reconstructed for proposal construction.

Each stage uses the new certified ancestor prefix.
Each proposal binds the target, stage, prefix, group membership, and aggregate statistics.
The service preserves signed uncertainty during selected replay.
Replay replaces a proposal with the exact target Gram.
A finite sequence of replay steps reaches exact fallback.

Within its selected state family and tier, successful repair returns the same canonical bytes as fresh retained construction.
Different state schemas need not have identical canonical bytes.
Their complete quantized model remains the same fixed target.
Repeated deletion has the same logical-state guarantee.
Deletion order does not change those bytes.
The service keeps transient proof traces outside committed state.
It does not keep persistent source or individual-moment caches.
Fixed callbacks must also avoid hidden record caches.

Input state remains immutable after success or failure.
This is a guarantee about committed logical state.
It does not securely erase caller-held objects, storage snapshots, or process memory.
The service assumes trusted construction or authenticated state storage.
SHA-256 checks bind content under collision assumptions.
Hashes alone do not authenticate hostile state replacements.

## Numerical target

Oracle V treats finite neural outputs as exact dyadic numbers.
It uses exact Grams and rational rounding decisions.
The original decoder pins its scalar binary64 program and runtime.
Its built-in shortcut proves unchanged finite inputs.
Other prefixes cause replay unless another sound provider supplies evidence.

The certified decoder defines a separate finite program with certified primitives.
It does not assume that host transcendental functions have correct rounding.
The affine response provider checks its supported chart and numerical domain.
The box provider instead checks coordinate membership in a fixed full-grid domain.
Unsupported prefixes or failed enclosures cause replay.
This scope does not cover arbitrary PyTorch, CUDA, or GPTQ kernels.

A checkpoint adapter maps architecture and parameter values into the declared decoder.
Parameter compatibility does not establish equality with the source framework's floating outputs.
Oracle E remains a distinct floating Gram and factorization program.
No V certificate establishes equality with E automatically.

## Work and fairness

The aggregate proposal avoids an individual descriptor scan.
The complete service still validates and rebuilds `O(N L)` metadata.
It also serializes the complete retained state.
Those costs have separate ledger events.
No sublinear complete-service claim follows from compact proposals.

Engine counters describe service events.
Separate telemetry times declared spans and records bounded available numerical decisions.
It does not recover every callback cause or rational bit operation.
Full comparisons must include setup, extraction, validation, replay, factorization, output, serialization, and cleanup.
The scheduler does not automatically preempt this service or GPU kernels.

Full-state direct fresh construction, ordinary model-only fresh, and equally indexed fresh remain distinct required comparisons.
The full-state oracle checks canonical state; the model-only control avoids unnecessary deletion-index construction.
Across families, `target_model_bytes` compares the common target and every stage code.
An equally indexed fresh solver can use these response summaries.
Report storage, preparation, deleted-side regeneration, all fallbacks, and lifetime costs.
Software correctness checks do not establish practical speedup.
Research experiments remain paused.


## Historical revision 6 extension

This section records the revision 6 implementation checkpoint.

The fixed-box route is documented in BOX_THEORY.md and report Sections 28–30.
It removes the affine-span condition for frozen-grid ancestor parameters.
Rank-zero intervals still require finite error bounds and valid decision certificates.
Hybrid midpoint anchors minimize the rectangular interval feature envelope.
They avoid a separate finite base evaluation for varying domains.
No acceptance dominance or practical speed follows.

The provider stores d²+6 rational slots per occupied stage group.
Its full-grid domain stores 2P_A rational endpoints.
Metadata, exact arithmetic size, base weights, replay, and output remain costs.
Lazy parameter wrappers reduce temporary construction without changing scalar operations.

The v6 runner supports four mechanism modes and exclusive component telemetry.
The worker isolates complete comparisons and enforces declared process limits.
Workload scores use original-state evidence only.
Inventories bind source hashes, configurations, roots, requests, repetitions, and method order.
The analyzer rejects mixed mode/chart/service identities within a stratum.

These changes preserve the fair indexed solver and canonical state target.
They do not close real-model feasibility, full-service timing, or useful NLP evidence.
The revision 6 checkpoint passed 261 correctness tests.
`VALIDATION_V6.md` preserves that historical validation record.
Use `VALIDATION_V7.md` for the later historical revision 7 log and source hashes.
See RESEARCH_TODO.md for remaining required tasks.


## Revision 7 service choices retained in revision 8

`ChartRecipe(response_tier="quadratic")` selects full affine-response Gram moments.
The default remains the compact linear tier.
The quadratic tier contracts all signed tangent cross terms and retains the complete feature-error bound.
It then uses the implemented absolute-error decision certificate.
It does not automatically implement the stronger whitened local-radius theorem.
Its storage and extraction costs are explicit ledger entries.
No acceptance or latency dominance follows merely from retaining more moments.

`make_service(..., verifier_policy="spectral_or_interval")` adds an interval decision route after spectral rejection.
The route preserves signed covariance endpoints and uses the true target ridge during interval elimination.
Every coordinate must satisfy the frozen rounding cell and lower-tie rule.
Invalid or empty evidence raises an error; unresolved valid evidence permits replay.
The default spectral route still returns immediately when it succeeds.
The policy remains outside canonical state and must be bound in the run configuration.

`make_identity_service(decoder, target)` constructs the separate identity-cache comparison family.
It stores one true sequential Gram per stage under the current quantized model.
It subtracts deleted contributions only when all required transitive ancestors remain identical.
Otherwise, it rebuilds the retained stage Gram under the new prefix.
Each successful request refreshes the complete cache to match direct fresh construction.
The optional cache stores no per-record matrices or source payloads.
Its bounded trusted-origin registry remains a separate runtime cost.
Repair and indexed fresh receive identical cache information and use the same solver.

## Historical revision 7 execution paths

This section preserves the former execution boundary and its then-open gaps.
Revision 8 supersedes the implementation-status statements below.

The warm comparison runner supports independent empty and complete deletion controls.
The local sequence runner prepares one original state and consumes successive committed repair states.
It verifies model and same-schema canonical state against independent fresh retained construction at every step.
It preserves original normalization and records all planned requests after a failure.
Restart verifies every completed predecessor and artifact before reusing the saved prefix.
Bulk campaign sequence dispatch remains unimplemented.

The isolated runner creates one setup worker and one worker for each method.
Repair and indexed fresh load the same saved original state.
Direct fresh does not load that unnecessary state.
The parent compares complete artifacts after each worker seals its child receipt.
A missing durable outer timing record prevents cached-child success during recovery.
A fully sealed worker retains its original timing and CPU debit on restart.

The worker timer includes startup, input loading, service work, artifact output, child commit, exit, and cleanup.
It excludes parent verification and the enclosing worker-control and parent receipt commitments.
Original preparation is separate, and isolated execution does not compute heldout quality.
Operating-system caches remain uncontrolled.
Read `ISOLATED_COMPARISON.md` before comparing its timings with warm-arm records.

The protocol-scoped CPU ledger reserves each worker's allowance before launch.
It retains unknown charges and records observed overruns without clipping.
It limits admission, not global physical CPU or arbitrary process trees.
A separate feasibility-phase label and cross-protocol accounting remain unimplemented.

All new paths retain the research pause.
No current control establishes real-model feasibility, useful certificate coverage, NLP quality, or reliable full-service speedup.

## Current revision 8 execution paths

`model_fresh.fresh_model` follows the complete sequential target with no response chart,
deletion metadata, or persistent Gram cache. Its CLI commits `model.json`, a manifest, and a result receipt.
It uses the same certified finite evaluator and exact quantizer, with independent replay control flow.
It is not an independent numerical library or a native framework implementation.
The fixed normalization and ridge-only empty-retained target remain unchanged.
The baseline skips heldout loading but parses the original calibration manifest before removing requested records.
This parsing cost is real; the implementation is not a lower bound on all possible requantizers.
Research execution requires exact-command CPU admission, and standalone confirmation requires future inventory support.
See `MODEL_ONLY_FRESH.md`.

Frozen isolated inventories now bind complete confirmation products and authorize membership checks in each child.
Optional `heldout_nll` quality work uses a separate limited process after method outputs agree exactly.
It evaluates base, original, retained fresh, and repaired models with separate timing and CPU debit.
Those finite losses are diagnostic; they establish neither useful absolute quality nor native inference equivalence.
Frozen sequence inventories now dispatch one limited process per ordered sequence.
Original preparation occurs once, committed predecessor lineage is checked at every step,
and failures retain all later planned outcomes. Each step's method arms remain warm.
See `ISOLATED_CAMPAIGN.md` and `SEQUENCE_CAMPAIGN.md`.

The external observer measures from source/input preflight through child-controller commits,
exit, cleanup, and output/source verification. Its final receipt follows the stop timestamp.
Observer bootstrap and receipt lookup also precede the interval.
The disjoint outer partition sums exactly to the enclosing clock; service timers remain nested diagnostics.
Canonical-state, model-only, comparison, and sequence contracts cannot be interchanged.
Single-role measurement does not independently establish equality with the external research oracle.
Fresh, resumed, and reused archival observations retain different labels and eligibility.
Primary campaign, analysis, and matched lifetime integration of the complete clock remain open (D04).
See `TRANSACTION_TIMING.md`.

Bounded certificate records retain exposed domain, descriptor, finite-bound, decision, replay,
and completion outcomes outside canonical state. Exact values use bounded rational pairs or magnitude summaries.
Counts expose dropped detail. Provider internals and unavailable decompositions remain unknown (partial C05).
The arithmetic audit observes constructed Fraction endpoints in its calling thread and process,
alongside available memory and artifact diagnostics. Hidden integer/native intermediates,
object lifetimes, complete memory attribution, and separate child execution remain outside that scope (partial D05).
Profiled records are excluded from clean timing ratios even without their sidecar.
See `CERTIFICATE_DIAGNOSTICS.md` and `ARITHMETIC_AUDIT.md`.

The shared admission ledger supports feasibility, development, confirmation, and software-test phases.
Protocol 4 plans 3, 12, and 64 worker CPU hours for the three research phases.
Unknown attempts retain their reservation and observed overruns remain charged.
No controller-CPU, cross-protocol, hostile-descendant, or global physical-resource ceiling follows.
Changing output directories does not reset the same protocol's debit.
Per-process address space is not measured RSS or a process-tree memory bound.
Operating-system caches remain uncontrolled across every execution mode.

Only the written feasibility policy C04 closes in revision 8.
It requires exactness, resource limits, useful changed-ancestor feature avoidance, quality,
preparation, and a strict three-request lifetime gain over ordinary model-only fresh on every feasibility root.
Its attainment and all real-model evidence remain unmeasured.
Use the sealed revision 8 validation record for current correctness evidence;
historical test counts and the unchanged report PDF do not validate changed source.
