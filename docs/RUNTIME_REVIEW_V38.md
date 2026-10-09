# Independent runtime review, V38

Date: 9 October 2026.

Status: local review complete. One bounded C4 workflow is approved with the gates below.
The external runtime comparison and empirical results remain pending.

The historical C4 campaign remains blocked.
Gate 7 from `RUNTIME_PORTABILITY_PLAN_V37.md` remains unresolved.
This host cannot supply the required comparison between live proc observations and the new collector.
Local tests cannot establish historical target compatibility.
No real-model computation supports this review.

## Scope and identity

The old decoder binds loaded libraries, CPU dispatch fields, Python, and arithmetic properties.
Its MPFR manifest independently binds GMP, MPFR, MPC, and the loaded gmpy2 extension.
The checkpoint adapter hardcodes the old constructor.
The certified decoder embeds both manifests in its evaluator identity.
The ordered decoder also binds its implementation separately.

A new collector changes evaluator identity, target digests, and prepared-state identity.
Matching weights or arithmetic helpers does not make historical states compatible.
Keep historical sources, failures, registration, and ledger entries unchanged.
Do not insert the new collector into the failed C4 transaction.

## Required gates

1. Enumerate live loaded libraries with a supported loader API.
2. Require each numerical dependency and resolve relevant symbol owners.
3. Reject missing, ambiguous, deleted, or unreadable library files.
4. Hash readable files and check their stability during collection.
5. Bind the collector source, helper binary, compiler identity, and compiler flags.
6. Collect actual CPU features, required OS state, and relevant dispatch settings.
7. Keep CPU affinity fixed during collection and evaluation.
8. Preserve binary64 rounding and gradual-underflow checks.
9. Reject unsupported architectures, missing APIs, incomplete observations, and changed evidence.
10. Check every public evaluation route, including prepared prefixes and suspended generators.
11. Use explicit construction paths with distinct manifests and source bindings.
12. Preserve all unchanged numerical helpers and parameter parsing rules.

These checks assume trusted process code and stable library files.
File hashes do not attest every mapped memory byte.
Symbol ownership does not prove every internal dispatch decision.
Record those limits explicitly.
Do not manufacture a proc-compatible flags string from CPUID.

## What local tests can establish

Fixtures can check schema validation, deterministic serialization, source bindings, and explicit refusal paths.
They can check missing libraries, changed hashes, incomplete CPU evidence, and affinity changes.
They can compare finite arithmetic against the unchanged scalar executor on declared fixture inputs.
They can confirm that separate construction leaves historical globals unchanged.
They can check evaluation entry points and generator advancement.

Live collection can establish which required interfaces actually work on this host.
Passing local collection does not establish broad platform support.
Passing fixtures does not establish real-model equality or completion behavior.

## What remains external

Gate 7 requires a compatible Linux host with readable proc interfaces.
Collect old and new observations in one controlled process, or equivalent controlled children.
Explain all differences between represented library and CPU facts.
Preserve raw observations, source hashes, affinity, and the comparison result.
Do not infer a passing result from API documentation or simulated proc input.

The existing plan lists this comparison as a minimum validation gate.
This review does not waive it.

## Minimum experiment after the gates pass

Register a new campaign before any real-model computation.
Freeze the new runtime schema, complete source inventory, input records, methods, and resource limits.
Prepare fresh state under the new evaluator identity.
Run repair and cold reconstruction under the same new identity and target recipe.
Compare all model codes, state bytes where required, and complete costs.
Record setup, preparation, verification, loading, output, fallback, and failures.
Do not use historical latency as the matched comparator.
Do not retry old attempts or replace old receipts.

Begin with one bounded C4 development request using previously declared records.
Treat this as development evidence, not independent confirmation.
Keep any later confirmation records unexposed.
Expand only after exact agreement and complete accounting pass.

## Source review coverage

Reviewed the relevant runtime consumers in these unchanged files:

- `src/transformer_backend.py`
- `src/finite_primitives.py`
- `src/certified_transformer.py`
- `src/ordered_finite_decoder_v30.py`
- `src/checkpoint_adapter.py`
- `src/runtime_contract.py`
- `src/worker_control.py`
- `src/transaction_timing.py`
- `scripts/run_ordered_service_v30.py`
- `scripts/preflight_environment_v34.py`

The normal worker controller does not require proc-based process enumeration.
The separate transaction observer does require proc interfaces.
Any new campaign must bind and review its actual controller path.

## Implementation review

The collector uses live ELF discovery, symbol ownership, CPUID, XCR0, and auxiliary-vector evidence.
It checks affinity, relevant environment variables, numerical controls, and loaded dependency files.
It binds NumPy's live feature selection and loaded binary dependencies.
It excludes sticky exception flags from runtime identity.
It checks supported numerical entry points before and after evaluation.

