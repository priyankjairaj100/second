# Compressed-factor certification: bounded design review

Date: 8 October 2026.
Status: design review and a separate implemented verifier.
The implementation uses software fixtures only.
It preserves the fixed-feature numerical target.

## 1. Decision before expansion

Run one bounded screen on the existing retained first-stage factor.
First distinguish a loose certificate from a genuinely nonconstant feature box.
Do not expand a failing certificate into complete-model timing.

Use `block.0000.qkv` from the existing DistilGPT2 request.
The retained record is `wikitext2:train:article-row-5326`.
Its factor contains sixteen tokens and 768 features.
Its weight matrix contains 2,304 rows and 768 columns.
The original normalization remains 32 after deletion.
The ridge remains `1/100`.
Use four-bit output grids with 24 significant scale bits.

The revision 23 record reports approximately 0.595 seconds for this exact stage solver.
That observation excludes complete request costs and cannot establish future timing.
It supports trying complete endpoint solves before a small row sample.

## 2. What the current verifier proves

`certify_dyadic_box` accepts only when every factor in the box gives the same codes.
The trusted descriptor supplies the separate containment premise.
Hashes bind prepared content but do not independently prove containment.

The verifier first builds every suffix coefficient enclosure.
It then checks weight coordinates in their fixed order.
It rejects the stage when any output row remains unresolved.
It does not expose failed row indices in its current exception.
An unresolved exception does not establish a changed model.

For coefficient position $i$, write

\[
G_i(X)=\beta I+\sum_{h\ge i}x_hx_h^{\mathsf T},
\qquad
u_i(X)=G_i(X)^{-1}x_i,
\qquad \beta=\lambda M_0.
\]

The code uses a midpoint inverse to propose $p_i$.
It encloses the residual $x_i-G_i(X)p_i$ through interval Gram entries.
It divides the squared residual bound by $\beta^2$.
This follows from $G_i(X)\succeq\beta I$.
The rule is sound under its stated arithmetic premises.

Three effects can make this bound too large.

1. Separate Gram intervals discard dependencies between entries of each factor row.
2. The ridge floor ignores larger eigenvalues in the actual suffix metric.
3. The final norm bound ignores the direction of the accumulated quantization error.

The interval accumulator adds another source of overestimation.
Narrow feature cells do not guarantee sufficient final decision margins.
Millions of output decisions make a single near-boundary decision consequential.
This is a risk statement, not a measured rejection rate.

## 3. A decisive negative witness

Decode the exact finite matrices $L$ and $U$ from one descriptor.
Run the existing exact point solver separately on both matrices.
Keep every weight column and its original order.
Use the same grid, ridge, normalization, and fallback limits.

If

\[
Q(W,L)\ne Q(W,U),
\]

then no constant-output certificate can accept the complete box $[L,U]$.
Both endpoints belong to that box, which proves the assertion directly.
One unequal row suffices, provided each compared row uses all 768 columns.
Column truncation changes the suffix metrics and would invalidate this witness.
Row restriction preserves the independent quantizer target for those rows.

Store both endpoint hashes, model hashes, and the first differing coordinate.
Also store the complete mismatch count when both solves finish.
An unresolved point solve gives no disagreement witness.
Different floating proposals also give no disagreement witness.

Endpoint agreement proves only agreement at those two endpoints.
Mixed corners or interior factors can still give different codes.
The quantizer is not coordinatewise monotone in the calibration factors.
Therefore endpoint agreement cannot establish a universal positive claim.

The witness rejects the specified box certificate only.
It does not reject all compressed repair methods.
The descriptor also binds tokens and a defining feature computation.
Some box points need not arise from that computation.
Exact recomputation can still identify the true factor.

If useful, test two additional corners selected by fixed alternating signs.
Construct each coordinate directly from its stored lower or upper endpoint.
Record these as additional deterministic witnesses, not statistical samples.
Stop after finding the first sound disagreement.
Do not search many corners merely to obtain a favorable result.

## 4. A sound improvement for loose residual bounds

The following componentwise bound avoids relying only on the ridge floor.
`src/preconditioned_box_certificate.py` now implements this bound separately.
The earlier certificate and numerical target remain unchanged.

