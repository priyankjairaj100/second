# Exact Calibration-Data Deletion for a Sequential Language-Model Quantizer

**Prospective main-text draft, 4 October 2026.** Mathematical and implementation statements below describe the declared reference contract. No real-model experiment has been completed for this draft. Bracketed `EVIDENCE` markers are mandatory unfilled result sentences, not claims. The reference identifiers map to repository sources; their primary landing pages were checked on 4 October 2026. Appendix E of R9 was also inspected. See CITATION_CHECK_V9.md. The broader novelty audit and final bibliography remain open. This file does not close manuscript or submission readiness.

## Abstract

Calibration documents influence sequential weight quantization both through local second-order statistics and through the quantized prefixes that generate later calibration features. Deleting their contributions from an old covariance is therefore insufficient when earlier codes change. We study exact calibration-data deletion for a specified finite feature evaluator and rational sequential quantizer, with the base model held fixed. Our repair procedure maintains additive record summaries defined by corpus-independent references, encloses retained statistics under a newly certified prefix, and accepts a discrete code only when its rounding decision is certified. A compact representation omits quadratic matrix coefficients while retaining a sound positive-semidefinite proposal; uncertain groups are replayed. Under successful required finite evaluations and sufficient resources, repair returns the retained-only model and the same canonical auxiliary state as fresh construction, including after repeated deletion. We distinguish this correctness guarantee from conditional complete-work savings and from the benefits available to an equally indexed fresh solver. **[EVIDENCE A1: state the supported real checkpoints, corpus and complete workload after artifact verification.] [EVIDENCE A2: report complete request and preparation-inclusive lifetime results against model-only fresh, all planned failures, and uncertainty; otherwise state that practical savings were not established.] [EVIDENCE A3: report changed-prefix coverage and absolute NLP quality, or identify the limiting failure.]**

## 1. Introduction

Post-training quantization can use calibration text to choose a compact model from fixed pretrained weights. In a sequential pipeline, quantized weights from earlier stages also change the features used to calibrate later stages. A document can consequently affect decisions well beyond its direct contribution to the first covariance. If that document is removed, the natural counterfactual is to run the same complete quantization procedure on the retained corpus.

This is a different deletion target from removing training information in the base weights and testing whether later quantization preserves forgetting [R3]. We keep those weights fixed. The requested change concerns calibration influence in the quantized output and its declared auxiliary state. Existing work on calibration-state provenance already makes broad claims of an unexplored connection between calibration and unlearning inappropriate [R9]. Our problem is the exact reconstruction of a specified retained-data sequential quantizer.

Two obstacles shape the method. First, once an early code changes, cached activations may no longer equal the retained target activations. A useful repair rule must reason under the new prefix rather than assuming that the old model remains valid. Second, auxiliary state can itself retain calibration influence. Producing the correct model while retaining an index fitted to the deleted corpus does not meet a complete-state counterfactual.

We use a fixed, corpus-independent response representation to address these obstacles together. Intrinsic record summaries are added exactly and can be removed exactly. Their contraction at a new ancestor prefix need only enclose the true covariance: the covariance need not be reconstructed exactly if every admissible covariance yields the same discrete codes. If the enclosure is insufficient, the algorithm obtains additional information by replaying retained groups. This connects additive deletion state [R4], approximate sufficient statistics [R5], and certified response bounds [R7] to the discrete decisions of a sequential quantizer. Those ingredients are established; our claim concerns their composition and contract, not priority for the ingredients.

The resulting theory establishes three statements. It gives an exact-output repair theorem that permits changed ancestors; it gives a canonical response-state construction with compact and quadratic storage tiers; and it isolates sufficient conditions for avoiding replay and for reducing complete work. None implies a favorable acceptance rate or measured speed on language models. A fair evaluation must compare repair with ordinary model-only requantization, charge preparation and state maintenance, and give an indexed fresh solver every reusable item available to repair. **[EVIDENCE I1: replace this sentence with the principal empirical finding and its failure scope, using the same primary endpoint as A2.]**

## 2. The deletion target

Let \(C\) be the original calibration records, \(F\subseteq C\) the deletion request, and \(R=C\setminus F\). Fix pretrained weights \(W\), a directed acyclic graph of quantization stages, finite grids, visit order, and the lower-code midpoint tie rule. At stage \(\ell\), let \(X_{\ell j}(Q_{<\ell})\in\mathbb R^{d_\ell\times t_j}\) denote the feature matrix for record \(j\) evaluated under its quantized ancestors. The target covariance is

