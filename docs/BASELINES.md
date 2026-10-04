# State loading and equal-information baselines

Revision 7 adds full quadratic response, original-model caching, and optional interval verification.
It retains durable state loading, matched controls, and equal-information comparisons.
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
Within the response family, it never reads an old model proposal.
It accepts an `AggregateState` for convenience but ignores that object's model.
It still validates retained summaries and metadata.

The response family supports four modes within each selected storage tier.
Every mode preserves that tier's canonical state definition and the same complete target.

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
Within the response family, both use retained summaries, base weights, fixed contracts, and newly constructed prefixes.
Response-family repair currently provides no separate advantage from the old model.
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

## Response storage tiers

`response_tier="linear"` remains the default aggregate service tier.
`response_tier="quadratic"` stores the full affine-response Gram polynomial.
The latter includes oriented cross matrices and every tangent Gram term.
It uses the same intrinsic finite-error descriptors.
It changes the proposal and storage, not the quantization target.
It is not a renamed compact proposal.

| Tier | Response slots per group | Additional error slots |
| --- | ---: | ---: |
| Linear | `(r+1)d²+r²` | `(r+3)(r+4)/2` |
| Quadratic | `(r+1)(r+2)d²/2` | `(r+3)(r+4)/2` |

The state manifest and schema bind the selected tier.
The parser rejects incompatible tiers.
A nonzero-rank compact state generally cannot recover missing quadratic moments.
An upgrade requires re-extraction or separately retained full moments.
Both tiers support empty, repeated, reordered, and complete deletion.
See `docs/QUADRATIC_CONTROL.md` for extraction, contraction, and serialization costs.

## Certificate portfolio

`verifier_policy="spectral_or_interval"` adds an optional second verifier.
The default policy remains `spectral`.
The service preserves every spectral acceptance before attempting the interval route.
The interval route checks all proposed rounding cells under signed covariance bounds and the fixed ridge floor.
It can operate when the relative spectral lower scale is nonpositive.
It charges extra candidate factorization when no candidate already exists.
Rejection resumes retained replay.

The policy stays outside canonical state because it changes only execution planning.
Run input and result bindings record it separately.
The portfolio may avoid replay but add more total work.
It gives no runtime dominance or real-model acceptance claim.

## Original quantized-model cache

`IdentityCacheService` provides the distinct original-model identity baseline.
Its runner adapter selects `service_family="identity_cache"`.
The cache stores true stage Grams under the current quantized model and binds every relevant ancestor prefix.
It keeps no per-record feature matrices or source payloads.

At each stage, it compares all transitive ancestors with the entering cached model.
Equal ancestors permit exact subtraction using only deleted features.
Changed ancestors require retained replay under the new prefix.
The service then stores refreshed true Grams under the new model.
Repeated deletion therefore uses the current cache rather than stale original statistics.

The cache stores `sum_l d_l²` Gram slots, plus model, metadata, prefixes, and rational integer storage.
Its canonical schema is `original-model-gram-cache-v1`.
It does not share canonical bytes with either response tier.
Cross-family comparisons check complete model equality under the same target.
Within-family comparisons additionally check complete canonical state equality.

The cache's equally indexed comparator receives the same old model, cache, deleted inputs, and retained source.
It executes the same solver as repair.
Its transient prepared object includes the original cache and deleted source payloads.
It is not a retained-only committed index.
The split interface's extra validation cannot establish an algorithmic advantage.

The core supports `certified`, `identity_only`, and `full_replay`.
The first two names select the same original-model identity algorithm.
The manifest loader currently allows this family only with default mode and verifier labels.
It also requires the `none` chart and default linear label, radius, and precision.
Those shared labels do not activate response extraction or spectral certification.
Read `docs/IDENTITY_CACHE.md` for trusted digest requirements and complete cost accounting.

## Ordered requests and complete deletion

The sequence runner prepares the original state once.
Each successful request commits the next entering state.
Every step checks all stage outputs and its family's canonical state against retained direct construction.
Its request and predecessor hashes bind the order.
A failure preserves unstarted planned steps and the earlier committed prefix.

An empty retained corpus remains a defined ridge-only target.
No record can be deleted twice from the live set.
Empty requests remain valid after complete deletion.
Archival predecessors remain outside the returned live-state deletion guarantee.
See `docs/SEQUENCE_EXECUTION.md` for the local dispatcher and restart contract.

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

Revision 7 implements both the original-model cache and the full quadratic response tier.
Their correctness fixtures establish target preservation within their declared state families.
The stronger whitened quadratic acceptance theorem remains unimplemented.
Neither control labels nor software fixtures close the practical speed gate.
