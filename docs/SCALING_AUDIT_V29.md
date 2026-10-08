# Scaling audit for the revision 28 implementation

This audit uses source inspection and integer arithmetic only.
No model, calibration, or empirical worker ran.
No numerical source or archived campaign changed.

**Recommendation:** do not expand the present automatic fallback policy directly to large retained-token counts.
First bound expensive coefficient work explicitly.
Then add a verified primal backend for stages where token count substantially exceeds feature width.

Revision 28 already shares ridge coefficients across output rows.
Another generic cross-row cache will not remove its principal scaling terms.
The hidden risk is eager preconditioning across every coordinate after even one difficult row.

## Dimensions and target

For one calibrated linear stage, use these symbols.

| Symbol | Meaning |
|---|---|
| \(m\) | Number of output rows in the weight matrix |
| \(d\) | Input feature width, also the number of quantization coordinates |
| \(T\) | Total retained tokens pooled across all retained records |
| \(N\) | Number of retained records |
| \(g\) | Number of row-grid codes, usually sixteen |
| \(r_1,r_2,r_3\) | Rows unresolved after ball, ridge intervals, and preconditioned intervals |

Weights have shape \(m\times d\).
The complete feature box has shape \(d\times T\).
The variable called `rank` in numerical code is \(T\).
It is not the numerical rank of the feature matrix.

The service concatenates each record's token-major factors and transposes the result.
Thus \(T=\sum_{s=1}^N T_s\).
For example, 128 records with 128 tokens each imply \(T=16{,}384\), not 128.
All tables below treat 128, 512, and 2048 as **total retained tokens**.

Let \(X\in\mathbb R^{d\times T}\) denote exact binary64 features.
Set \(\beta=\lambda\nu\), where \(\nu\) is the target's declared normalization.
The exact target uses

\[
H=\lambda I_d+XX^T/\nu.
\]

The code must preserve \(\nu\) during deletion.
It cannot silently replace normalization with the current retained token count.
Larger calibration configurations require prospectively specified targets.

## Source-level work

Complexities count arithmetic work and array elements, not elapsed seconds.
Binary64 operations have different constants from Python loops and exact rational checks.
Early rejection can reduce a particular call's work.
The following bounds describe complete paths unless stated otherwise.

| Operation | Source mechanism | Arithmetic work | Main additional storage |
|---|---|---:|---:|
| Decode and assemble a stage | `FixedCompressedService.run`, descriptor boxes, two concatenations and transpose copies | \(\Theta(dT)\) decoded entries plus metadata | \(\Theta(dT)\), with multiple copies |
| Row grids and discrepancy bounds | `dyadic_row_scales`, `_feature_uncertainty_bounds` | \(O(md+mg+dT)\) | \(O(md+dT+mg)\) temporary arrays |
| Ridge coefficient construction | `token_box_certificate._box_coefficients` | \(\Theta(dT^2)\) for \(T>0\) | \(\Theta(T^2+dT)\) |
| Uniform feature-prefix uncertainty | `_feature_uncertainty_bounds` | \(\Theta(dT)\) after weight discrepancies | \(\Theta(dT+T)\) |
| Ball underflow bounds | `_underflow_bounds` | \(\Theta(dT)\) | \(O(T+d)\) beyond inputs |
| First native ball pass | `nb_run`: rows, coordinates, two token loops | \(O(mdT+md\log g)\) | \(O(T)\) native scratch and \(O(md)\) output |
| Shared ridge interval retries | `_interval_rows` calls `nbc_run` on selected complete rows | \(O(r_1dT+r_1d\log g)\) | \(O(T)\) native scratch; shared \(O(dT)\) coefficients |
| Eager stronger coefficient construction | `_coefficient_bounds` and `_preconditioned_error` | \(\Theta(dT^3+dT^2)\) when finite preconditioners reach the contraction test | \(\Theta(T^2+dT)\), with larger constants |
| Stronger interval retries | `_interval_rows` with verified component radii | \(O(r_2dT+r_2d\log g)\) | As above |
| Final Python universal fallback | `certify_preconditioned_dyadic_box` on remaining rows | Another \(O(dT^3+dT^2+r_3dT)\) | \(O(T^2+dT+r_3T+r_3d)\) |
| Pack calibrated output | `StageCodes.from_array` | \(\Theta(md)\) code entries | \(\Theta(md)\) transient and packed output |