\[
H_\ell(R)=\lambda_\ell I+
\frac{1}{M_{0,\ell}}\sum_{j\in R}
X_{\ell j}(Q_{<\ell}(R))X_{\ell j}(Q_{<\ell}(R))^\top,
\tag{1}
\]

where the positive rational ridge \(\lambda_\ell\) and original normalization \(M_{0,\ell}>0\) remain fixed after deletion. Exact rational reverse-LDL elimination and deterministic grid rounding define \(Q_{\mathrm{seq}}(W,R)\). A change to packing, normalization, scale fitting, activation order, or another corpus-dependent branch would define a different target unless that branch were included in the counterfactual.

Our primary evaluator, \(V_{\mathrm{cert}}\), executes a pinned scalar finite program. Successful binary64 feature outputs are interpreted as exact dyadic rationals when forming (1). The implementation proves supported nonlinear rounding through rational intervals and rejects invalid domains or unresolved operations. It is a **partial evaluator**: successful target calls define the intended output; arbitrary inputs are not guaranteed to complete. The target differs from stock GPTQ's floating reductions and factorization [R1], from an ideal real-arithmetic network, and from the repository's legacy evaluator. We claim no bitwise equivalence among these programs.

Record boundaries, tokenization, masks and positions are fixed. Records are evaluated independently; deleting one does not repack the others. Fixed embeddings, norms, biases and output heads remain part of the bound model. A verified retained source remains available for replay, and the request supplies deleted payloads for checked subtraction.

For a fixed response tier, define the promised state

\[
\mathcal A(R)=\bigl(Q_{\mathrm{seq}}(W,R),\;
\mathrm{Bindings}(R),\;\mathrm{ResponseMoments}(R),\;
\mathrm{ErrorMoments}(R)\bigr).
\tag{2}
\]

The goal is byte equality with a fresh constructor of (2), not equality to a different historical interface that retains every sequential activation. Fixed identifier grouping and canonical rational serialization determine state bytes. The state includes retained identities and content/contribution digests, but not per-record feature or derivative arrays. Trusted state origin or an independently trusted expected digest is required; syntax and positive-semidefinite checks cannot authenticate historical provenance. This logical state guarantee does not erase external archives, caller copies, physical memory, or information already learned in \(W\).

## 3. Canonical response summaries and repair

### 3.1. Sound finite response bounds

Fix a stage and a chart chosen independently of the deletable corpus. Write its installed ancestor parameters as

\[
\theta=\theta_0+Da+u,\qquad Da=\sum_{t=1}^{r}a_tD_t.
\]

For record \(j\), choose fixed rational response coefficients \(Z_{j0},\ldots,Z_{jr}\) and set \(Z_j(a)=Z_{j0}+\sum_ta_tZ_{jt}\). Let \(f_j\) be the ideal smooth feature map associated with the finite program. Assume uniform finite-output error \(\nu_j\), center error \(e_{j0}\), directional errors \(e_{jt}\), restricted Hessian bound \(h_j\), and residual-direction bound \(l_j\) on a proved region. That region contains the entire chart segment \(\theta_0+sDa\) and, when \(u\ne0\), the residual segment \(\theta_0+Da+su\), for all \(s\in[0,1]\). The Hessian operator bound uses Euclidean coefficient directions and a Frobenius output norm; the residual derivative is bounded by \(l_j\|u\|_\Theta\) along its entire segment. Taylor's integral remainder gives

\[
\|X_j-Z_j(a)\|_F\le
\nu_j+e_{j0}+\sum_t|a_t|e_{jt}
+\tfrac12h_j\|a\|_2^2+l_j\|u\|_\Theta.
\tag{3}
\]

The Hessian bound must include every mixed derivative. The finite-output term must enclose the actual operation schedule; differentiating ideal operators or supplying a measured residual is insufficient. The automatic affine provider currently accepts only exact chart membership, \(u=0\). The general bound permits a residual only when its displayed premise is proved. Fixed-grid parameter boxes provide a separate domain control, not a guarantee of tightness or acceptance.

Define nonnegative descriptor and query vectors

\[
b_j=(\nu_j+e_{j0},e_{j1},\ldots,e_{jr},h_j,l_j),\quad
v=(1,|a_1|,\ldots,|a_r|,\|a\|_2^2/2,\|u\|_\Theta).
\]

