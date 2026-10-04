# Remaining research program

Updated 4 October 2026.
Revision 7 preparation builds on commit `3c6905e77bca86e4d3e54be20a82f3acdcfd294d`.
This register covers the path from the current reference implementation to a submitted ACL paper.
Every unchecked item remains open.
This implementation update does not resume experiments.
Checked items meet their stated preparation scope.
Unchecked items can contain partial work; see the progress table below.
Synthetic empirical datasets remain deferred.

The main unresolved question is practical value on real language models.
The affine provider requires exact chart membership for installed ancestor weights.
The new fixed-box provider covers frozen-grid prefixes without derivatives.
Coverage does not establish useful numerical bounds or certificate acceptance.
Correct replay handles rejection, but it can remove the expected speed benefit.

**Completed baseline**

- Reviewed changed-prefix induction and full Taylor remainder.
- Reviewed compact Gram bounds and canonical repeated deletion.
- Reviewed conditional work guarantees and their comparator limits.
- Implemented compact aggregate state and automatic certificates for `V_cert`.
- Implemented local GPT-2 safetensors loading.
- Passed 129 correctness tests with source hashes.
- Verified one deletion-induced early change without retained-record reads.
- Saved the v4 report and complete restart context.
- Added the v5 target/chart constructors, bounded reload, fair indexed solver, and atomic local runner.
- Added failure-aware analysis, a prospective protocol, and the T1–T7 publication sequence.
- Passed 197 correctness tests, including a fresh-process reload check.
- Updated the v5 report to 28 pages and corrected partial-evaluator fallback wording.
- Added fixed-box certificates, midpoint anchors, and lazy parameter wrappers in revision 6.
- Added worker limits, exclusive telemetry, mechanism controls, request laws, and bound campaign inventories.
- Extended the report with box proofs, storage counts, limits, and execution boundaries.
- Added full quadratic response storage with the same complete numerical target.
- Added a separate true-model Gram cache with current-ancestor identity checks and exact replay.
- Added an optional interval verifier after the existing spectral certificate.
- Added ordered local deletion, complete-deletion controls, and verified predecessor restart.
- Added protocol-scoped CPU admission and separate limited processes for individual comparison methods.
- Added final-state integer-size diagnostics and a deterministic vector repair diagram.

These results need no repetition without a concrete change or unresolved risk.
No current real-model benchmark supports a practical speed claim.
Earlier raw measurements remain unavailable.

**Priority and dependencies**

| Priority | Meaning | Start condition |
| --- | --- | --- |
| P0 | Define the target and prepare a valid experiment path | Can proceed while research experiments remain paused |
| P1 | Establish feasibility and real-model correctness | User resumes experiments; required P0 items are complete |
| P2 | Run frozen confirmation and explain the results | Feasibility passes; methods and analysis rules are frozen |
| P3 | Complete the manuscript and reproducibility release | Confirmatory evidence and claim decisions are available |
| C | Conditional extension | A measured blocker or an explicit paper claim requires it |

Writing and proof organization can proceed before experiments.
The priorities identify dependencies, not mandatory serial execution.
No task authorizes external compute or hardware from another project.

**A. Freeze the scientific target — P0**

- [x] **A01. Select the primary numerical target.** Recommend `V_cert` for the implemented certified path. State its deployment scope explicitly.
  Completion: one target identity governs the main theory, algorithms, and exactness experiments.
  Evidence: docs/TARGET_CONTRACT.md selects V_cert; legacy targets remain distinct.
- [x] **A02. Freeze every quantization choice.** Specify grids, order, ties, ridge, normalization, parameter conversion, and fixed parameters.
  Completion: an immutable manifest resolves every branch that can affect the returned model.
  Evidence: src/target_manifest.py constructs and binds fixed target choices.
- [ ] **A03. Freeze the feature contract.** Specify tokenizer, record boundaries, token order, masks, positions, runtime, and operation schedule.
  Completion: deleting records cannot silently change packing or another record's input definition.
- [x] **A04. Freeze the deletion interface.** State whether requests contain identifiers, deleted payloads, or authenticated contributions.
  Completion: the service obtains required deleted content before erasure and charges its retrieval.
  Evidence: The service accepts verified deleted payloads; the runner charges resident-source lookup and extraction.
