# Proof-safe numerical providers

Status: mathematical and algorithmic specification, 4 October 2026. No experiment or numerical test was run to prepare this document. This document does not assert that arbitrary vendor kernels already supply certified error bounds.

## 1. The exact target

Fix the base weights, tokenizer, record boundaries, masks, positional conventions, quantization grids and coordinate order, covariance normalization, ridge, and tie rule. Define a record-local feature evaluator `V(prefix, record)` by an executable deterministic finite program. Its inputs and all returned finite binary floating-point values are interpreted as exact dyadic rationals when constructing quantization statistics.

A concrete reproducible interface uses batch size one, a fixed padded sequence length, and a fixed implementation/device/kernel schedule. Larger fixed batches are allowed only when their composition and schedule are intrinsic to a record and independent of the current retained corpus, or when the resulting dependence is explicitly included in the target and repair proof. Deleting a record and repacking a batch is not automatically the same feature map. Disabling dropout and setting a seed do not establish deterministic numerical execution by themselves.

The quantization target uses

\[
H_\ell(R)=\lambda_\ell I+M_0^{-1}\sum_{j\in R}
V_\ell(Q_{<\ell}(R),j)V_\ell(Q_{<\ell}(R),j)^\top
\]

with exact arithmetic on the returned finite values. The quantizer is exact rational reverse LDL plus nearest-grid rounding with the pinned tie rule. This is an executable hybrid target: finite-program neural features, exact finite-input quantization. It is different from a target that also specifies a floating-point Gram accumulation and floating-point Cholesky quantizer.

A complete fallback always exists: execute `V` on every retained record in the specified order and context, construct the exact retained Grams, and execute the exact quantizer sequentially. If `V` itself is nondeterministic under the declared execution contract, a unique bitwise model target has not been defined; fix the contract before claiming exact equality.

Nonfinite feature outputs, an invalid mask, or an undefined primitive are explicit target errors, not successful repair results. A provider may return `UNKNOWN`; it must not silently replace an invalid operation by an arbitrary finite tolerance.

## 2. Provider interface and soundness obligation

For a node with ideal real map `f_theta` and finite implementation `E_theta`, a provider receives a proved input region `X`, parameter values, norm, arithmetic type and execution schedule. It returns either

- a rigorous outward error bound `nu` satisfying `||E_theta(x)-f_theta(x)|| <= nu` for every allowed finite input `x` in `X`; or
- `UNKNOWN`, treated as positive infinity by the planner.

Alternatively it returns an outward interval enclosure of each actual finite output over `X`. All parameter conversion, fused operations, intermediate precision, reassociation and exceptional-value rules are included in its proof obligation. Cached certificates bind the provider, binary/kernel version and parameter identity.

Three sound modes are allowed:

1. **Exact finite-program execution:** actually run the pinned program for the selected record. Its returned finite bits are exact data for `V`. No claim about closeness to an ideal real network is needed to acquire this record's features.
2. **Certified analytic floating-error bound:** apply a proved bound for the actual operation schedule and input region, such as the affine bound below.
3. **Certified interval primitive/composition:** use outward enclosures for correctly rounded primitives, or another explicitly proved primitive contract, and compose them through the actual computation graph.

An unspecified vendor `exp`, `rsqrt`, GELU approximation, tensor-core multiply, flush-to-zero mode or autotuned fused kernel does not qualify merely because its output usually looks accurate. In the absence of a compatible bound it returns `UNKNOWN`; the repair algorithm then replays that record/stage using the target program. `UNKNOWN` is an abstention, never evidence that the target changed.

## 3. Discrepancy propagation

Suppose reference and candidate finite activations have discrepancy at most `D`. For a common ideal node map with Lipschitz constant `L` over the relevant input region,

\[
D'\le LD+\nu_{\rm candidate}+\nu_{\rm reference}.
\]

For changed node parameters, include a proved parameter-transport term `P`:

\[
D'\le LD+P+\nu_{\rm candidate}+\nu_{\rm reference}.
\]

