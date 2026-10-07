# Revision 18: direct-grid box certification and bounded refinement

Date: 7 October 2026.
Status: implemented components with correctness tests.
This revision does not provide a complete transport service or measured repair speedup.

## Completed components

`src/dyadic_box_certificate.py` certifies the finer row grids over uncertain feature boxes.
It works in original weight units.
It never divides weights by a non-power-of-two scale.
It constructs shared coefficient enclosures once for each box.
It checks each output row against that row's exact rounding cells.
Singleton boxes use the existing point solver with shared fallback limits.
Positive-width boxes never use a pointwise fallback as a universal certificate.
Unsupported arithmetic, uncertain decisions, or invalid inputs prevent a returned model.

`src/box_refinement.py` implements deterministic request-local refinement.
Its inputs are proved record boxes and an exact evaluator.
It sorts records by identifier before concatenating token columns.
After rejection, it evaluates the record with the largest maximum coordinate width.
It compares widths as exact dyadic rationals.
It breaks ties by record identifier.
An evaluated record becomes a singleton box.
An exact value outside its supplied box aborts the operation.
The caller sets a hard limit on evaluated records.

These components do not prove that transformer factors lie inside supplied boxes.
They do not define persistent anchor state or its service integration.
Accepted, unevaluated boxes still require a valid external proof.
Checking fallback values does not validate all unevaluated bounds.

## Certificate theorem

Fix finite base weights, positive ridge, positive normalization, and the declared direct dyadic grids.
Let B contain every admissible feature matrix between the supplied endpoints.
Assume the documented finite arithmetic checks succeed.
If `certify_dyadic_box` returns Q, then every Z in B has exact sequential quantizer output Q.
The lower-code tie rule remains unchanged.

Proof:

1. The existing residual certificate encloses every token coefficient over B.
2. Before coordinate zero, every exact residual accumulator is zero.
3. Assume the stored accumulator interval contains each accumulator after the previously certified codes.
4. The coefficient error and accumulator interval enclose each next exact decision input.
5. The direct row-cell test accepts only an enclosure contained within one declared rounding cell.
6. Every admissible feature matrix therefore selects the returned code at that coordinate.
7. Directed interval products and sums enclose the next accumulator for every admissible feature matrix.
8. Induction proves every code.

The proof uses the existing token-box residual bounds and direct-grid cell proof.
Their numerical premises remain required.
Candidate codes cannot bypass any check.
A candidate mismatch rejects the returned candidate claim.

## Refinement theorem

Assume each initial box contains its actual target factors.
Assume the exact callback returns those factors for the requested record.
Every refined product box still contains the actual combined feature matrix.
Therefore, every returned certificate equals retained-data quantization under the declared target.

Each failed attempt evaluates one previously uncertain record, unless the budget stops the operation.
There are at most min(budget, uncertain records) exact evaluations.
There is at most one more certificate attempt than exact evaluations.
After all uncertain records become singleton boxes, the point solver is available.
Its separate numerical and resource limits can still prevent completion.
No theorem promises completion when those limits fail.

The widest-first rule determines behavior, not optimality.
It has no proved minimum-cost guarantee.
If certificate attempt k costs C_k and evaluated record r costs E_r, request work includes

\[
\sum_k C_k + \sum_{r\in R_{eval}} E_r
+ C_{selection}+C_{copies}+C_{concatenation}.
\]

Repeated rejected certificates can exceed fresh reconstruction cost.
Preparation, storage, persistent-state updates, and external transaction costs remain additional terms.
A future integration needs a predetermined work cap and equally optimized controls.

## Saved-factor audit

`analyze_factor_changes_v18.py` reads the verified revision 17 original and retained state arrays.
It checks state bytes and transaction bindings before comparing factors for retained records.
It performs no model execution and no new quantization.
The saved output binds both input artifacts.

| Quantity | Count |
|---|---:|
| Retained feature values across all stages | 516,096 |
| Values after changed ancestor prefixes | 503,808 |
| Unchanged values after changed ancestor prefixes | 41 |
| Changed values after changed ancestor prefixes | 503,767 |
| Complete factors after changed ancestor prefixes | 23 |
| Exactly reusable complete factors in that group | 0 |

The first factor contributes 12,288 unchanged values because it has no quantized ancestor.
The other 23 factors contain changes.
Thus, exact whole-factor reuse cannot resolve this particular pilot.
This finding does not prove that all transport algorithms fail.
It also does not establish a population rate or behavior under smaller deletion fractions.

## Why constant-code certification is insufficient for current-factor state

The current persistent state stores exact factors at the repaired ancestor prefix.
A constant-code certificate determines quantized codes, not exact factors.
A feature interval can contain different factor values with the same code result.
Those factor values produce different persistent state bytes.
Therefore, code constancy alone cannot justify a canonical current-factor state.

An interval-only state recovery procedure must identify one admissible binary64 value for each stored factor entry.
Otherwise, at least two admissible factor states remain consistent with its information.
Other algebraic information could resolve the ambiguity.
This argument does not forbid such information or establish a runtime lower bound.

The anchor-state design in TRANSPORT_DESIGN_V16.md avoids storing exact current factors.
Its calibration-independent leaves can survive deletions canonically.
That design still needs useful finite transformer bounds and complete service implementation.
The new certificate and refinement modules close two prerequisites only.

## Validation

The final focused run passed 29 tests.
Tests include independent dense rational oracles and all 64 vertices of one nonzero-width software fixture.
They also include three interior points, zero-rank factors, wrong candidates, invalid grids, and budget rejection.
Refinement checks cover deterministic ordering, callback avoidance, false provider bounds, and exact final codes.
These are correctness fixtures, not empirical datasets.
An initial refinement test indexed a record identifier instead of its lower array.
The corrected assertion passed; the failed log remains archived.
This was not a full-suite run or independent mathematical review.

No new research worker ran.
The inherited allowance remains 291 CPU seconds.
The forty scientific cells, broader quality, and reliable full-model speedup remain open.

## Next executable dependency

Implement the calibration-independent anchor summaries and their finite transformer bound provider.
Bind that provider to actual token records, checkpoint weights, runtime, and the target.
Then integrate the alternative canonical state and bounded fallback costs.
Only then run a prospectively limited bound-width pilot.
Do not present this component work as completed transport or empirical superiority.
