# Full quadratic response control

Revision 7 adds a separate storage tier to the complete aggregate service.
It preserves the declared sequential quantization target.
The primary factory uses the same `V_cert` finite feature evaluator.
It also preserves grids, ties, coordinate order, ridge, and original normalization.

This control stores the full Gram polynomial of the same affine feature response.
It does not create a quadratic Taylor model of transformer features.
It does not establish the stronger whitened acceptance theorem.
Research experiments remain paused.

## Stored state

Fix an intrinsic response with feature matrices `Z_0,...,Z_r` for each record.
The matrices have `d` rows and `n_j` columns.
Let `m=r+1`.
The quadratic tier stores these oriented group totals:

\[
C_{st}=\sum_{j\in g}Z_{sj}Z_{tj}^{\mathsf T},\qquad 0\le s\le t\le r.
\]

The off-diagonal matrices generally lack symmetry.
The service stores their full matrices and restores their transposes during contraction.
It stores the existing scalar error moments without changes.
It stores record identities, source digests, and contribution digests.
It stores no per-record feature matrix, response matrix, or error descriptor.

The group response count is

\[
\frac{(r+1)(r+2)}2d^2.
\]

The group error count is

\[
\frac{(r+3)(r+4)}2.
\]

These counts describe rational slots.
Integer sizes, metadata, base parameters, domain parameters, output models, and serialization require additional storage.
The exact canonical payload records actual serialized bytes.
Rank zero has the same mathematical response information in both tiers.
Its quadratic schema remains distinct.

## Proposal and certificate

For `b=(1,a_1,...,a_r)`, the exact proposal is

\[
S_q(a)=\sum_s b_s^2C_{ss}
 +\sum_{s<t}b_sb_t(C_{st}+C_{st}^{\mathsf T}).
\]

This equals the Gram matrix of the stored affine feature response.
It includes every tangent cross term.
Signed coefficients retain their signs in this expression.
The error descriptor query uses coefficient magnitudes where its proof requires them.

Let `E²` bound the sum of squared feature errors across this group.
The existing descriptor contraction supplies this bound.
It retains finite-evaluation error, center error, derivative error, mixed curvature, and any certified unrepresented displacement.
Let `Z²=tr(S_q)`.
The implementation computes

\[
\delta=2\operatorname{sqrt}_{\uparrow}(Z^2E^2)+E^2.
\]

Then

\[
-\delta I\preceq S_{\mathrm{true}}-S_q\preceq\delta I.
\]

The proof uses `X=Z+R`, the triangle inequality, and the Frobenius norm bounds.
It requires sound intrinsic descriptors and a valid domain query.
The service retains those existing provider premises.
It does not certify arbitrary callback code.

The group bound uses raw statistics.
The stage solver divides accumulated bounds by the fixed original normalization and ridge.
It then applies the existing exact rounding certificate.
A rejected certificate causes retained replay.
A failed required finite evaluation aborts the transaction.
No approximate model becomes a committed result.

The compact tier omits the tangent Gram and uses a conservative diagonal shift.
The quadratic tier computes that Gram directly.
Therefore this implementation is a distinct proposal with distinct storage costs.
It does not guarantee more accepted decisions or lower complete cost.
Different proposal metrics can produce different rounding margins.

## Canonical deletion and repeated use

Deletion regenerates the removed record's intrinsic contribution from supplied source bytes.
The service checks its source and contribution digests before subtraction.
Every response and error moment uses exact rational subtraction.
The service rebuilds retained membership and canonical state.
A fresh retained construction therefore produces identical moments and metadata.
Topological certification or exact replay produces the same complete target model.
This argument holds after repeated deletion and after deleting all records.
An empty state contains no groups and uses ridge-only stage quantization.
Deleting an already removed record fails.

Repair and indexed fresh use identical summaries, proposal logic, and replay rules.
The retained index contains no original model.
Index maintenance costs remain separate and count exactly once.
The quadratic tier creates no deletion-specific solver advantage against this equally indexed method.

## Extraction and work accounting

