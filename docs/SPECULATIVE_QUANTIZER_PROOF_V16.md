# Speculative quantization with exact verification

This document states a correctness argument for the revision 16 solver.
The solver keeps the existing dyadic target.
It changes the evaluation schedule.
It does not establish a repair speedup.

The triangular fixed-point principle is established background.
QuIP equation (2) gives the adaptive rounding equation.
YAQA gives simultaneous updates and a dependency-depth convergence bound.
The short arguments below specialize these principles to our exact token-space target.
They are not new fixed-point or convergence claims.
See [the primary-source audit](NOVELTY_AUDIT_V16.md) for references and limitations.
The proposed technical contribution concerns certified finite arithmetic and valid partial continuation.

## Exact target

Let the original weights be \(W\in\mathbb R^{p\times d}\).
Let the exact feature matrix be \(Z\in\mathbb R^{d\times T}\).
Every stored binary64 value denotes its exact rational value here.
Write \(z_i\in\mathbb R^T\) for feature row \(i\).
Let \(\beta>0\) denote the fixed ridge-normalization product.
Define

\[
G_i=\beta I+\sum_{h\geq i}z_hz_h^\top,
\qquad u_i=G_i^{-1}z_i.
\]

Positive ridge makes each \(G_i\) positive definite.
Each output row has a fixed exact dyadic grid.
Let \(R_a\) select its nearest grid value.
At an exact midpoint, \(R_a\) selects the lower value.
The sequential target satisfies

\[
s_{a,i}(Q)=\sum_{h<i}z_h(W_{a,h}-Q_{a,h}),
\qquad
Q_{a,i}=R_a\left(W_{a,i}+u_i^\top s_{a,i}(Q)\right).
\]

The grid depends on the base weights alone.
The solver does not divide weights by a general dyadic scale.
`docs/TOKEN_SPACE_SOLVER_V12.md` proves equivalence with the dense reverse-elimination target.
The normalization remains fixed after deletion.

## Theorem 1: complete verification identifies the unique target

Define \(F\) by the right side of the displayed recurrence.
Let \(\widehat Q\) contain only values from the specified grids.
Suppose a sound verifier establishes

\[
F(\widehat Q)_{a,i}=\widehat Q_{a,i}
\quad\text{for every }a,i.
\]

Then \(\widehat Q\) equals the sequential target.

Proof: Coordinate zero has an empty prefix.
Its value therefore equals \(R_a(W_{a,0})\) in every fixed point.
Assume all preceding coordinates equal the sequential target.
Then the exact prefix accumulator also equals the sequential target accumulator.
Both procedures apply the same deterministic rounding rule to the same exact value.
Thus coordinate \(i\) also equals the sequential target.
Induction proves equality at every coordinate. \(\square\)

Output rows have no cross-row dependencies.
The verifier can therefore certify complete rows separately.
Each accepted row must pass every coordinate check.
Unaccepted rows can use the sequential fallback.

The argument permits any candidate generator.
The candidate can come from a previous model or an approximate parallel update.
Candidate generation needs no correctness claim.
An unsuccessful complete certificate cannot justify model publication.
The solver can retain a certified prefix internally.

## Theorem 2: the directed exclusive scan encloses every prefix

For each row and token coordinate, enclose the exact terms

\[
t_h=z_h(W_{a,h}-\widehat Q_{a,h})
\]

with directed elementary operations.
Pad the coordinate axis to the next power of two.
The padding terms equal exact zero.
Use the standard Blelloch scan tree.
Each tree addition combines lower endpoints downward and upper endpoints upward.

During the upward pass, each node encloses its exact subtree sum.
This statement holds for leaves by construction.
Interval addition preserves it at each parent.
Set the root prefix to the singleton zero interval.
During the downward pass, give each left child its parent's prefix interval.
Give each right child the sum of that prefix and the left subtree interval.
These assignments preserve the exact prefix invariant.
At each leaf, the resulting interval encloses the sum of all preceding terms.
Discard padded leaves. \(\square\)

