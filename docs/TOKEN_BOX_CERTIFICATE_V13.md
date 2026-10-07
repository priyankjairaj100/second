# Token-factor box certificate

Status: implemented and checked with software fixtures on 7 October 2026.
This module proves a quantizer statement from a supplied feature box.
It does not construct that box from a changed transformer prefix.
It does not establish complete repair-state equality or measured repair speed.

## Implemented interface

```python
from src.token_box_certificate import certify_token_box, certify_row_scaled_box

result = certify_token_box(
    weights, feature_lower, feature_upper, fixed_column_grids,
    ridge=ridge, normalization=original_normalization,
    candidate_codes=old_codes,  # Optional; exact equality is required if supplied.
)

result = certify_row_scaled_box(
    weights, feature_lower, feature_upper, base_only_row_exponents,
    bits=4, ridge=ridge, normalization=original_normalization,
    candidate_codes=old_codes,
)
```

All matrices must be ordinary NumPy binary64 arrays.
Bounds must be finite, ordered, and dimensionally consistent.
Every input float denotes its exact dyadic value.
Inputs must remain unchanged throughout the call.
Grids must contain finite, exactly representable codes in increasing order.
The runtime requires round-to-nearest elementary arithmetic and gradual underflow.
The module checks the runtime before it evaluates a certificate.

The result contains immutable codes and diagnostic counts.
It contains no approximate replacement model.
An unresolved decision raises `TokenBoxUnresolved` before any model returns.
A candidate mismatch also raises this exception.

Positive-width boxes never use sampled or pointwise fallback.
Zero-width boxes can use the existing bounded exact point solver.
The two counts distinguish interval decisions from exact point decisions.
The row wrapper checks the canonical base-only scales.
It also checks exact normalization and exact scale restoration.

## Theorem: exact code constancy over a factor box

Let \(W\in\mathbb R^{p\times d}\) be fixed.
Let \(Z\in\mathbb R^{d\times T}\) have coordinatewise bounds \(Z^-\le Z\le Z^+\).
Let \(\lambda>0\) and \(M>0\) be fixed.
The exact target uses

\[
H(Z)=\lambda I_d+\frac{ZZ^\top}{M}.
\]

It uses fixed grids, a fixed coordinate order, and lower-code ties.
Set \(\beta=\lambda M\).
Write \(z_i\) for coordinate row \(i\), viewed as a token vector.
The reverse-LDL identity gives

\[
G_i(Z)=\beta I_T+\sum_{h\ge i}z_hz_h^\top,
\qquad
u_i(Z)=G_i(Z)^{-1}z_i.
\]

For output row \(a\), define the prefix accumulator

\[
s_{a,i}(Z)=\sum_{h<i}z_h\bigl(W_{ah}-q_{ah}\bigr).
\]

Its rounding input is

\[
v_{a,i}(Z)=W_{ai}+u_i(Z)^\top s_{a,i}(Z).
\]

Suppose the procedure below accepts every decision.
Then one returned code matrix equals the exact target for every \(Z\) inside the box.
This includes every exact binary64 feature matrix inside that box.

### 1. Coefficient enclosure

Construct an outward interval matrix containing every \(G_i(Z)\).
Each entry uses interval outer products and interval addition.
Diagonal products use the square of their own interval.
No independence assumption enters these enclosures.

Choose any finite proposal \(c_i\in\mathbb R^T\).
The implementation uses an untrusted midpoint inverse update.
If this proposal fails, the implementation can use zero.
Proposal accuracy affects acceptance, never validity.

Enclose the complete residual set

\[
r_i(Z)=z_i-G_i(Z)c_i.
\]

Let \(R_i\) be an outward upper bound on \(\|r_i(Z)\|_2^2\).
Every true matrix satisfies \(G_i(Z)\succeq\beta I_T\).
Therefore,

\[
\|u_i(Z)-c_i\|_2^2
=\|G_i(Z)^{-1}r_i(Z)\|_2^2
\le\frac{R_i}{\beta^2}
\le E_i.
\]

The implementation divides by a positive lower bound on \(\beta^2\).
It rejects underflow or nonfinite bounds.
An interval matrix need not be positive definite itself.
The exact Gram construction supplies the spectral lower bound.

### 2. Rounding-input enclosure

Assume every earlier decision has one proved code throughout the box.
Then each residual \(W_{ah}-q_{ah}\) is fixed.
Interval arithmetic encloses every \(s_{a,i}(Z)\).
Let \(S_{a,i}\) bound its squared Euclidean norm.
Let \([b^-_{a,i},b^+_{a,i}]\) enclose

\[
W_{ai}+c_i^\top s_{a,i}(Z).
\]

Cauchy–Schwarz gives

\[
v_{a,i}(Z)\in
\left[
b^-_{a,i}-\sqrt{E_i S_{a,i}},
b^+_{a,i}+\sqrt{E_i S_{a,i}}
\right].
\]

The implementation avoids a trusted square-root calculation.
It compares squared cell margins with an outward bound on \(E_i S_{a,i}\).
Every elementary bound operation rounds outward using `nextafter`.

