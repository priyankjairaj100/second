# Prospective empirical protocol

Version: 5. Date: 4 October 2026.

This document reconstructs the empirical plan from the current implementation.
It does not recover the missing earlier protocol.
No empirical observations accompany this document.
Experiments remain paused.
Software correctness fixtures remain separate from research evidence.

`configs/protocol_v5.json` stores the current numerical planning choices.
Versions 1 through 4 preserve earlier preparation plans.
All versions retain the compatible `calibration-protocol-v1` schema.
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

The ordinary requantization baseline is `model_only_fresh`.
It returns the quantized model without constructing deletion state.
The equal-information maintenance baseline remains `indexed_fresh`.
The complete-state correctness oracle remains `direct_fresh`.
Those output contracts answer different questions.
A gain against full-state reconstruction alone cannot establish faster ordinary requantization.
A tie against equally indexed fresh prevents a deletion-exclusive solver claim.
The measured primary and ordered-sequence inventories now authorize model-only confirmation only through actual frozen membership and exact live phase admission.
No real empirical inventory has been frozen.
No current implementation result establishes a reliable speedup.

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
Feasibility uses only the development-side pool.
It must not consume confirmation or evaluation documents.
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
`src/worker_control.py` enforces explicit limits before each bounded worker starts.
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
The proposed preflight and feasibility worker deadline is 15 minutes.
Later workers have a proposed 60-minute deadline.
The measured primary path applies these limits separately to each preparation, method, and requested quality worker.
Each worker requires its own reservation; the observer and campaign controller remain outside that child CPU allowance.
The proposed CPU limits are 900 and 3,600 seconds per worker.
These choices do not establish real-model feasibility, and final affinity and limits remain unresolved.
The proposed file limit is 512 MiB per written file.
The proposed thread setting is one.
Resolve supported CPU affinity identifiers before freezing the inventory.
The feasibility stage permits at most three CPU-hours.
Development permits at most twelve CPU-hours.
Confirmation permits at most sixty-four CPU-hours.
Stop admission when the next complete worker allowance does not fit.
The campaign now applies this rule for its supported phase labels.
Supported phase labels now include feasibility, development, confirmation, and software test.
Feasibility requires its own explicit three-hour admission cap.
The new phase label creates no source pool or model-run authorization.
Keep every unstarted planned run in the result inventory.

Use one timing repeat during preflight and feasibility.
Version 5 prospectively uses four paired repeats for development and confirmation.
This change gives the four actual timed methods one complete position block.
It is a planning choice, not a precision or power result.
Use the saved seeded four-method permutation with cyclic rotations.
Each complete four-repeat block places every method once in each position.
The next block reverses orientation.
A partial block does not guarantee exact position balance.
Record CPU affinity, thread settings, runtime versions, and system load.
Measured inventories require a runtime contract from `src/runtime_contract.py`.
It binds interpreter and selected standard-library contents, architecture, binary64, OS/kernel, selected execution flags, and numerical runtime limits.
`configs/runtime_reference_v1.json` describes the current software environment only.
It is not the final empirical hardware pin and proves nothing about identical physical hardware, caches, system load, or complete native dependencies.
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
`src/measured_sequence.py` now implements the measured ordered path.
Its plan fixes the original calibration input and normalization, cumulative fresh targets, incremental repair requests, and preceding committed state.
It separately measures one original canonical preparation and one original model-only preparation.
Repair and indexed fresh share the former observation; the ordinary comparator pays the latter.
Four fresh processes execute the four roles at each step under matched observer boundaries.
A dedicated optional quality worker stays outside method clocks.
The inventory binds the configuration × root × sequence × repeat product and frozen method/preparation orders.
Its schema is `calibration-measured-sequence-campaign-v1`.
A failed step preserves its observations and every unstarted later step.
Restart reuses the original sealed timings; incomplete lifetime totals remain null.
The legacy `src/sequence_runner.py` and `src/sequence_campaign.py` retain their separately labeled warm-step contract.
They cannot supply measured primary lifetime evidence by relabeling their worker clocks.
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