The common exact point backend also constructs token coefficients in \(\Theta(dT^2)\).
Its native row pass costs \(O(mdT)\).
These costs remain in the optimized reconstruction baseline.

### Why ridge construction is quadratic in tokens

`_box_coefficients` loops backward over all \(d\) input coordinates.
For every coordinate it does the following work.

1. Forms two \(T\times T\) bounds for an outer product.
2. Adds those bounds into a suffix Gram enclosure.
3. Multiplies the nominal inverse by a \(T\)-vector.
4. Performs a nominal rank-one inverse update.
5. Evaluates the residual using \(T\) vector operations of length \(T\).

The reverse recurrence shares suffix work across coordinates.
It does not invert a new dense matrix independently at every coordinate.
Nevertheless, each coordinate still requires \(\Theta(T^2)\) work.

The nominal Sherman–Morrison update is not accepted as numerical evidence.
The directed residual bound supplies that evidence.

### Why preconditioning is cubic in tokens

`_preconditioned_error` verifies the defect of a dense approximate inverse.
Its call `_left_product(inverse, gram_lo, gram_hi)` evaluates \(R_iG_i\).
The helper loops over \(T\) columns.
Each loop updates two \(T\times T\) arrays.
This is \(\Theta(T^3)\) elementwise work for one coordinate.

The residual transformations and fixed-count supersolution iterations add \(O(T^2)\) work.
They do not remove the dense defect verification.
`_coefficient_bounds` repeats this operation at every coordinate.

Revision 28 invokes this eager construction when \(r_2>0\).
One remaining row therefore triggers the same coefficient construction as many remaining rows.
The subsequent row verifier is sparse; the stronger coefficient construction is not sparse.

If \(r_3>0\), Python fallback constructs the complete stronger certificate again.
Its smaller row subset reduces row arithmetic only.
It does not reduce the common coefficient dimension or the number of suffixes.

### Complete stage bound before neural fallback

Ignoring fixed grid sizes, the principal upper bound is

\[
O\!\left(
dT^2+mdT+(r_1+r_2+r_3)dT
+\mathbf1_{r_2>0}dT^3
+\mathbf1_{r_3>0}dT^3
\right).
\]

This expression exposes repeated coefficient construction.
It does not treat independently reported timing subdivisions as additive twice.
The row counts satisfy \(0\le r_3\le r_2\le r_1\le m\).

## Structural scale examples

Consider a stage with \(d=768\) and \(m=2304\).
The entries below are exact integer products.
They are **not FLOP counts, wall-time predictions, or measurements**.

| Total retained tokens \(T\) | \(dT^2\) ridge units | \(dT^3\) eager defect units | \(mdT\) one row-token sweep |
|---:|---:|---:|---:|
| 16 | 196,608 | 3,145,728 | 28,311,552 |
| 128 | 12,582,912 | 1,610,612,736 | 226,492,416 |
| 512 | 201,326,592 | 103,079,215,104 | 905,969,664 |
| 2048 | 3,221,225,472 | 6,597,069,766,656 | 3,623,878,656 |

The native ball kernel contains two token loops per successfully completed coordinate.
Therefore its full successful traversal performs two such row-token sweeps.
Each sweep contains several arithmetic operations.
The table deliberately does not convert those operations into seconds.

At fixed \(d,m\), increasing tokens from 16 to 128 multiplies these terms by 64, 512, and 8.
Increasing tokens from 16 to 512 multiplies them by 1024, 32,768, and 32.
Increasing tokens from 16 to 2048 multiplies them by 16,384, 2,097,152, and 128.
These factors apply to separate structural terms, not complete observed runtime.

## Memory boundaries

These sizes use binary64 storage and MiB, where one MiB is \(2^{20}\) bytes.
The feature example again uses \(d=768\).

| \(T\) | One \(T\times T\) array | Two Gram bounds plus nominal inverse | One \(d\times T\) array |
|---:|---:|---:|---:|
| 16 | 0.001953125 MiB | 0.005859375 MiB | 0.09375 MiB |
| 128 | 0.125 MiB | 0.375 MiB | 0.75 MiB |
| 512 | 2 MiB | 6 MiB | 3 MiB |
| 2048 | 32 MiB | 96 MiB | 12 MiB |

