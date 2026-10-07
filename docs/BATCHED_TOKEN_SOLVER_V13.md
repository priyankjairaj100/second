# Optional common token-solver batching

Status: implemented and checked with software fixtures on 7 October 2026.
The original solver files remain unchanged.
No real-data timing result is claimed for this implementation.

## Interface

```python
from src.batched_token_solver import (
    batched_token_codes,
    batched_quantize_row_scaled,
)

result = batched_token_codes(
    weights, features, fixed_column_grids,
    ridge=ridge, normalization=original_normalization,
    max_exact_rank=64,
    max_exact_coordinates=16,
    max_refinement_coordinates=16,
)

result = batched_quantize_row_scaled(
    weights, features, base_only_row_exponents,
    bits=4, ridge=ridge, normalization=original_normalization,
)
```

Both functions return the existing `CertifiedTokenResult` type.
The signatures preserve the corresponding reference interfaces.
Codes remain read-only arrays.
The result records the same interval decisions, exact decisions, refinements, and coefficient-error bound.
Inputs must remain unchanged throughout the call.

The target remains

\[
H=\lambda I+ZZ^\top/M.
\]

Weights and factors retain their exact dyadic meanings.
Grids, coordinate order, lower-code ties, and normalization remain fixed.
The row wrapper retains the existing base-only scale rule.
It checks exact normalization and exact restoration.

## Changes

The implementation changes array layout and groups independent operations.
It stores accumulators with token coordinates first and output rows second.
Each reduction then reads one contiguous row.

| Operation | Change | Preserved dependency |
|---|---|---|
| Accumulator update | Batch all token/output entries | One update per weight coordinate |
| Cell-input products | Batch all independent products | Add token terms in their original order |
| Squared norm | Batch all independent squares | Add token terms in their original order |
| Coefficient residual | Batch token-matrix products | Add matrix columns in their original order |
| Fixed grids | Cache repeated grids and boundaries | Preserve exact rational boundary values |
| Candidate inverse | No mathematical change | Preserve the original update sequence |
| Refinement and exact fallback | Reuse existing functions | Preserve limits and fallback decisions |

There is no new BLAS reduction in the trusted certificate.
Candidate matrix products remain untrusted proposals.
The implementation still certifies each proposal through its residual.

## Operation-order argument

Let \(a_{ki}\) denote one stored accumulator endpoint.
The reference updates each token coordinate through a Python loop.
For every output row, it applies the same elementary functions:

\[
d_i=\operatorname{IntervalSub}(w_i,q_i),
\qquad
a_{ki}\leftarrow
\operatorname{IntervalAdd}\!\left(a_{ki},
\operatorname{IntervalMul}(d_i,z_{ik})\right).
\]

Different token/output entries have no dependency during this update.
Broadcasting executes the same operations on the same scalar operands.
It therefore gives the same endpoints under the declared runtime premise.
Only storage indices change.

For coefficient residuals and rounding inputs, the products are also independent.
The additions are not independent.
The implementation retains their original increasing-token order.
It also retains every outward `nextafter` operation and exact-zero shortcut.

The norm routine computes all squared terms together.
It then applies the original directed addition once per token, in order.
It does not replace that loop with `sum`, `dot`, or a tree reduction.

Thus, each trusted bound equals its reference bound under the same elementary arithmetic.
The original candidate inverse operations also retain their shapes and sequence.
The cell tests consequently receive the same inputs.
They produce the same accepted cells and unresolved decisions.
The shared exact fallback then produces the same exact codes.

Grid caching only reuses immutable exact values and their binary64 endpoint conversions.
It does not change a midpoint, a cell boundary, or a tie rule.

This argument concerns stable valid inputs on the declared runtime.
It does not claim identical exception timing or resource use.
It does not claim reproducibility across different untrusted numerical libraries.
Residual verification still protects code correctness when a proposal changes.

## Cost

The arithmetic order remains

\[
O(dT^2+pdT).
\]

Storage remains \(O(T^2+dT+pT+pd)\) entries.
Batching needs additional temporary arrays of those same orders.
It reduces Python dispatches for independent multiplication and accumulator operations.
It does not remove the ordered reduction dependencies.
Small matrices can receive no practical benefit.
Memory traffic can limit larger batches.
Measured speed requires a separate controlled comparison.

## Integration requirements

This is common numerical infrastructure.
Every compatible repair and fresh method must receive the same option.
It provides no deletion-specific advantage by itself.
Selecting it must appear in the execution configuration and source binding.
Bind this module and its imported numerical dependencies in each source snapshot.
Do not silently replace the solver in an existing attempt.
Existing frozen attempts retain their original code.

The module does not construct changed-prefix feature bounds.
It does not update canonical repair state.
It does not establish a full-model repair speedup.

## Verification

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python -m unittest tests.test_batched_token_solver_v13 -v
```

Eight focused tests passed.
Tests compare accepted codes against an independent exact dense oracle.
They also compare code bytes and every result diagnostic with the reference solver.
Cases include empty factors, deficient rank, strided arrays, subnormal boundaries, and exact ties.
Further cases exercise singleton grids, saturation, refinement, bounded exact fallback, and fallback exhaustion.
Tests check directed bounds and accumulator updates byte for byte.
They also check row scales, overflow rejection, invalid inputs, and runtime rejection.

These fixtures are software checks.
They are not empirical language-model evidence.
