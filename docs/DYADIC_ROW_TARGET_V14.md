# Fixed fine dyadic row target

Status: implemented and checked with software fixtures on 7 October 2026.
This is a new quantizer target.
It does not reinterpret any earlier power-of-two result.
It does not establish improved task quality without a new experiment.

## Purpose

The earlier output-row target uses one power-of-two scale per row.
That rule can leave almost a factor of two between required and selected scales.
A larger step can increase rounding error.
This target reduces that scale slack through finer exact dyadic scales.
The rule reads base weights only.
It does not read calibration documents or quality records.

This scale choice is a numerical implementation improvement.
It is not a deletion-specific novelty claim.

## Interface

```python
from src.dyadic_row_quantizer import (
    dyadic_row_scales,
    dyadic_row_scale_metadata,
    quantize_dyadic_rows,
)
from src.dyadic_row_target import build_dyadic_row_target

scales = dyadic_row_scales(weights, bits=4, significant_bits=24)
metadata = dyadic_row_scale_metadata(weights, bits=4, significant_bits=24)

result = quantize_dyadic_rows(
    weights, features, scales,
    bits=4, significant_bits=24,
    ridge=ridge, normalization=original_normalization,
    max_exact_rank=64,
    max_exact_coordinates=16,
    max_refinement_coordinates=16,
)

target = build_dyadic_row_target(decoder, recipe)
```

`scales` is a tuple of Python floats.
Each float exactly represents its declared dyadic scale.
Metadata gives its odd significand, exponent, exact hexadecimal value, and actual significant-bit count.
The result uses the existing `CertifiedTokenResult` type.
Codes remain read-only arrays.
Supplied scales must exactly match the canonical base-only rule.

The target constructor fixes 24 significant bits.
The numerical helper permits 1–24 bits for explicit software checks or separately declared variants.
The constructor retains base weights, dependencies, ridge, normalization, and evaluator bindings.
It records a distinct schema and scale recipe.
Each stage records every row scale as an exact hexadecimal value.
It also binds the constructor, new solver, batched solver, and token solver sources.

Stages expose `scale_values`, `bits`, and the required base fields.
They deliberately have no column-grid interface.
The target declares model codes only.
It does not declare a canonical repair-state contract.

## Canonical scale rule

For \(b\) quantization bits, set \(h=2^{b-1}\).
The integer code indices are

\[
\{-h,-h+1,\ldots,h-1\}.
\]

For output row \(a\), define the required scale

\[
r_a=\max\left\{
\frac{\max_i W_{ai}}{h-1},
\frac{-\min_i W_{ai}}{h},0
\right\}.
\]

For four bits, the denominators are seven and eight.
These calculations use exact rational values from the binary64 weights.

Choose the smallest positive admissible scale \(s_a\ge r_a\).
An admissible scale has the form

\[
s_a=m_a2^{e_a},
\]

with at most 24 significant binary digits.
Every grid code and every half-step midpoint must be finite and exactly representable in binary64.

The midpoint requirement implies

\[
s_a\ge 2^{-1073}.
\]

The midpoint between zero and the first positive code equals \(s_a/2\).
It must not lie below the smallest binary64 subnormal.
Zero rows therefore use \(2^{-1073}\).
Their quantized codes still equal zero.

### Exact construction

Let \(p\le24\) be the chosen significant-bit limit.
When \(r_a>0\), set

\[
e=\max\{-1073,\lfloor\log_2 r_a\rfloor-p+1\},
\qquad
m=\left\lceil\frac{r_a}{2^e}\right\rceil.
\]

Remove all factors of two from \(m\), increasing \(e\) accordingly.
When \(r_a=0\), use \(m=1\) and \(e=-1073\).
The implementation computes the logarithm comparison through integer bit lengths and exact rational comparisons.
It does not use floating logarithms.

