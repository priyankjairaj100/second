# Current execution: revision 12 completed diagnostics

Updated 7 October 2026. The user authorized empirical execution here; the earlier local-only instruction is historical.
Read docs/EMPIRICAL_PILOT_V12.md and pilots/v12/summary.json first.

Twelve bounded attempts are preserved: eleven completed, one failed and subsequently fixed.
Complete column-grid original/retained models and a prospective row-grid retained model were constructed.
Each contains 24 quantized projection stages and 42,467,328 certified code decisions.
The old-target deletion changed 5.637 percent of codes across every stage.

Heldout diagnostics contain only 30 predictions from two validation articles.
Column-grid perplexity was 4.830x base before deletion and 8.102x afterward.
Fixed output-row scaling improved the retained ratio to 1.315x.
An evaluator control reproduced every old-model NLL exactly.
This is a new quantizer target and an exploratory improvement, not a confirmed paper result.
The two evaluation IDs are excluded from future confirmation.

The core suite passed 590 tests; nine additional tests passed for later modules.
The inherited worker budget has 4283 charged CPU seconds and 6517 remaining.
Do not reset it through a new directory, source version, or target variant.

The complete empirical program remains blocked.
The compact path lacks canonical repair state, certified feature transport, and four-method integration.
The specified fully represented dense state needs at least 523.125 MiB, above the 512 MiB single-file cap.
The improved quality diagnostic also remains above the 1.20 screen.
No reliable full-model repair speedup is established.

Read docs/V12_REPAIR_INTEGRATION_AUDIT.md and docs/NEXT_ALGORITHMIC_STEPS_V12.md for next work.
Read docs/COMPACT_EXECUTION_V12.md for bounded commands and explicit target choices.
All attempt sources and receipts are preserved. Large code arrays remain reproducible local artifacts, bound by published hashes.

---

The following sections preserve historical checkpoints.

# Current instruction: local empirical execution

Updated 5 October 2026. Revision 11 handoff.
The user will run future research experiments on their local machine.
This chat prepares code and reviews returned evidence. Do not launch new research experiments here.
Local coding agents should execute docs/LOCAL_EMPIRICAL_PROGRAM.md under its staged gates.
Software checks remain allowed here.
Read LOCAL_LLM_START.md, docs/LOCAL_EMPIRICAL_PROGRAM.md, and handoff/program.json first.
Preserve all prior evidence. Generate new runtime bindings, budgets, paths, and inventories locally.
The original feasibility allowance has 614 charged CPU seconds. Never silently reset it.
Full-model repair, quality, and reliable speedup remain unmeasured.
The archived 4.471x/4.509x ratios describe first-block diagnostic workers only.
The previous research checkpoint is 4fb4f8a6137fa37e3130af94e7d31ecaa188bdcb.

---

The following sections preserve historical checkpoints.

## Revision 10 result

The user resumed empirical pilots on 5 October 2026.
The current reference representation failed full-model resource admission for DistilGPT2 and GPT-2.
Real first-block diagnostics used two WikiText articles and two C4 records.
A NumPy prototype preserves the scalar multiply-then-add schedule.
It produced identical feature bytes with 4.471x and 4.509x diagnostic worker ratios.
No quantization or repair occurred in these diagnostics.
LAMBADA input preparation and whole-word scoring checks are now present.
The full-model task matrix remains blocked.
See EMPIRICAL_PILOT_V10.md, pilots/v10/program.json, and RESUME.md.

> Current instruction, 5 October 2026: The user resumed local empirical pilots.
> Use protocol v6. Keep prior results and failures. Confirmation remains blocked.
> The earlier experiment pause below is historical.

# Project context and evidence provenance

## User objective and constraints

The user selected problem 2 from an ACL 2027 unlearning research agenda: deleting calibration documents from a quantized LM while holding the full-precision weights fixed. They requested deep theory, algorithms, a strong empirical program, execution here, algorithmic improvement after the first run, and a proof that a reliable full-model repair speedup remains. Their latest instruction pauses experiments until the remaining theoretical and algorithmic points have been attacked. Synthetic empirical datasets are deferred. The work so far used local CPU; no large-LM/GPU confirmation run is established. Do not borrow hardware or credentials from unrelated projects.

Research distinction: the target is Q(W,C\\F), the complete quantization rerun on retained calibration documents. In sequential GPTQ-style pipelines, earlier quantized blocks change the features used to calibrate later blocks. Ordinary subtract-a-Gram repair is therefore invalid downstream unless feature equality or a valid transport bound is proved.

## State of files at this checkpoint

On 4 October 2026 automated workspace maintenance left the current working directory with no previous project files. The following inventory is from the conversation, not recovered bytes. Some prior Library writes also failed authentication. The new repository starts with a context reconstruction and then receives newly authored work. Do not fabricate missing source, logs, hashes, or experiment reproductions.

Previously reported deliverables (missing locally):

- `acl2027_unlearning_research_agenda.pdf`: 15-page initial agenda with 36 primary references.
- `calibration_unlearning_theory.pdf`: 45-page theory report.
- `empirical_protocol.pdf`: 17-page empirical protocol.
- `algorithm_v2_report.pdf`: 7-page algorithm revision report.
- `calibration_unlearning_algorithm_v2.zip`: 378 files, approximately 5 MB.
- `full_model_speedup_proof.pdf`: 8-page proof and limits note.
- `full_model_speedup_proof_bundle.zip`: 13 entries, 451138 bytes; included proof source, independent notes, extracted evidence, and selected original logs/source. Last persistent upload failed. The user may have downloaded it.

## Prior implementation, reported in conversation

