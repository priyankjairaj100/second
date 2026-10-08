# Revision 29: novelty, comparison, and scaling audit

Date: 8 October 2026.
Scope: the implemented revision 28 compressed service and its fixed-feature target.
This audit includes primary sources available through this date.
It ran no empirical experiment and changed no numerical source.
Search absence does not establish novelty.

## 1. Decision

Continue the research, but do not claim an ACL-ready methods contribution.
The strongest position concerns exact calibration removal from compressed evidence under a declared finite target.
It does not concern forgetting pretraining knowledge or accelerating ordinary sequential GPTQ repair.

The source-local compression service now exists.
Its universal certificates, sparse row retries, and exact fallback form a concrete algorithm.
However, current evidence establishes neither superior complete latency nor a favorable general storage–latency tradeoff.
The complete compressed service saves 5.30% against the exact-factor state on one tiny request.
Its one complete timing approximately matches cold reconstruction.
The exact-factor service remains faster on that request.

Two newly located October papers increase the overlap with broad proposed claims.
QSS studies exact deletion with a frozen schema and additive mutable statistics.
ExecCert studies certificates for executed artifacts and current retained-set references.
Neither inspected abstract describes our exact calibration-code target from compressed feature enclosures.
That distinction is a research opportunity, not proof of priority.

Realistic token scaling is a blocking algorithm issue.
Sparse row retries reduce repeated row verification.
They do not remove the shared quadratic token-space matrices.

## 2. Closest primary sources

### S1. QSS: exact deletion with frozen structure

Ami Tavory, Shripad Gade, Tal Sarig, Noam Touitou, and Ido Guy.
*Exact Unlearning via Quantized Sufficient Statistics.*
Submitted 5 October 2026; the arXiv record reports acceptance at NeurIPS 2026.

