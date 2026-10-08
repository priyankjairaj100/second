# Exact Calibration Removal from Compressed Feature Evidence

Working manuscript, 8 October 2026.
This draft supersedes the sequential-target positioning in `MANUSCRIPT_DRAFT.md` for the implemented fixed-feature method.
The historical draft remains unchanged.
This manuscript is not submission-ready.
Numerical tables must follow the final verified campaign summaries.

## Abstract

Calibration text influences quantized weights even when pretrained weights remain fixed.
We study exact removal of this influence under an explicitly specified calibration algorithm.
Sequential calibration creates a difficult dependency: changed early weights invalidate later cached activations.
Our implemented method instead uses calibration-independent ancestor weights to generate source-local features.
It stores compressed feature enclosures and certifies the resulting discrete weight codes.
Successful requests reproduce retained-only calibration and canonical retained auxiliary state.
Ambiguous certificates invoke bounded refinement or exact feature replay; exhausted budgets cause explicit refusal.
A feature-space verifier avoids quadratic dependence on calibration length in its matrix storage.
An information bound separates exact model recovery from recovery using the deployed weights alone.
Real-data development experiments verify complete models and evaluate quality against matched calibration controls.
Current evidence does not establish broad speed, quality superiority, or faster repair of ordinary sequential GPTQ.

## 1. Scope and motivation

A calibration document can affect many quantized weights without modifying the pretrained checkpoint.
Deleting that document therefore requires a quantization counterfactual.
The target must specify feature computation, normalization, rounding, and auxiliary state.
Removing a document's old covariance contribution is generally insufficient for sequential calibration.
An earlier changed weight can alter later retained activations.

Our earlier sequential implementation exhibited this obstruction on real model inputs.
Its complete repair remained slower than matched cold reconstruction.
We preserve that result as a boundary motivating a different quantizer design.
We do not claim that the new design accelerates the original sequential target.

The implemented design freezes ancestor features independently of the deletable calibration corpus.
Fixed features and additive removal are established ideas.
The proposed contribution concerns exact adaptive rounding from compressed, uncertain feature evidence.
Its usefulness depends jointly on storage, certificate cost, fallback, and language-model quality.
Each quantity requires a separate measurement.

## 2. Declared counterfactual

Fix pretrained weights, record boundaries, tokenization, grids, coordinate order, and a binary64 feature program.
Fix a nearest-grid ancestor model using only the pretrained weights.
For stage \(\ell\) and record \(j\), this ancestor defines \(X_{\ell j}\).
Features never depend on other calibration records or on repaired stage weights.

For retained records \(R\), concatenate their features as \(X_\ell(R)\).
Use a fixed positive ridge \(\lambda_\ell\) and original normalization \(\nu_\ell\):

\[
H_\ell(R)=\lambda_\ell I+X_\ell(R)X_\ell(R)^\top/\nu_\ell.
\]

Every successful binary64 feature value denotes its exact dyadic rational.
The weight quantizer follows the repository's declared adaptive rounding recurrence.
Midpoint ties choose the lower code.
This defines \(Q_{\mathrm{fix}}(R)\).
It differs from stock GPTQ reductions and from sequential ancestor calibration.
It also differs from an ideal real-arithmetic transformer.

The feature evaluator is partial.
Unsupported or unresolved finite operations cause refusal.
The theorem conditions on successful required feature evaluations and sufficient declared resources.
No approximate model is committed after an unresolved certificate.

For each record, let \(D_j\) denote its canonical source-local compressed descriptors.
The promised state is the canonical serialization of:

\[
\mathcal S(R)=\bigl(Q_{\mathrm{fix}}(R),\{D_j:j\in R\},\text{retained provenance}\bigr).
\]

The common pretrained checkpoint remains required.
Its size must accompany storage comparisons, even when excluded as a shared constant.
This contract concerns model and declared service state.
It does not erase external archives or knowledge already present in pretrained weights.