The old project was named `calibration_lab`, with a Python environment using CPU PyTorch, NumPy/SciPy and python-flint/Arb. Thread settings for comparable measurements were OPENBLAS_NUM_THREADS=1, OMP_NUM_THREADS=1, MKL_NUM_THREADS=1 and TOKENIZERS_PARALLELISM=false.

- `frontier_v2.py`, `repair_v2.py`: earliest unresolved code per row, and a stronger blocked fresh baseline. Reported 36 targets x 5 repetitions, 1020 kernel timings, zero artifact mismatches. Width 128 approximately 1.307x kernel gain; width 512 approximately 0.783x. These are kernel results, not full-model savings.
- `verified_fast.py`: rigorous relative-factor certificate, approximately O(d^3+p d^2) after Gram acquisition. Reported 108 selected QKV rows matched an independent rigorous slow oracle. A 128-by-512 layer's 65536 decisions took about 7.4 seconds; an older partial 16-row route timed out around 182 seconds. Selected-row evidence is not all-stage certification.
- `verified_cache.py`: canonical exact-Gram unchanged-prefix caching.
- `audit_verified_cache_full.py`: checks every row before output writes; deliberately corrupted candidate abstained and wrote no output. Six services reported medians approximately .4795 seconds (width 128) and 5.6493 seconds (512). Warm deleted-feature state is not raw-document cold service. No full-model rigorous V service established.
- `model_runner_v2.py`: native block-local shared-input repair. Ten initial and 18 integrated targets reportedly matched full model artifact/features of finite program E.

Pilot data/model: Pythia-14M; real C4 text, first 1024-shard-prefix source; 16 development records, three roots of 64 calibration records, and 16 evaluation records, each 128 tokens. This description is historical context, not an available manifest.

## Prior measured full-model findings (NOT re-executed here)

The paired integration audit used one reused engineering root, a four-record deletion, two correlated bit settings and three timing repetitions. All 18 model/feature outputs reportedly matched target E.

| Method | 4-bit fresh/repair geometric ratio | 3-bit ratio |
| --- | ---: | ---: |
| Target-trace repair | 1.028099 | 0.967292 |
| Frontier hybrid | 0.924281 | 0.957311 |

Every method/bit pair had both wins and losses. There is no reliable population speedup or confidence interval established by these measurements.

Gram acquisition was nested inside the quantization timer: subtract nested time, never add overlapping fields. Factorization/rounding/dispatch excluding Gram represented 10.47-12.70% of recorded wall time. Making that entire interval free gives only a 1.1169-1.1455x fixed-other-cost ceiling. A hypothetical 1.31x gain over ALL of it yields only 1.0254-1.0310x full-model gain; the actual faster kernel covered a smaller subset.

Both repair variants still computed all 24 retained Grams and 360 retained record-block passes (60 retained records x 6 blocks). Two stages had unchanged INPUT dependencies (first QKV and first MLP input), but all 24 installed weight tensors changed. Those two Grams cost only about 10-11 ms. Six wide MLP-down Grams cost approximately .545-.643 seconds. A deletion of 4/64 records removes 512/8192 calibration tokens with fixed original normalization M0.

First-stage changed codes, out of 49152:

| Root | Bits | Delete 1 | Delete 4 | Delete 16 |
| --- | ---: | ---: | ---: | ---: |
| 00 | 3 | 734 | 1233 | 1981 |
| 00 | 4 | 620 | 1033 | 1998 |
| 01 | 3 | 719 | 1294 | 2186 |
| 01 | 4 | 558 | 1397 | 2154 |
| 02 | 3 | 652 | 1236 | 2466 |
| 02 | 4 | 663 | 1324 | 2444 |

A sound unchanged-artifact certificate for those observed E targets must reject. This is not automatically a rigorous claim about a distinct exact-statistic oracle V.

Historical source hashes (identifiers copied from conversation; files unavailable for rechecking now):

- `runs/repair_v2_frontier/evaluation.jsonl`: SHA256 `543d3c88d0ea07b8c245f5f1a2ff2b0dc2267a49f4d176bb99bff8cfa5fcbe54`.
- `runs/pipeline_kernels_v2/paired_results.json`: SHA256 `2a5a1c6dbe5d69b64d8bd682daad64fe79fface77b5364e6846c3e783d8d19f1`.
- `runs/pipeline_kernels_v2/execution_contract.json`: SHA256 `6e4a99cd1d0808dc168b4a7abead90ec7403d31b7d7364334dc0b672b08f0a3e`.

## Prior theorem stack

### Declared target

A deterministic quantization DAG with L stages. Record j has features X_lj, generated by quantized ancestors. H_l=lambda_l I+(1/M0) sum_j X_lj X_lj^T. Base weights, grids, coordinate order, tie policy, normalization and ridge fixed. Features deterministic and record-local. Any corpus-fitted preprocessing must be covered separately. Oracle V may use pinned floating-point feature evaluation followed by exact sufficient statistics and exact-grid decisions; this is different from pinned floating Gram/Cholesky program E. Every original stage and output row must be certified before using global proof shortcuts.

### PSD stability

Factor H=L^T D^{-1} L, L=I-B unit lower triangular, D=diag(g). For forced old prefix q, v_ai=w_ai-B_i,<i(w-q)_a,<i; E_ai=sum_h<i (v_ah-q_ah)^2/g_h; K_ai=sqrt(g_i E_ai). Let m_ai be the distance inside the emitted rounding cell to its boundary. If H'=H-Delta, Delta PSD, and rho bounds ||H^{-1/2}Delta H^{-1/2}||<1, then |v'_ai-v_ai| <= rho/(2 sqrt(1-rho)) K_ai. Whitening and an off-diagonal block contraction prove this. It is stronger than a generic signed-perturbation estimate.

