# Active continuation V51 — real wide-stage gate running

Updated 11 October 2026. This supersedes V50's next-action status. V45 remains a terminal CPU-limit failure; V49/V50 remain completed engineering diagnostics. Read this checkpoint before historical execution instructions.

## Current allocation and frozen identity

Slurm software job **13275 completed**, with **10 tests passing and zero skips** in the pinned Linux runtime. The tests include all prefixes versus a complete two-block feature traversal, foreign-context rejection, exact stopping/closure, durable command admission, and the existing V50 kernel bit/exception, interval and oracle comparisons. Mac admission fixtures also passed; Linux-only fixtures were deliberately skipped there and then executed on the cluster.

Slurm **13276 is running** on `csis.mn1`, under the one-use source commit `2c1a2bc699e4633bdab7243bb9e042be2f884c83`. Registered program SHA-256:
`af83f983447e022a5e5b386ddf60eb62db804db57dbd652212eab51fe9b7d10b`.

The authoritative run directory is `/nfs_home/users/poonam/second-20261010/local_runs/real-wide-stage-v51-20261011-a`. Its controller runs preparation, optimized point, historical point, then optimized compressed input in that fixed order. A worker failure stops the controller; there are no queued replacement trials, retries or automatic cap increases. The outer allocation has no requeue and a 125-minute ceiling. Do not submit another copy, call execute again, or run workers directly.

At the latest inspected progress, context loaded with the unchanged V45 target digest `908d7b60579a0197d775a4672f8c07c0aec9d9c870b1452f73a05c27a5a2f855`. The first registered record's wide-stage features matched a complete 24-stage traversal by actual bytes. Three records had finished preparation at that inspection. This is progress only: no complete stage result or gate success is yet verified.

## What the gate measures

This fresh gate uses the exact existing V45 root: thirteen known C4 development records, 128 tokens each, original normalization1664, unchanged checkpoint, ridge1/100, four-bit dyadic24 row grids and lower midpoint ties. It selects the first width3072 stage, `block.0000.mlp_down`, prospectively and checks all **2,359,296 codes**. No new quality data or empirical root was selected.

The new prefix wrapper advances the unchanged ordered feature generator through its first four yields with the same fixed anchor matrices, then closes it. It preserves the original feature target but has its own preparation source binding. The first real record additionally receives a complete traversal to verify its actual target-stage bytes. Source preparation validates every compressed enclosure and every lossless reconstruction.

The optimized point and compressed-box workers share V50's exact normal-neighbor kernel. Historical point isolates the kernel implementation change. The wide-stage hybrid control already uses lossless factors, so its relevant route is the optimized point arm; the native Gram limit remains width768. No wide Gram admission has been invented. A box refusal stops this diagnostic without hidden neural replay or point retry.

All three new complete packed code tensors must agree by actual bytes and match the preserved V45 stage hash `91b450c2c1547e40b6533005e8245fbdb6d1c4c34af889efab5fbf1e214eea5a`. Historical V45 code bytes were not retained: that part of the comparison is commitment-only. Fresh comparisons use complete new bytes.

One CPU/thread, 16GiB Slurm allocation and process address-space cap, 1GiB per-file limit. Fixed worker CPU/wall limits are prepare900/1200, candidate1200/1800, reference1800/2400 and compressed1200/1800 seconds. Separate phase reservations total5108 CPU seconds, including each worker's two-second rounding allowance. Controller/container/checking overhead is visible in Slurm accounting and is outside worker phase charges. These limits are prospective feasibility probes; they do not predict completion or expand V45's failed allowance.

## Evidence and resume

`campaigns/csis_wide_stage_v51_launch` preserves the launch snapshot, including the pending preparation reservation. It is deliberately a historical launch snapshot, not a terminal ledger. `validation/v51_launch_checks.json` verifies 346 frozen source hashes and records that the offline auditor correctly refuses a still-running gate. Subsequent terminal receipts must be copied into a separate terminal evidence archive.

Use one fresh read-only status check on the existing allocation:

```sh
sacct -n -P -j 13275,13276 --format=JobIDRaw,State,ExitCode,Elapsed,TotalCPU,MaxRSS
squeue -j 13276
```

Inspect progress, controller/worker logs and `gate.json` if present. A scheduler COMPLETED state alone does not establish numerical success. If still running, preserve the allocation and inspect only at useful phase changes. If access fails, stop bounded retries and leave the outcome unknown. Never infer a completed result or submit a duplicate.

Once terminal, copy the complete small stage archive (including descriptors, weights and all code binaries) to the fresh local checkout, retaining this launch snapshot. Copy terminal accounting using `JobIDRaw,State,ExitCode` in that exact order. Then run the read-only auditor:

```sh
.venv/bin/python -B -m research_v51_postrun.audit \
  local_runs/real-wide-stage-v51-20261011-a \
  PATH_TO_TERMINAL_ACCOUNTING OUTPUT_JSON
```

The auditor rejects pending/missing receipts, altered sources/inputs, missing binaries, unsettled charges, unexpected follow-on work and mismatched complete codes. It supports sealed worker failure without promoting partial progress. A controller-only failure may need a separate audit; do not rewrite its evidence to make this auditor pass. Save all failure charges and partial outputs.

The frozen implementation is in `research_v51`; read `PROTOCOL.txt`. The postrun auditor is additive and is outside the frozen numerical source set. Do not edit the frozen source during this job. Documentation-only publication does not alter the registered numerical source. No scheduled monitor was created.

## Publication boundary and next work

Passing this gate would establish feasibility and code agreement for one known development stage under these limits. It does not establish a full model, deletion-state equivalence, realistic service latency, quality, exact GPU feature evaluation, randomized speed advantage or ACL readiness. Do not extrapolate full-model runtime by multiplying a stage time. The earlier V43 latency loss versus the lossless cache, V45 failure and all60 quality exclusions remain intact.

No full-model recovery is registered. First inspect the terminal gate; only then review a separate prospective full-model experiment with shared optimization in every relevant arm, fixed target/membership, actual source/fallback costs, full canonical states and independent fresh comparisons. Further paper work still includes actual larger-model quality, a second checkpoint, stronger codec controls, ablations, repeated roots/deletions, untouched evaluation and novelty.

The existing editor master `outputs/second-research-draft.tex` remains unchanged, with repository snapshot `reports/manuscript_v50.tex`; its latest built-in compilation succeeded. Visual layout remains unverified. Engineering launch progress is not inserted as a paper result. The existing V47 GPU likelihood validation remains valid, and its parameter archive remains verified locally and on the cluster. Exact CPU feature generation is still required for this gate.