## 3. Repair from uncertain evidence

The encoder maps exact finite feature words into canonical dyadic enclosures.
Trusted preparation establishes containment for every original descriptor.
Hash and syntax checks preserve that provenance but cannot establish containment independently.

Repair first validates membership, target identity, descriptor identity, and the deletion request.
It retains unchanged descriptors for surviving records.
For each stage, it constructs feature boxes from those descriptors.
A point proposal supplies candidate weight codes.
The proposal's numerical solver is not trusted evidence.
Directed arithmetic verifies every accepted rounding decision over the entire feature box.

If a certificate fails, sparse refinement visits only requested unresolved coordinates.
Exact replay remains available under an explicit neural-work allowance.
Point solving has a separate cumulative work allowance.
Every admitted stage must also satisfy its own workspace and work bounds.
These allowances bound declared structural work; they do not predict wall time.

After successful certification, repair writes the complete model and retained canonical state.
Temporary exact factors and refinement results do not alter the canonical descriptor policy.
The same policy applies after direct, combined, and successive deletions.

### Conditional exactness

Assume trusted descriptor containment and matching mathematical target identities.
Assume every accepted certificate is universal over its supplied feature box.
Assume exact replay uses the same declared feature program.
Then every successful repair returns \(Q_{\mathrm{fix}}(R)\).
If surviving descriptors remain canonical, its state also equals \(\mathcal S(R)\).

Proof.
Source locality makes each surviving feature identical to its retained-only feature.
Descriptor containment places those features inside every verified box.
Universal certification therefore implies equality of each accepted discrete decision.
Within a stage, coordinate induction handles the adaptive rounding recurrence.
An exact replay replaces uncertain evidence with the same retained-only feature values.
Finally, canonical descriptor retention and serialization establish state equality.
Applying this argument to each successful request gives equality across deletion histories.

This statement is conditional correctness, not universal completion or speed.
Its detailed premises and implementation review appear in `FIXED_COST_THEORY_V23.md` and the V30 service reviews.

## 4. Verified feature-space coefficients

Let \(X\in\mathbb R^{d\times T}\), \(K=XX^\top\), and \(\beta=\lambda\nu>0\).
For suffix \(S_i=\{i,\ldots,d-1\}\), define \(B_i=\beta I+K_{S_i,S_i}\).
The rounding coefficient has the equivalent feature-space expression:

\[
a_{hi}=K_{h,S_i}B_i^{-1}e_1.
\]

This follows from the push-through identity for the equivalent token-space system.
It changes representation without changing the target.

A nominal inverse update proposes \(\widehat y_i\).
Directed arithmetic bounds the residual uniformly over the supplied feature boxes:

\[
\|e_1-B_i\widehat y_i\|_2^2\le E_i.
\]

The ridge floor supplies one coefficient bound.
A spectral inequality supplies another:

\[
\|K_{h,S_i}B_i^{-1}\|_2^2\le K_{hh}/(4\beta).
\]

Indeed, each singular value contributes \(s/(\beta+s^2)\le1/(2\sqrt\beta)\).
Hence the residual contribution to squared coefficient error is at most \(K_{hh}E_i/(4\beta)\).
Directed product error is added separately.
Intersecting independently sound bounds can tighten the resulting certificate.

The implementation avoids token-by-token square matrices.
Its structural work is \(O(d^2T+d^3+md^2)\), where \(m\) counts output rows.
This asymptotic description does not establish the fastest backend for every finite shape.
The adaptive dispatcher chooses between admitted feature-space and token-space routes using a declared work proxy.
Both routes require exact certificate acceptance.
Full derivation, implementation assumptions, and rational-oracle fixtures appear in `PRIMAL_CERTIFICATE_V30.md`.

## 5. Storage, lower bounds, and cost

The deployed quantized weights alone need not determine a deletion response.
The response lower bound constructs canonical four-bit models with positive rounding margins.
Under its finite information-access model:

