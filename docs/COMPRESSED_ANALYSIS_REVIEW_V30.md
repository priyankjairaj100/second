# Independent compressed analysis review

The compressed-service analyzer passed this independent source review after accounting corrections.
No remaining blocker was found within the recorded analysis scope.

| File | Reviewed SHA256 |
|---|---|
| `scripts/analyze_compressed_service_v30.py` | `32e3e5804d5e743e9d4de9e502695fbe6624cf57295104400c6228ef5ffd2d6f` |
| `tests/test_compressed_service_analysis_v30.py` | `7f7b45c999e359f7f7709af19b6d9292d9bd3ad64224821ace61bed173117183` |

## Evidence and comparison scope

The analyzer requires both registered compressed transactions and every declared external comparison.
It checks registration, source snapshots, exact commands, inputs, receipts, output artifacts, and settled CPU debits.
It retains the original complete model and verifies the retained model against its registered reference.
The quality prerequisite must bind that same retained model.

Scientific losses remain completed observations.
Storage equality does not pass the strict storage gate.
Latency equality does not pass the strict latency gate.
All three registered cold observations remain visible.
The latency gate uses their minimum, as registered before execution.
The matched lossless repair time and lossless/compressed ratio are also reported.

Complete compressed preparation includes lossless preparation and the additional conversion transaction.
The original model-only comparison has the same original model and mathematical target.
Its cost remains an existing observation, not a newly measured control.
No changing-state lifetime or population superiority follows from these calculations.

## Numerical work accounting

Conversion must verify every descriptor's source hash and containment without neural evaluation or quantization.
Every accepted box stage must name an admitted certificate route and report no rejection.
Every successful singleton stage must likewise report no rejection.
Accepted and singleton stage rows cannot report new neural traversals.

Every attempted certificate or point stage requires exactly one matching work reservation.
The reservation must match its actual route and admitted work allowance.
Missing, duplicate, additional, and mismatched stage reservations cause refusal.
Forced certificate routes are checked against their own admission, rather than the proxy's preferred route.

Replay counts agree across stage rows, retained sources, and aggregate diagnostics.
Source counts must be nonnegative integers.
The analyzer distinguishes certificate acceptance from avoided ancestor replay.
A later replay can traverse earlier accepted stages, so acceptance alone does not imply avoided neural work.

An early numerical refusal can occur before any unresolved coordinate round is recorded.
The final analyzer reports missing coordinate evidence as null and handles explicitly empty rounds safely.
It does not fabricate an empty set of unresolved coordinates from absent evidence.

## Verification

The reviewer independently reran all ten focused fixtures successfully in a reported 0.009 seconds.
The fixtures include preserved scientific losses, complete preparation accounting, and malformed stage reservations.
They also cover contradictory acceptance fields, missing external bindings, and empty diagnostic rounds.

The completed conversion and repair terminal diagnostics passed the same consistency checks during review.
The analyzer author remains responsible for the complete read-only archive audit under the reviewed source.
This review does not substitute a software fixture for that final archive verification.

No model inference, empirical worker, numerical source edit, or immutable evidence change occurred during this review.

## Final archive integration and root review

The first full audit refused the quality receipt because its schema omits a top-level source inventory.
No audit artifact existed after that refusal.
The final adapter supports only `adaptive-quality-followup-v30` with the exact follow-up worker name.
Its recorded evaluator hash must match the frozen source inventory.
The surrounding plan and worker checks still bind the full inventory, terminal plan digest, and literal command.

Root independently reviewed this adapter and cleared the final analyzer.
Root also reran its focused adapter fixture successfully.
The author ran all eleven analysis fixtures successfully in 0.010 seconds.

| Final artifact | SHA256 |
|---|---|
| `scripts/analyze_compressed_service_v30.py` | `1c76a6ab303b8cfd0665ba09770200d525547d84ed2c78a04385749c62cb1da0` |
| `tests/test_compressed_service_analysis_v30.py` | `72be2eb7e905aaffeaa099a6cf83d728f680308a7e867d52551e63a1d9235a85` |
| `campaigns/compressed_service_v30/audit.json` | `282302fe2fca7c93d432ffe5b166cde2da24f0568589bf75888de558ee71259a` |

The complete archive audit succeeded under the final source.
It recorded 3.903266989 CPU seconds outside the empirical worker ledger.
Both transactions settled, with 379 charged CPU seconds against the separate 1,200-second cap.
No unresolved reservations or historical ledger changes were found.
The immutable audit remains unchanged.

The audit preserves the failed latency gate and successful storage gate.
Repair took 312.326876080 seconds; the fastest registered cold observation took 140.549491491 seconds.
Matched lossless repair took 70.638262118 seconds.
The compressed successor saved 6,963,345 bytes, or 13.683448% of the complete lossless state.
Twenty-two accepted stage certificates still led to all twenty-four retained neural traversals.
Two unresolved decisions caused replay: `(415, 230)` in `block.0004.mlp_up` and `(568, 2229)` in `block.0005.mlp_down`.

Complete preparation includes 309.591227326 seconds for lossless preparation and 66.086826913 seconds for conversion.
The resulting 375.678054239-second preparation costs 88.782093707 seconds above matched original model-only preparation.
These observations do not establish a compressed-repair latency benefit.
