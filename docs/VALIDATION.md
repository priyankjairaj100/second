# Revision 8 validation

Date: 4 October 2026.
Scope: software correctness, independent review, prospective decisions, and document consistency.
Research experiments remained paused.

## Final software result

`python -m unittest discover -s tests -v`: **417 tests passed**, exit code 0.
Static compilation passed for all source, test, and script modules.
The final log is `validation/software_tests_v8.txt`.
The tested hashes are in `validation/tested_source_sha256_v8.json`.
All 91 source, test, and script hashes matched before and after the final run.
Test times are verification metadata, not research performance observations.

Revision 7's 340-test record remains in `docs/VALIDATION_V7.md`.
Its logs and source hashes remain unchanged.
Earlier validation records remain available.

## New correctness coverage

| Area | New tests | Checked properties |
| --- | ---: | --- |
| Isolated campaigns | 8 | Frozen inventories, exact confirmation products, verified membership, failures, quality, and feasibility admission |
| Sequence campaigns | 7 | Ordered provenance, complete products, original-once execution, shared admission, failures, and archive verification |
| Complete transaction timing | 14 | Exact clock partition, output contracts, fresh/resumed observations, descendant cleanup, and command admission |
| Arithmetic audit | 16 | Fraction endpoints, bounded attribution, memory availability, exceptions, source stability, profiling interference, and numerical parity |
| Certificate diagnostics | 10 | Bounded stage details, exact scalar limits, disposition totals, nested categories, and unchanged canonical outputs |
| Model-only fresh | 7 | Cross-family model equality, transitive ancestors, empty input, skipped index construction, pauses, restart, and admitted execution |
| Profiled analysis | 3 | Embedded flags, ratio exclusion, mismatch priority, and measurement failures |
| Independent review | 12 | Inventory and request tampering, admission bypass, bound inputs, model-only fairness, and transient arithmetic |

These 77 tests extend the previous 340 tests.
The fixtures do not constitute synthetic empirical datasets.
They establish software behavior within explicit contracts.

## Initial integration finding

The first integrated run failed four subcases of one existing role-isolation test.
Its abbreviated manifest lacked a phase field.
The new admission check correctly refused that incomplete research context.
The fixture now declares `phase="software_test"`.
Its forbidden-method assertions remain unchanged.
The targeted test passed before the final complete rerun.
The initial log remains in `validation/software_tests_v8_initial.txt`.
No production guard was weakened.

## Independent review and corrections

Read `theory_revision/preparation_review_v8.txt` for the complete review scope.
The review and integration corrected these issues:

1. Nested timing categories could exceed the intended diagnostic capacity.
2. Bound request changes required explicit restart verification.
3. Model-only and isolated child commands needed live admission checks before research loading.
4. Profiled outputs needed internal labels to prevent clean latency analysis without their sidecar report.
5. Sequence correctness needed separate treatment from clean timing eligibility.
6. Nested workers in separate sessions needed cleanup after an enclosing timeout.
7. Model comparison across state families needed a common target-and-code encoding.
8. Final documentation needed explicit feasibility worker limits and narrower diagnostic-count wording.

The model-only control skips response extraction and persistent deletion state.
The old direct fresh path remains the full-state oracle.
Its larger output contract cannot substitute for ordinary requantization cost.
The measured model-only integration test verifies a real reserved command and settled debit using local software fixtures.
It does not execute a research model.

## Timing and admission scope

The observer measures through the child transaction, controller commitments, output checks, and cleanup.
Its own final receipt lies outside that clock.
Disjoint spans sum exactly to the declared interval.
Complete individual role measurements are available.
A clock for a whole comparison cannot substitute for one method's clock.
Fresh and resumed transactions have separate labels.
Reused receipts never become new latency observations.
Operating-system caches remain uncontrolled.

Research leaf commands verify exact command, protocol, phase, source binding, and a live reservation.
The ledger controls admission within one frozen protocol scope.
It does not establish hostile-process containment or a global physical CPU cap.
Enclosing and nested debits can overlap when both are explicitly enabled.
Such accounting cannot become a claim of independent CPU work.
Controller and observer costs keep their stated exclusions.

Primary campaign and lifetime analysis still need integration with the complete role clocks.
Model-only confirmation still needs a compatible frozen inventory.
Actual research configurations and resource feasibility remain unresolved.

## Numerical diagnostics

The endpoint audit profiles standard Fraction allocation returns in the current process and thread.
It reports bit lengths, bounded attribution, available traced memory, process RSS, and output sizes.
It does not measure hidden integer intermediates or exact live rational storage.
Child execution, profiler interference, and observer errors mark coverage incomplete.
Unavailable measurements remain null.
The audit preserves numerical model and state hashes.

The runner records profiling flags in saved observations.
The analyzer excludes those observations from clean speed ratios.
Scientific exactness checks remain valid.
Provider internals and complete transient arithmetic accounting remain unresolved.
The funnel exposes bounded samples and disposition counts for recorded stages and events.
Omission and saturation counters expose lost detail.
It does not invent unavailable numerical failure causes.

## Document consistency

The current implementation note is `docs/REVISION_8.md`.
The consolidated 35-page theory PDF remains the unchanged revision 7 artifact.
The existing method figure also remains unchanged.
Protocol version 4 preserves the experiment pause.
It binds the fixed feasibility policy and retains unresolved research fields.
Earlier protocol versions remain unchanged.

The task register contains **29 completed and 49 open required items**, plus 12 conditional extensions.
Only C04 closes in this revision, at its written decision-policy scope.
C05, D04, and D05 retain their broader completion criteria.
Software infrastructure does not establish empirical threshold attainment.

## Excluded evidence

No pretrained model, tokenizer, calibration corpus, or research benchmark was acquired or executed.
No synthetic empirical study, cloud job, or unrelated hardware ran.
Useful real-model coverage, language quality, memory fit, lifetime value, and reliable speedup remain unmeasured.
Earlier missing raw results remain unavailable.
The paper is not ready for submission.