\[
b\ge\left\lceil\log_2 {N\choose N/2}\right\rceil.
\]

The construction has condition numbers at most three.
Its cumulative extension bounds stored bits plus response probes.
It does not prove transformer realizability or practical NLP speed.
Its positive margins shrink with the construction size.
The complete statement appears in `RESPONSE_LOWER_BOUND_V29.md`.

Request speed alone is insufficient.
Let \(P_s\) and \(P_0\) denote matched preparation costs with and without repair state.
Let \(r_i\) and \(c_i\) denote complete repair and cold request costs.
The measured lifetime difference is:

\[
(P_s-P_0)+\sum_i(r_i-c_i).
\]

All terms must use compatible optimized implementations and explicit service boundaries.
Repeated execution of one request is not a changing-state sequence.
An equally indexed constructor receives every item available to repair.
Since it can share repair's algorithm, strict superiority over that constructor is not required.

## 6. Empirical design and current evidence

All empirical inputs use real text.
Small rational and miniature decoder fixtures are software validation only.
The pilot policy runs a small case before expanding a scientific cell.
Registrations bind source snapshots, inputs, budgets, gates, and target identities.
Receipts include failed and interrupted work.
Complete latency includes loading, verification, state maintenance, and output.
Nested solver clocks are diagnostic and are never added to complete latency.

The V30 quality screen used eight previously untouched WikiText validation articles.
It evaluated 1,016 predictions per model with a shared inference implementation.
The small-calibration fixed/sequential perplexity ratio was 0.998565674.
Its descriptive paired-article interval included one.
The registered relative quality gate passed; superiority was not established.
Fixed calibration reduced perplexity relative to nearest rounding and increased it relative to full precision.
All twenty evaluated article exclusions remain reserved from future confirmation.

At 1,024 calibration tokens, the feature-space component took 22.02 seconds.
The optimized token-space comparator took 34.27 seconds.
All 3,072 checked codes agreed.
At 128 tokens, token space was faster.
These measurements cover four complete rows from one stage, not complete-model scaling.

The larger service pilot retains 128 tokens from an original 256-token corpus.
Its first repair and cold model agreed across all 24 stages and 42,467,328 codes.
An exact common neural optimization was then selected for stronger matched comparisons.
The final report must present those optimized results before making a performance claim.

Detailed tables belong to the verified V30 summaries.
This draft intentionally does not substitute component gains for complete service gains.

## 7. Related work and positioning

Fixed calibration features, additive statistics, and caching are established foundations.
GPTQ geometry also establishes row separability and triangular rounding structure.
Verified linear algebra supplies residual and inverse-defect tools.
Recent QSS and ExecCert work further limits broad novelty claims.
Our potential distinction is exact calibration-code recovery from source-local compressed enclosures with bounded repair.

The relevant primary-source comparison appears in `NOVELTY_AUDIT_V29.md`.
The current claim audit appears in `CLAIM_AUDIT_V30.md`.
Detailed ExecCert theorem comparison remains outstanding because its full text was unavailable during retrieval.
Search absence does not establish priority.
The final bibliography must include the inspected primary sources and precise theorem-level comparisons.

## 8. Limitations and submission gate

The implemented target differs from ordinary sequential GPTQ.
Our sequential-target repair did not establish a complete-model advantage.
The current model and corpus coverage remain narrow.
Repeated timing cannot replace independent deletion requests.
Small calibration workloads cannot establish large-model deployment performance.
Lossless alternatives remain strong controls for compressed evidence.
ALP has not been measured.
Confirmation, task-level generalization, and changing-state lifetime measurements remain separate requirements.

Submission requires a favorable, replicated storage–latency tradeoff against the strongest compatible controls.
It also requires matched quality, larger workloads, additional model/corpus coverage, and independent reproducibility review.
No theorem removes those empirical requirements.
