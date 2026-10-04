# Revision 6 validation

Date: 4 October 2026.
Scope: software correctness, independent review, mathematical review, and document checks.
Research experiments remained paused.

## Final software result

`python -m unittest discover -s tests -v`: **261 tests passed**, exit code 0.
Static compilation passed for all source, test, and script modules.
The final log is `validation/software_tests_v6.txt`.
The tested hashes are in `validation/tested_source_sha256_v6.json`.
Test duration is verification metadata, not a repair-performance observation.

Revision 5's 197-test record remains in `docs/VALIDATION_V5.md`.
Its original log and source hashes remain unchanged.
Earlier revision records also remain available.

## New correctness coverage

| Area | New tests | Checked properties |
| --- | ---: | --- |
| Fixed-box provider | 8 | Grid coverage, midpoint error, exact bounds, intrinsic state, domain checks, and lazy wrappers |
| Controls and telemetry | 10 | Target parity, reference identity, fixed-reference bounds, exclusive clocks, and failed-operation cleanup |
| Workload and inventory | 14 | Exact original-only scores, source withdrawal, phase separation, sampling, method order, and immutable inventory |
| Worker and campaign | 12 | Process caps, acknowledgment verification, cleanup, durable failures, confirmation products, and artifact checks |
| Independent adversarial review | 16 | Off-chart changes, Gram bounds, identity misuse, score edges, analysis mixing, and restart attacks |
| Root integration | 4 | Constructor bindings, resource counts, endpoint membership, and runner control parity |

These 64 tests extend the prior 197 tests.
They do not replace previous oracle, decoder, state, and changed-prefix checks.

The first full integrated run found one outdated timeout test stub.
The stub rejected the new optional telemetry keyword before raising its intended timeout.
Its signature now accepts optional keywords.
The timeout assertion remains unchanged and passes.
The initial log is `validation/software_tests_v6_initial.txt`.
The targeted check and complete final suite both pass.

## Independent review

See `theory_revision/preparation_review_v6.txt` and `theory_revision/box_theory_review_v6.txt`.
The review corrected these defects:

1. Unverified worker limit acknowledgments.
2. Missing failed-worker artifact verification on restart.
3. Incomplete confirmation configuration/root/request/repetition product checks.
4. Analysis mixing across mechanism modes, chart hashes, and service identities.

The reviewer found no remaining numerical defect in the inspected box and control paths.
This finding is not formal verification or proof that every defect is absent.
The box results remain conditional on sound intervals and successful required finite evaluations.

## Mathematical and algorithmic scope

The box route removes affine-span rejection for installed frozen-grid parameters.
It does not establish useful numerical bounds or rounding acceptance.
Midpoints minimize each rectangular interval feature envelope.
They remove separate finite anchor evaluation for varying parameter domains.
They do not guarantee better final Gram bounds, acceptance, or complete latency.

Rank-zero aggregate state uses d²+6 rational slots per occupied stage group.
The full-grid box stores 2P_A endpoint slots.
Metadata, bit lengths, base arrays, output, and replay remain costs.
Lazy parameter wrappers avoid constructing unused later matrices.
They do not prove whole-model memory fit.

V_cert remains a partial finite target distinct from legacy V, floating E, and native kernels.
Proof rejection permits retained replay.
Necessary finite-evaluator failure aborts without committing an approximate model.
Canonical deletion concerns returned live state under trusted storage.
The external research archive retains original states and failed attempts.
Physical erasure and hostile-storage authentication remain outside scope.

## Timing and comparison limits

The runner supplies instrumented warm diagnostic timing.
Nested component spans exclude their child durations.
One limited process isolates each comparison, not each method.
The methods share warm objects and process history.
Operating-system caches remain uncontrolled.
Final result commit and campaign orchestration lie outside method timers.
Cumulative phase CPU caps remain unenforced.
RSS remains a process high-water mark.
Detailed arithmetic size and every numerical rejection subtype remain unrecorded.

Repair and indexed fresh share the same planner.
The planner ignores old model codes.
No deletion-specific solver advantage follows.
The identity-only mode checks fixed base-reference ancestors.
It does not implement original quantized-model invariant-feature caching.
The full quadratic control remains open.
Sequence and complete-deletion campaign execution remain open.

## Document validation

The consolidated PDF has **31 pages**.
LaTeX completed without overfull boxes.
Every page was rendered and inspected in contact sheets.
The three new pages were also inspected at readable resolution.
The new sections cover fixed boxes, midpoint optimality, explicit limits, and preparation controls.
The research checklist contains 24 completed and 54 open required items.
It separately retains 12 conditional extensions.
Protocol version 2 preserves the pause and all unresolved execution fields.

## Excluded evidence

No pretrained model, calibration corpus, tokenizer, or research benchmark was acquired or executed.
No synthetic empirical study or external compute job ran.
No practical speed, useful coverage, NLP quality, memory fit, or lifetime value is established.
Historical missing raw results were not recovered or rerun.