- [x] **A05. Freeze the state and output contract.** Specify full model output, retained bindings, group sums, source storage, and snapshots.
  Completion: fresh and repair return the same defined state; trust and logical-erasure limits are explicit.
  Evidence: Bounded state loading and docs/BASELINES.md define canonical live state and trusted storage.
- [ ] **A06. Fix the intended claim and resource budget.** Specify supported model scope, memory limits, preparation limits, and allowed execution resources.
  Completion: the proposed headline names its target, comparator, workload, and success measure.

**B. Consolidate the publication theory — P0, then P3**

- [x] **B01. Correct unconditional fallback language.** The previous Section 16 statement omitted finite-evaluation conditions.
  Completion: every relevant statement requires successful finite evaluation; evaluator failure causes an explicit abort.
  Evidence: Report opening, completion theorem, state theorem, scheduler interface, and claim table now state execution conditions.
- [x] **B02. Build one theorem sequence.** Connect finite feature bounds, Gram bounds, discrete decisions, sequential exactness, canonical state, and conditional work.
  Completion: symbols and assumptions remain consistent across the main text and supplement.
  Evidence: docs/PUBLICATION_THEORY.md orders T1–T7 and maps the existing report proofs.
- [x] **B03. Map theorems to executable checks.** Identify each bound, recorded quantity, rejection reason, and fallback action.
  Completion: distinguish the stronger quadratic theorem from the implemented shifted linear acceptance rule.
  Evidence: docs/PUBLICATION_THEORY.md and docs/CLAIM_EVIDENCE.md map checks and separate acceptance rules.
- [x] **B04. State the finite error floor.** Include jet errors, numerical errors, and any residual errors.
  Completion: the second-order claim states when those terms prevent second-order scaling.
  Evidence: Publication T1–T3 and the finite-floor discussion distinguish local order from nonzero error terms.
- [x] **B05. Complete the work and storage model.** Count directions, mixed derivatives, fitting, metadata, integer sizes, replay, output, and preparation.
  Completion: no complete-service bound silently treats these terms as free.
  Evidence: The publication work model lists representation, arithmetic, metadata, replay, and complete-service costs.
- [x] **B06. Fix the reliability estimand.** Define request distributions, successful requests, aborts, timeouts, and the latency statistic.
  Completion: deterministic guarantees and statistical claims have separate scopes.
  Evidence: The publication reliability definition and prospective protocol retain aborts, timeouts, and missing planned attempts.
- [x] **B07. Create a claim-to-evidence map.** Include exactness, storage, coverage, speed, quality, and novelty.
  Completion: each claim points to a proof, software check, or new measurement.
  Evidence: docs/CLAIM_EVIDENCE.md separates proved, tested, and unmeasured claims.

**C. Make the certificate useful — P0 design, P1 feasibility**

- [x] **C01. Specify a reproducible chart constructor.** Select directions and radii independently of the deletable corpus.
  Completion: a manifest records the construction, provenance, rank, direction bytes, and preparation cost.
  Evidence: src/chart_construction.py supplies deterministic stage-rtn, coordinate, and none recipes with provenance and resource counts.
- [ ] **C02. Establish chart coverage as the first research gate.** Measure the complete installed prefix against the fixed chart.
  Completion: quantify residuals and radius violations; small deletion size is never used as a substitute for this check.
- [x] **C03. Define the response when chart coverage fails.** Choose residual certificates, independent charts, another sound construction, or a narrower claim.
  Completion: the selected route has sound bounds and canonical deletion semantics before confirmation.
  Evidence: Fixed parameter boxes have intrinsic additive state and reviewed finite bounds; useful acceptance remains unmeasured.
- [ ] **C04. Set feasibility thresholds before tuning.** Include exactness, coverage, memory, quality, preparation, and full service cost.
  Completion: written thresholds determine whether to continue, redesign, or narrow the paper.
- [ ] **C05. Record the complete coverage funnel.** Track chart fit, available descriptors, finite bounds, accepted stages, replayed groups, and model completion.
  Completion: every rejection has a stable reason and remains in the workload.