Within each binary binade, admissible \(p\)-bit scales use a fixed spacing.
The construction rounds upward to that spacing.
Crossing the upper boundary produces the next exact power of two.
Smaller-binade values lie below the required scale.
Thus, the construction gives the smallest admissible covering scale.

At the representability floor, upward rounding uses multiples of \(2^{-1073}\).
The same minimality argument applies.
The constructor rejects rows whose required grid cannot remain finite.

## Exactness of codes and midpoints

Each code equals \(ks_a\), where \(-h\le k\le h-1\).
Each boundary equals \((k+1/2)s_a\).
For \(b\le8\), these products need at most \(p+b\le32\) significant bits.
That is below the binary64 precision of 53 bits.
The minimum exponent rule protects their smallest half step.
Explicit endpoint checks reject overflow or any failed exact roundtrip.
Consequently, the array code and midpoint products are exact binary64 values.

The canonical grid covers every base weight:

\[
-hs_a\le W_{ai}\le(h-1)s_a.
\]

Away from the subnormal spacing floor, upward scale rounding satisfies

\[
1\le\frac{s_a}{r_a}<1+2^{1-p}.
\]

For \(p=24\), relative slack is below \(2^{-23}\).
Near the floor, only the corresponding absolute spacing bound applies.
This result concerns scale slack.
It does not prove lower sequential quantization loss or better language-model quality.

## Direct quantization in original units

The implementation does not normalize weights by their scales.
Division by a non-power-of-two dyadic can produce a non-dyadic value.
Rounding that quotient to binary64 would change the target.

Instead, the solver retains the original exact token identity:

\[
G_i=\lambda M I+\sum_{j\ge i}z_jz_j^\top,
\qquad u_i=G_i^{-1}z_i,
\]

\[
s_{a,i}=\sum_{j<i}z_j(W_{aj}-q_{aj}),
\qquad v_{a,i}=W_{ai}+u_i^\top s_{a,i}.
\]

Each output row compares its enclosed input with its own exact grid boundaries.
The lower-code tie rule remains unchanged.
Coefficient proposals, residual bounds, and accumulator updates use the existing certified operations.
Only grid selection differs.

When an interval decision remains unresolved, exact fallback computes \(v_{a,i}\) rationally.
It selects the nearest code from that row's rational grid.
The fallback does not use a normalized weight or approximate scale.
An exhausted fallback budget aborts without returning a model.

**Correctness proposition.**
For valid stable inputs, every returned code equals the exact reverse-LDL target with these fixed row grids.

The existing residual proof encloses each exact rounding input.
Accepted row-specific cells therefore establish exact codes.
The exact fallback establishes unresolved codes directly.
Induction preserves the exact prefix accumulator at every coordinate.
This proves the proposition.

## Experiment and integration requirements

Treat this as a prospective variant with its own target digest.
Preserve every earlier positive and negative result.
Freeze the source and scale rule before any new quality evaluation.
Use fresh quality records for any new development check.
Do not tune scales on previously evaluated records.
Every compatible repair and fresh method must use the same declared grid target.
All methods must receive the same common batched solver option.

The scale rule does not establish feature transport or repair-state equality.
It also does not establish reliable full-model repair speed.
Those claims require their own implementation and experiments.

## Verification

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python -m unittest \
  tests.test_dyadic_row_quantizer_v13 \
  tests.test_dyadic_row_target_v13 -v
```

Ten focused target/solver tests passed after the cumulative grid-budget correction.
They compare each row with an independent exact dense oracle.
They cover empty factors, deficient rank, non-power-of-two ties, and inexact-normalization traps.
They also check scale minimality by enumeration at small precisions.
Further checks cover exact code boundaries, subnormals, zero rows, overflow, refinement, fallback, and runtime rejection.
The target tests check distinct identity, complete base bindings, immutable metadata, and cumulative grid-budget enforcement.
The correction changes constructor source hashes.
Earlier empirical snapshots retain their original hashes and satisfy the corrected numerical limit.

These are software fixtures.
They are not empirical quality measurements.