Fix one suffix and suppress its index.
Let $R$ be a finite approximate inverse of the midpoint metric.
Let $p$ be any finite coefficient proposal.
Use directed arithmetic to construct nonnegative $D$ and $t$ satisfying

\[
|I-RG(X)|\le D,
\qquad
|R(x-G(X)p)|\le t
\quad\text{for every }X\in[L,U].
\]

All absolute values and inequalities here are componentwise.
Require a proved row-sum bound

\[
\gamma=\|D\|_\infty<1.
\]

Choose a nonnegative vector $e$ and verify

\[
t+De\le e.
\]

Then

\[
|G(X)^{-1}x-p|\le e
\quad\text{for every represented factor }X.
\]

**Proof.** Put $z=G(X)^{-1}x-p$.
The exact identity

\[
z=R(x-G(X)p)+(I-RG(X))z
\]

gives $|z|\le t+D|z|$.
Since $\gamma<1$, the nonnegative Neumann series defines $(I-D)^{-1}$.
Therefore $|z|\le(I-D)^{-1}t$.
The verified supersolution gives $(I-D)^{-1}t\le e$.
This proves the claim.

The midpoint inverse already exists inside `_box_coefficients`.
Reuse it as an untrusted proposal, then certify its bounds.
An approximate inverse alone is not sufficient.
Any failed contraction test returns unresolved.

A scalar fallback takes

\[
e=c\mathbf1,
\qquad
c\ge\frac{\|t\|_\infty}{1-\gamma}.
\]

Round the numerator upward and the denominator downward.
Then verify the supersolution inequality explicitly.
Zero residuals and exact equalities require exact zero handling.
Finite arithmetic must not replace a failed strict inequality with a tolerance.

For an accumulator interval $s\in[s^-,s^+]$, let

\[
a_k=\max(|s^-_k|,|s^+_k|).
\]

The coefficient contribution to decision uncertainty is at most

\[
\sum_k a_ke_k.
\]

Combine this with an outward interval for $p^{\mathsf T}s$.
Apply the existing asymmetric cell boundaries and lower-code tie rule.
Intersect independently valid enclosures when both old and new methods succeed.
Keep the old enclosure when the new method cannot certify its premises.

The current implementation constructs every suffix preconditioner eagerly.
Its directed matrix products cost $O(dT^3)$.
It retains $O(dT)$ coefficient bounds and $O(T^2)$ temporary matrices.
Here $T=16$, but this cost can grow quickly with calibration size.
The stronger cell test runs only where the ridge cell test has unresolved rows.
Lazy construction at unresolved coordinates remains a possible future optimization.
That optimization requires a declared storage or recomputation policy for suffix information.
Do not claim this method is faster before measurement.

## 5. Other sound refinements

### 5.1 Dependency-aware residual evaluation

Let $X=C+\Delta$ with $|\Delta|\le E$.
For a fixed suffix, its residual has the exact expansion

\[
x_i-G_i(X)p
=c_i-G_i(C)p+\Delta_i
-\sum_{h\ge i}\left[
c_h(\Delta_h^{\mathsf T}p)
+\Delta_h(c_h^{\mathsf T}p)
+\Delta_h(\Delta_h^{\mathsf T}p)
\right].
\]

This representation retains each factor row's structure before forming Gram intervals.
It can supply a second valid residual enclosure.
Its numerical implementation still needs directed accumulation.
It need not improve every case.
Intersect valid enclosures instead of assuming one always dominates.

### 5.2 Precision and block refinement

At fixed blocks, the 24-bit cells lie within the 16-bit cells.
The codec already proves this nesting property.
A 16-bit endpoint witness does not reject the narrower 24-bit box.
A 24-bit witness does not justify further work on that same broad box.
It instead supports finer stored precision or exact fallback.

Increasing precision requires new trusted information.
A 16-bit descriptor cannot create its missing low-order bits.
Charge stored refinement bits or the feature computation that produces them.
Changing block sizes requires a new declared encoding policy.
Smaller blocks can reduce outlier-driven cell widths, but add exponent and framing bytes.

Runtime refinement must remain temporary under the current canonical state contract.
Persistent mixed precision needs a deterministic, source-local preparation rule.
Preparation must not choose surviving precision using deleted records.
Queries must not commit different descriptors because they followed different deletion histories.

