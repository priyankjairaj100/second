# Frozen measured request campaigns

Status: implementation and software-fixture validation only. Research experiments remain paused. No measured speedup, feasibility threshold, or real-model result follows from this dispatcher.

`src/measured_inventory.py` and `scripts/run_measured_campaign.py` bind a complete, prospective independent-request campaign to the per-method transaction engine in `src/measured_comparison.py`. The four timed methods are `model_only_fresh`, `repair`, `indexed_fresh`, and `direct_fresh`. Model-only fresh returns the retained quantized model without constructing a deletion index; it is the comparator for ordinary requantization speed. The other three return complete canonical deletion states. Direct fresh provides the full-state oracle. State equality is inapplicable to the model-only arm; exact target and model-code agreement still apply to all four.

## Freeze without a hash cycle

The canonical inventory schema is `calibration-measured-campaign-v1`. It contains the generic workload/membership declarations, every run's measured plan payload and digest, the actual four-method order, source digests, worker limits, and a runtime contract. Plans use `calibration-measured-plan-v1` and freeze target, service configuration through the bound manifest, quality selection, and clean/diagnostic instrumentation mode.

Build plans from manifests whose protocol reference exists. The normalized manifest payload clears **only** `protocol.sha256`; all other fields remain bound. Freeze the canonical inventory, put its exact digest in `protocol.planned_inventory_sha256`, then write that final protocol digest into every raw manifest. Dispatch verifies both the normalized binding and final raw protocol/manifest bytes. No manifest edit other than the final protocol digest is exempt.

`build_measured_campaign` creates the inventory without loading checkpoint parameters. `validate_measured_campaign_files(..., execute=False)` checks inventory, protocol, plans, membership, runtime, and local hash bindings without model preparation. It is not an empirical run. Actual parameter parsing and target construction still occur inside admitted leaves before use.

For confirmation, the protocol must be frozen, contain no blocked fields, and declare the configuration × calibration-root × request × repetition product. Missing or duplicated primary slots fail before dispatch. All confirmation primary plans require clean instrumentation. Feasibility and development require explicit CPU caps and obey the research pause. Creating or validating an inventory does not grant permission to resume research.

## Four-arm order and runtime identity

`measured_counterbalanced_orders` uses the frozen workload seed and root/request IDs to choose a permutation, rotates all four positions, and reverses orientation after each four-repeat block. Each complete block puts every method in every position exactly once. Partial blocks are prospectively specified but are not exactly position-balanced. Configurations share that root/request schedule. The legacy three-arm order inside the underlying run manifest remains input metadata; the measured plan's four-arm order controls actual measured execution.

A configuration/phase cannot silently mix target, chart, service family, verifier, quality, or instrumentation settings. The required runtime contract binds declared interpreter contents, selected standard-library components, binary64 representation, OS/kernel, and architecture. It omits account, hostname, environment secrets, and executable path. This is software/runtime identity, not proof of identical physical hardware, system load, caches, or native dependency closure.

## Admission and confirmation leaves

`verify_model_manifest` reads the actual inventory and validates membership, plan, exact raw manifest, target, sources, execution mode, and runtime. It supports either this independent-request inventory or the separate ordered measured-sequence schema; sequence authorization checks the derived cumulative manifest for the exact frozen step. A caller-supplied Boolean cannot authorize confirmation.

The model-only CLI accepts `--inventory`, `--inventory-run-id`, `--plan`, and `--execution-mode`; ordered execution additionally supplies `--sequence-step`. All research leaves require a live shared phase-budget reservation for their **exact literal command**, including these arguments. Standalone confirmation remains blocked. Both the model-only and canonical-state leaves verify membership before loading parameters and recheck bound inputs after work.

The shared durable ledger is scoped to protocol digest and canonical dispatcher source identity. Setup is separately admitted and charged; each of the four methods is admitted separately, and optional heldout quality adds another admitted worker. Unknown or interrupted debits remain conservatively reserved. This is cumulative admission/accounting for the trusted local worker processes, not an aggregate CPU containment guarantee for arbitrary descendant programs. See [EXECUTION_BUDGETS.md](EXECUTION_BUDGETS.md).

## Timing, outcomes, and restart

Every method uses a fresh bounded transaction process with the same outer observer contract. The complete measured boundary includes source/input validation, child startup and loading, work, child and controller commits, cleanup, and output validation; the observer's own final receipt is necessarily outside that boundary. Setup, optional quality, and external cross-method correctness verification are separately reported. OS caches are uncontrolled; these are not disk-cold measurements. See [TRANSACTION_TIMING.md](TRANSACTION_TIMING.md) for the literal boundary and exclusions.

Outputs are stored at `OUTPUT/runs/RUN_ID`; the campaign receipt is `OUTPUT/result.json`. Every planned run remains in the final receipt even if setup, a method, budget admission, or dispatcher validation fails. Missing/failed methods are not replaced with zero time or removed from denominators. Complete controller status means outcomes have been sealed; inspect the separate outcome and each method status for success.

A terminal campaign rechecks each nested run archive and sealed comparison receipt. Failed partial archives are hash-bound too, including their absence when no child directory existed. An added file, changed artifact, changed source/runtime/input, or replaced receipt invalidates resume. A resumed successful observer retains its original time; it cannot create another independent timing repetition. These receipts support audit and analysis, not proof that every arbitrary interruption point is automatically recoverable.

Example validation (local frozen paths only):

```bash
python scripts/run_measured_campaign.py /absolute/path/inventory.json --output /absolute/path/results --validate-only
```

Actual research dispatch remains blocked until the protocol, real weights and token pools, frozen configurations/inventory, precision conditions, resource allocations, and explicit resume instruction are satisfied. Existing v8 isolated and warm paths remain available under their own distinct output and timing contracts; this path does not relabel those observations as measured primary evidence.