The decoder uses explicit constructors with distinct evaluator identities.
It preserves the existing arithmetic helpers and checkpoint parsing rules.
The ordered path checks each generator advancement and prepared-prefix evaluation.
The unsupported legacy jet service raises an explicit error.
No global constructor or registered numerical source is replaced.

Review identified three collector defects before approval.
The returned manifest could alias the cached helper identity.
Static Python needed the existing process handle.
ELF reads needed an earlier size bound.
The author corrected all three.
The final helper publication also prevents concurrent replacement of loaded helper files.

The reviewer independently passed all 19 collector fixtures and all 14 backend fixtures.
These are small software fixtures, not empirical datasets.
The final collector and scalar-equivalence invocation passed 20 tests in 40.055 seconds.
The remaining backend invocation passed 13 tests in 46.793 seconds.
These times are test-run wall times, not empirical service costs.

An earlier reviewer invocation passed 13 backend tests and refused one construction.
The collector author changed its source during that invocation.
The runtime check detected that change and prevented return.
The full invocation took 69.614 seconds and exited with one error.
The final checks used frozen source.
This software rerun does not retry a registered empirical attempt.

Reviewed source hashes:

| File | SHA-256 |
|---|---|
| `research_v38/live_runtime.py` | `b50f90921d4d56e392e4fbe00543316e352632356ae59a7ee13e5054176fa2aa` |
| `research_v38/runtime_probe.c` | `e8dc0167fa06bee1eab1f88725c54180ac3e967e2f1011b2e8a32cef5e502aad` |
| `research_v38/portable_backend.py` | `02f4fbba67b72622dda8d71437d6c6b43f1287d716b9ab9d9d8f655d8e4b45b0` |
| `research_v38/portable_checkpoint.py` | `22679847d592ba7451f9194f168311962ca8dfbc70bae2743d7251629ccb2d00` |
| `tests/test_live_runtime_v38.py` | `166e1ef5eea8f6e17917ca0e1982289a44ec2456e8257b5c137411ec5ff26ba0` |
| `tests/test_portable_backend_v38.py` | `bda290df655c0a1cca5e1534d2b253e2ec812c3fd18e5a02caa9d21729b4b16a` |

Local source and fixture review passes at these hashes.
External gate 7 remains unresolved.
This review does not approve portable-backend empirical execution before that gate closes.

## Separate path using the unchanged backend

A compatible Linux host can run the original backend without the V38 collector.
That path does not depend on gate 7.
It still requires a fresh registration and fresh preparation.
The failed historical C4 attempt remains unchanged.
The new host changes runtime facts and therefore changes evaluator identity.
The mathematical recipe stays fixed, but its recorded target digest changes.
Construct and verify that digest before registration.
Require the same digest in all seven new worker plans.
Record target-construction costs in a separate bounded ledger.

Prior WikiText success can serve as a declared development prerequisite.
This does not make a new C4 request independent confirmation.
Both C4 methods must use the same new preparation and runtime.
Old host timings cannot supply the matched comparison.

The reviewed GitHub workflow can run once under the specified controls.
The job must require a public repository and a standard hosted runner.
Use a bounded runtime and no paid hardware, cache writes, or artifact storage.
Limit token permissions to the contents writes needed for authorized repository checkpoints.
Never print credentials.
Commit registration before the first empirical worker starts.
Commit each trial outcome before the temporary host disappears.
Preserve failures and complete resource charges.
Keep all prior source and ledger bindings unchanged.

The runtime cross-check and C4 campaign use separate approval gates.
An unsupported V38 collector interface can block only the portable backend.
A contradiction in shared live facts must block both paths pending review.
Record that distinction before execution.
Do not catch every cross-check failure and continue silently.

## Final workflow decision

Approve one launch of the frozen public-repository workflow.
This approves the bounded procedure, not an empirical result or portable-runtime equivalence claim.
No empirical worker ran during this review.

The workflow requires genuine proc interfaces for the unchanged backend.
It runs bounded host fixtures before target construction.
The required constructor fixture must pass without a skip.
It publishes a one-use claim and each subsequent audit.
It publishes bootstrap registration before checkpoint construction.
It publishes campaign registration before calibration workers.
It publishes each trial intent before that worker starts.
It stops on publication failure, integrity failure, or an incomplete trial.
Scientific timing losses remain visible and do not trigger a retry.

The bootstrap has a separate 122-second CPU allowance.
The campaign has a 1,900-second CPU allowance.
An unresolved loss retains the applicable allowance without inventing observed use.
The workflow has a 60-minute wall limit.
It permits no paid hardware, cache storage, or artifact storage.
Its contents permission serves the authorized registration and evidence commits.
It never forces a repository update.

