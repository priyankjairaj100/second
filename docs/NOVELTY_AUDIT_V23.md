# Revision 23 novelty audit: fixed-feature calibration deletion

Date: 8 October 2026.
Scope: the revision 21 target and revision 22 factor representation.
This audit read primary papers, official proceedings, and author code.
It ran no model and changed no numerical implementation.
Search absence does not establish priority.

## Decision

The fixed-feature redesign solves a genuine dependency problem.
Its present core ingredients are established methods.
Independent layer calibration, cached activations, additive sufficient statistics, and quantization-based deletion stability all have close precedents.
Choosing nearest-grid anchor features does not, by itself, establish a strong central contribution.

The current implementation provides an unusually explicit finite target and canonical deletion-state contract.
That is valuable infrastructure, but it does not yet establish a competitive ACL methods contribution.
Thirty quality predictions cannot close that gap.

The most promising extension is **compressed calibration state with certified exact repair**.
It must preserve the existing fixed-feature target rather than silently quantizing its input features.
A useful storage–rounding-margin–fallback result would distinguish this extension from ordinary caching.
This is a prospective direction, not a completed theorem, implementation, or novelty claim.

The safest current paper position is narrower:

> We study exact calibration-data removal under explicit finite quantization targets.
> We identify a concrete obstruction to anchor-centered reuse and implement a separate, deletion-stable calibration architecture.
> We evaluate its exactness, quality, storage, and complete request costs against matched reconstruction.

The last sentence describes the required study.
Only small development evidence currently supports it.
The paper still needs either a stronger algorithm or a substantial empirical finding.

## 1. Current target and its actual distinction

Let A be a calibration-independent nearest-grid model.
For record r and stage i, define Z_i(r) from A's fixed ancestor prefix.
The repaired target is

\[
Q_i(R)=\operatorname{DyadicQuantize}_i
\left(W_i,[Z_i(r)]_{r\in R}\right).
\]

Every surviving Z_i(r) is unchanged by another record's deletion.
That fact makes cached factors valid without transformer transport.
It also places the target inside established source-local sufficient-statistic reasoning.

The nearest-grid anchor differs from using a full-precision teacher.
The fixed anchor also differs from the evolving quantized inputs used by sequential GPTQ.
Neither difference alone proves novelty or superior quality.
The value must appear in the quality, retained-state size, and complete maintenance costs together.

The calibration source is the deletion target.
The pretrained base weights remain fixed.
This claim does not remove content learned earlier during pretraining.

## 2. Primary-source map

### S1. Parallel and sequential calibration already coexist in AdaQuant

Itay Hubara, Yury Nahshan, Yair Hanani, Ron Banner, and Daniel Soudry.
*Accurate Post Training Quantization With Small Calibration Sets.* ICML 2021.

