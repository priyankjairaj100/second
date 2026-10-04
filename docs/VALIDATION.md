# Revision 4 validation

Date: 4 October 2026.
Scope: software correctness, independent source review, and document checks.
Research experiments remained paused.

## Final software result

`python -m unittest discover -s tests -v`: **129 tests passed**, exit code 0.
Python static compilation passed for every source and test module.

The complete test output is in `validation/software_tests_v4.txt`.
`validation/tested_source_sha256_v4.json` records the tested source and test hashes.
Runner elapsed time is verification metadata, not repair-performance evidence.

The earlier 77-test result remains in `docs/VALIDATION_V3.md`.
Its original log and hash manifest remain unchanged.

## New coverage

| Module or review | Tests | Main checked properties |
| --- | ---: | --- |
| Certified primitives | 14 | Rigorous nonlinear intervals, rounding ties, subnormals, overflow, signed zero, and failure paths |
| Compact aggregate service | 12 | Deleted contribution checks, compact sums, signed bounds, normalization, canonical repeated state, and selected replay |
| Local GPT-2 adapter | 12 | Four dtypes, shards, transposes, activation variants, tied heads, provenance, and invalid inputs |
| Automatic certified decoder | 6 | Mixed response bounds, chart rejection, changed features, accepted repair, fallback, and canonical state |
| Independent adversarial checks | 8 | Separate arithmetic oracles, mixed Hessians, cancellation, underflow, and stable softmax |

The existing 77 correctness tests also pass.
These include independent exact quantizer checks and legacy service integration.

## Strongest integration fixture

A deleted record changes one first-stage QKV code from zero to `1/1024`.
The finite downstream features also change.
The network has nonzero operators and multiple code choices.
The retained-record loader raises an error on every attempted read.
Certified repair succeeds without calling that loader.
Its complete canonical state equals fresh construction on retained records.

This verifies deletion-induced change, not merely drift from the base reference.
Downstream matrices largely start exactly on-grid.
The fixture does not establish dense downstream changes or realistic certificate coverage.
Other checks cover repeated deletions, changed-reference bounds, and out-of-chart replay.

## Independent review

The review is in `theory_revision/implementation_review_v4.txt`.
The reviewer found no unresolved soundness defect under the declared contracts.
This was manual source review, not proof-assistant verification.

Review resolved these concrete issues:

1. Proof entry points now enforce the binary64 runtime checks.
2. Primitive caches no longer retain data-dependent inputs.
3. Stable max-shift softmax replaced the temporary first-score shift.
4. The softmax sum proof now states its sequence-length bound.
5. The acceptance fixture now checks deletion-induced old-versus-new code changes.
6. Bare GPT2Model imports explicitly declare the added output head.

The review checked signed Gram bounds, normalization, mixed curvature, finite errors, and source bindings.
It also checked metadata costs and the absence of persistent per-record descriptor caches.

## Numerical and state limits

V_cert is a distinct finite numerical target.
It is not native Hugging Face, the earlier library-math V, or historical floating quantizer E.
Provider abstention triggers retained replay.
Unresolved or invalid finite execution aborts the transaction without returning an approximate model.
Completion requires the necessary finite executions to succeed.

Chart directions must be independent of the deletable corpus.
The implementation cannot prove that historical provenance condition.
Exact chart fitting can reject valid alternative representations when it sets free coefficients to zero.
This affects coverage, not correctness.

Canonical state excludes deleted logical entries and request-local caches.
It does not prove physical erasure or authenticate hostile storage.
Metadata still uses O(NL) entries and scans.
Rational bit lengths, chart fitting, and deleted extraction remain costs.

## Document validation

The consolidated PDF has **27 pages**.
LaTeX completed without overfull boxes.
All pages were rendered for inspection.
The new implementation pages were checked at full page size.
The report source and output remain in the repository.

## Excluded evidence

No pretrained checkpoint or calibration dataset was downloaded or evaluated.
No benchmark campaign, synthetic empirical dataset, or external compute job ran.
No practical coverage, latency, quality, memory, or lifetime result is claimed.
Earlier missing raw experiments were not recovered or rerun.
