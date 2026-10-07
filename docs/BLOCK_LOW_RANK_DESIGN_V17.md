# Revision 17: sparse repair and a cheaper verifier

Status: design review only.
This document contains no new empirical result.
The numerical target remains unchanged.
The complete current-factor state also remains unchanged.

## Decision

Sparse code changes alone do not make the revision 16 scan cheaper.
That scan constructs every candidate accumulator before it checks any code.
Small deletion fractions can improve candidate acceptance.
They do not remove this fixed verification cost.

The strongest immediate route replaces the scan tensor with small matrix products.
It keeps exact fallback and the existing state contract.
Every compatible comparator must receive this verifier.

## 1. Block identity

Write each feature row as a column vector z_i of length T.
Let u_i denote its exact token coefficient.
Let q_i denote an output row's candidate code.
The exact decision recurrence is

\[
v_i=w_i+u_i^\top s_i,
\qquad
s_{i+1}=s_i+z_i(w_i-q_i).
\]

Consider one coordinate block I containing b coordinates.
All earlier codes must already have certificates.
Let S contain their exact incoming accumulators, with shape p by T.
Let E_I=W_I-Q_I contain the candidate residuals.
Let U_I contain coefficient rows u_i^T.
Let Z_I contain feature rows z_i^T.
Define the strict lower matrix

\[
B_{ih}=\begin{cases}
u_i^\top z_h,&h<i,\\
0,&h\ge i.
\end{cases}
\]

Then all candidate decision inputs satisfy

\[
V_I=W_I+S U_I^\top+E_I B^\top. \tag{1}
\]

The candidate terminal accumulator satisfies

\[
S_{\rm next}=S+E_I Z_I. \tag{2}
\]

These are exact real identities for the fixed finite feature values.
They do not prescribe floating reduction order.
Their implementation therefore needs a separate numerical certificate.

### Proof

For each i in I, expand the accumulator before i.
It contains the incoming accumulator and candidate contributions from earlier block coordinates.
Multiplication by u_i gives the corresponding column of equation (1).
Adding every candidate contribution gives equation (2).

If every candidate input stays inside its candidate cell, every candidate code is correct.
Forward induction proves this statement.
The first failed cell ends the certified prefix for that output row.
Sequential continuation can then finish only that block's suffix.
Later blocks start from the resulting exact-code accumulator.

## 2. Why this differs from the rejected scan

The rejected verifier allocates arrays with shape b by T by p.
It performs directed arithmetic through each scan level.
Equation (1) needs only matrices with shapes p by T, p by b, and b by b.
The matrix B is shared across all output rows.
Its construction must occur once per block.

The arithmetic cost is

\[
O\bigl(pd(T+b)+dbT\bigr).
\]

For b no larger than T, this remains O(pdT+ dT^2).
Working storage is O(pT+pb+b^2+dT), apart from weights and codes.
These bounds exclude exact fallback costs.
They do not establish a wall-time benefit.

## 3. Numerical certificate choices

The existing coefficient certificate provides a proposal c_i and a bound delta_i.
It proves

\[
\|u_i-c_i\|_2\le\delta_i.
\]

Thus, each proposed local factor entry has error at most

\[
|u_i^\top z_h-c_i^\top z_h|
\le\delta_i\|z_h\|_2.
\]

The numerical dot-product error must also enter this bound.
The same rule applies to the incoming accumulator product.
Accumulator uncertainty must enter both products and the terminal update.

Two implementations are possible.

1. Use directed arithmetic for the small shared matrix and a compiled directed matrix kernel.
2. Use a checked floating matrix kernel with a proved forward-error envelope.

The second option cannot treat an arbitrary BLAS result as exact.
Its contract must cover operation count, underflow, overflow, arithmetic mode, and reduction behavior.
The bound computation must itself round outward.
An unsupported kernel must cause rejection or use the first option.
Candidate generation remains untrusted in either option.

This document does not certify any current BLAS implementation.
It also does not provide a finished matrix kernel.
Those are implementation and review requirements before an empirical screen.

## 4. Sparse correction and its actual benefit

Once a block prefix has certificates, a changed code adds one rank-one accumulator correction.
If the code at h changes from q_h to q'_h, that correction is