Let tau_l=min_{K>0} m/K, r_l=2 tau_l/(sqrt(1+tau_l^2)+tau_l). If rho<r_l then every code stays unchanged. Empty minimum means infinity and r=1; K=0 gives zero displacement; a nonzero-energy tie yields zero budget; failed certificate means abstention, not proof of changed codes.

### Whole-model scalar gate

Precompute ell_lj >= tr(H_l^{-1} X_lj X_lj^T)/M0; a_j >= max_l ell_lj/r_l. Sum_{j in F} a_j <1 proves all codes unchanged by topological induction: certified unchanged ancestors imply same retained features, then PSD deletion stability certifies this stage. This costs O(k) score lookup/addition with O(N) stored scores, plus all actual authentication, state, disposal and output costs.

Integer tickets: B0=2^b, s_j=min(B0,ceil(B0 a_j)) with certified outward ceiling. Saturating integer addition accepts iff sum_F s_j<B0. Equality rejects; clipping implies rejection. Authentication must bind immutable artifacts, IDs, grids, evaluator, DAG and numeric contract. Cached hashes alone are not authentication of mutable untrusted bytes.

### Finite stored factors

Treat finite Bhat,g as an exact surrogate Hhat=(I-Bhat)^T D^{-1}(I-Bhat). T=(I-Bhat)^{-1}D^{1/2}. Validate ||T^T H_C T-I||<=eps0 and per-record norms hatell>=||T^T X||_F^2/M0. Surrogate conditional-input enclosure MUST lie inside candidate's actual emitted code cell. Let lower margin/upper K yield tauhat. A positive rational budget b_l<=tauhat/(1+tauhat)-eps0 and a_j>=max hatell/b certify retained decisions via e/(1-e) K, e=eps0+sum_F hatell. No online Arb matrices on accepted scalar gate. The scalar compiler was derived, not implemented/benchmarked as a full-model service.

### Deterministic coverage and costs

With equal t tokens, M0=Nt, ||X_lj||_F^2<=A_l, ridge floors and tau_l>=tau0>0, explicitly choose ell=A/(Nt lambda), a=max A/(Nt lambda r_l). Every k-deletion passes if (k/N) max_l A_l/(t lambda_l)<r0. Integer upward rounding adds sufficient slack k/B0. Arbitrarily inflated valid scores do not inherit this coverage guarantee.

Fixed dimensions, uniformly controlled energy/ridge/margins, k=o(N), ticket precision k/B0=o(1), and all auth/state/output work o(N) imply sublinear successful artifact-only work versus a declared fresh retained scan Omega(N-k). This is a unit-cost/query theorem, not measured latency or a lower bound against all indexed algorithms. Charge bit operations and O(k log N) membership if used.

### Repeated state and reliability

Old inverse-leverage tables are not automatically valid after earlier deletions. A conservative canonical route stores intrinsic per-record stage norms, gates using current thresholds and ridge, replays only deleted records on successful invariance, subtracts exact Grams, refactors, reconstructs traces, refreshes thresholds. Cost includes k forward work, kt sum d^2, sum(d^3+p d^2), state and certification. No retained feature refresh on that unchanged-model route. Exact canonical state is not canonicality for a different float constructor.

For uniform size-k requests and normalized integer scores z_j in [0,1], E sum_F z=k mean(z), so Markov gives failure probability <=min(1,k mean(z)). This is not an adversarial request guarantee. A speculative attempt capped at alpha B followed by fresh fallback costs <=(1+alpha)B for every request, if B or a certified lower work budget is known. Successful service cost<=beta B and failure probability<=delta yield E[C/B]<=beta(1-delta)+(1+alpha)delta. Include timeouts; to use gate-only failure, accepted service must fit cap, e.g. beta<=alpha. This is not a ratio of mean wall times or p95 theorem.

### Changed suffix and limits

Certify an ancestor-closed prefix, load COMPLETE authenticated retained boundary checkpoints, and run identical fresh suffix. Exact output even with changed suffix codes. With h/L>=theta saved blocks, extra work<=eta core cost, eta<theta, shared output<=gamma core, fresh/repair >=(1+gamma)/(1+gamma-theta+eta)>1. Constants need justification. Canonical prefix state refresh, multiple residual cut tensors, loading and writes must be counted. Lifetime saving needs total request savings >extra preprocessing cost.

Materializing a P-word model costs Omega(P). Dense code changes do not prove retained replay is necessary: linear feature maps admit moment closure. Any nonlinear replay lower bound must declare its feature-query/cache model. A universal practical speedup has not been proved.

## Literature and novelty posture

Initial agenda correctly distinguishes this problem from making training-data unlearning survive quantization. GPTQ, asymmetric reconstruction, block reconstruction, Babai geometry, low-rank inverse updates and generic dynamic computation are prior techniques, not novelty claims. The contribution must be exact calibration deletion, valid propagated certificates, state/storage/cost tradeoffs, and a meaningful empirical phenomenon. Primary sources must be checked before writing priority claims. The original agenda searched through 3 October 2026; that did not establish absence of related work.

## Theory revision at its start (historical checkpoint)

Four independent analysis tracks were commissioned: changed-prefix exact repair/query limits; deletion-native teacher/anchor design; coverage and repeated state; adversarial review/cost accounting. Their notes will be saved under `theory_revision/`. Root is deriving candidate-prefix transport certification: use an anchored retained Gram as surrogate, bound actual new-prefix activation drift, certify candidate rounding against every Gram in the enclosure, and refine with selected retained-record replay if needed. Unlike the prior gate, this can allow changed codes at the first stage. It remains a derivation until the consolidated report says otherwise.