Both provider tiers use the same feature and descriptor extraction procedure.
The quadratic provider calls the exact full moment builder after that extraction.
It does not first construct compact moments.
The box provider directly builds its rank-zero full response schema, containing one constant Gram.

For one record, the standard full response builder performs

\[
\frac{m(m+1)}2d^2n_j
\]

rational product terms.
The standard compact builder performs

\[
[(1+2r)d^2+r^2d]n_j.
\]

The error builder adds `(r+3)(r+4)/2` scalar product terms.
The ledger records these declared builder counts for each successful extraction.
They are symbolic arithmetic counts, not measured CPU instructions.
An external callback can implement different extraction work.
The exclusive extraction timer also includes feature evaluation and descriptor construction.

Adding or deleting a supplied contribution touches every stored response and error slot.
The ledger counts these matrix operations and contribution-digest bytes.
A quadratic contraction costs `O((r+1)²d²)` arithmetic operations.
The service also checks proposal positive semidefiniteness.
Exact rational bit costs and factorization remain additional costs.
Deletion also requires source access, re-extraction, metadata reconstruction, serialization, and output.
Setup and replay remain part of complete-service accounting.
The `full_replay` mode still pays the selected tier's state-maintenance costs.

No complete timing or lifetime advantage follows from this implementation.
The comparison must report setup, retained state, request service, replay, and publication overhead separately.

## Schema and migration

Use `AggregateRepairService(..., response_tier="quadratic")`.
Its extractor returns `(RecordMoments, RecordMoments)` for response and error.
The default tier remains `linear` and retains its old schemas.
The quadratic service manifest binds `aggregate-quadratic-service-v1`.
Its canonical retained index uses `aggregate-quadratic-retained-index-v1`.
The target manifest remains unchanged across tiers.
Bounded loading rejects a tier mismatch and malformed canonical encodings.
Structural checks do not authenticate hostile state storage.

The old compact state cannot generally reconstruct the quadratic state.
For example, take `d=2`, `r=1`, and `Z_0=0`.
The alternatives `Z_1=(1,0)^T` and `Z_1=(0,1)^T` have identical compact moments.
Their tangent Grams differ.
Upgrading a nonzero-rank compact state therefore requires source re-extraction or separately retained full moments.
The service never silently upgrades a state.

## Correctness evidence

`tests/test_quadratic_v7.py` checks the following properties:

- Oriented cross moments produce the exact changed-prefix Gram.
- The quadratic proposal differs from the compact shifted proposal.
- Nonzero finite-error descriptors enclose actual Gram differences.
- Repeated, reordered, empty, and complete deletion preserve canonical equality.
- Storage counts and extraction product counts include quadratic work.
- State loading enforces tier identity and parser resource limits.
- All mechanism controls preserve the same target.
- Indexed fresh uses the same planner without an original model.
- Corrupt regenerated contributions leave the original state unchanged.

These are software correctness fixtures.
They provide no real-model acceptance, runtime, or NLP quality evidence.

## Optional interval portfolio

The constructor also accepts `verifier_policy="spectral_or_interval"`.
The default remains `spectral`.
This planner option applies to both response tiers.
It leaves the service manifest and canonical state unchanged.
Run configuration must bind the selected policy separately.

The service first executes its existing spectral certificate.
Every existing spectral acceptance returns immediately.
After rejection, the optional route converts signed covariance bounds into entrywise intervals.
Diagonal errors retain their asymmetric endpoints.
Off-diagonal error magnitudes use half the sum of the signed bounds.
The interval verifier uses the complete target's fixed ridge floor.
It can also run when the relative spectral lower scale is nonpositive.

The route reuses the existing proposal candidate when available.
Otherwise, it quantizes the PSD proposal and charges that additional factorization.
It certifies every decision before installing the candidate.
Rejection returns to the existing group replay planner.
Inconsistent interval evidence aborts instead of proving a vacuous certificate.

The ledger separates interval factorization, decision checks, candidate generation, and binding hash bytes.
Telemetry records interval attempts, accepted decisions, and rejected cells.
An accepted stage uses route `interval_transport_certificate`.
The extra verifier can increase total cost despite better certificate coverage.
No wall-time dominance is claimed.
