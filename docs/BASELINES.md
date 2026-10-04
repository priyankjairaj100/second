# State loading and equal-information baselines

Revision 5 adds durable state loading and an indexed fresh comparison.
These changes do not establish practical speedup.

## Canonical state loading

Save the bytes returned by `state.canonical_bytes()`.
Save their digest in a trusted record.
Reload them with the same declared service.

```python
from src.aggregate_response_service import StateParseLimits

state = service.load_state(
    payload,
    expected_digest=trusted_digest,
    limits=StateParseLimits(max_bytes=64 * 1024 * 1024),
)
```

The parser rejects duplicate keys, duplicate identifiers, unknown fields, floats, and noncanonical rational values.
It accepts UTF-8 identifiers and requires canonical output bytes.
It limits bytes, dimensions, records, groups, stages, terms, rational counts, integer digits, text lengths, and nesting.
Limits apply before expensive matrix validation where possible.
Callers must set limits for their supported workload.

The service checks its manifest, stage order, matrix shapes, grids, contracts, group membership, and contribution metadata.
It also checks nonnegative error moments and positive semidefinite norm matrices.
These checks detect invalid structure.
They cannot reconstruct aggregate provenance without original contributions.
Valid arithmetic changes can pass structural checks.
Use trusted state storage or a trusted expected digest.
An expected digest supplied by the same untrusted source provides no authentication.

`AggregateState.from_canonical_bytes` performs bounded syntax parsing without service validation.
Use `service.load_state` before using loaded state.
Reloading keeps no source payloads or individual moment matrices.
A software test saves state and reloads it in a fresh Python process.
That process deletes a record and writes the repaired state.
Its bytes match independent retained fresh construction in the parent process.
The test sets a 30-second process limit.
This check uses the exact affine software fixture.
It does not establish real-checkpoint compatibility or process recovery after an interrupted write.

## Baseline interfaces

```python
prepared = service.prepare_index(old_state, deleted_records)
indexed = service.indexed_fresh(prepared.index, retained_source)
replayed = service.indexed_fresh(
    prepared.index, retained_source, mode="full_replay"
)
repaired = service.repair(old_state, deleted_records, retained_source)
```

`prepare_index` validates retained metadata and regenerates deleted contributions.
It verifies contribution digests before exact subtraction.
It returns an `AggregateIndex` with records, groups, and the service manifest.
The index has canonical bytes and a digest.
It contains no model proposal.
Its ledger records deletion and index preparation work.

`indexed_fresh` validates the retained index and constructs every quantized stage.
It generates each stage prefix from newly constructed outputs.
It never reads an old model proposal.
It accepts an `AggregateState` for convenience but ignores that object's model.
It still validates retained summaries and metadata.

The default mode uses response certificates and selected replay.
The `full_replay` mode skips response queries and all response certificates.
It computes every retained feature Gram under each new prefix.
Both modes produce the same complete canonical state when finite evaluation succeeds.
Each call keeps a temporary replay cache.
No cache survives the call.

## Comparison meaning

Repair and indexed fresh share one stage planner.
Both use retained summaries, base weights, fixed contracts, and newly constructed prefixes.
Repair currently provides no separate advantage from the old model.
Therefore, indexed fresh is an equal-information comparison using the same algorithm.
It is not a strong independent competing algorithm.
Equal results or equal solver costs are expected.
Do not report a deletion-specific speedup against this comparison without an additional distinct mechanism.

The direct `fresh` path remains the independent correctness oracle.
It extracts summaries and evaluates all retained target features independently.
Its total includes rebuilding summaries.
That total is not an equally indexed timing baseline.

| Route | Input state | Online work |
| --- | --- | --- |
| Repair | Original state and deleted inputs | Validate, subtract, solve, serialize |
| Indexed fresh | Original state and deleted inputs | Prepare retained index, validate index, solve, serialize |
| Indexed full replay | Original state and deleted inputs | Prepare retained index, validate index, replay, serialize |
| Direct fresh | Retained inputs | Extract summaries, evaluate target, solve, serialize |

Charge `prepare_index` once for each complete indexed request.
Do not add its ledger to `repair`; repair already performs deletion.
Report solver-only timings separately from complete request timings.
The split interface also validates and serializes an intermediate index.
Report that interface overhead explicitly.
It is not an algorithmic repair advantage.

Index loading, checkpoint loading, output writing, durable commits, and original preparation remain additional measured costs.
Use the same initial files and cache conditions for each comparison.
Software checks establish equality and transaction behavior.
They do not measure real-model coverage or latency.

## Scope

The service assumes fixed deterministic trusted callbacks.
State parsing does not prove those callbacks.
Numerical abstention causes replay.
Finite-evaluator failure aborts the call without a committed state.
Logical deletion does not erase caller copies or physical memory.

The implementation does not yet provide unchanged-ancestor caching as a separate baseline.
It also does not provide a distinct full quadratic response solver.
Those comparisons remain separate tasks.
