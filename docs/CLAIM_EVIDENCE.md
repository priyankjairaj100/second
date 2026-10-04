# Claim and evidence map

Date: 4 October 2026.
Read this document with `PUBLICATION_THEORY.md` and the frozen experiment protocol.

The map separates derivations, executable checks, and empirical evidence.
Manual mathematical review is not proof-assistant verification.
Correctness fixtures are not benchmark observations.

## 1. Claim decisions

| Proposed claim | Current supporting evidence | Remaining evidence | Permitted scope |
| --- | --- | --- | --- |
| Successful repair matches complete retained quantization. | Publication T1–T5; exact local oracle; reviewed automatic provider; integration fixtures. | Real-checkpoint equality under the frozen target. | Mathematical guarantee under shared assumptions and successful finite execution. |
| Repair permits changed ancestors. | T5 induction; a fixture changes an early QKV code and later features. | Real requests with substantial early and later changes. | Supported mechanism. Practical frequency remains unknown. |
| Accepted codes require no approximation tolerance. | Squared rational cell checks and exact midpoint rules. | Independent comparisons on every real stage and output artifact. | Exact equality to the declared rational quantizer. |
| The provider certifies the actual numerical target. | Interval primitives, finite error propagation, runtime guard, mixed derivatives. | Check supported domains and errors on chosen checkpoints. | `V_cert` only. Native library or CUDA equality is absent. |
| Replay safely resolves missing certificates. | T5 and replay fixtures. | Real fallback paths and failure classifications. | Completion requires successful finite evaluation and sufficient resources. |
| The complete state equals fresh retained construction. | T6; canonical serialization; bounded reload; repeated-deletion tests. | Real repeated request sequences and storage audit. | Logical live state under the declared trusted storage interface. |
| Aggregate matrix storage avoids per-record matrices. | Group sums; empty embedded record lists; source review. | Serialized bytes and peak memory across real configurations. | Fixed-group matrix entry count. Metadata still grows with records. |
| Compact moments retain second-order uncertainty. | T3 and the exact-jet, in-chart analysis. | Measure every finite, jet, residual, and contraction contribution. | Conditional local order. Nonzero error floors can dominate. |
| Full quadratic moments give a larger local regime. | Whitened theorem and its margin condition. | Implement the same acceptance rule before empirical attribution. | Stronger theorem, separate from the compact service's rule. |
| Repair avoids retained reads. | One changed-prefix fixture; conditional stage certificate. | Coverage over fixed real workloads, including failure cases. | Some accepted requests. No universal or practical rate claim. |
| Repair reduces complete request latency. | T7 states sufficient cost conditions. No benchmark evidence. | Paired complete timing against direct and equally indexed fresh baselines. | Withhold until measured. |
| Repair provides reliable speedup. | A defined reliability estimand; no measured success probability. | Completion, joint speed events, tails, uncertainty, and full failure counts. | Withhold until measured on the frozen request law. |
| Preparation pays for itself. | Lifetime accounting condition only. | Setup, storage, repeated requests, and crossover measurements. | Withhold until measured. |
| Repaired models preserve retained-oracle NLP quality. | Exact model equality gives identical declared inference behavior. | Verify artifacts and held-out metrics under identical inference settings. | Equality to that oracle. It does not prove useful absolute quality. |
| The quantization target has useful NLP quality. | No pretrained empirical evidence. | Full-precision, original-calibration, and retained-calibration quality results. | Withhold until measured. |
| The method outperforms equally indexed fresh solving. | No inherent solver advantage follows from current information access. | Measured savings from a concrete additional mechanism. | Withhold. Report equal solving costs if observed. |
| The work is novel. | Focused primary-source audit with explicit adjacent precedents. | Updated audit and precise comparison near submission. | Narrow contribution claim. No universal priority assertion. |

## 2. Mathematical evidence locations

| Publication result | Existing derivation | Main executable support |
| --- | --- | --- |
| T1: finite response enclosure | Report Sections 18, 22, and 25; numerical contract. | `certified_transformer.py`, `certified_intervals.py`. |
| T2: intrinsic moments and Gram bound | Report Sections 17, 18, and 20. | `response_moments.py`, `response_certificate.py`. |
| T3: compact signed bound | Report Section 21. | `linear_response.py`, aggregate `_proposal`. |
| T4: discrete decision certificate | Report Section 2 and independent matrix derivation. | `exact_core.py`. |
| T5: sequential exactness | Report Sections 4, 19, and 24. | `repair_service.py`, `aggregate_response_service.py`. |
| T6: canonical state | Report Sections 1, 17, 19, and 24. | Aggregate deletion, bindings, and canonical serialization. |
| T7: complete-work condition | Report Sections 9, 20, and 24. | Complete cost measurement remains separate from local counters. |
| Conditional zero replay | Report Sections 19 and 21. | Compact rule uses signed absolute budgets. |
| Exact-query storage limit | Report Section 20. | Mathematical construction; no benchmark requirement. |
| Feature-query obstruction | Report Section 11. | Mathematical oracle model; no universal transformer conclusion. |
| Cooperative regression bound | Report Section 10. | `work_scheduler.py`; not integrated with full repair. |

