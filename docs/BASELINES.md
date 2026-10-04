# State loading and equal-information baselines

Revision 6 retains durable state loading and the indexed fresh comparison.
It adds matched response controls and exclusive diagnostic timing.
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

The service supports four modes with one target and one canonical state definition.

| Mode | Proposal rule | Main limitation |
| --- | --- | --- |
| `certified` | Use the selected response provider and selected retained replay | Proof bounds can fail |
| `fixed_reference` | Keep the constant anchor Gram and bound the omitted tangent response | Bounds can be larger |
| `identity_only` | Permit fixed-reference proposals only when ancestors equal the constructor reference | This tests base-reference identity |
| `full_replay` | Skip response queries and certificates; evaluate every retained feature Gram | It provides no response saving |

The fixed-reference control retains finite error and derivative approximation terms.
It adds a triangle bound for the omitted tangent response.
It changes the proposal without changing stored statistics.
The identity-only control checks every transitive ancestor.
A missing reference mapping causes replay.
It does not compare ancestors with the previous quantized model.

All modes produce the same complete canonical state when required finite evaluations succeed.
The runner applies its selected `service_mode` to repair and indexed fresh.
Direct fresh remains the independent correctness oracle.
The default mode is `certified`.
Use separate configuration identifiers for different modes.
The analyzer rejects mode, chart, or service-manifest mixing within one configuration.
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

## Telemetry and process boundaries

Each service operation accepts an optional `telemetry=ServiceTelemetry()` argument.
The collector records exclusive timings, operation counts, and proof outcomes.
It subtracts child intervals from parent intervals.
Never add its diagnostic total to the enclosing method timer.
Telemetry does not alter the canonical model or state.
Instrumentation overhead remains part of recorded elapsed time.

The runner also times resident payload lookup and durable artifact output.
The method boundary ends after atomic artifacts and directory synchronization.
Final experiment-result commit and campaign bookkeeping remain outside each method timer.
Original preparation, checkpoint loading, and equality checks have separate costs.

Campaign execution starts one process per complete comparison.
The three methods remain warm within that process.
Operating-system caches remain uncontrolled.
This is not per-arm process-cold service timing.
The split indexed interface still adds validation and serialization work.
That interface difference cannot establish an algorithmic repair advantage.

## Scope

The service assumes fixed deterministic trusted callbacks.
State parsing does not prove those callbacks.
Numerical abstention causes replay.
Finite-evaluator failure aborts the call without a committed state.
Logical deletion does not erase caller copies or physical memory.

The implementation does not yet provide an original-model cache or its unchanged-ancestor baseline.
The base-reference identity-only control does not close that task.
A distinct full quadratic response solver also remains unimplemented.
Neither control labels nor software fixtures close the practical speed gate.