For a retained group \(g\), the exact additive moment
\(C_g=M_0^{-1}\sum_{j\in R_g}b_jb_j^\top\) gives
\(\epsilon_g^2=v^\top C_gv\), an upper bound on the normalized sum of squared feature errors. All descriptor cross terms are retained. Each coefficient is an intrinsic record function of fixed references, so checked subtraction reproduces its retained-only sum.

### 3.2. A compact covariance proposal

The quadratic tier stores every coefficient of
\(S_g(a)=M_0^{-1}\sum_{j\in R_g}Z_j(a)Z_j(a)^\top\).
The compact tier instead stores the anchor Gram, \(r\) symmetric linear cross matrices, and a scalar tangent Gram \(G_g\). For \(\Delta Z_j=\sum_ta_tZ_{jt}\), define

\[
\begin{aligned}
S_{g,\mathrm{lin}}&=M_0^{-1}\sum_j
[Z_{j0}Z_{j0}^\top+Z_{j0}\Delta Z_j^\top+\Delta Z_jZ_{j0}^\top],\\
P_g&=M_0^{-1}\sum_j\Delta Z_j\Delta Z_j^\top,\qquad
\beta_g=a^\top G_ga=\operatorname{tr}(P_g).
\end{aligned}
\]

The omitted matrix satisfies \(0\preceq P_g\preceq\beta_gI\). Thus
\(\widetilde S_g=S_{g,\mathrm{lin}}+\beta_gI\succeq0\), without recovering \(P_g\). The exact surrogate norm is available as
\(z_g^2=\operatorname{tr}(S_{g,\mathrm{lin}})+\beta_g\).
An outward bound on \(\delta_g=2z_g\epsilon_g+\epsilon_g^2\) yields

\[
-(\beta_g+\delta_g)I
\preceq H_g^*-\widetilde S_g
\preceq\delta_g I,
\tag{4}
\]

where \(H_g^*\) is the true retained group Gram without ridge.

**Proposition 1 (compact enclosure).** Under (3), intrinsic exact moments, and sound outward contraction, (4) holds. With already replayed groups \(T\), unresolved groups \(U\), and

\[
\widetilde H=\lambda I+\sum_{g\in T}H_g^*+\sum_{g\in U}\widetilde S_g,
\quad A=\sum_{g\in U}(\beta_g+\delta_g),\quad D=\sum_{g\in U}\delta_g,
\]

we have \(\widetilde H\succeq\lambda I\). If \(A<\lambda\), then

\[
\alpha\widetilde H\preceq H^*\preceq\omega\widetilde H,
\qquad \alpha=1-A/\lambda>0,\quad\omega=1+D/\lambda.
\tag{5}
\]

*Proof sketch.* Expanding \(XX^\top-ZZ^\top\) bounds its operator norm by \(\delta_g\). The omitted response Gram is positive semidefinite with trace \(\beta_g\), which proves (4) and positivity of the shifted proposal. Summation and the ridge floor give (5). Replaying a group replaces its proposal by its exact Gram and removes its budgets. Endpoints tighten at a fixed prefix, although candidate margins and acceptance need not improve monotonically. ∎

Per group and stage, the implemented compact tier stores
\((r+1)d^2+r^2+(r+3)(r+4)/2\) rational slots; the quadratic tier stores
\((r+1)(r+2)d^2/2+(r+3)(r+4)/2\).
These counts exclude directions, model weights, metadata, payload storage, integer bit lengths, and temporary objects. Exact-query lower bounds for the full Gram polynomial do not imply that its coefficients are necessary for an exact discrete answer: the compact method accepts only when its uncertainty cannot change that answer, and otherwise requests more information.

### 3.3. Discrete certification and sequential composition

Factor the proposal as \(\widetilde H=\mathcal L^\top D_q^{-1}\mathcal L\), with \(\mathcal L=I-B\), \(D_q=\operatorname{diag}(g_i)\), and \(g_i>0\). For a row \(w\) and a forced preceding code prefix \(q_{<i}\), let

\[
v_i=w_i-B_{i,<i}(w-q)_{<i},\qquad
E_i=\sum_{h<i}(v_h-q_h)^2/g_h.
\]

**Lemma 2 (conditional decision displacement).** Under (5), the corresponding true-metric conditional input under the same forced prefix satisfies

\[
|v_i^*-v_i|^2\le
\frac{(\omega-\alpha)^2}{4\alpha\omega}\,g_iE_i.
\tag{6}
\]

