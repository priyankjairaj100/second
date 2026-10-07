# Exact token-space solver, revision 12

This note describes implementation work, not empirical evidence.
The solver preserves the declared rational quantizer.
It does not change the finite neural feature program.
All compatible baselines must receive this solver.

## 1. Bottleneck

The dense reference uses width-by-width rational Grams and reverse LDL.
A width of 3,072 requires approximately 4.8 billion Schur updates per factorization.
Each update operates on growing rational numerators and denominators.
The dense decision recurrence adds quadratic work for each output row.
These costs remain after compact checkpoint loading.

Let the input width be $d$.
Let the output width be $p$.
Let the retained token count be $T$.
The token-space method uses $O(dT^2+pdT)$ arithmetic operations before refinement and fallback.
It does not require a $d\times d$ matrix.
This bound helps when $T\ll d$.
It does not establish a wall-time bound.

## 2. Exact identity

Write the exact target metric as

\[
H=\lambda I+\frac1M ZZ^\top,
\qquad Z\in\mathbb Q^{d\times T},\quad\lambda>0,\quad M>0.
\]

$M$ remains the original normalization after deletion.
The rows $z_i^\top$ contain retained finite features.
The order of rows follows the fixed quantization order.
Define

\[
\beta=\lambda M,\qquad
G_i=\beta I+\sum_{j=i}^{d-1}z_jz_j^\top,
\qquad u_i=G_i^{-1}z_i.
\]

Every $G_i$ is positive definite, including rank-deficient feature inputs.
Let $L$ denote the reference reverse-LDL factor.
Then

\[
L_{ih}=u_i^\top z_h\quad(h<i).
\]

For each output row, define the exact accumulator

\[
s_i=\sum_{h<i}z_h(w_h-q_h).
\]

The exact quantizer input is therefore

\[
v_i=w_i+u_i^\top s_i.
\]

Round $v_i$ using the original fixed grid and lower-code tie rule.
Then update $s_{i+1}=s_i+z_i(w_i-q_i)$.
This recurrence produces exactly the dense reference codes.

### Proof

Before reverse elimination at coordinate $i$, write the Schur metric as

\[
\lambda I+Z_{0:i} C_i Z_{0:i}^\top,
\qquad C_i=\lambda G_{i+1}^{-1}.
\]

Its pivot and lower-factor entries satisfy

\[
t_i=\lambda+z_i^\top C_i z_i,
\qquad L_{ih}=\frac{z_i^\top C_i z_h}{t_i}.
\]

The Sherman–Morrison identity gives

\[
\frac{C_i z_i}{t_i}=G_i^{-1}z_i=u_i.
\]

Elimination updates the token matrix by

\[
C_{i-1}=C_i-\frac{C_i z_i z_i^\top C_i}{t_i}.
\]

The initialization is $C_{d-1}=I/M$.
Reverse induction proves the factor identity.
Forward induction proves every rounding decision.

`src/low_rank_exact.py` implements this identity using exact fractions.
Its traces also match reference pivots, inputs, and prefix energies.
Growing integer sizes still affect its cost.

## 3. Residual certificate

The practical implementation first proposes a binary64 coefficient $\widehat u_i$.
The proposal can come from any numerical solver.
The certificate does not assume that the solver is accurate.
Compute the exact residual

\[
r_i=z_i-G_i\widehat u_i.
\]

Because $G_i\succeq\beta I$,

\[
\|u_i-\widehat u_i\|_2
\le\frac{\|r_i\|_2}{\beta}.
\]

Thus

\[
|v_i-(w_i+\widehat u_i^\top s_i)|^2
\le\frac{\|r_i\|_2^2\|s_i\|_2^2}{\beta^2}.
\]

The implementation computes outward binary64 enclosures for every quantity on the right.
It encloses $G_i$ through individual outer products and additions.
It encloses the residual through individual products and additions.
It encloses the accumulator using the already certified codes.
It also encloses $w_i+\widehat u_i^\top s_i$.

Suppose that this final interval is $[a_i,b_i]$.
Suppose that $R_i^2$ bounds the squared displacement.
For a proposed code, let its rounding cell be $(\ell_i,h_i]$.
A sufficient positive-radius test is