Proof: insert the two ideal node outputs and apply the triangle inequality. The two numerical-error terms cannot generally be canceled, even when both programs use the same precision. Their executions can follow different input-dependent paths.

For the affine node, a useful Euclidean bound is

\[
D'\le \|A'\|_2D+\|(A'-A)x\|_2+\|b'-b\|_2
       +\nu_{A',b'}+\nu_{A,b},
\]

where `x` is the reference input; replace its parameter-transport term by an outward bound over the available reference input region when `x` is not stored. Frobenius norms apply to a matrix of token activations. Residual additions, attention branches and other merges use their actual graph topology; discrepancy contributions are added with certified norm bounds.

## 4. Affine gamma bounds and aggregation

Let the exact intended affine expression be `y=Ax+b`. Assume the specified binary arithmetic has unit roundoff `u`, all rounded intermediates are normal or exact zero, no overflow occurs, and every permitted operation satisfies the usual relative-error model. If a conservative schedule bound gives at most `m` accumulated rounding factors on a contribution path, define

\[
\gamma_m=\frac{mu}{1-mu},\qquad mu<1.
\]

Then an appropriate conservative componentwise bound is

\[
|E_{A,b}(x)-(Ax+b)|
\le \gamma_m\bigl(|A||x|+|b|\bigr).
\]

For an explicitly implemented length-`n` sequential dot product followed by a bias addition, `m=2n+1` is a safe conservative operation-count choice under these assumptions. A tighter `gamma_n`-type constant can be used only with the corresponding proved multiply/add/FMA schedule. Input casts, TF32 mantissa truncation, multiple accumulation precisions, and scaling must be covered separately; a standard FP32 bound cannot simply be assigned to them.

For token matrix `X`, a convenient aggregate certificate is

\[
\nu_F\le\gamma_m
 \bigl\||A||X|+|b|\mathbf 1^\top\bigr\|_F
\le\gamma_m\bigl(\||A|\|_2\|X\|_F+
 \sqrt{t}\|b\|_2\bigr),
\]

where `t` is the number of token columns. The rightmost expression can use an outward Frobenius upper bound for `|| |A| ||_2` and a stored intrinsic bound on `||X||_F`. It therefore need not inspect every retained activation at request time. Bounds on candidate activations follow from the reference norm plus the current discrepancy bound. All norm computations themselves must be outward bounded.

**Underflow and overflow rule.** The displayed relative-error formula is not silently extended outside its premises. If interval range propagation cannot establish the required normal-or-exact-zero regime, return `UNKNOWN`, unless the provider separately proves an absolute-error contract for gradual underflow, subnormal operations or the specified flush-to-zero behavior. Overflow, `mu >= 1`, or a nonfinite upper bound likewise produces `UNKNOWN`. Record replay remains available and does not rely on this analytic model.

## 5. Softmax: specific denominator and Lipschitz bounds

Use the pinned mask and a nonempty set of unmasked entries. The ideal stable softmax subtracts the exact maximum `m`, so `z_i=x_i-m <= 0`, at least one `z_i=0`, and

\[
1\le s=\sum_i e^{z_i}\le n.
\]

Its Jacobian is `diag(p)-pp^T`. Its row and column absolute sums are `2p_i(1-p_i) <= 1/2`, so its induced 1-, 2- and infinity-norms are at most `1/2`. Thus the ideal softmax map is globally `1/2`-Lipschitz in any of those norms on a fixed mask.

For a finite-program error certificate, first enclose the actual max/subtraction outputs, then the actual exponential outputs under the provider's primitive contract, then their specified finite sum. Let its denominator enclosure be `[s_lo,s_hi]`. Division is certifiable only when `s_lo > 0`; use outward division intervals. The ideal fact `s >= 1` does not by itself certify a different vendor implementation's finite denominator. It can help construct a primitive error proof when that implementation is known.

Correctly rounded `exp` can be enclosed by outward bounds on the exact exponential followed by the declared rounding map. A vendor approximation needs its own proved approximation and arithmetic error. A mask with all entries excluded is a specified target special case or an error, not covered by the nonempty-mask proof. Exponential underflow falls under the rule in Section 4 unless explicitly certified.

For an input region, enclosing both the ideal and finite computations and taking the largest possible componentwise difference gives a conservative `nu`; tighter correlated error propagation is optional. Independent interval evaluation can overestimate substantially, which affects acceptance, not correctness.

## 6. Layer normalization: positive denominator and Lipschitz bounds

For fixed dimension `n`, ideal layer normalization is

\[
f(x)=\gamma\odot\frac{Px}{\sqrt{\|Px\|_2^2/n+\epsilon}}+\beta,
\qquad P=I-\mathbf1\mathbf1^\top/n,\quad\epsilon>0.
\]

The derivative of the normalized part has spectral norm at most `1/sqrt(epsilon)`, hence a valid global bound is

\[
L\le\|\gamma\|_\infty/\sqrt{\epsilon}.
\]

A larger proved variance lower bound over the entire connecting input region can tighten the denominator bound. Changed scale/shift parameters require their parameter-transport terms; they do not disappear into the input Lipschitz term.

The finite provider encloses mean, centering, variance, epsilon addition, square root or inverse square root, multiplication, and affine scale/shift in the actual order. If the interval for the argument of the square root is `[a_lo,a_hi]` with `a_lo > 0`, the denominator is bounded below by a certified lower enclosure of `sqrt(a_lo)`. A reciprocal is safe only when this finite denominator enclosure excludes zero. If cancellation in a variance formula permits a negative lower bound, or epsilon underflows in the actual precision, return `UNKNOWN` or refine the enclosure.

The positive epsilon in the ideal formula does not prove safety of an unrelated finite variance implementation. Correctly rounded `sqrt` has a standard rounding enclosure; a vendor `rsqrt` approximation needs a proved error contract. Conservative global `1/sqrt(epsilon)` bounds may be too loose to save work and carry no acceptance guarantee.

## 7. Exact quantization, ties, and fallback termination

Returned finite features, finite weights and finite grid scales are dyadic rationals. Their exact sums/products and division by a fixed integer normalization are rational. With positive rational ridge, the exact Gram is SPD. Reverse LDL uses only rational arithmetic and positive rational pivots, so the triangular conditional quantization inputs are rational as well.

An interval filter may establish a unique rounding cell quickly. If refinement remains ambiguous, exact rational comparison against rational cell boundaries decides the code, including exact equality under the fixed tie rule. This removes a possible nontermination at ties. Exact rational operation counts do not imply bounded constant-time arithmetic; integer growth and serialization costs are charged separately.

If the intended target instead specifies floating Gram accumulation, floating factorization and a blocked floating quantization recurrence, that whole program must have a compatible verified enclosure or be replayed exactly. Equality to the rational oracle is not sufficient. A small norm error or an empirical tolerance does not prove bitwise equality of such a program.

## 8. Planner behavior and audit fields

For each attempted shortcut:

1. Bind the feature/quantization contract and provider identities.
2. Obtain intrinsic reference norms and certified parameter/input regions.
3. Propagate discrepancy using proved node bounds, including both numerical terms.
4. Convert finite bounds into the covariance and rounding certificates.
5. On `UNKNOWN`, an invalid denominator, or an unresolved rounding cell, refine only using authorized certified information or replay the needed record/stage.
6. Keep the full declared fallback progressing under the weighted scheduler, or use a separately proved work-cap policy. Missing bounds must not block this terminating route.

Record which provider mode was used, which premise failed on abstention, and which target contract was returned. Any canonical-state theorem must specify whether this audit is transient or a canonical function of the retained corpus; history-dependent transcripts cannot silently remain part of a claimed canonical state.

This contract closes the soundness gap between ideal-network transport algebra and a finite-program feature target. It does not certify every vendor kernel, guarantee tight bounds, or establish that the repair path is faster on a particular workload. Those are distinct implementation and empirical obligations.