This is a specialization of classical positive-definite matrix geometry [R6]. Its constant is sharp for the abstract quadratic perturbation class; neither that constant nor a GPTQ/Babai interpretation is claimed as new [R2]. Whitening and bounding the change of a constrained quadratic minimizer prove (6). Containment of the resulting interval in a rounding cell proves the next code. Coordinate induction then certifies a complete stage. The implementation uses squared rational comparisons; positive-radius boundary contact abstains, and zero-radius decisions apply the exact lower-code tie rule.

An optional ridge-aware interval verifier supplies a second sound route when the relative spectral test is unavailable or inconclusive. It encloses reverse elimination, intersects pivots with the known ridge floor, and checks lower-tie cells. Rejection continues replay. It adds possible certificates and extra work; it does not imply universal acceptance or runtime dominance.

**Algorithm 1: canonical sequential repair.**

1. Validate the entering state, request, target, and source bindings. Recompute deleted intrinsic contributions, verify their digests, and subtract them exactly.
2. Visit stages topologically. Fix the already certified new ancestor prefix. Query retained response moments only under that prefix.
3. Form a sound positive-definite proposal and candidate codes. Accept the stage only if every decision is certified by a supported verifier.
4. On unavailable or insufficient evidence, replay an unresolved retained group under that same prefix, update the exact Gram contribution, and retry. Each failed retry replays a new unresolved group, so uncertainty-only retries cannot prevent progress. Once all groups have replayed, use the exact retained covariance.
5. Serialize the complete model and retained intrinsic state canonically; commit only after the request succeeds. Required finite-evaluator failure aborts without committing an approximate model.

**Theorem 3 (complete model and canonical state).** Fix the target, independently chosen references/domains, group assignment, and state tier. Assume record-local evaluation, valid sound response premises for every accepted certificate, exact additive and decision arithmetic, trusted state origin, verified deleted payloads and retained replay access. Then every successfully committed request returns exactly \(\mathcal A(R)\). If there are finitely many groups/stages, every required finite evaluation succeeds, exact local arithmetic terminates within the available resources, and retries eventually replay a new unresolved group, the request completes. The statement permits changes in the first stage and every later stage.

*Proof sketch.* Deleted intrinsic sums equal fresh retained sums by exact additivity. At a stage whose ancestors have been proved correct, its enclosure refers to the true retained features. Lemma 2 or the alternative sound verifier proves the candidate codes; full replay instead supplies the exact covariance. Coordinate induction proves the stage and topological induction proves the model. The final auxiliary state depends only on retained records and fixed references, so canonical serialization equals fresh construction. Finitely many replay steps resolve uncertainty under the additional completion assumptions. Apply the argument after each completed request for repeated, combined, reordered, or adaptive deletion. ∎

**Corollary 4 (conditional zero retained replay).** At every stage under its newly certified ancestor prefix, let \(\beta=\sum_g\beta_g\), \(\delta=\sum_g\delta_g\), and let \(\tau>0\) lower-bound the candidate rounding-cell margin divided by \(\sqrt{g_iE_i}\) for every positive-energy decision. If

\[
\beta+\delta\le\lambda/2,
\qquad \beta+2\delta<\lambda\tau,
\tag{7}
\]

and all domain, finite-bound and zero-energy tie premises hold, the compact spectral rule certifies the entire model without retained feature replay. Indeed its displacement coefficient is
\((\beta+2\delta)/(2\sqrt{(\lambda-\beta-\delta)(\lambda+\delta)})<\tau\).
This condition concerns the actual repaired prefixes and margins. It is not implied by a small deleted fraction. Finite error floors, out-of-chart prefixes, weak margins, or broad domains can defeat it. The stronger ideal whitened quadratic-radius result is supplementary theory; the implemented quadratic tier uses its declared absolute-error or interval rule and cannot inherit that stronger result by name.

## 4. Equal information and complete cost

Canonical moments support both repair and fresh solving from the retained index. In the response implementation, these routes share the stage planner and certificate options; the old quantized model is not an extra information advantage. An equally indexed fresh baseline must therefore receive the same valid summaries, source access and solver. Extra split-interface validation is reported as overhead, not a deletion-specific solver improvement.

The original-model Gram cache is a distinct control. It can subtract deleted contributions exactly while all required ancestors match the entering cached model. Changed ancestors require retained replay and a refreshed cache. This yields the same target within its own state interface but no general changed-prefix avoidance guarantee.

For a specified ordinary fresh comparator, write \(C_F=F+G+J\), where \(F>0\) is genuinely avoidable retained work and \(G+J\) is demonstrated comparable solving and output work. If repair satisfies
\(0<C_R\le sF+U+G+J\), with \(s,u,\gamma\ge0\), \(U/F\le u\), \((G+J)/F\le\gamma\), and \(s+u<1\), then