At the prior checkpoint this derivation/review was completed in a 17-page report (now superseded by v3 below). See `docs/STATUS.md`, the consolidated report, `docs/THEOREM_LEDGER.md`, `docs/ALGORITHM_SPEC.md` and `docs/NUMERICAL_CONTRACT.md` for the current result. The report now proves the changed-prefix transport route, sharper shape sensitivity, canonical independent-reference state, adaptive fallback and explicit cost limits. The local rational core was authored and manually/static checked; a full transformer service and practical speedup remain unestablished.

Experiments remain paused. Continue this project from the current status rather than starting a new survey or assuming the paper is finished.


## Revision 3 completed work (4 October 2026)

The user next asked to complete remaining items for maximum novelty. We developed intrinsic response-moment indices, rigorous second-order remainder accounting, full-model conditional zero-replay regimes, a polynomial-coefficient information bound, and a lower-storage shifted linear-Gram tier. The latter stores O(r d²+r²) values per group and encloses an omitted PSD quadratic term instead of reconstructing it.

New executable modules include full stage fresh/repair/canonical state, a deterministic complete scalar decoder, sparse repair, response/remainder indices and adapters, low-storage response arithmetic, and a cooperative scheduler utility. Correctness/adversarial tests were run; no research benchmarks or synthetic empirical datasets were run. General certified finite transformer response jets and pretrained adapters remain unimplemented. The transparent adapter stores per-record response payloads and scans their descriptors, distinct from theoretical compact group-index costs.

The novelty audit found Gunn 2026 derivative-sketch deletion, classical Kantorovich/Wielandt geometry for the shape constant, and calibration-scale refitting in a September 2026 audit. Claims were narrowed accordingly. An equally indexed fresh quantizer can use the same summaries: strict deletion-exclusive speedup does not follow. See current STATUS, VALIDATION, NOVELTY_AUDIT and the report; those supersede earlier implementation-status paragraphs above.

## Revision 4 implementation blockers (4 October 2026)

The user requested: "Proceed on the remaining implementation blockers."
Research experiments remained paused.
Software correctness fixtures and independent code review were permitted.

Four modules now close the scoped reference implementation gaps.
`aggregate_response_service.py` stores group response sums and scalar remainder moments.
It retains per-record identity and contribution digests, but no individual matrix descriptors.
Deleted payloads regenerate contributions for checked exact subtraction.
Proposal construction reads aggregate statistics only.
Complete state still includes O(NL) metadata and associated scans.

`certified_intervals.py` supplies rigorous rational enclosures and certified binary64 nonlinear rounding.
It caches only data-independent constants.
`certified_transformer.py` uses these primitives in a distinct finite decoder.
Automatic interval differentiation encloses all mixed Hessians.
Numerical propagation bounds finite execution against the ideal smooth feature map.
Stable softmax uses separate ideal-derivative and finite-schedule proofs.
The provider accepts only changes inside a fixed corpus-independent affine chart.
It returns UNKNOWN for unsupported proof conditions.
The service then replays retained records.
Failure inside the finite evaluator aborts the transaction.

The new numerical target is V_cert.
It is distinct from both legacy library-math V and historical floating quantizer E.
This distinction is recorded in source and runtime manifests.

`checkpoint_adapter.py` loads local GPT-2 safetensors, including shards and default gelu_new.
It maps four floating storage formats and checks architecture assumptions.
It does not download models or reproduce native Hugging Face kernels.
No pretrained checkpoint was evaluated during this revision.

See VALIDATION for the final software result and review record.
No real-data quality, chart-coverage, latency, or memory result follows from these software checks.
Large charts and interval bounds may be impractical.
The eager scalar decoder can require substantial memory.
Equally indexed fresh comparison, lifetime costs, and complete service timing remain required when experiments resume.

## Research program register (4 October 2026)

The user requested a comprehensive list of remaining paper tasks.
The authoritative register is docs/RESEARCH_TODO.md.
It includes priorities, completion criteria, dependencies, conditional extensions, and submission gates.
No experiments resumed during this planning update.

The main gate is useful chart coverage for real changed prefixes.
The exact chart can reject general quantization changes, even after small deletions.
The current acceptance fixture does not establish practical coverage.
The experiment runner, equally indexed fresh baseline, and full current empirical protocol remain outstanding.
The old empirical protocol remains unavailable.

The audit found one concrete wording inconsistency in report Section 16.
Its fallback statement must include successful finite evaluation, as the current numerical contract already requires.
The register tracks this correction without reopening the reviewed induction proof.

## Revision 5 preparation (4 October 2026)

The user instructed us to proceed with the remaining research program.
This revision implements preparation while research experiments remain paused.
Current STATUS and RESUME supersede older unfinished-infrastructure statements above.

V_cert is selected for the implemented path.
A manifest binds weight-only grids, ridge, original normalization, fixed order, and lower ties.
Deterministic chart recipes use base weights and fixed configuration only.
A config-only preflight counts dense storage before eager tensor loading.
Byte estimates are planning heuristics, not measured memory or proved bounds.

Canonical state now has a strict bounded reload path.
A fresh-process software test loads saved bytes and reproduces the next deletion.
The service exposes retained index preparation and indexed fresh construction.
Both repair and indexed fresh call the same planner.
That planner ignores the old quantized model.
Therefore current solving has no deletion-specific algorithmic advantage.
Index maintenance savings remain a separate potential benefit.

The local runner connects hash-bound checkpoint inputs, target/chart construction, preparation, deletion, three comparisons, and held-out loss.
It requires complete model and canonical-state equality before recording successful comparisons.
Atomic storage preserves incomplete attempts and seals completed results.
The research archive retains original states outside the live-state deletion guarantee.
Warm instrumented timings have explicit boundaries and do not establish production latency.

