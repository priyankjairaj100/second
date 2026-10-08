# Primary-source novelty audit, revision 30

Date: 8 October 2026.
Scope: the current fixed nearest-anchor target and bounded certificates in `MANUSCRIPT_V30.md`.
This audit reads primary papers and publication records; it executes no experiment.
It does not change the manuscript or theory files.
Search absence never establishes priority.

## Decision

The defensible proposed contribution is **exact calibration-code recovery from source-local compressed enclosures, with bounded certification and charged replay**.
The target holds pretrained weights and calibration-independent ancestor features fixed.
Successful execution matches the specified retained-data quantizer, including its original normalization and tie rule.
This is conditional exactness for a deliberately specified quantizer.
It is neither general sequential GPTQ repair nor removal of knowledge from pretrained weights.

Fixed features, removable statistics, quantized unlearning, compressed unlearning archives, and executable certificates all have relevant predecessors.
None should be presented as the central invention.
The current combination remains a candidate contribution; this audit does not establish its priority or submission readiness.

One additional close overlap deserves immediate inclusion: MEDU studies unlearning from lossy compressed stored updates.
The main remaining retrieval blocker is ExecCert's full text.
Its existence and abstract are verifiable through the indexed primary arXiv record.
Its theorem-level overlap remains unresolved.

## Closest verified primary sources

### 1. Frozen structure and exact deletion: QSS

