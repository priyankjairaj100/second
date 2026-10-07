# Revision 16: concrete transport design and its limits

Date: 7 October 2026.
Status: algorithm design and proof review.
This document reports no experiment and claims no measured speedup.
It preserves the finer dyadic numerical target.
It proposes a different complete state contract.

## Decision

The present identity cache cannot meet the changed-ancestor avoidance gate.
Its implementation requires an unchanged prefix before it reuses a factor.
No timing repetition can change this property.

A concrete successor can use record-local anchor traces and scalar perturbation bounds.
The anchor prefix must be fixed independently of the calibration corpus.
The nearest-grid model gives one explicit anchor prefix.
Its grids remain the declared, base-derived dyadic grids.
This design needs no additional dataset and does not change the numerical target.

The bound provider below uses stored summaries and matrix differences.
It does not traverse the retained transformer for each request.
The provider can fail through wide bounds.
Failure triggers exact evaluation under the declared target.
This design is implementable, but useful acceptance remains unproved.

There is no basis for calling the research blocker closed.
The new algorithm must pass a bound-width screen before another timing campaign.

## 1. Canonical state

Let A denote nearest rounding on every declared base-derived grid.
Its midpoint rule equals the numerical target's lower-code rule.
A depends only on the fixed base checkpoint and target configuration.
It does not depend on the calibration corpus.

For each retained record r, evaluate the declared finite transformer under A once.
Store a canonical leaf L_r containing these fields:

1. The record identifier and exact token sequence.
2. The checkpoint, runtime, anchor, and target bindings.
3. Every anchor input factor used by a quantized stage.
4. Absolute bounds for the anchor intermediates listed below.
5. Positive lower bounds for the required anchor denominators.
6. The lengths, widths, masks, and operation schedules used by each group.

The summaries are deterministic reductions of exact anchor values.
Use exact rational extrema and outward binary64 endpoints during their construction.
Reject a summary when its declared finite endpoint cannot be represented.
Normalize factor zero signs only where the state contract explicitly permits that normalization.

Define the persistent state by

\[
S(R)=\operatorname{Encode}\bigl(\tau,A,
\operatorname{Sort}\{(r,L_r):r\in R\},Q(W,R)\bigr).
\]

Here, tau binds the numerical target and this state schema.
The state does not contain exact current-prefix factors.
Those factors can exist temporarily during a request.
The service must remove all temporary arrays before it commits the final persistent state.

A retained leaf has identical bytes before and after another record's deletion.
Fresh construction on R produces the same leaf.
Therefore, exact codes and sorted surviving leaves determine the complete canonical state.
This argument does not rely on identical model histories.

This contract differs from factor_identity_v1.
A result under this contract cannot retroactively satisfy an earlier current-factor state claim.

## 2. A cheap finite bound provider

The provider tracks absolute differences from the fixed anchor execution.
It groups scalar operations across tokens and output coordinates.
A group stores bounds on its anchor operands.
The provider propagates one scalar difference bound per group.
Finer predetermined groups can improve bounds at additional cost.
Group definitions must remain fixed before the experiment.

Let a and b denote anchor operands.
Let a' and b' denote the requested-prefix operands.
Suppose

\[
|a|\le M_a,\quad |b|\le M_b,
\quad |a'-a|\le\delta_a,\quad |b'-b|\le\delta_b.
\]

Every bound below must use outward arithmetic.
An implementation can use exact rational arithmetic for these few scalar calculations.
This avoids trusting ordinary floating-point rounding of the bounds themselves.

Let u=2^{-53} and eta=2^{-1074}.
For a finite exact real operation result x, use the conservative error bound

\[
|\operatorname{RN}(x)-x|\le u|x|+\eta.
\]

The bound permits gradual underflow.
Reject possible overflow, nonfinite values, or an unsupported runtime.
If identical operands execute the same operation, return a zero difference exactly.
This special case prevents artificial error when the prefix is unchanged.

### Addition and subtraction

Set D=delta_a+delta_b and M=M_a+M_b.
Then the finite result difference is at most

\[
D+u(2M+D)+2\eta.
\]

The real result difference is at most D.
The two rounding errors give the remaining terms.
Subtraction uses the same absolute bound.

### Multiplication

Set

\[
D=M_a\delta_b+M_b\delta_a+\delta_a\delta_b.
\]

The finite result difference is at most

\[
D+u(2M_aM_b+D)+2\eta.
\]

This follows by expanding a'b'-ab and bounding both rounding errors.

### Division

Suppose the anchor denominator satisfies |b|>=m>0.
Require delta_b<m.
Then set

\[
D=\frac{\delta_a}{m-\delta_b}
 +\frac{M_a\delta_b}{m(m-\delta_b)}.
\]

The finite result difference is at most

\[
D+u\left(\frac{M_a}{m}
 +\frac{M_a+\delta_a}{m-\delta_b}\right)+2\eta.
\]