Analysis retains failed and missing planned attempts.
It reduces timing repeats within requests and resamples independent calibration roots.
The new prospective protocol does not recover the missing earlier protocol.
Its thresholds and sample sizes are planning decisions, not measured feasibility or power evidence.

Source metadata candidates include DistilGPT2/GPT-2, WikiText-2 raw, C4 English, and English LAMBADA.
No model or corpus was downloaded.
The catalog leaves unavailable pins unresolved.
Ordinary candidate dimensions exceed the default reference resource plan.
The adapter now accepts verified historical DistilGPT2 label metadata without changing LM computation.
Actual public checkpoint compatibility remains untested.

Independent review found and corrected parsing, source binding, result sealing, locking, restart, and failure-classification defects.
The current validation file records the final suite and hashes.
The report consistently conditions completion on successful finite evaluation and sufficient resources.
Publication T1–T7 and a claim-to-evidence map organize the existing theorem stack.

The experiment-ready gate remains open.
Feasible execution, complete source/token manifests, stress-selector equations, worker limits, inventory scheduling, and required diagnostics remain pending.
Practical coverage, complete speed, lifetime value, and NLP quality remain unmeasured.
No universal reliable speedup or final publication readiness is claimed.


## Revision 6 completed preparation (4 October 2026)

Latest instruction: "What are the remaining to-do items? Please proceed on them now."
The previous verified commit is b662d2c7ed7f4799029ff1093e93acf0d400699c.
This revision preserves every earlier evidence distinction.

The fixed-box provider covers installed frozen-grid ancestor parameters without affine derivatives.
Its hybrid anchor uses interval midpoints for varying domains and exact finite features for fixed-base domains.
Midpoints minimize the rectangular interval feature envelope.
They remove a separate finite anchor evaluation for varying domains.
They do not guarantee better Gram bounds, acceptance, or speed.
The provider retains exact intrinsic deletion state and the V_cert target.
Lazy parameter wrappers reduce temporary construction without changing operation order.
The new report sections contain B1–B8, storage counts, and explicit limits.

Execution preparation adds worker limits, exclusive telemetry, source-bound inventories, and complete confirmation products.
Original-only concentration and difficulty scores define prospective stress requests.
The score producer verifies original codes and charges its complete construction.
Mechanism controls include certified, fixed-reference, full-replay, and base-reference identity-only modes.
The last control is not an original-model invariant-feature cache.
The complete quadratic control remains open.

All 261 correctness tests pass.
The first integrated suite exposed an outdated timeout stub lacking the new telemetry keyword.
The stub now accepts optional keywords; its timeout assertion remains unchanged.
The initial failure and final pass logs are preserved separately.
No research observation follows from software test runtimes.

The report has 31 pages.
The register closes C03, E05, and F05 at their stated preparation scope.
It now contains 24 completed and 54 open required items, plus 12 conditional extensions.
The preparation gate remains open.

Process isolation applies to each comparison, not each method.
Method arms remain warm and share process history.
Operating-system caches remain uncontrolled.
Cumulative phase CPU caps and complete committed timing remain open.
Real inputs, useful model feasibility, token artifacts, actual partitions, and the final inventory remain absent.
Sequence/full-deletion laws exist, but their campaign execution remains blocked.

No experiment, model download, dataset download, or cloud job ran.
No reliable speedup or practical coverage claim is established.
The user still authorizes saving all substantive files and restart context to the repository.


## Revision 7 completed preparation (4 October 2026)

Latest instruction: “Proceed on the remaining tasks. Please ensure that we have maximum revenue.”
We interpret “maximum revenue” as research value within the ongoing paper program.
No monetization target or financial guarantee follows.
The previous verified checkpoint is 3c6905e77bca86e4d3e54be20a82f3acdcfd294d.
Current STATUS and RESUME supersede older unfinished-preparation statements without changing their historical provenance.

Research experiments remain paused.
This revision adds mathematics, implementation, software correctness fixtures, and execution controls.
It does not recover historical raw results or establish real-model measurements.

The new certificate portfolio runs the existing spectral certificate first.
After rejection, it uses signed covariance entry intervals and the true target ridge.
Exact interval reverse elimination and lower-tie cell checks certify the fixed candidate.
Standalone common-binding intersection supports conditional acceptance monotonicity.
A rational fixture establishes strict certificate improvement.
Additional arithmetic can still increase runtime or exhaust resources.
No acceptance result establishes full-service speed or finite-budget completion dominance.
A complete stored multi-domain bank remains future work.

The quadratic control stores the full Gram polynomial of the same affine feature response.
Its canonical schema differs from the compact tier.
Both retain the same exact quantization target and remainder assumptions.
Setup, extraction, subtraction, storage, and output costs remain explicit.
Different proposals can change margins and acceptance in either direction.

The identity-cache family stores true sequential Grams under the current quantized model.
It reuses a Gram only when all relevant old and new transitive ancestors agree.
It then subtracts exact deleted-record contributions.
Changed ancestors force retained replay.
Every successful request refreshes canonical retained-only cache state.
Repeated, reordered, empty, and complete deletion match direct retained construction in software tests.
Its bounded runner trust registry remains outside returned live state.

The response-family planner still ignores old model codes.
The identity-cache planner uses the old quantized model as its feature-cache reference.
Indexed fresh receives the same valid information and solver within each family.
Neither solver has a deletion-exclusive advantage over that comparator.
Extra split-interface preparation overhead cannot support such a claim.
Cross-family comparisons check target model equality because their canonical state interfaces differ.