The downward pass must copy any subtree value before an overlapping assignment overwrites it.
The scan must remain exclusive.
Its first prefix must equal exact zero.
No reduction through BLAS, `np.sum`, or `np.cumsum` enters this proof.

For \(D=2^{\lceil\log_2 d\rceil}\), the scan uses \(2(D-1)\) interval additions per scalar sequence.
It uses \(2\log_2 D\) rounds of independent additions.
A row batch requires storage proportional to \(DT\) times the batch size.
These are arithmetic counts.
They do not predict measured execution time.

## Corollary: verified prefixes permit exact continuation

Suppose a row passes every fixed-point check before coordinate \(k\).
The induction in Theorem 1 proves that its first \(k\) codes equal the target.
The exclusive scan at coordinate \(k\) encloses the corresponding exact accumulator.
The sequential solver can therefore resume from that interval.
Its ordinary induction and cell checks remain valid.
A bounded exact fallback must use those same certified prefix codes.

The implementation must store the prefix and accumulator from the same verified proposal.
It must preserve both if a later pass proves no longer prefix.
A zero-length prefix starts from the exact zero accumulator.
A complete prefix needs no sequential continuation.
Different rows can resume at different coordinates.
Before its resume coordinate, a row must receive no accumulator update.
Previously proved prefix codes can remain fixed during later speculative updates.

Scan intervals can be wider than the sequential intervals.
Thus prefix continuation can require additional exact fallback.
Correctness does not imply lower cost.
Count each distinct certified prefix coordinate once in mechanism diagnostics.
Repeated checks still count in execution costs.

## Coefficient error and cell verification

The existing residual verifier supplies a candidate \(c_i\) and a bound \(E_i\geq0\).
Its contract is

\[
\|u_i-c_i\|_2^2\leq E_i.
\]

The residual argument uses \(\lambda_{\min}(G_i)\geq\beta\).
Specifically,

\[
\|u_i-c_i\|_2
\leq \frac{\|z_i-G_ic_i\|_2}{\beta}.
\]

Candidate inverse updates remain untrusted.
Directed residual evaluation provides the error bound.
The scan provides an interval box \([\ell_{a,i},r_{a,i}]\) containing the exact accumulator.
Directed operations enclose

\[
W_{a,i}+c_i^\top s_{a,i}
\in[L_{a,i},U_{a,i}].
\]

Let a directed upper bound satisfy

\[
S_{a,i}\geq\sum_k\max(|\ell_{a,i,k}|,|r_{a,i,k}|)^2.
\]

Cauchy-Schwarz gives

\[
|u_i^\top s_{a,i}-c_i^\top s_{a,i}|
\leq\sqrt{E_iS_{a,i}}.
\]

Therefore the exact rounding input lies in

\[
[L_{a,i}-\sqrt{E_iS_{a,i}},
 U_{a,i}+\sqrt{E_iS_{a,i}}].
\]

The implementation can compare squared positive gaps without evaluating a square root.
It must round the squared gap downward.
It must round the radius squared upward.
A strict lower boundary implements the lower-code midpoint rule.
An inclusive upper boundary implements the same rule.
A strict test on both boundaries remains sound but can abstain at a valid tie.
When the radius is zero, an explicit inclusive upper test can accept an exact tie.
The extreme grid cells have only one finite boundary.

A midpoint of an enclosure can select a candidate index.
That selection does not certify the index.
The full containment test provides the certificate.

## Arithmetic premises

Elementary binary64 operations must use round-to-nearest with gradual underflow.
`nextafter` must move to the adjacent representable value in the requested direction.
The existing runtime checks test necessary parts of these premises.
They do not prove every property of arbitrary hardware or modified numerical libraries.

The scan rejects nonfinite endpoints.
The cell verifier rejects nonfinite value bounds and squared radii.
Subnormal arithmetic uses outward neighboring values, including the smallest subnormal.
No relative-error assumption replaces these directed bounds.
An overflowing positive gap can produce the largest finite downward bound.
That value remains a valid lower bound.
A zero shortcut must preserve exact rational zero semantics.