## 3. Existing software evidence

The revision 4 baseline passed 129 correctness tests.
The exact log is `validation/software_tests_v4.txt`.
The tested hashes are in `validation/tested_source_sha256_v4.json`.
These files describe that checkpoint only.
Later code changes require their own validation record.

The strongest fixture checks an early QKV code change from zero to `1/1024`.
Its downstream finite features change.
Its retained loader rejects every attempted source read.
Repair still equals the complete fresh canonical state.
Several later matrices start on-grid.
Do not present this fixture as dense practical model repair.

`docs/VALIDATION.md` gives test categories and review corrections.
`theory_revision/implementation_review_v4.txt` records independent source review.
The review found no unresolved defect under the stated contracts at that checkpoint.
It does not prove absence of all implementation defects.

## 4. Required empirical records

Each request record must identify the target, checkpoint, corpus root, deletion request, and method.
It must identify exact configuration and source revisions.
Save complete artifact hashes and canonical state hashes.
Compare full artifacts where hashes or metadata disagree.

Record the following diagnostic groups:

| Group | Required quantities |
| --- | --- |
| Target execution | Success, abort subtype, primitive limits, runtime guard, and token boundary checks. |
| Chart fit | Rank, direction bytes, ancestor displacement, residual result, box result, and fitting time. |
| Provider evidence | Availability, numerical rejection subtype, finite bound, jet bound, curvature contribution, and residual contribution. |
| Gram certificate | `beta`, `delta`, signed budgets, ridge, normalization, and outward contraction precision. |
| Decision certificate | Candidate codes, changed codes, margins, energy, scale interval, and rejected cells. |
| Replay | Groups, records, source bytes, evaluated stages, attempts, and replay time. |
| State | Deleted extraction, bindings, metadata scans, serialized bytes, and persistent caches. |
| Resources | Complete elapsed time, disjoint component times, peak memory, integer lengths, and output bytes. |
| Quality | Held-out loss and selected NLP metrics under the declared evaluation protocol. |
| Failures | Every attempted request, consumed resources, timeout, abort, mismatch, and exclusion reason. |

Some quantities need runner instrumentation.
The current stage audit does not export every numerical rejection subtype or local margin.
Do not infer missing quantities from a successful return code.

## 5. Comparison obligations

The direct fresh oracle must use the same numerical target and full output contract.
The equally indexed fresh solver must receive the same retained indices and supported planner.
Do not force that solver to read records when a valid certificate avoids those reads.

Report preparation separately for each method.
Include the preparation difference in lifetime cost.
Separate solver-only timing from the complete request.
The complete request includes deleted evidence extraction, validation, state maintenance, and output.

Compare fixed-reference and response methods under matched settings.
Compare replay-only behavior and certificate-driven behavior.
Use affordable quadratic moments only under a stated memory budget.
Distinguish the quadratic mathematical bound from any implemented experimental rule.

## 6. Claim rejection rules

An incorrect artifact blocks the corresponding exactness experiment.
Investigate the cause before interpreting its latency.
Keep the failed attempt in the recorded workload.

Poor chart coverage requires a narrower claim or a justified algorithm change.
A new chart fitted to deletable data requires its own deletion semantics.
An undocumented numerical target change invalidates a matched exactness comparison.

No full-service advantage means no full-service speed claim.
Equal indexed solving costs mean no deletion-exclusive solver claim.
High preparation costs must appear in lifetime results.
Low absolute language quality cannot be replaced by perfect repair agreement.

## 7. Wording guardrails

Use: "Repair matches the declared retained-data target under the stated execution assumptions."
Avoid: "Fallback always succeeds."

Use: "Compact group moments reduce the matrix entry count at fixed rank and grouping."
Avoid: "State storage is independent of dataset size."

Use: "A conditional theorem permits exact repair after changed ancestor codes."
Avoid: "Small deletions guarantee fast full-model repair."

Use measured reliability values only after the frozen confirmatory study.
Do not replace them with fixture pass rates or local rounding counts.

The project has no recovered raw evidence from its earlier missing experiments.
Historical narrative remains context, not a substitute for current reproducible results.
