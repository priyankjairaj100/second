# Novelty audit and defensible paper claims

Audit date: 4 October 2026. Scope: the current sequential calibration-deletion theory, plus the proposed canonical response-moment extension. This is a targeted primary-source audit, not an exhaustive priority determination. No benchmark, model download, or dataset experiment was run for this audit.

## Recommendation

The strongest paper is **Exact Calibration-Data Deletion for Sequentially Quantized Language Models**. Its central result should be an exact-output algorithm that uses approximate, rigorously enclosed response statistics to avoid retained-document forwards even when early quantization decisions change. The paper should preserve the original sequential quantizer, account for complete retained-only state, and measure the storage/work boundary.

The paper should not lead with a newly discovered matrix inequality, the first Taylor sketch for deletion, the first use of additive sufficient statistics, or the first connection between compression and unlearning. Those broader ingredients have substantial prior art. The distinctive contribution is their precise composition around a discontinuous, calibration-dependent pipeline: sound response approximation, exact discrete decisions, changed-ancestor induction, canonical state, and a complete cost comparison.

An implemented reference verifier and valid theorems do not establish practical speedup. The empirical claim still requires saved retained replay and end-to-end cost on real language-model calibration workloads.

## Search quality and reproducibility

The search used both available engines, followed by direct arXiv, proceedings, author, and official-repository reads. Several multi-phrase quoted searches in the stronger engine returned generic last-keyword pages. Those failed searches provide no negative evidence. Useful discovery came from simpler queries, including `quantization unlearning arxiv`, `machine unlearning Taylor sufficient statistics`, `PASS GLM polynomial approximate sufficient statistics`, `generalized Wielandt inequality positive definite angles`, and `incremental neural network verification weight perturbations`. Every substantive prior-art claim below is tied to a primary URL actually inspected. Search-result publication ages were not used as bibliographic dates when the primary page supplied dates.

The narrow fixed-base-weight calibration-document deletion problem did not appear as the main problem in the inspected sources. That is a qualified observation, not proof of absence. The calibration-state audit below is particularly important: even the broader problem motivation has close adjacent work.

## Closest primary sources

All links in this table were inspected on 4 October 2026. Dates refer to the paper or named version, not the crawler.

