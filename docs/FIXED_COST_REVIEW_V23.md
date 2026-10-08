# Revision 23 cost and compression theory review

Status: algebraic review completed on 8 October 2026.
This is an internal review by a separate project agent.
It is not external verification or proof-assistant verification.
The review adds no numerical experiment or empirical observation.
It does not establish novelty.

Reviewed document: `docs/FIXED_COST_THEORY_V23.md`.
Reviewed document SHA-256: `a57e2ef7e0c048ef16d1e2ab3285dc8d4984fb1c7051a362bcdecee3991c142e`.

## Findings and corrections

No blocking algebraic defect remains under the document's explicit premises.
The review requested two corrections before this conclusion.

First, the original wording bounded an arbitrarily chosen upper bound from above.
That inference was invalid.
The corrected text instead chooses a certified value for the relative distortion bound.
Its choice is $\rho=u/\sqrt{M_0\lambda}$, where $u\ge\|D\|_2$ is certified.

Second, the compression threshold initially left pivot and energy conventions implicit.
The document now defines its normalized reverse-LDL factors explicitly.
It sets $g_j=1/t_j$ and

\[
P_{aj}=\sum_{h<j}(v_{ah}-q_{ah})^2/g_h.
\]

These definitions agree with the repository's exact reference recurrence.
The document also distinguishes exact mathematical outputs from bounded solver completion.

## Exact moments and model semantics

T1 correctly uses equality of exact normalized metrics.
Positive ridge supplies unique reverse-LDL pivots in the fixed elimination order.
The deterministic grid rule then gives identical mathematical model codes.
The displayed token-space coefficient agrees with `src/low_rank_exact.py` and `src/low_rank_certified.py`.
It includes the current coordinate in its suffix Gram.

Equal metrics do not determine ordered factor bytes.
The document correctly keeps the revision 22 factor-state contract separate.
Sign reversal supplies one exact counterexample to that reconstruction implication.
Signed zeros supply another byte-level distinction.

The proposed moment-state corollary requires exact arithmetic and canonical encoding.
Floating subtraction alone cannot establish deletion-order independence.
Deleted contributions also require stored values or declared access to deleted records.
Record identifiers do not supply those values.
An equivalent indexed constructor receives the same allowed information.

## Information and output bounds

T2 is a valid deterministic response-class counting argument.
Its state bound concerns the entire allowed query family.
It excludes uncounted corpus-dependent side information.
The scalar example separates exact-metric queries from model-only queries correctly.
It does not establish a transformer-specific or model-query memory lower bound.

T3 is valid for the declared byte-access model and standalone literal state format.
The output contains all retained factor payloads and emitted model bytes.
Consequently the specified writer cannot have sublinear work in that output length.
This statement is not a physical-storage lower bound for arbitrary filesystems.
Block cloning, shared objects, or lazy manifests require different access and output contracts.
The document explicitly excludes those alternatives from the stated bound.

The lifetime crossover in T4 follows by exact subtraction of the two stated ledgers.
It correctly counts each record's number of retained future uses.
It permits negative per-record savings.
It is not a distributional or wall-time theorem.
Its shared solver term may cancel only when the declared comparison actually shares that work.
Initial preparation and repeated state output remain charged.

## Bit costs

Every finite binary64 value has the form $u2^{-1074}$ with $|u|<2^{2098}$.
A product numerator therefore has magnitude below $2^{4196}$.
Summing $T$ such terms needs at most the stated conservative signed width.

For $\lambda M_0=p/q$, the integer-scaled metric is correctly written as

\[
q\sum_s u_su_s^{\mathsf T}+p2^{2148}I.
\]

Its scale is positive and preserves the reverse-LDL decision coefficients.
The document includes the additional bit lengths of $p$ and $q$.
Its determinant estimate follows the standard Hadamard bound.
These arithmetic statements do not make exact updates constant-time machine operations.
The token-space and dense-metric work estimates also remain separate.
Dense moment subtraction can lose when the retained token count is small.

## Quality statements

The augmented-feature proof for T5 is sound.
The ridge augmentation preserves the exact local reconstruction loss.
Both triangle inequalities yield the stated upper and lower distortion bounds.
Clamping the lower factor at zero is necessary when $\rho\ge1$.

The approximation-ratio transfer requires fixed deployment inputs and an identical codebook.
Changing preceding deployed stages can invalidate that comparison premise.
The diagonal minorant supplies a valid lower bound on the grid-constrained optimum.
Its ratio is available only when that lower bound is positive.
The document does not assume that greedy rounding solves the global discrete optimization problem.

T6 follows from exact selection over its declared candidate bank.
That selection changes the target.
It guarantees local anchor-loss dominance only.
It provides no full-model perplexity or deployment-loss guarantee.

## Compression and fallback

T7 has the correct conditional structure.
Each descriptor must enclose the defining exact finite factors.
Acceptance must prove the same quantizer output throughout the represented set.
Exact fallback must evaluate the defining fixed-feature target.
The theorem does not infer descriptor validity from a checksum or observed containment.

Canonical state follows only because persistent descriptors remain source-local and unchanged.
Request-local refinement factors must be discarded under this contract.
Persisting a history-dependent refinement cache would require a new canonical state rule.

The moment perturbation estimate

\[
\|H_X-H_C\|_2\le 2he+e^2
\]

follows from the Gram expansion and norm submultiplicativity.
The ridge floor then gives the stated relative metric enclosure for $\eta<1$.
Substitution into the existing relative-metric theorem gives

\[
|v_{aj}(H_X)-v_{aj}(H_C)|^2
\le\frac{\eta^2}{1-\eta^2}g_jP_{aj}.
\]

This bound remains conditional on matching earlier codes.
The strict cell-margin test supplies that premise by coordinate induction.
The threshold $\eta^2(1+\tau^2)<\tau^2$ follows by rearranging that strict inequality.
Zero energy, midpoint ties, and saturation require the separate treatments stated in the document.
The fixed-range encoding error bound has the correct $\sqrt{dT/M_0}\,2^{-b}$ dependence.

Mathematical constancy becomes easier under genuinely nested interval refinement.
A particular finite verifier need not have monotone acceptance behavior.
The document correctly distinguishes these statements.
Positive true margins guarantee a sufficiently small mathematical neighborhood through continuity.
They do not guarantee that an implemented bounded verifier reaches that neighborhood within budget.

The replay dependency closure in section 9.4 is necessary.
Reconstructing one late factor can require earlier accepted stages for the same record.
Accepted-stage counts alone therefore cannot establish avoided neural work.
The complete ledger includes candidate work, proof work, fallback, state output, and disposal.
Initial compression remains a separate lifetime cost.

## Remaining research obligations

The compression route remains an unimplemented proposal.
It needs an encoder, a sound verifier, and a complete state service.
It also needs useful real-data margins, measured fallback rates, and complete cost comparisons.
The full empirical program and novelty assessment remain separate obligations.
The theory does not establish reliable repair speed or competitive language quality.

## Reference implementation hashes

| File | SHA-256 |
|---|---|
| `src/exact_core.py` | `155724c268b0afd2e8dd97a0de6377609fe44545885061dc97351d0aa3c3a4c9` |
| `src/low_rank_exact.py` | `0d5e8d85f5a54f27c0e10ec2be7218a759abc9ae6d2773fc4324336e7a62c8c1` |
| `src/low_rank_certified.py` | `aca8914616f15f7f3f8d31a31a05fb3e3e19c35b40445466ba4c97a3f156f301` |
