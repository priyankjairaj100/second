# Revision 16 focused validation

Updated 7 October 2026.
The final focused regression passed 58 tests in 2.716 seconds.
This is software validation, not empirical performance evidence.
It is not a rerun of the full historical suite.

The run covers directed scans, both speculative solvers, canonical state, service integration, grids, and inherited admission.
Independent dense rational oracles test the solver outputs.
Cases include ties, subnormals, partial prefixes, incoming accumulators, global limits, and factor-free warm model seeds.

See validation/software_tests_v16.txt and validation/tested_source_sha256_v16.json.
The latter identifies the tested sources and selected test modules.
Separate proof review also checked 2,808 rational scan prefixes.
This is not proof-assistant verification or a guarantee of defect absence.

Two empirical workers were also executed under separate CPU accounting.
Their outcomes and missing cells appear in docs/EMPIRICAL_PILOT_V16.md.

---

Historical validation follows.

# Revision 9 validation

Date: 4 October 2026.
Scope: software correctness, independent review, exact accounting, and prospective manuscript preparation.
Research experiments remained paused.

## Final software result

`python -m unittest discover -s tests -v`: **524 tests passed**, exit code 0.
Static compilation passed for all source, test, and script modules.
The complete log is `validation/software_tests_v9.txt`.
The frozen tested-source record is `validation/tested_source_sha256_v9.json`.
All 118 Python file hashes matched before and after the suite.
Durations in this log are verification metadata, not research performance observations.

`docs/VALIDATION_V8.md` preserves the previous 417-test checkpoint.
Earlier validation logs and source hashes remain available and unchanged.
The current record applies only to the source named in its hash manifest.

## Added correctness coverage

| Area | Checked properties |
| --- | --- |
| Measured comparisons | Four distinct roles, common model equality, applicable canonical-state equality, setup failure, independent fresh attempts, durable clocks, tamper rejection, and restart |
| Frozen campaigns | Actual model-only membership, runtime/source bindings, full planned products, four-method ordering, phase admission, and paused research |
| Measured sequences | Original preparation once per system, actual predecessor state, empty/full deletion, separate method clocks, lifetime sums, failures, and original timing reuse |
| Verified analysis | Original archives reread, target DAG and group exports, exactness, quality bindings, duplicate-observation rejection, clean child/observer profiles, sole-primary inference, and root clustering |
| Conditional decisions | Exact coverage denominator, quality-token agreement and logarithm enclosure, complete lifetime arithmetic, resource rules, missing-evidence handling, and no empirical promotion |
| Archive-to-policy bridge | Loader-issued evidence, full replay audits crosschecked with target-call counters, diagnostic parity, bound quality, resource accounting, and explicit unavailable premises |
| Runtime/instrumentation | Fresh-process runtime identity, malformed/mutated contracts, profiling/trace/allocation/monitoring rejection, lazy diagnostic bypass, and canonical output identity |
| Provider diagnostics | Affine-fit causes, available bounded proof components, failure phases, omission semantics, and no effect on numerical output |
| Diagnostic decomposition | Actual windows, disjointness and enclosure, exact sum identities, cleanup split, legacy compatibility, absent/truncated details, and explicit unclassified residual |
| Independent attacks | Local-only monitoring, impossible enclosing clocks, changed-leaf coverage, slot/parent substitution, unsealed parents, and invalid diagnostic partitions |

These are software correctness fixtures, not synthetic empirical datasets or NLP benchmark runs.
Fixture equality does not establish real-model feasibility or certificate usefulness.

## Independent review and substantive corrections

The initial full run executed 524 tests on an unchanged source snapshot.
One older test expected the former error wording when quality output was presented as a canonical-state transaction.
The new generalized output-contract check correctly rejected it with a different message.
Only that assertion was updated; no production guard changed.
The targeted regression passed, followed by the final complete rerun.
The initial log remains in `validation/software_tests_v9_initial.txt`.

Read `theory_revision/preparation_review_v9.txt` and `theory_revision/manuscript_review_v9.txt`.
The implementation and review corrected or made explicit these boundaries:

1. Clean mode rejects allocated Python monitoring tool IDs, including local-only callbacks invisible to global event masks.
2. A worker cannot claim an elapsed interval longer than its enclosing complete transaction.
3. Changed stage codes affect descendant-input coverage; a leaf's changed output does not make its own input changed.
4. Confirmation eligibility requires the sole registered primary comparator/configuration, not every favorable secondary ratio.
5. Complete leaf artifacts cannot promote an unsealed parent into a successful planned observation.
6. Parent, manifest, target, and ordered sequence slots bind every reused observation.
7. A later service request uses the previous measured child's committed state and receipt. External research lineage/oracle archives are not uncharged production dependencies.
8. Canonical output serialization has explicit diagnostic spans even after the service-local telemetry context ends.
9. Loading, service construction, internal exclusive spans, and cleanup are checked by actual interval coordinates before decomposition.
10. Bounded diagnostic samples alone cannot establish group-level feature avoidance. Full replay audits must agree with actual target-call counters and retained membership.

This is independent mathematical/source review and correctness testing, not proof-assistant verification or proof of defect absence.

## Measurement boundaries

The primary observer charges source/input checks, worker admission/preparation, process startup/loading, service work, child commitments, exit, cleanup, worker accounting, and output verification.
Its bootstrap and final observer receipt remain excluded.
The clock is a declared local transaction, not externally observed deployment latency.
Nested worker durations are not added to its total.

Every matched lifetime charges one appropriate original preparation plus all actual request transactions.
Model-only and indexed preparations are distinct.
Repair and indexed fresh may share one preparation observation, charged once to each system.
Research equality, common-model conversion, quality, scheduling, and archive bookkeeping remain separate.

Clean observations disable supported optional Python instrumentation in both child and observer.
Required exact counters, validation, hashing, state output, and cleanup remain charged.
Native profiling, operating-system caches, and machine load retain their stated limits.
Diagnostic decomposition never estimates clean latency by subtracting overhead.
Unknown elapsed causes remain an explicit residual.
D04 therefore remains partial under its exhaustive named-attribution criterion.

CPU admission remains trusted protocol-scoped worker accounting.
It does not contain hostile processes or bound controller, cross-protocol, or global physical CPU usage.
A verified ledger snapshot concerns the stated ledger at read time, not all project activity.
Pending reservations and observed overruns retain their charges.

## Feasibility and scientific scope

The unchanged written policy is in `configs/feasibility_gates_v1.json`.
The public archive bridge derives available facts from verified records.
Missing scientific provenance, resources, quality, or diagnostic coverage remains explicit.
An asserted JSON field cannot establish its own correspondence with observations.
No output authorizes a research run, establishes population speedup, or claims empirical attainment.

The numerical target remains complete sequential `V_cert`.
Provider rejection permits exact retained replay.
Required finite-evaluator failure aborts without an approximate successful commit.
Legacy libm `V`, historical floating `E`, and native library execution remain distinct.

The manuscript draft states conditional theory and explicit evidence slots.
No abstract, result, table, or conclusion may turn fixture timings into research evidence.
A current literature audit, real-model validation, useful quality, and actual performance remain necessary.

## Artifact consistency

`validation/artifact_checks_v9.json` records source, task-register, protocol, manifest, and unchanged binary checks.
The 35-page theory PDF remains the revision 7 artifact.
The method figure also remains unchanged.
Protocol version 5 remains prospective and paused; versions 1–4 and the feasibility policy retain their original bytes.

The register contains **29 completed and 49 open required items**, plus **12 conditional extensions**.
Revision 9 closes implementation substeps inside open research tasks.
C05, D04, and D05 retain their broader criteria.
G0 remains open.

No pretrained model, tokenizer, calibration corpus, synthetic empirical study, research benchmark, cloud job, or unrelated hardware ran.
No reliable full-model speedup, useful real-model coverage, language quality, or submission readiness is established.
Historical missing raw evidence remains unavailable.
