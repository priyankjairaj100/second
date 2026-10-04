# Publication theory package

Date: 4 October 2026.
Status: consolidated mathematical contract for the next research phase.

This document orders existing results for publication.
It adds no measured performance claim.
The derivations appear in the report and independent theory notes.
The implementation provides supporting correctness checks, not a formal proof.

## 1. Target, notation, and shared assumptions

Let `C` contain the original calibration records.
Let `F` contain the requested deletion records.
Write `R = C \ F` for the retained records.

The fixed base model has weights `W`.
Its quantization graph has stages `ell = 1, ..., L`.
Stage `ell` quantizes a matrix with `p_ell` rows and `d_ell` columns.

The primary feature evaluator is `V_cert`.
Its successful outputs are binary64 values interpreted as exact dyadic rationals.
The target covariance is

\[
H_\ell(R)=\lambda_\ell I+M_{0,\ell}^{-1}
\sum_{j\in R}X_{\ell j}(Q_{<\ell}(R))X_{\ell j}(Q_{<\ell}(R))^\top.
\]

The target model is `Q_seq(W, R)` under these covariances.
Exact rational reverse LDL determines each sequential quantization decision.
Nearest-grid rounding resolves midpoint ties toward the lower code.

| Assumption | Required contract |
| --- | --- |
| A1: Fixed model target | Bind weights, grids, order, ties, ridge, normalization, conversion, and all fixed parameters. |
| A2: Fixed feature target | Bind source, runtime, operation schedule, tokenization, record boundaries, masks, and positions. |
| A3: Record independence | Evaluate each record independently under the installed ancestor prefix. |
| A4: Positive covariance | Use fixed positive rational ridge and normalization at each stage. |
| A5: Intrinsic evidence | Select chart directions and domains independently of deletable calibration records. |
| A6: Sound bounds | Cover ideal derivatives, all mixed derivatives, finite errors, domains, and parameter conversion. |
| A7: Exact state arithmetic | Construct, add, subtract, and serialize all retained moments canonically. |
| A8: Accessible inputs | Supply verified deleted payloads and a verified retained source for requested replay. |
| A9: Trusted state origin | Use service-generated state or state authenticated through the declared storage interface. |
| A10: Completion domain | Require successful finite evaluation for every necessary target call. |

`V_cert` is a partial finite program.
Provider abstention permits exact retained replay.
An unresolved nonlinear rounding operation can instead prevent target evaluation.
An invalid finite operation also prevents target evaluation.
These failures abort the request without committing an approximate model.

The exactness theorem describes successful target executions.
The completion theorem additionally requires successful replay and finite service resources.
Neither theorem proves total execution for arbitrary weights and inputs.
The legacy evaluator `V` and historical floating target `E` remain different programs.

## 2. Ordered theorem package

Use T1 through T7 as the main mathematical sequence.
Place the matrix geometry proof and lower bounds in the supplement.

### T1. Finite response enclosure

Fix a stage and omit its index.
Represent installed ancestor parameters as

\[
\theta=\theta_0+Da+u,\qquad Da=\sum_{t=1}^{r}a_tD_t.
\]

The current automatic provider requires `u = 0`.
The general theorem permits a certified residual term.
Let `f_j` denote the ideal smooth feature map.
Let `X_j` denote the actual finite output.
Choose fixed rational feature jets `Z_j0, ..., Z_jr`.
Define

\[
Z_j(a)=Z_{j0}+\sum_{t=1}^{r}a_tZ_{jt}.
\]

Assume these uniform bounds on the declared region:

\[
\begin{aligned}
\|X_j-f_j(\theta)\|_F&\le\nu_j,\\
\|f_j(\theta_0)-Z_{j0}\|_F&\le e_{j0},\\
\|Df_j(\theta_0)[D_t]-Z_{jt}\|_F&\le e_{jt},\\
\|D^2[f_j(\theta_0+D\cdot)](z)[v,w]\|_F
&\le H_j\|v\|_2\|w\|_2,\\
\|Df_j(\theta_0+Da+su)[u]\|_F&\le L_j\|u\|_\Theta.
\end{aligned}
\]

The last condition holds throughout `0 <= s <= 1`.
The chart segment from zero to `a` must remain inside the proved region.
Then

