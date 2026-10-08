# Independent numerical review for revision 30

This review concerns the unchanged exact calibration target.
It does not establish empirical speed or broad model quality.
The rational fixtures are software checks, not synthetic empirical datasets.

## Exact primal identity

Let the feature matrix be \(X\in\mathbb R^{d\times T}\).
Let \(K=XX^T\), \(\beta=\lambda\nu>0\), and \(S_i=\{i,\ldots,d-1\}\).
The declared normalization \(\nu\) remains fixed during deletion.

The token coefficient is

\[
c_i=(\beta I_T+X_{S_i}^TX_{S_i})^{-1}x_i^T.
\]

Define \(B_i=\beta I+K_{S_i,S_i}\) and \(y_i=B_i^{-1}e_1\).
The push-through identity gives

\[
c_i=X_{S_i}^Ty_i,
\qquad
a_{hi}=x_hc_i=K_{h,S_i}y_i.
\]

Thus the exact decision remains

\[
v_{ri}=w_{ri}+\sum_{h<i}(w_{rh}-q_{rh})a_{hi}.
\]

This changes the computational dimension without changing the mathematical target.
It preserves coordinate order, fixed grids, saturation, and lower-code ties.
No feature rank assumption is needed.

The suffix Gram uses the same realized feature matrix as the cross terms.
An interval hull can contain indefinite matrices without invalidating this proof.
Every realized matrix still satisfies \(B_i\succeq\beta I\).
The certificate cannot apply that property to arbitrary unrelated interval matrices.

## A tighter residual certificate

Let \(\widehat y_i\) be any finite numerical proposal.
Set \(r_i=e_1-B_i\widehat y_i\).
Then

\[
a_{hi}-K_{h,S_i}\widehat y_i
=x_hX_{S_i}^TB_i^{-1}r_i.
\]

For every singular value \(\sigma\ge0\),

\[
\frac{\sigma}{\beta+\sigma^2}\le\frac{1}{2\sqrt\beta}.
\]

Therefore

\[
\boxed{
|a_{hi}-K_{h,S_i}\widehat y_i|^2
\le \frac{K_{hh}}{4\beta}\|r_i\|_2^2.
}
\]

This bound uses a Gram diagonal rather than an entire cross-row norm.
It can improve the earlier bound \(\|K_{h,S_i}\|_2^2\|r_i\|_2^2/\beta^2\).
Neither bound uniformly dominates the other.
Their minimum remains a valid bound when both computations round outward.

The factor \(1/4\) is sharp under these premises.
Take \(\beta=1\), \(x_h=2\), and the one-entry suffix \(X_{S_i}=1\).
Then \(K_{h,S_i}B_i^{-1}=1\) and \(K_{hh}/(4\beta)=1\).

For feature boxes, bound \(K_{hh}\) and \(\|r_i\|_2^2\) uniformly.
The product of their upper bounds gives a valid uniform certificate.
Ignoring their dependence can reduce acceptance but cannot create false acceptance.

This is an elementary residual bound, not a priority claim.
It addresses certificate tightness; it does not remove all conditioning or margin problems.

## Reverse Schur recurrence

Let \(B=\beta I+K\), with \(J_i=\{i+1,\ldots,d-1\}\).
Define the remaining Schur matrix

\[
M_i=B_{0:i,0:i}-B_{0:i,J_i}B_{J_i,J_i}^{-1}B_{J_i,0:i}.
\]

For an empty \(J_i\), the second term is zero.
The exact coefficient satisfies

\[
a_{hi}=\frac{M_i[h,i]}{M_i[i,i]},\quad h<i.
\]

The next matrix follows from

\[
M_{i-1}=M_i[0:i-1,0:i-1]
-\frac{M_i[0:i-1,i]M_i[i,0:i-1]}{M_i[i,i]}.
\]

The existing exact reference implements this recurrence through reverse LDL factors.
Its factor entry \(L_{ih}\) equals \(a_{hi}\).
The new independent fixtures compare both forms with exact token solves.

Numerical Schur updates supply proposals only.
A positive floating pivot does not verify the exact coefficient.
Residual checks must still prove every accepted interval.
Reverse block-inverse proposals also satisfy this requirement when independently verified.

One shared reverse recurrence costs \(O(d^3)\) arithmetic operations.
Independent suffix factorizations would cost \(O(d^4)\).
That repeated factorization is unnecessary.

## Arithmetic conditions

1. Binary64 inputs denote their exact dyadic values.
2. Elementary operations require round-to-nearest arithmetic and gradual underflow.
3. Each interval product, sum, division, and square-root bound must round outward.
4. BLAS products and inverse updates supply proposals only.
5. Grid boundaries come from the declared exact dyadic row grid.
6. A cell excludes its lower boundary and includes its upper boundary.
7. Nonfinite values or unresolved cells cause refusal before model output.
8. Caller-owned input arrays must remain unchanged during verification.

A square-root proposal needs a verified outward adjustment.
For an upper root \(u\), a downward-rounded product must prove \(u^2\ge z\).
For \(z=0\), the exact upper root is zero.

Directly squaring a tiny root can underflow during verification.
Revision 30 first writes \(z=\widetilde z2^e\), with even \(e\) and \(\widetilde z\in[1/2,2)\).
It verifies the normalized root and then scales by \(2^{e/2}\).
For positive binary64 inputs, \(-1074\le e\le1024\).
The final root remains normal and finite, so this power-of-two scaling is exact.
This change removes a safe but unnecessary refusal at subnormal squared radii.

A strict cell test must not reject a structural zero merely from artificial interval inflation.
Unresolved nonstructural ties can still require refusal.

## Structural cost