- [Versioned record](https://arxiv.org/abs/2610.07197v1)
- [Primary full text](https://arxiv.org/html/2610.07197v1)
- [Author implementation](https://github.com/atavory/rqu)

Sections 2–3 separate frozen schema from additive content.
They distinguish label deletion from complete example deletion.
Their predictor uses quantized regions and local correction statistics.
Our calibrated weights instead follow a declared adaptive rounding recurrence.
Their exact subtraction principle overlaps directly with our fixed-feature architecture.
Our potential distinction concerns uncertain stored evidence and universal preservation of discrete calibration outputs.
Do not claim that frozen structure plus exact additive deletion is new.

### S2. ExecCert: executable certificates and retained-set references

Ziyu Zhao, Xinyu Wang, Xiaowen Chang, and Yixuan He.
*From Mathematical to Executable Certificates for Machine Unlearning.*
The indexed primary record reports submission on 1 October 2026.

- [Primary record](https://arxiv.org/abs/2610.02268)
- [Primary PDF location](https://arxiv.org/pdf/2610.02268)

The primary abstract describes release certification for finite-precision artifacts.
It includes retained-set reference verification and incremental evidence for frozen representations with mutable ridge heads.
Our distinction is exact discrete output equality across every factor inside a compressed enclosure.
Do not claim the first executable unlearning certificate or the first maintained numerical evidence.
This audit retrieved the indexed primary abstract.
Direct abstract, HTML, and PDF opening repeatedly failed.
Detailed theorem comparisons remain a required pre-submission check.
Third-party summaries do not support theorem-level claims here.

### S3. AdaQuant: fixed versus sequential calibration

Itay Hubara and colleagues.
*Accurate Post Training Quantization With Small Calibration Sets.* ICML 2021.

- [Proceedings](https://proceedings.mlr.press/v139/hubara21a.html)
- [Primary paper](https://proceedings.mlr.press/v139/hubara21a/hubara21a.pdf)

Revision 23 checked its fixed-feature and sequential objectives in Equations 2–3.
This audit reopened its proceedings record.
Independent calibration features therefore cannot supply our central novelty claim.
Our nearest-grid anchor differs from its features and optimizer.
That difference requires quality and maintenance evidence.

### S4. Cao–Yang: source-local sufficient statistics

Yinzhi Cao and Junfeng Yang.
*Towards Making Systems Forget with Machine Unlearning.* IEEE S&P 2015.

- [Author paper](https://www.cs.columbia.edu/~junfeng/papers/unlearning-sp15.pdf)

Its summation framework makes transformed source contributions removable.
Our fixed-factor architecture applies that established principle.
Canonical retained descriptors add a precise service contract.
They do not create a new additive deletion principle.

### S5. PCMU and prior quantization-based unlearning

Zijie Zhang and colleagues.
*Prompt Certified Machine Unlearning with Randomized Gradient Smoothing and Quantization.* NeurIPS 2022.

- [Primary proceedings](https://papers.neurips.cc/paper_files/paper/2022/hash/5771d9f214b75be6ff20f63bba315644-Abstract-Conference.html)

PCMU connects randomized smoothing, quantized gradients, and certified deletion budgets.
It differs from deterministic calibration-code equality under uncertain retained factors.
Generic claims about quantization enabling deletion certificates are already occupied.
Revision 23 also identified Exact-Fun, ICDM 2023.
Its previously cited author PDF returned HTTP 404 during this audit.
Recover a working primary copy before adding detailed Exact-Fun comparisons to the manuscript.

### S6. GPTQ geometry and independent output rows

Jiale Chen and colleagues.
*The Geometry of LLM Quantization: GPTQ as Babai’s Nearest Plane Algorithm.* ICLR 2026.

- [Versioned primary paper](https://arxiv.org/html/2507.18553v4)
- [Primary record](https://arxiv.org/abs/2507.18553)

The paper connects reverse-order GPTQ with Babai's nearest-plane algorithm.
Its formulation shares metric coefficients across separate output vectors.
Thus, output-row separability and triangular rounding geometry are established structures.
Our sparse certificate scheduler uses this structure to avoid repeating already certified complete rows.
That scheduler needs a precise cost result and measured benefits beyond obvious filtering.
Section E.2 uses 256 calibration sequences with 2,048 tokens each.
This workload also exposes the gap between realistic token counts and our sixteen-token retained pilot.

### S7. Verified linear algebra

Siegfried M. Rump.
*Verification Methods for Dense and Sparse Systems of Equations.* 1994.

- [Author-hosted primary chapter](https://www.tuhh.de/ti3/paper/rump/Ru94.pdf)
- [Author research index](https://www.tuhh.de/ti3/rump/Research_Rump/topics.shtml)

Verified inverse defects, residual enclosures, and interval linear systems have established numerical foundations.
Our contraction and supersolution checks belong within this literature.
Do not present their general numerical principle as new.
The possible contribution is their efficient use inside complete adaptive rounding certificates.

### S8. Lossless floating-point compression

- [FPC author source and paper links](https://userweb.cs.txstate.edu/~burtscher/research/FPC/)
- [ALP primary institutional record, SIGMOD 2024](https://ir.cwi.nl/pub/33334/)
- [ALP author implementation](https://github.com/cwida/ALP)
- [Zstandard reference implementation](https://github.com/facebook/zstd)

FPC preserves binary64 streams exactly.
ALP provides vectorized lossless floating-point compression, including a route for nondecimal values.
Zstandard supplies a mature general lossless comparator.
These methods remove uncertainty before the shared exact solver.
They require no universal enclosure certificate after successful exact decoding.
Our codec must beat their complete storage–latency tradeoff on actual factors.
The old zlib-only storage audit cannot establish that result.

### S9. Recent activation compression and runtime certificates

Yipin Guo and Siddharth Joshi.
*SplitZip: Ultra Fast Lossless KV Compression for Disaggregated LLM Serving.* 2026.

- [Primary record](https://arxiv.org/abs/2605.01708)

SplitZip preserves activation words through exponent coding and sparse escapes.
Its declared target is KV transfer, not binary64 calibration factors or deletion.
It nevertheless strengthens the need for a relevant lossless activation comparator.
Its hardware throughput cannot transfer directly to our CPU implementation.

*WitCert: Sound Runtime Risk Observability and Gating for KV-Cache Quantization.* 2026.

- [Primary record](https://arxiv.org/abs/2607.28699)

Its abstract describes runtime bounds for attention distortion after KV compression.
Our contract requires exact quantizer codes, rather than bounded attention distortion.
Avoid broad claims that compression receives its first runtime certificate here.

### S10. Quality and calibration dependence

- [Williams–Aletras, ACL 2024](https://aclanthology.org/2024.acl-long.544/)
- [GPTAQ, ICML 2025](https://proceedings.mlr.press/v267/li25dn.html)
- [Quantization failure after unlearning, ICLR 2025](https://openreview.net/pdf?id=lHSeDYamnz)
- [QUAIL, 2026 primary record](https://arxiv.org/abs/2601.15538)
- [DurableUn, 2026 primary record](https://arxiv.org/abs/2605.02196)

Calibration dependence and quantization-sensitive forgetting already have dedicated studies.
GPTAQ supplies a relevant quality control for accumulated calibration error.
Its matched teacher outputs do not imply source-local student features.
The other unlearning papers change learned knowledge before or during quantization.
Our base weights remain fixed while calibration membership changes.
Therefore, their forgetting scores are not direct substitutes for our retained-reference equality test.

## 3. Three defensible contribution packages

These packages distinguish implemented results from prospective extensions.
None receives a priority claim from search absence.

### C1. Exact output recovery from compressed calibration evidence

State the finite target, source-local encoder, trusted containment premise, and bounded failure behavior together.
Prove equality with fresh retained-only calibration after every successful request.
Also prove canonical compressed-state equality across valid deletion histories.

The reviewed precision condition already connects feature error, ridge, and rounding margins.
For certified bounds \(h,e\), define

\[
\eta=(2he+e^2)/\lambda.
\]

With the defined positive margin quantity \(\tau\), a sufficient condition is

\[
\eta^2(1+\tau^2)<\tau^2.
\]

The derivation appears in `docs/FIXED_COST_THEORY_V23.md`, Section 9.3.
Preserve its induction, finite-grid, saturation, and tie conditions.
An enclosure containing two different exact outputs cannot certify one constant output.
Revision 25 supplies such a sixteen-bit witness.

The defensible novelty unit is this calibration-specific contract and its quantitative precision–fallback boundary.
Generic interval soundness and additive deletion are supporting tools.
The current bound still needs useful predictive validation across independent requests.
It does not guarantee compression at every rounding boundary.

### C2. Sparse complete-row certification with shared evidence

Let \(p\) count output rows and let \(u_k\) count unresolved rows before retry tier \(k\).
Let \(B_k\) count shared coefficient work and \(c_k\) count each complete row check.
Conditional verification work satisfies

\[
C_{\rm sparse}=B_0+p c_0+
\sum_{k\ge1}\mathbf1\{u_k>0\}B_k+
\sum_{k\ge1}u_k c_k.
\]

This expression assumes bounded per-row costs for each stated tier.
For varying row costs, replace each product with the actual row-cost sum.
It excludes neural fallback and ordinary service overhead.
The complete service ledger must add both.

Each complete row certificate quantifies over the same feature enclosure.
Their conjunction certifies the stage without a probability union bound.
Failed partial rows cannot contribute uncertified prefixes.
Revision 28 implements this composition and avoids six repeated full-stage retries in the development request.

Do not claim row separability itself as new.
The plausible algorithm contribution combines shared evidence, exact completion, and sparse retry scheduling.
Measure its benefit against equally optimized reconstruction and exact cached factors.

### C3. Dimension-aware evidence and a realistic scaling boundary

This extension remains prospective.
Let \(T\) count retained tokens, \(d\) count input features, and \(p\) count output rows.
The current ordinary token-space work is

\[
O(dT^2+pdT),
\]

with \(O(T^2+dT)\) shared working storage before row outputs.
Dense feature-space solving instead needs ordinary work

\[
O(Td^2+d^3+pd^2).
\]

These are arithmetic counts, not machine-time guarantees.
Exact fallback also depends on operand bit widths.

A useful extension selects token space or feature space under an explicit memory limit.
Its proof must preserve the same finite output target across representations.
It must include certified conversion, accumulation order, uncertainty growth, and fallback costs.
Woodbury identities alone do not establish this contribution.
Approximate low-rank truncation changes the target unless certified enclosures cover every discarded component.
This extension could establish a stronger practical contribution than additional sixteen-token optimization.

## 4. Realistic scaling calculations

The GPTQ author loader defaults to 128 samples of 2,048 tokens.

- [Author loader](https://github.com/IST-DASLab/gptq/blob/main/datautils.py)
- [Author feature-space implementation](https://github.com/IST-DASLab/gptq/blob/main/gptq.py)

These mutable source pages were inspected on 8 October 2026.
Pin their commits before reproducing a comparator.
They establish a workload reference, not a mandatory minimum for every experiment.

Our calculation gives \(T=262,144\).
One binary64 token-space matrix then needs

\[
8T^2=549,755,813,888\text{ bytes}=512\text{ GiB}.
\]

The current coefficient builder maintains several such arrays.
This calculation already excludes model weights, descriptors, row buffers, and temporary products.
At 256 sequences, one such matrix reaches 2,048 GiB.
Therefore, direct token-space expansion is not an executable realistic-scale plan.

The current retained archive stores 4,128,768 raw factor bytes for sixteen tokens across twenty-four stages.
That equals 258,048 bytes per token under the current architecture and format.
Linear extrapolation to 262,144 tokens gives 63 GiB of exact factor payload.
This is a dimensional calculation, not a compression forecast or an empirical memory measurement.
Compression overhead, escapes, token records, and preparation peaks require separate accounting.

Sparse output-row verification cannot solve this shared-state scaling problem.
The next design must examine feature-space statistics, source-local moment blocks, or a certified hybrid representation.
Every option must preserve deletable-source membership and canonical state semantics.

## 5. Required comparisons

| Comparison | Required conclusion |
|---|---|
| Exact-factor repair | Does compressed evidence justify its extra certificate work? |
| Equally indexed reconstruction | Expected equality; no unique deletion advantage from identical information |
| Lossless factors: raw, Zstandard, FPC or ALP | Does uncertain compression beat exact decoding at complete cost? |
| Matched cold and warm reconstruction | Does retained evidence save complete request time? |
| Fixed nearest versus fixed full-precision features | Does the chosen anchor justify its quality tradeoff? |
| Sequential calibration and nearest rounding | Does the new target retain useful NLP quality? |
| Token-space versus feature-space solving | Does the implementation remain practical as tokens increase? |

Use source-local compression blocks or externally fixed dictionaries for the lossless controls.
A corpus-trained dictionary can preserve deleted-source dependence in stored state.
Global recompression can preserve model exactness while changing the required canonical-state cost.
State these contracts explicitly.

Count preparation, parsing, checks, codec work, solving, fallback, output, and common checkpoint storage.
Measure actual deletion sequences before making lifetime claims.
Do not compare our CPU prototype directly with unrelated published GPU latency numbers.
Do not claim superior language modeling from exactness against our own calibration target.

## 6. Go/no-go guidance

**Proceed with the exact-output evidence direction** if the next design removes the token-space memory barrier.
Before broad experiments, screen relevant lossless codecs on saved factors.
Then test complete transactions on independent requests under a frozen precision policy.

**Stop the latency-superiority claim** if compressed repair remains slower than equally optimized exact cached factors.
A storage–latency tradeoff paper remains possible if storage savings are substantial and useful at realistic scale.
The current 5.30% complete-state saving does not establish that case.

**Stop the broad GPTQ-repair claim** while the fixed-feature target differs from sequential GPTQ calibration.
Keep the sequential obstruction as a documented reason for the architectural choice.

**Do not expand the old forty-cell plan unchanged.**
First specify the final target, scaling path, comparator contracts, and quality gate.
The current quality evidence remains two articles and thirty predictions.
It cannot support preserved language-model quality.

## 7. Search record and limitations

Queries covered calibration deletion, compressed calibration evidence, exact output certification, quantization stability, and lossless activation compression.
Additional queries covered GPTQ geometry, realistic calibration counts, and verified linear algebra.
The audit used primary papers, proceedings, author pages, and author code for its substantive claims.
Secondary search results only identified candidate sources.

QSS received primary full-text inspection.
ExecCert currently has abstract-level primary evidence because direct full-text access failed.
The unavailable Exact-Fun author PDF remains an explicit retrieval gap.
These gaps prevent claims that every closest theorem has received a complete comparison.
Recheck both papers and newly published work before writing the final novelty statement.