The middle column is not peak memory.
`_multiply` materializes four product arrays before selecting endpoint extrema.
Outer products, inverse updates, and residual checks create more temporaries.
Preconditioner verification additionally holds defect and transformed-product arrays.

The service retains decoded per-record lower and upper boxes while assembling combined matrices.
It then holds combined lower and upper arrays, centers, radii, and coefficient proposals.
Sparse interval retry adds a \(d\times T\) component-radius array.

Additional memory includes weights, dense output codes, packed outputs, descriptors, and the original state.
The original state can still contain sources being deleted.
`prepare_context` constructs nearest-grid ancestor matrices for every calibrated stage, not just the current stage.
Its storage scales with \(\sum_s m_sd_s\).
Descriptor storage scales with \(\sum_s d_sT\), plus source metadata and codec framing.

Source-local compression reduces constants in stored feature evidence.
The current parser and verifier decode that evidence into binary64 bounds.
Compressed file size therefore does not bound verification workspace.

Decoding directly into final aligned arrays could remove several temporary copies.
This is a useful implementation improvement.
It does not remove the quadratic token workspace or cubic preconditioner work.

## Fallback limits are not scaling guards

The \(2^{20}\) width/rank restriction protects arithmetic assumptions.
It is not a practical memory or work limit.

The service's `max_exact_rank=64` limits rational point fallback only.
It does not cap token-space ridge construction, preconditioning, or floating direct refinement.
The reference point fallback may attempt up to 64 refined coordinates.
Each `_refined_coefficient` rebuilds a suffix Gram and solves a dense \(T\times T\) system.
Its work is \(O((d-i)T^2+T^3)\) for coordinate \(i\).

If a box remains unresolved, the service replays retained sources through the required ancestor closure.
It subsequently solves the entire stage with exact features.
Already certified output rows do not survive this service-level fallback interface.

Neural replay depends on individual record lengths, not only pooled \(T\).
Transformer attention includes work depending on \(\sum_s T_s^2\).
The same pooled token count can therefore have different replay costs.
Record count and stage-record traversals alone are not sufficient runtime predictors.

The neural traversal cap does not limit work already spent in coefficient certification.
A large failed coefficient attempt can exhaust resources before that cap matters.

## Immediate implementation: budgeted, requested-coordinate preconditioning

The first improvement should bound the existing conditional cost.
It requires no new target, codec, or model training.

1. Preserve V28's initial ball pass and shared ridge interval retries.
2. Collect the union of unresolved coordinates reported by those retries.
3. Build stronger component certificates only at those coordinates.
4. Reuse original ridge component radii at every other coordinate.
5. Retry affected full-width rows with the mixed, verified coefficient table.
6. Repeat only within declared coordinate, work, and memory budgets.

Let \(K\) be the number of stronger coefficient checks actually requested.
One reverse suffix sweep can reconstruct candidate inverses and Gram bounds in \(O(dT^2)\).
It performs dense defect verification only at requested coordinates.
The stronger construction then costs \(O(dT^2+KT^3)\), rather than \(O(dT^3)\).

Cache proved proposals and component bounds using \(O(KT)\) storage.
Avoid caching \(K\) dense inverse matrices, which would require \(O(KT^2)\) storage.
Additional adaptive rounds may repeat suffix sweeps.
Their complete work must be charged.

A requested-coordinate certificate must remain paired with its own proposal.
A different preconditioning matrix may validate an existing proposal through its residual.
It cannot validate unrelated cached radii by identity alone.

This change limits expensive verification when failures are sparse.
It does not solve the normal path's \(dT^2\) growth.
At large \(T\), even a single \(T^3\) check may be unacceptable.
An explicit work budget must allow clean refusal before allocating or computing that check.

Reusing previously proved stronger evidence also avoids rebuilding it inside final Python fallback.
The fallback interface should accept checked coefficient evidence with full provenance.
Any bounded refusal must remain a refusal, not a midpoint acceptance.

## Large-token implementation: verified primal/dual selection

The current solver always operates in token space.
When \(T\) greatly exceeds \(d\), that is the wrong dense dimension.
Add a second verified implementation over the input-feature Gram matrix.

Let

\[
K=XX^T,\qquad S_i=\{i,\ldots,d-1\},
\qquad B_i=\beta I+K_{S_i,S_i}.
\]

The current token coefficient is

\[
c_i=(\beta I_T+X_{S_i}^TX_{S_i})^{-1}x_i.
\]