- [Proceedings](https://proceedings.mlr.press/v139/hubara21a.html)
- [Paper](https://proceedings.mlr.press/v139/hubara21a/hubara21a.pdf)

Section 3.1, Equation 2, calibrates layers using fixed input features.
The authors explicitly permit parallel optimization across layers.
Equation 3 instead uses inputs produced by quantized predecessors.
The paper therefore already distinguishes independent calibration from sequential correction.

Its optimizer and full-precision features differ from our exact dyadic solver and nearest-grid anchor.
Those differences limit the collision to the architectural principle.
They do not make independent calibration a new principle.

### S2. Fixed teacher outputs do not imply independent student features

Markus Nagel, Rana Ali Amjad, Mart van Baalen, Christos Louizos, and Tijmen Blankevoort.
*Up or Down? Adaptive Rounding for Post-Training Quantization.* ICML 2020.

- [Paper](https://proceedings.mlr.press/v119/nagel20a/nagel20a.pdf)

Section 3.3, Equation 25, reconstructs full-precision outputs using inputs from quantized predecessors.
Thus, asymmetric teacher matching can still retain sequential feature dependence.
Calling our method teacher-guided would obscure this distinction.

Yuhang Li, Ruokai Yin, Donghyun Lee, Shiting Xiao, and Priyadarshini Panda.
*GPTAQ: Efficient Finetuning-Free Quantization for Asymmetric Calibration.* ICML 2025.

- [Proceedings](https://proceedings.mlr.press/v267/li25dn.html)
- [Author manuscript](https://arxiv.org/pdf/2504.02692)
- [Proceedings PDF](https://raw.githubusercontent.com/mlresearch/v267/main/assets/li25dn/li25dn.pdf)

Earlier records use the name GPTQv2.
The checked manuscript is version 3, dated 13 May 2025.
Section 4, Equation 4, compares quantized-input outputs with fixed full-precision teacher outputs.
The student inputs still depend on preceding quantized layers.
GPTAQ consequently motivates a meaningful quality comparator.
It does not directly supply our source-local feature law.

### S3. GPTQ really propagates calibrated layer outputs

Elias Frantar and colleagues.
Official GPTQ implementation, function `opt_sequential` in `opt.py`.

- [Author code](https://github.com/IST-DASLab/gptq/blob/main/opt.py)

The checked code recalculates outputs after quantizing each layer.
It then exchanges the input and output buffers for the next layer.
This directly supports the sequential dependency underlying our original target.
The source branch is mutable; this audit does not claim a pinned code reproduction.
Revision 23's mathematical target remains repository-defined rather than identical to arbitrary GPTQ releases.

### S4. Source-local summation deletion is foundational prior work

Yinzhi Cao and Junfeng Yang.
*Towards Making Systems Forget with Machine Unlearning.* IEEE S&P 2015.

- [Author page](https://www.cs.columbia.edu/~junfeng/papers/unlearning/)
- [Author PDF](https://www.yinzhicao.org/unlearning/UnlearningOakland15.pdf)
- [DOI](https://doi.org/10.1109/SP.2015.35)

Figure 1 and Section IV formulate learning through sums of transformed individual records.
Deletion subtracts affected contributions before recomputing the output.
The framework includes feature extraction and downstream modeling.
Their covariance-like recommendation example makes the overlap especially direct.

Our exact arithmetic and discrete quantizer require additional implementation care.
However, subtracting source-local feature Grams is an application of this established framework.
The present minimal backend retains exact factors rather than implementing a new sufficient-statistic theorem.

### S5. Quantization stability already supports unlearning certificates

Zijie Zhang, Yang Zhou, Xin Zhao, Tianshi Che, and Lingjuan Lyu.
*Prompt Certified Machine Unlearning with Randomized Gradient Smoothing and Quantization.* NeurIPS 2022.

- [Proceedings](https://papers.neurips.cc/paper_files/paper/2022/hash/5771d9f214b75be6ff20f63bba315644-Abstract-Conference.html)
- [Paper](https://openreview.net/pdf?id=ue4gP8ZKiWb)

The paper derives deletion budgets through randomized smoothing and gradient quantization.
Its target and certificate differ from deterministic calibration-data requantization.
It nevertheless precludes claiming that quantization stability first enables deletion certification here.

Zuobin Xiong, Wei Li, Yingshu Li, and Zhipeng Cai.
*Exact-Fun: An Exact and Efficient Federated Unlearning Approach.* ICDM 2023.

- [Author manuscript](https://zuobinxiong.github.io/assets/pdf/ExactFedUnlearning.pdf)
- [DOI](https://doi.org/10.1109/ICDM58522.2023.00188)

Its quantized federated learning design uses unchanged quantized models to avoid retraining when stability holds.
The author manuscript explicitly distinguishes stable cases from necessary retraining.
Our adaptive rounding, calibration counterfactual, and finite exactness requirements are more specific.
Generic unchanged-code reuse is already established.

### S6. Calibration choice already has demonstrated NLP consequences

Miles Williams and Nikolaos Aletras.
*On the Impact of Calibration Data in Post-training Quantization and Pruning.* ACL 2024.

- [Proceedings](https://aclanthology.org/2024.acl-long.544/)
- [Paper](https://aclanthology.org/2024.acl-long.544.pdf)

This study reports downstream variation across calibration data, models, methods, and tasks.
Calibration dependence itself is therefore not a new empirical discovery.
Our experiments must isolate deletion repair and architecture changes from ordinary calibration sampling effects.

### S7. Quantization after unlearning is a different established counterfactual

Zhiwei Zhang and colleagues.
*Catastrophic Failure of LLM Unlearning via Quantization.* ICLR 2025.

- [Proceedings](https://proceedings.iclr.cc/paper_files/paper/2025/hash/ba79fb5c4fe70050752f20c90c5f07ca-Abstract-Conference.html)
- [Paper](https://openreview.net/pdf?id=lHSeDYamnz)

The paper investigates quantization of models that already underwent unlearning.
Our base model remains fixed while calibration records change.
The distinction belongs in the opening problem statement.
It cannot justify claiming the broad combination of quantization and unlearning.

## 3. Claim-by-claim disposition

| Proposed claim | Current assessment | Required treatment |
|---|---|---|
| Independent features remove cross-layer recalibration dependencies | Established architectural principle; direct consequence of this target | Attribute AdaQuant; state our exact law |
| Full-precision teacher outputs make calibration deletion local | False in general | Distinguish teacher targets from student inputs |
| Cached retained features avoid repeated neural execution | Valid engineering consequence | Charge cache construction, validation, reads, and storage |
| Additive Grams permit exact source subtraction | Established sufficient-statistic method | Cite Cao–Yang |
| Quantization margins can certify unchanged models | Established broad approach | Compare PCMU and Exact-Fun; narrow our certificate claim |
| Triangular feedback and fixed-point iteration are new | Already rejected by revision 16 | Retain QuIP, YAQA, and GPTQ-2D attribution |
| Nearest-grid anchors yield a better deletion–quality tradeoff | Plausible hypothesis | Compare nearest, full-precision, and sequential features |
| Complete canonical state is independent of deletion order | Proven under current trusted deterministic preparation | Present as the service contract, not a priority assertion |
| Current repair beats any equally indexed reconstruction | Unsupported and conceptually misplaced | The matched implementation can run the same algorithm |
| The 51.3 percent state reduction proves novel compression | False | It removes unnecessary summaries from our earlier representation |
| Calibration deletion with fixed base weights is unstudied | Not established | Avoid first-work language |
| Exact repair from certified compressed factors gives practical savings | Stronger prospective contribution | Prove and implement before claiming results |

The present study has an exactness contract and working infrastructure.
It does not yet have a demonstrated, distinctive algorithmic advantage.

## 4. Strongest realistic extension: compressed factors with exact output

This proposal preserves the revision 21 model target.
It changes stored evidence, not the features defining that target.
The existing exact-factor backend remains its mandatory baseline and fallback.

For source r, let Z_r be its exact finite anchor feature matrix.
Store a deterministic compressed center C_r and a certified enclosure of Z_r.
For example, require

\[
\|Z_r-C_r\|_F\le e_r.
\]

Choose the codec independently of the deletable corpus.
Alternatively, let every leaf's encoding depend only on that leaf and fixed public settings.
A codec chosen from the original aggregate corpus can retain deleted-source influence in the state.
It can also break canonical equality with retained-only preparation.

Using the fixed normalization M_0, construct

\[
\widetilde H_R=\lambda I+M_0^{-1}\sum_{r\in R}C_r^\top C_r,
\]

and the valid bound

\[
\|H_R-\widetilde H_R\|_2\le
\delta_R=
M_0^{-1}\sum_{r\in R}
\left(2\|C_r\|_F e_r+e_r^2\right).
\tag{1}
\]

Equation 1 follows by expanding each Gram difference and applying norm inequalities.
It is established matrix algebra, already used in the project's earlier theory.
Its novelty cannot be claimed separately.
All stored norms and arithmetic bounds must round outward under the declared numerical contract.

The algorithm would then proceed as follows:

1. Remove deleted source leaves and rebuild the canonical retained index.
2. Propose quantized codes using compressed centers or existing deployed codes.
3. Certify every proposed code against the exact-factor enclosure.
4. Recompute unresolved retained features through the fixed anchor when certification abstains.
5. Return exact target codes and the prescribed canonical compressed state.

Prior codes must also reach the warm reconstruction comparator.
Refinement scratch must not create history-dependent committed leaves.
Original raw retained records remain necessary whenever compressed evidence cannot resolve a decision.
Their availability and storage must be charged explicitly.

### The required theorem is quantitative

An interval certificate alone is insufficient.
The result should connect stored precision, feature energy, conditioning, and adaptive-rounding margins.
It should bound both acceptance and the remaining exact work.

For illustration, suppose a proved local decision bound has sensitivity K_i.
Let m_i be its positive distance from the nearest relevant rounding boundary.
An inductive certificate can accept when K_i delta_R is smaller than m_i.
Each step assumes the earlier decisions are already certified.
The actual derivation must handle finite grids, saturation, ties, and uncertain feedback coefficients.
It cannot use an unproved Lipschitz constant for the complete discontinuous quantizer.

If precision p gives delta_R at most D times 2 to the power minus p, acceptance follows conditionally.
One sufficient requirement is p greater than log2(D max_i K_i / min_i m_i).
This is only an illustrative implication of the stated bounds.
No uniform storage reduction follows when a required margin approaches zero.
An exact midpoint may require directed information or exact fallback.

The useful theorem would make these constants computable and substantially tighter than a full scalar box traversal.
The useful experiment would show state savings with a high exact acceptance rate and lower complete lifetime cost.
Neither result currently exists in this repository.

### Why this escapes the measured centered-box obstruction

Revision 20 bounded changed-prefix features around different anchor features.
Its witness showed that both endpoints required different quantizer outputs.
Here the target factors themselves are fixed source-local anchor features.
A compressed enclosure only needs to contain those exact factors.
It need not contain the original sequential target's changed-prefix features.
The earlier endpoint witness therefore does not directly reject this new certificate.
Certification can still fail near rounding boundaries or because the enclosure is too loose.

### Why this might still fail

Exact factors may already fit in memory and load cheaply.
Certificate scans may cost more than the shared native point solver.
Gram storage scales quadratically with feature width.
Small token counts may favor exact token factors over any dense moment representation.
Fallback may erase storage and latency advantages.
Generic certified compression is not itself new; the contribution needs this exact deletion-specific tradeoff.

Do not launch a large campaign before a bounded stage screen resolves these risks.
Do not present the proposal as a rescued positive result.

## 5. Minimum reviewer-facing comparisons

The existing fixed-nearest target needs the following architectural controls:

- Sequential calibration using the shared optimized solver.
- Fixed full-precision features using the same solver, grids, ridge, and normalization.
- Fixed nearest-grid features using exact cached factors.
- Nearest-grid rounding without calibration.
- The strongest compatible warm and equally indexed reconstruction controls.

A compressed-state extension additionally needs exact-factor, lossless-codec, and precision-tier controls.
Compare complete transactions, including serialization and fallback.
Do not compare compressed repair against a deliberately slower exact solver.

Report quality as differences between target laws.
Report exactness as equality between repair and reconstruction within one law.
These are different comparisons.
Cross-target quality should include downstream NLP tasks and realistic contexts once small pilots pass.

The paper should retain the centered-box counterexample as a design boundary.
It explains why the new architecture exists.
Removing this evidence would weaken the justification and conceal the redesign's cost.

## 6. Search coverage and limitations

Queries covered fixed-feature PTQ, parallel layer calibration, teacher activations, calibration-corpus deletion, and cached-statistic unlearning.
Additional queries covered quantization-based certified deletion and compressed calibration state.
The audit inspected AdaQuant's Equations 2–3, AdaRound's Equation 25, GPTAQ's Equation 4, and Cao–Yang's summation framework.
It checked official GPTQ's buffer update and post-quantization forward pass.

The Exact-Fun author manuscript was available through indexed primary-source text.
Direct browser opening failed on a later attempt.
PCMU's proceedings and primary manuscript records supplied its stated certificate scope.
No unsupported implementation equivalence is inferred from either source.

Searches did not identify a directly matching treatment of the narrow revision 21 deletion target.
That observation does not establish novelty or completeness.
Update this audit near submission and inspect any newly found close methods before writing priority claims.