\[
\|X_j-Z_j(a)\|_F\le
\nu_j+e_{j0}+\sum_t|a_t|e_{jt}
+\tfrac12H_j\|a\|_2^2+L_j\|u\|_\Theta.
\tag{T1}
\]

Proof: apply the integral Taylor formula and triangle inequality.
Integrate the residual segment separately.
Include every mixed Hessian entry.
Differentiate the ideal map, not quantization decisions or the discontinuous finite program.

The implementation bounds elementary rounding by

\[
|\operatorname{fl}(z)-z|\le2^{-53}|z|+2^{-1075}.
\]

It first excludes overflow and invalid domains.
It transports existing operand errors through each operation.
It proves nonlinear rounding through rational intervals.
Softmax uses a separate proof for the actual finite maximum-shift schedule.

### T2. Deletable evidence and Gram enclosure

Define the nonnegative descriptor and query vectors

\[
b_j=(\nu_j+e_{j0},e_{j1},\ldots,e_{jr},H_j,L_j),
\quad
v(a,u)=(1,|a_1|,\ldots,|a_r|,\|a\|_2^2/2,\|u\|_\Theta).
\]

For each fixed group `g`, store

\[
C_g=M_0^{-1}\sum_{j\in R_g}b_jb_j^\top,
\qquad \epsilon_g^2=v^\top C_gv.
\]

Then `epsilon_g²` bounds the normalized sum of squared feature errors.
The descriptor matrix retains all cross terms.
Dropping these terms does not preserve the bound.

Full quadratic response moments recover

\[
S_g(a)=M_0^{-1}\sum_{j\in R_g}Z_j(a)Z_j(a)^\top
\]

without retained record reads.
They use `binomial(r + 2, 2)` matrix coefficients.
Each coefficient is an additive intrinsic record function.
Exact deletion therefore reproduces retained moments in every deletion order.

Let `z_g² = tr(S_g)`.
The actual normalized group Gram differs by at most

\[
\delta_g=2z_g\epsilon_g+\epsilon_g^2.
\tag{T2}
\]

Proof: expand `XXᵀ - ZZᵀ` and use Frobenius norm bounds.
The implementation uses an outward rational square-root bound.

### T3. Compact shifted proposal

Full quadratic matrices are unnecessary for a valid enclosure.
Set `Delta Z_j = sum_t a_t Z_jt`.
Define

\[
\begin{aligned}
S_{g,\mathrm{lin}}&=M_0^{-1}\sum_{j\in R_g}
\left[Z_{j0}Z_{j0}^\top+Z_{j0}\Delta Z_j^\top+
\Delta Z_jZ_{j0}^\top\right],\\
P_g&=M_0^{-1}\sum_{j\in R_g}\Delta Z_j\Delta Z_j^\top,\\
G_{g,st}&=M_0^{-1}\sum_{j\in R_g}\langle Z_{js},Z_{jt}\rangle_F,\\
\beta_g&=a^\top G_ga=\operatorname{tr}(P_g).
\end{aligned}
\]

Thus `0 <= P_g <= beta_g I` in Loewner order.
Use the shifted proposal `S_tilde_g = S_g,lin + beta_g I`.
It is positive semidefinite because

\[
\widetilde S_g=S_g+(\beta_gI-P_g)\succeq0.
\]

Its feature norm remains available from `z_g² = tr(S_g,lin) + beta_g`.
T2 therefore gives

\[
-(\beta_g+\delta_g)I
\preceq H_g^*-\widetilde S_g
\preceq\delta_gI.
\tag{T3}
\]

Here `H_g*` excludes the stage ridge.
Add the ridge once after summing groups.
Define the unresolved budgets

\[
A=\sum_{g\in U}(\beta_g+\delta_g),\qquad
D=\sum_{g\in U}\delta_g.
\]

Exact replay replaces a group proposal with its actual Gram.
It removes that group's two budgets.
The global proposal keeps its ridge floor throughout replay.
When `A < lambda`, valid relative scales are

\[
\alpha=1-A/\lambda,\qquad \omega=1+D/\lambda.
\]

These conservative endpoints tighten during replay at a fixed prefix.
Candidate codes and their margins need not change monotonically.
Changing the chart also need not tighten the bound.

