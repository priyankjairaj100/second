# Local experiment runner

The runner executes only local, hash-bound inputs.
It does not download models, data, tokenizers, or source code.
It does not execute checkpoint code.
Importing the runner does not start work.

Research experiments remain paused at this implementation checkpoint.
The tests use small software fixtures.
Their timings are not empirical paper evidence.

## Commands

Validate a prepared manifest:

```bash
python scripts/run_experiment.py run.json --output runs/request-001 --validate-only
```

Execute an authorized manifest:

```bash
python scripts/run_experiment.py run.json --output runs/request-001
```

Validation checks recipes, local configuration, checkpoint hashes, token records, and chart budgets.
It does not evaluate transformer features.
A rejected configuration plan stops before checkpoint parameters load.
A passing plan does not prove memory fit.
See `src/resource_preflight.py` for planning exclusions.

Only `warm_sequential_os_cache_uncontrolled` execution is implemented.
The caller fixes method order in the manifest.
The runner does not randomize order automatically.
Protocol generation must counterbalance order across repetitions.
Cold-process trials remain unimplemented.
A protocol marked `experiments_paused` blocks research execution.
Software fixtures remain allowed.
Confirmation requires `status="frozen_confirmation"` and an empty `blocked_fields` list.
It also requires a valid `planned_inventory_sha256`.
The external scheduler and analysis must check actual inventory membership.

## Run manifest

The schema is `calibration-run-v1`.
The runner rejects missing fields and unknown fields.

| Field | Required value |
| --- | --- |
| `root_id` | Independent calibration-root identifier |
| `request_id` | Deletion-request identifier |
| `configuration_id` | Fixed comparison-stratum identifier |
| `repeat_index` | Nonnegative integer |
| `phase` | `development`, `confirmation`, or `software_test` |
| `checkpoint` | Local path, exact file hashes, and parameter-element limit |
| `calibration` | Local JSON path and SHA256 |
| `heldout` | Local JSON path and SHA256 |
| `protocol` | Local protocol JSON path and SHA256 |
| `deleted_ids` | Unique calibration IDs; at least one record must remain |
| `target` | Complete `TargetRecipe.payload()` |
| `chart` | Complete `ChartRecipe.payload()` |
| `method_order` | Each supported method, exactly once |

Each JSON reference has `path` and `sha256` fields.
Relative paths use the run manifest directory.
The checkpoint object requires `path`, `files_sha256`, and `max_parameter_elements`.
Its hash map must equal the adapter's complete source-file map.
Use `TargetRecipe.payload()` and `ChartRecipe.payload()` to generate their fields.
See `docs/TARGET_CONTRACT.md` for those contracts.

The prepared record schema is `prepared-token-records-v1`.
Its fields are `schema`, `provenance`, and `records`.
Each record has `id` and `tokens`.
IDs must be unique within each manifest.
Token IDs must be integers within the model vocabulary.
Boolean token IDs are invalid.
Held-out records require at least two tokens.
All records must fit the model's position limit.

Provenance requires these nonempty strings:

- `dataset_id`
- `dataset_revision`
- `split`
- `license`
- `tokenizer_id`
- `tokenizer_revision`

Calibration and held-out IDs must differ.
Their complete token payloads must also differ.
These checks do not prove semantic independence.
The protocol must define sampling and partition rules.
The target's original token count must equal the calibration token total.

## Execution and comparisons

The runner first builds the original complete state.
It writes that state atomically.
It then loads the actual saved bytes through the validated state parser.

Every comparison uses the same original state and deletion request.

| Method | Measured operations |
| --- | --- |
| `repair` | Deleted lookup, complete repair, canonical serialization, and atomic output |
| `indexed_fresh` | Deleted lookup, index subtraction, indexed construction, serialization, and atomic output |
| `direct_fresh` | Retained selection, direct retained construction, serialization, and atomic output |

The indexed method receives the same retained summaries and source access.
It does not use the original model as a proposal.
Its split interface serializes and validates an intermediate index.
The integrated repair interface avoids that duplicate boundary.
Report this interface overhead explicitly.
It does not establish a deletion-specific algorithmic advantage.

Direct retained construction provides the correctness oracle.
Successful comparisons require complete canonical-state equality.
They also require equality of every quantized stage and the fixed target binding.
The model artifact contains every quantized stage and its fixed target binding.
It references the unchanged base checkpoint through that binding.
It is not a standalone pretrained checkpoint export.

The runner evaluates next-token loss on held-out records.
It evaluates the base model, original quantization, retained oracle, and repaired model.
It uses each record independently.
It does not score transitions between records.
The loss uses stable binary64 log-sum-exp with Python library math.
This metric is diagnostic, not an exact arithmetic certificate.

