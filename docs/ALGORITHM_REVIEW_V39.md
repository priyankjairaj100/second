# V39 algorithm and implementation review

Review date: 10 October 2026.
The primary agent performed this review.
It is not an independent review or a new impossibility theorem.
Read the existing proof map in `METHOD_AND_THEORY_MAP_V32.md` first.

## Feature-space certificate

Let each possible retained feature matrix satisfy \(L\le X\le U\).
Let \(N_0>0\) remain the original token count.
Let \(\lambda>0\) be the fixed ridge.
The target metric is

\[
H(X)=XX^\top/N_0+\lambda I.
\]

Every actual Gram \(XX^\top\) is positive semidefinite.
Its directed enclosure comes from the existing native feature Gram kernel.
An arbitrary matrix inside the resulting entrywise enclosure need not be positive semidefinite.
The proof requires positivity only for actual feature matrices.
We never accept an external enclosure without feature or trusted Gram provenance.

Each suffix system has minimum eigenvalue at least \(\lambda N_0\).
For a proposed suffix solution \(\widehat z\), let \(\eta\) bound its exact residual norm.
Then

\[
\|z(X)-\widehat z\|_2\le \eta/(\lambda N_0).
\]

The existing directed residual verifier bounds every actual residual in the feature box.
Its component bounds therefore cover every actual rounding coefficient.
The proposal is only an acceleration aid.
The residual verifier supplies the evidence.

The shared row kernel uses identity virtual features in feature space.
These identity columns are coordinate vectors, not synthetic calibration records.
Its accumulated error and coefficient inner product equal the direct feature-space recurrence.
An outward Euclidean radius bounds the coefficient error.
A certified rounding cell therefore contains the exact decision.
Induction across coordinates preserves all previously certified decisions.
The fixed tie rule remains unchanged.

Ball-refused rows receive the existing directed interval verifier.
That verifier uses the same coefficient evidence.
If it also refuses, the adapter returns no code array.
If every row completes, the output matches the fixed target for every feature matrix in the box.
For a point box, this gives exact equality with retained-feature requantization.

This claim assumes supported IEEE arithmetic and unchanged inputs during execution.
It also requires fixed grids, positive ridge, fixed normalization, and every existing residual-verifier premise.
Software fixtures support implementation review; they do not replace these premises.

## Algorithmic change

`research_v39/feature_primal_ball.py` joins two existing verified components.
It combines directed feature-space Gram formation with the shared fast row kernel.
The older feature-space implementation uses a more expensive generic row verifier.
The new adapter retains that verifier as a mandatory fallback.
This removes an avoidable mismatch in high-token comparisons.

Token-space coefficient construction has a structural term proportional to \(dT^2\).
Feature-space construction has terms proportional to \(d^2T+d^3\).
The shared row stage has a term proportional to \(Rd^2\) in feature space.
Here, \(T\) is retained tokens, \(d\) is width, and \(R\) is output rows.
These are work proxies, not wall-time guarantees.
Constants, decoding, interval width, fallbacks, and storage can change the empirical ranking.
The pilot compares both solvers at all three sizes.

Admission includes directed Gram formation and two complete row passes.
It also includes explicit feature arrays and fallback copies.
The process limit covers additional allocator, compiler, and interpreter memory.
The admission estimate alone does not guarantee completion.

## Exact Gram adaptation

The V37 wrapper implicitly applied the exact archive's default 256-token limit.
That limit would reject this pilot's larger retained Grams.
`research_v39/scaled_gram_ball.py` passes an explicit archive budget.
Its numerical function otherwise matches V37 exactly.
A focused source comparison verifies that narrow change.
Trusted source lineage, positive semidefinite construction, and outward conversion remain mandatory.
No runtime fact or historical numerical result is overridden.

## Failure reporting correction

The existing public diagnostic helper requires a mapping or dataclass.
Some certificate refusals have no attached diagnostic object.
Passing `None` would raise a reporting error and hide the numerical outcome.
The new worker supplies an empty mapping when diagnostics are absent.
It also preserves native ball diagnostics when available.
Runtime and allocation failures remain fatal.

## Review evidence and limits

The focused fixtures include rational oracle agreement and nonzero feature boxes.
They include exact ties, mandatory fallback, and refusal without partial output.
They check admission before Gram allocation and token-dependent resource estimates.
They check explicit larger-token Gram admission with a small software fixture.
They check one-use execution, immutable evidence, fixed arm sets, and separate CPU caps.
They do not use synthetic empirical datasets.

No new empirical speed result existed at review time.
The adapters do not establish a universal full-model speedup.
They do not certify ordinary sequential calibration through changed downstream activations.
They do not establish complete successor-state correctness or useful lifetime cost.
Those remain separate scientific gates.
