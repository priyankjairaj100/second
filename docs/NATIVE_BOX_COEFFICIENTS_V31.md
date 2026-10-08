# Native universal box coefficients, revision 31

The new backend moves directed Gram and residual loops into strict C.
It preserves the universal feature-box certificate and the original floating proposal schedule.
It does not replace uncertain features with their midpoint.

The implementation changes no V30 numerical source or frozen campaign snapshot.
V30 timings and numerical refusals remain evidence about their original implementation.
V31 requires a separate registered empirical comparison.

## Public interfaces

```python
from src.native_box_coefficients_v31 import (
    NativeBoxCoefficientBudget,
    assess_native_box_coefficients,
    native_box_coefficient_enclosures,
)

assessment = assess_native_box_coefficients(width, tokens, budget=budget)
evidence = native_box_coefficient_enclosures(lower, upper, beta, budget=budget)
proposals = evidence.coefficients
error_squares = evidence.errors
```

Inputs are ordinary NumPy binary64 matrices.
Their endpoints denote exact dyadic values.
The scalar `beta` is an exact positive integer or rational.
It equals ridge times the original normalization.
Caller inputs must remain unchanged during execution.

Both output arrays have immutable byte owners.
The result records compilation, nominal proposal, native verification, and total durations.
It also records source, binary, wrapper, compiler, and compiler-flag identities.
Empty token sets produce empty proposals and zero error squares without compilation.
They still receive a positive structural work charge.

The certificate integration is explicit:

```python
from src.sparse_box_certificate_v31 import (
    SparseCertificateBudget,
    certify_sparse_ball_dyadic_box,
)

result = certify_sparse_ball_dyadic_box(
    weights, lower, upper, scales,
    ridge=ridge,
    normalization=normalization,
    budget=sparse_budget,
    coefficient_backend="native",  # or the explicit "reference" control
)
```

`SparseCertificateBudget` is the exact V30 class, not a replacement class.
The default coefficient backend is `native`.
The `reference` option calls the existing Python coefficient builder.
Neither route replaces a global function or accepts caller-supplied coefficient evidence.
There is no automatic retry using another coefficient backend.

## Universal coefficient theorem

Let \(Z\in\mathbb R^{d\times T}\) lie inside the supplied endpoint box.
Write its coordinate rows as \(z_i\in\mathbb R^T\).
For the suffix beginning at coordinate \(i\), define

\[
B_i(Z)=\beta I_T+\sum_{h=i}^{d-1}z_hz_h^\top,
\qquad a_i(Z)=B_i(Z)^{-1}z_i,
\qquad \beta>0.
\]

The implementation returns one floating proposal \(p_i\) and one nonnegative floating bound \(E_i\).
The intended guarantee is

\[
\|a_i(Z)-p_i\|_2^2\le E_i
\quad\text{for every }Z\text{ inside the complete supplied box.}
\]

The proposal can be inaccurate without invalidating the certificate.
Only the directed residual proof determines its accepted error bound.

### Gram enclosure

The reverse sweep begins with an enclosure of the exact diagonal matrix \(\beta I_T\).
Each suffix update adds an enclosure of \(z_i z_i^\top\).
Off-diagonal entries use all four endpoint products.

Diagonal entries retain the shared-variable square relation.
For an interval \([\ell,u]\), its square lower bound is zero when \(\ell\le0\le u\).
Otherwise it is the smaller endpoint square, rounded outward.
The upper bound is the larger endpoint square, rounded outward.
An exact zero interval keeps an exact zero square.

Consequently, every accepted Gram enclosure satisfies

\[
(G_i^-)_{jk}\le (B_i(Z))_{jk}\le (G_i^+)_{jk}
\quad\text{for every admissible }Z.
\]

The proof permits dependencies between different Gram entries.
Entrywise enclosure can lose those dependencies conservatively.
It never treats their intervals as evidence of independent source variables.

### Residual certificate

For fixed \(p_i\), directed interval arithmetic encloses

\[
r_i(Z)=z_i-B_i(Z)p_i.
\]

Each component bound uses the complete right-hand-side interval and the complete Gram enclosure.
The verifier computes an outward bound \(R_i^2\ge\|r_i(Z)\|_2^2\).
Let \(b_2>0\) be its proved binary64 lower bound on \(\beta^2\).
The final division rounds upward:

\[
E_i\ge R_i^2/b_2.
\]

Since \(B_i(Z)\succeq\beta I_T\),

\[
\|a_i(Z)-p_i\|_2^2
=\|B_i(Z)^{-1}r_i(Z)\|_2^2
\le\frac{\|r_i(Z)\|_2^2}{\beta^2}
\le\frac{R_i^2}{b_2}
\le E_i.
\]

This proves the universal guarantee without trusting the nominal inverse.
If a positive representable denominator bound cannot be established, the implementation refuses.
Nonfinite Gram, residual, norm, or final error values also cause refusal.

## Reference operation schedule

The native Gram update runs before constructing that coordinate's nominal proposal.
This preserves the original control order.
The update visits suffix coordinates in descending order.
Independent symmetric entries can share one computed result.

