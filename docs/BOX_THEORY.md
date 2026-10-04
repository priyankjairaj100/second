# Fixed-box certificates for calibration deletion

Date: 4 October 2026.
Status: mathematical contract for the revision 6 implementation.

This document extends the preparation package.
It contains no research measurements.
It leaves the quantization target unchanged.
The target remains the successful execution of `V_cert` followed by exact rational quantization.

## 1. Purpose and scope

A small affine chart can reject ordinary quantized prefixes.
A full coordinate chart avoids that rejection but creates large derivative arrays.
A fixed parameter box provides another route.
It covers ancestor parameters directly and requires no derivative arrays.

This route replaces affine representation with interval inclusion.
It does not establish useful certificate acceptance.
A broad box can produce weak bounds or unavailable evidence.
These outcomes require retained replay.

The underlying interval rules and Gram perturbation inequality are standard tools.
This document does not claim those tools as new mathematics.
The relevant contribution concerns their deletion interface and complete sequential target.

## 2. Definitions and assumptions

Fix a quantization stage `ell`.
Let `theta` collect its installed ancestor parameters.
Let `Theta_ell` be a fixed axis-aligned box containing those parameters.
Construct the box from fixed weights, target grids, and a fixed recipe.
Do not construct it from the deletable calibration corpus.

The box must contain the actual installed binary64 parameters.
Exact rational grid endpoints alone do not specify those parameters.
Apply the decoder's conversion before constructing or checking the box.
Include the converted base parameters when missing prefix entries use those parameters.

Let `X_ell,j(theta)` denote the actual finite feature matrix for record `j`.
It has `d_ell` rows and `t_j` columns.
The anchor rule has two deterministic branches.
If every ancestor parameter equals its fixed finite base value, evaluate the finite base feature.
Set its feature error to zero.
Otherwise, choose each interval midpoint after the fixed enclosure program completes.

Thus

\[
Z_{\ell j}=\begin{cases}
X_{\ell j}(\theta_{\rm base}),&\text{fixed-base domain},\\
\operatorname{mid}([l_{\ell j},u_{\ell j}]),&\text{otherwise}.
\end{cases}
\]

Interpret successful binary64 anchor outputs as exact dyadic rationals.
Compute interval midpoints by exact rational arithmetic.
The anchor is intrinsic because its definition excludes other calibration records.
The branch depends only on the fixed domain, not the calibration corpus or deletion request.

Assume the following conditions.

| Condition | Requirement |
| --- | --- |
| Fixed target | Bind weights, grids, order, ties, conversion, ridge, normalization, and finite operation schedule. |
| Fixed proof | Bind the box, anchor, interval precision, provider source, and primitive source. |
| Input identity | Bind token records, record boundaries, source digests, masks, and positions. |
| Sound intervals | Enclose the ideal feature value and every discrepancy from the finite operation schedule. |
| Exact state | Add, subtract, compare, and serialize rational contributions exactly. |
| Trusted origin | Authenticate committed state or trust the declared state interface. |
| Completion | Require all necessary target evaluations and enough resources to complete the request. |

`V_cert` remains a partial finite program.
A proof failure makes the descriptor unavailable.
A necessary target evaluation can separately fail.
Such a failure aborts the request without an approximate model.

## 3. B1: Uniform finite feature bound

For each feature entry, let interval propagation return

\[
f_{\ell j,ab}(\theta)\in[l_{\ell j,ab},u_{\ell j,ab}],
\qquad
|X_{\ell j,ab}(\theta)-f_{\ell j,ab}(\theta)|
\le e_{\ell j,ab},
\]

for every `theta` in `Theta_ell` where the target succeeds.
Here `f` is the ideal real feature map under the same operation graph.
The uniform finite discrepancy includes all parameter conversion and operation errors.
Parameter conversion contributes zero additional error when box coordinates already denote installed finite parameters.

Set

\[
c_{\ell j,ab}
=\max\{|l_{\ell j,ab}-Z_{\ell j,ab}|,
        |u_{\ell j,ab}-Z_{\ell j,ab}|\}
  +e_{\ell j,ab}.
\]

For the midpoint branch, this simplifies to

\[
c_{\ell j,ab}
=\tfrac12(u_{\ell j,ab}-l_{\ell j,ab})+e_{\ell j,ab}.
\]