Local sequence execution now consumes preceding committed states.
It constructs the original state once and supports complete deletion with fixed original normalization.
It verifies every method against direct fresh and preserves lineage across restart.
Bulk sequence campaign admission and a frozen ordered inventory remain open.

The isolated executor separates setup and every method into limited processes.
Repair and indexed fresh reload the same original cache.
Direct fresh constructs its retained result without loading that cache.
Method clocks include startup, inputs, service work, artifact synchronization, child receipt, exit, and cleanup.
They exclude parent validation, equality verification, parent receipt, and post-cleanup accounting commitments.
The isolated executor does not yet compute quality metrics.
Its confirmation gate remains closed until supported frozen isolated inventories exist.
Operating-system caches remain uncontrolled.

Durable phase CPU admission reserves worker allowances before process creation.
Observed wait4 usage settles known outcomes; uncertain attempts keep their full reservation.
Observed overruns remain charged and prevent later admission.
The ledger applies to trusted workers sharing one frozen protocol identity.
It does not bound all physical CPU, controller CPU, hostile descendants, or cross-protocol project totals.
A separate feasibility phase dispatcher remains open.

The final validation records 340 correctness tests.
The report contains 35 pages.
The register contains 28 completed and 50 open required items, plus 12 conditional extensions.
Protocol version 3 preserves explicit unresolved fields and the research pause.
The experiment-ready gate G0 remains open.

Real checkpoint, tokenizer, source, document, and token artifacts remain absent.
Ordinary model feasibility remains unresolved under the scalar reference target and resource limits.
Remaining preparation includes complete parent timing, transient arithmetic diagnostics, campaign integration, actual partitions, inventories, and precision justification.
Empirical exactness, useful acceptance, complete service cost, lifetime savings, and NLP quality remain unmeasured.
The manuscript, current literature audit, independent review, and reproducibility release remain future program tasks.

No research experiment, model download, dataset download, cloud job, or unrelated hardware ran.
No reliable full-model speedup or publication-readiness claim is established.
The user continues to authorize repository checkpoints and complete restart context.


## Revision 8 completed preparation (4 October 2026)

The previous verified checkpoint is e8d6f593a0311ad05fa3a7e87088d29aaa1646d3.
The user continues to request progress on the remaining paper program.
The earlier “maximum revenue” phrase is interpreted as research value, without monetization claims or financial guarantees.
Current STATUS and RESUME supersede older unfinished-preparation statements while preserving their historical provenance.

Research experiments remain paused.
Revision 8 advances comparisons, software, execution controls, diagnostics, and prospective feasibility decisions.
It does not acquire models or data, recover old raw results, or establish empirical observations.

The model-only fresh control corrects an important comparison mismatch.
Existing direct_fresh constructs both the retained model and canonical deletion state.
Ordinary requantization only needs the model.
The new control constructs every stage under its newly quantized ancestors without a response chart or persistent deletion index.
It preserves the V_cert target, grids, ridge, order, ties, and fixed original normalization.
Common target digests and complete stage codes permit cross-family model comparison.
Full-state direct construction remains the separate canonical-state oracle.

A gain against unnecessary index reconstruction cannot establish faster ordinary requantization.
The equally indexed comparator still receives the same valid summaries or original-model cache as repair.
The response solver ignores old codes; the identity-cache solver uses its previous quantized model.
Neither family establishes a deletion-exclusive solver advantage.

Frozen isolated campaigns now bind plans, sources, workloads, configurations, roots, requests, repetitions, and method order.
Confirmation verifies real inventory membership and the complete declared Cartesian product.
Each setup and method uses a separate limited process.
An optional quality worker evaluates finite next-token NLL for base, original, retained, and repaired models.
Its time and CPU remain separate from method clocks and enter the same protocol ledger.
These are implementation capabilities, not measured language quality.

Frozen sequence campaigns bind complete ordered requests and predecessor lineage.
Each sequence prepares original state once inside a limited worker.
Later requests consume preceding committed repair states.
Failures, unstarted work, interrupted attempts, and resume evidence remain visible.
Methods within a sequence still share warm process state.
A resumed attempt's elapsed time cannot represent the entire sequence lifetime.

Feasibility is now a supported phase with an explicit protocol CPU allowance.
Its actual source draws must remain on the development side, separate from confirmation and evaluation data.
No real source pools or empirical inventory exist yet.
The protocol pause remains authoritative.

An external observer now measures declared child transactions through source validation, final child commitments, cleanup, and output verification.
Its disjoint component intervals sum to the enclosing wall clock.
Its final observer receipt and observer lock release remain excluded.
Model-only, canonical-state, comparison, and sequence output contracts remain distinct.
A complete comparison clock cannot be relabeled as a single method clock.
Matched primary campaign and lifetime-clock integration remains open.
A compatible model-only confirmation inventory also remains open.

Research model-only and direct isolated-child commands require live exact-command CPU admission.
Supported campaign children verify their source, protocol, inventory, and target bindings.
Unknown attempts retain reserved allowances, while observed overruns remain charged.
These controls cover trusted local workers sharing one frozen protocol identity.
They do not impose absolute physical CPU, hostile-process-tree, or cross-protocol project limits.
External observer and controller CPU remain outside child allowances.
Operating-system caches remain uncontrolled.

The arithmetic audit observes both standard Fraction allocation paths in the current process and thread.
It records endpoint bit lengths, a separate initial visible-value snapshot, bounded attribution, available traced memory, RSS, and artifact sizes.
It preserves numerical model and state bytes in software tests.
It rejects cached-run reuse and unsupported child-controller coverage.
Interference or changed source evidence produces incomplete diagnostics.
Embedded profiling flags prevent the standard analyzer from using these timings as clean ratios, even without sidecars.
Hidden integer intermediates, exact object lifetimes, and physical live-rational memory remain outside its scope.