\[
\frac{C_F}{C_R}\ge\frac{1+\gamma}{s+u+\gamma}>1.
\tag{8}
\]

Every excess cost belongs in \(U\): deleted evidence, repeated fits or factorizations, proof attempts, metadata, state maintenance, extra output and required verification. Equation (8) is an arithmetic implication of these premises, not a performance result. A fraction of accepted groups is not a cost-weighted value of \(s\), and rational-operation counts are not constant-time word operations.

For the frozen request horizon \(H\), preparation-inclusive costs instead obey

\[
T_R(H)-T_F(H)=P_R-P_F-\sum_{h=1}^{H}(F_h-R_h),
\tag{9}
\]

where \(P_R\) prepares the original model and index, \(P_F\) independently prepares the original model alone, and \(F_h,R_h\) are the complete fresh and repair request costs (distinct from the avoidable-work term \(F\) above). Strict gain requires savings greater than this preparation debt. A first crossing can be reversed by a later expensive request. Missing or failed required terms leave complete lifetime undefined, while observed consumed costs and unknown/missing cost indicators remain reported. No universal full-model speedup or population reliability follows from (7)–(9).

## 5. Evaluation design and unfilled results

The prospective study uses real text, independently sampled calibration roots, fixed record boundaries, and disjoint development-side, confirmation, and heldout documents. Concrete checkpoints, token pools, primary configuration, final runtime/hardware conditions, and empirical inventories remain unresolved. Candidate metadata and planning sizes are not validated execution inputs. **[EVIDENCE S1: insert the final source/target table and resource feasibility outcome; stop the full-model empirical claim if the declared program cannot complete.]**

Four fresh-process transactions are scheduled in a frozen counterbalanced order: repair, equally indexed fresh, direct full-state fresh, and ordinary model-only fresh. Model-only fresh builds no deletion index. All four must agree on the target and exact stage codes; the three canonical-state methods additionally match state bytes. Setup and optional quality have separate workers. Clean observers and children disable supported optional Python profiling and detailed telemetry; OS caches, native profiling and machine load are not universally controlled. The complete declared boundary includes required validation, startup, loading, work, durable child/controller commits, cleanup, accounting and output verification, excluding observer bootstrap and measurement-manifest preparation before the boundary, and final observer receipt/snapshot writes after it. Research equality and orchestration work are excluded symmetrically; available observations are reported separately, and unmeasured components remain unknown. The declared transaction clocks do not establish complete research-harness wall-time or CPU accounting.

The independent-request matrix covers uniform, contiguous, concentrated and difficult requests chosen from frozen original-state information. Its primary comparison is model-only fresh versus repair; controls and extensions remain separate. Medians over timing repeats are reduced within requests, then log ratios within roots and equally across roots. Root-cluster bootstrap intervals accompany every eligible conditional ratio and the complete planned failure denominator. Reused observer receipts cannot count as independent repetitions. **[EVIDENCE R1: insert the primary latency and failure table, including an explicit negative result when warranted.]**

