# Automatic transformer certificates

`src/certified_transformer.py` closes the automatic-provider gap for a declared scalar decoder.
It derives response jets, mixed curvature, and finite arithmetic errors from explicit weights.
It accepts no user-supplied error tolerance.
It uses the compact aggregate service in `src/aggregate_response_service.py`.

## Target contract

`CertifiedDecoder(base)` creates a **distinct finite target**, named `V_cert`.
It preserves the decoder architecture and explicit weights.
It replaces host nonlinear routines with the proved primitives in `certified_intervals.py`.
It binds both source files and the base manifest to its evaluator identity.

The architecture has learned position embeddings, pre-LayerNorm blocks, causal attention, and residual connections.
It supports erf-GELU and the explicit tanh-GELU variant.
It binds each activation schedule in its manifest.
Embeddings, normalization parameters, biases, and the output head remain fixed.
The stage order remains QKV, attention output, MLP input, and MLP output.

Each record runs alone with an explicit binary64 operation schedule.
The program checks round-to-nearest mode and gradual underflow at each public evaluation.
Proof entry points also check these conditions.
Each nonlinear result uses correctly rounded binary64 output.
Unresolved primitive rounding aborts evaluation.
Nonfinite results abort evaluation.
Thus, this program does not promise a result for every possible finite input.
Provider abstention triggers replay.
A primitive failure during replay aborts the request without an approximate model.
Exactness and fallback completion require every necessary finite execution to succeed.

Attention uses a stable finite maximum shift.
The proof does not differentiate that maximum.
The ideal function is smooth softmax.
A separate error bound covers the finite maximum, subtraction, exponential, sum, and division schedule.
The program rejects an interval whose possible score subtraction exceeds binary64 range.
This restriction prevents an unsound overflow certificate.
It no longer requires the first-score shift used during development.

This target is not the prior host-libm decoder target.
It also does not claim bit identity with Hugging Face, CUDA, or a floating GPTQ executable.
A local checkpoint adapter supplies weights to the declared architecture.
The adapter does not establish identity with another implementation.

## Fixed affine chart

Construct `AffineChart(directions, radii, provenance)` before using the deletable corpus.
Each direction maps stage names to exact rational matrices.
The box has one exact nonnegative radius per direction.
Missing matrices have zero direction.
The provider uses the decoder's finite base weights as its center.

For coefficients `a`, the mathematical parameter vector is

\[
\theta(a)=\theta_0+\sum_{t=1}^{r} a_t D_t,
\qquad |a_t|\le R_t.
\]

The chart and its provenance enter the reference identity.
The implementation cannot verify a historical claim that someone selected directions before viewing data.
The caller must satisfy that provenance condition.
The implementation proves the numerical bounds for the supplied fixed chart.

The provider solves an exact rational system for every new ancestor prefix.
It first applies the target's parameter conversion to the installed codes.
Thus, the chart must represent the actual finite weights exactly.
It rejects every nonzero residual.
It rejects coefficients outside the box.
It sets free coefficients to zero.
This choice can reject a chart that has another valid representation.
That rejection affects coverage, not correctness.

The provider ignores current and later matrices when fitting a stage's ancestors.
Those matrices cannot affect the stage input.
A chart does not need to represent unused later changes at that stage.

## Automatic derivative and error calculation

Each scalar jet stores four objects:

- An interval for the ideal real value.
- An interval for every first derivative.
- An interval for every mixed second derivative.
- A uniform bound for finite evaluation error.

The same decoder graph computes center jets and box-wide jets.
The center supplies rational midpoint response matrices `Z_0, Z_1, ..., Z_r`.
Interval radii give their respective errors `e_0, e_1, ..., e_r`.
The box-wide Hessian intervals give

\[
H_j=\sqrt{\sum_{o,s,t}\sup_{a\in\mathcal B}
  |\partial_s\partial_t F_{j,o}(a)|^2}.
\]

All square roots round upward to rational bounds.
The sum includes every output and every mixed derivative.
Cauchy--Schwarz bounds each Hessian action by `H_j ||a||_2^2`.
Taylor's integral remainder therefore gives

