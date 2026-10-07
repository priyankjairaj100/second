# Revision 14: exact transport and the complete-state boundary

Date: 7 October 2026.
Status: theoretical review; no new empirical claim.

The existing modules do not establish a reliable full-model repair speedup.
They establish exact codes, complete current-factor state, and conditional box certificates.
Those results have different information requirements.
This document makes those requirements and their cost consequences explicit.

## 1. The exact contract

Let the retained records be R.
Let P_j(R) contain the exact quantized ancestors before stage j.
For each retained record r, define its target factor by

\[
Z_{r,j}(R)=\operatorname{FiniteFeature}(W,r,P_j(R)).
\]

The numerical target fixes every finite operation and every quantizer tie rule.
The `factor_identity_v1` state contains each exact binary64 factor.
Its canonical encoding identifies both signed zeros with positive zero.
It also contains the retained codes and current prefix bindings.

Matching the quantized model does not alone match this state.
An accepted code box can contain several different canonical factor arrays.
Those arrays can produce the same model codes.
A complete repair must nevertheless identify the required array.

**Abstraction boundary.** Suppose a proof transcript only establishes that Z belongs to a set U.
If U contains two different canonical factor arrays, that transcript alone cannot certify one factor array.
This remains true when the quantizer is constant throughout U.
A factor-producing conclusion needs stronger information, such as a singleton enclosure or exact transport.

This is a statement about the certificate's information.
It is not an impossibility theorem for the actual transformer.
The fixed weights, retained tokens, and new prefix already determine the actual factor.
An algorithm may exploit their structure more effectively than the present certificate does.

## 2. Calibration-independent anchors are sufficient, not necessary

A separate canonical anchor state is one sufficient design.
The conditional theorem in `TOKEN_BOX_CERTIFICATE_V13.md` describes that design.
It still needs a cheap, sound bound provider.

Such anchors are not necessary for every exact repair algorithm.
An algorithm can retain the current state family instead.
It must then compute the new factors or prove their exact values.
In particular, a changed prefix can produce an unchanged factor.
A valid proof permits copying that factor and rebinding its prefix.
The old factor's calibration history does not invalidate a proved exact equality.

History-dependent *unverified* reuse remains invalid.
Merely retaining the old prefix hash also remains invalid.
The serialized result must contain the current canonical prefix binding.

## 3. A concrete exact gate using the present factors

There is a narrow transport gate that needs no new numerical target.
It also needs no additional persistent state fields.
It is not implemented or empirically evaluated here.

Consider a quantized affine stage with old matrix Q and new matrix Q'.
Assume its complete live execution state is identical before the affine operation.
In particular, the stage input factor X is identical.
Let