The grid constructor must prove exact representation of codes and midpoint boundaries.
Inputs must remain immutable during verification.
Candidate shape, finiteness, and exact grid membership require validation.
Array subclasses must not replace trusted elementary operations.

## Bounded speculation and fallback

A fixed bound limits speculative updates.
Each accepted output has a complete certificate.
If speculation stops, sequential continuation computes the unchanged target.
It can start from a certified prefix or coordinate zero.
Its established exact-fallback limits still apply.
If that solver also fails, the operation returns no model.

Exact simultaneous updates recover at least one additional prefix coordinate per update.
This observation does not give the approximate implementation a finite convergence guarantee.
The practical solver must use its explicit update limit.
Near-boundary values can defeat interval certification even when a candidate is correct.

Compatible fresh methods must receive the same solver optimization.
A warm candidate may improve repair performance.
Theoretical correctness does not prove that empirical advantage.
Preparation, candidate scans, verification, and fallback all belong in reported costs.

## Theorem 3: exact parallel iteration needs at most d updates

Let \(Q^{(0)}\) be any finite candidate matrix.
Apply the exact simultaneous update

\[
Q^{(t+1)}=F(Q^{(t)}).
\]

After update \(t\), every coordinate before \(\min(t,d)\) equals the sequential target.

Proof: The first coordinate depends on no previous candidate coordinate.
Thus update one computes its exact target code.
Assume the first \(t\) coordinates are correct.
Update \(t+1\) uses only those coordinates when it computes coordinate \(t\).
It therefore computes the correct next code.
Earlier correct codes remain correct.
Induction proves the claim. \(\square\)

All output rows satisfy this argument independently.
Thus at most \(d\) exact updates recover the whole stage.
This is a depth bound for exact arithmetic.
It is not a practical runtime bound.
The implemented approximate update does not inherit this termination guarantee.
Its interval checks can remain unresolved at an exact target candidate.
A bounded fallback returns the target only if its numerical and resource limits permit completion.
Otherwise the solver fails without publishing a model.

## Theorem 4: prefix continuation reduces sequential decisions

Let \(k_a\in\{0,\ldots,d\}\) be the certified prefix length for output row \(a\).
Let

\[
K=\sum_{a=1}^{p}k_a,
\qquad M=\sum_{a=1}^{p}(d-k_a)=pd-K.
\]

A sequential continuation needs exactly \(M\) remaining grid decisions.
Coordinate \(i\) acts on the rows

\[
A_i=\{a:k_a\leq i<d\}.
\]

Therefore

\[
\sum_{i=0}^{d-1}|A_i|=M.
\]

This identity counts decisions once.
Repeated speculative checks are additional work.

Use one global continuation after all speculative batches finish.
That continuation combines every unfinished row at each coordinate.
It uses at most \(d-\min_{a:k_a<d}k_a\) sequential rounds.
There are no continuation rounds when every row is complete.
The implementation must not repeat the entire coordinate loop for each speculative batch.
Different row starts preserve the accumulator invariant proved above.

Without refinement or exact fallback, continuation arithmetic costs \(O(TM)\).
Coefficient construction still costs \(O(dT^2)\) in the existing implementation.
It occurs before speculation and does not disappear when \(K\) is large.
Exact fallback and coefficient refinement require separate cost terms.
Their cost depends on numerical difficulty and rational operand sizes.

Let \(D=2^{\lceil\log_2d\rceil}\).
Suppose speculative batch \(b\) uses at most \(B_b\) sweeps on \(p_b\) rows.
A conservative scan bound is

\[
2(D-1)T\sum_b B_b p_b
\]

interval additions.
Each sweep also constructs product intervals and verifies all candidate cells.
Those operations cost

\[
O\!\left(d(T+2^q)\sum_b B_b p_b\right),
\]

where \(q\) is the fixed grid bit count.
Completed rows can reduce the actual work below this bound.
Candidate validation and grid construction add further costs.