Tavory et al., *Exact Unlearning via Quantized Sufficient Statistics*, arXiv:2610.07197v1, 5 October 2026.
[Primary record](https://arxiv.org/abs/2610.07197v1) · [Accessible full text](https://arxiv.org/html/2610.07197v1).

Sections 2–3 separate frozen schema from additive prediction corrections.
Proposition 1 states exact instance deletion for QSS-E when the schema excludes deletable examples.
Remark 2 separates label deletion from instance deletion.
Schema deletions require rebuilding.
Appendix D.2 explicitly compares maintained ridge statistics.

This directly overlaps the structural reason our fixed features permit deletion.
Our candidate distinction concerns uncertain feature enclosures and exact discrete weight codes, rather than QSS's correction predictor.
QSS's quantization organizes feature regions; our quantizer produces deployed weight codes.
Do not claim the first frozen-schema exact deletion method or the first quantization-enabled exact unlearning architecture.

### 2. Executed artifacts and evolving references: ExecCert

Zhao et al., *From Mathematical to Executable Certificates for Machine Unlearning*, arXiv:2610.02268, 1 October 2026.
[Primary record](https://arxiv.org/abs/2610.02268) · [PDF endpoint](https://arxiv.org/pdf/2610.02268).

The indexed primary abstract describes release verification for actual finite-precision candidates.
It covers native certificate closure and fidelity to current retained-set retraining.
It also describes incremental certification for frozen representations with mutable ridge heads.
These claims overlap our artifact-aware verification and maintained evidence.

Our proposed distinction is universal constancy of discrete calibration outputs across compressed feature boxes.
This is a target distinction, not a verified separation from every ExecCert theorem.
Direct abstract, versioned HTML, PDF, export-arXiv, and Hugging Face retrieval attempts failed during this audit.
No third-party summary substitutes for the missing theorem comparison.
Do not claim the first executable unlearning certificate, incremental certificate, or retained-reference release check.

### 3. Lossy unlearning archives: MEDU

Lang, Helvitz, and Shlezinger, *Memory-Efficient Distributed Unlearning*.
The arXiv record uses “Helvitz”; the publisher-associated record uses “Helvits”.
[Accessible primary record](https://arxiv.org/abs/2505.03388) · [Publisher](https://ieeexplore.ieee.org/document/11389783/) · [DOI](https://doi.org/10.1109/ACCESS.2026.3663428).
The publisher records IEEE Access 14, pages 24361–24378, published 10 February 2026.

Its abstract describes sparsification, thresholding, and random lattice coding of stored distributed updates.
It bounds deviation between the reconstructed unlearned model and retained-data retraining.
The earlier *Distributed Unlearning with Lossy Compression* [author repository](https://github.com/alonhelvits/FedUL_Quant) confirms this research line.

Thus, lossy storage for future unlearning and its storage–fidelity tradeoff are established topics.
Our contract instead requires exactly identical discrete calibration codes whenever certification succeeds.
It explicitly refuses or replays when its universal certificate cannot establish that equality.
Only abstract-level guarantees were needed and verified here; detailed MEDU constants were not audited.

### 4. Analytic deletion and information requirements

Quan, Wu, and Montana, *Exact Federated Continual Unlearning for Ridge Heads on Frozen Foundation Models*, arXiv:2603.12977v3.
[Accessible full text](https://arxiv.org/html/2603.12977v3).

Theorem 6.1 gives retained ridge-solution equality from exact sufficient statistics.
Section 6.2 covers order and partition invariance.
Lemma 2 shows first-order summaries cannot determine every exact second-order update.
The paper explicitly discusses floating-point drift and reports small nonzero numerical discrepancies.

This overlaps frozen-feature maintenance, deletion-history invariance, and the general necessity of auxiliary information.
Our response-counting result must retain its narrower quantizer-specific access model and finite archive statement.
Do not present “deployed weights alone can be insufficient” as a newly discovered general principle.
Maintained exact pooled-Gram reconstruction remains a relevant same-target model baseline under matched data access.

Cao and Yang's *Towards Making Systems Forget with Machine Unlearning* already develops removable transformed summations.
[Accessible author paper, IEEE S&P 2015](https://www.cs.columbia.edu/~junfeng/papers/unlearning-sp15.pdf).
Source-local accumulation and subtraction should cite this foundation.

### 5. Calibration architecture and rounding geometry

Hubara et al., *Accurate Post Training Quantization With Small Calibration Sets*, ICML 2021.
[Accessible paper](https://proceedings.mlr.press/v139/hubara21a/hubara21a.pdf).
Equations 2–3 distinguish independent layer calibration from calibration using previously quantized inputs.
Our nearest-grid anchor is a particular source-independent feature design; independence itself is established.

Chen et al., *The Geometry of LLM Quantization: GPTQ as Babai's Nearest Plane Algorithm*.
[Accessible versioned paper](https://arxiv.org/html/2507.18553v4).
Theorem 4 establishes the GPTQ/Babai correspondence after aligning coordinate order.
Theorem 6 permits shared orthogonal structure across output channels under a common permutation.
Theorem 5's stated error bound assumes no clipping.
Row separability, shared metric work, and triangular rounding geometry therefore are supporting infrastructure.
Their results do not automatically establish our finite-grid box certificate, saturation behavior, or lower-tie convention.

### 6. Quantization-based deletion certificates

Zhang et al., *Prompt Certified Machine Unlearning with Randomized Gradient Smoothing and Quantization*, NeurIPS 2022.
[Primary proceedings](https://papers.neurips.cc/paper_files/paper/2022/hash/5771d9f214b75be6ff20f63bba315644-Abstract-Conference.html).
PCMU derives deletion budgets through randomized smoothing and gradient quantization.
Quantization stability enabling deletion certificates is therefore established.
Our deterministic enclosure certificate applies to a different output and uncertainty set.

Muresanu et al., *Fast Exact Unlearning for In-Context Learning Data for LLMs*, ICML 2025.
[Accessible proceedings record](https://proceedings.mlr.press/v267/muresanu25a.html).
It changes adaptation to in-context learning with quantized clustering, enabling efficient exact deletion.
Changing the learning architecture to make unlearning easier is itself established practice.

Exact-Fun, ICDM 2023, also develops quantized federated learning for exact unlearning.
The [author's indexed PDF](https://zuobinxiong.github.io/assets/pdf/ExactFedUnlearning.pdf) exposes its abstract through primary search results.
Direct PDF retrieval still failed; detailed theorem claims remain excluded.

### 7. Verified numerics and alternatives to calibration

Rump, *Verification Methods for Dense and Sparse Systems of Equations*, 1994.
[Accessible author chapter](https://www.tuhh.de/ti3/paper/rump/Ru94.pdf).
Verified residuals, interval linear systems, and inverse-defect checks have established numerical foundations.
The push-through identity and elementary ridge spectral bound are mathematical tools, without priority claims here.
Requested-coordinate scheduling must demonstrate additional useful work reduction within our certificate, beyond generic selective refinement.

Muller et al., *SINQ: Sinkhorn-Normalized Quantization for Calibration-Free Low-Precision LLM Weights*, ICML 2026.
[Accessible proceedings record](https://proceedings.mlr.press/v306/muller26a.html).
SINQ uses weight-derived row/column scaling without requiring calibration samples.
It supplies an application-level alternative that avoids this calibration-deletion obligation altogether.
It is a quality/storage alternative, not a same-target exact-repair comparator.

Williams and Aletras, *On the Impact of Calibration Data in Post-training Quantization and Pruning*, ACL 2024.
[Accessible primary record](https://aclanthology.org/2024.acl-long.544/).
Its empirical study already establishes sensitivity to calibration choice.
Our paper cannot claim discovery of calibration dependence.

## Consequences for claims and experiments

| Proposed claim | Audit judgment |
| --- | --- |
| Fixed features make exact deletion possible. | Established structural idea; cite the sources above. |
| Lossy stored evidence can support unlearning. | Established broad topic; MEDU is directly relevant. |
| Successful universal box certification recovers every exact calibration code. | Candidate calibration-specific contribution; keep all containment, arithmetic, and refusal premises. |
| Sparse requested checks and feature-space verification reduce work. | Implemented mechanisms; prove their stated costs and measure against optimized compatible controls. |
| The information theorem establishes a practical universal storage lower bound. | Unsupported. Its finite access model, shrinking margins, and response family must remain explicit. |
| Exact successor-state equality proves deletion across all external archives. | Unsupported. Equality concerns only the declared canonical state and fixed preparation family. |
| Faster repair is guaranteed by bounded structural work. | Unsupported. Admission bounds schedules and arrays, not time, acceptance, or process memory. |

The closest direct controls remain optimized cold reconstruction, equally indexed reconstruction, exact factors, and strong lossless factor storage.
Exact pooled-Gram maintenance also qualifies under a declared sufficient-information and deleted-record access contract.
Do not require our descriptor format from a valid model-only competitor.
Charge preparation, conversion, accesses, certification, replay, and serialization in complete and lifetime comparisons.
Shared ordered neural execution is a fairness improvement, not a new unlearning theorem.

The original sequential-target losses remain relevant evidence about scope.
Preserve them alongside current fixed-target results.
This audit supplies no new empirical claims and does not override dated measurement cutoffs.

## Search scope and remaining closure

Queries covered calibration-data deletion, quantization/unlearning certificates, lossy unlearning archives, fixed-feature ridge deletion, and named neighboring papers.
Sources were restricted to arXiv, conference proceedings, publisher records, and author-hosted papers or repositories.
Nonprimary search results were discovery leads only.
The Hugging Face paper endpoints were also attempted for the two named October papers; they returned access failures.

Before submission, obtain ExecCert's primary full text and compare its exact premises, release target, evolving state, and incremental costs.
Recover Exact-Fun's full primary paper before making a theorem-level separation from it.
Use MEDU's final publisher bibliography rather than citing its withdrawn submission as an accepted conference paper.
Do not claim that an inaccessible paper lacks an overlapping result.
The literature audit can bound claims now; it cannot conclusively close those unavailable theorem comparisons.
