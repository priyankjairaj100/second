# Transient rational endpoint diagnostics

Revision 8 adds an optional diagnostic wrapper around the existing local runners.
It does not replace arithmetic, alter quantization targets, or resume research experiments.
It runs the original manifest loader and its existing pause, source, and resource checks.

## Observed quantities

`ArithmeticAudit` observes successful returns from the standard `Fraction` allocation methods.
This Python version uses both `Fraction.__new__` and `Fraction._from_coprime_ints`.
Ordinary rational arithmetic often bypasses `__new__` through the second allocator.
The audit observes both sites and counts each successful allocation once.
Its runtime record binds the Python version, allocator names, and standard-library Fraction source hash.

For every observed rational object, the audit records:

- Numerator and denominator bit lengths.
- Maximum observed numerator and denominator bit lengths.
- Sums of endpoint bit lengths across constructed objects.
- Construction counts and zero-numerator counts.
- Bounded phase and nearest project-caller summaries.

The bit-length sums describe cumulative constructed endpoints.
They do not describe simultaneously live data or resident memory.
The audit never stores a constructed Fraction, its numerator, its denominator, or a callback frame.
It stores only scalar counts, bit lengths, and bounded textual attribution.
Large exact values therefore do not expand the diagnostic JSON into their decimal representations.

The allocation observer includes checkpoint conversion, target/domain factories, finite/proof features, Grams, factors, verification, and serialization-related rational construction.
Actual local target construction starts inside the profile scope.
Classifications use source-frame attribution and can remain unclassified.
They are diagnostic labels rather than exclusive scientific cost phases.
The aggregate stream covers the entire runner, including preparation, verification, and quality work when that runner executes them.

Each attribution map permits a fixed number of distinct labels plus one explicit overflow bucket.
Overflow retains all counts and maxima.
It loses attribution detail without losing aggregate endpoint counts.
The observer does not retain an unbounded call history.

## Initial values

The initial snapshot separately scans GC-visible live Fraction objects before profiling starts.
It records counts and endpoint sizes without retaining object references afterward.
Its configured scan cap and truncation flag appear in the report.
Values present before profiling are not added to construction counts.

The snapshot covers only GC-visible objects reached within that scan.
It does not enumerate every Python, native, or memory-mapped source value.
For the command wrapper, real checkpoint and target factories run after profiling begins.
Their newly constructed rational values enter the construction stream.
Already imported global rational constants remain in the separate initial snapshot when visible.

## Memory observations

The audit observes the runner's existing `tracemalloc.start` and `tracemalloc.stop` scopes.
It samples current and peak traced allocations immediately before tracing stops.
It also samples memory after tracing starts, periodically during construction, and at scope boundaries.
It never starts or stops an external allocation trace itself.
This preserves the runner's prohibition on nested allocation measurements.

Missing traced-memory observations are `null`, not zero.
The report states whether tracing was active at entry and exit.
Peak traced bytes include profiler overhead and other allocations in the same process.
They are not rational-only memory.

Current RSS comes from `/proc/self/statm` when available.
Unavailable current RSS includes an explicit reason.
The process lifetime high-water mark comes from `getrusage`.
That peak can include work completed before the audit started.
The maximum sampled current RSS can miss short peaks between samples.
Neither statistic allocates resident memory to weights, domains, jets, metadata, or rational values individually.

The wrapper inventories serialized files under its fresh runner output directory.
It records bounded file paths, byte sizes, total listed bytes, truncation, and skipped symlinks.
These are output-artifact measurements, not resident-memory estimates.
The diagnostic sidecar lives outside the immutable runner output directory.

## Scope and unobserved work

The profiler covers the calling thread in the current process.
It does not automatically propagate into child processes or other threads.
Detected child or thread launches mark whole-run coverage ineligible.
Existing extra threads, observer failures, or replacement of the profiler also make the audit incomplete.
The report always declares the current-thread/current-process scope.

The CLI accepts only the direct experiment and ordered-sequence runners.
It rejects isolated and campaign controllers because their child computations would escape the observer.
Those child processes need a separately bound audit entrypoint before whole-campaign arithmetic coverage is claimed.

The observer measures constructed Fraction endpoints.
It does not measure every integer temporary used to construct those endpoints.
For example, cross-products and greatest-common-divisor inputs may exceed the final reduced numerator and denominator.
It also cannot see unexposed native arithmetic, C-extension allocator bypasses, or every Python integer expression intermediate.
Object frees and precise lifetimes remain unobserved.
No maximum-live-rational-memory theorem follows from these diagnostics.

## Running the diagnostic

```bash
python scripts/run_arithmetic_audit.py experiment local-run.json \
  --output diagnostic-run \
  --audit-output arithmetic-audit.json

python scripts/run_arithmetic_audit.py sequence local-sequence.json \
  --output diagnostic-sequence \
  --audit-output sequence-arithmetic-audit.json
```

The output directory must be absent or empty.
Completed or partial runs cannot be reused through this wrapper.
That rule prevents cached completion from appearing as zero arithmetic work.
The sidecar path must be new and outside the runner output directory.

`--validate-only` preserves the runner's validation-only behavior.
Such an audit measures validation, not model execution.
`--sample-every` controls periodic memory observations.
It does not subsample Fraction construction counts.
`--max-attributions` bounds detailed phase and caller groups.

The report binds the input manifest hash and audit source hash.
It rechecks those files after execution and marks changed or missing sources as incomplete coverage.
It retains declared quantization, chart precision, and protocol references.
It also copies target, service, policy, protocol, and execution identities from runner output when available.
The original runner artifacts remain immutable.
The wrapper creates only its separate diagnostic report.

`ArithmeticAudit` is also a single-use context manager for software checks.
`audit.phase(name)` provides an optional explicit attribution label.
Existing profilers and nested audits are rejected without replacing them.
On normal or exceptional exit, the audit restores the previous profiling setting.
Ordinary evaluator exceptions retain their original type and propagate through the wrapper.
When possible, the wrapper writes a failed diagnostic receipt before propagating that exception.

## Interpretation and D05

Every profiled timing is diagnostic.
This includes timings emitted by the underlying runner while the profiler is active.
The runner embeds `profiler_active=true` in its comparison and measured method records.
Profiled execution also changes the explicit run input binding.
The standard analyzer excludes these observations from clean timing ratios even if the sidecar is unavailable.
Their verified numerical outputs remain valid correctness evidence.
Do not insert these runs into the clean-latency confirmatory inventory.
Use separate diagnostic paths and retain the sidecar with every reported arithmetic observation.
Profiler overhead can change memory, timing, and resource-limit outcomes substantially.

Successful software validation closes the endpoint-instrumentation implementation gap.
It does not produce real-model D05 measurements while research experiments remain paused.
D05 can be marked complete only at an explicitly stated diagnostic implementation scope.
If D05 requires measured real-model memory, that empirical requirement remains open.
The original requirement cannot be strengthened into hidden-intermediate or exact live-memory coverage without another instrument.

`tests/test_arithmetic_audit_v8.py` verifies both allocators, exact output preservation, exception cleanup, bounds, and unavailable-memory semantics.
It checks initial-value separation, existing profilers, threads, child processes, and incomplete diagnostic coverage.
It compares every method's model and state hashes with an unprofiled standard-runner software fixture.
These tests are correctness evidence only.
They are not language-model experiments, useful-memory measurements, or speed evidence.
