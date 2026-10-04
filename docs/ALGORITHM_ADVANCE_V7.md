# Revision 7: intersected covariance certificates

Date: 4 October 2026.
Status: proved conditional verifier, standalone implementation, and service integration contract.
Research experiments remain paused.
The target remains complete sequential `V_cert` quantization.

## 1. The concrete improvement

Revision 6 converts feature uncertainty into one relative spectral enclosure.
That conversion can reject a correct candidate because its scalar lower scale becomes nonpositive.
It also merges different coordinate effects into one displacement budget.

Revision 7 adds an exact interval verifier after spectral rejection.
The verifier retains signed covariance information and the target's fixed ridge.
It follows the actual reverse-LDL and rounding recurrence.
It can certify decisions without a positive relative lower scale.

Several sound enclosures can also be intersected before verification.
Their intersection can certify a candidate that every separate enclosure fails to certify.
A supplied two-dimensional rational fixture proves this strict gain.
This fixture checks mathematics and software only.
It is not an empirical dataset or evidence about language models.

Keep the existing spectral route first.
The new route supplements that route.
Replacing the spectral verifier would lose its distinct coverage advantages.

## 2. Fixed candidate and covariance contract

Fix one stage and its installed ancestor prefix.
Fix the retained records, source identities, normalization, grids, ridge, and coordinate order.
Let the complete normalized covariance be

\[
H^*=\lambda I+M_0^{-1}\sum_{j\in R}X_jX_j^\top,
\qquad \lambda>0.
\]

Thus `H* >= lambda I` follows from the target definition.
Fix any candidate matrix `q` whose entries belong to the frozen grids.
The candidate need not equal an earlier model.
It can come from an existing surrogate quantization.

A `GramBinding` records the target, stage, installed prefix, retained-set digest, and normalization.
Every intersected enclosure must use the same binding.
For different providers, hash the common retained record IDs and source digests.
Do not substitute provider-specific contribution digests for that common retained identity.
The caller must verify these fields against actual inputs.
The verifier cannot authenticate a false bound or an invented source history.

A `GramBox` specifies rational symmetric entry intervals

\[
\mathcal I_{ij}=[\ell_{ij},u_{ij}],\qquad H^*_{ij}\in\mathcal I_{ij}.
\]

The box can contain indefinite matrices.
The proof uses only its subset containing matrices above the declared ridge floor.
It does not certify positive definiteness of the entire rectangle.

## 3. R1: retain signed Loewner information

Suppose an existing provider proves

\[
-aI\preceq H^*-S\preceq bI,\qquad a,b\ge0.
\]

Set `c=(b-a)/2` and `r=(a+b)/2`.
Then

\[
\|(H^*-S)-cI\|_2\le r.
\]

Consequently,

\[
H^*_{ii}\in[S_{ii}-a,S_{ii}+b],\qquad
H^*_{ij}\in[S_{ij}-r,S_{ij}+r]\quad(i\ne j).
\tag{R1}
\]

Proof: each error eigenvalue belongs to `[-a,b]`.
Subtracting `c` places every eigenvalue in `[-r,r]`.
An entry magnitude never exceeds the operator norm.
Diagonal entries also obey the original Rayleigh quotient bounds.

This preserves asymmetric diagonal information.
The off-diagonal radius can improve on `max(a,b)`.
The radius is sharp without further information.
The matrix with diagonal `c` and off-diagonal `r` has eigenvalues `-a` and `b`.

The service stores raw uncertainty before normalization.
Divide both raw error magnitudes by `M0` before applying R1.
Include the ridge in the center exactly once.

## 4. R2: a common ridge survives every Schur complement

Partition an SPD covariance as

\[
H=\begin{pmatrix}A&B\\B^\top&C\end{pmatrix},\qquad H\succeq\lambda I.
\]

Its Schur complement `T=A-BC^{-1}B^T` satisfies

\[
x^\top Tx
=\min_y\begin{pmatrix}x\\y\end{pmatrix}^\top
 H\begin{pmatrix}x\\y\end{pmatrix}
\ge\lambda\|x\|_2^2.
\tag{R2}
\]