The bounded certificate funnel records descriptors, domain queries, bounds, decisions, replay, and operation completion.
It preserves disposition counts for recorded stages and events, with explicit omission, saturation, and unavailable components.
Large exact values receive bounded magnitude summaries.
Numerical targets and canonical state remain unchanged by the diagnostic interface.
Provider-internal decomposition remains incomplete.

The written feasibility policy fixes zero mismatches, resource limits, changed-ancestor coverage, finite quality, preparation, and lifetime decisions.
It uses two independent real calibration roots and a three-request lifetime horizon.
Repair must beat model-only fresh lifetime cost on every feasibility root under the same declared transaction boundary.
Missing evidence leaves the decision open.
These are prospective engineering thresholds, not power guarantees or attained results.
C04 closes at this policy scope only.
C05, D04, and D05 remain partial under their complete criteria.

The final suite contains 417 correctness tests.
The register contains 29 completed and 49 open required items, plus 12 conditional extensions.
Protocol version 4 records the new capabilities and unresolved fields.
G0 remains open.
The consolidated PDF remains the unchanged 35-page revision 7 report.
The current revision note is docs/REVISION_8.md.

Real checkpoints, tokenizer artifacts, corpus records, partitions, scores, inventories, and precision justification remain unresolved.
Practical model feasibility, useful certificate coverage, complete cost, lifetime savings, and NLP quality remain unmeasured.
The manuscript, current literature audit, independent review, and reproducibility release remain future program tasks.
No research experiment, model download, dataset download, cloud job, or unrelated hardware ran.
No empirical speed or quality claim is established.
The user continues to authorize repository checkpoints and complete restart context.


## Revision 9 completed preparation (4 October 2026)

The previous verified checkpoint is 552340bd0c1014d2b68c96439740288340938c6e.
The latest user steering asks us not to stop prematurely and to continue known next tasks.
Proceed autonomously within authorized preparation; do not reinterpret that steering as lifting the research-experiment pause.
The earlier “maximum revenue” phrase remains research value within this program, without monetary guarantees.
Current STATUS and RESUME supersede older unfinished-preparation statements without changing their historical provenance.

Research remains paused.
Revision 9 completes another implementation, algorithmic-accounting, and independent-review pass.
No real model/data download, research benchmark, synthetic empirical study, cloud job, or unrelated hardware ran.
Software correctness fixtures are not empirical datasets, calibration roots, or speed observations.

The complete sequential V_cert target remains unchanged.
Necessary finite-evaluator failure still aborts without an approximate model, and proof rejection still permits exact retained replay.
The response solver ignores old codes; the identity-cache solver uses its previous quantized model and transitive-ancestor identity.
Equally indexed fresh receives identical valid information and solver policy within each family.
No deletion-exclusive solver advantage is established.

Frozen measured single-request campaigns now contain model-only fresh, repair, equally indexed fresh, and direct full-state fresh.
The ordinary baseline constructs no unnecessary response chart or deletion index.
The full-state oracle retains its distinct correctness role.
Inventories bind normalized manifests, target, source hashes, actual runtime, limits, execution profile, complete planned products, and counterbalanced order.
Model-only confirmation membership is implemented.
Each role uses a separate bounded child and a complete declared external observer transaction.
Actual empirical inventories remain absent.

Measured ordered sequences charge indexed original preparation once and ordinary model-only original construction separately once.
Repair and indexed fresh share that indexed preparation observation explicitly.
Every actual scheduled request has separate observed roles and preserves cumulative retained membership and fixed original normalization.
The production predecessor check reads the prior state-producing setup/repair child receipt and exact model/state artifacts within the measured method.
An external research lineage/oracle commit is not a required production service input.
The harness separately verifies research lineage and independent oracle equality before advancing.
Failures, interrupted attempts, later unstarted steps, original observations, and budget evidence remain retained.
Restart does not convert archival loading into a new independent latency sample.

Each observer covers source/input checks, bounded worker startup and admission, loading, required service work, output serialization, child commitments, exit, cleanup, worker accounting/commit, and output validation.
Its contiguous timing spans sum to the enclosing clock without adding nested child durations again.
Observer bootstrap and final observer receipt remain excluded.
External equality, common-model conversion, quality, sequence scheduling, and research lineage are separate.
A system's preparation-plus-requests lifetime is an attributable transaction-cost estimand, not elapsed wall time of the full validation harness.
Operating-system caches remain uncontrolled.

Clean mode disables optional Python profiling, tracing, allocation tracing, monitoring tools, and detailed telemetry in both observer and leaf.
Required exact arithmetic ledgers and correctness work remain charged.
Native profilers remain unobserved.
Diagnostic execution can preserve exact model/state outputs but cannot enter clean timing ratios.
Frozen runtime bindings reject incompatible environments rather than treating them as interchangeable repetitions.

Artifact-aware analysis rehashes the archive, observer, child, actual output, source/input/runtime, and budget bindings.
It reconstructs common model equality and within-contract state equality instead of trusting convenience flags.
All frozen missing, failed, interrupted, and unstarted slots remain visible.
One original observer identity/attempt cannot occupy several roles, roots, or repetitions.
An unsealed parent cannot supply complete primary timing even when its leaves finished.
Request medians reduce paired repeats, request log ratios average within root, and roots receive equal weight.
Bootstrap intervals resample roots only.
Available-pair estimates remain conditional.
Only the frozen sole primary comparator/configuration can receive confirmation timing flags, with all planned exact clean completion and frozen inference settings.
Secondary indexed and full-state ratios do not create extra unadjusted confirmatory claims.

