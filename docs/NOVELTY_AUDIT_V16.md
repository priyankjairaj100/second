# Revision 16 novelty audit

Audit date: 7 October 2026.
Scope: speculative verification for exact calibration-data deletion.
This is a targeted primary-source audit.
It does not prove that no matching prior work exists.
No experiment ran for this audit.

## Decision

The fixed-point formulation is established prior work.
Parallel adaptive rounding and dependency-depth convergence are also established prior work.
They must appear as background, with attribution.

The narrower research claim concerns exact retained-data repair under explicit finite arithmetic.
Its potential components are warm candidate verification, certified partial reuse, and complete deployment state.
Their combination still needs broader related-work review and convincing complete-model results.
A theorem alone does not establish that combination's novelty or practical value.

## Primary sources checked

### 1. QuIP

Jerry Chee, Yaohui Cai, Volodymyr Kuleshov, and Christopher De Sa.
*QuIP: 2-Bit Quantization of Large Language Models With Guarantees.*
NeurIPS 2023; initial arXiv submission: 25 July 2023.

- [Proceedings](https://proceedings.neurips.cc/paper_files/paper/2023/hash/0df38cd13520747e1e64e5b123a78ef8-Abstract-Conference.html)
- [Paper](https://papers.nips.cc/paper_files/paper/2023/file/0df38cd13520747e1e64e5b123a78ef8-Paper-Conference.pdf)
- [Author manuscript](https://arxiv.org/abs/2307.13304)

Section 3.1 writes adaptive rounding as a triangular feedback equation.
Its equation (2) already has the form Q=Round(W+(W-Q)U).
The triangular structure makes each coordinate depend on earlier coordinates.
Section 5.1 establishes equivalence between LDLQ and the compared GPTQ formulation.

Therefore, discovering a triangular fixed point is not a new contribution here.
The present token-space expression changes how the feedback is evaluated.
It does not create the fixed-point principle.

### 2. YAQA

Albert Tseng, Zhaofeng Sun, and Christopher De Sa.
*Model-Preserving Adaptive Rounding.*
ICML 2026, PMLR 306:122351–122370, 6–11 July 2026.
Initial arXiv submission: 29 May 2025.

- [Proceedings](https://proceedings.mlr.press/v306/tseng26b.html)
- [Proceedings PDF](https://raw.githubusercontent.com/mlresearch/v306/main/assets/tseng26b/tseng26b.pdf)
- [Author manuscript](https://arxiv.org/abs/2505.22988)
- [Author code](https://github.com/Cornell-RelaxML/yaqa-quantization)

Equation (3) presents LDLQ as a fixed-point update.
Section 3.1.1 and Lemma 3.2 bound iteration count through dependency depth.
Appendix A.6 gives simultaneous updates and equality-based stopping.
The method extends feedback through a Kronecker approximation of the full-model Hessian.

The checked source file also rounds blocks along reverse anti-diagonals.
Thus, fixed-point iteration, depth-based termination, and parallel blocks are not new claims for this project.
Our approximate verifier must still prove its finite-arithmetic decisions independently.
An equality test on approximate arrays does not prove an exact fixed point.

Checked commit: `f9508723251ad839f0162326569f17fe70486fcc`.
Commit date: 20 June 2025.
Checked file: `lib/algo/ldlq.py`, function `LDLQ_2hess`.

### 3. GPTQ-2D

Jiale Chen, Torsten Hoefler, and Dan Alistarh.
*GPTQ-2D: Cubic-Time Two-Sided Adaptive Rounding.*
arXiv version 1: 29 July 2026.

- [Paper record](https://arxiv.org/abs/2607.27042)
- [Versioned PDF](https://arxiv.org/pdf/2607.27042v1)

Theorem 1 proves invariance across valid dependency orders.
Theorem 2 proves agreement with the corresponding vectorized rounding trajectory.
The method handles two-sided feedback through separate factors.
Its maintained buffer reduces square-matrix work from quartic to cubic.
Section 4.3 groups updates into matrix products.

Consequently, exact trajectory preservation under parallel scheduling is established prior work.
A generic claim that parallel feedback preserves sequential codes would overstate our contribution.
Our current method uses one-sided token factors and finite rounding certificates.
GPTQ-2D does not supply that implementation merely by changing its scheduling.
Its real-arithmetic equivalence must not be mistaken for bitwise identity under arbitrary floating-point reassociation.

### 4. Parallel scans

Guy E. Blelloch.
*Prefix Sums and Their Applications.*
CMU-CS-90-190, November 1990.

- [Primary technical report page](https://www.cs.cmu.edu/~scandal/papers/CMU-CS-90-190.html)

The report develops parallel prefix operations and their applications.
The scan structure in our verifier uses this established algorithmic primitive.
The new work must concern its certified rounding application and resulting repair behavior.
The scan itself cannot be claimed as new.

### 5. Quantization after unlearning

Zhiwei Zhang and colleagues.
*Catastrophic Failure of LLM Unlearning via Quantization.*
ICLR 2025; initial arXiv submission: 21 October 2024.

- [Proceedings](https://proceedings.iclr.cc/paper_files/paper/2025/hash/ba79fb5c4fe70050752f20c90c5f07ca-Abstract-Conference.html)
- [Author manuscript](https://arxiv.org/abs/2410.16454)

This work studies knowledge recovery after quantizing a model that underwent unlearning.
Our declared target instead removes calibration records while retaining the original base weights.
These are different counterfactuals.
The broad combination of quantization and unlearning is therefore not an acceptable novelty claim.

## Claim map

| Proposed claim | Audit result | Required treatment |
|---|---|---|
| LDLQ has a triangular fixed point | Established in QuIP and YAQA | Cite as background |
| Exact simultaneous updates terminate by dependency depth | Established in YAQA | Attribute the principle |
| Valid parallel orders preserve the rounding trajectory | Established in GPTQ-2D | Attribute the principle |
| Parallel prefix sums reduce synchronization depth | Established scan method | Cite Blelloch |
| Old deployed codes provide a useful deletion candidate | Plausible application | Compare against warm model-only reconstruction |
| Directed token scans certify exact finite-grid decisions | Potential technical contribution | State arithmetic premises and compare existing verification methods |
| Certified prefixes support exact continuation | Potential integration contribution | Prove initialization, ties, and exceptional fallback |
| Repair reproduces retained codes and canonical factor state | Project guarantee | Check sequential requests and complete bytes |
| Repair is faster after preparation and state costs | Unproved empirical claim | Require complete matched measurements |
| Calibration deletion with fixed base weights is new | Unsettled priority claim | Extend the search before using first-work language |

This table distinguishes established ingredients from the project's proposed integration.
It does not assign novelty from missing search results.

## Immediate consequences for the theory text

Rename the fixed-point result as an attributed characterization.
Rename the d-step result as a specialized dependency-depth bound.
Keep the short proofs because they fix our indexing and exact target.
Do not present those proofs as the paper's main new theorems.

The main theorem should instead state the verifier's exact output guarantee.
It should include coefficient uncertainty, interval scans, finite grids, and midpoint ownership.
A second theorem can establish valid partial continuation and canonical state equality.
A third result must connect actual saved work to complete request costs.
That result needs quantitative content beyond an accounting identity.

Any numerical target must specify its grid limits and saturation behavior.
Integer-lattice results cannot silently justify a finite saturated grid.
Each referenced theorem also needs its stated sweep direction and factor convention.
These details matter when transferring an established result.

## Improvements worth testing

These proposals are deductions for this project.
They are not attributed as established results from the papers above.
No experiment currently supports their speed.

### A. Certify coordinates after an unresolved predecessor

Prefix continuation stops reuse at the first uncertain coordinate.
A stronger certificate can sometimes retain later coordinates.
The exact feedback coefficients are

\[
b_{ih}=u_i^\top z_h,\qquad h<i.
\]

Let C denote a proposed row and q its exact target row.
For each predecessor h, maintain a proved allowed code set A_h.
Initially, A_h can contain the entire finite grid.
A proved coordinate gives a singleton set.
Then

\[
v_i(q)=v_i(C)+\sum_{h<i}b_{ih}(C_h-q_h).
\tag{1}
\]

Construct an interval for the correction in equation (1).
A later coordinate passes when its entire interval lies inside one rounding cell.
That proof remains valid despite unresolved earlier coordinates.
A sequential fallback can skip such proved decisions.

The implementation can bound token accumulators without constructing the dense b matrix.
Use the existing directed scan on z_h(C_h-A_h).
Combine its enclosure with the certified coefficient error.
Only intersect an allowed set with codes justified by a universal enclosure.
Never remove a possible target code because a sampled proposal disagrees.

This method requires more verification work.
Permit it only under a prospective pass limit and a measured cost rule.
If its sets remain broad, the current prefix method can be faster.

### B. Stop speculation when its observed benefit is too small

Extra speculative passes cost a full scan over active rows.
They can cost more than the continuation they remove.
Use the previous pass's verified counts and elapsed cost to decide whether another pass is permitted.
Fix this decision rule before confirmation.
All fresh comparators must receive the same rule.
The rule controls cost only; exact fallback controls correctness.

A predetermined one-pass policy is a useful first control.
Compare it against the current two-pass policy on development records only.
Do not select the final policy on confirmation results.

### C. Separate warm-start benefit from deletion infrastructure

Model-only reconstruction can receive the deployed model codes.
Those codes already exist before the request.
Thus, warm initialization is not inherently exclusive to a persistent repair index.

Use four controls:

1. Sequential model-only reconstruction.
2. Speculative model-only reconstruction with nearest-grid codes.
3. Speculative model-only reconstruction with deployed codes.
4. Complete indexed repair with deployed codes and committed retained state.

The third control isolates the value of prior codes.
The fourth pays for the stronger state contract.
A gain over only the first control can reflect a shared solver improvement.
It does not establish a deletion-specific advantage.

### D. Keep feedback recomputation separate from feature transport

A warm candidate can reduce quantizer work while every retained feature is recomputed.
This can still improve measured complete cost.
It cannot satisfy the existing changed-ancestor avoidance gate.
Report both quantities without substituting one for the other.
If the scientific target changes, register the changed target prospectively.
Preserve the earlier gate and its negative result.

## Search scope and retrieval record

Queries covered both paper titles, LDLQ fixed points, parallel verification, warm starts, and calibration deletion.
The audit read the YAQA proceedings PDF and the GPTQ-2D version-1 PDF.
It also checked the author repository file listed above.
Search results alone did not establish algorithm details.

The browser service failed to retrieve the two arXiv pages directly.
Direct PDF retrieval succeeded through the execution environment.
The audit used those primary documents.
It did not depend on third-party paper summaries for the algorithm claims.

Retrieved PDF checksums:

| Source | SHA-256 |
|---|---|
| YAQA proceedings | `24b17c59ef85ec7610a4cf68ac86d56c35bf01b374757585a5a583100da14e54` |
| GPTQ-2D version 1 | `e13b836b89e5af04b26ff998f7f2d6c0b864f4531ae4f9db53b30c9c5b98ed0e` |

The PDFs remain external source documents.
This repository stores their citations and checksums, not redistributed paper copies.
