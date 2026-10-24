# Active continuation V54 — full-model campaign running

Updated 11 October 2026. Snapshot cutoff: 2026-10-11T10:41:56.714729+00:00. This supersedes V52's no-active-job status. User asked to continue and finish the remaining program; the complete-model pipeline now runs through dependent Slurm jobs without another prompt. This is ongoing work, not paper completion.

## Active execution

Frozen source: `9826a9522e1586206766e3ba1f85fd1b415dd03e`. Program: `03a6181b0d32ad023706145fbde28f202ed5d137e95a4b16ecbd19686858465b`.
Directory: `/nfs_home/users/poonam/second-20261010/local_runs/full-model48-v54-20261011-a`.

- 13308: all 76 Linux software checks passed, no skips; original archive/data admission passed.
- 13309: registration completed.
- 13310: preparation running; first full source traversal recorded at this cutoff.
- 13311: cached control; 13312: cold control; 13313: hybrid native-Gram control; 13314: compressed48.
- 13315: independent fresh retained-token oracle; 13316: primary byte audit; 13317: supplemental byte/accounting audit.

All dependent jobs are pending behind the preceding success. No requeue or automatic retry. Do not rerun either one-use launcher or register duplicate experiments. Check actual scheduler status and artifacts before interpreting these snapshot states. A running worker's CPU reservation is not a settled measured charge.

The fixed comparison order is prepare,cached,cold,hybrid,compressed,oracle. Original normalization 1664, 13 C4 sources x 128 tokens, retained 12 then 6, ridge 1/100, original four-bit grids and fixed nearest-anchor features remain unchanged. All arms use the shared V50 optimized primal kernel where dispatched. The state has an explicit V53 schema with uniform compressed48/block256; old compressed40 validation remains frozen and rejects 48.

The new worker phase cap is 81,012 CPU seconds, separate from old allowances: prepare 10800/14400 CPU/wall; cached 10800/14400; cold 12600/16200; hybrid 14400/18000; compressed 18000/21600; oracle 14400/18000. One CPU/thread, 16 GiB address-space, 2 GiB file cap. These larger prospective resource limits do not erase V45's failed 4800-second attempt, predict runtime, or establish a speedup. Both canonical state and model codes must match independent fresh reconstruction at both deletions; all replay, preparation and state/trust/checkpoint bytes are counted.

## Preserved launch failure and correction

V53's 70 software checks passed, but registration 13299 failed before a program, numerical directory, worker or numerical budget existed. All eight downstream jobs 13300--13307 were cancelled without numerical execution. Registration scheduler CPU was 1.979 s, separate from worker budgets. Metadata/log/accounting: `campaigns/csis_full_model_v53_admission_failure`; audit: `validation/v53_admission_failure_audit.json`.

The old data-phase verifier compared the original entire live history inventory against today's expanded inventory. The correction imports the unchanged V53 numeric/state/service implementation and verifies every one of the 264 original entries, exact V45 program, selection, runtime, sources, exclusions, both acquired prefixes and sealed settled debit. It explicitly records 25 added experiment metadata files. There is no data reselection, claimed new independence or relaxed numerical test. V54 adds six software fixtures and validates real archive admission before registration. The failed V53 sources and launch remain preserved.

V54 launch metadata: `campaigns/csis_full_model48_v54_launch`; independent local source/registration review: `validation/v54_launch_audit.json`. This is a launch snapshot, not terminal evidence. 386 source bindings match locally. New full numerical artifacts stay on the 15 TiB-free cluster; the Mac had 4.3 GiB free at setup, so do not blindly copy a multi-GiB archive. Retrieve/hash text receipts first, then plan binary transfer against actual disk availability. This does not change the remote audit's requirement to compare real binary outputs.

## Research boundary and next action

V51's 40-bit gate remains a certificate refusal. V52's 48-bit result remains adaptive single-stage engineering evidence: 2,359,296 matching codes, 9.03% descriptor saving, 690 CPU seconds. V43 remains the tiny 96 -> 64 -> 32 full-model result, including worse latency than the indexed cache and below 1%deployment saving. V45 remains a CPU-limit failure. All 60 historical quality exclusions remain protected.

No V54 full model, successor equality result, service timing result or quality score exists at this cutoff. If the chain succeeds, inspect both audit receipts and actual terminal accounting, then prepare matched quality for the actual1664-normalization model. V44's norm 96 score cannot transfer. V47's GPU likelihood parity does not admit GPU replacement of exact feature generation. No new quality run, second checkpoint, stronger codec control, ablation or untouched confirmation is registered here. Those and a defensible novelty contribution remain necessary for an ACL paper.

Do not change frozen V53/V54 files while jobs run. Subsequent engineering must use a new version and fresh paths. Preserve all failures and costs. If SSH fails, stop bounded retries and retain unknown remote status instead of inferring completion or duplicating jobs. No unrelated account job was touched.

## Manuscript and publishing

The existing open `outputs/second-research-draft.tex` now distinguishes the integration/software result from pending numerical work, preserving old failures. Repository snapshot: `reports/manuscript_v54.tex`; built-in compilation succeeded. Layout remains unverified. No replacement document, separate PDF or new tab. Existing draft PR remains the single publication/handoff route. No scheduled monitor was created.