- [ ] **C06. Select a target-preserving performance route.** Use measured bottlenecks to guide changes to arithmetic, extraction, or model loading.
  Completion: the chosen workload runs within its declared budget without weakening numerical guarantees.

**D. Build the experiment infrastructure — P0**

- [x] **D01. Add a complete experiment runner.** Connect loading, preparation, fresh quantization, deletion, repair, oracle checks, and evaluation.
  Completion: one command executes a manifest and records every stage outcome.
  Evidence: src/experiment_runner.py connects local inputs, three methods, equality checks, and diagnostic held-out loss.
- [x] **D02. Add durable state loading.** Current canonical serialization must have a validated path back into the service.
  Completion: a new process loads saved state and reproduces subsequent deletion results.
  Evidence: Bounded canonical loading passes a fresh-process deletion and retained-fresh comparison.
- [x] **D03. Add atomic restart handling.** Separate incomplete requests from committed results.
  Completion: interruption cannot produce a successful artifact or contaminate later requests.
  Evidence: src/run_store.py provides isolated attempts, atomic artifacts, immutable completion, and verified restart.
- [ ] **D04. Add complete timing instrumentation.** Existing event counters do not measure callback work or elapsed time.
  Completion: disjoint timers cover loading, extraction, proof, replay, factorization, metadata, serialization, output, and cleanup.
- [ ] **D05. Measure memory and arithmetic size.** Include fixed weights, charts, temporary jets, rational values, metadata, and output artifacts.
  Completion: logs contain peak memory, serialized bytes, precision, and integer lengths.
- [x] **D06. Define cold and warm execution.** Fix caches, thread counts, synchronization, and output policy.
  Completion: compared methods receive identical declared conditions.
  Evidence: Warm and isolated contracts bind sources, limits, affinity, threads, method order, and synchronized output.
  Scope: Isolated methods use fresh processes; operating-system caches remain explicitly uncontrolled.
- [x] **D07. Add scripts that generate tables and figures.** Read immutable run records rather than copied summary values.
  Completion: every displayed value traces to a manifest, log, and artifact hash.
  Evidence: scripts/summarize_results.py generates hash-traceable tables and optional plots from recorded inputs.

**E. Implement fair comparisons — P0**

- [x] **E01. Retain direct fresh quantization as an oracle.** Check every stage and the complete retained state.
  Completion: the fresh control path independently checks repair control decisions.
  Evidence: The runner compares every quantized stage and complete canonical state against direct retained fresh construction.
- [x] **E02. Implement equally indexed fresh quantization.** Give it the same valid summaries, caches, storage budget, and state interface.
  Completion: the comparison cannot depend on withholding reusable information from fresh quantization.
  Evidence: prepare_index and indexed_fresh share the valid retained index and repair planner.
- [x] **E03. Add an identity-only repair baseline.** Reuse features only when the relevant finite ancestors remain identical.
  Completion: changed dependencies cause exact replay under the same target.
  Evidence: src/identity_cache.py compares all current transitive ancestors and refreshes exact Grams after subtraction or retained replay.
  Scope: Its separate state family includes preparation, state, source, solver, and equal-information comparison costs.
- [x] **E04. Add fixed-reference and response baselines.** Compare constant summaries, compact linear responses, and quadratic responses where affordable.
  Completion: each method uses sound bounds and reports its full preparation and storage cost.
  Evidence: The quadratic tier stores oriented cross moments and retains the existing proved finite-error descriptors.
  Scope: Provider extraction, resource previews, arithmetic counts, serialization, and storage distinguish the tiers.
  Limit: The stronger whitened acceptance theorem and real-model affordability remain unestablished.
- [x] **E05. Add replay and verifier controls.** Compare full replay and the existing replay heuristic; isolate the cost of certification.
  Completion: every control returns the same target or carries an explicit diagnostic-only label.
  Evidence: Certified and full-replay modes share the target; exclusive telemetry isolates proof and replay work.
- [x] **E06. Decide the claim if indexed fresh ties repair.** Separate gains from indexing from gains specific to deletion.
  Completion: the paper does not claim a strict deletion advantage that the fair comparison cannot support.
  Evidence: The current planner ignores old codes; claim index maintenance value separately from deletion-specific solving.