The unchanged feasibility policy now has an executable conditional evaluator.
It checks exact counts, finite-quality evidence, resource limits, complete three-request lifetime costs, and missing evidence.
Its output cannot establish empirical attainment, authorize research, permit confirmation, or prove population speedup.
Typed measured archive evidence can bind the timing/model/state/resource projection.
Changed-ancestor coverage needs matched diagnostic identities and complete denominators without relevant omissions.
Quality, complete resources, real source provenance, and sampling assumptions retain independent evidence obligations.
The frozen thresholds remain engineering decisions without observed attainment.

Provider diagnostics now expose available affine inconsistency, selected-coefficient box rejection, extraction-stage failures, and finite/center/curvature/gradient proof components.
The selected free-zero coefficient vector can violate its box even when another affine representation could fit.
Therefore that rejection does not prove full-domain exclusion.
Box providers expose their available envelope and anchor route.
Clean mode skips lazy diagnostic builders; bounded numerical/text encoding and omission counters remain explicit.
These diagnostics are proof bounds and observed causes, not realized-error measurements, exhaustive primitive traces, or hidden arithmetic-intermediate accounting.

Final validation records 524 correctness tests.
The task register contains V9_REQUIRED_COMPLETED completed and V9_REQUIRED_OPEN open required items, plus 12 conditional extensions.
C04 remains closed at its written policy scope.
C05 and D05 remain partial; the final register records D04's review disposition.
G0 remains open.
Protocol version 5 records current implementation and unresolved real-evidence fields while preserving the pause.
The consolidated PDF remains the unchanged 35-page revision 7 report; the new current note is docs/REVISION_9.md.

Actual checkpoint/tokenizer/document/corpus/token artifacts, resource-feasible model execution, primary settings, disjoint source pools, root draws, score artifacts, workloads, empirical inventories, and precision justification remain unresolved.
Practical acceptance, complete costs, full-model speedup, quality, and feasibility are unmeasured.
The manuscript, current literature audit, scientific review, reproducibility release, and submission checks remain ahead.
Historical missing raw results remain unavailable.
Research archives and the bounded cache trust registry remain outside returned live-state deletion guarantees; trusted hashes do not establish hostile-storage authentication or physical erasure.
The user continues to authorize repository checkpoints and complete restart context.


## Final revision 9 continuation work

The user asked us to keep progressing through known next tasks rather than end at an early checkpoint.
The existing research-experiment pause remained active throughout.
This pass continued implementation, independent review, correctness fixtures, manuscript preparation, and a bounded citation check.

The four-method measured engine, frozen campaign inventory, ordered per-method sequence runner, and artifact-aware analysis are integrated.
Each system pays its own original preparation and every request under the same declared transaction boundary.
Ordinary model-only fresh emits no deletion index; direct fresh remains the full-state oracle.
Repair and indexed fresh receive the same valid reusable information.
The charged sequence predecessor is the prior setup/repair child's own committed receipt and artifacts.
External research lineage, oracle copies, and prior observers are not required service dependencies.

Revision 9 adds diagnostic interval coordinates and explicit loading, construction, serialization, durable-output, and cleanup spans.
The verified diagnostic adapter checks disjointness, containment, and exact sums.
Unknown worker/controller time stays residual; named_attribution_complete remains false when such time remains.
It does not subtract profiling overhead to estimate clean timing.
The original exhaustive D04 criterion remains partial.
Provider diagnostics add available fit causes and error-bound components, but C05 and physical/transient D05 observability remain partial.

The public feasibility bridge accepts loader-issued clean and diagnostic sequence evidence.
It derives actual target graphs, transitive changed-ancestor denominators, retained groups, complete replay audits, target-call counters, bound quality, preparation, and request sums.
The bridge also reads the complete trusted protocol CPU ledger and complete supplied campaign-root file inventories.
Reservations, overruns, prior/unselected attempts, missing workers, aliases, and nontransaction files stay visible.
Ledger snapshots cover that protocol at read time, not global/project/controller CPU; storage covers supplied roots, not all inputs or physical disk allocation.
Read-only analysis never instantiates writers or reconstructs missing budget files.
Scientific real-workload provenance is still unavailable, so the public bridge cannot promote the project into empirical success.

New user-facing commands include run_measured_campaign.py, run_measured_sequence.py, summarize_measured.py,
analyze_diagnostic_breakdown.py, evaluate_feasibility.py, and check_runtime.py.
Their argument contracts and pauses are documented in the corresponding current docs.
No current protocol or software fixture authorizes research execution.

The prospective manuscript and evidence companion now make the exactness, conditional work, fair-comparator, and empirical argument reviewable.
They contain ten explicit unfilled result slots, five table plans, and three figure plans.
Independent manuscript review checks the math and comparison scope.
The ten working reference identities were checked on primary pages; the relevant calibration-scale Appendix E was inspected.
This bounded check does not close the broader literature audit or establish priority.
The consolidated 35-page report and existing figure remain unchanged revision 7 artifacts.

The final integrated validation and source hashes are recorded in docs/VALIDATION.md and validation/*v9*.
The original task register remains conservative: 29 completed, 49 open required items, 12 conditional extensions.
Several implementation substeps are closed within those open research tasks; no empirical gate is closed.
Next work depends on actual validated model/tokenizer/text artifacts, resource-feasible execution, final configurations and source pools,
independent roots and statistical precision, and an instruction to resume research experiments.
The main-text/supplement must then incorporate observed evidence and undergo final novelty, limitations, reproduction, and venue checks.
Do not turn software fixture timings, old unrecovered narrative, or conditional cost lemmas into reliable speedup claims.