\[
z_h(q_h-q'_h).
\]

This update costs O(T) per affected output row.
It does not require rebuilding an earlier certified prefix.
Within the block, its decision-input correction is

\[
B_{ih}(q_h-q'_h),\qquad i>h.
\]

These identities support event updates after a candidate fails.
The event updates require valid numerical bounds and ordered certification.
They cannot install later candidate cells before earlier changed codes receive certificates.

A sparse event count does not by itself prove a total speedup.
The initial block verifier, coefficient computation, and state operations still cost time.
Every complete comparison must include those costs.

## 5. Why an old-margin cache is not an immediate solution

An old-margin cache could support scalar perturbation tests for many decisions.
The present state stores codes and factors, but not exact decision inputs.
Rebuilding all old decision inputs costs O(pdT).
It can therefore erase the proposed saving.

Stored interval margins also create a state problem.
A repair can widen an old interval into a valid new interval.
Fresh construction need not produce the same interval bytes.
Thus, validity alone does not prove canonical state equality.

The caller could erase a disposable cache after one request.
Its preparation and next-request reconstruction must then enter the cost ledger.
This does not solve the registered deletion sequence for free.
Adding a history-dependent cache requires a new, explicit state contract.

## 6. Prospective screen

Do not repeat the rejected revision 16 cells merely for favorable timings.
First validate a cheaper kernel against an independent exact oracle.
Keep the fixed target, row grids, normalization, and tie rule.

Then compare the new verifier with optimized sequential quantization on both frozen real roots.
Use one predetermined block width and sweep limit.
Give prior codes to a compatible warm model-only control.
Report candidate preparation, coefficients, verification, continuation, and total kernel time.
Preserve every failed or missing cell.

If its verification cost already exceeds sequential quantization, reject the route before full-model work.
If it passes, test a small deletion fraction under a new prospective protocol.
Half-deletion observations cannot establish performance at a smaller deletion fraction.
Conversely, smaller deletions cannot repair an inherently expensive verifier.

## 7. Operation-count dominance in the present service

This section concerns `CompactIdentityService` and its current stream implementation.
It does not establish a limit for every possible repair algorithm.
It also does not establish a universal wall-time ordering.

### Theorem: complete replay after a changed ancestor

Assume N nonempty retained records and J required quantized stages.
Assume both compared executions complete successfully.
The repair cache requires equality of the complete quantized ancestor prefix.
Its state contains factors, but no complete resumable decoder frontier.
Each newly created source stream starts at the first factor.
The stream follows the same fixed finite target as fresh reconstruction.
Assume prefix bindings distinguish the unequal code sequences used here.

Suppose the retained model differs from the prior model before the final stage.
Let k be their first differing stage, using indices from zero.
Then the repair executes exactly NJ neural stage-record pairs.
It also reads N(k+1) cached factors before that replay.
Fresh model-only reconstruction executes the same NJ neural stage-record pairs without those cache reads.

### Proof

Before stage k+1, every ancestor code agrees with the prior model.
Each retained record therefore supplies its first k+1 factors from the cache.
The changed code at k remains inside every later ancestor prefix.
Every later prefix check therefore fails for every retained record.

The first failure creates a source stream at its first factor.
The stream then advances to the requested factor.
Later failures continue the same stream through the final required factor.
Thus, every retained record evaluates each of the J factors once.
Fresh reconstruction follows that same complete source stream.
Earlier cache reads do not remove any operation from the later source stream.
This proves both counts.

The theorem also covers k=0.
Its counts then become NJ neural pairs and N additional cache reads.
It excludes a change confined to the final stage.
Such a change has no later required calibration factor.

### Corollary: service work against a warm model-only control

Give both methods the same prior codes, backend, grids, limits, and retained records.
Count source-stage evaluations, quantizer calls, code packing, cached-factor reads, and factor packing separately.
Call this vector the declared service work vector.

Both methods make J quantizer calls and pack J output code arrays.
Both execute NJ source-stage evaluations under the theorem's conditions.
Both supply the same mathematical factors and prior-code proposals to quantization.
Repair additionally reads N(k+1) cached factors and packs NJ current factors.
It also validates prior membership and constructs the complete factor state.
The model-only control does neither operation.

Repair's declared work vector is therefore componentwise no smaller than the warm model-only control's vector.
At least the cached-factor and factor-packing components are strictly larger.
Fixed, nonnegative common charges for these operations preserve this ordering.

The vector counts routine work, not every machine instruction.
Equal numerical solver inputs and a deterministic solver also give equal internal solver traces.
This stronger statement requires identical runtime and numerical bindings.
It must not be inferred from equal final codes alone.

The two methods produce different persistent outputs.
Repair produces the complete factor state; model-only reconstruction produces only the model.
The comparison therefore isolates the additional cost of that state.
Indexed fresh receives the same state and follows the same repair path.

### Observed count checks

The archived progress files contain these complete transaction counts.
The revision 15 fresh control used no proposal.
The listed revision 17 fresh control also used no proposal.
These rows verify the replay count, not a measured warm-control speed claim.

| Revision and attempt | Method | Retained records | Neural pairs | Cache reads |
|---|---|---:|---:|---:|
| v15/attempt-002 | repair | 1 | 24 | 1 |
| v15/attempt-003 | model-only fresh | 1 | 24 | 0 |
| v15/attempt-004 | indexed fresh | 1 | 24 | 1 |
| v15/attempt-005 | direct fresh | 1 | 24 | 0 |
| v17/attempt-003 | repair | 1 | 24 | 1 |
| v17/attempt-004 | model-only fresh | 1 | 24 | 0 |

Each row comes from `pilots/REVISION/ATTEMPT/outputs/progress.json`.
Every listed repair reports 23 changed-ancestor pairs and zero avoided pairs.
No current measurement is required for the theorem's proof.

### Consequence for the next algorithm

A faster shared quantizer cannot remove this service work difference.
A warm advantage against a cold comparator remains possible.
The warm model-only comparator receives that same possible advantage.
The repair method must therefore save other work or provide a separately justified state benefit.

A resumable decoder frontier could remove catch-up evaluations.
Exact transport could remove required factor evaluations.
Both changes require new implementation, state semantics, and complete cost accounting.

A common compiled kernel can reduce both K_c and K_w.
That improvement can make the implementation practical.
It does not establish a deletion-specific advantage.
It can also reduce the fraction of total time available for quantizer savings.

Thus, the next complete comparison needs three distinct findings.

1. The cheaper certificate must beat optimized sequential quantization.
2. Warm proposals must improve the same kernel beyond nearest proposals.
3. The complete method must retain that saving after state and replay costs.

The first finding alone cannot support the full-model speed claim.
The warm model-only control remains necessary after any shared kernel improvement.
Indexed fresh must receive identical surviving factors and the same solver policy.

No theorem in this document proves a reliable full-model speedup.
The empirical budget remains inherited and unchanged.