A separate ordered study deletes three disjoint batches while consuming each preceding committed state. Each system pays for its own original output once; indexed repair/fresh share the declared indexed preparation, and model-only fresh pays for a separate original model construction. Analysis independently resums complete saved observations. Lifetime is the sum of attributable per-system transactions, not elapsed research-harness wall time. Oracle, equality and research-lineage work are excluded symmetrically; available cost observations are reported separately without imputing unmeasured components. Online predecessor validation requires no prior oracle, observer or research common-model-copy artifacts. **[EVIDENCE R2: insert every system's preparation, fixed-horizon cost and final balance, with incomplete horizons visible.]**

Mechanism diagnostics use separately bound diagnostic replicates with the same target, request, prefixes, model and state as clean observations. The changed-ancestor denominator includes every nonempty retained group whose transitive ancestor codes actually change. Source-cache hits do not count as avoiding target-feature evaluations. Missing groups, saturation or truncated evidence remain inconclusive. Compare compact/quadratic moments, fixed-reference/full replay, the interval portfolio, and original-model caching under declared storage budgets. **[EVIDENCE R3: insert complete changed-prefix coverage and replay costs; retain any result showing that proof overhead exceeds avoided work.]**

NLP evaluation compares base, originally calibrated and retained-calibrated models on identical heldout tokens and a task selected for the supported application. Exact agreement with a retained oracle establishes relative agreement under its declared inference contract, not useful absolute language quality or native-framework equivalence. **[EVIDENCE R4: insert absolute quality, calibration-deletion effects and the selected task metric.]**

The evidence slots are specified in `MANUSCRIPT_EVIDENCE_SLOTS.md`. No table or plot from software fixtures may fill them. The fixed feasibility policy controls engineering continuation, not confirmation power or publication acceptance.

## 6. Related work and limitations

GPTQ supplies the sequential second-order quantization setting [R1], and its relationship to nearest-plane geometry is existing work [R2]. Quantization-robust training-data unlearning studies a different target [R3]. Calibration-state provenance and retained-only scale audits are also precedents [R9]. We therefore avoid a first-use claim for calibration deletion or compression-aware forgetting.

Summation-form unlearning [R4], polynomial approximate sufficient statistics [R5], algorithm-output sketches [R8], and certified Taylor bounds [R7] establish important components. Our summaries are intrinsic record responses under independent parameter references; their deterministic remainder bounds certify exact discrete outputs, with replay when insufficient. This does not imply a better sketch dimension than randomized whole-algorithm methods. Complete-state deletion and adaptive history semantics also require attribution [R10]. The conditional displacement constant is classical [R6]. A current literature audit must still determine the precise contribution boundary before submission.

The reference target is deliberately explicit and can be expensive. Exact rational arithmetic, finite primitive certification, high-rank jets, dense directions, chart fitting and canonical output can dominate saved feature work. The compact trace bound can be loose; full quadratic moments increase storage; a complete fixed-grid domain can have uninformative bounds. Every successful theorem invocation requires valid numerical premises, and target failure can prevent completion. Retained replay requires source availability. The state guarantee assumes trusted provenance and excludes external archives and base-weight knowledge. Only real frozen workloads can establish whether this contract supports a useful language-model application. **[EVIDENCE C1: final conclusion must match the strongest supported combination of exactness, coverage, quality, complete cost and uncertainty; retain a limitation-led conclusion if any essential result fails.]**

## Working repository-mapped references

These identifiers support drafting. Their primary landing pages were checked, with the additional R9 appendix inspection described in `CITATION_CHECK_V9.md`. All mappings already occur in `NOVELTY_AUDIT.md`; this check discovered no new reference. Full bibliographic formatting, theorem-level attribution, adjacent-work completeness, and novelty priority require the final literature pass.

| ID | Existing repository mapping |
| --- | --- |
| R1 | Frantar et al., *GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers*, ICLR 2023, [arXiv:2210.17323](https://arxiv.org/abs/2210.17323). |
| R2 | Chen et al., *The Geometry of LLM Quantization: GPTQ as Babai's Nearest Plane Algorithm*, ICLR 2026, [official repository](https://github.com/IST-DASLab/GPTQ-Babai). |
| R3 | Zhang et al., *Catastrophic Failure of LLM Unlearning via Quantization*, ICLR 2025, [arXiv:2410.16454](https://arxiv.org/abs/2410.16454). |
| R4 | Cao and Yang, *Towards Making Systems Forget with Machine Unlearning*, IEEE S&P 2015, [author page](https://www.cs.columbia.edu/~junfeng/papers/unlearning/). |
| R5 | Huggins, Adams and Broderick, *PASS-GLM*, NeurIPS 2017, [proceedings](https://papers.nips.cc/paper_files/paper/2017/hash/07811dc6c422334ce36a09ff5cd6fe71-Abstract.html). |
| R6 | Lin and Sinnamon, *The Generalized Wielandt Inequality in Inner Product Spaces*, [arXiv:1201.6294](https://arxiv.org/abs/1201.6294). |
| R7 | Entesari and Fazlyab, *Hierarchical End-to-End Taylor Bounds for Complete Neural Network Verification*, L4DC 2026, [proceedings](https://proceedings.mlr.press/v331/entesari26a.html). |
| R8 | Gunn, *How to sketch a learning algorithm*, [arXiv:2604.07328](https://arxiv.org/abs/2604.07328). |
| R9 | Junlong Shen and Xingyu Li, *Published Unlearning Numbers Move Per Checkpoint…*, [arXiv:2609.11490v1](https://arxiv.org/abs/2609.11490v1), 10 September 2026, Appendix E. Title abbreviated here. |
| R10 | Cohen et al., *Control, Confidentiality, and the Right to be Forgotten*, [arXiv:2210.07876](https://arxiv.org/abs/2210.07876). |