### T4. Exact discrete decisions

Suppose `alpha H_tilde <= H* <= omega H_tilde`, with `0 < alpha <= omega`.
Use reverse LDL factors of `H_tilde`.
For a forced preceding code prefix, let `v_i` denote the current conditional input.
Let `g_i` denote the reciprocal pivot.
Let `E_i` denote the preceding quantization error energy.
Then

\[
|v_i^*-v_i|^2\le
\frac{(\omega-\alpha)^2}{4\alpha\omega}g_iE_i.
\tag{T4}
\]

The report proves this bound through classical matrix geometry.
The coefficient is not a new universal matrix inequality.

Containment inside the declared rounding cell proves the next code.
Coordinate induction proves the complete candidate matrix.
The implementation compares squared rational quantities.
Positive-radius contact with a finite cell boundary causes abstention.
Zero displacement preserves the declared midpoint rule exactly.

The local verifier assumes the supplied spectral premise.
It does not prove an arbitrary caller's spectral assertion.
T1 through T3 establish that premise for the supported automatic provider.
Typed bindings prevent accidental reuse with another prefix or group.
They do not provide proof-assistant verification of arbitrary callbacks.

### T5. Complete sequential repair

Process stages in dependency order.
Bind every proposal to the already certified new ancestor prefix.
Apply T1 through T4 under that prefix.
If a certificate fails, replay another unresolved retained group.
After all groups replay, use the exact retained covariance.

Under A1 through A10, this procedure returns `Q_seq(W, R)`.
It permits changes at the first stage and every later stage.
It does not assume that the old ancestor prefix remains correct.

Proof: coordinate induction proves each stage.
Topological induction proves the complete model.
There are finitely many stages and groups.
Replay completion still requires every necessary finite evaluation to succeed.
Finite resources must also suffice for exact arithmetic and output.

### T6. Canonical repeated state

Define the complete logical state as

\[
\mathcal A(R)=\left(Q_{\mathrm{seq}}(W,R),
\mathrm{Bindings}(R),
\{\mathrm{LinearMoments}_g(R),\mathrm{ErrorMoments}_g(R)\}_g\right).
\tag{T6}
\]

Fixed identifier grouping and canonical serialization determine its bytes.
Each record binding contains its identifier, payload digest, group, and contribution digests.
It contains no retained feature matrix or derivative array.

Verified deletion recomputes intrinsic deleted contributions before subtraction.
Unavailable descriptors use deterministic markers and counts.
These counts also subtract exactly.
T5 determines the model from retained data.
Additivity determines the retained evidence.
The committed state therefore equals fresh construction on `R`.

This result holds after repeated, combined, reordered, or adaptive deletion requests.
Each request must satisfy the same assumptions.
Audit logs remain outside the canonical state.
The theorem concerns logical state, not physical Python memory erasure.
It removes calibration influence under the chosen interface.
It does not remove information already present in fixed base weights.

### T7. Conditional complete-work gain

Let a specified fresh comparator cost `C_B = F + G + J`.
Here `F` is its avoidable retained computation.
Here `G` is comparable local quantization work.
Here `J` is comparable commit and output work.
Suppose repair satisfies

\[
C_R\le sF+U+G+J,
\qquad U/F\le u,
\qquad (G+J)/F\le\gamma.
\]

Charge every excess cost to `U`.
This includes repeated factorization and any mismatch in supposedly shared work.
If `F > 0` and `s + u < 1`, then

\[
\frac{C_B}{C_R}\ge\frac{1+\gamma}{s+u+\gamma}>1.
\tag{T7}
\]

This is an arithmetic implication of complete costs.
It is not a latency measurement or a distributional guarantee.
Zero retained reads alone does not establish its premises.

## 3. Two local acceptance results with different scopes

The full quadratic proposal gives a stronger theoretical normalization.
Let `H_bar = lambda I + S` and `e = epsilon / sqrt(lambda)`.
Whitening yields

\[
\eta\le2a_0e+e^2,\qquad a_0\le1.
\]

It permits scales `(1 - eta, 1 + eta)` when `eta < 1`.
In the ideal regime, set `K_R² = M_0^-1 sum_j H_j²`.
Assume exact jets, zero finite error, and zero chart residual.
Then `epsilon <= K_R ||a||² / 2`.
If every positive-energy normalized margin exceeds `tau > 0`, sufficient acceptance is

