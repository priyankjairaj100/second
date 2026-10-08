# Universal boxes with the existing native ball kernel

This wrapper reuses the unchanged C source in `src/native_ball_quantizer.py`.
It changes the supplied bounds, not the numerical target.
It has no empirical speed claim.

`certify_ball_dyadic_box` accepts the existing dyadic certificate arguments.
Its optional `allow_python_fallback` flag defaults to true.
Successful results certify the complete inclusive feature box.
Source containment remains an independent caller obligation.

## Feature uncertainty

Let \(C\) be a finite binary64 center within the feature box.
The implementation halves endpoints before addition, then clamps the result into the box.
This avoids midpoint overflow and handles subnormal rounding.

It constructs directed bounds

\[
R_{hk}\ge\max(|X^-_{hk}-C_{hk}|,|X^+_{hk}-C_{hk}|).
\]

These use actual center differences.
They do not assume that a rounded half-width encloses either endpoint.
Singleton feature entries receive zero radius.

For each input coordinate, define

\[
D_h\ge\max_r\max_{q\in\mathcal G_r}|w_{rh}-q|.
\]

Absolute distance is maximized at a grid endpoint.
Directed subtraction encloses both endpoint discrepancies for every row.
The implementation takes their maximum.

For each retained prefix, compute

\[
E_{ik}\ge\sum_{h<i}D_hR_{hk},
\qquad E_i^{\max}=\max_k E_{ik}.
\]

Directed products and additions bound every sum.
Exact zero factors remain zero.
Nonzero subnormal products receive outward rounding.
Nonfinite feature bounds reject the attempt.

## Augmenting the existing accumulator proof

Fix any feature matrix \(X\) within the box.
Fix one row and any accepted prefix of grid codes.
The exact accumulators satisfy

\[
S_{ik}(X,q)-S_{ik}(C,q)
=\sum_{h<i}(w_h-q_h)(X_{hk}-C_{hk}).
\]

Consequently,

\[
|S_{ik}(X,q)-S_{ik}(C,q)|\le E_{ik}.
\]

The reviewed native proof supplies

\[
|S_{ik}(C,q)-\widehat s_{ik}|
\le c_i\widehat A_{ik}+U_i^0.
\]

Supply the unchanged kernel with

\[
U_i\ge U_i^0+E_i^{\max}.
\]

The triangle inequality proves

\[
\boxed{|S_{ik}(X,q)-\widehat s_{ik}|
\le c_i\widehat A_{ik}+U_i.}
\]

The unchanged kernel already uses this uniform bound in both required places.
Its proposal contribution includes \(U_i\|p_i\|_1\).
Its coefficient contribution includes the norm allowance \(TU_i\).
Thus both contributions cover feature uncertainty.

This proof requires no independence between coefficients, features, and accepted codes.
The discrepancy bound covers every possible accepted grid code.
Induction establishes the accepted prefix for each matrix in the box.

The original binary64 runtime assumptions remain required.
The wrapper enforces width and rank at most \(2^{20}\).
Every native double input has aligned contiguous storage.
The original native runtime checks execute without modification.

## Coefficient bounds and rejection

The first pass uses the existing universal ridge coefficient certificate.
Its proposals satisfy

\[
\|c_i(X)-p_i\|_2^2\le B_i
\quad\text{for every }X\text{ in the box}.
\]

An exact rational check verifies the supplied square-root radius.
Native rejection triggers the reviewed preconditioned coefficient construction.
Its component radii yield an additional directed squared norm bound.
The smaller certified squared bound is used for the same proposal.
Invalid component certificates retain the independently valid ridge bound.

Each pass restarts all native rows.
It preserves every repeated cost.
No partially certified model is returned.

If both native passes reject, optional fallback invokes the existing Python universal verifier.
Uncertain boxes never invoke pointwise exact fallback.
Singleton boxes explicitly dispatch to the shared native point solver.

The native ball kernel can reject exact rounding ties because its arithmetic radius is positive.
The Python universal fallback may certify those ties.
Every accepted path retains lower-code ties.

## Receipts

The wrapper reports feature bounds, coefficient bounds, ball bounds, native kernels, fallback, compilation, and complete elapsed time.
Every pass records its policy, failed rows, failure location, and work counters.
Counters include duplicated work.
Rejected calls attach `native_diagnostics` to their exception.

The receipt binds the unchanged native C source and compiled binary.
It also binds the new wrapper source.
Registered source snapshots must bind the imported coefficient and arithmetic modules.
Existing binary caches remain untrusted.

Singleton timing uses one complete point-solver duration.
That duration includes compilation when needed.
Its separately exposed compilation field must not be added twice.

Native passes do not measure per-decision dependence on preconditioning.
The corresponding inherited count remains zero with its measurement flag false.
Python universal fallback reports the existing measured count and sets the flag true.

## Software verification

The tests compare accepted boxes with exact rational quantization at every small-box corner.
They also check interior points and actual ambiguity rejection.
Separate exact tests verify feature radii, grid discrepancies, prefix errors, and augmented accumulator bounds.

Further fixtures cover subnormals, wide finite boxes, ties, aligned copies, and read-only inputs.
They check both coefficient passes, universal fallback, singleton dispatch, input validation, and source bindings.
These are software fixtures, not empirical datasets.
No real calibration experiment ran during implementation.

The global discrepancy bound can be much larger than actual rounding errors.
That conservatism may reduce native acceptance.
The present implementation favors a simple auditable proof.
Any refinement requires its own proof and complete cost comparison.