**F. Rebuild and freeze the empirical protocol — P0**

- [x] **F01. Reconstruct the missing protocol.** The earlier 17-page empirical protocol is unavailable.
  Completion: the repository contains the current full protocol without presenting reconstructed details as recovered evidence.
  Evidence: docs/EMPIRICAL_PROTOCOL.md reconstructs the prospective plan without claiming recovery of the missing protocol.
- [ ] **F02. Select supported pretrained checkpoints.** Define useful size and architecture coverage within the resource budget.
  Completion: record revisions, parameter hashes, architecture support, and model licenses.
- [ ] **F03. Select real calibration and evaluation text.** Include source variation appropriate to the paper's claims.
  Completion: record dataset versions, licenses, record identifiers, preprocessing, and token manifests.
- [ ] **F04. Separate development and confirmation.** Keep calibration, tuning, held-out evaluation, and final request selection distinct.
  Completion: record overlap checks and freeze all data-dependent method choices before confirmation.
- [x] **F05. Define the deletion workload.** Include random, source-based, contiguous, concentrated, repeated, and difficult requests.
  Completion: each request law, fraction, sequence, and selection rule is recorded before final analysis.
  Evidence: request_workload.py defines original-only scores, random/source/contiguous laws, sequences, and controls. Execution limitations remain explicit.
- [ ] **F06. Define the quantization grid.** Vary supported precision, calibration size, context length, ridge, grouping, and chart settings.
  Completion: primary comparisons and sensitivity studies are distinct; unsupported branches remain excluded.
- [ ] **F07. Define independent research units and analysis.** Use independent calibration roots and requests; separate them from timing repetitions.
  Completion: paired intervals respect shared roots and repeated requests; sample sizes have a stated precision goal.
- [x] **F08. Define failure and exclusion rules.** Include abstention, fallback, timeout, memory failure, and finite-evaluator aborts.
  Completion: no failed request silently disappears from headline denominators or cost summaries.
  Evidence: The protocol and analyzer preserve failed, unverified, interrupted, and missing planned attempts.

**G. Establish correctness on real checkpoints — P1**

- [ ] **G01. Validate imported parameters and architecture.** Check actual pretrained tensors, attention, normalization, activations, and the output head.
  Completion: independent mapping checks distinguish architectural agreement from bit identity with external kernels.
- [ ] **G02. Validate the finite evaluator's domain.** Inspect primitive resolution, overflow limits, and numerical failures on real inputs.
  Completion: provider rejection and evaluator failure have separate counts and transaction outcomes.
- [ ] **G03. Compare every quantized stage with fresh execution.** Include codes, final artifacts, and canonical state bytes.
  Completion: any mismatch blocks performance claims until its cause is resolved.
- [ ] **G04. Check repeated and reordered deletion.** Include sequential, combined, adaptive, empty, and complete deletion requests.
  Completion: each retained set gives the same defined fresh state.
- [ ] **G05. Include difficult changed prefixes.** Exercise early changes, substantial downstream changes, small margins, and rejected certificates.
  Completion: correctness evidence extends beyond the current fixture with mostly on-grid downstream matrices.
- [ ] **G06. Audit stored state after deletion.** Inspect logical entries, caches, intermediate files, snapshots, and external source handling.
  Completion: the observed storage behavior matches the declared interface; physical erasure remains a separate claim.

**H. Run the feasibility study — P1**

- [ ] **H01. Measure coverage by stage and depth.** Include chart membership, descriptor availability, acceptance, and replay.
  Completion: identify the first failing stage and its cause for every request.
- [ ] **H02. Compare actual drift with certified bounds.** Use replayed values only as diagnostics.
  Completion: separate curvature slack, numerical error, omitted quadratic terms, and rounding margins.
- [ ] **H03. Measure chart and grouping tradeoffs.** Vary rank, radius, groups, and precision on development workloads.
  Completion: report gained coverage beside preparation, storage, deleted extraction, and verification costs.
- [ ] **H04. Measure complete request cost.** Include successful certificates and all fallback paths.
  Completion: identify whether saved retained work exceeds every additional service cost.
- [ ] **H05. Measure initial quality and memory.** Check whether the declared target remains useful at meaningful context lengths.
  Completion: the selected workload satisfies the frozen feasibility thresholds.