### 3. Cell acceptance and induction

For increasing grid codes \(g_0<\cdots<g_{K-1}\), let

\[
m_k=(g_k+g_{k+1})/2.
\]

The lower-code tie rule gives these cells:

\[
(-\infty,m_0],\quad
(m_{k-1},m_k],\quad
(m_{K-2},+\infty).
\]

The complete input enclosure must fit inside one cell.
The lower finite boundary is strict.
The upper finite boundary permits equality when the proved error radius is zero.
Other equality cases can cause conservative abstention.

At the first coordinate, every accumulator is zero.
Acceptance therefore proves its codes independently of the uncertain features.
The proved codes make the next accumulator valid throughout the box.
Induction establishes every later decision.
Thus, all accepted decisions hold simultaneously for every factor matrix in the box.

The proof does not select a different factor matrix at each accepted decision.
It proves each decision universally over the same complete box.

## Row scales

For a fixed positive row scale \(a\), write \(W_a=aW'_a\).
Use the integer grid for \(W'_a\).
The coefficient \(u_i(Z)\) does not depend on the output row.
Induction gives \(v_{a,i}=av'_{a,i}\) and \(q_{a,i}=aq'_{a,i}\).
Positive scaling preserves order and the lower-code tie rule.
The wrapper checks binary64 roundtrips before it returns restored codes.

## Cost and storage

The positive-width path needs

\[
O(dT^2+pdT)
\]

elementary work, apart from grid searches and validation.
Its arrays need \(O(T^2+dT+pT+pd)\) entries.
It never constructs a \(d\times d\) matrix.
These bounds assume fixed-cost elementary binary64 operations.
The zero-width exact fallback has additional rational arithmetic costs.
The bounds do not include construction of the feature box.

Wide boxes, small ridge values, or small cell margins can cause abstention.
A valid certificate does not guarantee a useful acceptance rate.
It also does not imply a speedup over direct retained-data evaluation.

## Integration boundary

The caller must independently prove the true retained features lie inside the box.
It must bind that proof to the exact retained IDs and current ancestor codes.
It must also bind the checkpoint, grids, normalization, target, and runtime.
Bounds from a floating approximation alone do not establish this premise.
Derivative bounds alone do not account for finite rounding discontinuities.
The provider must include those rounding effects.

Accepted codes can avoid a factor evaluation only when the provider is cheaper.
This module does not measure that cost.
The returned counters are diagnostics, not a standalone serialized proof object.
A verifier can rerun the certificate from the bound inputs.

Most importantly, constant codes do not determine the current factors.
Two feature matrices can share all codes and have different exact Gram matrices.
Therefore, this certificate cannot establish the existing canonical current-factor state.
That state still requires exact factors when its schema commits them.

## A possible canonical anchor state

The following construction is a separate prospective state family.
It is not implemented by this module.
It changes the state contract, while preserving the declared exact code target.

Choose a fixed anchor prefix as a deterministic function of base weights alone.
The anchor must not depend on the calibration corpus or deletion history.
For each record \(r\), compute an anchor leaf

\[
L_r=\operatorname{Anchor}(W,r).
\]

Each leaf contains deterministic source-local features or certified response data.
Assume a sound provider can form

\[
\operatorname{Box}(L_r,P,j)
\supseteq \{Z_{r,j}(P)\}
\]

for the current prefix \(P\) at stage \(j\).
The provider must handle the declared finite semantics.
Failure can trigger exact source evaluation.

Define the canonical persistent state as

\[
S(R)=\operatorname{Encode}\!\left(
\text{fixed target bindings},
\operatorname{Sort}\{(r,L_r):r\in R\},
Q(W,R)
\right).
\]

Exact current factors and execution caches are not fields of this state.
They can remain temporary data during a request.
Any persistent cache requires separate deletion and state semantics.

**Conditional state theorem.**
Assume deterministic source-local anchors, canonical encoding, sound boxes, and a terminating exact fallback.
Delete each requested anchor leaf and compute certified retained codes.
Then the resulting state equals a fresh construction on the retained records.

The anchor leaves agree because each leaf depends only on its surviving record.
The code matrices agree by the certificate or exact fallback.
Canonical encoding then gives state equality.

This theorem does not provide an efficient feature-box provider.
It also does not bound fallback frequency or total repair cost.
Calibration-dependent original prefixes cannot replace the fixed anchor in this proof.
Such anchors can retain influence from deleted records.
Reanchoring that depends on repair history also breaks this canonical definition.

## Verification

Run:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python -m unittest tests.test_token_box_certificate_v13 -v
```

Eleven focused tests passed.
They cover zero-width agreement with an exact rational oracle.
They also cover every vertex of a nontrivial six-dimensional box.
Interior points provide additional checks.
Separate tests check the residual bounds against exact coefficients at every vertex.
Further checks cover differing-code abstention, candidate equality, row scales, ties, saturation, and singleton grids.
Input checks cover invalid bounds, nonfinite values, tiny ridge values, and runtime rejection.
These fixtures verify software behavior.
They are not empirical language-model evidence or a substitute for the proof above.
