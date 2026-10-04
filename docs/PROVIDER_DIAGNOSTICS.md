# Provider diagnostics in revision 9

The diagnostic profile now records available internal provider evidence.
The clean timing profile does not evaluate its lazy diagnostic builders.
Neither profile changes certificate decisions or canonical state.

## Affine-domain checks

The affine provider distinguishes an inconsistent linear system from a selected coefficient vector outside its box.
These are different rejection reasons.
An inconsistent system establishes that the installed finite prefix lacks an affine representation in the declared directions.
A coefficient-box rejection applies to the solver's selected representation.

The current solver sets free variables to zero.
Another feasible representation might satisfy the box.
Therefore selected-coefficient rejection does not prove that the full affine domain excludes the prefix.
The generic abstention message now states this limitation correctly.
Exact fitting and certificate acceptance remain separate events.

## Descriptor extraction

The affine provider identifies failed center-jet and region-jet construction separately.
The parameter-box provider distinguishes domain checks, fixed-base features, feature enclosures, and error-envelope construction.
Caught proof failures retain their exception type and bounded reason text.
They still return unavailable descriptors under the same conditions as before.
Required finite evaluation during later replay retains its original abort behavior.

Successful affine extraction reports available upper bounds for finite error, center error, mixed curvature, and sampled gradient errors.
Successful box extraction reports its uniform feature-error bound and anchor route.
Record content digests bind the reported descriptor to its input.
Reported quantities are proof bounds.
They are not measured realized approximation errors.

## Limits

The existing collector caps stage records, event kinds, samples, text, and exact-number encodings.
Oversized numbers receive explicit magnitude summaries.
Dropped observations retain omission counters.
No missing descriptor component becomes a zero-valued numerical observation.

These events do not provide a complete primitive execution graph or every temporary Hessian value.
They do not recover discarded observations after a cap.
They cannot independently establish complete changed-ancestor group coverage.
That evidence requires matched diagnostic runs with complete group identities and no relevant omissions.
C05 remains open under its full empirical and numerical-decomposition criteria.

Five dedicated correctness fixtures check failure attribution, exact component identities, bounded callbacks, and clean-profile parity.
They are not empirical model or dataset results.