The existing three-method comparison contains repair, equally indexed fresh, and direct fresh.
Each method produces the same declared model and canonical state within its family and tier.
Use the same target manifest and retained identifiers.
Give equally indexed fresh the same valid summaries and storage allowance.
Record any unavoidable information difference.

`src/model_fresh.py` adds the separate ordinary requantization output contract.
It evaluates retained features, forms temporary exact Grams, and quantizes every stage.
It constructs no response chart, persistent cache, or deletion state.
Its common target encoding includes every stage code without a family-specific state digest.
Compare these complete model codes across output families.
Use `direct_fresh` separately when validating the full live state.
`docs/MODEL_ONLY_FRESH.md` specifies the baseline and its remaining inventory limitation.
The baseline skips heldout loading during quantization.
It still pays for parsing the original calibration manifest before applying deletion.

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
Model-only fresh has that separate output contract and timing row.
Its research execution requires exact-command phase admission.
Standalone confirmation without actual supported inventory evidence remains blocked.
The measured request and ordered-sequence dispatchers now provide that evidence path.
Amortize preparation only in the separately declared lifetime analysis.

## 8. Timing boundaries and instrumentation

The primary path is `src/measured_comparison.py`, with inventories in `src/measured_inventory.py`.
Each plan freezes all four timed methods: model-only fresh, repair, indexed fresh, and direct full-state fresh.
Every method executes in a fresh limited child under the same complete observer boundary:
`observer_source_validation_through_child_exit_controller_commits_cleanup_and_output_validation`.
Its cache label is `measured_method_transactions_os_cache_uncontrolled`.
The child includes required loading, extraction, proof, replay, arithmetic, validation, metadata, serialization, output, and child commit.
The enclosing observer also includes source/input verification, admission, startup, exit, cleanup, worker accounting and receipt, and output verification.
Disjoint accounting spans must sum exactly to the enclosing duration.
Do not add nested service timers to that duration.

The observer's final tree-snapshot files and receipt writes follow the stop timestamp and are excluded.
Parent plan validation, setup, common-model comparison copies, cross-method equality, optional quality, and the final comparison receipt are separately reported.
These exclusions are explicit and symmetric; required online work cannot be moved into free research bookkeeping.
The comparison's total wall time is not a method latency.
The method clock does not claim every physical action an external service user might perform.
Observer/controller CPU remains outside the admitted child-process CPU allowance.
See `docs/TRANSACTION_TIMING.md` and `docs/MEASURED_COMPARISON.md` for the complete contract.

Model-only fresh constructs no deletion index and does not load charts or heldout tokens.
Direct full-state fresh constructs its required state but does not read the original state.
Repair and indexed fresh load the same original or preceding state.
Non-quality canonical-state arms skip heldout loading.
All current arms parse the original calibration input before filtering deletions; this is not an optimized retained-only reader.
Setup failure preserves attempts by both independent fresh baselines and leaves dependent methods explicitly unstarted.

A primary measured plan freezes `execution_mode="clean"`.
The observer and complete child both enter the clean instrumentation scope.
Saved entry/exit facts verify supported Python profile/trace hooks and allocation tracing are absent.
Optional service telemetry and canonical-state integer-size scans are disabled.
Required arithmetic counters, exact checks, hashing, and durable output remain charged.
Native profiling is unobserved, and machine load and OS page caches are uncontrolled.
A fresh process is not proof of cold disk caches.
Do not combine cache modes or call these observations disk-cold.

Detailed certificate coverage comes from a separate `execution_mode="diagnostic"` plan and output directory.
That replicate must bind the same target, algorithm, root, request, retained membership, ancestor codes, and actual model/state outputs.
It has its own observer and worker identities and remains outside clean latency ratios.
An available funnel is not automatically complete: omissions, saturation, missing predecessor codes, or missing groups leave coverage inconclusive.
Bounded certificate diagnostics and arithmetic endpoint profiles retain their scopes in `docs/CERTIFICATE_DIAGNOSTICS.md` and `docs/ARITHMETIC_AUDIT.md`.
They neither observe every hidden arithmetic temporary nor prove exact live rational memory.

