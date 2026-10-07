# Revision 19: affine bounds without retained dot products

Date: 8 October 2026, Asia/Calcutta.
Status: implemented and checked on software fixtures.
No new empirical worker ran.
This is one transport component, not a complete transformer provider.

## Interface and work

`prepare_affine_anchor(X0, W0, b)` executes the declared finite affine schedule once.
It stores the exact anchor output and scalar maxima for each coordinate.
The summaries contain input, rounded product, and rounded accumulator magnitudes.
The anchor output has immutable byte-backed storage.
Preparation binds the anchor matrix and fixed bias with hashes.
The caller must ensure this preparation belongs to a calibration-independent anchor execution.
The function alone does not establish that condition.

`prepare_affine_change(W0, W)` scans two matrices once.
It produces column bounds for target magnitudes and matrix changes.
The same change object can serve every retained record with that anchor matrix.
This shared scan costs O(pd), where W has p rows and d columns.
It performs no token-dependent dot products.

`affine_error_bound(anchor, change, bias, delta)` propagates an input error bound.
Its required premise is |X-X0| <= delta at every input entry.
The function reads O(d) scalar summaries and scans the fixed bias.
It does not read X or X0.
It returns an exact rational upper bound on every output difference.
Rational bit complexity can grow with depth; the operation count is not a wall-time guarantee.

`enclose_affine_output(anchor, error)` materializes outward binary64 endpoints around the stored output.
This costs O(np) for n tokens.
It does not execute retained dot products.
Endpoint conversion uses exact rational comparisons and directed corrections.
A nonrepresentable finite enclosure causes rejection.

All prepared objects require trusted provenance and unchanged caller inputs during preparation.
Hashes detect mismatched inputs; they do not authenticate hostile summary objects.
No function here changes persistent model or state semantics.

## Finite arithmetic proof

Let u=2^-53 and eta=2^-1074.
For a finite elementary operation result y, use

\[
|RN(y)-y|\le u|y|+\eta.
\]

Suppose real anchor result y0 has |y0| <= M.
Suppose its proposed counterpart satisfies |y-y0| <= D.
Then

\[
|RN(y)-RN(y0)|
\le D+u(2M+D)+2\eta.
\tag{1}
\]

If D=0, the numerical results are identical and the returned difference bound is zero.
This statement concerns numerical values, not signed-zero bit identity.
The implementation rejects bounds that cannot exclude overflow.
Its runtime checks retain the existing round-to-nearest and gradual-underflow requirements.

At coordinate i, the real product difference satisfies

\[
|w'_i x'_i-w_i x_i|
\le |w'_i|\delta+|w'_i-w_i|M_{x_i}.
\tag{2}
\]

Preparation stores the maximum magnitude P_i of the rounded anchor product.
The real anchor product magnitude therefore satisfies

\[
|w_i x_i|\le\frac{P_i+\eta}{1-u}.
\tag{3}
\]

Use equations (2) and (3) in equation (1) to bound the rounded product difference.
Let A_i bound the anchor accumulator magnitude before coordinate i.
If E_i bounds its difference, the real addition difference is at most E_i plus the product difference bound.
The real anchor addition magnitude is at most A_i+P_i.
Equation (1) therefore bounds the next rounded accumulator difference.
Induction through the declared coordinate order proves the final accumulator bound.
Apply the same rule once more for the unchanged bias addition.

All bound arithmetic uses exact rational operations.
The stored maxima describe finite values produced by separate multiply and add operations.
The code does not substitute a BLAS reduction or fused multiply-add schedule.

For the shared matrix scan, rounded subtraction is monotone.
One upward adjacent binary64 value encloses the magnitude of each exact subtraction result.
Taking the maximum before that upward step preserves the enclosure.
A rounded zero difference between distinct finite binary64 values cannot arise below the minimum subnormal spacing.
Thus, the implementation safely preserves zero bounds when the matrices agree numerically.
Nonfinite subtraction results cause rejection.

## Composition requirement

Suppose an upstream certificate proves the required input error bound.
Then the returned affine box contains every corresponding finite affine output.
This implication can connect to the direct dyadic box certificate from revision 18.

A complete transformer proof must also cover its actual normalization, attention, activation, and residual schedules.
The affine component does not provide those bounds.
It also does not construct calibration-independent anchor traces or their canonical persistent state.
These remain implementation requirements before any avoidance claim.

Even a valid complete provider can give boxes too wide for quantizer certification.
This revision proves no useful acceptance rate or full-model repair speedup.
The preparation cost and shared matrix scans must enter all future timing comparisons.
The full comparison must retain equally optimized reconstruction controls.

## Validation

The focused run passed 15 tests.
Five tests cover this component; ten cover the existing dyadic certificate and refinement components.
The affine checks include 45 perturbed input/matrix cases across three widths and three magnitude scales.
They compare bounds against a separate scalar finite schedule.
Other checks cover exact zero-change behavior, cancellation, subnormals, matrix differences, binding failures, and overflow rejection.
Software fixtures do not replace real-data experiments or independent mathematical review.

The original worker allowance still has 291 CPU seconds.
No new quality, confirmation, or repair timing result was produced.
The latest complete-model evidence remains revision 17.