For this one-record pilot, regenerating one factor often requires its whole ancestor computation.
Partial numerical refinement does not imply partial neural replay.
The full-model work ledger must charge the ancestor closure.

### 5.3 Partial row certification

Rows are independent once their shared feature matrix is fixed.
A future verifier can retain completed rows and report unresolved rows.
It can then use exact factors only for unresolved output rows.
This saves some numerical work when exact factors are already available.
It does not remove the neural work needed to regenerate those factors.
The current all-or-nothing interface does not implement this result.

## 6. Proposed screen within 120 CPU seconds

Register the complete order, stop rules, inputs, and budget before execution.
Use one CPU and one numerical thread.
Include process setup, native compilation, output, and controller costs.
Use the existing bounded worker controller and preserve all attempts.

| Step | Maximum CPU allowance | Required output |
|---|---:|---|
| Load, verify, and encode the retained factor | 20 seconds | Source and descriptor hashes; containment; bytes |
| Solve all-row lower and upper endpoints at 16 bits | 15 seconds | Exact results or unresolved status |
| Solve all-row lower and upper endpoints at 24 bits | 15 seconds | Exact results or unresolved status |
| Run the current 16-bit box verifier, unless disproved | 20 seconds | Accepted model or failure coordinate |
| Run the current 24-bit box verifier, unless disproved | 20 seconds | Accepted model or failure coordinate |
| Bounded diagnosis on the unresolved case | 20 seconds | At most two additional corner results |
| Seal receipts and leave termination margin | 10 seconds | Final budget and artifact bindings |

The total allowance is 120 CPU seconds.
Unused step allowances do not authorize a larger total.
Start no step without enough remaining allowance for its bound and final sealing.
Preserve stage-level timeouts as unresolved evidence.
Do not infer a scientific outcome from a killed process.

The original retained factor is available for this development audit.
It can check accepted codes against the archived exact target.
This audit access is not free access for a compressed production service.
Report that distinction explicitly.

If either box accepts, verify every code against the retained reference.
Then compare its complete stage cost with the exact factor solver.
Acceptance alone does not justify a complete-model speed claim.

If endpoints disagree, report an information-width obstruction for that box.
If endpoints agree and certification fails, report unresolved certificate tightness.
Only the latter result directly motivates the preconditioned bound.
Both failures can motivate a prospectively registered precision experiment.

## 7. Promotion conditions

A complete compressed service must preserve exact target codes.
Its canonical compressed state is a new state family.
It must not claim byte equality with the old exact-factor state.
Its indexed reconstruction comparator receives the same descriptors and certificate implementation.

Count retained descriptor bytes, model bytes, metadata, and every fallback input.
Count descriptor preparation separately in lifetime cost.
Count failed certification and repeated solves inside repair cost.
Count duplicate model export when the output contract requires it.

Current projected state savings are 11.19% at 16 bits and 9.23% at 24 bits.
The calibrated model already dominates this tiny complete state.
Saved I/O can therefore be small compared with certificate overhead.
Larger calibration sets change both storage benefit and solver rank.
Neither change alone proves a favorable tradeoff.

Promote only after useful acceptance survives matched cost accounting.
Then test later stages before complete-model repair timing.
One unresolved late stage can require nearly a complete ancestor traversal.
Keep precision failures and their exact witnesses in the published development record.

## 8. Scope

This design adapts standard interval and residual reasoning.
It does not establish publication novelty for those mathematical tools.
It supplies a concrete diagnostic path for the proposed compressed repair contribution.
Broader quality, additional deletion requests, and replication remain necessary.

## 9. Implemented verifier and software evidence

The new public entry point is `certify_preconditioned_dyadic_box`.
Its arguments match the existing dyadic box certificate.
It preserves grid construction, coordinate order, normalization, ridge, and tie rules.
Nonzero-width boxes never invoke a pointwise exact fallback.
Singleton boxes use the existing bounded point solver.

Every suffix retains the existing ridge error bound.
The midpoint inverse also proposes the new preconditioner.
Directed matrix products bound its defect and transformed residual.
Directed row sums must prove strict contraction.
Candidate iteration proposes a nonnegative componentwise radius.
The final directed inequality must verify that radius before any cell can use it.
Failed contraction or supersolution verification leaves only the ridge certificate.

