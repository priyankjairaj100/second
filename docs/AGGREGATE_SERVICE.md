# Compact aggregate repair service

`src/aggregate_response_service.py` implements complete fresh construction and deletion repair.
It preserves the sequential quantizer target V.
It uses the compact linear response construction.
It does not store full quadratic response matrices.

## Public interface

```python
service = AggregateRepairService(
    job,
    evaluator,
    intrinsic_moments,
    contracts,
    query,
    provider_id="fixed-proof-program-version",
    extractor_id="fixed-intrinsic-program-version",
)
original = service.fresh(records)
repaired = service.repair(original.state, deleted_records, retained_source)
```

The evaluator accepts `(record, stage, certified_prefix)`.
It returns exact rational feature values for the declared finite program.
The extractor accepts `(record, stage)`.
It returns `(LinearRecordMoments, RecordMoments)` or `None`.
The second component contains scalar moments for the error descriptor.
Each error descriptor has exactly one column.

The query accepts an `AggregateGroupContext`.
It returns an existing `ResponseQuery` or `UnknownBound`.
The context contains the new certified prefix and aggregate statistics.
It exposes no retained record sequence, source content, or individual descriptor.
The query must bind its result to `context.binding`.

Contracts can omit unsupported stages.
The service does not call the extractor for those stages.
A `None` result marks unavailable evidence for that record and stage.
Any unavailable evidence forces replay of that entire group.
Deleting the last unavailable record restores the group's eligibility for certification.

## Canonical state

The state stores these components:

| Component | Stored information |
| --- | --- |
| Model | Exact codes for every target stage |
| Record metadata | Record ID, content digest, group ID, contribution digests, availability flags |
| Group metadata | Retained IDs and a digest of their metadata |
| Group statistics | Constant Gram, linear responses, scalar tangent Gram, scalar error moments |

Each contribution digest binds both moment payloads.
The service discards individual moment payloads after aggregation.
Group indices use empty `records` tuples.
The empty tuples do not represent an empty calibration group.
They prevent arithmetic helpers from scanning individual record bindings.
The service validates source identity, descriptor columns, and bases before aggregation.

For fixed stage dimensions and occupied groups, the aggregate rational count is independent of record count.
For one stage and group, response storage uses `O(r d² + r²)` rational entries.
Error moments add `O(r²)` entries.
Record metadata uses `O(N L)` fixed-size bindings.
Group membership uses `O(N)` IDs.
Actual byte cost also depends on rational numerator and denominator lengths.

`stored_aggregate_rational_count` counts matrix slots only.
It excludes model coordinates, metadata, and integer bit lengths.
It is not a byte count.

The service has a separate canonical-state manifest.
This manifest binds the target, state schema, extractor identity, provider identity, bases, and chart radii.
Target prefixes still use `job.manifest_digest`.
`service.target_manifest_digest` returns that target identity.
`service.manifest_digest` returns the complete service identity.

## Transaction and replay

Deletion requires the original source content for each removed record.
The service checks its content digest.
It regenerates the intrinsic contribution under the fixed extractor.
It checks the regenerated contribution digest before subtraction.
A changed extractor result aborts the transaction.
This check also rejects changed availability markers.

The service subtracts exact rational contributions from group totals.
It removes empty groups and deleted metadata.
It builds the target model in dependency order.
Each proposal uses the new certified ancestor prefix.

The compact proposal adds the omitted tangent trace to its diagonal.
This shift makes the proposal Gram positive semidefinite.
The service preserves the asymmetric error bounds:

\[
-(\beta+\delta)I
\preceq S_* - S_{\rm proposal}
\preceq \delta I.
\]

The service applies normalization and ridge after summing group bounds.
It checks every rounding decision under the resulting relative enclosure.
If certification fails, it replays one retained group.
Unknown groups have priority.
Otherwise, the service selects the largest remaining absolute uncertainty.
This selection rule is a heuristic.
It has no minimum-work guarantee.

Replay replaces that group's proposal with its exact target Gram.
Replay removes that group's uncertainty.
It does not remove the exact Gram from the candidate.
Every failed iteration replays another group.
The final exact fallback therefore terminates for finite input and terminating feature evaluation.

The result contains the complete model and canonical retained state.
Proof traces and work counters remain separate.
Repeated deletions produce the same state bytes as fresh construction on the retained set.
Deletion order does not change those bytes.

## Costs and trusted boundaries

A proposal contracts one group's matrices without reading individual retained descriptors.
A successful proposal needs no retained source read.
The complete service still scans metadata.
These costs remain visible:

| Ledger event | Work described |
| --- | --- |
| `validated_record_entries` | Original record metadata validation |
| `validated_membership_entries` | Group membership validation |
| `metadata_validation_hash_bytes` | Bytes hashed during membership validation |
| `metadata_deletion_filter_entries` | Original metadata scanned for deletion |
| `metadata_membership_rebuild_entries` | Retained metadata used to rebuild groups |
| `metadata_membership_hash_bytes` | Bytes hashed for new membership bindings |
| `metadata_serialized_entries` | Retained record entries written to canonical state |
| `canonical_serialized_bytes` | Complete serialized state bytes |
| `proposal_aggregate_rational_entries` | Aggregate scalar slots supplied to contraction |
| `proposal_aggregate_digest_bytes` | Aggregate bytes hashed for proposal binding |
| `deleted_intrinsic_extractor_calls` | Calls that regenerate deleted contributions |
| `retained_source_record_reads` | Unique retained source records read during repair |
| `retained_replay_evaluator_calls` | Retained feature evaluations for exact replay |

The ledger counts engine events.
It does not measure callback internals, factorization operations, integer bit operations, or wall time.
Intrinsic extraction can contain expensive derivative and enclosure calculations.
Their complete cost belongs in performance measurements.

The service holds no persistent source cache.
The retained source cache exists only during one repair request.
The caller owns the external retained source.
The fixed extractor and query must not retain record content, jets, or individual matrix payloads.
Such hidden caches would invalidate the storage claim.
Fixed model and chart caches are allowed and must be measured separately.

The service trusts the declared feature evaluator and proof implementation.
It cannot establish an arbitrary callback's mathematical truth.
It also trusts committed state or an authenticated state store.
Contribution hashes detect mismatched regenerated values under standard collision assumptions.
Hashes alone do not authenticate hostile state replacements.
Logical omission does not securely erase Python objects or caller copies.

The direct fresh constructor supplies an independent exactness check.
It is not a lower bound for equally indexed fresh solvers.
Those solvers can use the same response statistics.
No complete-service speedup follows from fewer retained feature evaluations alone.

## Software verification

`tests/test_aggregate_response_service.py` contains twelve behavioral tests.
They cover changed first-stage codes and accepted repair without retained replay.
They check repeated, combined, and reordered deletion against complete fresh state bytes.
They check fixed aggregate storage as record count changes.
They verify that proposals expose no retained descriptor sequence.
They check selected replay, absent evidence, unsupported stages, and exact fallback.
They reject stale prefixes, bad source bytes, changed contribution digests, and malformed metadata.
They check asymmetric bounds and nonunit normalization.
They also check empty retained sets and immutable service configuration.

These are software correctness checks.
They are not a benchmark campaign or synthetic empirical dataset study.
Research experiments remain paused.
