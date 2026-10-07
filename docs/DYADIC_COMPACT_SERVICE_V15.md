# Complete identity repair with finer dyadic grids

The compact identity service now supports the finer dyadic row target.
This extends complete model and state reconstruction to that numerical target.
It does not establish a speedup or changed-prefix transport method.

## Numerical contract

Each row uses its fixed, base-derived dyadic scale.
The solver works in original weight units.
It never divides weights by an arbitrary dyadic scale.
Exact grid boundaries preserve the lower-code midpoint rule.
Positive ridge and original token normalization remain fixed after deletion.

The existing numerical target digest remains separate from the service contract.
Its historical manifest declares model codes, without specifying repair-state bytes.
This wrapper adds the `factor_identity_v1` state contract.
Worker snapshots must bind both the numerical target and service implementation.
The wrapper does not alter or retroactively reclassify earlier experiments.

## Canonical complete state

Each stage packs indices with `grid_axis="dyadic_row"`.
Canonical hexadecimal binary64 strings bind its row scales.
Exact current-prefix factors retain the existing token and ancestor bindings.
Prior-state validation checks every scale, dimension, and retained token identity.

Direct fresh, indexed fresh, and repair emit identical state bytes for identical retained records.
Model-only fresh emits identical model codes without committing factor state.
Sequential and combined deletion preserve the same canonical final state.
No-op repair reuses every factor without neural replay.
Empty retained sets use the fixed positive-ridge quantizer.

The induction proof in `COMPACT_SERVICE_V13.md` applies unchanged.
Dyadic row scales are fixed and calibration-independent.
Each certified row decision therefore equals the same exact retained-data oracle.
Packed metadata preserves those exact code values without an inexact normalization step.

## Comparable solver work

All four methods call the same `quantize_dyadic_rows` routine.
That routine uses the common batched token coefficient and accumulator kernels.
Legacy `reference` and `batched` selectors both use this routine for dyadic stages.
Diagnostics record the effective solver as `dyadic_direct_grid`.
The selector therefore cannot create a method-specific acceleration advantage.

Repair and indexed fresh remain the same identity-cache algorithm.
Every changed ancestor prefix requires exact factor replay.
The reported changed-ancestor avoidance remains zero.
Finer grids address numerical quality; they do not resolve the transport blocker.

## Software validation

Focused fixtures compare all four methods and nonempty repeated deletions.
They also cover no-op repair, empty retained sets, and incorrect token or scale bindings.
A restarted finite decoder independently supplies each stage's factors.
A dense rational oracle then checks every row decision on a small complete decoder.
These fixtures are software validation, not empirical research datasets.
Real-model transaction results must be reported separately.