- [ ] **H06. Make the continuation decision.** Continue, redesign, or narrow the claim using the predefined gates.
  Completion: publish the decision and freeze the method before confirmation.

**I. Run the confirmatory study — P2**

- [ ] **I01. Execute frozen workloads across independent roots.** Preserve every request outcome and artifact hash.
  Completion: the final run matrix follows the registered selection rules.
- [ ] **I02. Measure paired complete latency.** Randomize method order and control cache and hardware conditions.
  Completion: report paired speed ratios, intervals, median latency, tail latency, and observed regressions.
- [ ] **I03. Report unconditional performance.** Keep accepted-only results as a separate diagnostic.
  Completion: headline results include the declared handling of fallback, timeout, and abort outcomes.
- [ ] **I04. Measure lifetime cost.** Include preparation, storage, repeated state updates, and cumulative request costs.
  Completion: show whether savings repay preparation; report when no break-even occurs.
- [ ] **I05. Measure held-out language quality.** Compare base weights, original quantization, retained fresh quantization, and repair.
  Completion: exact repair agrees with retained fresh; deletion effects are distinguished from quantization effects.
- [ ] **I06. Evaluate NLP tasks matched to the claim.** Use the declared evaluator or a verified deployment representation.
  Completion: task selection and metrics establish ACL relevance without substituting an unrelated numerical target.
- [ ] **I07. Run mechanism ablations.** Test response information, shape bounds, compact storage, grouping, and replay choices.
  Completion: each claimed gain has a controlled explanation; expensive quadratic variants use a declared feasible subset.
- [ ] **I08. Run robustness analyses.** Include context length, model size, deletion concentration, difficult margins, and repeated requests.
  Completion: report failure regions alongside successful settings without selecting only favorable cases.

**J. Prepare the tables and figures — P2, then P3**

- [ ] **J01. Create the main performance table.** Include exactness, complete latency, indexed comparison, fallback rate, preparation, and storage.
  Completion: every comparison shares the same state and output requirements.
- [ ] **J02. Create the quality table.** Show original quantization and retained fresh quality beside exact repair agreement.
  Completion: the table explains which changes come from the target itself.
- [ ] **J03. Create the ablation table.** Include response tiers, certificate choices, grouping, and replay policy.
  Completion: each row changes one declared factor or states the coupled factors.
- [x] **J04. Draw the sequential repair diagram.** Show changed ancestors, aggregate queries, decision checks, replay, and canonical commit.
  Completion: the diagram makes the downstream dependence and exactness argument clear.
  Evidence: output/figures/sequential_repair.svg and its PDF show the complete dependency and replay loop.
  Scope: docs/REPAIR_DIAGRAM.md records interpretation, deterministic rebuilding, and visual verification.
- [ ] **J05. Plot coverage and disjoint costs.** Include a stage heatmap and complete service breakdown.
  Completion: figures show where saved feature work survives or loses to overhead.
- [ ] **J06. Plot storage, lifetime, and latency distributions.** Include break-even behavior and unsuccessful requests.
  Completion: uncertainty and failure treatment match the protocol.

**K. Write and audit the paper — P3**

- [ ] **K01. Write the ACL manuscript.** Convert the research report into one problem, method, theorem sequence, and empirical argument.
  Completion: the main text presents the narrow contribution without relying on the report as unexplained background.
- [ ] **K02. Build the supplement.** Include full proofs, assumptions, algorithms, manifests, and complete additional results.
  Completion: every main-text reference resolves to a complete supporting item.
- [ ] **K03. Update the literature audit near submission.** Check primary sources and new work on quantization, calibration deletion, and derivative summaries.
  Completion: attribute classical geometry and prior machinery; justify only the specific contribution.
- [ ] **K04. Write measured limitations.** Cover chart restrictions, partial execution, numerical scope, metadata scans, memory, and fair indexed competition.
  Completion: no claim exceeds the supported target or workload.
- [ ] **K05. Complete research disclosures.** Address data licenses, potential sensitive text, compute, author contributions, and required AI-use statements.
  Completion: disclosures match actual project conduct and current venue requirements.