Therefore every true reverse-elimination pivot is at least `lambda`.
This fact concerns the actual covariance, not every rectangular interval matrix.

Before each interval division, intersect its pivot interval with `[lambda,infinity)`.
This intersection preserves every valid true pivot.
It also prevents division by an interval containing zero.
If this intersection is empty, the premises are inconsistent.
Raise an error or abstain without committing a model.
Never treat an empty set as a successful certificate.

## 5. R3: exact interval reverse-LDL

Initialize the interval matrix `A^(d)` from the supplied covariance box.
For `k=d-1,...,0`, compute

\[
[t_k]=[A_{kk}]\cap[\lambda,\infty),\qquad
[L_{ki}]=[A_{ki}]/[t_k]\quad(i<k),
\]

\[
[A_{ij}]\leftarrow[A_{ij}]-[A_{ki}][A_{kj}]/[t_k]
\quad(i,j<k).
\tag{R3}
\]

Use the exact interval square when `i=j`.
All endpoints are rational.
No floating tolerance or guessed eigenvalue enters the calculation.

Claim: these intervals contain the actual factors of every admissible covariance.

Proof: initialization contains each true matrix entry by assumption.
Assume the current intervals contain the true Schur complement.
R2 validates the pivot intersection.
Interval division by a positive interval contains the true multiplier.
Interval addition, subtraction, multiplication, and squaring contain the updated Schur entries.
Backward induction proves the claim.

Dependency overestimation can make these intervals very wide.
R2 prevents one division failure but does not remove that overestimation.
Rational numerator sizes can also grow substantially.

## 6. R4: exact decision certification

The target recurrence uses `B=I-L`.
For candidate row `q` and original row `w`, enclose each conditional input by

\[
[v_i]=w_i+\sum_{h<i}[L_{ih}](w_h-q_h).
\tag{R4}
\]

The candidate's rounding cell is `(m_lower,m_upper]`.
A missing endpoint represents the corresponding infinite endpoint.
Accept a coordinate exactly when

\[
\inf[v_i]>m_{\rm lower},\qquad
\sup[v_i]\le m_{\rm upper},
\]

for the finite endpoints that exist.
A singleton grid always has an unbounded cell.

These inequalities implement lower-code midpoint ties exactly.
A positive-width interval may touch its inclusive upper boundary.
It may not touch its exclusive lower boundary.

Claim: acceptance at every row and coordinate proves exact target codes.

Proof: coordinate zero has no earlier candidate assumptions.
Assume earlier candidate coordinates equal the true codes.
R3 and R4 then enclose the true current input.
The cell test proves its deterministic code equals the candidate.
Coordinate induction proves each row.
Applying the same argument at every stage proves the complete model.
All required feature evaluations and resources must still succeed.

The verifier checks all coordinates even after finding a failed check.
A failed earlier check makes later checks conditional only.
The final result remains false unless every check passes.

## 7. R5: intersection and acceptance monotonicity

Let `I_1,...,I_B` be sound boxes for the same bound covariance.
Define their entrywise intersection `J=intersection_b I_b`.
Then `H*` belongs to `J`.
Intersection is commutative, associative, and idempotent.
The implementation canonicalizes evidence identities.

Fix the same candidate, ridge, grids, weights, and operation schedule.
If `J` is contained in `I`, every factor interval computed from `J` is contained in its counterpart from `I`.

Proof: interval sum, difference, product, and square are inclusion isotone.
Intersecting a pivot with the same ridge half-line preserves inclusion.
Division on positive intervals also preserves inclusion.
Induct over the elimination operations and then the decision expressions.

Therefore

\[
\operatorname{Accept}_{\rm box}(I,q)
\Longrightarrow
\operatorname{Accept}_{\rm box}(J,q).
\tag{R5}
\]

This statement requires valid nonempty premises and completed arithmetic.
It does not cover changed candidates or changed numerical targets.
Resource limits may abort the narrower calculation.
The theorem does not promise that an implementation finishes under every finite resource cap.