| Primary source | What is already established | Boundary for this project |
| --- | --- | --- |
| Frantar et al., **GPTQ**, arXiv v1 31 Oct 2022; ICLR 2023; [paper](https://arxiv.org/abs/2210.17323), [official implementation](https://github.com/IST-DASLab/gptq) | Calibration-based approximate second-order weight quantization and sequential error compensation. | GPTQ is the reference algorithmic family. Subtracting an unchanged-feature Gram or using inverse updates is not sufficient novelty. |
| Chen et al., **The Geometry of LLM Quantization: GPTQ as Babai's Nearest Plane Algorithm**, ICLR 2026; [official repository and paper links](https://github.com/IST-DASLab/GPTQ-Babai) | The GPTQ/Babai relationship, geometric interpretation, and guarantees under the paper's assumptions. | Do not claim the lattice interpretation as new. Our fixed-grid, possibly saturated decision certificate has a different objective: exact counterfactual agreement under metric uncertainty. |
| Zhang et al., **Catastrophic Failure of LLM Unlearning via Quantization**, arXiv v1 21 Oct 2024, v3 21 Mar 2025; ICLR 2025; [paper](https://arxiv.org/abs/2410.16454) | Quantization can restore behavior apparently removed by training-data unlearning. | This changes/compares unlearned base models before compression. Our base weights stay fixed; the deleted inputs belong to calibration. |
| Abitante et al., **Quantization-Robust LLM Unlearning via Low-Rank Adaptation**, v1 13 Feb 2026, v3 7 Apr 2026; IJCNN 2026; [paper](https://arxiv.org/abs/2602.13151) | LoRA-based unlearning designed to survive later quantization. | A frozen base model alone does not establish our distinction: their adapters still encode training-data unlearning, whereas our complete target is retained-only recalibration. |
| Mishra and Mehreen, **QUAIL**, 21 Jan 2026; [paper](https://arxiv.org/abs/2601.15538); Sadhu et al., **Forgetting That Sticks**, 14 May 2026; [paper](https://arxiv.org/abs/2605.15138) | Additional quantization-aware/quantization-permanent approaches to preserving forgetting. | Cite these as adjacent objectives. Do not present `quantization + unlearning` as an unexplored combination. Their claimed guarantees should be described as the authors' claims, not adopted as verified facts here. |
| Xiao et al., **The Right to be Forgotten in Pruning**, v1 24 Jul 2025, v2 2 Dec 2025; [paper](https://arxiv.org/abs/2507.18725) | Deleted data can affect pruning topology; un-pruning seeks retained-data topology with an approximation bound. | Compression structure carries data influence already has precedent. Our target is exact calibration-dependent quantization, including propagation through changed codes. |
| Shen and Li, **Published Unlearning Numbers Move Per Checkpoint...**, v1 10 Sep 2026; [paper](https://arxiv.org/abs/2609.11490), [Appendix E](https://arxiv.org/html/2609.11490v1) | At fixed weights, the authors refit static 8-bit activation scales on different calibration sets in vision models, including retained-only sets. They distinguish state provenance from stale-state effects and report limited downstream changes in that setting. | We cannot claim the first investigation of calibration-derived state in unlearning. This is an audit, not an exact sequential weight-repair algorithm; its weak effects also warn against assuming calibration deletion has major behavioral consequences. |
| Cao and Yang, **Towards Making Systems Forget with Machine Unlearning**, IEEE S&P May 2015; [author page](https://www.cs.columbia.edu/~junfeng/papers/unlearning/) | Unlearning through summation-form computations, including feature-selection and modeling stages. | Exact deletion by subtracting intrinsic record summaries is established. Our contribution must handle the changing nonlinear feature map and exact downstream decisions. |
| Huggins, Adams, and Broderick, **PASS-GLM**, NeurIPS 2017; [proceedings](https://papers.nips.cc/paper_files/paper/2017/hash/07811dc6c422334ce36a09ff5cd6fe71-Abstract.html) | Polynomial approximate sufficient statistics, with approximation guarantees and streaming/distributed extensions. | A polynomial response representation with additive coefficients is not a new abstraction by itself. The proposed use must add certified remainders, canonical deletion updates, and exact sequential discrete output. |
| Gunn, **How to sketch a learning algorithm**, v1 8 Apr 2026, v3 18 Jun 2026; [paper](https://arxiv.org/abs/2604.07328), [full PDF](https://arxiv.org/pdf/2604.07328) | Counterfactual model-output prediction after data deletion via higher-order derivatives in random complex directions, with error/failure guarantees under a stability condition. Forward-mode differentiation avoids explicit derivative tensors. | Strongest adjacent theoretical prior. Our sketch should be of independent record response maps in parameter directions, with deterministic enclosures used to certify exact discrete codes, rather than probabilistic approximation to measurements of a whole learning algorithm. |
| Lin and Sinnamon, **The Generalized Wielandt Inequality in Inner Product Spaces**, 30 Jan 2012; [paper](https://arxiv.org/abs/1201.6294), [author PDF](https://www.math.uwo.ca/faculty/sinnamon/pdf/wielandt.pdf) | Sharp relationships between angles under positive-definite changes of inner product, part of the classical Kantorovich/Wielandt theory. | The sharp shape constant is classical matrix geometry specialized to quantizer conditional inputs. Do not claim the scalar constant as a new general matrix inequality. |
| Cohen et al., **Control, Confidentiality, and the Right to be Forgotten**, v1 14 Oct 2022, v2 4 Dec 2023; [paper](https://arxiv.org/abs/2210.07876) | Connections among deletion, adaptive history independence, and interactive state semantics. | Complete-state and repeated-deletion semantics need attribution. Our new result is a concrete canonical response-index construction for this quantization target, not the definition of history independence. |
| **NN-Poly**, Frontiers in Robotics and AI, 2022; [primary article](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2022.968305/full) | Taylor-polynomial approximations to neural networks. | Network-to-polynomial conversion is prior art. Fixed independent parameter directions and a deletion-compatible coefficient index supply the application-specific structure. |
| Entesari and Fazlyab, **Hierarchical End-to-End Taylor Bounds for Complete Neural Network Verification**, L4DC 17–19 Jun 2026; [proceedings](https://proceedings.mlr.press/v331/entesari26a.html) | Certified Taylor bounds for neural-network reachability. | Higher-order verification and branch/refinement are established. We must specify and validate the actual remainder/numerical provider, not rename generic Taylor verification. |
| Fischer et al., **Shared Certificates for Neural Network Verification**, CAV 2022; [author page](https://www.sri.inf.ethz.ch/publications/fischer2021shared), [paper](https://arxiv.org/abs/2109.00542); **IVAN**, PLDI 2023; [official implementation](https://github.com/uiuc-arc/Incremental-DNN-Verification) | Reuse of proof effort across inputs or perturbed neural networks. | Certificate reuse and changed-weight verification are established; the distinction is exact retained-corpus quantization decisions and their canonical service state. |
| **GPTAQ**, arXiv 2504.02692; [paper](https://arxiv.org/abs/2504.02692); Li et al., **BRECQ**, 2021; [paper](https://arxiv.org/abs/2102.05426) | Asymmetric calibration and block reconstruction are existing quantization designs. | A fixed-teacher or reset-block alternative must remain a separately named target. Its novelty cannot be teacher anchoring or reconstruction alone. |

## The shape constant: an explicit classical reduction

This derivation is our comparison to classical matrix geometry, not a claim that the cited paper states this quantizer theorem verbatim.

Whiten the original metric. Let the new metric be a symmetric matrix M with aI <= M <= bI. For a fixed quantization prefix, let S be the feasible suffix-direction subspace, y the old minimizing residual, and z = y + delta the new residual. Then y is orthogonal to S, delta belongs to S, and Mz is orthogonal to S.

For nonzero z, the Kantorovich angle bound gives

    <z,Mz> / (||z|| ||Mz||) >= 2 sqrt(ab)/(a+b).

Since <delta,Mz> = 0, the same cosine is at most ||y||/||z||. Pythagoras gives

    ||delta|| <= (b-a)/(2 sqrt(ab)) ||y||.

One can verify the angle bound directly: M^2 <= (a+b)M-abI; for unit z and c=<z,Mz>, minimize c^2/((a+b)c-ab) over c in [a,b], obtaining 4ab/(a+b)^2. The coordinate dual norm and forced-prefix energy then produce the project's local bound chi(a,b) sqrt(g_i E_i).

This preserves the theorem's correctness and sharpness. The novelty statement should instead emphasize the resulting exact rounding certificate, harmless-scale invariance, finite-grid cells/ties, and its use under changed-prefix covariance enclosures. State sharpness for the abstract quadratic class, not as evidence that every transformer instance attains it.

## How to distinguish the proposed response index

The proposed extension fixes an anchor parameter vector and a finite direction family independently of the deletable calibration corpus. For each record it constructs polynomial coefficients of a stage response map, such as its Gram contribution, plus a certified remainder descriptor. Retained coefficients are canonical sums. A new candidate prefix supplies coordinates in the fixed family and an explicitly bounded residual outside the family. Evaluating the retained polynomial predicts the new Gram; the remainder encloses the true one; exact rounding is accepted only when the entire admissible region has the same output. Otherwise retained groups are replayed.

The following separations are necessary:

| Dimension | Our intended claim | What is insufficient |
| --- | --- | --- |
| Target | Exact full retained-only sequential quantizer output | Small logit error or approximate Gram alone |
| Direction choice | Fixed independently of deletable records, or reconstructed canonically at charged cost | Directions fitted to original calibration and retained after deletion |
| Coefficients | Intrinsic record contributions; exact/canonical retained aggregates | A frozen Taylor expansion of the originally calibrated model |
| Remainder | Sound on the whole accepted parameter/domain region | Empirical residuals on sampled records |
| Finite arithmetic | Encloses the actual pinned finite neural evaluator, or declares a different ideal target | Differentiating through ideal operators and calling the finite program certified |
| Deletion sequence | Fresh retained-set state after every completed request | Correct output with historical auxiliary state left behind |
| Work | Setup, deletion update, bounds, reads, replay, output, cleanup, arithmetic bit cost | A local oracle kernel timing |

Relative to Gunn's paper, emphasize the discrete-output certificate and canonical additive response state. Do not claim a generally better sketch dimension: his randomized scheme and our fixed-direction representation have different assumptions and guarantees. Full multivariate degree-p response coefficients in r directions can cost binomial(r+p,p) matrices. A low rank/direction budget only helps if the omitted-parameter residual can be certified cheaply and tightly. If most changed-prefix drift lies outside the direction span, higher polynomial degree may yield little improvement.

Relative to PASS-GLM and Taylor verification, the decisive new theorem is compositional: certified approximate sufficient information can determine the exact output of an adaptive discrete pipeline, with safe replay when information is insufficient. The argument needs every corpus-dependent branch, not only scalar rounding: ordering, scales, dead-column treatment, clipping, group construction, numerical schedules and packaging must be fixed or certified.

## Principal remaining attacks and how to close them

1. **The new method is an ordinary approximation plus rounding.** Answer with a full changed-ancestor theorem and a verified implementation that certifies every code, not selected rows. Explain why approximation can be harmless to a discrete target despite nonzero statistic error; distinguish exact decision certification from a claim that the approximate statistic is exact.
2. **The index makes a different task easier.** Preserve Q_seq(W,R). A fixed teacher may supply reference information, but may not replace target-prefix calibration. Keep the deletion-native teacher quantizer out of the primary equality theorem.
3. **The index retains deleted influence.** Prove intrinsic coefficients, remainder summaries, IDs, serialization and group state are the same as a fresh retained-only constructor. Erase transient fitted anchors and historical certificates. Deletion logs or allocator/storage side channels lie outside a mathematical state theorem unless included explicitly.
4. **The shape theorem is rediscovered classical geometry.** Cite Kantorovich/Wielandt and use the lemma as a supporting tool. The main result is the algorithm and its complete contract.
5. **An indexed fresh solver gets the same benefit.** Correct. The retained-only index can also accelerate construction of Q_seq(W,R). Report a conventional fresh rerun and an indexed-fresh solver with the same state access. Warm starts may improve the dynamic service, but cannot be assumed to create an information advantage. A bound against a forced scan is not a universal lower bound.
6. **The proof provider is the whole unsolved problem.** A callback returning a user-provided error bound is a conditional reference interface. A working transformer claim requires implemented finite-operator bounds, actual prefix dependency handling and UNKNOWN/replay for unsupported cases. A toy affine provider cannot substantiate a full-language-model implementation.
7. **Coverage is assumed, so speedup is tautological.** Tie the complete cost inequality to independently logged quantities: derivative/index bytes and preparation cost, parameter residual, margin quantiles, accepted stages, retained records avoided, duplicate work and fallback cost. A theorem characterizes a regime; experiments must establish that the regime occurs.
8. **Rounding margins vanish at scale.** Certifying all entries can be harder as model size increases. Report abstentions and coordinate/group refinement rather than excluding ties or difficult layers. Per-coordinate cells and selective exact replay should replace a single global minimum where possible.
9. **Real arithmetic is passed off as deployed exactness.** Keep the V/E distinction. Equality to a rational-statistic quantizer with fixed dyadic neural features does not imply equality to stock GPTQ's floating reductions and Cholesky. State the executable, schedules, numerical exceptions and serialization.
10. **Novelty is diluted by many reserves.** Main text should carry three contributions: original-target exact repair with changed ancestors; canonical response-state construction and storage/accuracy tradeoff; complete-ledger conditional work plus safe fallback. Put alternate quantizers, generic obstruction examples, and scheduling details in supporting sections.

## Recommended paper claim language

“We study deletion of calibration documents from a fixed-weight language-model quantization pipeline. We develop a certified repair procedure that reproduces a specified retained-only sequential quantizer, including cases where early quantized weights change. Canonical additive response summaries produce rigorously bounded calibration statistics; a scale-invariant decision test converts these bounds into exact codes, with selective replay and exact fallback when the summaries are insufficient. We characterize storage and work conditions for savings and evaluate those conditions on real calibration workloads.”

The final sentence is a prospective empirical obligation until experiments resume. At present it must read “we specify an evaluation of those conditions” in any report describing completed work.

Avoid “first,” “reviewer-proof,” “reliable speedup proved for LMs,” “all theory closed unconditionally,” and “certified forgetting of pretrained knowledge.” A complete retained-calibration rerun is the reference here; knowledge already contained in fixed W is outside the deletion target.

## Handoff to implementation/review

The 17-page existing report is internally careful about target/state/cost scope. The main needed literature correction is attribution of the shape constant and stronger comparison to polynomial sketches, especially Gunn (2026). The response-index extension should be reviewed against the table above before being called implemented. This file audits novelty and scope only; it is not an independent numerical validation of the forthcoming service.

## Storage improvement suggested by this audit

The exact affine-feature Gram index stores quadratic cross matrices, costing O(r^2 d^2) values. Its exact-Gram-query lower bound does not rule out a cheaper *certified approximate* Gram interface. A first-order Gram response keeps only the anchor Gram and r symmetric cross matrices, for O(r d^2) matrix storage. Let the normalized surrogate be Z(a)=Z0+DeltaZ(a). Then

    H_lin(a) = lambda I + Z0 Z0^T + Z0 DeltaZ^T + DeltaZ Z0^T,
    H_sur(a) = H_lin(a) + DeltaZ DeltaZ^T.

The omitted term is PSD and its norm is at most beta=||DeltaZ||_F^2. Beta is a quadratic form in a, recoverable from an r-by-r matrix of scalar tangent inner products. If feature remainder has normalized Frobenius bound epsilon and z bounds ||Z(a)||_F, the additional true-minus-surrogate uncertainty is bounded by delta=2z epsilon+epsilon^2. Consequently,

    H_lin-delta I <= H_true <= H_lin+(beta+delta) I.

If H_lin has a certified positive lower eigenvalue mu and delta<mu, this yields a valid asymmetric spectral enclosure relative to H_lin, with a_lower=1-delta/mu and b_upper=1+(beta+delta)/mu. Both beta and delta are second order locally when the feature response remainder is second order. The method therefore retains the quadratic local regime while dropping most matrix coefficients, at the price of a looser bound and an SPD check. The exact quadratic index remains a stronger, more expensive tier; replay remains the final tier.

This is a mathematical algorithm suggestion made during the audit. It is not implemented or empirically validated by this file. A claimed storage lower bound for *exact* Gram queries must not be used to call the larger index optimal for *exact quantized output*: a bounded approximate statistic can already certify that output. This distinction strengthens the proposed paper's storage/accuracy story.


## Closing update from implementation/review

The subsequent v3 work proved the linear-Gram suggestion, including a shifted PSD proposal, signed error endpoints and adaptive replay invariant; see theory_revision/linear_gram_response.txt. It was implemented in src/linear_response.py and connected to the generic service proposal interface. This updates the earlier audit-time "suggestion" status, without changing any empirical claim. The consolidated report is now 24 pages. The decoder's nontrivial finite-response provider and pretrained adapter remain absent.

## Revision 4 implementation update

The implementation gaps described above have changed.
The new complete service stores compact group moments and record bindings.
The certified decoder computes automatic jets, mixed curvature, and finite-error bounds within a fixed affine chart.
A local GPT-2 safetensors adapter is also implemented.
The consolidated report now has 27 pages.
These changes establish a concrete reference path for the stated method.
They do not establish useful pretrained coverage or practical speed.
Rational interval arithmetic and automatic differentiation remain established ingredients.
This update makes no new literature-priority claim.
