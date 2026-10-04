# Fixed parameter boxes

Revision 6 adds an optional certificate provider.
The provider preserves the sequential V_cert target.
It removes the affine-span restriction from prefix membership.
It does not establish useful coverage or a speed improvement.

## Construction and API

`ParameterBox` stores an exact interval for each named weight coordinate.
Missing stages keep their finite base weights.
The constructor freezes every interval and validates shapes through the provider.
Its canonical payload binds endpoints, precision, and provenance.

`grid_box(decoder, target, provenance, precision_bits=96)` constructs one fixed box.
It reads base weights and frozen grids only.
It converts grid values through the decoder's binary64 installation rule.
Each interval contains the finite base value and every finite grid value.
The constructor includes only stages that affect later calibration features.

`BoxResponseProvider(decoder, box)` exposes the aggregate service interface.
Its provider identity binds the decoder, box, and provider source.
`contains_prefix(stage_id, prefix)` checks every installed finite ancestor coordinate.
Membership does not require an affine representation.
An external manually constructed box still requires independent provenance.
The registered grid recipe supplies reproducible provenance without calibration access.

## Finite feature bound

For a varying domain, propagate parameter intervals through the existing scalar proof evaluator.
Use each interval midpoint as the fixed anchor Z_j.
Use rank-zero jets, with empty gradient and Hessian arrays.
Each output entry provides a real interval [l,u] and finite discrepancy e.
Every successfully evaluated finite feature lies in [l-e,u+e].

Define the entrywise bound and its outward Frobenius bound:

\[
Z_{j,ab}=(l_{ab}+u_{ab})/2,
\qquad
d_{ab}=(u_{ab}-l_{ab})/2+e_{ab},
\qquad
\epsilon_j\ge\sqrt{\sum_{ab}d_{ab}^{2}}.
\]

Then every admitted successful finite evaluation satisfies this inequality:

\[
\|X_j-Z_j\|_F\le\epsilon_j.
\]

The midpoint minimizes the largest entrywise distance to the expanded interval.
It avoids a separate finite evaluation for the anchor.
It does not guarantee a better decision certificate because it also changes the proposal Gram.
The anchor is a feature matrix, not an installed model.

Identical installed ancestors imply identical finite features.
The implementation detects boxes containing only singleton base values for required ancestors.
It evaluates the finite base anchor and sets epsilon to zero without interval propagation.
Stages without ancestors also use this exact identity rule.

The provider identity binds this deterministic hybrid anchor policy.
The response record stores Z_j Z_j transpose.
The error record stores descriptors [epsilon_j,0,0].
The query uses an empty coefficient vector and zero residual.
Existing exact moment contraction supplies the Gram bound:

\[
\left\|\frac{\sum_j X_jX_j^T-\sum_j Z_jZ_j^T}{M_0}\right\|_2
\le 2\sqrt{z^2 e^2}+e^2,
\quad
z^2=\frac{\sum_j\|Z_j\|_F^2}{M_0},
\quad
e^2=\frac{\sum_j\epsilon_j^2}{M_0}.
\]

The implementation rounds the square root outward.
The response has no omitted tangent term.
All moments remain intrinsic and deletion-additive.

## Failure rules

Prefix membership and certificate success are separate conditions.
The full-grid recipe admits every possible frozen-grid prefix.
A broad interval can still fail the numerical proof.
A successful numerical proof can still produce an unusable Gram bound.

Examples include denominator intervals containing zero and excessive accumulated finite error.
Repeated interval occurrences can also produce excessive bounds.
The extractor marks these contributions unavailable.
The service then uses exact retained replay when necessary.
Required finite-evaluator failure still aborts the transaction.
No approximate model replaces a failed finite target.

## Resource changes

The response rank is zero.
Each group stores d squared response entries and six scalar error entries per stage.
The full-grid box stores two rational endpoints per used parameter.
This count excludes rational bit lengths and Python objects.

Parameter wrappers now use a lazy stage mapping.
The finite decoder, affine provider, and box provider share this mapping.
The executor creates only the parameter matrix currently requested.
The mapping does not cache parameter wrappers.
Later unused parameter matrices are never created.
The scalar operation order remains unchanged.

Activations, model weights, prefixes, exact Grams, and serialization still require memory.
This change does not make ordinary checkpoints feasible under current limits.
It does not reduce exact covariance dimension.
It does not prove a full-model latency improvement.

## Correctness checks

`tests/test_box_response_provider.py` checks independent coordinate changes outside an affine span.
It checks installed finite membership and all ancestor dependencies.
It verifies actual finite features and Gram matrices against computed bounds.
It checks canonical equality between repair, fresh execution, and direct replay.
It checks lazy allocation against the previous eager finite schedule.
These are software fixtures, not empirical datasets or performance measurements.

## Scientific scope

Interval propagation and constant feature anchors are established mathematical tools.
Their integration closes the affine-span membership limitation in this implementation.
It does not establish a new general interval-analysis method.
Useful certificates remain an empirical and algorithmic question.
Repair and indexed fresh receive the same provider.
The box therefore creates no inherent deletion-specific solver advantage.