The push-through identity gives

\[
c_i=X_{S_i}^TB_i^{-1}e_1.
\]

Therefore the existing exact decision can be written as

\[
v_{ri}=w_{ri}
+\sum_{h<i}(w_{rh}-q_{rh})a_{hi},
\qquad
a_{hi}=K_{h,S_i}B_i^{-1}e_1.
\]

This identity preserves the original coordinate order and lower-code ties.
It is an algebraic backend change, not a new deletion problem or a novelty claim.

### A concrete certificate route

Build directed bounds for \(K\) from the original feature boxes.
Column outer products require \(O(d^2T)\) work.
Every realized suffix matrix satisfies \(B_i\succeq\beta I\).
That fact follows from the actual feature construction, even if the interval hull contains indefinite matrices.

For a nominal vector \(\widehat y_i\), verify a residual bound

\[
\|e_1-B_i\widehat y_i\|_2\le\eta_i
\quad\text{for every realized }B_i.
\]

Then

\[
\|B_i^{-1}e_1-\widehat y_i\|_2\le\eta_i/\beta.
\]

Directed products bound \(K_{h,S_i}\widehat y_i\).
Add the coefficient error allowance

\[
\|K_{h,S_i}\|_2\eta_i/\beta
\]

to enclose each \(a_{hi}\).
The norm must itself be bounded over the supplied Gram enclosure.
The resulting triangular coefficient intervals support a universal row decision verifier.

Generate nominal suffix proposals with reverse block-inverse or factorization updates.
Those updates require verification; they remain untrusted proposals.
Building and checking every suffix this way can cost \(O(d^3)\) overall.
Independently factoring every suffix would instead introduce an avoidable \(O(d^4)\) term.

The proposed total structural cost is

\[
O(d^2T+d^3+md^2),
\]

with \(O(d^2+dT+md)\) stage workspace before optional streaming improvements.
This is a design target, not an implemented or measured bound.
The residual certificate may be too loose at real conditioning and precision.
Acceptance must be tested before claiming a useful improvement.

### Select dimensions per stage

For \(d=768,T=2048\), the coefficient proxies are

\[
dT^2=3{,}221{,}225{,}472,
\qquad d^2T+d^3=1{,}660{,}944{,}384.
\]

For \(d=3072,T=2048\), they instead become

\[
dT^2=12{,}884{,}901{,}888,
\qquad d^2T+d^3=48{,}318{,}382{,}080.
\]

These are structural proxies with different hidden constants.
They do not prove a timing crossover.
They do show why one global token threshold is inappropriate.
An MLP output projection can have a different input width from an attention projection.

The policy must consider \(d,T,m\), workspace, certificate acceptance, and complete measured costs.
Any backend improvement must also be available to exact reconstruction where applicable.
The retained model target and canonical compressed state must remain unchanged.

## Approaches that do not close this gap

**Another cross-row coefficient cache:** V28 already shares the ridge coefficient table across all rows.
Stronger coefficients are also shared once constructed.
The remaining avoidable work concerns which coordinates need stronger checks and fallback reconstruction.

**Treating numerical rank as token count:** current allocations and loops still use all \(T\) columns.
The ridge matrix has full dimension \(T\) even when the feature matrix is rank deficient.
An exact smaller factorization would require its own verified identity and construction cost.

**Dropping tokens or applying an approximate projection:** this changes the exact calibration problem unless approximation error is certified.
A proved discarded-residual bound could support a new verifier.
It cannot silently replace the original feature matrix.

**Keeping one aggregate Gram matrix:** arbitrary source deletion still needs source-specific contributions or source replay.
A per-source dense Gram can exceed a short source's factor storage substantially.
Deletion histories also require canonical and numerically certified aggregate maintenance.
This route needs a full storage and reconstruction comparison before adoption.

**Increasing codec precision alone:** tighter boxes may improve acceptance.
They do not reduce \(dT^2\) construction or the dimensions of eager preconditioning.
The existing 16-token acceptance result cannot establish a sufficient precision at larger \(T\).

**Timing only the native kernel:** this omits descriptor decoding, Gram construction, verification, context construction, output, and fallback.
The principal large-token problem occurs outside that kernel too.

## Required gates before expansion