Directed feature-column outer products build the Gram enclosure in \(O(d^2T)\) work.
Shared suffix proposals and residual checks require \(O(d^3)\) work.
All row decisions require \(O(md^2)\) work for a fixed grid size.
The complete structural bound is

\[
O(d^2T+d^3+md^2).
\]

Workspace is \(O(d^2+dT+md)\) before service-level copies and stored state.
This removes the primal route's \(T^2\) numerical arrays.
It does not remove \(d^2T\) work or storage for source features.
An MLP projection with large \(d\) can remain expensive.

Work proxies and workspace estimates are admission policies.
They are not elapsed-time predictions or certified peak-memory bounds.
Both repair and reconstruction must have access to the same numerical backend.

## Requested-coordinate preconditioning

Sparse retries must preserve the original coefficient proposal at each coordinate.
An intersection of two proved radii remains valid only for that same proposal.
The preconditioning matrix itself can change because the residual check verifies its effect.

A reverse sweep costs \(O(dT^2)\).
Verifying only \(k\) requested dense preconditioners costs \(O(kT^3)\).
Multiple rounds must charge each repeated sweep and every attempted check.
The resulting per-round bound is \(O(dT^2+kT^3)\).

The implementation must reject an exhausted budget before expensive work starts.
It must not call an eager all-coordinate fallback after that rejection.
Already verified full rows can remain valid during retries.
Partially verified rows cannot enter the output model.

## Review status

The primal and sparse implementations passed the independent source review.
The initial combined numerical suite passed 33 tests in a reported 0.739 seconds.
Those checks comprise 14 primal tests, 15 sparse tests, and four independent numerical tests.
The primal author subsequently passed 16 tests, adding normalization and subnormal Gram checks.
The final reviewed test files therefore contain 35 tests across these three suites.

The independent tests verify these properties.

- Primal coefficients equal token coefficients and reverse-Schur factors over exact rational fixtures.
- The tighter residual bound contains the exact error and has a sharp constant.
- Both arithmetic backends enclose all 64 corners of a correlated three-by-two feature box.
- Deliberately wrong suffix proposals remain harmless after residual verification.

The source review checked these implementation paths.

| Path | Reviewed condition |
|---|---|
| Primal Gram | Directed products, sums, symmetric entries, and nonnegative realized diagonals |
| Primal coefficients | Realized ridge floor, directed residuals, both error bounds, and verified roots |
| Primal rows | Original fixed grids, original coordinate order, complete-row acceptance, and lower-code ties |
| Sparse retries | Original proposals, paired radii, requested coordinates, and bounded repeated sweeps |
| Resource refusal | No model output and no automatic eager fallback |

The adaptive adapter received two integration corrections during review.
It now preserves the ordinary binary64 input contract and aligns arrays before native token calls.
The primal assessment returns refusal details without preventing assessment of the token route.

The scaling worker compares identical first-stage features, weights, grids, and normalization.
Its result concerns a component and cannot establish complete repair speed.
An oversized row slice must be rejected before reporting its requested row count.

These reviewed numerical source versions have the following SHA256 values.

| File | SHA256 |
|---|---|
| `src/primal_certificate_v30.py` | `d5510446c7bd4e486fe7940553e139b0c314c4bf820af14a8bff311538d6bb80` |
| `src/sparse_box_certificate_v30.py` | `0d44c381f0abcbfab6a0de46836c3b33a419371b773b5befec71101f648008b7` |
| `tests/test_primal_certificate_v30.py` | `0023abee25d9e1d5230945bc5be16d3b88b3311a3eb4b49cd8dbffa1cab0b4f3` |
| `tests/test_sparse_box_certificate_v30.py` | `e76e6a6c87b1b802b7a5db16bccab6c64447a2a0d4b4578a1437ce65ad0605b2` |
| `tests/test_numerical_review_v30.py` | `ca6c83e31226d2ab882d85ac992060d55351379e146a8285335fa0bb4527a112` |

The primal backend closes the missing-implementation blocker from revision 29.
It still needs real-data acceptance and complete cost evidence.
The work bound alone cannot prove a useful runtime or broad practical scale.
No empirical run occurred during this review.

## Native token integration review

The later point optimization replaces coefficient verification through an explicit module interface.
It preserves the existing native row kernel and bounded selected-row fallback.
Repair and reconstruction receive the same implementation.

The review confirmed these conditions.

- Input arrays retain their original binary64 values.
- Weights, features, and immutable coefficient arrays satisfy native alignment requirements.
- The row verifier receives each coefficient with its matching error bound.
- The original coordinate order, row grids, and lower-code tie rule remain unchanged.
- Failed native rows receive the established complete-row fallback.
- Adaptive dispatch disables exact rational fallback and caps numerical refinement coordinates.
- Admission reserves fallback work before selecting the route.
- Route selection uses a structural work proxy, not a claimed timing crossover.
- Both native compilations and repeated fallback work remain inside complete transaction costs.

The wrapper's nested coefficient clock includes coefficient compilation when required.
The combined compilation field also reports that same event.
These diagnostic fields must not be summed as independent costs.

No arithmetic or dispatch blocker remained after the alignment correction.
This review did not run an empirical worker.

| File | Reviewed SHA256 |
|---|---|
| `src/native_token_coefficients_v30.py` | `807cb9007c1948a2243499996400f22720d12c8ca87c45460e6ab23ebf8669bc` |
| `src/fast_token_quantizer_v30.py` | `d48456a6164f1fd07c5dbc9f130f38628085945985138ca6bb7de846892fdecf` |
| `src/adaptive_calibration_v30.py` | `88cfa106918f65ca77052f633202240e231751b76be681daf9ad0b2bd89a543f` |
