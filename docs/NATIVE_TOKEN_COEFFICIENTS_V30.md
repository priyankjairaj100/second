# Native token coefficient verification

This module accelerates the existing exact point certificate.
It preserves the mathematical target and all retained feature columns.
It does not introduce a new unlearning method.

The scaling diagnostic identified Python coefficient checks as a substantial component cost.
This implementation moves their directed array loops into strict native code.
Both repair and reconstruction can use the same implementation.
No empirical speed result follows from the software tests below.

## Interface

`native_token_coefficient_enclosures(features, beta, budget=...)` returns `NativeCoefficientResult`.

- `features` is an ordinary finite binary64 matrix with shape \(d\times T\).
- Each feature denotes its exact represented dyadic value.
- `beta` is a positive exact integer or fraction.
- The caller sets \(\beta=\lambda\nu\), using the fixed target normalization.
- The caller must keep input arrays unchanged during verification.

The result contains coefficient proposals and squared Euclidean error bounds.
It also contains dimensions, resource estimates, nested clocks, and native build identities.
The returned numerical arrays have immutable byte owners.

No global function replacement or mutable monkeypatch connects this implementation to a solver.
Callers must use its explicit interface.
Historical numerical modules remain unchanged.

## Unchanged coefficient target

For coordinate \(i\), let \(X_{S_i}\) contain rows \(i,\ldots,d-1\).
The exact coefficient is

\[
c_i=(\beta I_T+X_{S_i}^TX_{S_i})^{-1}x_i^T.
\]

The implementation supplies a numerical proposal \(\widehat c_i\).
It proves

\[
\|c_i-\widehat c_i\|_2^2\le E_i.
\]

The existing ball or interval row verifier can consume this evidence directly.
The proposal itself does not certify a quantized decision.

## Directed native recurrence

Initialize directed bounds for \(G=\beta I_T\).
Visit input coordinates in descending order.
For each coordinate, add a directed enclosure of \(x_i^Tx_i\).
The native loop updates the symmetric Gram entries together.
It preserves the reference recurrence's suffix order.

NumPy constructs the same nominal Sherman–Morrison proposal as the previous point implementation.
These matrix products remain untrusted.
The native loop then encloses

\[
r_i=x_i^T-G_i\widehat c_i.
\]

Every realized suffix matrix satisfies \(G_i\succeq\beta I\).
Therefore

\[
\|c_i-\widehat c_i\|_2^2
\le \frac{\|r_i\|_2^2}{\beta^2}.
\]

Native code rounds residual products, sums, squares, and divisions outward.
The denominator uses a positive downward bound for \(\beta^2\).
An underflowed denominator causes refusal.
Nonfinite proposals, Gram entries, residual bounds, or errors also cause refusal.

The runtime requires IEEE binary64 elementary operations with round-to-nearest and gradual underflow.
The compiler disables contraction and fast-math transformations.
The native kernel checks the active rounding mode and subnormal behavior.

The native addition deliberately omits an extra exact-cancellation shortcut.
This matches the current point reference's operation order.
Accepted certificates remain valid even when different numerical proposals change their interval widths.
Bitwise equality of proposals across arbitrary BLAS implementations is not required.

## Limits and costs

The implementation currently accepts point features only.
It does not verify a positive-width feature box.
It has no exact rational fallback, preconditioned fallback, or neural replay path.

Its asymptotic coefficient work remains \(O(dT^2)\).
Its workspace remains \(O(T^2+dT)\).
The optimization removes Python loop overhead and large residual-product temporaries.
It does not remove token-space quadratic scaling.
The primal route remains necessary when the feature dimension is more suitable.

`NativeCoefficientBudget` limits a structural work proxy and an explicit array allowance.
The work proxy is \(dT^2+dT+T^2\).
The array allowance is

\[
8(24T^2+4dT+16T+4d)\text{ bytes}.
\]

This allowance covers coefficient arrays, nominal updates, alignment copies, and conservative numerical temporaries.
It excludes compiler memory, allocator overhead, caller residency, and opaque BLAS workspace.
It is an engineering admission rule, not a certified process memory bound.
Rejection occurs before Gram allocation or native compilation.

Reported clocks are nested.
`nominal_elapsed_ns` covers proposal work and its finite checks.
`native_elapsed_ns` covers native Gram and residual calls.
`compile_elapsed_ns` records compilation within the current call.
`total_elapsed_ns` includes the complete coefficient routine through immutable evidence construction.
These clocks must not be added again to a complete transaction clock.

## Verification

Ten focused software tests passed in a reported 0.214 seconds.
An independent agent reviewed the native arithmetic and reran all ten tests successfully.
That review found no soundness blocker.
They cover these conditions.

- Exact agreement with the current directed coefficient reference on several finite fixtures.
- Exact rational containment of each true suffix coefficient.
- Integration with the existing row certificate and exact quantizer oracle.
- Empty-token behavior without native compilation.
- Unaligned, noncontiguous, and read-only inputs.
- Subnormal products and exact rational containment near underflow.
- Overflow, tiny ridge products, invalid inputs, and runtime refusal.
- Admission before expensive work and immutable result arrays.
- Native source, binary, and wrapper identities.

These fixtures do not constitute synthetic empirical datasets.
No model evaluation or empirical timing run occurred during implementation.
Complete service measurements must include compilation, feature loading, coefficient work, row decisions, and output.
