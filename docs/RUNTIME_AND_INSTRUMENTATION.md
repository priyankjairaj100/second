# Runtime binding and optional instrumentation

Revision 9 separates primary timing from numerical diagnostics.
These changes establish execution contracts and correctness checks.
They do not establish empirical speed or model feasibility.

## Runtime identity

`src/runtime_contract.py` captures the declared reference runtime.
It binds the CPython version, interpreter bytes, selected standard-library bytes, and binary64 representation.
It also records Linux, kernel, architecture, compiler, build, and libc version.
Selected Python flags, recursion limits, and integer-string limits are bound too.
The selected modules cover rational arithmetic, decimal arithmetic, binary packing, JSON, hashing, and process controls.
The reference implementation uses these standard-library facilities without third-party numerical packages.

The record excludes local paths, account identifiers, environment variables, and host names.
Content digests permit identical software at different installation paths.
Runtime verification compares the declared properties before execution and when verifying a saved run.
An incompatible runtime requires a new prospective binding.
The verifier never silently changes the existing binding.

`configs/runtime_reference_v1.json` records the software-validation environment.
It is not an executed research inventory or a promise of another machine's compatibility.

```bash
python scripts/check_runtime.py --capture runtime-local.json
python scripts/check_runtime.py --verify runtime-local.json
```

Capture refuses an existing destination.
These commands do not load checkpoints, datasets, or token records.
Runtime fingerprints do not authenticate hostile storage or pin every dynamic library and imported transitive dependency.
They do not establish identical physical hardware, load, frequency, filesystem behavior, or operating-system caches.
Worker limits separately bind CPU affinity and requested library thread counts.
Actual experimental conditions still require their own record.

## Primary timing profile

Each measured plan declares `execution_mode="clean"` or `execution_mode="diagnostic"`.
The leaf enters the declared scope before loading or quantizing inputs.
It records `execution_mode` and `instrumentation_state` in its receipt.
Its frozen identity binds that selection.

The clean profile disables optional detailed service telemetry and Python allocation tracing.
The service does not evaluate lazy numerical diagnostic builders under that profile.
State output skips optional integer-size scans and stage-detail export.
Unavailable diagnostic fields remain null.
They do not report zero arithmetic work or zero storage.

Clean execution retains exact arithmetic work counters, numerical checks, canonical output, hashing, required state validation, and outer transaction observation.
These costs remain charged to the measured method.
"Clean" therefore describes the removal of specified optional diagnostics.
It does not claim zero instrumentation overhead or production deployment latency.

The scope rejects active Python profiling, tracing, allocation tracing, and allocated monitoring tools.
Allocated monitoring tools are rejected because local monitoring callbacks can exist without global event masks.
Checks run at scope entry and exit.
Existing diagnostic collectors cannot enter a clean scope.
A nested operation cannot enable diagnostic mode inside that scope.
The original numerical failure remains primary if its instrumentation postcheck also fails.

The scope does not detect native profilers or external operating-system tracing.
Their status is explicitly unobserved.
Trusted local code and immutable bound sources remain part of the execution contract.

## Diagnostic profile

The diagnostic profile retains detailed event, allocation, and numerical reports.
These observations can explain certificate rejection, replay, and arithmetic growth.
They must use separate bound runs when clean timing is the primary endpoint.
Diagnostic observations cannot supply clean speed ratios merely because no Python profiler was active.

The existing warm runners retain their previous diagnostic defaults.
The new context does not change their historical timing interpretation.
Clean and diagnostic correctness fixtures compare complete model and state bytes.
Instrumentation must not change the numerical target.

## Input-cost parity

Quantization-only state roles can skip held-out evaluation loading.
Model-only fresh already skips that loading.
The optional quality role loads and evaluates those tokens separately.
All methods still pay their actual calibration parsing, model loading, and required retained-state costs.
Deleting a calibration record never changes the fixed original normalization implicitly.

Software fixtures verify these distinctions.
Real-data memory, language quality, useful coverage, and reliable speed remain unmeasured.
