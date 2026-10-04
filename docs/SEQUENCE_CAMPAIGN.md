# Frozen sequence campaigns

Revision 8 adds source-bound bulk dispatch for local ordered deletion sequences.
It preserves the experiment pause and uses no model or dataset downloads.
Correctness fixtures establish implementation behavior only.

## Inventory and provenance

`build_sequence_campaign` creates `calibration-sequence-campaign-v1`.
Its inputs are a campaign ID, protocol path, frozen workloads, run specifications, worker limits, and source hashes.
Each run specification supplies its run ID, local manifest path, sequence manifest, and target digest.

The inventory embeds each complete workload.
It binds their joint canonical hash.
Each entry binds the root, configuration, sequence, repeat, phase, target, and method order.
It embeds the sequence manifest with only `protocol.sha256` cleared.
Every other manifest field remains bound.

Each sequence request must match its frozen workload row exactly.
The request provenance stores the source row hash and position.
The first request must start from the original state.
Every later request must name the preceding request as its starting state.
Its declared previous and cumulative deletion sets must agree with the ordered schedule.
Already removed IDs cannot reappear in later deletion sets.
Blocked source requests remain blocked.
The prepared calibration record order must equal the frozen root order.

The original workload score artifact remains independently prepared evidence.
This inventory binds its supplied hash and request rows.
It does not reconstruct scores or establish undocumented source provenance.
It does not treat artificial fixture hashes as empirical evidence.

A sequence ID keeps the same request membership across its repeats and configurations for the same root and phase.
Repeats form a complete zero-based prefix.
The method order uses the existing deterministic counterbalance rule with the sequence ID as its request domain.
That order applies to every step inside the sequence.
Do not describe the individual steps as independently sampled calibration roots.

## Removing the hash cycle

Use this order:

1. Construct frozen workloads and sequence manifests with unresolved protocol hashes.
2. Build and save the inventory as exact canonical JSON bytes.
3. Put its SHA256 in the protocol's `planned_inventory_sha256` field.
4. Save the final protocol.
5. Put the final protocol hash into every external sequence manifest.
6. Validate normalized manifests and final raw hashes before dispatch.

Changing any bound target, source, request, order, method, or path changes the inventory binding.
The executable source set includes the sequence implementation and dispatch scripts.
The controller checks the complete current source set.
Each child checks it again before and after sequence execution.
The child checks the actual constructed target digest before original feature preparation.

## Confirmation and pause guards

Research execution remains blocked while the protocol status contains `experiments_paused`.
Software correctness fixtures remain allowed.

Confirmation requires a frozen protocol with no blocked fields.
Its `sequence_confirmation` object explicitly lists:

- `configuration_ids`
- `root_ids`
- `sequence_ids`
- `timing_repeats`

The inventory must contain exactly their complete Cartesian product.
This requirement prevents silent omission of roots, sequences, configurations, or repeats.
The controller does not infer missing combinations from completed outcomes.
The declaration does not itself establish independent sampling or adequate statistical precision.

## Bounded execution

`run_sequence_campaign` starts one limited process for each complete sequence.
The process prepares one original canonical state.
Each subsequent request consumes the preceding committed repair state.
Every step independently compares all three methods with the complete retained fresh oracle.
The original normalization, ridge, grids, and feature target remain fixed.

The three methods within each step remain warm and share the sequence process.
Operating-system caches remain uncontrolled.
The execution label is `isolated_sequence_worker_warm_step_methods_os_cache_uncontrolled`.
This path does not provide independent method processes within each sequence step.

Empty and complete deletion controls remain supported under the fixed target.
A later empty request is valid after complete deletion.
Heldout records remain nonempty.
The sequence manifest defines the complete ordered schedule before execution.

The worker shares the protocol-hash `PhaseBudget` with other supported dispatch paths.
Each whole sequence requires one allowance before launch.
Budget denial creates a durable failed outcome without process launch.
Every planned sequence and every planned step remains visible.
Unknown reservations retain their full charge, and observed overruns remain charged.
This is trusted worker admission, not a global hardware CPU cap.
Controller CPU and arbitrary descendants remain outside that guarantee.

## Persistence and failed artifacts

Each campaign saves its complete inventory before dispatch.
A stable per-run request file binds the exact child command inputs.
Worker identity includes that request's hash.
Completed campaign resume verifies those stable request bytes.

Each sequence retains its initial state and every numbered step.
`verify_sequence_archive` checks every historical attempt's artifact hashes.
Those checks include failed and interrupted attempts.
Successful sequences also verify predecessor identities, fixed metadata, retained membership, and complete oracle artifact equality.
The campaign saves a snapshot of every sequence file except transient writer locks.
Resume rejects changes to that snapshot, including failed child files and newly inserted archive files.

Completed worker records remain immutable, including failures and budget denial.
A completed campaign does not rerun those workers automatically.
A new prospective inventory must identify deliberate repetitions.
A parent interrupted after a sealed worker reuses the original worker record and CPU debit.

A child can finish before its enclosing worker timing becomes durable.
The child refuses a cached completed sequence on a newly launched worker.
This recovery becomes failure instead of an artificially fast successful observation.
An incomplete sequence can resume its committed prefix when its enclosing attempt was not sealed.
Earlier attempt files and CPU reservations remain in the archive.
The worker elapsed value describes that attempt only.
The individual step timings preserve their own original observations.
Do not use a resumed attempt's elapsed time as the entire sequence's lifetime cost.

Top-level campaign `status="complete"` means the controller sealed all planned outcomes.
The `outcome` field and each run status determine scientific success.
Interrupted controllers preserve completed, attempted, and unstarted entries before returning an error.

## Interface

```python
inventory = build_sequence_campaign(
    campaign_id="planned-sequences",
    protocol_path="protocol.json",
    workloads=frozen_workloads,
    runs=sequence_run_specifications,
    worker_limits=limits.payload(),
    sources=source_hashes(repository),
)
```

```bash
python scripts/run_sequence_campaign.py sequence-inventory.json --output sequence-results --validate-only
```

Validation checks inventory, local token-manifest metadata, source hashes, protocol references, and available worker limits.
It does not load checkpoint tensors or execute feature evaluation.
Remove `--validate-only` only after the research pause and preparation gates are resolved.

## Measurement limits

The outer worker elapsed time is a resource diagnostic for a whole sequence attempt.
Step results retain `service_through_atomic_artifact_fsync` warm-arm timings.
Predecessor loading, sequence lineage writes, parent verification, and final controller commits remain separate costs.
Original preparation appears once in the sequence setup record.
The archive retains old states outside the live-state deletion guarantee.
No physical erasure or hostile-storage authentication claim follows.

This implementation does not provide real source pools, scores, partitions, or a final empirical inventory.
It does not establish language-model quality, useful acceptance, complete latency, lifetime savings, or reliable speedup.
Research experiments remain paused.

The supported execution phases now include feasibility.
It requires its own explicit CPU-hour cap and obeys the research pause.
Feasibility draws must come from the development-side pool.
They must not use confirmation or evaluation documents.
The phase label does not create or validate those missing real source pools.

Worker failure and sequence failure use separate diagnostic fields.
A nonzero process exit does not overwrite the underlying scientific failure record.
Saved preflight failures include their artifact hash and specific error when no sequence result exists.