Optional `quality="heldout_nll"` adds a separate admitted quality worker.
It evaluates base, original, retained-direct, and repaired outputs on the same heldout tokens after exact model/state agreement.
Its binary64 NLL is a diagnostic observation, not native-framework equivalence or certified population language quality.
Its cost and resource use remain visible outside each method clock.
Requested quality failure makes the comparison unsuccessful while preserving completed method observations.

The legacy warm runner and v8 isolated runner remain available under their original boundaries.
Warm arms share process history; v8 isolated clocks exclude later controller commits.
Neither is silently promoted to this v9 primary transaction contract.
Implementation and correctness fixtures establish the contract's behavior only.
Actual clean model-scale latency, resources, and useful speed remain unmeasured.

## 9. Exactness, failures, and restart

Every successful primary comparison requires the same target binding and every exact stage code across all four methods.
Repair, indexed fresh, and direct fresh must additionally match complete canonical state, service manifest, and chart within their declared family and tier.
State equality is inapplicable to model-only fresh and must remain null.
Across different state families compare common model output and all required storage, not incompatible state encodings.
Any mismatch stops performance interpretation of the affected method version.

A rejected certificate can fall back to exact replay and still finish correctly.
An evaluator failure, mismatch, invalid output, timeout, memory failure, interruption, denied budget, or missing planned result cannot produce an exact completed latency.
Keep consumed time visible as consumed time; it is not time to an exact answer.
No slow or difficult request disappears from the frozen denominator.
Only predeclared malformed-source exclusions occur before sampling, with their reasons recorded.

A sealed controller receipt can contain failed outcomes.
Inspect `outcome` and every role status instead of treating top-level completion as success.
Every planned run and all four methods remain represented after failure.
Partial failed archives, their files, and absence of outputs are bound too.
Terminal resume verifies source/runtime/input bindings, observer and worker receipts, CPU ledger debits, child artifacts, and exact comparison outputs.
A saved observer retains its original duration and cannot become a new repetition.
A committed child with a missing complete observer receipt cannot become a short cached success.
These checks assume trusted local storage; hashes alone cannot authenticate hostile rewriting of all evidence.

## 10. Frozen inventories and analysis

`build_measured_campaign` freezes the independent-request inventory.
`build_measured_sequence_campaign` separately freezes ordered sequences.
Primary inventories bind every configuration, root, request, repetition, method order, target, runtime contract, source digest, limit, and instrumentation policy.
Sequence inventories additionally bind ordered request provenance, cumulative membership, predecessor semantics, and preparation order.
Actual inventory membership is verified at the controller and leaf before model loading.
A Boolean grant or copied run ID cannot authorize confirmation.
Every research leaf also requires exact-command live CPU admission.

Canonical embedded manifests clear only `protocol.sha256` to avoid a digest cycle.
The final protocol binds the exact inventory bytes; actual raw manifests then bind that final protocol hash.
All other embedded fields remain immutable.
The measured source map includes every `src/*.py` and `scripts/*.py` file.
Changed sources, runtime, inputs, target, order, or instrumentation invalidate reuse.
Confirmation requires a frozen unblocked protocol and the complete declared Cartesian product.
The prospective v5 file deliberately leaves actual configuration IDs, selected configuration, and inventory digest unresolved.
Implementation support is not a real frozen research inventory.

`src/measured_analysis.py` independently verifies artifacts before issuing typed measured evidence.
It rereads observer/child receipts, exact model/state artifacts, input bindings, phase accounting, and timing partitions.
Assertions in convenience fields alone cannot establish equality or latency.
It rejects reusing one underlying observer as multiple planned repetitions.
Missing and failed slots remain explicit; malformed sealed evidence raises an error rather than contributing a ratio.
The older `result_analysis.py` retains its separate warm/state-only contract.
See `docs/MEASURED_ANALYSIS.md`.

Reduce paired timing repetitions to a median for each request.
A conditional speed ratio admits a request only when both methods finish every planned repetition exactly with the required clean child and observer contract.
Compute log(baseline/candidate), average request values within each root, then average roots with equal weights.
Exponentiate that mean and report all planned success/failure counts beside it.
Keep controls and extensions separate from primary requests.
Do not present the conditional ratio as an unconditional reliability guarantee.