Each row can use either independently valid cell certificate.
Two successful certificates must identify the same grid cell.
The implementation raises an error if that consistency check fails.
Unresolved rows abort the complete stage without returning a partial model.
Accepted arrays use immutable byte storage.

The current implementation does not promise acceptance whenever some sound certificate exists.
Its eager computation can exceed a resource budget.
A nonfinite ridge residual can also stop before a useful preconditioned bound is attempted.
These conditions fail closed and remain optimization limits.

The focused fixture suite contains sixteen tests.
It includes exact rational products, exact two-dimensional solves, and verified componentwise inequalities.
It checks every corner of a small factor box against the independent dense target.
It also checks interior points, singleton targets, empty rank, and candidate rejection.
A deterministic fixture demonstrates acceptance when the ridge-floor certificate is unresolved.
Another fixture proves endpoint disagreement and requires rejection.
Subnormal products, near-one contraction, exact ties, nonfinite inputs, and runtime guards receive separate checks.
These are software tests, not empirical datasets or model-speed evidence.

The initial real-factor screen remains separate evidence under its registered worker receipt.
It found 61 differing endpoint codes for the 16-bit box.
Its 24-bit endpoints matched the true factor's codes.
The old 24-bit box certificate remained unresolved at coordinate 22.
Those observations motivate a registered follow-up with this verifier.
They do not prove that the new verifier will accept the 24-bit box.

## 10. Gradient-selected negative witness proposals

`src/box_corner_witness.py` supplies deterministic corner proposals.
It does not certify codes or declare box ambiguity.
Its entry point is

```python
gradient_corners(weights_row, candidate_row, lower, upper, coordinate, *, beta)
```

Here `beta` is the exact positive ridge-normalization product.
Feature matrices retain their full width-by-token shape.
The result has `minus`, `plus`, `gradient`, `midpoint`, and `midpoint_decision` fields.
Returned arrays use immutable byte storage.

At coordinate $i$, hold the candidate prefix codes $q_h$ fixed.
Define

\[
s=\sum_{h<i}(w_h-q_h)x_h,
\qquad
G=\beta I+\sum_{h\ge i}x_hx_h^{\mathsf T},
\qquad
a=G^{-1}x_i,
\qquad
b=G^{-1}s.
\]

The conditional decision input is

\[
f=w_i+x_i^{\mathsf T}G^{-1}s.
\]

Using $dG^{-1}=-G^{-1}(dG)G^{-1}$ gives

\[
\nabla_{x_h}f=
\begin{cases}
(w_h-q_h)a, & h<i,\\
b-(x_i^{\mathsf T}b)a-(x_i^{\mathsf T}a)b, & h=i,\\
-(x_h^{\mathsf T}b)a-(x_h^{\mathsf T}a)b, & h>i.
\end{cases}
\]

The implementation evaluates this expression with an ordinary floating solve.
It uses a finite midpoint proposal clamped inside the box.
The clamp handles subnormal averages that lose a half-step.
These calculations carry no certificate authority.

The plus corner selects the upper endpoint wherever the gradient is nonnegative.
It selects the lower endpoint elsewhere.
The minus corner uses the opposite endpoint at every position.
Zero gradients select upper for plus and lower for minus.
Both corners retain the selected endpoints' exact binary64 bits.
The implementation rejects nonfinite inputs, invalid boxes, and failed numerical solves.

Evaluate both proposals with the exact point solver and every original weight column.
Check their box membership independently before either solve.
Use the unchanged grids, ridge, normalization, coordinate order, and tie rule.
Distinct exact output codes then prove nonconstant output inside this box.
Changed prefix codes at a corner do not invalidate that witness.
They only weaken the gradient's usefulness as a search direction.

Equal corner outputs remain inconclusive.
The proposed gradient does not globally maximize the decision input.
A different interior point or corner can still produce another output.
Treat every numerical gradient failure as unresolved, never as a positive or negative certificate.

Seven focused software tests check this proposal module.
Exact dual-number differentiation checks all gradient regions independently.
Exact rational central differences provide another check.
Other tests cover endpoint bits, zero-gradient rules, subnormals, shape preservation, and failed solves.
These tests use mathematical fixtures and contain no empirical dataset evidence.