- [ ] **K06. Run an independent paper review.** Audit novelty, correctness, NLP relevance, comparisons, and reproducibility.
  Completion: resolve substantive objections or narrow the associated claims.
- [ ] **K07. Check current submission rules.** Verify dates, page limits, format, anonymity, links, and required statements.
  Completion: validate the final PDF and submission package against the selected venue's current rules.

**L. Release reproducible evidence — P3**

- [ ] **L01. Pin the environment and commands.** Record package versions, runtime requirements, source hashes, seeds, and resource requirements.
  Completion: a clean checkout can identify every dependency and execute the declared workflow.
- [ ] **L02. Release traceable raw results.** Include request manifests, timing logs, failure records, and output hashes.
  Completion: each paper value can be regenerated without private intermediate files.
- [ ] **L03. Run a clean reproduction.** Use a separate process or environment without hidden caches.
  Completion: reproduce selected complete results, including one fallback and one repeated deletion sequence.
- [ ] **L04. Package anonymous review artifacts.** Keep the public development repository separate from any required anonymous package.
  Completion: the review package follows venue rules and contains no identifying metadata where prohibited.
- [ ] **L05. Tag the release and refresh restart notes.** Preserve results, source, paper, supplement, and status in the authorized repository.
  Completion: the release identifies completed, measured, missing, and optional work without relying on chat history.

**Conditional extensions — not an unconditional implementation backlog**

| ID | Extension | Trigger and completion condition |
| --- | --- | --- |
| CEX01 | Improve constrained chart fitting | Avoidable free-variable rejection matters. Find a valid boxed solution without accepting an unexplained residual. |
| CEX02 | Add certified residual transport or independent charts | Exact chart coverage fails. Prove the new finite bounds and preserve intrinsic state. |
| CEX03 | Tighten interval or spectral bounds | Represented prefixes fail from loose bounds. Improve acceptance within a measured cost budget. |
| CEX04 | Accelerate certified arithmetic or GPU execution | Scalar execution blocks useful workloads. Prove the new schedule or declare a separate target. |
| CEX05 | Integrate bounded fallback scheduling | Claim service regression bounds. Account for packets, cancellation, resources, and complete transactions. |
| CEX06 | Support additional architectures and GPTQ branches | Claim broader compatibility. Add adapters and deletion semantics for fitted grids, damping, ordering, and dead columns. |
| CEX07 | Add sparse repair, factor updates, or better replay selection | Measurements identify their costs as material. Preserve exactness and show complete-service value. |
| CEX08 | Replace linear metadata scans | Metadata dominates. Define compatible persistent state and count authentication, update, serialization, and output costs. |
| CEX09 | Repair a learned chart | Independent charts prove inadequate. Include chart fitting and all dependent summaries in the deletion target. |
| CEX10 | Strengthen lower bounds or formal verification | The paper needs the stronger claim. State the access model and respect interval-query limitations. |
| CEX11 | Add hostile-storage authentication | The threat model includes hostile state. Hash matching alone does not satisfy this claim. |
| CEX12 | Study a deletion-native quantizer | Sequential repair fails the feasibility gate. Treat the alternative as a separate target and evaluate its quality. |

**Revision 7 partial work and unresolved preparation**

There are 28 completed required items and 50 open required items.
The 12 conditional extensions remain separate.
This revision closes D06, E03, E04, and J04 at their stated preparation scope.
D04 and D05 remain open after reviewing their complete criteria.
Software completion does not close the experiment-ready gate.

