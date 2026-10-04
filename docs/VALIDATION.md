# Revision 7 validation

Date: 4 October 2026.
Scope: mathematical derivation, software correctness, independent review, and document checks.
Research experiments remained paused.

## Final software result

`python -m unittest discover -s tests -v`: **340 tests passed**, exit code 0.
Static compilation passed for all source, test, and script modules.
The final log is `validation/software_tests_v7.txt`.
The tested hashes are in `validation/tested_source_sha256_v7.json`.
Source, test, and script hashes matched before and after the final run.
Test durations are verification metadata, not repair-performance observations.

Revision 6's 261-test record remains in `docs/VALIDATION_V6.md`.
Its original log and hashes remain unchanged.
Earlier validation records also remain available.

## New correctness coverage

| Area | New tests | Checked properties |
| --- | ---: | --- |
| Quadratic service | 9 | Oriented cross-moments, negative coefficients, finite error, modes, tiers, serialization, and repeated deletion |
| Original-model cache | 17 | Transitive prefix dependencies, exact subtraction/replay, canonical refresh, bounded trusted state, and indexed fairness |
| Sequences | 7 | Previous-state lineage, original-once construction, full deletion, failures, future requests, and restart |
| CPU admission | 9 | Reservation, settlement, unknown attempts, retry charges, caps, overruns, and ledger integrity |
| Isolated executor | 6 | Separate workers, exact outputs, pauses, denial, failed artifacts, interruption, and timing integrity |
| Interval verifier | 10 | Signed bounds, ridge pivots, factors, ties, inclusion, strict intersection gain, and binding failures |
| Independent adversarial review | 18 | Cross-tier mathematics, cache dependencies, lineage, budgets, analyzer mixing, isolation, and failure cleanup |
| Root integration | 3 | Quadratic planning counts, schema compatibility, target identity, identity factory, and complete deletion |

These 79 tests extend the previous 261 tests.
Existing runner and workload tests were also adapted to their expanded supported contracts.
No empirical dataset study ran.

## Initial integration findings

The initial integrated run had two errors.
An adversarial fixture lacked the newly required stable worker request file.
The fixture now supplies that binding before exercising its original corruption attack.
A final source-description edit during the initial run triggered an immutable source-hash rejection.
The source guard correctly refused the changed plan.
All code then froze before the final complete rerun.
The initial log remains in `validation/software_tests_v7_initial.txt`.

Independent review also corrected these defects before final integration:

1. A phase-budget snapshot exposed mutable ledger state.
2. Sequence plan-writing failure could retain a writer lock.
3. Direct fresh unnecessarily loaded the original canonical index.
4. Child receipt failure could skip writer-lock cleanup.
5. Missing outer timing could permit reused child output to receive misleading short latency.

The last case now records failure instead of manufacturing a successful replacement timing.
Read `theory_revision/preparation_review_v7.txt` for the review's actual scope.
The review is not formal verification or proof that all defects are absent.

## Mathematical and algorithmic scope

R1–R6 derive signed entry bounds, ridge-safe elimination, exact candidate verification, intersection monotonicity, and canonical bank conditions.
The optional service policy keeps the spectral verifier first and adds one interval enclosure after rejection.
It preserves accepted spectral decisions at the same proposal when calculations complete.
It does not establish runtime or completion dominance under finite resource caps.
Software examples establish strictly additional certified cases with exact fresh-state equality.
They do not establish useful neural coverage.
The complete neural multi-domain bank remains unimplemented.
Classical interval arithmetic and Schur identities receive explicit attribution.

The full quadratic tier uses the existing unwhitened error bound.
Its stronger whitened acceptance rule remains unimplemented.
The original-model cache stores true current-prefix Grams and refreshes them canonically after every request.
Equally indexed fresh receives the same valid cache and old model.
Both families retain solver parity with their equally indexed comparator.
No deletion-specific solving advantage follows.

V_cert remains a partial finite target distinct from legacy V, floating E, and native kernels.
Proof rejection permits exact retained replay.
Required finite-evaluator failure aborts without an approximate committed model.
Canonical deletion concerns returned live state under trusted storage.
External archives, physical erasure, and hostile-storage authentication remain outside scope.

## Execution boundaries

The warm runner and separate-process executor have distinct labels.
The isolated executor uses one setup process and one process per method.
Its clock includes startup, inputs, requested work, artifacts, child commitment, and process cleanup.
Parent validation/equality, post-cleanup settlement, logs, and controller receipts remain outside that clock.
Operating-system caches remain uncontrolled.
Setup cost remains separate and must enter lifetime accounting.
Each worker exposes peak RSS and observed child CPU.
Final serialized rational integer counts and maximum bit lengths are recorded.
Comprehensive transient arithmetic-size diagnostics remain open.

A durable ledger governs admitted worker allowances within one frozen protocol scope.
Observed overruns remain charged; unknown attempts retain reservations.
This does not establish absolute physical CPU containment or a global budget across protocol variants.
Controller CPU is excluded.
Bulk sequence dispatch and isolated confirmation inventory remain open.
The isolated executor does not yet compute NLP quality.

## Document checks

The consolidated report has **35 pages**.
LaTeX completed without overfull boxes.
Every page was inspected in rendered contact sheets.
The four new pages were also inspected at readable resolution.
The deterministic method figure is available as editable SVG and vector PDF.
Repeated figure builds produced identical hashes.
Its one-page PDF contains no embedded raster images.

The register contains **28 completed and 50 open required items**, plus 12 conditional extensions.
Newly closed items are D06, E03, E04, and J04, at their stated scopes.
Protocol version 3 preserves the pause and unresolved empirical gates.

## Excluded evidence

No pretrained model, tokenizer, calibration corpus, or research benchmark was acquired or executed.
No synthetic empirical study, cloud job, or unrelated hardware ran.
Useful coverage, practical latency, real memory fit, NLP quality, and lifetime value remain unmeasured.
Earlier missing raw results were not recovered or rerun.
No reliable full-model speedup or publication readiness is established.
