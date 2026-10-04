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