The coefficient proposal retains the original midpoint expression:

\[
m_i=\operatorname{RN}\!\left(\operatorname{RN}(\ell_i/2)+\operatorname{RN}(u_i/2)\right),
\]

with the addition separately rounded by the existing NumPy operation.
The inverse-vector product and Sherman–Morrison proposal remain unchanged NumPy computations.
They are untrusted intermediate values.

If the nominal denominator, proposal, or updated inverse is invalid, both inverse and proposal become zero.
This is the existing bounded zero-proposal policy.
The zero proposal still requires a complete universal residual certificate.
It is not an exact coefficient or a point-feature fallback.

Within each residual component, matrix-vector terms enter in ascending token order.
Squared residual magnitudes also enter the final sum in ascending token order.
The native interval addition deliberately omits the row kernel's extra cancellation shortcut.
It matches the reference coefficient builder's zero-addend behavior.

The compiler disables fast math and contraction.
Separate scalar operations preserve each rounding boundary.
Runtime checks require binary64, nearest rounding, and gradual underflow.
Callers must not change the floating-point environment during execution.
No BLAS result constitutes certificate evidence without the residual proof.

Signed zeros, subnormal products, crossing-zero intervals, and overflow refusal have explicit software fixtures.
Accepted proposal and error encodings match the reference on the tested completion domain.
No claim of identical exception ordering or resource behavior is required for soundness.

## Bounded integration

The helper's declared structural work proxy is

\[
W_{\mathrm{coeff}}=dT^2+dT+d.
\]

Its dense-array allowance is

\[
M_{\mathrm{coeff}}=8(28T^2+8dT+24T+8d)\text{ bytes}.
\]

The allowance charges endpoint inputs, alignment copies, inverse temporaries, Gram bounds, proposals, and immutable outputs.
It does not bound compiler memory, library workspaces, process RSS, or elapsed time.
Independent process limits remain necessary.

The sparse wrapper already reserves

\[
W_0=dT^2+md(2T+b+1)+dT+m2^b,
\]

where \(m\ge1\) is the number of weight rows and \(b\) is the model bitwidth.
Thus \(W_{\mathrm{coeff}}\le W_0\) for supported nonempty weights.
The helper receives the same total work ceiling but adds no second reservation.
Its executed schedule remains inside the already-reserved initial phase.

The existing sparse dense-array allowance dominates the helper's allowance for supported shapes.
The wrapper still checks its complete allowance before numerical work.
The helper independently checks its own allowance before value scans or compilation.
This avoids double charging while preserving an explicit standalone API contract.

All requested-coordinate refinement remains unchanged V30 code.
It retains its original coordinate, round, work, and workspace limits.
Its proposals remain the same checked proposals used by the native initial certificate.
The optional stronger radii are intersected around those unchanged centers.

No factor compression precision enters the new helper.
Forty-bit and forty-eight-bit descriptors can both supply binary64 endpoint boxes.
Different descriptor widths require separately registered empirical plans.
The exact model grid and lower-code midpoint rule remain unchanged.

## Provenance, alignment, and failure receipts

C receives only contiguous, correctly aligned binary64 inputs.
The sparse wrapper explicitly aligns immutable proposal evidence before passing it to legacy row verifiers.
Those verifiers retain their own alignment checks.
Caller arrays are not modified.

Successful sparse results include the coefficient backend and its complete build evidence.
Compilation contributes to the complete compilation diagnostic.
Coefficient time contains its own nested compilation and verification work.
These nested clocks must not be added as disjoint costs.

Numerical failures preserve coordinate progress, attempted native work, and available compilation evidence.
The wrapper preserves these nested receipts alongside its sparse reservations and failed-row evidence.
No failed coefficient or row pass returns a partial model.
There is no unbounded rational solve or automatic replay inside this backend.

## Verification and limits

Nineteen focused fixtures passed in a reported 0.711 seconds.
That duration is software test output, not an empirical benchmark.

```bash
python -m unittest tests.test_native_box_coefficients_v31 tests.test_sparse_box_certificate_v31 -q
```

The fixtures cover these contracts:

- Bitwise proposal and error equality for point and uncertain boxes.
- Every intermediate directed Gram update against the Python reference.
- Exact rational corner coefficients inside the returned universal error balls.
- Diagonal square correlation, signed zeros, and subnormal arithmetic.
- Invalid nominal inverses followed by verified zero proposals.
- Unaligned, noncontiguous, and read-only inputs with immutable outputs.
- Resource refusal before construction and compilation.
- Numerical overflow, tiny-ridge refusal, and compilation failure receipts.
- Identical complete quantizer codes at exact rational corners.
- Unchanged requested-coordinate refinement and structural reservations.
- Refusal when a box contains genuinely different quantizer outputs.

The optimization preserves certificate strength on matching numerical evidence.
It cannot resolve a box whose exact outputs differ.
It also cannot remove the cost of retained feature replay after certificate refusal.
Requested-coordinate preconditioning remains a possible Python bottleneck.
Complete-model speed and useful acceptance remain empirical questions.
