# Revision 5 validation

Date: 4 October 2026.
Scope: software correctness, independent source review, and document checks.
Research experiments remained paused.

## Final software result

`python -m unittest discover -s tests -v`: **197 tests passed**, exit code 0.
Static compilation passed for all source, test, and script modules.
The full log is `validation/software_tests_v5.txt`.
The tested hashes are in `validation/tested_source_sha256_v5.json`.
Test-run duration is verification metadata, not a repair-performance observation.

Revision 4's 129-test record remains in `docs/VALIDATION_V4.md`.
Its original log and source hashes remain unchanged.
Revision 3's 77-test record also remains available.

## New correctness coverage

| Area | New tests | Checked properties |
| --- | ---: | --- |
| Target and chart construction | 13 | Fixed grids, target/source binding, independent recipes, membership, and planning limits |
| State and baselines | 15 | Canonical bounded reload, malformed input rejection, fresh-process deletion, and indexed information parity |
| Local runner and storage | 8 | Complete fixture pipeline, sealed results, atomic attempts, restart checks, and protocol gates |
| Result analysis | 9 | Planned failures, paired repeats, independent-root intervals, mixed-target rejection, and lifetime accounting |
| Config-only resource planning | 5 | Formula agreement, large-model rejection, huge dimensions, and no tensor reads |
| Independent preparation attacks | 17 | Binding forgery, malformed state, old-model poisoning, storage corruption, locks, and failure classification |
| Checkpoint metadata compatibility | 1 | Historical label metadata leaves language-model computation unchanged |

These 68 tests extend the prior 129 tests.
They do not replace the existing mathematical and decoder checks.

## Integration evidence

The runner fixture uses a locally authored safetensors checkpoint and token-record manifest.
It constructs the target, chart, original state, and three retained comparison outputs.
Successful output requires complete canonical-state and every-stage equality.
The result passes the analysis schema.
This is a small software fixture, not a synthetic empirical study.
Its timings cannot enter a paper's performance table.

The durable-state test starts a fresh Python process.
That process rebuilds the declared service, loads saved canonical bytes, and performs deletion.
Its bytes match independently constructed fresh retained state.
A timeout bounds the correctness check.
This checks process-independent state loading, not cold-service performance.

The fair baseline test replaces old model codes with other valid codes.
Indexed fresh still returns the same retained target.
The solver uses the index and fixed target, not old model proposals.
Repair and indexed fresh share this planner.
No deletion-specific solver speedup follows.

The strongest earlier changed-prefix fixture remains in the suite.
Deletion changes an early QKV code and downstream finite features.
Certified repair matches fresh state without retained-source reads.
Its mostly on-grid downstream weights still limit the fixture's practical scope.

## Independent review

See `theory_revision/preparation_review_v5.txt`.
The reviewer found no unresolved defect in the reviewed declared paths.
Manual review and tests do not establish absence of all defects.

Review corrected these concrete issues:

1. Unicode canonical-state parsing.
2. Target digests missing actual grids, ridge, and normalization.
3. Service identity missing the generated target digest.
4. Writes after completion and completed-result replacement.
5. Racy lock handling and exceptional lock cleanup.
6. Restart checks that did not read persisted artifact bytes.
7. Unchecked failures incorrectly marked as observed mismatches.
8. Lost nested failure subtypes and mixed analysis targets.
9. Config preflight allocating a list before rejecting huge layer counts.
10. Missing finite-error scalars in parameter-jet planning.

The current protocol prevents paused research execution.
Confirmation additionally requires a frozen protocol without blocked fields.
Actual frozen-inventory membership requires the future scheduler and analysis workflow.

## Timing, numerical, and storage limits

The runner offers instrumented warm diagnostic timing.
Its method boundary ends after model/state artifact synchronization.
Loading, setup, verification, quality evaluation, and final result commit have separate scopes.
The method timer does not establish the protocol's complete-service reliable-speed claim.
Python allocation tracing adds overhead.
RSS is a process-lifetime high-water mark.
Cold execution, hard worker limits, and internal callback timers remain pending.

V_cert remains distinct from native kernels, legacy V, and floating E.
Proof rejection permits replay.
Finite-evaluator failure aborts without returning an approximate model.
The report now states completion conditions consistently.

Deletion covers returned canonical live state.
The external research archive deliberately retains original states and failed attempts.
It lies outside that guarantee.
Trusted hashes do not authenticate hostile storage or prove physical erasure.

Config-only byte estimates are planning heuristics.
They do not prove memory fit or useful runtime.
Default reference limits reject ordinary candidate dimensions.
Real checkpoint compatibility and useful chart coverage remain untested.

## Document validation

The consolidated PDF has **28 pages**.
LaTeX completed without overfull boxes.
Every page was rendered for visual inspection.
Modified pages were inspected separately.
The theory now has a T1–T7 publication map and an explicit claim/evidence register.
The research checklist records 21 completed and 57 open required items.
It separately retains 12 conditional extensions.

## Excluded evidence

No model weights or calibration datasets were downloaded or evaluated.
No research benchmark, synthetic empirical study, or external compute job ran.
No practical speed, NLP quality, chart coverage, or lifetime value is established.
Historical missing raw results were not recovered or rerun.