Reject the group when its denominator condition fails.
This rejection is conservative.
It does not establish a failure of the actual transformer.

### Correctly rounded primitives

Suppose f has Lipschitz bound L on the combined operand range.
Suppose |f(a)|<=B and |f(a')|<=B'.
Then the finite result difference is at most

\[
L\delta_a+u(B+B')+2\eta.
\]

For tanh, use L=1 and B=B'=1.
For erf, use L=2/sqrt(pi) and B=B'=1.
For exp, use L=exp(U), where U bounds both inputs from above.
For sqrt, use its secant formula when a positive lower endpoint exists.
A zero lower endpoint instead permits the bound sqrt(delta_a).
Every constant requires a certified outward endpoint.

For a maximum operation, the output difference is at most the largest input difference.
Copies, reshapes, masks, and fixed index selections preserve the corresponding bounds.

These formulas cover the target's primitive schedule.
They do not replace that schedule with an idealized activation function.
For GELU, propagate the actual multiplication, addition, and primitive operations in their declared order.
For normalization, propagate its declared mean, square, variance, epsilon, square-root, and division operations.
For attention, preserve the declared causal lengths and reduction order.
The finite softmax denominator is at least one because a maximum score produces an exact zero shift.
Its exponential is exactly one, and the remaining terms are nonnegative.
Use this structural lower bound when it improves the generic division bound.

### Affine groups without token traversal

Let X_0 denote the anchor input and Q_0 the anchor matrix.
Let X and Q denote the requested-prefix values.
Suppose every input entry differs by at most delta.
Let M bound every anchor input magnitude.
Use matrix norms induced by the vector infinity norm.
The difference between the corresponding real affine maps is bounded by

\[
\|Q\|_\infty\delta+\|Q-Q_0\|_\infty M.
\tag{1}
\]

Finite dot products require an additional bound for each execution's rounding error.
The scalar group evaluator can produce this bound through the declared reduction schedule.
It evaluates one bound per coordinate position, not one dot product per token and output row.
At each position, it uses the stored maximum anchor accumulator magnitude.
It also uses matrix-entry maxima and the input magnitude bounds.
The addition and multiplication rules above then prove the group bound by induction.

There is no trusted BLAS reduction in this proof.
The matrix norms and maxima require directed or exact accumulation.
Their cost is one matrix scan per changed stage, shared by all retained records.
The record-specific scalar propagation costs one reduction-length scan per group.

Equation (1) can tighten the real discrepancy term.
The finite error enclosure must still cover the exact target schedule.
A real-valued derivative bound alone is insufficient.

### Required anchor summaries

For each group, store the maximum absolute anchor operands and intermediate accumulators.
For division groups, also store the minimum absolute denominator.
For square-root groups, store the minimum argument.
For attention, group by causal length and head when their schedules differ.
For normalization, store the minima after adding the configured epsilon.
These summaries require only deterministic maxima and minima during anchor preparation.
They do not require a trained sensitivity model.

The summaries can become loose after grouping.
For example, one token's maximum numerator can combine with another token's minimum denominator.
This affects acceptance, not validity.

## 3. Exact quantization from the resulting boxes

At stage j, let delta_rj bound a retained record's factor difference.
Its factor box is

\[
[\operatorname{down}(Z^A_{rj}-\delta_{rj}),
 \operatorname{up}(Z^A_{rj}+\delta_{rj})].
\]

Concatenate the record boxes in the canonical token order.
Run the existing token-space certificate on these boxes.
The certificate must use the finer dyadic grid in original weight units.
Arbitrary dyadic division followed by integer-grid rounding is invalid here.

The existing row wrapper targets power-of-two scaling.
A finer-grid wrapper therefore needs direct row-specific grids.
The point solver already demonstrates the required grid semantics.
This integration requires new software checks before a real workload runs.

The certificate can infer codes from their proved cells.
It need not require that all codes equal the previous model.
Thus, a changed model can still receive a valid box certificate.
Every accepted code must equal the exact retained-data quantizer output.

When certification fails, evaluate an exact retained record under the requested prefix.
Replace that record's box with its exact factor.
Choose the record with the largest predetermined contribution bound.
Break ties by canonical record identifier.
Repeat until the stage is certified or every factor is exact.
The final case uses the existing exact solver.

The failure path always terminates when the exact target completes.
It does not substitute an approximate model.
All failed bound work remains part of the transaction cost.

## 4. Full-state correctness

Prove the following invariant before each quantized stage:

- Every installed ancestor code equals the exact retained-data target.
- Every current factor box contains its exact retained factor.
- Every persistent leaf depends only on its surviving record and fixed anchor.

The invariant holds initially because the embeddings and anchor are fixed.
The finite bound rules establish each requested factor box.
Exact fallback establishes a singleton box when necessary.
The token-space certificate or exact solver establishes the next code matrix.
Induction proves the complete target model.

Delete every requested leaf and sort the remaining leaves.
Their bytes equal fresh construction on the retained records.
The model codes also equal fresh construction.
Canonical encoding therefore proves full-state equality for this new state family.

This proof separates state equality from factor materialization.
It does not claim equality with the old factor_identity_v1 encoding.

## 5. Costs and the necessary screening order

Let N denote retained records, T total tokens, and d_j,p_j the stage dimensions.
The matrix scans cost O(sum_j p_j d_j).
Group propagation costs the sum of its declared reduction lengths across records.
Neither cost includes a retained transformer traversal.

Reading anchor factors and constructing boxes costs O(T sum_j d_j).
The existing token certificate costs O(d_j T^2+p_j d_j T) per stage.
These costs can dominate the saved feature work.
The provider cannot hide them inside preparation.

Anchor construction adds one finite nearest-prefix traversal per original record.
State serialization writes anchor factors, summaries, tokens, and model codes.
That storage must be measured against the same output cap.
Fresh indexed reconstruction must receive the same surviving anchor leaves.
All compatible baselines must receive common numerical improvements.

Late fallback can replay earlier accepted stages.
The implementation must count that catch-up work.
A provisional box hit is not permanent source avoidance.
Count avoidance only after the complete transaction settles.

Use this order before any confirmation campaign:

1. Build the anchor state on one frozen real root.
2. Report its preparation cost and complete serialized size.
3. Compute actual matrix differences from the existing retained model.
4. Propagate scalar bounds without running the quantizer certificate.
5. Compare bound widths with directly observed factor differences as a diagnostic.
6. Reject the design if bounds overflow or force denominator failure across the root.
7. Run the certificate only for surviving stages.
8. Include every fallback and state operation in the complete comparison.

Step 5 uses existing exact factors only to audit conservatism.
It must not shrink the proved bounds using unavailable exact retained factors.
A bound that contains measured differences is not proved by that measurement.
The finite analysis supplies its proof.

A first-stage certificate failure need not invalidate later stages theoretically.
However, later stages may depend on expensive fallback work.
The complete comparison must include that work.

## 6. Why acceptance may still fail

The nearest anchor can differ from the calibrated prefix at many codes.
Normalization can amplify a coarse input bound.
Attention can couple each token to earlier tokens.
Residual branches retain several sources of error.
Scalar grouping discards correlations between those sources.

The certificate also faces millions of rounding cells.
A small number of narrow margins can trigger exact fallback.
A high fraction of individually stable codes does not imply useful whole-model source avoidance.
No positive acceptance rate follows from the correctness theorem.

These are concrete failure mechanisms.
They are not a universal impossibility result for transport.
Finer groups, stronger correlations, or different exact transport can improve the provider.
Such changes require new costs and fresh prospective controls.

## 7. Why lazy symbolic factors do not close the gap

A canonical symbolic factor can store tokens, target bindings, and the current ancestor codes.
Its expression denotes the exact factor without materializing its entries.
This representation can eliminate factor-byte output.
It does not supply the factor values needed by the quantizer.

An unevaluated expression is not a numerical certificate.
If a later query evaluates that expression, charge the deferred computation then.
If the service stores evaluated caches, include their deletion semantics and persistent bytes.
Do not exclude a cache merely because its interface calls it temporary.

A full response table over every low-bit prefix is source-local and exact.
Its size is exponential in the number of prefix code coordinates.
It is not a feasible replacement under the current storage cap.

A history-dependent memoization table is smaller.
However, its entries can encode a deleted record's effect through their prefix keys and values.
Such entries need deletion, exact rebinding, or an explicitly different state guarantee.
Renaming them as symbolic state does not prove fresh-state equality.

## 8. Two attractive shortcuts that do not solve the registered task

### Rounded current traces

Suppose the cache stores only the canonical rounding cell of an old activation.
That cell does not identify the activation's distance from its boundary.
Widening the entire cell by any positive perturbation crosses its boundary.
Thus, the old cell alone cannot certify the same new canonical cell.
Additional information can help, but its own state contract needs proof.
This observation prevents a circular proof based only on stable quantized caches.

### One-shot disposable traces

A single request can use old calibrated traces and then erase every trace.
This permits tighter local bounds around the previous model.
The final persistent output can contain only retained tokens and exact model codes.
However, the next request no longer has those traces.
Rebuilding them is additional retained computation.

This design can support a separately declared one-shot study.
It does not satisfy the present three-deletion program without additional accounting.
It cannot assume that erased traces remain available for the next request.

## 9. What this revision closes

This document specifies a finite-arithmetic provider with concrete inputs and update rules.
It defines a canonical state that does not require current-factor materialization.
It proves how certificates and fallback preserve the finer dyadic target.
It exposes the complete preparation, storage, and request costs.

It does not establish useful bound widths, source avoidance, or reliable speedup.
Those claims require implementation and the ordered screen above.
The current empirical program remains unpromoted until those claims pass.