Use 2,000 deterministic bootstrap draws over independent calibration roots and the central 95% percentile interval.
Timing repeats and requests do not increase the number of independent roots.
One root provides no reported interval.
Twelve confirmation roots and four repeats are prospective planning choices, not guaranteed precision.
Use development variability to justify the confirmation design before freezing it.
Any expansion or revision must precede observation of confirmation outcomes.

The sole declared primary comparison is model-only fresh versus repair.
Indexed fresh is the equal-information maintenance comparison; direct fresh remains the full-state correctness oracle.
Only the prospectively declared configuration/comparator under frozen confirmation and complete exact clean planned outcomes can receive primary confirmation flags.
Other matrices remain secondary; any multiple-comparison inference needs a separately declared correction.
Source independence, data provenance, useful language quality, complete mechanism coverage, and statistical precision remain separate obligations.

## 11. Ordered lifetime cost

`src/measured_sequence.py` provides one complete original canonical preparation shared by the repair/indexed controls and a separately measured original model-only preparation.
Those original models must agree before requests begin.
Method and preparation orders are frozen and counterbalanced across repetitions.
Each request uses the predecessor's committed live state for repair and indexed fresh, and cumulative retained-data construction for both independent fresh controls.
The leaf validates the preceding trusted lineage and required state inside its transaction.
It does not read prior oracle/observer archives as an online dependency.
Research archive verification checks those separately.

Let P_R be original model-plus-index preparation and P_F be original model-only preparation.
For the fixed horizon H, let R_h and F_h be complete repair and ordinary fresh transaction costs.
Then the exact accounting identity is

\[
T_R(H)-T_F(H)=(P_R-P_F)-\sum_{h=1}^{H}(F_h-R_h).
\]

Strict lifetime gain holds precisely when request savings exceed preparation debt.
Repair and indexed fresh each count their shared preparation once within their own system total.
Ordinary fresh counts its own separate preparation once.
Independent oracle, cross-method equality, quality, and research lineage bookkeeping remain separately reported and symmetric.
The lifetime sum is an attributable transaction-cost estimand, not elapsed runtime of the validation harness.

Analysis independently resums saved original observations.
Any required failed or missing preparation/request makes the complete lifetime null.
Keep completed and failed consumed costs visible rather than replacing unknown terms with zero.
Report the full declared horizon and final balance, including an early crossing that a later expensive request reverses.
A projected constant-saving crossing requires its stated assumption; it is not observed permanent break-even.
Storage remains a separate budget unless a cost model is declared.
Neither coverage nor a source-cache hit establishes positive complete cost savings.

## 12. Prospective decision policy and evaluator

`configs/feasibility_gates_v1.json` remains byte-for-byte unchanged.
Its fixed C04 engineering policy has hash `3fe1488125f86d04857a17e99bda41fe8be6e1cf900476389850bedb04c7bea1`.
Threshold attainment remains unknown.
The policy promotes development only and supplies neither confirmation power nor reliable population speed.
`src/feasibility_decision.py` implements a fail-closed deterministic decision over supplied evidence; see `docs/FEASIBILITY_DECISION.md` and `docs/FEASIBILITY_GATES.md`.

| Gate | Fixed criterion | Failure action |
| --- | --- | --- |
| Exactness | Zero mismatches and no invalid successful commits | Stop the affected implementation |
| Completeness | Every planned root/request and required artifact present | Leave the gate open |
| Coverage | Avoid retained target-feature evaluation for at least one quarter of changed-ancestor groups on every feasibility root | Improve bounds or narrow scope |
| Resources | Fixed worker allowances, observed memory/artifact limits, complete costs, and three worker CPU-hours | Redesign within remaining allowance or narrow scope |
| Quality | Retained mean NLL minus base mean NLL at most log(6/5), on identical positive heldout tokens for every root/request | Revise configuration prospectively or narrow scope |
| Lifetime value | Complete three-request repair lifetime strictly beats model-only fresh on each root, including each system's preparation | Redesign cost or narrow scope |
| Confirmed speed | All planned requests exact and lower 95% ratio interval strictly above 1.05 | No reliable-speed claim |