1. Implement coefficient-work and workspace limits independent of neural replay limits.
2. Test requested-coordinate certificates and mixed-table row assembly against exact small oracles.
3. Implement the primal route and prove its equivalence to the existing exact target.
4. Verify its directed Gram, residual, norm, and tie arithmetic independently.
5. Register small real-data comparisons with identical targets and optimized baselines.
6. Record total retained tokens, record lengths, width, failed rows, requested coordinates, and route-specific work.
7. Expand only after complete cost and quality gates pass.

The present code is not approved for automatic broad expansion at \(T=512\) or \(T=2048\).
This is an engineering decision based on exposed scaling, not a predicted runtime failure.
At \(T=128\), a bounded registered diagnostic may be appropriate after work guards exist.
None of these token counts is a universal scientific adequacy threshold.

## Implemented conservative admission helper

`src/calibration_admission_v29.py` evaluates necessary array sizes using exact Python integers.
It allocates no numerical arrays and does not invoke a quantizer.

The caller supplies a tuple of `StageShape(stage_id, width, rows)` values.
`assess_calibration_admission` also requires pooled `retained_tokens` and `process_cap_bytes`.
Each stage reports these quantities.

- One dense token matrix: \(8T^2\) bytes.
- One feature matrix and one coefficient table: \(8dT\) bytes each.
- Logical lower and upper endpoints: \(16dT\) bytes.
- One weight matrix: \(8md\) bytes.
- A hypothetical primal matrix: \(8d^2\) bytes.

The implemented lower bound is the maximum required single-array size across stages.
It deliberately avoids summing potentially aliased storage.
A request is rejected only when this lower bound exceeds the specified process cap.

A passing result is named `not_ruled_out_by_lower_bound`.
It does not guarantee fit, speed, completion, or certificate acceptance.
The helper also reports \(8T\sum_s d_s\) raw factor bytes.
Those bytes are not compressed storage and are not added to the process lower bound.

The primal size is informational only.
The helper labels the primal certificate as unimplemented and never dispatches to it.
This admission helper does not implement the stronger coefficient-work guards recommended above.

Static plans appear in `campaigns/calibration_admission_plans_v29.json`.
They assume one stage with \(d=3072\), \(m=768\), and a six-GiB process cap.

| Pooled tokens | One token matrix | One raw factor matrix | Necessary single-array bound | Result |
|---:|---:|---:|---:|---|
| 16 | 2 KiB | 384 KiB | 18 MiB | Not ruled out |
| 128 | 128 KiB | 3 MiB | 18 MiB | Not ruled out |
| 512 | 2 MiB | 12 MiB | 18 MiB | Not ruled out |
| 2048 | 32 MiB | 48 MiB | 48 MiB | Not ruled out |
| 262144 | 512 GiB | 6 GiB | 512 GiB | Ruled out |

The hypothetical \(d\times d\) matrix is 72 MiB in every row.
That observation does not authorize an unsupported primal path.
Eight allocation-free software tests passed in a reported 0.001 seconds.
No empirical budget or existing numerical source changed.

## Audited source identities

| File | SHA256 |
|---|---|
| `src/native_ball_quantizer.py` | `543929a1cec335d8b111952b1d24d998d2420cc7abab734f5153e2b201069084` |
| `src/preconditioned_box_certificate.py` | `272dfff6829fdf0e1c5f30595c83d146844784f59f3c92de6b67d446c5473088` |
| `src/ball_box_certificate_v28.py` | `bf98801856dd629abbd6362acdf9d621151cfc4584743fc458680f2467aea906` |
| `src/fixed_compressed_service_v28.py` | `a060d5bbc6c21bd7bfe32f87750b157b440119121da4e8b03f0607276541e664` |
| `src/token_box_certificate.py` | `7144f740bc6d60dbab8128c990bfc0b2a7cc04034f857423a59f0f62904fec06` |
| `src/batched_token_solver.py` | `2e3f7aafd23312b4070fe566ff982a1311f6c5bb911023fe10bf03f014a12711` |
| `src/ball_box_certificate_v27.py` | `34e6c01c740941f17acbad07a017de7f8d94ba119205a59eb3ef5339ba4960d5` |
| `src/native_box_certificate.py` | `1b58c9c7771bd025d9f22c692fa77a5e8db7d2c27fc45bc2d3a0d0823bcd0033` |

Independent review cleared the scaling derivations and proposed algebraic identities.
The proposed numerical algorithms still require their own implementation and arithmetic reviews.