Thus \(K\) measures eliminated sequential decisions.
It does not measure total eliminated arithmetic.
It does not measure avoided feature construction.
Extra scans can make the complete solver slower despite a large \(K\).

## Complete-model benefit condition

For method \(m\), decompose a complete request cost as

\[
T_m=L_m+F_m+C_m+A_m+B_m+R_m+S_m+O_m.
\]

Use disjoint accounting categories:

| Term | Included work |
|---|---|
| \(L_m\) | Loading, target setup, input checks, prior state checks |
| \(F_m\) | Feature construction, replay, and factor access |
| \(C_m\) | Initial coefficient construction and residual certification |
| \(A_m\) | Grid setup, candidate construction, candidate validation |
| \(B_m\) | Speculative scans, cell verification, prefix bookkeeping |
| \(R_m\) | Sequential continuation, refinement, exact fallback |
| \(S_m\) | Canonical state construction and state verification |
| \(O_m\) | Output serialization, durable writes, and transaction completion |

The complete worker measurement must also include process startup and cleanup.
Assign those costs consistently to the declared categories or report them separately.
Do not sum overlapping timers.
The solver's internal timers do not cover every category.

Let \(f\) denote the matched fresh comparator and \(r\) denote repair.
Repair is faster on one request exactly when

\[
\sum_{X\in\{L,F,C,A,B,R,S,O\}}(X_f-X_r)>0.
\]

Since \(R_r\geq0\), a necessary condition is

\[
L_r+F_r+C_r+A_r+B_r+S_r+O_r<T_f.
\]

If this condition fails, eliminating every continuation decision still cannot give a speedup.
This condition includes costs that speculative prefixes cannot remove.
It provides an early rejection test after complete cost measurement.

Suppose \(P_m\) is the complete preparation cost for method \(m\).
For a request sequence of length \(J\), the preparation-inclusive condition is

\[
P_r+\sum_{j=1}^{J}T_{r,j}
<
P_f+\sum_{j=1}^{J}T_{f,j}.
\]

Equivalently,

\[
\sum_{j=1}^{J}(T_{f,j}-T_{r,j})>P_r-P_f.
\]

These exact accounting identities give necessary and sufficient cost conditions.
Prefix counts alone cannot establish either condition.
They also cannot establish statistical reliability across requests or roots.
Preparation must include any cache needed for later repair.
The model-only comparator has no retained state construction cost.
Repair retains its complete state cost in that comparison.
The indexed comparator must receive the same candidate information and compatible solver improvements.
A separate warm model-only control can isolate gains from access to deployed codes.
Any cold comparator must disclose its restricted candidate access.

## Scope and open claims

The verifier certifies model codes for supplied exact features.
It does not avoid constructing those features.
It does not reconstruct canonical factors from unchanged codes.
It does not certify an arbitrary transformed feature cache.
The existing identity service still replays changed prefixes.
Any repair-speed claim therefore needs a measured complete-model comparison.
Any source-avoidance claim needs a separate factor transport mechanism.

## Required software checks

Use exact rational sums to check every exclusive prefix.
Include width one, non-power-of-two widths, cancellation, subnormals, and signed zero.
Compare accepted codes against the independent dense rational oracle.
Include exact midpoints and both extreme grid cells.
Give the verifier malformed, off-grid, and intentionally wrong candidates.
Test nonfinite intermediates and forced fallback limits.
Verify that row batching changes neither codes nor target identity.
These fixtures test software correctness.
They are not empirical dataset evidence.

## Independent implementation review

The initial review inspected `src/speculative_dyadic_solver.py`.
Its downward pass uses advanced indexing to copy both child values.
Its upward and downward additions reject nonfinite endpoints.
It accepts complete rows only after every cell is certified.
It shares exact coefficients across fallback batches.
Its limits count unique exact and refinement coordinates.

