# Verified primal certificate, revision 30

This module closes the missing feature-space implementation from the V29 scaling audit.
It preserves the exact fixed-feature target and its canonical dyadic scales.
It does not establish practical speed, full-model completion, or publication novelty.

The module is `src/primal_certificate_v30.py`.
Its software fixtures are `tests/test_primal_certificate_v30.py`.
No empirical model run was used to develop these fixtures.

## API

```python
from src.primal_certificate_v30 import (
    PrimalBudget,
    assess_primal_budget,
    certify_primal_dyadic_box,
)

budget = PrimalBudget(
    max_workspace_bytes=256 * 1024 * 1024,
    max_work_units=100_000_000,
)

report = assess_primal_budget(
    rows=weights.shape[0],
    width=weights.shape[1],
    tokens=lower.shape[1],
    bits=4,
    budget=budget,
)

result = certify_primal_dyadic_box(
    weights, lower, upper,
    ridge=ridge,
    normalization=normalization,
    bits=4,
    significant_bits=24,
    budget=budget,
    arithmetic_backend="native",
)
```

Inputs must be ordinary finite binary64 NumPy matrices.
They must remain unchanged during the call.
Each float denotes its exact dyadic value.
Ridge and normalization accept built-in integers or exact fractions.
Both must be positive.

`scale_values`, when supplied, must equal the existing canonical base-only scales.
`candidate_codes`, when supplied, must match the final certified codes.
The result owns immutable code bytes.
No candidate model can override a failed certificate.

`assess_primal_budget` allocates no numerical arrays.
It returns dimensions, structural work, estimated array bytes, `admitted`, and `refusal_reason`.
Malformed arguments raise errors.
Oversized plans return `admitted=False`.
The quantizer refuses those plans before compilation or coefficient allocation.

`arithmetic_backend="python"` selects a directed reference implementation.
The default native route compiles strict C kernels once per process.
It never loads an existing compiled cache.
Compilation belongs inside complete service timing.

A failed attempt raises `PrimalUnresolved` and returns no partial model.
The module has no exact rational fallback and no token-space fallback.
A caller can use another separately bounded certificate after refusal.

## Exact identity

Let the retained feature matrix be \(X\in\mathbb R^{d\times T}\).
Let \(m\) denote output rows.
Set \(\beta=\lambda\nu\), preserving the declared normalization \(\nu\).

\[
H=\lambda I+XX^T/\nu,
\qquad K=XX^T,
\qquad S_i=\{i,\ldots,d-1\},
\qquad B_i=\beta I+K_{S_i,S_i}.
\]

The existing token coefficient is

\[
c_i=(\beta I_T+X_{S_i}^TX_{S_i})^{-1}x_i.
\]

The push-through identity gives

\[
c_i=X_{S_i}^TB_i^{-1}e_1.
\]

Therefore the exact rounding input is

\[
v_{ri}=w_{ri}+\sum_{h<i}(w_{rh}-q_{rh})a_{hi},
\qquad
 a_{hi}=K_{h,S_i}B_i^{-1}e_1.
\]

This identity changes the numerical representation only.
It does not change source deletion, coordinate order, normalization, or the target quantizer.

## Directed coefficient evidence

The Gram kernel bounds every entry through directed products and sums.
It processes each feature dot product directly.
Diagonal entries use the same-variable square rule.
Every realized Gram matrix lies within the resulting entrywise enclosure.
The interval hull can contain indefinite matrices.
The proof only uses realized matrices, which satisfy \(B_i\succeq\beta I\).

A reverse block-inverse update proposes \(\widehat y_i\).
The nominal inverse and BLAS products supply no accepted numerical evidence.
A failed nominal update resets its affected suffix to zero.
Residual verification still determines acceptance.

The certificate proves

\[
\|r_i\|_2^2
=\|e_1-B_i\widehat y_i\|_2^2
\le E_i
\]

for every realized matrix.
The ridge floor gives

\[
\|B_i^{-1}e_1-\widehat y_i\|_2^2
\le E_i/\beta^2.
\]

The ordinary coefficient radius follows from

\[
|a_{hi}-K_{h,S_i}\widehat y_i|^2
\le \|K_{h,S_i}\|_2^2 E_i/\beta^2.
\]

A second bound can improve this radius substantially.
Write \(Z=X_{S_i}\) and \(x=X_h\).
Then

\[
K_{h,S_i}B_i^{-1}=xZ^T(\beta I+ZZ^T)^{-1}.
\]

For every singular value \(s\ge0\),

\[
\frac{s}{\beta+s^2}\le\frac1{2\sqrt\beta}.
\]

Consequently,

\[
\|K_{h,S_i}B_i^{-1}\|_2^2
\le K_{hh}/(4\beta),
\]

and

