# Executable reference service

This code implements target V with explicit numerical contracts.
It prioritizes inspectable correctness.
It does not provide fast quantization for large checkpoints.
Exact rational values can require large numerators and denominators.
Event counters and software tests do not measure latency.

## Modules

| Module | Responsibility | Explicit boundary |
| --- | --- | --- |
| `src/exact_core.py` | Exact factorization, rounding, and shape checks | The caller establishes the spectral premise |
| `src/sparse_repair.py` | Code-change injection and exact coordinate fallback | The target factor must be known |
| `src/response_moments.py` | Quadratic response totals and exact deletion | The extractor must be fixed and sound |
| `src/response_certificate.py` | Error contraction and rational Gram bounds | Descriptors must cover the actual finite evaluator |
| `src/linear_response.py` | Compact response totals and omitted-PSD bounds | It does not prove neural derivatives |
| `src/repair_service.py` | Original complete service with reference descriptors | Its callbacks have explicit trusted contracts |
| `src/response_service_adapter.py` | Original response bridge through individual descriptors | Proposal construction scans retained descriptors |
| `src/aggregate_response_service.py` | Compact grouped state and complete exact repair | It trusts the fixed extractor and query theorem |
| `src/transformer_backend.py` | Original deterministic scalar decoder | Its built-in proof establishes input identity only |
| `src/certified_intervals.py` | Rational intervals and certified scalar primitives | Resource limits can reject unsupported calculations |
| `src/certified_transformer.py` | Explicit decoder with automatic response bounds | Certification requires a supported parameter chart |
| `src/checkpoint_adapter.py` | Local GPT-2 parameter import | It does not reproduce external floating kernels |
| `src/work_scheduler.py` | Cooperative scheduling of two exact branches | Packet and cleanup costs require separate accounting |

The original response adapter remains a useful correctness reference.
It stores individual response payloads inside canonical descriptors.
It scans those payloads when it constructs group totals.
This historical path has `O(N)` descriptor reads.
Its response matrices can require `O(N r² d²)` entries.

The aggregate service replaces that storage layout.
It stores response matrices only at group level.
Its proposal contracts group totals without scanning individual descriptors.
Read `docs/AGGREGATE_SERVICE.md` for the complete interface and ledger.

## Original decoder usage

Construct `DecoderConfig` and `DeterministicDecoder` from explicit weights.
Then call `make_repair_service` with fixed grids, ridge, normalization, and group count.
Provide token IDs through `Record(id, decoder.record_payload(tokens))`.
The normalization and grids stay fixed across deletion.
The example downloads no tokenizer or checkpoint.

```python
service = decoder.make_repair_service(
    grids_by_stage=fixed_grids_by_stage,
    ridge=1,
    normalization=original_token_normalization,
    group_count=4,
)
initial = service.fresh(records)
removed = (records[0],)
retained_by_id = {r.record_id: r for r in records[1:]}
repaired = service.repair(initial.state, removed, retained_by_id.__getitem__)
fresh_retained = service.fresh(records[1:])
assert repaired.state.canonical_bytes() == fresh_retained.state.canonical_bytes()
installed = {stage.stage_id: stage.codes for stage in repaired.state.model}
logits = decoder.logits(evaluation_token_ids, installed)
```

`tests/test_transformer_backend.py` gives the complete original constructor.
The backend manifest binds frozen model configuration.
The output contains the quantized stages promised by the job.

## Compact aggregate usage

```python
service = AggregateRepairService(
    job,
    target_evaluator,
    intrinsic_moments,
    stage_contracts,
    response_query,
    provider_id="fixed-proof-version",
    extractor_id="fixed-extractor-version",
)
initial = service.fresh(records)
repaired = service.repair(initial.state, deleted_records, retained_source)
```

The intrinsic extractor returns compact response moments and scalar error moments.
It can return `None` when it cannot establish the required evidence.
The query receives aggregate totals and the new certified prefix.
It receives no individual retained descriptor or source payload.
It returns a bound query or `UnknownBound`.
Missing evidence causes exact replay of the affected group.

The automatic provider supplies concrete hooks for its supported decoder and chart.
The generic service still permits other explicitly trusted hooks.
A callback's declared identity does not prove its mathematics.

## Complete logical state

The original service returns `CanonicalState` with reference descriptors.
The aggregate service returns a distinct `AggregateState`.
Both states include the complete target model.
They do not have interchangeable schemas.

Aggregate state stores record IDs, content digests, group IDs, contribution digests, and availability flags.
It stores constant Grams, linear responses, tangent Grams, and error moments at group level.
It stores no individual matrix payload, response jet, or source content.
Its group membership lists contain retained IDs only.

With fixed occupied groups, matrix storage does not grow with record count.
For each stage and group, it uses `O(r d² + r²)` rational entries.
Record metadata uses `O(N L)` bindings.
Group membership uses `O(N)` IDs.
Byte cost also depends on integer bit lengths.

Deletion checks supplied source content against its committed digest.
It regenerates intrinsic moments for deleted records only.
It checks each contribution digest before exact subtraction.
It rejects a changed extractor result or availability marker.
No individual retained moment must be reconstructed for proposal construction.

Each stage uses the new certified ancestor prefix.
Each proposal binds the target, stage, prefix, group membership, and aggregate statistics.
The service preserves signed uncertainty during selected replay.
Replay replaces a proposal with the exact target Gram.
A finite sequence of replay steps reaches exact fallback.

Successful repair returns the same canonical bytes as fresh retained construction.
Repeated deletion has the same logical-state guarantee.
Deletion order does not change those bytes.
The service keeps transient proof traces outside committed state.
It does not keep persistent source or individual-moment caches.
Fixed callbacks must also avoid hidden record caches.

Input state remains immutable after success or failure.
This is a guarantee about committed logical state.
It does not securely erase caller-held objects, storage snapshots, or process memory.
The service assumes trusted construction or authenticated state storage.
SHA-256 checks bind content under collision assumptions.
Hashes alone do not authenticate hostile state replacements.

## Numerical target

Oracle V treats finite neural outputs as exact dyadic numbers.
It uses exact Grams and rational rounding decisions.
The original decoder pins its scalar binary64 program and runtime.
Its built-in shortcut proves unchanged finite inputs.
Other prefixes cause replay unless another sound provider supplies evidence.

The certified decoder defines a separate finite program with certified primitives.
It does not assume that host transcendental functions have correct rounding.
Its response provider checks the supported chart and numerical domain.
Unsupported prefixes or failed enclosures cause replay.
This scope does not cover arbitrary PyTorch, CUDA, or GPTQ kernels.

A checkpoint adapter maps architecture and parameter values into the declared decoder.
Parameter compatibility does not establish equality with the source framework's floating outputs.
Oracle E remains a distinct floating Gram and factorization program.
No V certificate establishes equality with E automatically.

## Work and fairness

The aggregate proposal avoids an individual descriptor scan.
The complete service still validates and rebuilds `O(N L)` metadata.
It also serializes the complete retained state.
Those costs have separate ledger events.
No sublinear complete-service claim follows from compact proposals.

Engine counters describe service events.
They do not measure callback internals, rational bit operations, or elapsed time.
Full comparisons must include setup, extraction, validation, replay, factorization, output, serialization, and cleanup.
The scheduler does not automatically preempt this service or GPU kernels.

Both direct fresh construction and equally indexed fresh construction remain required comparisons.
An equally indexed fresh solver can use these response summaries.
Report storage, preparation, deleted-side regeneration, all fallbacks, and lifetime costs.
Software correctness checks do not establish practical speedup.
Research experiments remain paused.