For the fixed-base branch, use `b_ell,j = 0` directly.
The interval branch chooses a rational upper square root and defines

\[
b_{\ell j}
\ge\sqrt{\sum_{a,b}c_{\ell j,ab}^{\,2}}.
\]

Then

\[
\|X_{\ell j}(\theta)-Z_{\ell j}\|_F\le b_{\ell j}
\quad\text{for every covered successful prefix.}
\tag{B1}
\]

Proof: the interval bounds each ideal entry's distance from its anchor entry.
The triangle inequality adds the finite discrepancy.
Sum squared entry bounds and take an outward square root.
No derivative or affine coefficient appears in this proof.
For the fixed-base branch, the actual feature equals its anchor throughout the declared domain.
That identity proves its zero error without interval propagation.

Rank-zero `Jet` operations implement this interpretation.
Their derivative tuples are empty.
Their value intervals and finite discrepancies remain necessary.
A rank-zero box is not a claim that features remain constant.
The descriptor bounds all feature changes inside the box.

## 4. B2: Additive Gram evidence

For a fixed group `g`, let `R_g` contain its retained records.
Use the original fixed positive normalization `M_0,ell`.
Store

\[
S_{\ell g}=M_{0,\ell}^{-1}
\sum_{j\in R_g}Z_{\ell j}Z_{\ell j}^{\top},
\qquad
E_{\ell g}=M_{0,\ell}^{-1}
\sum_{j\in R_g}b_{\ell j}^{\,2}.
\]

Define outward bounds

\[
z_{\ell g}\ge\sqrt{\operatorname{tr}(S_{\ell g})},
\qquad
\epsilon_{\ell g}\ge\sqrt{E_{\ell g}},
\qquad
\delta_{\ell g}=2z_{\ell g}\epsilon_{\ell g}
+\epsilon_{\ell g}^{\,2}.
\]

For the actual normalized group Gram `H_ell,g(theta)`, B1 implies

\[
-\delta_{\ell g}I
\preceq H_{\ell g}(\theta)-S_{\ell g}
\preceq\delta_{\ell g}I.
\tag{B2}
\]

Proof: write `X_j = Z_j + Delta_j` and expand both Grams.
Apply the triangle inequality and Cauchy-Schwarz inequality to the cross terms.
Use the Frobenius norm to bound the operator norm.

Both anchor branches provide exact rational Gram contributions.
A midpoint anchor need not equal any actual neural feature.
The Gram proof requires only B1, so this distinction does not change exactness.

The implementation can contract the squared quantities directly.
Its outward rational result can exceed the displayed ideal square-root expression.
Use that actual result when testing acceptance.

The existing compact moment interface implements B2 with rank zero.
Its response basis contains one term.
Its error basis contains three terms: `(b_ell,j, 0, 0)`.
The query supplies empty coefficients and zero residual.
The omitted tangent Gram vanishes, so `beta = 0`.

These descriptors encode a uniform bound directly.
They do not require a Taylor remainder interpretation.
The scalar error matrix contains six triangular slots.
Only its first slot can be nonzero.

## 5. B3: Exact stage and complete model

Sum unresolved group proposals and exact replayed Grams.
Add the fixed ridge once.
Call this positive definite matrix `H_tilde`.
Let `Delta` be the sum of unresolved group budgets.
Then

\[
-\Delta I\preceq H^*-\widetilde H\preceq\Delta I.
\]

Because `H_tilde >= lambda I`, `Delta < lambda` gives

\[
\alpha\widetilde H\preceq H^*\preceq\omega\widetilde H,
\qquad
\alpha=1-\Delta/\lambda,
\qquad
\omega=1+\Delta/\lambda.
\]

Apply T4 from `PUBLICATION_THEORY.md` to this enclosure.
If every candidate code passes, the complete candidate matrix equals exact retained quantization.
Otherwise, replay another unresolved group under the current certified ancestor prefix.
Replay replaces its proposal and removes its uncertainty budget.

Process stages in dependency order.
At each stage, check the new installed ancestor parameters against the fixed box.
A failed check requires replay.
A successful check establishes B1's domain premise.
It does not establish B1's numerical proof or T4's rounding test.