\[
\|a\|_2^2<\frac{2\sqrt\lambda}{K_R}
\left(\sqrt{1+\tau/\sqrt{1+\tau^2}}-1\right).
\]

This expression assumes `K_R > 0`.
If `K_R = 0`, affine response has no truncation error on the proved region.
The small-margin sufficient radius scales as `sqrt(tau)` under controlled constants.
It does not prove universal dominance over another candidate.

The compact service instead applies T3's signed absolute budgets.
For each stage, an implementation-matched sufficient condition is

\[
\beta+\delta\le\lambda/2,
\qquad \beta+2\delta<\lambda\tau.
\]

Here `beta` and `delta` sum the unresolved group contributions.
These conditions imply acceptance without retained replay.
They must hold under each newly certified stage prefix.
The implementation does not automatically obtain the stronger quadratic radius.

### Error floors

At the chart center, the descriptor floor includes `nu_j + e_j0`.
Directional jet errors add terms proportional to `|a_t|`.
A residual bound adds `L_j ||u||`.
These terms can prevent second-order scaling.

Outward contraction also adds numerical conservatism.
At square-root precision `b`, its additional Gram slack is less than `2^(1-b)` in the contraction's units.
The service then applies the stage normalization.
This slack is zero when the relevant square root is represented exactly.

Increasing precision can reduce enclosure error.
It does not remove actual finite-versus-ideal discrepancy.
Small deletion size does not prove small displacement from the fixed chart.
The original quantized prefix can already lie outside that chart.

## 4. Executable theorem map

| Result | Implementation | Checked quantity | Failure action |
| --- | --- | --- | --- |
| A2, A10 | `CertifiedDecoder`, runtime guard, `certified_intervals.round_*` | Finite execution, primitive enclosure, environment | Abort failed target execution. |
| A5 | `AffineChart`, provider manifest | Fixed directions, radii, declared provenance | Reject malformed configuration. Historical independence remains a premise. |
| T1 domain | `AutomaticResponseProvider.coefficients` | Exact installed ancestor displacement and coefficient box | Return `UnknownBound` and replay. |
| T1 bound | `feature_jets`, `intrinsic_moments`, `Jet` | Mixed Hessians, jet widths, finite error | Mark descriptor unavailable and replay. |
| T2 moments | `linear_record_moments`, `record_moments` | Intrinsic rational contributions | Reject malformed dimensions or identities. |
| T2 contraction | `response_error_squared`, `dyadic_sqrt_upper` | Complete descriptor quadratic and outward norm | Reject malformed evidence. |
| T3 | `shifted_linear_response_bound`, aggregate `_proposal` | `beta`, `delta`, positive semidefinite proposal | Reject invalid witness or request replay. |
| T4 | `certify_relative_enclosure` | Squared radius, cell endpoints, prefix energy | Abstain if any cell remains unresolved. |
| T5 | `AggregateRepairService.repair` | Certified prefix, unresolved budgets, replay groups | Replay; abort if target execution fails. |
| T6 | Aggregate `_extract`, `_delete`, `_finish`, `canonical_bytes` | Deleted contribution digests and exact retained sums | Reject mismatched deletion or state. |
| T7 | Complete runner ledger and external timing | Every charged component and comparator conditions | Withhold the speed claim if conditions fail. |

The source computes more quantities than the audit currently exports.
In particular, stage audits do not record every margin or numerical rejection subtype.
The experiment runner must preserve these diagnostics without changing the canonical state.

## 5. Complete work and storage model

Let `P` count chart-addressable model parameters.
Let `P_ell` count ancestor parameters inspected at stage `ell`.
Let `N` count retained records and `G_ell` count stored groups.
Let `t_j` count record tokens.
Let `K_ell` count factorization attempts during repair.
Let `b` bound the relevant integer bit lengths during a measured operation.

The compact persistent rational-entry count is

\[
O\!\left(rP+\sum_\ell G_\ell
\left[(r+1)d_\ell^2+r^2\right]\right).
\]

