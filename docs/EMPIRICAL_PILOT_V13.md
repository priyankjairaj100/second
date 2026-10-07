# Revision 13: complete-state empirical pilot

Updated 7 October 2026. This is development evidence, not scientific confirmation.

## Main result

The complete model and retained state now fit the bounded worker.
Four methods returned identical retained models.
Three state-producing methods returned identical canonical state bytes.
Sequential and combined deletion agreed, ending with an empty retained set.
These observations close the earlier implementation blocker.
They do not close the repair-efficiency claim.

## Complete transactions

| Attempt | Operation | Wall seconds | Charged CPU seconds | Outcome |
|---|---|---:|---:|---|
| attempt-001 | Original preparation, logging defect | 35.540 | 36 | failed |
| attempt-002 | Original preparation | 546.164 | 543 | complete |
| attempt-003 | Repair | 263.641 | 264 | complete |
| attempt-004 | Model-only fresh | 284.776 | 285 | complete |
| attempt-005 | Indexed fresh | 282.691 | 282 | complete |
| attempt-006 | Direct fresh | 278.757 | 279 | complete |
| attempt-007 | Sequential second deletion | 46.714 | 47 | complete |
| attempt-008 | Combined deletion | 59.429 | 60 | complete |
| attempt-009 | New quality control | 581.804 | 582 | complete |
| attempt-010 | Batched repair | 174.839 | 175 | complete |
| attempt-011 | Batched model-only fresh | 182.655 | 183 | complete |

All model constructions cover 24 projection stages and 42,467,328 code values.
The original packed state uses 29,638,144 bytes.
The retained packed state uses 25,500,538 bytes.
Both fit the 512 MiB output cap.

Model agreement includes every decoded binary64 code.
State agreement uses canonical serialized bytes.
The common numerical kernels are shared between methods.
This comparison does not independently validate every neural operation.
Small software tests separately compare quantization with exact dense oracles.

## Deletion propagation

Deleting one of two calibration articles changed 1,970,198 codes, approximately 4.64 percent.
It changed 503,769 of 516,096 retained factor values.
This is one 50-percent deletion from a tiny root.
It does not estimate typical behavior on larger corpora.

The identity service encounters 23 changed-ancestor factor pairs.
It avoids none.
A cached first-stage read is later recomputed during downstream replay.
The counter includes that replay.
Repair and indexed fresh execute the same algorithm.

## Common solver improvement

The batched repair transaction took 174.839 seconds.
The matched batched model-only transaction took 182.655 seconds.
Both reproduce the reference model exactly.
The repaired state also reproduces the reference state exactly.
Batching applies equally to compatible methods.
These single timings establish no reliable speedup or deletion-specific advantage.
Cache state and other machine activity were uncontrolled.
Preparation-inclusive lifetime performance was not evaluated.

## Prospective quality control

Four previously unused validation articles provide 60 next-token predictions.

| Model | Perplexity | Ratio to base |
|---|---:|---:|
| base | 123.135998 | 1.000000 |
| nearest_rounding | 178.470179 | 1.449375 |
| retained_calibrated | 172.815176 | 1.403450 |

The calibrated model fails the proposed 1.20 quality-ratio screen on these articles.
These data are too small for a corpus-level quality claim.
No scientific gate passes from this diagnostic.
All four article IDs are excluded from later confirmation.
Earlier revision 12 article IDs remain excluded.

Revision 14 prospectively tests finer fixed dyadic scales on four different articles.
It defines a separate numerical target.
It does not revise this negative result.

## Accounting and provenance

Eleven attempts settled: ten complete and one failed.
The logging failure remains archived and charged.
The inherited debit through revision 13 is 7,019 CPU seconds.
The inherited remaining allowance was 3,781 seconds before revision 14.
Controller analysis, source freezing, and software tests are separate overhead.
They are not hidden inside repair-speed ratios.

An early controller misclassified a provisional reserved receipt.
Its erroneous derivative report remains archived.
The corrected driver requires settled receipts and ledgers.
Shared locks prevent overlapping research workers across revisions.

Plans, source snapshots, input hashes, receipts, and progress logs accompany every attempt.
Complete checkpoint, corpus, model, and state arrays remain local and reproducible.
Their hashes are published.
A fresh clone must regenerate those arrays.

## Decision

Complete-state correctness is supported on this tiny real-model case.
Useful changed-prefix factor transport remains unimplemented.
The current identity cache cannot meet the changed-ancestor avoidance gate.
Reliable full-model repair speed remains unproven.
The larger two-root feasibility workload and forty scientific cells remain unpromoted.

Read RESEARCH_DECISION_V13.md and TRANSPORT_BOUNDARY_V14.md before scheduling more timing repetitions.
Do not promote the method because one uncontrolled repair transaction appears faster.
