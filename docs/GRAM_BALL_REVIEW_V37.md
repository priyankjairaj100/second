# Independent review of the shared-ball Gram baseline

Reviewed on 9 October 2026, before V37 registration or empirical outcomes.
The new adapter and prospective stage protocol pass this independent review.
All nineteen focused V37 software tests passed independently in 0.346 seconds.
No new Gram or real-data quantization was evaluated during review.

## Decision

V37 is ready for a separately registered bounded component experiment.
It strengthens the pooled-Gram comparator using compatible existing numerical infrastructure.
It does not establish a measured speedup, a new learning target, or a publication novelty claim.
Every V35 and V36 source snapshot and result remains unchanged.

## Mathematical check

The unchanged direct-Gram verifier establishes exact coefficients \(a_{ih}\) and componentwise bounds
\( |a_{ih}-\widehat a_{ih}|\le r_{ih}\).
Their exact target recurrence is

\[
v_{ri}=w_{ri}+\sum_{h<i}(w_{rh}-q_{rh})a_{ih}.
\]

Using virtual features \(z_h=e_h\) makes the generic accumulator
\(s_{i,h}=w_{rh}-q_{rh}\) for \(h<i\), and zero otherwise.
The supplied coefficients therefore describe precisely the same rounding input.
The adapter does not solve a new identity-metric quantization problem.
It passes the already certified Gram coefficients directly to the existing decision kernel.

Directed squared sums produce \(E_i\ge\sum_h r_{ih}^2\).
The existing exact square check then gives \(\rho_i^2\ge E_i\).
Consequently, \(\|a_i-\widehat a_i\|_2\le\rho_i\), satisfying the ball verifier's coefficient premise.
No independence or correlation assumption about coefficient errors is required.

The existing accumulator, dot-product, and underflow proof applies to these identity features.
Its dimension bound remains enforced with virtual rank equal to width.
The adapter retains the existing strict native source, compiler flags, and runtime checks.
Grid construction, coordinate order, subtraction signs, and lower-code ties remain unchanged.
Trusted PSD source lineage and preserved original normalization remain mandatory.

## Fallback and resource checks

A refused ball row receives one complete interval-verifier pass from coordinate zero.
That pass uses the same coefficient centers, radii, weights, and row grid.
The Gram and coefficient certificates are not recomputed.
Any unresolved fallback prevents return of the entire model.
Partially written native output buffers are never accepted as complete codes.

The admission calculation counts both possible row passes.
It also covers identity storage, radius temporaries, full output, and selected-row copies.
For the full QKV stage, it reports 3,172,737,024 structural work units and 413,614,080 explicit array bytes.
These fit the stated six-billion-unit and 512-MiB limits.
The bounds remain structural estimates, not wall-time or total-process-memory guarantees.
Caller Gram residency, exact accumulation, compiler overhead, and OS limits remain separately accounted.

Runtime and allocation errors remain fatal.
Only the previously declared narrow scientific refusal patterns permit independent arms to continue.
Successful and refused arms remain distinguishable from overall execution completion.
No reconstruction speed ratio is assigned to an incomplete certificate attempt.

Fallback diagnostics preserve the original failed-row mapping and measured fallback duration.
When the old fallback helper discards its receipt, unavailable native counts and duration are recorded as null.
They are not misreported as zero work.

## Protocol review

The same authenticated V36 stage capsule supplies every input.
All 2,304 output rows and 768 coordinates remain included.
The records, retained normalization, ridge, grids, order, and code reference remain fixed.
The new source inventory binds the adapter and both new controller scripts.
Prior ledgers remain unchanged; the new phase allowance is separate.

Preparation, pooled deletion, fresh retained-Gram reconstruction, and cached-token reconstruction run in fixed order.
Both Gram arms receive the strengthened row verifier.
The token comparator retains the same native ball kernel it already used.
All radius conversion and fallback costs remain inside the relevant arm.
Shared setup and compilation remain separately reported under the V36 clock boundary.

Terminal verification checks actual accepted code files against the authenticated complete reference.
It revalidates refusal class and message and prohibits partial output artifacts.
Canonical repaired and independently constructed Gram artifacts must still agree.
Unknown errors stop execution, with no automatic retry or replacement sample.

This is adaptive development following the V36 bottleneck diagnosis.
One fixed-order stage observation cannot establish reliable complete-model or lifetime superiority.
Further optimization of the shared coefficient builder or accumulator remains possible.
The forthcoming result therefore compares concrete implementations, not all possible Gram methods.

## Validation and reviewed digests

Eleven numerical fixtures check rational oracles, deletion, normalization, exact ties, and unchanged kernel provenance.
They also check Euclidean radius containment, failed proposals, two-pass admission, and fallback refusal.
Eight protocol fixtures check narrow failure classification, registration integrity, prior ledgers, and no retries.
These are software fixtures, not synthetic empirical datasets.

| File | SHA-256 |
|---|---|
| `research_v37/direct_gram_ball.py` | `5f0400c9d09e6fe2517c4de5ca9ecc059067de74b624bb91b85cc79f53681b0a` |
| `scripts/execute_gram_ball_stage_v37.py` | `99e28fde2cf3764e91bcd50ccc6a7293a1c1e18d988bd1705a2c6e7c27a664e6` |
| `scripts/launch_gram_ball_stage_v37.py` | `ce06587b5aaed3d55305b7568586840ab5acee151a2646a43eecd82c369f3336` |