| Open items | Preparation now present | Work still required |
| --- | --- | --- |
| A03, F02–F04 | Source revisions, strict token schema, document rules, phase overlap checks | Actual weights, tokenizer hashes, prepared text, licenses, partitions, and local validation |
| A06, C06 | Config planning, rank-zero boxes, lazy wrappers, limited workers, protocol CPU admission | Resource-feasible checkpoint, frozen resource scope, and target-preserving performance route |
| C02, C04 | Domain inclusion proof and prospective thresholds | Useful numerical coverage and frozen feasible scope before tuning |
| C05 | Stable rejection events, spectral and interval routes, and exclusive cost spans | Complete per-stage numerical reasons, margins, and bound decomposition |
| D04 | Exclusive service telemetry and an isolated worker boundary through child commit, exit, and cleanup | Complete disjoint controller, worker-receipt, final parent commit, and cleanup accounting for the intended service claim |
| D05 | Independent worker RSS, allocation peaks, output sizes, final-state integer counts, and maximum bit lengths | Comprehensive transient arithmetic-size diagnostics across weights, domains, jets, factors, and temporary exact values |
| F06 | Quantization recipes, full quadratic tier, identity cache, and interval policy | Final primary settings, sensitivity matrix, and selected proof construction |
| F07 | Root sampling, counterbalanced order, complete product validation, and analysis plans | Development-based precision justification and actual frozen empirical inventory |
| F04, F07, I01 | Standalone isolated setup and individual method workers | Frozen isolated confirmation inventory and supported campaign dispatcher before confirmation |
| G04, I04 | Standalone ordered execution, verified predecessor lineage, restart, and independent complete-deletion controls | Bulk sequence campaign dispatch and real repeated-deletion correctness and lifetime evidence |
| H05, I05, I06 | Diagnostic held-out loss in the warm runner and separate quality requirements | Real-model memory, language quality, task metrics, and utility under the same target |
| L01, L05 | Source hashes, commands, updated docs, diagram, and repository checkpoint | Final environment pin, submission release, and release tag after evidence |

The original runner measures instrumented warm diagnostic costs.
The isolated executor starts separate limited processes for setup and each method.
It reloads inputs and services independently and includes child commit, exit, and cleanup in its worker timer.
Operating-system caches remain uncontrolled in both contracts.
The isolated worker timer excludes parent validation, parent equality checks, worker-control receipt commitment, and final parent commitment.
Those exclusions keep D04 open for complete disjoint transaction accounting.
Stored integer lengths do not measure transient arithmetic growth, so D05 also remains open.

Protocol-scoped admission reserves CPU allowances before workers start.
Unknown interrupted attempts retain their allowances, and observed overruns remain charged.
Changing output directories cannot reset that frozen protocol's ledger.
This is not a strict physical CPU ceiling or a cross-protocol project budget.
Cross-protocol accounting and hostile descendant containment require additional controls if the paper claims those guarantees.
Controller CPU remains outside the worker ledger.

The quadratic control uses the implemented unwhitened finite-error enclosure.
The stronger whitened acceptance theorem remains an unimplemented potential extension.
The interval portfolio preserves spectral acceptance but does not guarantee lower total work.
The true-model cache's equally indexed comparator receives the same valid old model and Grams.
Neither comparison withholds reusable information to create an artificial deletion advantage.

Standalone sequence execution does not close bulk sequence campaign dispatch.
Standalone isolated development execution does not close its frozen confirmation inventory.
Confirmation remains blocked until that dispatcher and inventory are supported.
Real-model feasibility, statistical precision, quality, and reliable complete-service savings remain unmeasured.
The current protocol blocks research execution while paused.
No resource limit may be raised silently to bypass an unfavorable plan.

**Decision gates**

| Gate | Required evidence | Action if the gate fails |
| --- | --- | --- |
| G0: Experiment ready | Frozen contracts, protocol, runner, fair baselines, costs, and failure handling | Complete P0 work; keep experiments paused until authorized |
| G1: Exactness | Correct imports, valid finite execution, fresh-identical model and canonical state | Resolve mismatches before interpreting speed |
| G2: Coverage | Useful accepted requests with genuine changed ancestors under an affordable proof construction | Improve certificates or narrow the target |
| G3: Full service value | Savings survive complete costs and the equally indexed comparison | Change the performance claim or redesign the method |
| G4: NLP value | Meaningful quality and task results on held-out real text | Revise the supported application or reconsider venue fit |
| G5: Submission ready | Frozen evidence, coherent paper, clean reproduction, and current venue checks | Resolve missing evidence before submission |

The immediate order is feasible checkpoint execution, real input manifests, remaining measurement controls, and supported confirmation inventories.
Original-only selector definitions and campaign membership checks are now implemented.
The first authorized study should resolve G1 and G2 before expanding the benchmark matrix.
Do not promise a universal speedup or treat another conditional theorem as measured reliability.