Scalar descriptor moments add `O(sum_ell G_ell r²)` entries.
Dense direction matrices account for the `rP` term.
Base weights and the complete output model require additional storage.
Record and contribution bindings require `O(NL)` metadata.
Retained payload storage is separate and available to both methods.

The full quadratic tier instead stores `O(sum_ell G_ell r² d_ell²)` response entries.
Exact polynomial query lower bounds concern this exact-output interface.
They do not prohibit a smaller interval-query interface.

| Component | Work or storage that must be charged |
| --- | --- |
| Initial preparation | Checkpoint loading, conversion, chart construction, every intrinsic extraction, aggregation, hashing, and serialization. |
| Response extraction | Center and region evaluation with all first and mixed second derivatives. |
| Parameter jets | Current construction allocates jets for every stage, including stages after the requested feature location. |
| Temporary jet memory | Each live scalar can carry `O(r²)` interval entries. Parameter jets also contribute this cost. |
| Compact moment extraction | Per record and stage, `O(t_j[(r+1)d_ell² + r²d_ell])` rational operations. |
| Deletion | Read deleted payloads, verify digests, regenerate intrinsic evidence, and subtract exact contributions. |
| Chart fitting | Inspect ancestor coordinates and solve an exact rational linear system. |
| Current dense fitting | At most `O(P_ell r²)` elimination operations, plus input construction and conversion. |
| Repeated fitting | The current provider can repeat fitting for each group at the same stage. |
| Aggregate contraction | Per group, `O(rd_ell² + r²)` rational operations and serialized evidence reads. |
| Proposal validation | Exact positive semidefinite checks can require cubic matrix work. |
| Local decisions | Each attempt costs `O(d_ell³ + p_ell d_ell² + p_ell d_ell m_ell)`. |
| Replay | Charge retained source reads, actual prefix evaluation, Gram accumulation, replacement, and further attempts. |
| Metadata | Charge validation, membership reconstruction, hashes, scans, and canonical serialization. |
| Output | Charge complete model materialization, state writes, atomic commit, and required diagnostics. |

Here `m_ell` is the largest coordinate grid size.
The number of factorization attempts can grow with replayed groups.
The current evaluator can repeat ancestor computation across requested stages.
Source payload caching does not eliminate this computation.

Rational-operation counts are not fixed-word runtime bounds.
Multiplication, division, comparison, and normalization depend on operand bit lengths.
Hashing and serialization depend on encoded byte counts.
Intervals also incur primitive refinement and integer-square-root work.
Peak memory includes temporary objects, caches, and simultaneous old and new states.

For a request, use the disjoint accounting identity

\[
\begin{aligned}
C_R={}&C_{\rm input}+C_{\rm validate}+C_{\rm delete}
+C_{\rm fit}+C_{\rm contract}+C_{\rm proof}\\
&+C_{\rm factor}+C_{\rm replay}+C_{\rm state}
+C_{\rm output}+C_{\rm control}.
\end{aligned}
\]

Measure inclusive elapsed time separately from this component decomposition.
Do not add overlapping timers.
Report setup separately and include it in lifetime comparisons.
Lifetime savings require

\[
\sum_q(C_{B,q}-C_{R,q})>P_R-P_B.
\]

Here `P_R` and `P_B` contain the respective preparation costs.
Charge equivalent state access and output obligations to each method.

## 6. Fair comparator consequence

An equally indexed fresh solver can use the same retained response aggregates.
It can also use the same chart, certificates, replay planner, and numerical target.
Starting without old quantized codes does not prevent this route.
The current candidate solver does not require those old codes.

Therefore the index alone gives no inherent deletion-exclusive solver advantage.
Identical retained inputs and planner choices can produce identical solver work.
Their difference can remain in index maintenance, preparation, or the declared service interface.
Measure these differences instead of assigning fictitious retained scans to the comparator.

Use direct fresh quantization as the correctness oracle.
Use equally indexed fresh solving as a separate performance baseline.
If both solve at equal cost, report efficient indexed quantization and exact deletion maintenance separately.
Do not report an algorithmic repair speedup over that baseline without measured extra savings.

## 7. Reliability estimands

Freeze a distribution over calibration roots and deletion request sequences.
Specify dataset, checkpoint, calibration sampling, deletion sampling, and execution conditions.
Adaptive requests need a fixed policy with explicit observable inputs.
Keep difficult requests and all attempted requests in the declared workload.

