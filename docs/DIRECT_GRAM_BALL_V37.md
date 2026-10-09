# Shared ball verification for the pooled-Gram baseline

This revision strengthens a comparator before interpreting its measured loss.
It changes the row verifier, preserving the exact quantization target.
No numerical source from V35 or V36 is modified.
The new adapter is `research_v37/direct_gram_ball.py`.
No empirical result follows from its software fixtures.

## Diagnosis from completed receipts

V36 covers all 2,304 first-stage output rows, each with width 768.
Its retained feature rank is 128.
The original normalization remains 256.

| V36 component | Pooled deletion | Fresh retained Gram | Cached features |
|---|---:|---:|---:|
| Coefficient verification | 10.928831 s | 9.029200 s | 0.522181 s |
| Native row verification | 48.889642 s | 46.623397 s | 0.605546 s |
| Complete component arm | 65.995601 s | 61.257673 s | 1.299832 s |

These values come from `campaigns/pooled_gram_stage_v36/attempt/outputs/completion.json`.
The first two row kernels use the generic interval-box loop.
That loop scans 768 virtual dimensions twice per decision.
The cached-feature comparator uses the faster ball loop at rank 128.
Both coefficient builders execute once per arm, regardless of output-row count.
No repeated coefficient-construction defect was found.

Thus two mechanisms affect the comparison.
The primal representation uses a larger dimension on this workload.
It also uses a slower compatible row-verification kernel.
The latter should be improved before claiming a strong baseline defeat.
This diagnosis does not identify an intrinsic lower bound for pooled-Gram methods.

## Exact recurrence

Let the trusted exact retained Gram be \(K\succeq0\).
Let \(\nu\) be its preserved original normalization.
Set \(\beta=\lambda\nu>0\), with \(\lambda\) the declared ridge.
The quantizer metric is \(H=\lambda I+K/\nu\).

For coordinate \(i\), define \(S_i=\{i,\ldots,d-1\}\).
The unchanged primal identity gives

\[
a_{ih}=K_{h,S_i}(K_{S_i,S_i}+\beta I)^{-1}e_1\quad(h<i),
\qquad a_{ih}=0\quad(h\ge i).
\]

The exact decision input is

\[
v_{ri}=w_{ri}+\sum_{h<i}(w_{rh}-q_{rh})a_{ih}.
\]

The V35 coefficient routine proves componentwise bounds

\[
|a_{ih}-\widehat a_{ih}|\le r_{ih}.
\]

This proof still requires trusted exact accumulation and valid source-subtraction lineage.
Parsing a checksum-valid matrix does not establish this PSD premise.
Neither a positive diagonal nor a floating eigenvalue estimate substitutes for it.

Now supply virtual feature rows \(z_h=e_h\), the rows of \(I_d\).
The generic native accumulator becomes

\[
s_{i,t}=\sum_{h<i}z_{h,t}(w_{rh}-q_{rh})
=\begin{cases}w_{rt}-q_{rt},&t<i,\\0,&t\ge i.\end{cases}
\]

Therefore \(w_{ri}+\widehat a_i^Ts_i\) is precisely the proposed primal decision center.
This substitution does not quantize against an identity covariance.
The kernel consumes coefficients already certified for \(K\).
The identity only expresses their accumulator representation.

## Euclidean coefficient bounds

The adapter computes upward squares and a sequential upward sum:

\[
E_i\ge\sum_h r_{ih}^2.
\]

It uses the unchanged `_norm_squared_upper` implementation.
Zero terms remain exact zero.
Positive underflowed products are rounded upward to enclose the true product.
Overflow or nonfinite bounds cause refusal.

The unchanged `_coefficient_radii` routine proposes \(\rho_i\) using a square root.
Exact rational squaring then verifies \(\rho_i^2\ge E_i\).
Consequently,

\[
\|a_i-\widehat a_i\|_2\le\rho_i.
\]

This converts componentwise evidence into the existing ball kernel's required premise.
It can be looser than the original weighted componentwise bound.
That affects acceptance and runtime, never the accepted target.

## Reused floating arithmetic proof

`docs/NATIVE_BALL_PROOF_V17.md` proves the generic accumulator and decision certificates.
Its argument depends on the coefficient error bound, not its construction method.
Its feature matrix can be the exactly representable identity.
The virtual rank is \(d\), and both dimensions must satisfy \(d\le2^{20}\).

The adapter calls the unchanged `_underflow_bounds(I_d, centers)` routine.
This supplies the required feature-prefix and coefficient absolute-sum bounds.
The same native kernel bounds accumulator error, coefficient error, and rounded dot products.
Its interval must fit inside a single exact dyadic rounding cell.
The lower boundary is excluded; the upper boundary is included.
This preserves lower-code midpoint ties whenever a decision is certified.

All existing runtime premises remain mandatory:

- CPython IEEE binary64, round-to-nearest, and gradual underflow.
- Fixed caller inputs and finite accepted intermediates.
- The original strict compiler flags, including disabled contraction and fast-math.
- No trusted BLAS reduction in the decision certificate.

Native runtime or allocation errors cause immediate failure.
They are not classified as rounding-cell refusals.
Both the coefficient binary and row binary receive separate provenance fields.
The row binary hash identifies the reused ball kernel, not the old interval kernel.

## Bounded fallback

The ball kernel reports every refused row and its first failed coordinate.
Each refused row receives one complete run of the unchanged primal interval verifier.
This fallback shares existing coefficient centers and radii.
It never rebuilds the Gram or coefficients.
It processes complete rows from coordinate zero under the original grid.

Exact midpoint ties can require this fallback.
If any required interval verification fails, the adapter returns no model.
Partially written native buffers are never published as accepted codes.
Successful rows are assembled into immutable output storage.
An optional supplied candidate is compared after certification, without changing acceptance.

## Admission and timing

Admission conservatively includes both possible complete row passes.
It adds identity storage, radius-conversion temporaries, and selected-row copies.
It also includes coexistence of the full output and fallback output.
The structural work proxy is

\[
d^3+2md^2+2m2^b+3d^2.
\]

This expression is not a FLOP, bit-cost, or wall-time bound.
Exact accumulation, caller Gram residency, compilation, and allocator overhead retain separate accounting.
An operating-system memory cap remains necessary.

Results report coefficient, radius setup, ball, fallback, and complete row times separately.
They retain ball attempted decisions and certified-prefix counts.
Fallback counts remain separate because failed prefixes can be repeated.
Complete-call time includes wrapper checks and hash collection.
No empirical speedup, complete-service result, or lifetime advantage is asserted here.

## Software checks

The focused V37 suite contains eleven tests.
It checks independent rational oracles and agreement with the earlier interval implementation.
It also covers original normalization, deletion, exact ties, bounded fallback, and immutable outputs.
Exact rational tests validate the Euclidean radius construction, including underflow.
Other fixtures check admission, kernel provenance, failed proposals, and runtime-error classification.
Synthetic software fixtures are not research datasets.
