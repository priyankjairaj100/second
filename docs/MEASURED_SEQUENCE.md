# Matched measured sequences and lifetime costs

Revision 9 adds `src/measured_sequence.py` and `scripts/run_measured_sequence.py`.
It preserves the legacy warm sequence runner.
This is preparation infrastructure and software correctness evidence only.
Research remains paused. No model, corpus, or timing study has run through this path.

## Fixed input and ordered target

A measured sequence plan binds the original sequence manifest, complete numerical target, executable sources, runtime contract, worker limits, execution mode, four-role order, preparation order, and optional quality policy.
The original calibration records and original normalization remain fixed in every derived run manifest.
Step `i` changes only the request identity and cumulative deletion list.
The initial preparation manifest has an empty deletion list.
All filtering and feature work occur inside the measured child.

The frozen inventory schema is `calibration-measured-sequence-campaign-v1`.
Its embedded ordered inventory binds original record order, workload hashes, request provenance, cumulative membership, configuration, root, sequence, and repeat.
The associated measured plan adds clean or diagnostic execution, a four-position method counterbalance, and alternating preparation order.
Confirmation checks the declared configuration × root × sequence × repeat product.
Every external plan and manifest must match its embedded binding.
Only the protocol hash is cleared from embedded manifests, preventing a protocol/inventory hash cycle.
The final protocol binds the exact inventory bytes.

`verify_measured_sequence_manifest` derives the authorized role manifest independently.
Step `-1` authorizes original preparation; nonnegative steps authorize cumulative retained targets.
A changed cumulative list, original normalization, checkpoint, target, or protocol fails that check.
Research pause and protocol CPU admission remain independent gates.

## Two preparations, performed once

The indexed system constructs its original model and canonical state once.
Repair and equally indexed fresh share this same preparation observation.
The ordinary fresh system separately constructs the original model without deletion state once.
Their complete model encodings must agree before the first request starts.
The preparation order is frozen and alternates across repetitions.
Sharing an indexed preparation across two controls is explicit correlation, not an independent repetition.
Preparation observations are never shared across different roots or repetitions.

Every later request has four separately measured roles:

| Role | Entering information | Returned output |
| --- | --- | --- |
| Repair | Previous committed state, newly deleted records, retained source | Complete model and next canonical state |
| Indexed fresh | The same previous state and valid reusable information | Complete model and next canonical state |
| Direct full-state fresh | Original manifest with cumulative deletions | Independent complete model and canonical state oracle |
| Model-only fresh | Original manifest with cumulative deletions | Ordinary retained requantization model |

Direct full-state and model-only fresh do not read the predecessor state.
Repair and indexed fresh validate the predecessor at the leaf, inside their measured transaction.
The check binds the original sequence plan, step index, previous and new deletion sets, preceding setup/repair child receipt, saved prior request, actual state/model artifacts, exact state digest, and live original-record membership.
The charged predecessor check reads the actual preceding repair/setup child receipt and its state/model artifacts, all already produced inside that earlier transaction.
Its saved request must match the independently derived previous step and the same target and source bindings.
It does not require a compact research lineage commit, common-model copy, prior observer receipt, or oracle/comparator artifact tree.
Full research archive verification checks all role receipts and rederives common model encodings separately.
Compact commits are research records and do not supply service state.
The prior state is not rebuilt.
A successful step commits an immutable lineage receipt before the next request.
Empty requests, complete deletion, and empty requests after complete deletion keep the same ridge-only target semantics.

## Complete transaction clocks

Each preparation and role uses `measured_comparison.invoke_role` and the external observer in `docs/TRANSACTION_TIMING.md`.
The clock includes source/input validation, worker startup, required loading and state validation, computation, artifacts, child-controller commits, exit, cleanup, and output verification.
Its final observer receipt is outside the interval.
Operating-system caches remain uncontrolled.
A fresh child process does not establish cold disk caches.

Non-quality roles skip held-out input loading.
Clean mode disables optional detailed service and allocation profiling while retaining required arithmetic counters and correctness checks.
Diagnostic observations remain separately labeled.
The frozen runtime contract and leaf instrumentation record are checked with the other bindings.

Sequence scheduling, common-model conversion, equality checks, and research lineage bookkeeping occur outside production-role clocks.
The same exclusions apply to all systems.
This is a research harness: it advances a step only after independent oracle equality has passed.
Its actual end-to-end wall time therefore includes oracle and research bookkeeping costs.
The per-system lifetime sum is an attributable transaction-cost estimand, not the elapsed duration of running this validation harness.
The method does not claim that a deployed repair service needs the oracle's model, state, or archive to process the next request.
The direct full-state oracle has its own complete observed cost and is a research control.
Optional held-out quality uses a separate bounded observed worker after exact step equality.
Quality time does not enter request or lifetime speed ratios.
These clocks describe declared transactions, not every physical action an external user might perform.

## Lifetime accounting

For the declared ordered horizon, a system's complete lifetime is its own initial preparation plus every complete request transaction.
Repair includes indexed preparation once and its repair requests.
Equally indexed fresh includes that same preparation once and its own requests.
Model-only fresh includes its separately observed original model construction once and every retained-data model reconstruction.
Direct-oracle, equality, and quality research costs are reported separately and never added to one system alone.
Nested observer spans are not added again to their enclosing total.

The result stores preparation rows, every planned step and role, predecessor hashes, canonical commit references, and convenient lifetime totals.
Analysis must rederive those totals from verified observer receipts.
A missing or failed required transaction makes the complete lifetime total null.
Observed completed costs and failed attempt durations remain visible; missing clocks cannot be reconstructed as zero cost.
No latency or break-even claim follows from an implementation fixture.

## Failure, archival verification, and restart

Every sequence and every planned step remains present after a failure.
A failed step stops progression of the committed state; later steps remain explicitly unstarted.
Other planned roles at that step retain their outcomes.
Each complete or failed child has its own observer result and nested artifact snapshot.
A sealed campaign verifies all archived runs, including failed artifacts, before returning saved results.

Restart reuses sealed observations with their original durations and CPU debits.
It never times loading an archived result as fresh service work.
A child whose original observer timing was lost cannot become a short successful observation.
The fresh observer refuses its preexisting transaction output, retaining an incomplete outcome.
A parent interruption after a sealed observation can continue from that observation.
The archive still preserves earlier attempts.

Trusted local storage is assumed.
Hashes and receipt consistency do not authenticate hostile replacement of all bound inputs.
The research archive retains predecessor states; returned live-state deletion does not erase that archive.

## Interfaces

- `build_measured_sequence_plan(...)`
- `build_measured_sequence_campaign(...)`
- `validate_measured_sequence_plan(...)`
- `validate_measured_sequence_campaign_files(...)`
- `verify_measured_sequence_manifest(...)`
- `run_measured_sequence(...)`
- `run_measured_sequence_campaign(...)`
- `verify_measured_sequence_archive(...)`

A campaign stores each result under `OUTPUT/runs/RUN_ID/result.json`.
Individual sequence output contains `work/preparation`, `work/steps`, `work/commits`, and derived manifests.

```bash
python scripts/run_measured_sequence.py /absolute/plan.json --output /absolute/output --validate-only
python scripts/run_measured_sequence.py /absolute/inventory.json --output /absolute/campaign --campaign --validate-only
```

Validation does not resume paused research.
Actual checkpoint feasibility, data partitions, frozen empirical inventories, statistical precision, useful certificates, quality, and speed remain unmeasured.
