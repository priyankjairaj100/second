# Local experiment runner

Updated 4 October 2026, revision 6.
The runner uses local inputs with verified hashes.
It downloads no models, data, tokenizers, or executable source.
It does not execute checkpoint code.
Importing its modules starts no work.

Research experiments remain paused.
Software fixtures test correctness and failure handling.
Their timings are not empirical paper evidence.

## Commands

Validate one prepared run:

```bash
python scripts/run_experiment.py run.json --output runs/request-001 --validate-only
```

Validate a frozen campaign without loading checkpoint tensors:

```bash
python scripts/run_campaign.py inventory.json --output runs/campaign-001 --validate-only
```

Execute an authorized campaign under its declared worker limits:

```bash
python scripts/run_campaign.py inventory.json --output runs/campaign-001
```

A protocol containing `experiments_paused` blocks research execution.
Software fixtures remain permitted.
The campaign never changes the protocol status.
The direct single-run command does not create the campaign's worker limits.

Single-run validation checks recipes, configuration, checkpoint hashes, token records, and proof-domain budgets.
It does not evaluate transformer features.
A rejected configuration plan stops before checkpoint parameter loading.
A passing plan does not prove memory fit.
See `src/resource_preflight.py` for exclusions.

Campaign validation checks inventory membership, executable source hashes, protocol hashes, manifest hashes, and available worker limits.
It reads no checkpoint tensors.
Passing campaign validation does not establish input feasibility or useful coverage.

## Run manifest

The schema is `calibration-run-v1`.
Unknown fields cause rejection.

| Field | Required value |
| --- | --- |
| `root_id` | Calibration-root identifier |
| `request_id` | Frozen deletion-request identifier |
| `configuration_id` | Fixed comparison configuration |
| `repeat_index` | Nonnegative integer |
| `phase` | `development`, `confirmation`, or `software_test` |
| `checkpoint` | Local path, complete file hashes, and parameter-element limit |
| `calibration` | Local prepared-record path and SHA256 |
| `heldout` | Local prepared-record path and SHA256 |
| `protocol` | Local protocol path and SHA256 |
| `deleted_ids` | Unique calibration IDs that leave at least one retained record |
| `target` | Complete `TargetRecipe.payload()` |
| `chart` | Complete `ChartRecipe.payload()` |
| `method_order` | All three comparison methods, exactly once |
| `service_mode` | Optional mode; default `certified` |

Supported modes are `certified`, `fixed_reference`, `identity_only`, and `full_replay`.
The selected mode applies to repair and indexed fresh.
Direct fresh remains unchanged.
See `docs/BASELINES.md` for each control's exact meaning.

JSON references contain `path` and `sha256`.
Relative paths use the run manifest directory.
Checkpoint references contain `path`, `files_sha256`, and `max_parameter_elements`.
Their hashes must equal the adapter's complete source-file map.
Use recipe APIs to produce complete target and chart fields.
The chart can select affine directions or the fixed `grid-box` domain.

## Prepared records and workloads

The record schema is `prepared-token-records-v1`.
Its fields are `schema`, `provenance`, and `records`.
Each record contains `id` and `tokens`.
IDs must be unique within each manifest.
Tokens must be integer vocabulary IDs.
Boolean tokens are invalid.
Held-out records require at least two tokens.
Every record must fit the position limit.

Provenance requires six nonempty strings:

- `dataset_id`
- `dataset_revision`
- `split`
- `license`
- `tokenizer_id`
- `tokenizer_revision`

Calibration and held-out IDs must differ.
Their complete token payloads must also differ.
These checks do not prove semantic independence.
The original token count must equal the calibration token total.
Deletion never repacks retained records.

`src/request_workload.py` builds reproducible roots and request selectors.
Original-state scores use verified original features and quantization decisions.
They never inspect repair outcomes.
Score preparation has separate measured costs.
Difficulty scores define a stress proxy, not guaranteed failure or latency.
The documented stream model defines uniform sampling claims.
Saved method orders balance positions across complete repetition blocks.

Phase validation checks document IDs, normalized text hashes, record IDs, and token-payload hashes.
Document withdrawal expands to every prepared record from the requested documents.
Source withdrawal requires complete documented source labels.
The helper does not establish those labels' semantic validity.
See `docs/WORKLOAD_CONTRACT.md` for score formulas, ordering rules, and open provenance gates.

## Frozen campaign inventory

`src/experiment_inventory.py` binds workloads, source hashes, limits, and run manifests.
Each entry names its root, request, configuration, phase, repetition, and method order.
Each entry binds its deletion membership and calibration source.
Executable source changes invalidate the campaign binding.

Manifest binding clears only `protocol.sha256`.
The protocol separately binds the exact canonical inventory hash.
Dispatch then checks the final raw protocol hash and each final run manifest.
This rule resolves the hash cycle without excluding scientific inputs.

Confirmation requires a frozen protocol and no blocked fields.
It also requires declared configurations, root count, request types, and repetitions.
The campaign validates their complete primary Cartesian product before dispatch.
Development can use declared smaller inventories.
Unsupported sequential requests and complete-deletion requests cannot enter executable inventories.

The analysis plan retains every planned run.
It preserves the selected service mode.
Missing runs remain in failure denominators.
The analyzer rejects differing modes, chart hashes, or service hashes within one configuration.
Unknown optional hashes do not remove missing planned runs.

## Execution and comparisons

The runner first builds the original complete state.
It writes that state atomically.
It reloads the actual saved bytes through the validated parser.
Each comparison starts from that same original state.