An implementation can preserve already accepted cell checks during refinement.
Only previously unresolved cells need another containment test.
Factor intervals still require valid recomputation or a separately proved incremental update.
The current implementation recomputes all intervals and checks.

## 8. Strict gain fixture

Use

\[
S_\pm=\begin{pmatrix}2&\pm9/10\\\pm9/10&2\end{pmatrix},
\quad \delta=91/100,\quad \lambda=1,
\quad H^*=2I.
\]

Both spectral balls contain `H*` because their actual error norm is `9/10`.
Both centers are positive definite.
Their centers minus the ridge are also positive semidefinite.

Take `w=(49/100,0)`, `q=(0,0)`, and grids `{-1,0,1}`.
Each separate entry enclosure allows a second input beyond one cell boundary.
Each separate interval verifier therefore abstains.
The revision 6 relative spectral verifier also abstains for both centers.

Their intersection has off-diagonal interval `[-1/100,1/100]`.
Its last pivot is at least `109/100` before any extra ridge clipping.
Therefore

\[
|v_1|\le(49/100)(1/109)=49/10900<1/2.
\]

The intersection verifier accepts both exact codes.
This establishes strict conditional certificate improvement.
It establishes no practical coverage frequency or speedup.

A second service fixture uses scalar width and an exact midpoint weight.
Its code is covariance-independent.
The interval route can certify it even when the relative lower scale is nonpositive.
This fixture exercises complete state equality after deletion.

## 9. Preserve the spectral route

The required portfolio rule is:

1. Run the existing spectral certificate with its original premises.
2. Return immediately when it succeeds.
3. Otherwise construct the signed entry enclosure and run R3–R4.
4. Return only if the new certificate succeeds.
5. Otherwise continue the original exact replay policy.

A spectral candidate can be reused after rejection.
When no positive relative lower scale exists, quantize the SPD proposal to obtain a candidate.
Candidate construction remains charged work.

This OR-composition preserves every successful existing stage check at the same proposal.
It can add successful stage checks.
It does not establish full-service latency or completion dominance.
New checks consume time, memory, and rational arithmetic.
Those costs can exhaust a finite global budget.
Never describe acceptance dominance as runtime dominance.

The `full_replay` control must continue to bypass both certificate routes.
The declared experiment configuration must record the chosen certificate policy.
The target and canonical index definition need not change.
Solver policy and source changes still require reproducible provenance.

## 10. Fixed domain banks and canonical deletion

A future bank may contain corpus-independent parameter domains `Theta_b`.
Bind every domain, anchor rule, finite proof program, and precision before accessing deletable calibration records.
Store intrinsic additive moments for every bank entry.
At a query, use only entries that contain the actual installed ancestor prefix.
Compute a covariance enclosure for each eligible entry.
Intersect those enclosures using R5.

For each record contribution `m_b(j)`, define

\[
M_b(R)=\sum_{j\in R}m_b(j).
\]

Then

\[
(M_b(C)-M_b(F))_{b=1}^B=(M_b(C\setminus F))_{b=1}^B.
\tag{R6}
\]

Exact subtraction and fixed ordering give canonical state independently of selected query entries.
Query choices must not silently delete bank entries from canonical state.
Changing domains or anchor rules requires charged index reconstruction.

A fixed singleton prefix gives a useful limiting case.
Compute its actual finite features as intrinsic anchors.
Its feature error is exactly zero whenever that exact installed prefix recurs.
This requires explicit finite evaluation at the singleton prefix.
Shrinking an ideal interval does not automatically erase finite error bounds.

A bank containing every finite grid prefix can avoid retained feature scans in principle.
Its size can be exponential in ancestor coordinates.
Distinct rational codes that install identical finite parameters should share one prefix identity.
Further sharing requires a proved functional equivalence.

Banks therefore present a storage–query tradeoff, not a free repair method.
The revision 7 standalone intersection API supports their eventual proof interface.
The current canonical service does not yet store a multi-domain bank.
Single-enclosure portfolio integration requires no such redesign.

