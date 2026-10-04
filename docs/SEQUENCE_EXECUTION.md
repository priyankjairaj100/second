# Ordered deletion execution

Revision 8 adds frozen bulk dispatch and an explicit feasibility phase.
Read `SEQUENCE_CAMPAIGN.md` for the current inventory and admission contract.
The remaining sections describe the standalone sequence interface introduced in revision 7.

`src/sequence_runner.py` implements incremental deletion over one fixed service target.
`run_sequence` prepares the original canonical state once.
Each later request consumes the preceding committed repair state.
It never reconstructs that original state between requests.

## Public API

```python
run_sequence(decoder, service, records, requests, heldout, output, metadata,
             method_order=METHODS, service_mode="certified")
```

Metadata requires `sequence_id`, `root_id`, `configuration_id`, `repeat_index`, and `phase`.
Each request contains `request_id` and `deleted_ids`.
Request IDs must be unique within the sequence.
Deletion IDs refer to the current live set.
An already removed record cannot be deleted again.
Empty requests are valid before and after complete deletion.
Heldout records remain nonempty.

`run_comparison` now accepts an optional canonical `initial_state` and `sequence_lineage`.
The default API preserves independent request behavior.
It validates live record identities and payload digests against the supplied state.
All three methods retain the existing `calibration-experiment-v1` result schema.

## Exact target and controls

The service object remains fixed throughout the sequence.
Its manifest binds the original normalization, grids, base weights, and evaluator.
No step replaces original normalization with the retained token count.

Each step executes repair, indexed fresh, and direct fresh.
Direct fresh uses the complete current retained set and the same fixed service target.
The runner checks every model byte and every canonical state byte against direct fresh.
It commits the repair state as the next predecessor only after all methods complete successfully.

Complete deletion has an empty retained calibration set.
The service evaluates its fixed ridge and grid decisions for zero data Gram contributions.
This is a valid fixed-target output.
It does not imply a trained model or erase the fixed base weights.

## Persistence and restart

The output directory contains `initial`, `step-0000`, and later numbered step directories.
Each directory uses the existing immutable-attempt `RunStore`.
The parent stores the complete ordered plan before model evaluation.
Each child identity binds the sequence digest, step index, request ID, predecessor state, and predecessor result.
Successful child results bind all saved artifact hashes.
The parent records all planned steps, including unstarted steps after failure.

Restart reuses the saved original state and completed prefix.
It verifies their artifact hashes and ordered predecessor bindings.
A failed step receives a new attempt directory.
Earlier failure records remain available.
Changing request order, membership, metadata, or service manifest changes the sequence identity and rejects reuse.
A completed parent also verifies every child completion before returning its saved result.

These checks assume the declared trusted local filesystem.
They do not authenticate hostile edits to all hashes and metadata together.
Research archives intentionally retain historical states and failed attempts.
The deletion guarantee applies to the returned canonical live state.

## Local manifests

`scripts/run_sequence.py` accepts `calibration-sequence-v1` manifests.
They use the standard checkpoint, target, chart, protocol, data, and method fields.
Replace `request_id` and `deleted_ids` with `sequence_id` and `requests`.
The loader preserves local file hashes, original normalization, resource planning, and experiment pause guards.
It never downloads models or data.

```bash
python scripts/run_sequence.py local-sequence.json --output local-results --validate-only
```

Validation checks the ordered deletion schedule without feature evaluation.
Research execution remains paused under the current protocol.
Campaign inventory integration must use the sequence dispatcher before enabling scheduled sequence studies.

## Measurement scope

Each comparison remains serial within one shared process.
Objects are warm, and operating-system caches remain uncontrolled.
The initial preparation cost appears once in the sequence setup record.
Step setup reports predecessor reload without original preparation.
Method clocks include service work, model serialization, artifact hashing, writes, and directory synchronization.
They exclude sequence lineage commit, final result commit, and independent equality and quality evaluation.
The sequence reports elapsed time before its final result commit.
These fields do not establish a complete external service latency or independent cold-method timings.

## Validation limits

Tests use tiny deterministic software fixtures.
They cover exact state and model equality, complete deletion, empty requests, middle-step failure, restart, and lineage tampering.
They do not measure real-model acceptance, throughput, statistical reliability, or research speedup.

## Comparison families and policies

The manifest optionally selects `service_family`: `response` or `identity_cache`.
The response family uses the declared chart and its response tier.
It also accepts `verifier_policy`: `spectral` or `spectral_or_interval`.
The chosen policy changes certificate planning without changing the mathematical quantization target.

The identity-cache family requires the `none` chart, linear schema label, default radius, and default precision.
It also requires the default verifier and service mode.
The loader creates no response provider for this family.
Its construction digest binds the target and identity-service manifest.
Its local preflight uses the conservative zero-rank resource plan.
The preview separately reports actual cache Gram slots and model code slots.

Every comparison result records the family, response tier, and verifier policy.
Nondefault labels enter the explicit input binding.
The default response labels preserve the previous independent-request input hash.
The service manifest still binds its declared state contract.

For sequence steps, the existing `original_quantized` quality key refers to the entering committed model.
The result identifies this role with `initial_model_role="preceding_committed_state"`.
Independent requests retain `initial_model_role="original_preparation"`.
This preserves the prior quality schema while making the model reference explicit.