| Method | Included operations |
| --- | --- |
| `repair` | Deleted lookup, complete repair, canonical serialization, and durable artifact output |
| `indexed_fresh` | Deleted lookup, retained index preparation, indexed construction, serialization, and durable output |
| `direct_fresh` | Retained selection, direct retained construction, serialization, and durable output |

Indexed fresh receives the same valid retained summaries and source access.
It never reads the original quantized model as a proposal.
Repair and indexed fresh share the stage solver.
Their interface overhead cannot establish a deletion-specific algorithmic advantage.

Successful methods must match the direct oracle's complete canonical state.
They must also match every quantized stage and its target binding.
The model artifact references the unchanged checkpoint through that binding.
It is not a standalone pretrained checkpoint export.

The runner measures diagnostic next-token loss on held-out records.
It evaluates base, original quantization, retained direct, and repaired outputs.
It never scores transitions between records.
The metric uses stable binary64 log-sum-exp with Python library math.
The metric is not an exact arithmetic certificate.
Task-level NLP evaluation remains open.

## Timing and telemetry

The method boundary is `service_through_atomic_artifact_fsync`.
It includes resident payload lookup, service execution, serialization, hashing, atomic artifact writes, and directory synchronization.
Index preparation is already inside the indexed method timer.
Never add `index_preparation_ns` to that timer.

`ServiceTelemetry` records exclusive nested intervals.
It subtracts child intervals from each parent interval.
Repeated category names remain exclusive.
Categories cover extraction, source access, feature execution, Gram arithmetic, decisions, validation, serialization, and service overhead.
The runner adds payload lookup, saved-state reload, and artifact output spans.
Events record proof attempts, rejection reasons, unavailable groups, and replay.
Operation counts remain separate from elapsed time.

Telemetry is diagnostic instrumentation.
Its overhead remains inside recorded elapsed time.
Its total is contained within the applicable setup or method boundary.
Never add that total to its enclosing timer.
Any difference from the enclosing timer remains unclassified runner overhead.
It does not prove optimized production latency.

Checkpoint loading and proof-domain construction belong to preflight.
Original state preparation belongs to setup.
Independent equality checks and quality evaluation have separate timings.
The final experiment-result commit occurs after the reported overall run timer.
Campaign bookkeeping and its final commit also remain outside method timers.
These costs must remain visible in complete campaign or lifetime accounting.

`full_run_wall_ns_before_result_commit` begins before original preparation.
`complete_pipeline_wall_ns_before_result_commit` also includes preflight and input loading.
Both include experiment controls and quality checks.
Neither field is an individual method latency.

Elapsed time uses `perf_counter_ns`.
CPU time uses `process_time_ns`.
Python allocation peaks use `tracemalloc`.
RSS is the process lifetime high-water mark.
It is not an independent per-method peak.
Allocation peaks exclude objects created before their scope.
Rational-entry counts do not measure physical memory.

## Worker limits and cache conditions

`src/worker_control.py` launches each comparison without a shell.
The child applies CPU affinity and POSIX address-space, CPU, and file-size limits before execution.
The parent enforces wall time and terminates ordinary descendants in the worker's process group.
The controller verifies the child's applied-limit acknowledgment.
It checks the request digest, limits, affinity, thread environment, PID, and process group.

Address-space limits apply per process and concern virtual memory.
They are not physical-memory measurements.
CPU limits also apply per process.
They do not enforce cumulative phase budgets or total descendant CPU use.
Thread environment values request library behavior.
Affinity separately limits available CPUs.
The process group is not containment for hostile programs.

Each complete comparison starts in a separate process.
Methods within that comparison share warm objects.
Operating-system caches remain uncontrolled.
This is per-comparison isolation, not per-arm process-cold timing.
All prepared payloads remain resident during a comparison.
Garbage collection occurs outside each method timer.

## Results, failures, and restart

The comparison schema is `calibration-experiment-v1`.
It preserves all three planned methods and their observed order.
It binds the target, service, chart, protocol, executable sources, inputs, and deletion request.
Both exactness flags must become true before a method becomes complete.
Unchecked flags are null.
False flags record observed mismatches.

Failures retain explicit kinds, including evaluator abort, memory limit, timeout, and mismatch.
Attempted methods record elapsed time when exception handling can complete.
Forced termination can prevent the latest method record from committing.
The worker controller still records the terminal outcome.
Preflight failures remain separate records tied to the run manifest.
Missing results stay in the frozen inventory.

`RunStore` uses a POSIX advisory writer lock.
Process exit releases that lock.
Each attempt has a separate directory.
Artifact writes use temporary files, atomic replacement, and synchronization.
Completed comparisons cannot be overwritten.
Restart verifies every referenced artifact and the input binding.

Direct single-run restart can create a new attempt after a failed comparison.
Campaign worker outcomes are terminal, including failures.
A campaign resume reuses each sealed worker outcome instead of silently rerunning failures.
It verifies failed-worker artifacts as well as successful comparison artifacts.
A controller record marked complete means its outcome is sealed.
Inspect `outcome.status` or the campaign outcome to determine scientific success.

The research archive intentionally preserves original states and previous attempts.
Only the returned canonical live state has the deletion guarantee.
The guarantee does not cover archive contents or physical memory erasure.
Hashes detect changes under trusted storage.
They do not authenticate hostile storage.

## Open implementation gates

Real checkpoint feasibility and useful proof coverage remain unmeasured.
Source acquisition, tokenizer validation, and concrete record manifests remain open.
Repeated deletion execution and complete-deletion campaign controls remain open.
Per-arm cold timing and cumulative phase budgets remain open.
An original-model cache and a distinct quadratic response solver remain open.
No reliable full-model speedup follows from this infrastructure.