## Timing and memory

The method boundary is `service_through_atomic_artifact_fsync`.
Each method timer includes these operations:

- Source lookup from prepared, resident records.
- The complete service call.
- Canonical serialization and artifact hashing.
- Atomic artifact writes and directory synchronization.

The indexed method timer also includes index preparation.
Its `index_preparation_ns` field is nested inside that method timer.
Never add this field to the method total.

Checkpoint loading, source verification, and chart construction have separate preflight costs.
Original state preparation has a separate setup cost.
Equality checks and held-out evaluation have separate costs.
Final result serialization and commit occur after the reported overall timer.
The method clocks do not include that shared result commit.
The result states these boundaries explicitly.

`full_run_wall_ns_before_result_commit` starts before original state preparation.
`complete_pipeline_wall_ns_before_result_commit` also includes input loading and preflight.
These fields include experiment controls and quality checks.
They are not individual request-latency estimates.

The runner uses `perf_counter_ns` for elapsed time.
It uses `process_time_ns` for CPU time.
It measures Python allocation peaks with `tracemalloc`.
That instrumentation adds overhead.
Reported times describe the instrumented reference program.
They do not estimate optimized production latency.

RSS reports the process lifetime high-water mark.
It is not an independent per-method peak.
Python allocation peaks exclude objects created before their measured scope.
The runner reports serialized sizes and maximum serialized integer lengths.
It does not infer total memory from rational-entry counts.

All prepared payloads remain resident during comparisons.
Operating-system caches remain uncontrolled.
Garbage collection occurs outside each method boundary.
No timer claims to separate internal certificate and replay callback costs.
Stage ledgers provide operation counts, not subroutine elapsed times.

## Result schema

The result schema is `calibration-experiment-v1`.
It includes root, request, configuration, phase, and repetition identifiers.
`planned_methods` always includes all three methods.
Method failures remain in that denominator.
`method_order` records their actual execution order.

The result binds these identities:

- Run manifest hash.
- Protocol hash.
- Target manifest hash.
- Service job hash.
- Complete service hash.
- Chart hash.
- Source-file hashes.
- Input-record and request hash.

Each completed method reports `complete_wall_time_ns`.
It also reports canonical-state and model hashes.
Both exactness flags must be true before its status becomes `complete`.
Unchecked exactness flags are null.
A false flag means an observed mismatch.

Failure records include a stable kind and the failing exception type.
Examples include `evaluator_abort`, `memory_limit`, `timeout`, and `mismatch`.
A method that never starts remains `not_started`.
The runner records measured elapsed time when an attempted method fails.
External forced termination can prevent the latest timing record from committing.
The prior `running` record still identifies the attempted method.

Preflight failures use separate `calibration-preflight-failure-v1` records.
They never create a completed comparison result.
Their run-manifest hash identifies the planned request when input bytes exist.
Analysis must retain these failures alongside the frozen run inventory.
A missing comparison result must never disappear from that inventory.

## Atomic storage and restart

`RunStore` uses a persistent POSIX advisory lock.
Process exit releases the lock automatically.
The lock file can remain after a run.
Its presence alone does not indicate an active writer.
The implementation requires POSIX filesystem semantics.

Each attempt gets a new directory.
Artifact names cannot contain directory traversal.
The store rejects symlink paths and duplicate artifacts.
Artifact writes use a temporary file, atomic replacement, and synchronization.
A result becomes complete only after all checks succeed.

A restart verifies every artifact hash before accepting a completed result.
It also verifies the input and request binding.
A changed run identity causes rejection.
A completed result cannot be overwritten by another attempt.
An interrupted or failed request starts a new complete attempt.
The runner does not resume halfway through a model stage.
It preserves earlier attempts for audit.

The run directory is an external research archive.
It intentionally retains original states and failed attempts.
Those artifacts can contain influence from subsequently deleted calibration records.
The deletion guarantee applies only to the returned canonical live state.
It does not apply to the complete research archive.
Delete archive artifacts separately when the applicable storage policy requires it.

The store assumes trusted local storage.
Hashes detect changed artifacts but do not authenticate hostile storage.
Atomic logical commits do not establish physical memory erasure.

## Remaining infrastructure limits

The current runner handles one request per run manifest.
Repeated requests need separate manifests or direct service calls.
The confirmation scheduler must freeze and execute the planned inventory.
Process-cold execution and resource-limit enforcement remain separate work.
The runner does not implement task-level NLP benchmarks.
It implements next-token loss only.
It does not download or prepare real datasets.
It does not prove checkpoint equivalence to native Hugging Face execution.
