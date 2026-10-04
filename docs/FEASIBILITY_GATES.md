# Predeclared feasibility decisions

This policy closes C04 at its written decision scope.
It does not establish that any checkpoint meets the thresholds.
`configs/feasibility_gates_v1.json` freezes the numerical policy before real tuning.
The thresholds are engineering choices, not universal standards or power guarantees.
Research remains paused.

## Required workload

Use two independent calibration roots.
Each root contains eight real records with 32 tokens per record.
Use the protocol's complete request laws and three ordered deletion requests.
Retain every planned failure and missing observation.
The calibration, development, confirmation, and evaluation sources follow the existing separation rules.
Software fixtures cannot satisfy this gate.

A one-root, two-record, 16-token preflight only checks whether the complete path can run.
It cannot establish useful coverage, quality, or speed.
All target and source bindings must be valid before that preflight.

## Correctness and resource decisions

Every model must match all target stage codes.
Every repair state must match its declared retained-state oracle.
The allowed mismatch count is zero.
A mismatch stops promotion and requires an implementation correction.
Missing outputs cannot count as matches.

Each worker has a 900-second wall limit and a 900-second CPU limit.
Its declared address limit is 6 GiB.
Observed peak RSS must also remain at most 6 GiB.
Each artifact must remain at most 512 MiB.
Complete original preparation must finish within 900 seconds.
The complete three-request lifetime must finish within 3,600 seconds.
The feasibility allowance is three worker CPU hours.
The development allowance after redesign is 12 worker CPU hours.
These limits do not imply physical containment of every process.
The existing admission contract still applies.
Supported campaigns now provide explicit feasibility phase dispatch.
The selected command must still use its required admission path.

A resource failure requires redesign within the remaining allowance or a narrower paper scope.
Do not increase limits after observing failure without a prospective policy revision.
Keep the failed attempt in the record.

## Changed-ancestor coverage

For each request, compare installed ancestor codes with the preceding committed model.
Identify every nonempty retained stage group whose transitive ancestors actually changed.
Those groups form the denominator.
Include every such group from every planned request on that root.
Do not select only stages with favorable margins or available descriptors.

Count a group in the numerator only when repair avoids its retained target-feature evaluation.
A resident data cache does not turn feature evaluation into avoidance.
A certificate for an unchanged ancestor group does not enter this numerator.
The ratio must reach one quarter on every root.
A zero denominator means the changed-ancestor mechanism was not demonstrated.
It does not mean perfect coverage.
A missing or failed request keeps the coverage decision incomplete.

Coverage below the threshold requires certificate redesign or a narrower mechanism claim.
Coverage alone does not justify promotion.
Preparation and lifetime costs must also pass.

## Quality

Evaluate the retained fresh model and base model on identical heldout tokens.
Use the same declared evaluator and token boundaries.
Require equal positive scored-token counts.
For every root and request, require:

\[
\operatorname{NLL}_{\mathrm{retained}}-\operatorname{NLL}_{\mathrm{base}}
\le \log(6/5).
\]

This equals a maximum perplexity ratio of 1.2.
Compute the decision in log space.
Missing or nonfinite metrics keep the quality decision incomplete.
This diagnostic uses finite numerical loss calculations.
It is not a certified bound on language quality.
A failure requires a prospectively revised quantization setting or narrower scope.

## Complete cost and lifetime

The ordinary requantization comparator returns only the quantized model.
It does not rebuild the response index.
The existing `direct_fresh` method remains the separate canonical-state oracle.
Equally indexed fresh receives the same valid retained information as repair.

For each root, compare a fixed horizon of three ordered requests.
Charge each system's original preparation once.
Charge every request, input read, required online verification, state update, serialization, commit, and cleanup.
Record external research oracle checks separately.
Do not charge those checks asymmetrically across systems.
Use the same declared external observation boundary.
Exclude only the final external observer receipt from both systems.
Never add nested method clocks to their enclosing transaction clock.
A missing cost or unsupported boundary keeps the lifetime decision incomplete.

Require the repair system's complete lifetime to be strictly smaller on each root.
The comparator performs original model-only construction and each retained model-only construction.
The repair system also pays for the index it needs.
This checks whether three requests amortize that extra preparation.
A gain against a full-state reconstruction alone does not satisfy this condition.

A tie or loss against equally indexed fresh prevents a deletion-exclusive solver claim.
Useful gains may instead support a claim about index maintenance and sequential model construction.
If coverage and quality pass but lifetime cost fails, redesign cost or narrow the contribution.

## Promotion and stopping

Apply the policy in its listed order.
Correctness failure takes priority over performance.
Missing evidence keeps the gate open.
Resource, quality, coverage, or cost failure requires redesign or scope reduction.
After the fixed development allowance, preserve the failure and choose the narrower supported claim.
Passing all feasibility gates permits development.
It does not permit confirmation or establish reliable speedup.

Confirmation still requires frozen settings, a full inventory, and a justified number of roots.
A reliable speed claim requires all planned requests to complete exactly.
Its lower 95 percent interval must exceed 1.05 under the specified root-level analysis.
No current result meets or tests these conditions.
