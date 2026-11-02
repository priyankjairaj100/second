# Active session: full-model run with conditional CPU quality and GPU parity

Updated 11 October 2026. Read `handoff/program_v56.json` and `validation/v56_launch_audit.json`.
This supersedes the V54 handoff's statement that no quality continuation is prepared.
The earlier handoffs and all negative results keep their historical cutoffs.

## Current verified state

V54 program03a6181b0d32ad023706145fbde28f202ed5d137e95a4b16ecbd19686858465b remains active.
At 2026-10-11T11:07:39.877673+00:00, preparation13310 was RUNNING:13 source traversals and3/24
original stages had completed. Four controls13311--13314, fresh oracle13315 and
both complete-byte audits13316--13317 remain pending. The full numerical result is
unverified. All386 frozen V54 sources remain unchanged. Do not infer a final
model, quality or useful speedup from partial progress.

V55 source `792400b5518442baf57c1890f9ec01fd443b9382` passed all18 Linux fixtures, zero skips, job13324
(7.790 scheduler CPU seconds, separate from empirical ledgers). Tests compare
all miniature sequential feature words and packed model codes with the original
ordered constructor, preserve prefix/refusal/cleanup behavior, reject tampering,
validate actual complete synthetic packed model extents, and retain negative
quality outcomes. All399 source bindings match. The fresh actual-model
registration13325 is queued after13317, then quality13326 and audit13327.
No V55 program or numerical ledger exists at this cutoff: queued registration is
not executed registration. Never rerun `cluster_setup/v55_pipeline.sh`.

V56 source `5dcd24c29fa46fd012eaf49394b39693ff831e7a` passed all12 CUDA fixtures on an A100 with zero skips,
job13328 (7.668 scheduler CPU seconds). This covers miniature CUDA/NumPy logits,
causality, exact word transfers, tampering, all78 real parameter-array commitments
without actual-checkpoint inference, GPU-runtime imports, and accepting valid
negative CPU quality. NIS/RPC warnings remain in the log; the tests exited0.
All409 source bindings match. One GPU allocation13329 is queued after13327;
it registers, runs and audits once. It has not registered or evaluated new
models at this cutoff. Never rerun `cluster_setup/v56_pipeline.sh`.

## Gates and resource boundaries

V55 first requires BOTH V54 actual-model/state audits, all8 comparisons and settled
six-worker accounting. It reconstructs the actual compressed48 final successor
and uses the same original normalization1664 and retained6x128=768 tokens.
A fresh exact sequential comparator uses each preceding calibrated output with
the unchanged stage dispatcher and shared optimized primal kernel. Its target
remains different from fixed-anchor calibration and its time is not a repair
speed baseline. Four models use the shared ordinary NumPy float64 evaluator on
exactly the8 exposed V30 articles,1016 predictions/model. All16 old FP/nearest
losses must match at1e-8 mean NLL first. Keep pooled fixed/sequential<=1.05 and
every-article<=1.20 guards. A valid failed guard remains a result, not a retry.
New phase cap14402 CPU seconds; worker CPU14400/wall18000,1thread,16GiB,2GiBfile.

V56 admits a valid V55 result whether its quality guard passes or fails. It reuses
the verified V47 CPU parameter-word snapshot and unchanged Float64 CUDA evaluator,
compares all32 actual matched losses at1e-8 mean NLL, and checks150 word-preserving
array/prefix transfers. Exact GPU feature/calibration equivalence is not claimed.
Separate worker CPU cap1202; CPU1200/wall1500;1A10080GB,1CPU,16GiB physical host,
8GiB CUDA allocator;128TiB virtual-address ceiling is for CUDA mappings. No new
quality inputs, untouched confirmation, approximate calibration or paid compute.
Software/registration/audit costs are reported outside empirical worker budgets.

All chains use afterok dependencies, no requeue and cancellation on invalid
predecessors. Existing jobs proceed automatically; no recurring monitor was
created. Check status read-only before any continuation. Do not touch unrelated
cluster jobs. Source directories and old ledgers are frozen; add new versions
for future changes. A failed gate must keep its partial evidence and charged cost.

## Remaining scientific work

Actual full-model comparisons, CPU quality and new-model GPU parity are pending.
The V43 tiny-model negative service comparison, V45 CPU-limit failure, V51 40-bit
refusal and adaptive V52 single-stage48-bit success remain preserved. V44 quality
and V47 GPU results do not transfer to the larger model. No broad advantage,
confirmation or ACL readiness is established.

After these gates, assess what the complete evidence supports before registering
additional work: second-checkpoint transfer, stronger lossless codec controls,
matched ablations/lifetime accounting, independent calibration/deletion roots,
randomized repetitions and untouched article-level quality with prospectively
frozen endpoints. A strong paper still needs a defensible contribution beyond
engineering parity. Do not spend confirmation inputs to tune precision or gates.

The master remains the existing open `outputs/second-research-draft.tex` in the
Codex task workspace. Its committed snapshot is `reports/manuscript_v56.tex`.
Text receipts/launch metadata live in `campaigns/csis_quality_v55_launch` and
`campaigns/csis_gpu_v56_launch`. The new full numerical archives remain on the
cluster; local disk is limited, so do not copy multi-GiB state blindly.
