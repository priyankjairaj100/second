# Revision 3 validation

Date: 4 October 2026. Scope: mathematical review, software correctness and document validation. Research experiments remained paused.

## Final software result

`python -m unittest discover -s tests -v`: **77 tests passed**, exit code 0.

Full output is in `validation/software_tests_v3.txt`. `validation/tested_source_sha256.json` binds every tested source/test file to its SHA256. Python static compilation also passed for all source and test modules. The unittest runner's elapsed time is incidental verification metadata; it is not a quantization/repair benchmark result.

Covered properties include:

- Exact quantizer decisions against independently written constrained quadratic solves, including ties, scaling, saturated grids and invalid inputs.
- Sparse code injection against independent solves and full target recurrence; false/stale envelope and trace handling.
- Direct feature-Gram vs response-polynomial agreement; oriented cross terms; canonical deletion order; identity and payload rejection.
- Squared error descriptors including mixed terms and exact outward square roots.
- Compact linear response storage, direct constant/linear/tangent contraction, shifted PSD enclosures and normalization.
- Complete fresh/repair stage state, changed first-stage codes, immutable prefixes/configuration, repeated/combined/empty/all deletions, request/source identity and stale witness rejection.
- Quadratic and low-storage response adapters with zero retained neural replay on supported algebraic correctness fixtures; chart miss and legitimately unavailable response evidence safely replay.
- A signed-bound normalization case with M0=1/4 that would falsely certify incorrect codes if normalization were omitted.
- Complete decoder causality, multihead/multiblock execution, exact dyadic export, finite target errors, logits/generation, changed first quantized stage after deletion, fresh/repair canonical bytes and full logits, repeated requests and provider-disabled fallback equivalence.
- Weighted scheduling bounds for uneven cooperative packets with cancellation and commit charges, and rejection before commit on invalid packets.

These fixtures verify program behavior. They are not synthetic empirical datasets, model-quality studies, certificate-coverage estimates or practical-speed measurements.

## Independent review

The theory and code were reviewed in separate parallel tracks. See `theory_revision/implementation_review_v3.txt`, `response_moments.txt`, `linear_gram_response.txt` and `docs/NOVELTY_AUDIT.md`.

Two concrete defects were discovered and resolved before the final run:

1. Reassignable service configuration could become inconsistent with a cached target manifest. Service configuration is now frozen and regression-tested.
2. A legitimate unavailable response descriptor was treated as malformed evidence. Both adapter tiers now use a canonical unavailable marker, yielding UNKNOWN and exact replay; malformed claimed evidence still fails closed.

Review checked full mixed curvature, finite/residual remainder terms, coefficient-information lower-bound scope, PSD omission, signed enclosure direction, replay invariants and all normalization factors. Mathematical proofs remain conditional on their stated domains and trusted provider assumptions; no proof assistant was used.

## Report checks

The consolidated PDF builds successfully, has 24 pages, and produced no Overfull-box warning. All pages were rendered and visually inspected; updated pages were re-rendered after corrections. Benign Underfull table-layout warnings do not affect content visibility.

## Not validated by this work

- Real pretrained model quality, real-data certificate coverage or saved full-model latency.
- Automatic certified finite transformer jets/curvature providers or arbitrary vendor kernels.
- A compact group-aggregate response state integrated into the service; the transparent adapters retain and read per-record payloads.
- An advantage over the best equally indexed fresh algorithm, GPU scheduling, cold-service I/O or preparation amortization.
- Physical erasure of Python/caller memory copies, hostile-store authentication or equivalence to a different finite quantizer E.
- Recovery or re-execution of historical experiments whose raw files were pruned.