The copied controller preserves all seven trial definitions except their expected target digest.
The new digest comes from verified construction on the actual host.
The records, methods, numerical limits, trial order, dependencies, and comparisons remain unchanged.
The copied analysis preserves the original computational checks.
Both methods use fresh state on the same host.
No historical latency becomes a matched comparator.

The runtime comparison binds genuine old manifests and bounded proc observations.
It compares selected CPU facts with CPUID and the old first-record fields.
It compares common library hashes and preserves facts absent from the older schema.
It keeps CPU flags and CPUID registers as distinct representations.
It checks relevant OS state for mapped vector features.

Only a narrow list of unsupported portable interfaces permits the original backend to continue.
That path requires fresh, matching old manifests before and after the refusal.
It also requires stable sources, affinity, and selected CPU facts.
Gate 7 stays open on that path.
Changed hashes, unexpected symbol owners, contradictory facts, and unknown errors block execution.
The wrapper checks each completion flag and the matching observations before admission.

The reviewer independently ran the final CI, bootstrap, and comparison fixtures.
The command completed 46 tests in 0.415 seconds.
Forty-five tests passed.
One genuine-proc constructor fixture skipped because this host lacks proc interfaces.
The workflow requires that same fixture to pass on its compatible host.

Final reviewed hashes:

| File | SHA-256 |
|---|---|
| `research_v38/c4_controller.py` | `13ced369c022a009f520150465e875523517b25e5a28e2191f34ef379e6a0f2f` |
| `research_v38/c4_analysis.py` | `32c95bcbe76f34d3c2a5ad9bf2b487ab4f6607465a5a16d20cd7ff27d2533615` |
| `research_v38/bootstrap_target.py` | `e5da4bb5ef9eead25d7299cf132015d28ff60ff1c978dcf7f7fbfc107b8597a5` |
| `scripts/execute_ci_c4_v38.py` | `9c756e71a0231cf2aac207f0bf037d093d964fa1c408c292e77970f4689be1e2` |
| `scripts/check_runtime_portability_v38.py` | `6427d39a29ebfe7e2acaf348f431d82af624a21990d4b32f539729a947af7d30` |
| `.github/workflows/c4-v38.yml` | `b9a5b317eb7f6791ff5096854b3e466a8bdab4a865b340b0546af1b3d537091c` |
| `.github/ci/c4-v38-trigger.json` | `22ed2f55def5d6554e84e2016498c2364e3fdd54122407e6055b99be7fb4b22a` |
| `requirements-ci-v38.txt` | `aaf12af73eea818e7e83ca3afb91cbc0ce1b7f7e66b99412558848d33c905050` |
| `tests/test_ci_c4_v38.py` | `054cd64df0454cec16521a7c9164735aa71edc885cb768604485c41e4bc5cc22` |
| `tests/test_bootstrap_target_v38.py` | `836893db52441085c0d5e4b2f47c62d55fc46c24f65e5daeabab6086c89ae947` |
| `tests/test_runtime_crosscheck_v38.py` | `bcc63758eaacf5d772a217870e0284fcd6529d58c8da3449f68ab477e8586888` |

Changes to these sources require a new review before execution.
Actual workflow observations must determine whether each remaining gate closes.

## Pre-runner syntax amendment review

GitHub rejected run `37948393273` before it created any jobs.
The source commit was `1cf45ff1861b7e347bcef6308b3eddbb1e5e6534`.
The saved incident reports empty job and check-run lists.
No claim, registration, or model worker started.
Read `validation/workflow_yaml_rejection_v38.json` for the preserved evidence.

The initial review missed a YAML parsing defect.
The plain dependency command contained a colon followed by a space.
The corrected workflow uses a block scalar.
The parsed command remains exactly unchanged.

The reviewer independently parsed the complete workflow with PyYAML 6.0.3 using `BaseLoader`.
The reviewer checked the trigger pattern and exact dependency command.
All 22 CI fixtures passed in 0.394 seconds.
This validates YAML syntax and the declared fields.
GitHub still validates its own workflow contexts.

Approve publication of this narrow amendment for the first actual runner execution.
The trigger records the rejected run and source commit.
The one-use revision, campaign guard, limits, workers, and numerical policy remain unchanged.
This is not a retry of any registered trial.
No automatic rerun button is authorized.
All earlier empirical and runtime gates remain required.

Amended source hashes:

| File | SHA-256 |
|---|---|
| `.github/workflows/c4-v38.yml` | `d1b9cf1e35cd3a90d0ea02f36e85b45aea1f31e3213ae3986ccd24a1be84ff48` |
| `.github/ci/c4-v38-trigger.json` | `7ec775ff5044eec0e5a5454f86635cc09b81b2b75eabf2c9d2e503f7dd31402b` |
| `scripts/execute_ci_c4_v38.py` | `a8f867b2af8c693bf00e985a21c1e4f330e8b7e9d6d26fcd81b39ccba11fcddd` |
