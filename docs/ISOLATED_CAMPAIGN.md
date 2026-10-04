# Frozen isolated campaigns

Revision 8 adds frozen inventory dispatch for separate-process comparisons.
It also adds an optional, separately budgeted diagnostic quality worker.
Research execution remains paused under the current protocol.
Correctness fixtures exercise these paths without providing empirical research evidence.

## Inventory and digest construction

The inventory schema is `calibration-isolated-campaign-v1`.
It binds all planned roots, requests, configurations, repetitions, method orders, workloads, sources, and worker limits.
Each entry also binds an isolated plan path, payload, and exact canonical hash.
Plan and manifest paths must be normalized relative paths within the inventory layout.

Each plan contains the standard manifest with only `protocol.sha256` cleared.
Its digest therefore does not depend on the final protocol bytes.
The protocol then binds the exact inventory through `planned_inventory_sha256`.
Finally, each runtime manifest receives the actual protocol hash.
Dispatch checks those final raw bytes independently.
No plan omits another manifest field from its binding.

The preparation order is:

1. Prepare workload definitions and local run manifests.
2. Construct isolated plans using `build_isolated_plan`.
3. Construct the inventory using `build_isolated_campaign`.
4. Bind the canonical inventory digest in the protocol.
5. Bind the resulting protocol digest in each runtime manifest.
6. Validate every source, plan, workload, manifest, and protocol binding.

These operations do not acquire inputs or authorize research execution.
Real checkpoint files, token records, source partitions, and score artifacts still need their separate validation.

## Confirmation admission

Confirmation requires `frozen_confirmation`, schema `calibration-protocol-v1`, and an empty `blocked_fields` list.
The declared configuration, root, request, and repeat Cartesian product must be complete.
The validator rejects missing comparisons, duplicate identities, changed method order, and altered deletion membership.
One configuration cannot mix target, chart, service, verifier, or quality settings within a phase.
Controls retain their separate analysis groups.

A standalone confirmation call cannot authorize itself with a Boolean flag.
It must provide a real inventory path and run identifier.
The executor reads and verifies the full inventory before accepting membership.
Each child independently checks the inventory, plan, runtime manifest, and declared target again.
The current source hashes must match at dispatch and resume.

The existing protocol pause blocks research before output creation.
No executor changes that pause or fills unresolved protocol fields automatically.
Feasibility uses its own declared phase and CPU cap.
Its source pool remains on the development side, separate from confirmation and evaluation data.
Supporting that phase does not authorize a new model run.

## Dispatch and failure accounting

The campaign dispatches each frozen plan serially.
Within each comparison, setup and the three methods receive separate limited processes.
Setup remains a distinct preparation cost.
Repair and indexed fresh reload the original state.
Direct retained construction avoids that unnecessary read.

Direct retained construction here builds the complete declared state interface.
It is an exact comparison oracle, not a claim about minimal model-only requantization cost.
Model-only baselines require their separate output contract.

The parent preserves all planned arms when setup, admission, evaluation, or a method fails.
Missing outcomes cannot disappear from the analysis denominator.
`isolated_analysis_plan` provides the frozen plan for the existing analysis code.
The cache and service-boundary labels distinguish this path from warm comparisons.

The campaign seals terminal success and failure records.
Resume verifies nested comparison, child, and worker receipts, including failed artifacts and budget debits.
It does not rerun a terminal failed campaign to replace inconvenient results.
Interrupted controllers retain their unfinished attempts and prior worker observations.
A sealed child without a sealed outer timing receipt still cannot become a cached fast success.

## CPU and timing scope

All setups, methods, and requested quality workers share one protocol-scoped phase ledger.
Research phases require explicit CPU-hour caps.
Software fixture defaults account for every planned worker across the inventory.
Each worker reserves before launch and settles observed usage under the existing budget contract.
Changing output directories does not reset that frozen protocol ledger.

The admission cap is not an absolute physical CPU ceiling.
Unknown attempts retain their allowance.
Observed overruns remain charged.
Controller CPU and hostile descendant containment remain outside this worker ledger.

Method timing retains the boundary documented in `ISOLATED_COMPARISON.md`.
It includes worker startup, inputs, one method, artifact writes, child commitment, exit, and cleanup.
It excludes parent verification and post-cleanup accounting receipts.
A separate transaction observer can measure its own larger declared boundary.
Operating-system caches remain uncontrolled.

## Optional quality worker

Passing `quality=True` to `build_isolated_plan` records `quality="heldout_nll"`.
That policy adds one dedicated process after all method outputs pass exact byte comparison.
The inventory binds the policy before execution.
The quality process receives the same source, target, protocol, limit, and budget checks.

It evaluates the base model, original quantized model, direct retained model, and repaired model.
Each saved state must match its expected record membership and content bindings.
The repaired and direct models must produce identical diagnostic results.
The worker persists NLL sums, token counts, and means.

These are local binary64 next-token NLL diagnostics.
They are not exact certificates or native framework equivalence claims.
They do not replace task evaluations, baseline quality gates, or real-model validation.
The quality worker's time and CPU are separate from every method clock.
Its failure makes the requested overall comparison unsuccessful.
Previously verified method outcomes remain visible.

## Interfaces

```python
build_isolated_campaign(
    campaign_id=...,
    protocol_path=...,
    worker_limits=...,
    plans=[{"plan_path": ..., "plan": ...}],
    workloads=...,
    sources=...,
)

run_isolated_campaign(inventory_path, output, validate_only=False)
```

```bash
python scripts/run_isolated_campaign.py inventory.json --output results
python scripts/run_isolated_campaign.py inventory.json --output results --validate-only
```

Validation does not load checkpoint parameters.
It does not prove feasible real-model execution or useful certificate acceptance.
No reliable speedup or publication readiness follows from these implementation checks.