\[
D=\{(a,h):Q'_{ah}\not\equiv_{\mathrm{bits}} Q_{ah}\}.
\]

For every token t and every changed entry, check

\[
\operatorname{RN}(Q'_{ah}X_{th})
\equiv_{\mathrm{bits}}
\operatorname{RN}(Q_{ah}X_{th}).
\tag{1}
\]

Use the target's separate multiplication operation and its checked runtime.
Do not replace this check with a real-valued dot-product identity.
Do not permit fused multiplication and addition.
Bitwise comparison makes the gate conservative about signed zero.

The stored factor replaces both feature zero signs with positive zero.
This does not invalidate the equality test under its live-state invariant.
For nonzero features, the stored value already has the actual feature bits.
For zero features, the old and new live executions have the same zero sign.
For a zero feature, finite binary64 multiplication gives a zero sign equal to the operands' sign-bit exclusive-or.
Replacing a common negative-zero feature by positive zero therefore flips both compared product signs.
Flipping both signs preserves whether their bits agree.
This also holds when either coefficient is a signed zero.
Thus, the test can use canonical positive-zero factors without recovering their original zero signs.
The coefficients must still be the actual installed target coefficients.
This argument does not authorize changing their signs or accepting nonfinite coefficients.

**Product-identity lemma.** If every check in (1) passes, the affine output is bitwise unchanged.

**Proof.** Unchanged weights and inputs give unchanged products.
Equation (1) gives unchanged products at every remaining coordinate.
The bias and initial accumulator are unchanged.
Each ordered addition therefore receives identical operands.
Induction through the declared reduction gives identical output bits.

All fixed operations before the next quantized stage then receive identical operands.
Consequently, their outputs and complete live execution state remain identical.
The next cached factor is exact under the new prefix.
Its values can be copied into a newly bound `RecordFactor`.

This argument covers the declared attention, residual, normalization, and activation schedules.
It relies on equality of the complete live state before the affine stage.
Equality of one exposed factor alone need not establish that invariant.
A residual stream can contain information absent from that factor.

### A valid staged algorithm

For each retained record, maintain an `unchanged_live_state` flag.
Initially, the flag is true because embeddings and fixed parameters are unchanged.

1. Obtain each stage factor from a proved cache hit or exact replay.
2. Run the ordinary exact retained-data quantizer for that stage.
3. Compare the old and new stage matrices to identify changed entries.
4. For records whose flag remains true, run (1).
5. Preserve the flag only when every required product matches.
6. On failure, start the exact sequential source stream under the new prefix.
7. Serialize every exact factor with its current prefix binding.

The final quantized stage requires no outgoing product check.
No later calibration factor depends on that stage's output.

After a failed gate, comparing exposed factors alone cannot restore the flag.
Restoration would require proving equality of the complete live execution frontier.
That frontier is not stored by `factor_identity_v1`.

**Complete-state correctness.** Every reused factor has a finite-operation equality proof.
Every other factor comes from exact replay.
The ordinary stage quantizer therefore receives exactly the fresh retained factors.
Induction over stages gives fresh retained codes and factors.
Canonical serialization then gives the complete fresh retained state.

The argument assumes trusted prior state provenance and unchanged retained token identities.
It inherits the service's target, membership, runtime, and input-validation requirements.
It does not turn content hashes into execution proofs.

### Costs and a crucial catch-up effect

Discovering changed entries costs O(p_j d_j) using a dense comparison.
This comparison can share a traversal with code construction.
Its actual overhead must still be charged.

For a record with T_r tokens, a stage's product gate costs

\[
O\!\left(T_r|D_j|\right)
\]

multiplications and comparisons, besides input and metadata access.
A failed comparison can terminate that record's gate early.

The existing state does not store a complete resumable decoder frontier.
Thus, a late failed gate starts the source stream from the record's beginning.
That replay recomputes earlier factors which had already passed gates.
These recomputations must count as retained-source work.
A provisional cache hit must not be reported as permanently avoided computation.

With this fallback, any record that eventually fails can incur its whole fresh feature traversal.
Only records passing every required gate can avoid that whole traversal.
The precise result depends on the declared streaming schedule and final feature boundary.
It does not depend on how the diagnostic counters are named.

A resumable-frontier extension could change this catch-up cost.
It would need a new complete state contract and its own storage accounting.
It is not part of the algorithm above.

## 4. Why this exact gate has a narrow acceptance regime

The target uses fixed uniform low-bit grids.
At one changed matrix entry, write the old and new values as ks and ls.
Here, s is positive, k and l are different integers, and |k|, |l| are at most K.
For the present 2–8 bit grids, K is at most 128.

Suppose x is nonzero.
Assume every nonzero exact product ksx and lsx lies in the normal binary64 range.
Assume their rounded products remain finite.
For binary64 round-to-nearest, let u=2^-53.
Then

\[
\begin{aligned}
|\operatorname{RN}(ksx)-\operatorname{RN}(lsx)|
&\ge |sx|\bigl(|k-l|-u(|k|+|l|)\bigr)\\
&\ge |sx|(1-2Ku)>0.
\end{aligned}
\]

A zero code contributes zero rounding error, so that case also satisfies the argument.
Thus, different codes cannot pass (1) on such a nonzero feature.

The gate can accept changed entries supported entirely on zero features.
It can also accept some underflow cases excluded by the normal-range assumption.
Bitwise signed-zero comparison can reject some otherwise harmless zero cases.
Other exact transport algorithms may exploit cancellation or later nonlinear saturation.
This lemma does not rule them out.

The gate therefore closes a logical possibility, not the practical efficiency gap.
It supplies no reason to expect broad acceptance on dense normal-valued transformer factors.
No acceptance rate is asserted without measurement.

## 5. Necessary and sufficient cost inequalities

Use one nonoverlapping additive cost measure throughout this section.
This can be deterministic operation cost or measured, attributed transaction time.
Common kernels and their optimizations must be available to every compatible baseline.
Measured timings still need the registered replication and uncertainty analysis.

For one retained request, write the model-only fresh cost as

\[
C=F+Q+M.
\]

Here, F is retained feature work, Q is quantization work, and M is other baseline transaction work.
Let A denote fresh feature work actually avoided by repair.
Let H denote all repair-specific overhead relative to those common components.
It includes failed gates, replay catch-up, validation, state I/O, and any additional certificate work.
Count each operation once.
If catch-up already appears in unavoided feature work, do not also include it in H.

When repair uses the same quantization schedule, its cost is

\[
C_R=C-A+H.
\tag{2}
\]

Equation (2) is an accounting identity under the declared partition.
It is not a claim that source avoidance is the only possible algorithmic improvement.
A separately justified quantizer saving can be added to A, with a distinct counter.

Strict request speedup holds exactly when A>H.
For a requested ratio rho>1,

\[
\frac{C}{C_R}>\rho
\quad\Longleftrightarrow\quad
A-H>\left(1-\frac1\rho\right)C.
\tag{3}
\]

For rho=1.05, net savings must exceed approximately 4.762% of fresh cost.
Since A cannot exceed F, a necessary condition is

\[
F-H>\left(1-\frac1\rho\right)C.
\tag{4}
\]

This condition can fail even with perfect feature avoidance.
The common quantizer and complete-state overhead can dominate the transaction.
A positive changed-ancestor avoidance fraction alone therefore cannot prove speedup.

For an ordered deletion sequence, let P_R and P_M denote actual preparation costs.
Let D=P_R-P_M be the preparation difference.
Let A_t, H_t, and C_t denote request costs.
Strict lifetime improvement holds exactly when

\[
\sum_t(A_t-H_t)>D.
\tag{5}
\]

A lifetime ratio above rho requires

\[
\sum_t(A_t-H_t)
>D+\left(1-\frac1\rho\right)\left(P_M+\sum_t C_t\right).
\tag{6}
\]

These inequalities include every required request and preparation exactly once.
A missing or failed required transaction leaves the registered complete comparison unresolved.
The inequalities do not create a confidence bound from one timing observation.

## 6. The full current-factor output has an unavoidable size

Let d_j be the factor width at stage j.
The current uncompressed canonical factor payload has exactly

\[
B_F=8\sum_{r\in R}\sum_j T_r d_j
\]

bytes, before metadata and model codes.
Materializing this explicit byte sequence costs Omega(B_F) output operations in the ordinary byte-output model.
The implementation also hashes and validates its serialized state.
These operations remain part of complete repair.

This is a representation-specific lower bound.
It does not prove a physical disk-bandwidth lower bound with filesystem cloning or shared storage.
It does not apply to a different compressed or symbolic canonical state.
Such representations require a separately declared state contract and measured operations.

## 7. Defensible closure

The current identity service cannot avoid changed-ancestor factor pairs by construction.
The new box certificate does not change that fact by itself.
Its current feature-box provider traverses retained tokens and must be charged accordingly.

Exact factor transport remains possible without changing the target or state family.
The product-identity gate proves this possibility under explicit, restrictive conditions.
Its normal-product limitation explains why it does not establish the desired practical result.

The remaining research requirement is therefore specific.
A successor must produce exact current factors cheaply, or introduce a separately declared canonical state with useful transport.
It must then satisfy equations (3) and (6) on the registered complete workloads.
Neither code constancy nor an isolated timing win closes those requirements.