Coordinate induction establishes each successful stage.
Stage induction establishes the complete retained-data model.
After every group replays, the service has the exact retained covariance.
Completion still requires successful necessary target evaluations and finite resources.

The implemented provider detects domains whose ancestor parameters are fixed at their finite base values.
Its actual finite features then equal the finite base anchor.
It assigns zero feature error and skips interval propagation.
The first stage always satisfies this condition because it has no quantized ancestors.
A successful anchor evaluation remains necessary.

## 6. B4: Canonical deletion and order independence

Each record contributes intrinsic rational moments and a fixed availability marker.
Fixed identifiers determine its group.
Deletion verifies the source digest and regenerates the same intrinsic contribution.
Exact subtraction produces the retained totals.

Thus

\[
\operatorname{Index}(C)-\operatorname{Contrib}(F)
=\operatorname{Index}(C\setminus F).
\tag{B4}
\]

The identity holds componentwise, including availability counts.
Canonical serialization removes dependence on summation or deletion order.
B3 determines the retained model.
The complete successful state therefore equals fresh construction on retained records.

Repeated and adaptive deletion requests preserve this result.
Each request must use the same fixed target and proof configuration.
Changing the box or anchor changes the index definition.
That change requires a separately charged index reconstruction.

The theorem concerns logical state.
It does not establish physical memory erasure.
It does not remove information already present in fixed base weights.

## 7. B5: Monotone uncertainty under deletion

Keep the box, anchor, precision, grouping, and original normalization fixed.
For retained sets `R_g'` contained in `R_g`, positivity gives

