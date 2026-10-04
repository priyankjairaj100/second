# Exclusive complete-transaction attribution

The revision 9 diagnostic adapter measures and verifies components of an existing complete transaction. It does not estimate clean performance by subtracting profiling overhead. Research remains paused; the accompanying executions are software correctness fixtures only.

`src/diagnostic_breakdown.py` reads the original observer and child artifacts through the measured role verifier. It checks their source/input bindings and archive hashes, then produces an exact accounting identity:

\[
T_{\mathrm{observed}}=\sum_c T_c+T_{\mathrm{unclassified}}.
\]

The terms are disjoint measured wall durations. They are not CPU work, a critical-path model, or inferred algorithmic complexity. Waiting and scheduling can occur inside any wall span.

## Category map

| Report category | Measured source | Interpretation |
| --- | --- | --- |
| `loading` | Preflight `loading_measurement`, plus exclusive `persisted_state_reload` | Checkpoint/data/target loading and required saved-state parsing/validation |
| `chart_construction` | Preflight `chart_construction_measurement` | Chart and service construction; absent for model-only fresh |
| `extraction` | `extraction` | Intrinsic response/descriptor extraction |
| `proof_verification` | Both spectral and interval verifier wrappers | Entire certificate verification, including verifier-internal factorizations |
| `proof_bound_query` | `bound_query` | Query/construction of the retained aggregate enclosure |
| `retained_replay` | Response/cache retained feature evaluator spans | Actual retained feature reevaluation under the requested prefix |
| `fresh_features` | Response/cache/model-only fresh evaluator spans | Fresh target feature evaluation |
| `deleted_features` | Cache deleted-feature evaluator span | Deleted contribution evaluation for subtraction |
| `factorization_rounding` | Proposal/exact-target `factor_rounding`, cache equivalent | Candidate or exact quantization solve; excludes the separately timed certificate verifier |
| `gram_accumulation` | Exact Gram and combination helpers | Gram construction and combination |
| `metadata_validation` | Response/cache validation helpers | Membership, digest and state checks covered by those helpers |
| `serialization` | Canonical serialization and explicit commit encoding spans | Exact model/state encoding, including previously inactive output-path serialization |
| `durable_output` | Explicit artifact write spans | Artifact hashing, atomic file replacement, flush and directory sync through `RunStore.write_artifact` |
| `source_access` | Source reads and payload lookup/selection | Required source access and input lookup covered by the spans |
| `diagnostic_overhead` | Provider/certificate diagnostics and artifact size diagnostics | Bounded diagnostic collection and size scans |
| `feature_extraction_overhead` | Exclusive cache contribution wrapper | Feature validation/bookkeeping after nested evaluator and Gram work are removed |
| `service_overhead` | Exclusive operation root | Measured service work outside its nested named helpers |
| `artifact_commit_overhead` | Exclusive outer artifact-output span | Commit wrapper work outside serialization, durable output and diagnostics |
| `cleanup` | Worker cleanup plus observer adopted-descendant cleanup windows | Actual controller cleanup intervals, including normal no-descendant cleanup checks |
| Outer observer/worker phases | Original complete-clock partition | Observer pre/postflight, worker preparation, and worker finalization/commit |
| `unclassified_worker_execution` | Enclosing worker span minus verified child windows | Startup/imports, untimed leaf/control work, exit, waiting and scheduling remain unassigned |

These are operation boundaries, not an exhaustive explanation of every machine-level cause. A proof verifier may itself factor a matrix; its whole cost stays in `proof_verification`. Gram work nested within feature extraction is subtracted from the enclosing category before totals are reported.

## Why nested time is not counted twice

`ServiceTelemetry` already subtracts child spans from each parent. It now also records its top-level intervals. The adapter requires:

1. Every nanosecond field is a nonnegative built-in integer; every window's duration equals its end minus start.
2. Exclusive category durations sum to the collector's total and to its complete top-level window durations.
3. Collector, loading and chart windows are pairwise disjoint and lie inside the observed worker execution interval.
4. Recorded cleanup windows are disjoint, inside the observer interval, and do not overlap child execution or the ordinary cleanup interval.
5. All reassigned category durations plus remaining outer phases and the explicit residual sum exactly to the original complete wall time.

The clock contract is `time.perf_counter_ns_system_monotonic`, in the pinned supported CPython/Linux runtime. Custom test clocks are labeled `custom_unverified` and cannot provide artifact-level attribution. The adapter verifies cross-process containment using recorded coordinates; it does not add clocks from unrelated processes, machines or observations.

The top-level window list is bounded by the telemetry limits. If windows are omitted, the adapter leaves that service time unclassified rather than treating a partial list as complete. Unknown category names are reported explicitly as `unmapped_service_category`. The default exact work counters remain separate and are never converted into time estimates.

## Cleanup and compatibility

The worker adds `cleanup_start_ns` but keeps its original elapsed meaning: `cleanup_end_ns - start_ns`. The observer retains the original `timing_spans` unchanged for compatibility. Its additional `timing_detail_spans` splits only the old worker execution-plus-cleanup interval, and both partitions have the same exact total.

Older worker records without a cleanup-start coordinate keep their combined interval. Their cleanup attribution is unavailable. The adapter does not reconstruct an imaginary split. Observer adopted-descendant cleanup has its own actual windows, subtracted from the enclosing finalization or postflight phase before entering `cleanup`.

## Output and interpretation

```bash
python scripts/analyze_diagnostic_breakdown.py RESULTS --output breakdown.json
```

This command reads an existing measured comparison; it launches no worker or model. Each role retains the observer identity/attempt, target/source hashes and original receipt hashes. Failed or unstarted observations remain visible.

`decompose_records(observer, child)` is a pure arithmetic validator and returns `verified_artifacts=false`. Only `diagnostic_breakdown(row)` and `diagnostic_report(root)` check original artifacts and set that marker true. Archive consistency remains a trusted-local property, not hostile-store authentication.

`status="attributed"` means the available required instrumentation has been consistently decomposed. It does **not** mean all wall time has a named internal cause. `named_attribution_complete` is false whenever the explicit residual is nonzero, a component is unavailable, a category is unmapped, or the transaction failed. Clean or truncated diagnostic observations are partial. A zero category means no measured span in that observation; it does not prove that an operation is always free.

This implements the named loading/extraction/proof/replay/factorization/metadata/serialization/output/cleanup timers and their artifact-verified decomposition. Exhaustive attribution of every nanosecond remains open whenever the result reports a residual. Practical coverage, absolute cost, and speed require real diagnostic replicas and separate clean observations.

## Correctness checks

`tests/test_diagnostic_breakdown_v9.py` checks exact sum identities, retained residuals, overlap/escape rejection, boolean and malformed durations, bounded window omission, unknown category handling, clean-profile exclusion, legacy cleanup compatibility, and real tiny four-arm software artifacts. It checks that loading, serialization, durable output and cleanup have actual measured spans and that model-only fresh has no chart construction charge. These fixtures are not publication performance results.