## 11. Costs and adaptive scheduling

One intersection of `B` dense boxes costs `O(B d²)` rational comparisons.
The interval factorization costs `O(d³)` rational operations.
All row checks cost `O(p d²)` rational operations.
These counts exclude bit lengths, metadata validation, and matrix construction.
They do not depend on retained record count after the enclosures exist.

For fixed-box banks, independent extraction and stored moments can grow linearly with bank size.
A bank with `B` entries uses up to

\[
B\sum_\ell G_\ell(d_\ell^2+6)
\]

rational moment slots, plus every domain description and source binding.
Deleting `k` records can require regenerating their contributions for every entry.
Those costs belong in the service and lifetime ledgers.

An adaptive query schedule can stop after any sound certificate succeeds.
It can skip re-verification when a new enclosure leaves the intersection unchanged.
This skip requires exact interval comparisons.
It can use a fixed cost order or a frozen prediction rule.
Selection cannot weaken correctness because every admitted bound must remain sound.

No distribution-free cost advantage follows from choosing the smallest-looking box.
An opaque bank may contain one useful entry at the last inspected position.
Any deterministic query order can then pay for every entry.
A clairvoyant comparator would inspect only the useful entry.
A constant competitive guarantee against that comparator needs additional assumptions.

A speculative phase can instead use a declared work cap.
If its cost is at most `alpha B0`, and complete fallback costs at most `B0`, total cost is at most `(1+alpha)B0`.
Here `B0` must be a justified work budget for that same request.
It cannot be an observed average runtime reused as a worst-case bound.
Preemption, cleanup, serialization, and failed work count toward the cap.
This elementary bounded-overhead guarantee is not a speedup theorem.

## 12. Boundaries and publication claim

Classical interval intersection, inclusion monotonicity, and interval elimination are established tools.
Schur complement variational identities are also established tools.
This document claims no priority for them.

The defensible contribution is their target-specific composition:

- signed covariance contraction from intrinsic deletion summaries;
- ridge-safe factor enclosures for the exact sequential quantizer;
- exact lower-tie cell verification;
- canonical repeated deletion despite adaptive certificate selection;
- explicit separation of accepted coverage, work, storage, and runtime.

That composition still needs real-model evidence.
No theorem here proves useful language-model acceptance or reliable full-model speedup.
The same bank and verifier must be available to equally indexed fresh computation.
A gain over that comparator must arise from justified state maintenance or another stated mechanism.

Primary source check:

- S. M. Rump, *Verification methods: Rigorous results using floating-point arithmetic*, Acta Numerica 19, 287–449, 2010.
  Sections 5–6 discuss inclusion and dependency effects.
  Section 10.1 shows severe limitations of direct interval Gaussian elimination.
  https://www.tuhh.de/ti3/rump/intlab/ActaNumerica2010.pdf
- Jean Gallier, *The Schur Complement and Symmetric Positive Semidefinite (and Definite) Matrices*.
  The author-hosted notes develop the Schur complement identities used here.
  https://www.cis.upenn.edu/~jean/schur-comp.pdf

These sources support the classical foundations and limitations.
They do not establish the novelty of the calibration-deletion application.
A separate current literature audit remains necessary before a priority claim.

## 13. Implementation evidence

`src/domain_refinement.py` implements exact rational interval operations, signed contraction, binding checks, intersection, reverse-LDL, and candidate verification.
`tests/test_domain_refinement.py` covers strict gain, exact factors, ties, saturation, inclusion, binding mismatch, invalid input, and singular premises.
The module exposes that its enclosure and ridge premises remain caller-verified.
Standalone tests do not establish a complete bank implementation.
Service integration and its test results belong in the final revision validation record.

The aggregate service now exposes `verifier_policy="spectral_or_interval"`.
The default remains `"spectral"`.
The optional route uses the current provider's single signed enclosure.
It requires no extra canonical index state.
The scalar service fixture verifies complete retained-state equality and zero retained replay.
It also checks that candidate construction and interval factorization appear in the work ledger.