The fixed feasibility workload has two roots, eight records per root, 32 tokens per record, and three sequential requests.
Each worker has 900-second wall and CPU limits, 6 GiB address-space and observed-RSS ceilings, and 512 MiB maximum artifact size.
Each original preparation must finish within 900 seconds; each compared complete lifetime within 3,600 seconds.
Changing those values requires a new prospective policy version.

Coverage includes every nonempty retained stage group under actually changed transitive ancestor codes across all planned requests.
The evaluator reconstructs ancestor changes from complete saved stage maps.
A cache hit alone is not feature avoidance.
A zero denominator means the mechanism was not demonstrated.
Missing, truncated, saturated, or mismatched diagnostic evidence is inconclusive.
Separate diagnostic replicates must match clean target, configuration, retained membership, predecessor codes, and actual model/state artifacts.

Quality requires identical evaluator and heldout bindings and equal positive scored-token counts.
The finite NLL comparison uses a rational enclosure of log(6/5); an unresolved boundary is inconclusive.
This certifies the comparison of recorded finite numbers, not the underlying loss computation or population quality.
Perplexity alone is insufficient downstream NLP evidence; a supported application still needs an appropriate task metric.

The evaluator checks complete preparation and request boundaries, resource identities, and no reused clean observations.
The implemented `evaluate_verified_feasibility` adapter requires loader-issued `VerifiedMeasuredEvidence` and checks complete sequence timing, preparation, source, target, configuration, membership, stage-code, state, and worker projections.
The public `src/feasibility_archive.py` bridge additionally derives supported timings, model/state agreement, diagnostic coverage, and quality from loader-issued clean and matched diagnostic archives.
It does not accept naked caller assertions as a promotion route.
Scientific workload provenance, a complete exported shared phase ledger, and nontransaction artifact-size coverage remain explicit blocking obligations.
The pure conditional evaluator still requires its declared premises; it is not a substitute for that archive bridge.
Any conditional pass leaves empirical attainment, execution authorization, confirmation, and population speedup false; independent integration review remains separate.
No decision engine manufactures evidence, proves source independence, or completes bounded funnel omissions.
No empirical gate pass has been recorded.

## 13. Artifacts and remaining work

Store immutable input manifests and raw outcomes, separating unfinished and committed transactions.
Preserve source, runtime, protocol, target, tokens, lineage, model, state, worker and observer identities, and every failed/unstarted slot.
Record original workload-score preparation and storage costs separately.
`scripts/summarize_measured.py` reads the measured artifacts without model execution.
Older summaries keep their distinct contracts.
Software fixtures and profile numbers are not paper observations.

Research execution still requires:

- A resource-feasible real checkpoint and validated adapter, with actual local checkpoint, tokenizer, and corpus hashes.
- Frozen document boundaries, chunks, normalization, positions, masks, and disjoint source pools, with saved independent root draws.
- Real original-state scores and complete preparation costs.
- One selected primary target/chart/family/tier/verifier configuration, plus predeclared controls.
- Final worker affinity, limits, empirical runtime/hardware conditions, and clean real-model resource measurements.
- Complete diagnostic coverage and quality artifacts linked to the clean outputs without counting diagnostic times as primary latency.
- Actual frozen measured request and ordered-sequence inventories with explicit confirmation configurations.
- Development-based justification of confirmation precision and real attainment of the fixed feasibility policy.
- The user's instruction to resume research experiments.

Four-method measured confirmation admission, matched sequence lifetime execution, clean child/observer scopes, and artifact-aware analysis now have implementation paths.
They remove those infrastructure-only blockers, subject to final integration checks.
They do not supply missing real inputs, practical acceptance, memory fit, language quality, or speed.
The identity-cache, quadratic, interval, and parameter-box alternatives remain controls whose practical value is unmeasured.
No reliable full-model repair speedup follows from this revision.
