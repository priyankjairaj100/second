# Complete compact service transactions

This implementation uses the new `factor_identity_v1` family.
It preserves the declared quantizer target.
It changes the stored state representation.
It stores exact factors, not dense Gram matrices.
It does not implement aggregate response repair.

## Contract

Each stage stores packed indices and fixed grid metadata.
Each retained record stores its exact finite feature factors at every stage.
Each factor binds the record tokens and the complete ancestor code prefix.
Original token normalization remains fixed after deletion.
The state contains no request history, timings, or previous deleted factors.
A trusted receipt binds the state bytes.
Internal hashes alone do not authenticate a hostile supplier.

The service accepts the complete sequential dependency graph.
It validates retained membership and token identities before cache access.
It reuses a factor only when its complete ancestor prefix matches.
Otherwise, it evaluates the retained record under the new prefix.
The certified token solver then computes the exact declared code matrix.
All compatible methods use the same finite kernels and solver.

## Four methods

| Method | Input cache | Output |
|---|---|---|
| model_only_fresh | None | Complete packed model |
| repair | Trusted previous state | Complete model and retained state |
| indexed_fresh | Same trusted previous state | Complete model and retained state |
| direct_fresh | None | Complete model and retained state |

Repair and indexed fresh currently execute the same algorithm.
They differ only in the declared comparison role.
Separate runs measure separate transactions.
They do not establish a deletion-specific algorithm advantage.
Direct fresh constructs every factor from retained records.
Model-only fresh does not construct or serialize retained state.

## Correctness

Proceed through stages in the fixed order.
At the first stage, features depend only on the record and base parameters.
Assume all earlier installed codes equal retained-data reconstruction.
A matching cached prefix therefore produces the same finite features.
A replay computes those same features directly.
The certified solver returns the same exact stage codes.
Induction proves complete model equality.

Every emitted factor then equals direct retained reconstruction at its current prefix.
Deterministic stage and record ordering gives identical canonical state bytes.
Repeated deletion and combined deletion therefore produce identical state bytes.
This statement assumes the same fixed target and identical final retained records.
Empty retained sets use the same positive ridge and fixed original normalization.

## Cost and coverage

The worker includes checkpoint validation and loading.
It includes target construction, state parsing, replay, quantization, packing, and output verification.
It writes artifacts atomically and syncs them before completion.
External worker receipts include process startup and cleanup under existing limits.
Controller analysis and source freezing remain separate costs.
Those costs are disclosed rather than added to a repair-speed ratio.

A cached read does not always avoid neural work.
Later replay can recompute earlier cached features.
The `neural_stage_record_pairs` counter includes that replay.
The service reports zero changed-ancestor feature avoidance.
No timing ratio can override that declared limitation.

## Separate transport modules

`finite_feature_boxes` bounds the finite decoder under supplied weight boxes.
`token_box_certificate` proves constant quantizer codes throughout a feature box.
Their composition gives a conditional code guarantee.
The current box evaluator still reads retained tokens and evaluates their operations.
This work counts as retained-source computation.
It does not demonstrate avoided feature evaluation.

A code certificate also does not reconstruct exact current feature factors.
It therefore cannot replace factor reconstruction in this service family.
A calibration-independent anchor family can change that state requirement.
Its complete costs and useful acceptance rates still need evidence.

## Measured pilot and later validation

EMPIRICAL_PILOT_V13.md records the completed eleven-attempt program.
TRANSPORT_BOUNDARY_V14.md states the complete-state information and cost requirements.
The later row-grid budget guard changes source-bound target digests.
Archived attempts keep their original source snapshots and target hashes.
Regenerate both preparation and query comparators under one source version for fresh runs.