\[
a_i>\ell_i,\quad (a_i-\ell_i)^2>R_i^2,
\qquad
b_i<h_i,\quad(h_i-b_i)^2>R_i^2.
\]

The implementation rounds the squared margins downward.
It rounds the squared radius upward.
Infinite cell endpoints require no test.
The zero-radius test preserves the inclusive upper endpoint.
A singleton grid always has an unbounded cell.

These tests prove a code only after all earlier codes are established.
Forward induction therefore proves the complete output.
The module never installs an unresolved approximate decision.

## 4. Arithmetic premise

The certificate assumes IEEE binary64 elementary operations with nearest rounding and gradual underflow.
The public API calls the existing runtime guard.
The guard checks CPython binary64, Linux architecture, `fegetround`, and gradual underflow.
An additional NumPy probe checks subnormal arithmetic.

Every enclosure uses separate NumPy elementary operations and `nextafter`.
The trusted enclosure operations use no BLAS dot products.
The proposal solver may use BLAS.
Residual checks cover all errors from that proposal.
Overflow or a nonfinite enclosure aborts without an output model.
The source and numerical libraries must enter the new runtime binding.

## 5. Refinement and fallback

The initial proposal uses reverse Sherman–Morrison updates.
An unresolved coordinate can request a fresh direct solve.
The direct solve uses a midpoint Gram as its proposal matrix.
The same outward residual check verifies this new proposal.
A failed proposal cannot cancel an already certified decision.

Remaining unresolved rows use an exact rational coefficient solve.
The fallback reconstructs the exact suffix Gram from binary64 feature values.
It then computes the exact decision input for each unresolved row.
It applies the original nearest-grid and lower-code tie rules.

The default caps are 16 refinement coordinates, 16 exact coordinates, and exact rank 64.
These caps are execution limits.
They do not change the quantizer target.
A limit violation raises `LowRankUnresolved` without returning model codes.
Prospective empirical plans must bind these limits before execution.

## 6. Interface

```python
from fractions import Fraction
from src.low_rank_certified import certified_token_codes

result = certified_token_codes(
    weights_float64,              # shape [output width, input width]
    retained_features_float64,    # shape [input width, retained tokens]
    exact_grids,
    ridge=Fraction(1, 100),
    normalization=original_token_count,
    max_exact_rank=64,
    max_exact_coordinates=16,
    max_refinement_coordinates=16,
)
```

Both arrays must already contain finite binary64 values.
Array subclasses are rejected because they can override numerical operations.
The caller must keep both arrays unchanged throughout the call.
Their represented dyadic values define the exact input.
The API does not silently convert rational inputs to binary64.
Every grid code must be exactly representable in binary64.
The returned array contains exact grid codes and is read-only.

`interval_decisions` counts decisions proved without rational fallback.
`exact_decisions` counts decisions resolved by rational fallback.
`exact_coordinates` and `refined_coordinates` identify the affected coordinates.
Neither count measures deletion repair or avoided feature work.

## 7. Storage and integration limits

Working numerical arrays require $O(dT+pT+T^2+pd)$ entries.
The final $pd$ term stores the codes and weights.
Exact fallback adds rational matrices of size $T^2$.
Their integer sizes depend on the input.
A worker limit must bound actual memory and time.

This module solves quantization from supplied retained features.
It does not implement changed-prefix feature certificates.
It does not replace canonical state or reference aggregate storage.
It does not establish byte-identical historical state serialization.
It does not evaluate language-model quality.
These tasks remain with the complete service.

The algorithm can strengthen fresh quantization as much as repair.
Use it in every compatible baseline before claiming a repair speedup.
Token-space identities and residual verification are established numerical techniques.
Their implementation alone does not establish research novelty.

## 8. Software evidence

`tests/test_low_rank_solver_v12.py` contains 11 software tests.
They cover exact factors, traces, codes, rank deficiency, deletion, and fixed normalization.
They also cover ties, saturation, singleton grids, subnormals, overflow, and runtime rejection.
An independent dense oracle checks the exact recurrence.
Exact arithmetic checks the residual coefficient bounds.
A difficult numerical fixture tests refinement and exact fallback.
All 11 tests passed before any empirical pilot used this module.
These fixtures do not count as empirical results.
