# V59 completed: fixed full-precision teacher passes the exposed quality screen

Updated 14 October 2026. This V60 reporting checkpoint supersedes V59's
preparation-only access status; it does not register a V60 experiment.
Read `handoff/program_v60.json` for exact identities and accounting.

## Verified outcome

The one declared full-precision-teacher candidate completed all 24 stages and
42,467,328 four-bit codes on the exact root that failed V55. Its PPL is
**51.85007677238838**, versus **52.063420135148434** for the actual matched
sequential model. Candidate/sequential pooled ratio **0.9959022407247494** passes
the unchanged 1.05 limit; maximum article ratio **1.0655980501752642** passes
the unchanged 1.20 limit. The candidate has lower loss on five articles and higher
loss on three. It improves all eight over the old nearest-anchor calibrated model
(PPL 55.146657300702955; candidate/old-fixed ratio 0.9402215711763078).

This is one adaptive development candidate on eight already exposed articles,
not an untouched test, superiority result, or population claim. All sixty
historical exclusions remain. V55's valid adverse result is unchanged.

The new target uses original checkpoint weights for all feature traversals;
calibrated outputs never become teacher weights. Six C4 records / 768 tokens,
original normalization 1664, checkpoint, four-bit dyadic24 grids, ridge, order,
ties, evaluator and articles are unchanged. All 32 prior control losses reproduced
exactly before construction (maximum mean-NLL difference 0.0 under the frozen
1e-8 tolerance). The first-stage packed bytes match both old calibrated controls.

## Execution and cost

Clean local, GitHub and cluster source was synchronized to
`60a514098511526924cb5746a2a61851b5f6bd23` before the one-use launcher ran.
Its numerical source inventory has 412 files, all still unchanged.

- 13548: 49 pinned Linux tests passed, zero skips; Slurm wall 10 s, CPU 8.126 s.
- 13549: registration completed; Slurm wall 5 s, CPU 3.930 s.
- 13550: complete valid diagnostic; Slurm wall 27:17, CPU 27:11.434.
- 13551: actual-artifact audit verified; Slurm wall 1:11, CPU 1:09.653.

All four jobs completed with exit 0:0. None remains active. The quality worker's
sealed debit is **1,626 CPU seconds**, from **1,625.89083 observed CPU seconds**,
within its separate 14,402-second phase cap. Constructor wall time is
1,484.628365599 s; worker measured wall time is 1,630.261437620 s; complete
controller transaction time is 1,633.577485841 s. These scopes differ from Slurm's
allocation totals. Supporting allocations are separate, not hidden in this debit.
The audit's measured analysis CPU is 68.131072130 s. No GPU work was needed.

## Evidence and verification boundary

Program: `4a22292c903b4817629bd43449dcf6f22c827f7c31c9e525fcb3fdcca448e835`.
Completion: `2c80712913d314aa88d5abede08f324e8a773b9ffb847b58a9b721e7301c731c`.
Cluster audit: `286a2c74b676e55ff4d463d31545ca8138eb7dce36e515112fb697575a89f6e6`.
Candidate target: `3853008973e0a89db5c80d73d30cb4304bc5d9c89fafa80e6f7f15de232a1245`.
Candidate model: `904d2dc59a22b28d74db20b388bc1acc5d7566150441d65a7318a5d896271192`
(21,233,664 packed bytes; remains on the cluster).

`campaigns/csis_terminal_v59_metadata_20261014.tar.gz` contains 100 copied
metadata files plus a collection manifest, 538,971 bytes, SHA256
`aecceb538d03b798f11c914c672b6daac86eaab3eac60dc72434544d823084f3`.
The capture is terminal and includes logs, scheduler accounting, software checks,
registration, targets, stage metadata, all 40 losses, 69 progress records, sealed
worker receipts, the settled ledger and actual-artifact audit.

The portable checker passed: 100 copied files, 412 frozen sources, complete
530-entry audit inventory and 525 available bound inputs verified. Five uncopied
numerical binaries are explicitly NOT revalidated locally; no metadata is missing.
The cluster auditor inspected actual packed model codes and grids. Neither audit
independently repeats neural inference or calibration. Trusted execution/storage
and the pinned numerical implementation remain assumptions.

After extracting the archive into a fresh directory, run from the full checkout:

```sh
python3 -B validation/check_v59_metadata.py /path/to/extracted-v59
```

It reads the committed V58 metadata archive for prior receipts. The final report
is `validation/v59_terminal_metadata_check.json`. Six focused checker fixtures
pass, and isolated mutations of actual copied receipts are rejected even after
their collection hashes are refreshed. These are reader tests, not new model work.

## Research decision and next work

The quality screen supports further investigation of this distinct source-local
target. **It does not establish a new repair service.** V59 exports a model only;
it declares no canonical successor state, compressed evidence, source-deletion
operation, or matched service cost. Do not transfer V54's storage, timing or state
equality results to this target, or interpret the tiny pooled quality difference
as established superiority.

The next concrete gate is a versioned full-precision-teacher state/service
contract, preserving the frozen nearest-specific validators. Existing
`research_v42.resource_plan.BoundTarget`, `research_v53.state` and its parser,
and `research_v53.service` enforce the nearest target; simply replacing matrices
or relabelling a target is invalid. Source locality can support the same
conditional correctness arguments, but a new service must actually implement
the required provenance, containment, canonical descriptors/Grams and deletion
lineage before those state claims apply.

Prepare and review new source-local evidence for the 13-record root and both
successors, then newly admit the complete workload, memory, fallback and CPU
costs before registering any run. Compare actual complete model bytes and
representation-specific successor states with fresh retained-input reconstruction,
and measure cached, cold, hybrid and compressed controls with preparation,
serialization, failures and replay included. Freeze a useful method before
untouched quality, independent roots/checkpoints and prospective repetitions.
No successor source, registration, budget or launcher is admitted by this report.
Never rerun V59 or alter its ledgers, thresholds, inputs or numerical sources.

The existing open LaTeX source was updated in place, duplicate archival prose was
shortened, and native compilation passed. Its repository snapshot is
`reports/manuscript_v60.tex`; visual layout has not been independently reviewed.
The evidence package is a research handoff, **not an ACL submission bundle**.
The SANW2 reviews concern another manuscript and remain separate.