\[
|a_{hi}-K_{h,S_i}\widehat y_i|^2
\le K_{hh} E_i/(4\beta).
\]

The code takes the smaller of these two independently valid upper bounds.
It also includes directed error in \(K_{h,S_i}\widehat y_i\).
The resulting center and radius enclose the exact coefficient.
Neither bound treats the nominal inverse as correct.

This spectral inequality is mathematical infrastructure, without a priority claim.
Its usefulness on real calibration matrices remains an empirical question.

## Verified square-root radius

A library square root supplies an untrusted proposal.
The verifier first applies exact power-of-two scaling.
For positive finite binary64 \(z\), choose an even exponent \(e\) such that

\[
u=z2^{-e}\in[1/2,2).
\]

The code accepts a proposed \(r\) only when

\[
\operatorname{down}(r\,r)\ge u.
\]

It returns \(r2^{e/2}\).
This rescaling is exact and remains normal and finite.
The exponent lies between \(-1074\) and \(1024\).

This check covers subnormal squared radii without squaring a tiny returned root.
The first implementation safely refused some such radii.
The final scaled check resolves that avoidable refusal.
A bounded proposal search can still refuse.

Nonfinite residual or solution-error diagnostics cause refusal.
The module does not emit infinite numerical diagnostics in successful results.

## Row verification and ties

The native route reuses the reviewed strict interval row kernel.
It supplies identity features and the triangular primal coefficient table.
The resulting accumulator holds earlier differences \(w_{rh}-q_{rh}\).
This is an algebraic reuse of the verifier, not new calibration data.

Each decision encloses the complete rounding input.
A finite cell uses a strict lower boundary and an inclusive upper boundary.
Thus exact midpoint ties select the lower code.
Saturated cells require only their existing boundary.

Induction proves all returned codes match the exact target for every supplied feature matrix.
The proof assumes the true features lie inside the supplied box.
This module does not establish that upstream containment premise.

Structural ties with zero corrections can be certified exactly.
A nontrivial exact tie can remain unresolved because its enclosure has positive width.
Refusal is permitted and preserves soundness.
Sampling, midpoint substitution, and tolerance-based acceptance are absent.

## Work and storage

The native Gram kernel performs \(O(d^2T)\) arithmetic work.
Reverse inverse proposals and coefficient checks perform \(O(d^3)\) work.
The shared native row kernel performs \(O(md^2)\) work.
The normal complete bound is

\[
O(d^2T+d^3+md^2).
\]

No \(T\times T\) array exists on this route.
No suffix receives an independent dense factorization.
All coefficient arrays occupy \(O(d^2)\) storage.
Aligned input copies and output arrays add \(O(dT+md)\) storage.

The admission report uses the structural score

\[
d^2T+d^3+md^2+2m2^{b},
\]

where \(b\) is the quantization bit count.
This score is not an operation count or a latency prediction.
It supports declared resource gates and route comparison.
Constants differ between primal and token-space routes.
A smaller score does not prove a faster implementation.

The array envelope reserves

\[
8\bigl(40d^2+24d+4dT+10md+8m2^b+24m\bigr)
\]

bytes.
This is a conservative allowance for explicit numerical arrays.
It excludes caller residency, compiler memory, allocator overhead, and opaque BLAS workspace.
An independent process cap remains necessary.
Passing admission does not establish memory fit, useful acceptance, or completion.

The native loop removes Python overhead from Gram and coefficient verification.
Nominal inverse updates still use NumPy and BLAS.
Large widths can remain expensive because the cubic feature term remains.
Wide projections can favor the token-space route.
The same primal backend must be available to compatible reconstruction baselines.

## Verification and limits

Sixteen focused software tests pass.
They compare point outputs against the independent rational dense oracle.
They also check every corner of small uncertain boxes and exact coefficient solutions.

The tests cover the following cases.

- Canonical scales and lower-code ties.
- Empty token sets and unchanged normalization semantics.
- Genuine endpoint disagreement and deliberate incorrect solve proposals.
- Directed Gram containment, including underflow products.
- Smallest and largest subnormal squared radii.
- Minimum normal and maximum finite squared radii.
- Overflow, tiny ridge products, and unsupported runtime refusal.
- Candidate mismatch and immutable output bytes.
- Noncontiguous and unaligned input matrices.
- Resource refusal before compilation and coefficient work.
- Linear token growth and constant coefficient storage with respect to tokens.

These are software fixtures, not synthetic empirical datasets.
They establish implementation evidence within the declared runtime assumptions.
They do not replace formal proof or broad numerical validation.

Independent review found no arithmetic or algebraic blocker in the final route.
Its reviewer also injected incorrect proposals and checked exact corner solutions.
Current evidence does not establish realistic-token acceptance or full-model speed.
A registered real-data pilot must test those claims before expansion.
