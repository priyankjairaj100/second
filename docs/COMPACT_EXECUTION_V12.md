# Compact execution and token-space quantization

Date: 7 October 2026. This revision resumes bounded research execution here.
The user requested maximum progress with limited remaining credits.
The original target and scientific feasibility thresholds remain unchanged.

## Implemented changes

Checkpoint tensors now retain immutable source bytes.
Exact access creates rational values only when needed.
The stored values equal the previous Fraction representation.
Signed zeros follow the previous Fraction conversion rule.
Stored causal masks receive exact shape and triangle checks.
The first real loading attempt exposed this previously unsupported buffer case.
Its failure remains in the experiment archive.

Parameter hashes and target weight hashes now stream their existing canonical encoding.
StageSpec retains validated compact storage instead of copying every parameter.
JobSpec caches its digest after streaming the immutable values.
Hash equivalence has software checks against the original encodings.
An explicit binary64 tree encoding avoids expensive decimal rational serialization.
It requires exact binary64 representability and binds every value, shape, and tree key.
Its identifiers differ from the default encoding.
The pilot declares both parameter and target-weight encodings in its frozen plan.

Finite linear maps batch independent output coordinates.
They preserve separate multiply/add operations and input-coordinate order.
They use no BLAS reduction for the declared finite target.
The reference rational nonlinear backend remains the default.
An optional MPFR backend constructs directed enclosures and checks identical rounded endpoints.
Both backends return the same correctly rounded values whenever both complete.
Their resource limits and rejection domains are not claimed equivalent.
The optional backend and loaded library hashes enter the evaluator identity.
Proof jets retain their existing arithmetic.

The incremental feature iterator computes each sequential prefix once per record.
Each stage receives the same features as a complete restart with the same preceding installed codes.
This follows by induction over the stage order.
The iterator preserves record-local attention, positions, residual branches, norms, and nonlinear operations.
It stops after producing the final stage's inputs when only quantization codes are needed.
Quality evaluation still requires the final output and language-model head.

The token-space solver avoids dense width-by-width rational matrices.
Its exact identity and residual certificate appear in TOKEN_SPACE_SOLVER_V12.md.
Approximate numerical solves only propose coefficients.
Directed residual checks and exact rounding-cell tests decide acceptance.
Unresolved decisions use bounded exact fallback or abort without returning model codes.
No tolerance silently changes an exact code.

Every compatible comparator must receive these changes.
They improve common execution and do not establish a deletion-specific solver advantage.

## Diagnostic execution policy

The reference dense planner remains unchanged.
A separate compact planner covers base loading, finite forward execution, and target metadata.
A token-quantizer pilot adds explicit storage allowances for codes, token matrices, and fallback workspace.
Neither planner proves peak memory or arithmetic completion.
External workers enforce the existing 900-second and six-GiB limits.

Each attempt freezes a separate source copy, protocol, input hashes, and runtime record.
Each worker receives live CPU admission before loading model weights.
The launcher carries the 614 prior charged seconds and every new reservation or debit.
The combined inherited feasibility allowance remains 10,800 worker CPU seconds.
Changing source snapshots or output directories does not reset that project allowance.
Launch attempts serially; the launcher does not provide concurrent cross-protocol admission.

These workers measure implementation feasibility.
Their clocks are diagnostic clocks, not complete four-method comparison clocks.
The result declares whether it produced finite logits or complete quantization codes.
It never labels those outputs as complete repair or canonical state.
The unchanged scientific gate still requires state correctness, changed-ancestor coverage, quality, and preparation-inclusive gains.

## Commands

Restore pinned inputs with `scripts/acquire_pilot_inputs.py`.
Use a fresh attempt identifier for each launch.

```bash
python scripts/launch_compact_pilot.py --id attempt-NEW --dataset wikitext2 --mode load_forward
python scripts/launch_compact_pilot.py --id attempt-NEXT --dataset wikitext2 --mode first_stage_quantization
python scripts/launch_compact_pilot.py --id attempt-LATER --dataset wikitext2 --mode full_quantization
```

Use `--dataset c4` for the archived bounded-prefix C4 records.
Do not describe that prefix as a corpus-wide sample.
Preserve each outcome before changing implementation or settings.
Use the measured campaign interfaces only after their complete prerequisites pass.

## Deletion and quality diagnostics

`--delete-index 0` removes the first lexicographically ordered calibration record.
The original normalization remains 32.
`--compare-attempt attempt-ORIGINAL` binds an already completed original model by hashes.
The worker requantizes retained records and compares codes stage by stage.
It separately advances the original prefix on the same retained records.
Feature comparisons therefore measure actual downstream propagation.
That diagnostic performs retained replay and claims no avoided features or repair speed.

Use `--mode model_quality --compare-attempt attempt-RETAINED` for the two-record WikiText quality check.
The heldout file binds two validation articles chosen using the existing fixed input order.
Their thirty next-token predictions cannot close a statistical quality gate.
Both IDs are excluded from future confirmation evaluation.
Ordinary floating NLL is explicitly distinguished from certified arithmetic.

## Explicit row-grid variant

`--grid-axis row` selects the new fixed output-row target.
The default remains the historical column target.
Use the same flag for quantization and its subsequent quality worker.

```bash
python scripts/launch_compact_pilot.py --id attempt-FRESH --dataset wikitext2 --mode full_quantization --delete-index 0 --grid-axis row
python scripts/launch_compact_pilot.py --id attempt-QUALITY --dataset wikitext2 --mode model_quality --compare-attempt attempt-FRESH --grid-axis row
```

The row variant has no declared complete repair-state contract.
Its scales depend only on fixed base weights.
ROW_SCALED_TARGET_V12.md explains exact normalization, restoration, ties, and rejection conditions.
Quality workers bind the actual model-generation plan and capture immutable prefixes once.
The original complete evaluation cost remains inside the worker clock.