A separate rational check tested 2,808 interval prefixes.
Widths were 0, 1, 2, 3, 5, 8, 9, 17, and 33.
The check used NumPy generator seed 160701.
Each width had twelve three-column arrays.
Centers used signs from {-1, 0, 1} and binary exponents from -1074 through 999.
Each input interval used the neighboring binary64 values around its center.
Exact rational sums lay inside every returned prefix interval.
An additional overflowing sum raised `LowRankUnresolved`.
These checks support the scan implementation, within its stated arithmetic premises.
They do not establish empirical speed or dataset quality.

The second review inspected prefix continuation.
The code stores the exclusive accumulator at the certified prefix length.
It copies certified codes before any exact suffix calculation.
It updates only rows whose continuation has started.
It maps active rows correctly during exact fallback.
No soundness defect was identified in these reviewed paths.
The separate test module checks independent dense rational target values.

## Revision 16 extension: bounded coordinate blocks

`src/block_speculative_dyadic_solver.py` limits each speculative scan to a coordinate block.
Its default block width is 32.
Its default row batch limit is 4,096.
Its default sweep limit is one.
These defaults define a development algorithm.
They do not establish optimal settings.

The solver computes all coefficients from the complete feature suffixes before processing any block.
It never computes coefficients from a truncated block metric.
Every coefficient therefore belongs to the unchanged exact target.

Let a block contain coordinates \(b,\ldots,e-1\).
Assume its incoming interval contains the exact accumulator

\[
s_{a,b}=\sum_{h<b}z_h(W_{a,h}-Q_{a,h}),
\]

where every preceding code already equals the target.
For a block candidate, the directed scan encloses

\[
\widetilde s_{a,i}
=s_{a,b}+\sum_{h=b}^{i-1}z_h(W_{a,h}-\widehat Q_{a,h}),
\qquad b\leq i<e.
\]

The same cell tests certify a contiguous candidate prefix inside the block.
Earlier certified blocks supply the induction base.
The fixed-point induction then proves every accepted block prefix.
Sequential continuation repairs the remaining suffix.
It uses global coordinates and all earlier committed codes during exact fallback.

A completely accepted block also needs its terminal accumulator.
The implementation encloses it with

\[
s_{a,e}
=s_{a,e-1}+z_{e-1}(W_{a,e-1}-Q_{a,e-1}).
\]

The exclusive scan alone does not contain this final update.
A repaired block obtains the terminal accumulator through its last sequential update.
The next block receives these sound terminal intervals.
Induction over blocks proves equality with the complete sequential target.

Each block freezes its incoming intervals before any row completes that block.
Different row batches cannot change another batch's incoming values.
Within a block, one continuation combines all unfinished rows.
Exact coefficient and refinement caches use global coordinate keys.
Their limits do not reset at block or batch boundaries.

Let \(k_{a,b}\) count the certified prefix decisions for row \(a\) in block \(b\).
Then

\[
K_{\mathrm{block}}=\sum_{a,b}k_{a,b},
\qquad
M_{\mathrm{block}}=pd-K_{\mathrm{block}}.
\]

These are block prefixes.
They need not form one uninterrupted prefix across the original candidate row.
Correcting an early block permits later blocks to certify their own candidates.
All scan and verification costs remain charged.
The complete-model cost condition above still applies.

The certificate workspace scales with block width, token count, and the row batch limit.
The implementation also retains the full output matrix and global coefficient arrays.
Candidate grid validation uses the same bounded coordinate blocks.
A smaller scan does not prove an execution-time improvement.

Nine focused tests passed for this implementation.
They compare output values with an independent dense rational oracle.
They cover every prefix length in a four-coordinate block.
They cover unequal row prefixes and corrected blocks followed by accepted blocks.
They verify terminal intervals across several accepted blocks.
They force exact fallback after a nonzero prefix in a later block.
They confirm that exact and refinement limits remain global.
They also cover midpoint ties, subnormals, partial final blocks, and zero sweeps.
An independent code review found no soundness defect in the reviewed paths.
No empirical result follows from these software fixtures.
