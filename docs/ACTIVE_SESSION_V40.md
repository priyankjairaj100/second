# Current native-control and streamed-solver checkpoint

Updated 10 October 2026, before publication of the V40 one-use trigger.
This checkpoint supersedes earlier execution-status notes.
Actual workflow records and campaign evidence remain authoritative.

V39 completed successfully and every one of seventeen arm/size outputs matched exactly.
Read `SCALE_RESULTS_V39.md` for all results, accounting, and the research decision.
Its final evidence commit is `2881ca95793a0d0a97d76134633ae7a8f28c600d`.
Its workflow is https://github.com/priyankjairaj100/second/actions/runs/38023401448.
All V39 workers are settled.
The local metadata audit passed; absent binaries were not locally reverified.

At 1,536 tokens, the primal solver beats the token solver by 2.76 times.
Gram deletion remains faster and smaller than the cached primal and 48-bit compressed arms.
At 768 tokens, 40-bit compression offers a narrow payload/latency tradeoff.
These are single-stage development observations.
They do not establish a strong paper or reliable complete-model superiority.

## V40 before trigger publication

New implementation lives under `research_v40`.
`native_exact_gram.py` preserves exact V35 archives using admitted integer arithmetic.
`streamed_primal_ball.py` avoids a concatenated retained feature matrix.
Read `NATIVE_EXACT_GRAM_V40.md`, `STREAMED_PRIMAL_V40.md`, and `SCALE_PROTOCOL_V40.md`.
Twenty-six focused software checks passed locally.
They include independent rational comparisons, exact archive equality, arithmetic edge cases, and execution guards.
No V40 empirical registration or result exists at this document's cutoff.

Publishing `.github/ci/native-scale-v40-trigger.json` can start the free public workflow.
The workflow is `.github/workflows/native-scale-v40.yml`.
The evidence prefix is `campaigns/ci_native_scale_v40`.
The same thirteen exposed real articles support fresh comparisons at 768 and 1,536 retained tokens.
There are six arms per size and twelve observations total.
The normalization remains 1,664, with ridge 1/100 and four-bit fixed base-only grids.
Only the complete first QKV stage is evaluated.
Its 1,769,472 codes must match for every completed arm.
Native and reference source archives must match before the comparisons proceed.
Deleted and fresh retained exact Gram archives must also match.
No outcome-based repetitions or cross-run causal timing claims are authorized.

The data allowance is 122 CPU seconds.
The model allowance is 1,700 CPU seconds, with 1,646 seconds reserved across all planned workers.
These are new phase limits, not measured usage or resets of older ledgers.
The process limit is 6 GiB with one numerical thread and one CPU.
Setup, software checks, publication, and audits are outside empirical ledgers.
No paid compute, cache storage, or artifact upload is used.

## Recovery rules

Inspect the actual workflow and evidence before doing anything else.
Never use the rerun button or reuse an attempt directory.
Never push unrelated changes while the workflow publishes.
Do not change source or control files after registration.
The controller stops when the remote parent differs.
On failure, preserve the error and settled receipts before proposing a fresh registration.
If settlement evidence is lost, hold the full affected phase allowance.
Never present an unknown hold as observed CPU usage.

Read the execution claim, program, registration publication, trial receipts, ledgers, analysis, and finalization.
Derived binaries remain on the temporary runner.
CI must compare actual bytes before shutdown.
Git preserves text evidence and binary commitments.
A later local metadata audit does not recover missing binaries.

## Ordered remaining work

1. Complete and audit V40 without discarding baseline wins or compression refusals.
2. Choose the solver and representation using those results and declared access constraints.
3. Integrate the strong Gram and streamed controls into a complete model service.
4. Compare every complete model and canonical successor state against an independent retained reconstruction.
5. Run successive deletions; test root independence, empty retention, and deletion-order invariance.
6. Measure preparation, complete stored bytes, loading, repair, fallback, and lifetime break-even points.
7. Establish a useful compression frontier against the strongest baseline.
8. Add another model, independent corpus roots, and untouched quality evaluation.
9. Diagnose acceptance and refusal mechanisms with ablations fixed before confirmation.
10. Freeze the method and run randomized prospective confirmation with uncertainty analysis.
11. Finish theorem-to-code checks and the primary-literature novelty audit.
12. Complete the manuscript, limitations, exact claim table, and reproduction package.

Read `CLOSEST_WORK_UPDATE_V39.md` before writing novelty claims.
ExecCert's full text is now retrieved; the earlier retrieval gap is closed.
Its implementation has not been reproduced here.
Fixed features, additive deletion, and residual certificates alone do not establish novelty.
The most plausible contribution concerns exact discrete code recovery from uncertain evidence.
Its useful empirical tradeoff remains unresolved.

The full research program and ACL manuscript remain incomplete.
The original sequential target still lacks demonstrated full-model repair superiority.
Preserve all adverse findings and all sixty historical quality exclusions.
Preserve `src/*.py`, `scripts/run_*.py`, frozen sources, and historical ledgers.
Use new research directories for future implementations.
Repository pushes remain authorized; force-pushes and subagent delegation do not.
