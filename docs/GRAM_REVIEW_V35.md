# Independent pooled-Gram component review

Review date: 9 October 2026. This document concerns the new `research_v35` modules.
It does not alter any historical numerical implementation or empirical record.
The component remains separate from complete-model execution.

## Review state

The direct-Gram algebra and exact accumulator pass the independent review below.
The component worker and controller pass the final source review.
All thirty-seven focused numerical and protocol fixtures pass independently.
No real-data numerical outcome was used for this review.
The bounded component is ready for prospective registration and execution.
This approval does not extend to full-model experiments or publication readiness.

## Mathematical target

Let the exact stored matrix be \(K=XX^T\), formed from binary64 words interpreted as exact dyadics.
The target metric remains \(H=\lambda I+K/\nu\).
The original positive normalization \(\nu\) remains fixed after deletion.
Set \(\beta=\lambda\nu\) and \(B_i=K_{S_i,S_i}+\beta I\).

For an approximate suffix solution \(\widehat y_i\), directed arithmetic bounds
\(\|e_1-B_i\widehat y_i\|^2\le E_i\).
Trusted PSD provenance gives \(B_i\succeq\beta I\).
Therefore the existing coefficient error bound remains valid:

\[
|a_{hi}-K_{h,S_i}\widehat y_i|^2
\le \min\left\{
\|K_{h,S_i}\|^2E_i/\beta^2,
K_{hh}E_i/(4\beta)
\right\}.
\]

The second inequality follows from a PSD factorization of the exact matrix.
It does not require every matrix in its entrywise enclosure to be PSD.
Neither a positive diagonal nor a floating eigenvalue check supplies this premise.

The new wrapper preserves the V30 coefficient and row kernels.
Its nominal inverse remains a proposal, checked through directed residuals.
The row recurrence retains the sign \((w_{rh}-q_{rh})a_{hi}\).
Strict lower and inclusive upper cell boundaries preserve lower-code midpoint ties.
An unresolved certificate returns no accepted approximate model.

## Trust and arithmetic requirements

Trusted accumulation must interpret every finite binary64 word exactly.
Source deletion must subtract complete committed contributions using exact integers.
Source membership must match, remain disjoint under addition, and preserve normalization.
Raw deserialization alone must never activate the PSD-dependent certificate.
Restored trust requires an independently authenticated prior trusted archive binding.
An attacker-controlled checksum cannot establish either PSD or source provenance.
Arbitrary mutation of private Python internals lies outside this process-level trust boundary.

Admission must precede expensive multiplication and allocation.
Bit-width bounds must cover intermediate products, sums, and aligned subtraction.
Parser and serializer bounds must include Python objects, not merely packed payload bytes.
OS limits remain separate from these explicit representation estimates.

## Findings raised before execution

The first parser and serializer drafts used a three-times-payload memory rule.
That rule undercounted Python integer and temporary byte objects.
The corrected parser now admits Python integer representation before allocation.
It separately bounds JSON expansion before decoding.
The serializer now writes a bounded bytearray instead of joining many entry objects.
Its admission includes integer residency and temporary header representations.

The first overflow enclosure handler converted a huge integer through `copysign`.
That conversion could itself overflow.
A sign-comparison correction now produces outward infinite endpoints as intended.
The direct certificate safely refuses nonfinite enclosures.

Canonical serialization now enforces the parser's 65,536-byte header limit.
Accumulation now snapshots feature storage before scanning and multiplication.
The caller must not mutate storage concurrently with that initial copy.
These corrections preceded registration and real-data outcomes.

## Software validation

The independent reviewer ran `tests.test_exact_gram_v35`: all fifteen tests passed.
They compare exact accumulation with rational oracles, including subnormal and overflow cases.
They check canonical add/subtract bytes, complete commitments, resource admission, and trusted restoration.
The conversion API also rechecks its own integer-bit and binary64-source exponent limits.

The reviewer also ran `tests.test_direct_gram_v35`: all thirteen tests passed.
They check independent rational target equality, exact deletion, preserved normalization, and midpoint ties.
They also test deliberately bad inverse proposals and refusal of unauthenticated parsed Grams.
These small software fixtures establish no empirical latency or scientific generalization.

All nine tests in `tests.test_gram_protocol_v35` also passed independently.
They check complete-row transposition, grid preservation, input binding, and no-overwrite behavior.
They reject modified plan fields, symbolic links, and retrying an existing attempt.
The final combined run passed all thirty-seven tests in 0.292 seconds.

Reviewed source digests:

| File | SHA-256 |
|---|---|
| `research_v35/exact_gram.py` | `4695e0d3069e9a956dfe57c0bbdce19de0fa0a6c8ad71c25698b0b3b09a85973` |
| `research_v35/direct_gram.py` | `29b7c7e9fe2e45e5ab341e1287e4cd42599a1c440ae540b08305fb907c47ae21` |
| `research_v35/archive_capsule.py` | `bbbe6f512b5558c3ba6512d7fbbb6c735221463f300b293ea785e51bbbee3de9` |
| `scripts/execute_gram_pilot_v35.py` | `4de2585c882b25e29cf8387c8cc6d9444c50b437b6ca5c221c510accede93262` |
| `scripts/launch_gram_pilot_v35.py` | `c4b6095241b0901394cfb73f876e34e937e188de6b6d3bfa615725c30aba3096` |

## Portable archive capsule

`research_v35/archive_capsule.py` provides a separate bounded archival reader.
Export authenticates the original full states and checkpoint before extracting selected bytes.
The capsule preserves original descriptor encodings and exact decoded feature hashes.
It also binds the four complete weight rows and previously evaluated reference codes.
Export performs no new Gram accumulation or model quantization.

Its distinct `ArchiveFeature` type avoids asserting current encoder equivalence.
The registered external capsule hash supplies its authenticated extraction premise.
Neural feature generation remains historical provenance, not a newly verified execution.
This reader neither changes nor relaxes the original transformer runtime contract.

## Required empirical interpretation

The planned component uses four complete output rows at width 768.
It must retain every feature coordinate and the original row grids.
The inputs must come from the pinned real WikiText archive.
Software fixtures are not empirical datasets.

Original-minus-deleted moments must equal independently accumulated retained moments exactly.
Every complete output row must match the archived retained reference and cached-token comparator.
Decode, accumulation, serialization, subtraction, solve, verification, and output costs must remain visible.
Shared loading, verification, compilation, and parsing costs must be separately reported.

Archived features exclude neural replay.
Four output rows exclude the remaining model rows and stages.
One fixed-order component observation cannot establish a complete-service or lifetime speedup.
It cannot settle the larger-model or prospective-confirmation requirements.
Unresolved certificates, resource refusals, timing losses, and failed attempts must remain published.

The reviewed controller binds the attempt plan to the registered program.
It checks command, resource limits, receipt, ledger settlement, terminal copies, and stdout commitment.
It compares actual retained Gram and code artifacts after the worker completes.
One attempt is permitted; failures cannot trigger automatic retries or replacement samples.