\[
\operatorname{tr}(S_{\ell g}(R_g'))
\le\operatorname{tr}(S_{\ell g}(R_g)),
\qquad
E_{\ell g}(R_g')\le E_{\ell g}(R_g).
\]

Monotone outward square-root evaluation therefore gives

\[
\delta_{\ell g}(R_g')\le\delta_{\ell g}(R_g).
\tag{B5}
\]

Unavailable descriptor counts also cannot increase after deletion.
Deleting the last unavailable record can make a group eligible for certification.

This property holds independently of the newly installed prefix within the same box.
It differs from a query-dependent affine response budget.
It can support conservative work planning across deletion requests.

It does not prove monotone certificate acceptance.
Deletion changes the proposal covariance, candidate codes, pivots, and margins.
A smaller uncertainty budget can accompany a smaller rounding margin.
It also does not prove lower total cost.
State validation and serialization can still dominate a request.

Renormalizing by the retained token count would invalidate this argument.
The declared target uses the original fixed normalization.

## 8. B6: Conditional acceptance threshold

Let `m_i` be a candidate code's positive distance from its finite rounding boundaries.
Use its reciprocal pivot `g_i` and preceding quantization error energy `E_i`.
For `E_i > 0`, define

\[
\tau_i=\frac{m_i}{\sqrt{g_iE_i}},
\qquad
\tau=\min_{i:E_i>0}\tau_i.
\]

T4 gives the displacement factor

\[
\frac{\omega-\alpha}{2\sqrt{\alpha\omega}}
=\frac{\Delta}{\sqrt{\lambda^2-\Delta^2}}.
\]

A sufficient strict acceptance condition is

\[
\frac{\Delta}{\lambda}
<\frac{\tau}{\sqrt{1+\tau^2}}.
\tag{B6}
\]

Zero-energy coordinates have zero certified displacement under T4.
They follow the target's exact tie rule.
Positive uncertainty at an exact midpoint provides no positive-margin guarantee.

For one pooled bound with anchor norm `z`, let `t = tau/sqrt(1+tau^2)`.
Then `2z epsilon + epsilon^2 < lambda t` suffices.
Equivalently,

\[
\epsilon<\sqrt{z^2+\lambda t}-z.
\]

This condition explains the role of tight feature bounds.
A proof of box coverage alone gives no control of `epsilon`.
Small deletion size also gives no control of this uniform box error.
The box includes prefixes that the current request never approaches.

For example, suppose every retained record has `b_ell,j >= b_0 > 0`.
Then

\[
\epsilon^2\ge |R|b_0^2/M_{0,\ell}.
\]

Removing one record need not make this quantity small.
For equal record lengths, it can remain nearly unchanged as corpus size increases.
This statement concerns a bound floor, not measured feature error.

## 9. B7: Limits of one fixed box

Let `X(theta)` range over one record's successful feature matrices inside the box.
Any uniform radius around any fixed anchor satisfies

\[
\sup_{\theta}\|X(\theta)-Z\|_F
\ge\tfrac12\sup_{\theta,\theta'}
\|X(\theta)-X(\theta')\|_F.
\tag{B7a}
\]

Proof: apply the triangle inequality through `Z` to each pair of feature matrices.
A wide actual feature range forces a large uniform error.
More interval precision cannot remove that range.
Dependency loss can make the computed error larger still.

The same argument applies to fixed Gram proposals:

\[
\sup_{\theta}\|H(\theta)-\widetilde H\|_2
\ge\tfrac12\sup_{\theta,\theta'}
\|H(\theta)-H(\theta')\|_2.
\tag{B7b}
\]

Suppose two covered prefixes produce different exact stage codes for the same retained records.
No sound certificate can declare one fixed code matrix correct throughout that box.
The current constant proposal uses the same enclosure for both prefixes.
Its universal rounding certificate must therefore abstain somewhere.
A prefix-dependent proof could distinguish these cases, but that requires additional information or computation.

These observations do not prove failure on real language models.
They disprove any unconditional acceptance or speedup claim for this route.

## 10. Resource comparison

Let `P` count quantized parameters in the complete model.
Let `P_A` count parameters in stages used by later stages.
Let `r` denote the existing affine chart's global rank.
Let `G_ell` denote the number of occupied groups at stage `ell`.

| Quantity | Current affine provider | Fixed-box provider |
| --- | --- | --- |
| Derivative coordinates | `r` | Zero |
| Interval components per scalar | `1 + r + r²`, plus finite error | One, plus finite error |
| Compact response slots per group | `(r + 1)d_ell² + r²` | `d_ell²` |
| Scalar error slots per group | `(r + 3)(r + 4)/2` | Six |
| Direction construction | Dense declared direction matrices | Box endpoints |
| Prefix check | Exact affine fit and radius check | Entrywise interval inclusion |
| Stored source bindings | `O(NL)` | `O(NL)` |
| Exact matrix quantization | Required | Required |
| Retained replay after failed proof | Required | Required |

The existing full coordinate recipe has `r = P_A`.
Its dense direction matrices contain `sum_s P_s²` rational slots.
That storage is an implementation property, not a lower bound for sparse coordinate representations.

The implemented full-grid box stores two rational endpoints per ancestor parameter.
Thus its endpoint count is `2P_A`.
A shared endpoint recipe could reduce those stored constants.

Aggregate storage becomes

\[
\sum_\ell G_\ell(d_\ell^2+6)
\]

rational slots, excluding bindings and model parameters.
This removes the global derivative-rank factors.
It does not remove the quadratic feature-width term.
Large exact Gram matrices can still exceed local memory.

The revised executor constructs each parameter matrix only when its stage needs that matrix.
It does not construct unused later matrices.
This change also applies to finite evaluation and the affine provider.
It preserves the scalar operation order.
Peak parameter-wrapper storage therefore depends on the largest accessed matrix, not their complete sum.
Other live activations and fixed model arrays still require separate memory.

Box propagation uses one interval value and one finite discrepancy per live scalar.
It removes Hessian construction but still executes the certified neural graph.
A nonconstant domain uses interval midpoints and requires no separate finite anchor evaluation.
A domain fixed at base evaluates its finite anchor and skips interval propagation.
These applicable costs recur when regenerating deleted contributions.

A prefix check costs `O(P_ell)` scalar comparisons at stage `ell`.
Repeating it for each group adds a group factor.
A request-local cache can reuse a check for the same immutable prefix and stage.
Such a cache must include the provider identity and prefix digest.
It must not persist hidden calibration features.

All counts exclude rational bit lengths, Python objects, serialization, and primitive refinement.
They provide no latency or memory guarantee.
Finite error growth can prevent proof completion before memory becomes the limiting factor.

## 11. Implementation map

| Result | Implementation |
| --- | --- |
| Fixed boxes | `ParameterBox` in `src/box_response_provider.py` |
| Complete converted grid coverage | `grid_box(decoder, target, provenance, precision_bits)` |
| Prefix inclusion | `BoxResponseProvider.contains_prefix` |
| B1 interval propagation | `BoxResponseProvider.feature_enclosures` |
| Intrinsic B2 moments | `BoxResponseProvider.intrinsic_moments` |
| Rank-zero query | `BoxResponseProvider.query` |
| Temporary parameter construction | `_StageWeights` in `src/certified_transformer.py` |
| B3 and B4 state machinery | Existing aggregate service and exact certificate engine |

The provider binds its box, precision, decoder identity, and source digest.
The service separately binds the complete quantization target.
A caller-provided provenance string does not prove historical corpus independence.
The generated recipe supplies the executable construction used by the runner.

## 12. Fixed box banks as a separate extension

A fixed bank can contain several boxes and anchors.
Construct every box before access to deletable records.
Store intrinsic moments for every bank entry.
At query time, select only entries that contain the installed prefix.
A deterministic selection rule can choose the smallest proved budget.

B1 through B4 then hold for each selected entry.
The canonical state contains all bank entries, regardless of query choices.
Changing the selected entry does not change that state definition.

A bank of `B` independently stored entries multiplies extraction and aggregate storage by up to `B`.
Cross-entry sharing requires a separate accounting argument.
A box added after seeing calibration data requires additional justification and retained-state reconstruction.

Worst-case coverage has an exponential cost.
Suppose `m` independent coordinates each have two possible values separated by `h`.
Any axis-aligned box with width less than `h` in every coordinate contains at most one grid vertex.
Covering all `2^m` vertices therefore requires at least `2^m` such boxes.
This argument does not rule out useful structured banks.
It shows why universal narrow coverage needs additional structure.

The revision 6 route does not claim this bank implementation.
Treat a bank as a separately reviewed extension.

## 13. B8: Optimal anchor for each interval envelope

Any intrinsic rational anchor supports B1 through B4.
It need not equal a finite base feature.
For a nonconstant box, choose the interval midpoint

\[
Z_{\ell j,ab}^{\rm mid}
=\tfrac12(l_{\ell j,ab}+u_{\ell j,ab}).
\]

Its entrywise radius becomes

\[
c_{\ell j,ab}^{\rm mid}
=\tfrac12(u_{\ell j,ab}-l_{\ell j,ab})+e_{\ell j,ab}.
\]

For every scalar anchor `z`,

\[
\max\{|l-z|,|u-z|\}\ge (u-l)/2.
\]

Thus the midpoint minimizes this interval-based entry bound.
Summing squared bounds gives no larger feature radius than any other anchor under the same intervals.
It also removes the separate finite base evaluation for that record and stage.
The implementation retains an exact finite anchor and zero error for a domain fixed at base.

This deterministic hybrid preserves intrinsic contributions and canonical deletion.
The provider manifest must bind the selected anchor policy.
A changed policy requires index reconstruction.

The midpoint does not necessarily improve decision acceptance.
It changes the proposal Gram, its norm, candidate codes, and rounding margins.
The final Gram error can also change without a fixed ordering.
Only the entry-bound reduction and removed anchor evaluation follow unconditionally.

The revision 6 provider implements this deterministic hybrid.
This optimality result concerns the rectangular interval envelope.
It does not claim optimality over the smaller set of reachable neural features.

## 14. Algorithmic assessment

The fixed-box route closes a specific implementation gap.
It permits complete grid-prefix coverage without full coordinate derivatives.
It also gives an intrinsic constant Gram and a prefix-independent additive error index.

It does not establish a new universal perturbation inequality.
It does not establish affordable complete model repair.
It does not establish a deletion-specific advantage over indexed fresh computation.
Both methods can use the same box index and stage planner.

The strongest present claim is a sound additional certificate route with smaller derivative storage.
Its practical value depends on feature bounds, rounding margins, replay work, and complete costs.
A useful paper still needs evidence that these conditions hold on real text and declared model targets.

The hybrid anchor reduces interval-based feature uncertainty and removes a separate finite evaluation for nonconstant domains.
The next theoretical improvement should reduce uncertainty further while preserving intrinsic additive state.
The next engineering improvement should avoid unnecessary ancestor work and repeated prefix scans.
Neither improvement permits a speedup claim before complete measurements.