\[
\left\|F_j(a)-Z_{0j}-\sum_t a_t Z_{tj}\right\|_F
\le e_{j0}+\sum_t |a_t|e_{jt}+\tfrac12H_j\|a\|_2^2.
\]

Let `nu_j` bound the finite evaluator's error over the same box.
The intrinsic descriptor is

\[
b_j=(\nu_j+e_{j0}, e_{j1},\ldots,e_{jr},H_j,0).
\]

The last entry is zero because the provider rejects unrepresented parameters.
This yields the existing response certificate without a caller-supplied numerical premise.

Basic operations use

\[
|\operatorname{fl}(z)-z|\le 2^{-53}|z|+2^{-1075}.
\]

The provider proves a finite range before using that inequality.
It propagates both argument errors through multiplication and division.
Division requires the expanded denominator interval to exclude zero.
Nonlinear errors use derivative bounds over the expanded input interval.
LayerNorm uses a square operation that preserves nonnegativity.
It requires a positive square-root input throughout the expanded interval.
Unknown range, domain, or resource conditions make the descriptor unavailable.
The service then uses exact retained replay.

## Stable softmax proof

The ideal derivative uses `p_i = softmax(s)_i` and `mu = sum_i p_i grad(s_i)`.
Its first derivative is `p_i (grad(s_i)-mu)`.
Its second derivative includes the covariance of all score gradients.
The implementation retains every mixed term.
A fixed interval shift computes probability enclosures.
That shift does not enter the derivative as a branch.

The finite schedule chooses the largest finite score.
Its shifted arguments are nonpositive.
At least one argument is exactly zero.
Its exponential is exactly one.
Thus, the finite denominator is at least one.
Each finite exponential and each finite probability is at most one.
For sequence lengths at most `2^53`, monotonic rounding bounds each partial sum by its integer length.
This proves that denominator addition cannot overflow.

The ideal softmax Jacobian has infinity norm at most `1/2`.
This controls the effect of score errors.
Separate bounds cover subtraction, exponential rounding, denominator rounding, and final division.
The code uses the expanded finite score span in those bounds.
It rejects a probability enclosure whose denominator can include zero.

## Complete service

Use `decoder.make_repair_service(grids, chart, ...)` to construct the complete service.
It binds the automatic extractor, chart query, and finite evaluator.
It stores grouped response moments and source digests.
It does not retain per-record jets or source payloads.
Neither the decoder nor the provider caches record-dependent values.

Preparation computes intrinsic moments from each source record.
Deletion regenerates each removed record's intrinsic contribution.
A repair query fits the new prefix and contracts grouped moments.
Successful certificates need no retained source access.
Failed certificates replay retained records under the new prefix.
The resulting model and aggregate state match the independent fresh constructor.

## Software evidence and limits

Tests cover the complete decoder and both activation options.
They verify actual downstream feature changes against the generated Gram bounds.
They verify chart rejection and exact replay fallback.
They verify repeated deletion and canonical equality with fresh construction.
A nonzero decoder with multiple grid choices certifies without retained reads.
A further fixture makes deletion change an early code and its downstream features.
That fixture still requires no retained replay.
These are software correctness fixtures, not empirical datasets or speed measurements.

The implementation stores dense directions and full mixed derivative arrays during extraction.
A scalar operation can therefore need `O(r^2)` derivative arithmetic.
The direction bank can need `O(r P)` entries for `P` model parameters.
Exact chart fitting also reads ancestor weights.
Those costs remain part of preparation and query work.

Committed group storage uses `O(r d^2+r^2)` rational entries per stage and group.
It also stores `O(N L)` record metadata.
Integer bit lengths and canonical serialization add costs.
These counts do not imply a small memory budget for a large rank or model width.

The chart admits only represented changes within its fixed box.
An arbitrary pretrained quantization result can lie outside that chart.
A full coordinate chart would generally have impractical rank.
Interval bounds can also become too wide across deep blocks.
The service then replays correctly, but provides no acceleration claim.

This implementation establishes an executable certified path for the declared architecture and chart.
It does not establish useful coverage or latency on pretrained models.
Those questions require the paused real-data experiments.