For method `m` and request `q`, define

\[
S_{m,q}=\mathbf1\{\text{a verified complete artifact returns within the resource budget}\}.
\]

Set `T_m,q` to the complete elapsed time when `S_m,q = 1`.
Set `T_m,q = infinity` otherwise.
Also record actual consumed time for failed requests.
Distinguish evaluator abort, resource failure, timeout, and incorrect output.
Certificate rejection followed by successful replay is a successful request.

Report all of these quantities:

| Estimand | Definition and interpretation |
| --- | --- |
| Completion | `Pr(S_R = 1)` over every attempted repair request. |
| Target completion | `Pr(S_B = 1)` for the direct fresh oracle. |
| Joint exact speed event | `Pr(S_B = S_R = 1 and T_R <= T_B / s)` for a fixed `s > 1`. |
| Deadline service | `Pr(S_R = 1 and T_R <= t)` for a fixed deadline `t`. |
| Latency quantiles | Quantiles of extended `T_R`, including infinite values from failed requests. |
| Conditional paired ratio | `T_B / T_R` among jointly successful pairs, explicitly labeled conditional. |
| Total consumed work | Actual resources used by every attempted request, including failed requests. |
| Replay coverage | Retained source reads and replayed stages, with fixed denominators and failure categories. |

The joint speed event avoids labeling a failed baseline as infinite speedup.
The conditional ratio alone cannot support a reliability claim.
Timing repetitions do not create independent calibration roots.
Repeated requests from one root require clustered analysis.
Fix confidence levels and interval procedures before confirmatory evaluation.

T7 can imply a probabilistic speed guarantee only with a justified probability for its premises.
No such probability is currently proved or measured.
Software fixture acceptance does not estimate the request distribution.

## 8. Supplementary limits and optional results

The feature-query obstruction rules out universal record-free repair in its stated black-box model.
It does not rule out every explicit transformer algorithm.
The coefficient-information bound concerns exact polynomial Gram queries without other side information.
It does not concern every interval query or model-output interface.

The weighted scheduler bounds cooperative charged work under bounded packets and explicit cancellation costs.
It requires an exact branch that terminates on the request.
It does not establish GPU preemption or a latency bound.
The complete transformer service does not yet use this scheduler.

Sparse code injection assumes a valid target factor and certified input envelopes.
Its acquisition and validation costs remain additional.
The fixed-teacher alternative changes the quantization target.
It cannot replace sequential repair inside the primary exactness claim.

## 9. Publication boundary

The mathematical contribution combines deletable evidence with exact sequential decisions and canonical repeated state.
Its matrix geometry, polynomial statistics, and Taylor verification ingredients have existing precedents.
The paper must state its narrower contribution against those precedents.

Current software evidence establishes reference behavior on correctness fixtures.
It does not establish useful chart coverage on pretrained models.
It does not establish competitive preparation, storage, quality, or complete latency.
These remain explicit empirical gates.


## Revision 6 extension

The fixed-box route is documented in BOX_THEORY.md and report Sections 28–30.
It removes the affine-span condition for frozen-grid ancestor parameters.
Rank-zero intervals still require finite error bounds and valid decision certificates.
Hybrid midpoint anchors minimize the rectangular interval feature envelope.
They avoid a separate finite base evaluation for varying domains.
No acceptance dominance or practical speed follows.

The provider stores d²+6 rational slots per occupied stage group.
Its full-grid domain stores 2P_A rational endpoints.
Metadata, exact arithmetic size, base weights, replay, and output remain costs.
Lazy parameter wrappers reduce temporary construction without changing scalar operations.

The v6 runner supports four mechanism modes and exclusive component telemetry.
The worker isolates complete comparisons and enforces declared process limits.
Workload scores use original-state evidence only.
Inventories bind source hashes, configurations, roots, requests, repetitions, and method order.
The analyzer rejects mixed mode/chart/service identities within a stratum.

These changes preserve the fair indexed solver and canonical state target.
They do not close real-model feasibility, full-service timing, or useful NLP evidence.
See VALIDATION.md for the 261-test result and source hashes.
See RESEARCH_TODO.md for remaining required tasks.
