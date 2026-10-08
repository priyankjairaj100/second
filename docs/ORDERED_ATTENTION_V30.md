# Ordered finite attention

This implementation preserves the declared finite causal attention values.
It batches independent coordinates and keeps every reduction in its original order.
It does not replace attention with a BLAS or approximate softmax kernel.

## Identified cost

Let \(L\) be the record length, \(d\) the model width, and \(H\) the head count.
The number of causal query–key pairs is \(P=L(L+1)/2\).

The scalar implementation constructs approximately \(4dP\) multiply/add results per block.
This includes score dot products and weighted value sums.
At \(L=128\), \(d=768\), and \(H=12\), this gives 25,362,432 scalar results per block.
Six blocks therefore require 152,174,592 such results.
Each block also needs \(HP=99,072\) exponential evaluations.

These are source-derived operation counts, not observed timing fractions.
They identify avoidable Python object work.
Correctly rounded primitives and other decoder components can still dominate after this change.

## Interface

`finite_attention(qkv, width, heads, constant)` returns rows of `_Finite` values.
Its interface matches the finite use of the existing attention function.
It rejects proof jets and malformed dimensions.
The caller must keep inputs unchanged during execution.
The constant function must return the declared finite constants.

Only causal pairs are allocated and evaluated.
No unused future score can cause an overflow or affect an earlier output.

## Score equivalence

For each causal pair and head, initialize the score with the declared zero.
Visit head coordinates in ascending order.
Each coordinate performs a separate binary64 multiplication and addition.
NumPy batches only the independent query, key, and head coordinates.
The intermediate product array prevents multiply-add contraction.

The head-width square root uses the existing correctly rounded primitive backend.
Each completed score receives the same binary64 division as the scalar reference.

For each query and head, the maximum starts with key zero.
Later keys replace it only when their score is strictly larger.
This preserves the first maximum, including equal signed-zero values.
The shift uses a separate negation and addition, matching `_Finite.__sub__`.

## Softmax and value equivalence

Each shifted score receives a proved correctly rounded exponential.
The denominator starts with the declared zero.
Its terms enter in ascending key order.
Each probability receives the same binary64 division as the scalar reference.

For weighted values, the implementation again visits keys in ascending order.
Each key contributes a separate multiplication and addition.
Only independent queries, heads, and output coordinates are batched.
The output rows therefore retain the scalar reduction order.

Every active multiplication, addition, and division must remain finite.
An overflow or invalid elementary result raises `FiniteTargetError`.
Subnormal results remain permitted under the declared gradual-underflow premise.

## Batched exponential certificates

The later integration generalizes this helper to `exp`, `tanh`, `erf`, and `sqrt`.
`batch_rounded_exp()` remains an explicit wrapper around the exponential case.
The same directed-endpoint proof applies to every supported primitive.
Zero preserves its sign for `tanh`, `erf`, and `sqrt`.
Negative square-root inputs follow the unchanged rejection path.

The rational primitive backend continues to call the existing `rounded()` function.
The MPFR backend processes bounded chunks of at most 4096 arguments.

For each ordinary argument, two explicit 104-bit contexts compute directed endpoints:

\[
\ell\le\exp(x)\le u.
\]

Binary64 input conversion is exact because each input has at most 53 significant bits.
Both contexts bind rounding mode, exponent limits, normalization, and exception settings.
They do not inherit an unrelated ambient context.

Each endpoint uses MPFR's public `as_integer_ratio()` method.
The repository's integer-based `round_fraction()` converts that exact rational to binary64.
No direct MPFR-to-float conversion or foreign-library ABI assumption enters this proof.

The implementation accepts only when both endpoint encodings match.
Monotonic nearest-even rounding then proves the returned exponential value.
Ambiguous endpoints use the unchanged `rounded('exp', x)` fallback.
Arguments outside the existing ordinary range also use that fallback.
For the exponential, both signs of zero return the exact value one.

The new enclosure can complete where the earlier absolute interval refinement could not.
It preserves correctly rounded values on their common completion domain.
It does not claim identical resource use or identical refusal behavior for every primitive input.

The proof uses documented public interfaces:

- [gmpy2 contexts](https://gmpy2.readthedocs.io/en/latest/contexts.html) define directed rounding and nearest-even rounding.
- [gmpy2 real numbers](https://gmpy2.readthedocs.io/en/latest/mpfr.html) document exact rational endpoint conversion.
- [gmpy2 overview](https://gmpy2.readthedocs.io/en/stable/overview.html) describes correctly rounded MPFR arithmetic.

## Work and storage

Arithmetic work remains \(O(dL^2)\), plus \(O(HL^2)\) exponential work.
The change removes most Python scalar wrapper construction.
It also shares MPFR contexts and avoids unnecessary absolute interval expansion.

Array storage is \(O(HL^2+dL)\).
The implementation stores causal scores, shifted scores, probabilities, and bounded temporary arrays.
Exponent endpoint objects are limited by the fixed chunk size.
This is not a whole-process memory guarantee.
Registered workers must still enforce their process limits and record lengths.

Both repair and reconstruction must receive this common decoder optimization.
A speed claim against an avoidably slower reconstruction path would be invalid.
Complete comparisons must include all primitive, feature, quantization, and output costs.

## Verification

Ten software tests passed in a reported 0.039 seconds.
They compare binary64 encodings with the original scalar attention function.

The fixtures cover these cases.

- Several token lengths, head counts, and head widths.
- Both primitive backends.
- Signed zeros, subnormals, and cancellation-sensitive sums.
- Causal isolation under changes to future tokens.
- Overflow in an unused future score, which must never execute.
- Overflow in an active score or softmax shift, which must cause refusal.
- Exponentials near underflow and overflow.
- Ambiguous endpoint fallback and explicit MPFR context restoration.
- Empty inputs, invalid dimensions, and runtime checks.

These are program-equivalence fixtures, not synthetic empirical datasets.
No empirical worker ran during implementation.
No historical decoder source changed.

The original attention review covered its first implementation hash.
The generic primitive extension and explicit decoder require their own final source review.
See `ORDERED_FINITE_DECODER_V30.md` for the integration contract.
