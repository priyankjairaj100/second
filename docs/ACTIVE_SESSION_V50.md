# Active session V50: cluster restored; exact-kernel software optimization verified

Updated 11 October 2026. This supersedes V48's unavailable/unknown status. Continue from the GitHub/ChatGPT handoff in the fresh `/Users/priyankjairaj/Downloads/ACL/Second` checkout, branch `codex/second-cluster-v42`. Do not use the old Two or acl2027-second folders.

## Connection and GPU

The user restored access. A password-only connection succeeded and established `/tmp/second-csis-01a12469.sock`; reuse it while it exists, and stop after a new connection failure. No password is saved. The cluster checkout remains `/nfs_home/users/poonam/second-20261010`.

Fresh Slurm job 13271 passed a synthetic CUDA check on an NVIDIA A100 80GB PCIe, PyTorch 2.10.0+cu128. This establishes current device/runtime access, not research-target equivalence. The earlier V47 evaluator validation remains the evidence for all 32 exposed CPU/GPU likelihood comparisons, with maximum mean-NLL deviation 1.2084821332612728e-14. Exact calibration/certification still uses the pinned CPU runtime.

The complete V47 parameter archive is now backed up locally: 964,501,350 bytes, SHA-256 `c5cc19cde2e526bb3098efaec5c7709ac3714bd781f8753c1c5b77f6c4a67f2b`. Every one of its 78 binary64 arrays was checked using the unchanged snapshot loader. Read `validation/v49_gpu_backup_audit.json`. This is a verified binary backup without new inference; the NPZ remains excluded from GitHub and the output ZIP. It resides at `local_runs/cpu-parameters-v47-20261010-a/outputs/parameters.npz` in both fresh checkouts.

## Terminal V45 failure

Original job 13228 failed at the frozen 4,800 CPU-second limit. Its sealed observation is 4,800.713602 CPU seconds; the charged debit is 4,801, settled within the 4,802-second reservation. Jobs 13229–13235 were cancelled by dependencies and did no worker execution. The original 26,412-second model-phase ceiling was not increased or reused. The separate data phase remains complete with 15 charged CPU seconds.

All 13 source extractions finished. Progress recorded 11 of 24 certified stages; the last was block.0002.mlp_up. The two completed width-3,072 MLP-down stages took 1,217.75 and 1,222.92 seconds. These are partial progress records. There is no complete original model, no deletion result and no final artifact audit. No target exactness/quality or compression benefit may be inferred for the larger run.

The copied failure audit verified all 325 frozen source hashes, sealed receipt artifacts, scheduler outcomes and the settled ledger. Evidence is in `campaigns/csis_full_model_v45_failure`; read `validation/v49_v45_failure_audit.json`. The frozen program remains `02c7f6cfc0240bc34f2a5faec05dfb5392b81d12e5ac4cd95279167ef99c6d50`; its original directory and all partial artifacts are preserved. This is a known terminal failure, replacing the previous unknown status.

## Completed V49 diagnosis

Frozen source `9b20c1ea9e4bed1e4a908409f87bbc8c8deaa16c`. Program `5235ba0681eb220f03b72c84a57e8070a7bdd36484d8dccd8472bea807f6de9b`. Jobs 13265 software, 13266 registration and 13267 profile all completed. Sixteen Linux tests passed. The fresh software-profile ledger charged 124 CPU seconds and is settled.

The fixed synthetic cases use widths 192/768/1,536, four output rows, 128 tokens, normalization 1,664 and ridge 1/100. At width 1,536, coefficient certification accounted for 98.845 of 106.613 seconds (92.7%). This is not a measured breakdown of V45's actual model stage. No model, calibration record or quality article was used. Read `research_v49/PROTOCOL.txt`, `campaigns/csis_synthetic_profile_v49` and `validation/v49_profile_audit.json`.

## Completed V50 software optimization

Frozen source `e33181213e1ff6d23a137669978bf89c70a9aaae`. Program `8b732267fefab478296300837f26e475782c780afdfe2e15104633c9d7d3db95`. Jobs 13268 software, 13269 registration and 13270 profile all completed. The new profile charged 68 CPU seconds from its separate 602-second phase and is settled. No earlier grant was reset.

The separately compiled primal kernel computes adjacent ordinary normal binary64 values by integer word steps. Zeros, subnormals, boundary normals, infinities and NaNs retain the original nextafter call. Arithmetic order, products, interval widths, grids and targets remain unchanged. The new adapter operates only in a dedicated single-thread process, restores the old kernel even on exceptions, and does not edit historical sources. Its representation argument, gates and limitations are in `research_v50/PROTOCOL.txt`.

All 18 Linux checks passed, including 2,032,770 direction comparisons over fixed random/boundary words with both result bits and floating exception flags checked, identical Gram endpoints and coefficient centers/radii on point/box fixtures, an exact rational-code oracle, and restoration/nesting checks. These are finite tests under the supported runtime, not exhaustive enumeration of all bit patterns.

All three larger synthetic fixture/code hashes match V49. Observed complete case times are 1.099 -> 0.313 seconds at width 192, 15.314 -> 7.035 at width 768 and 106.613 -> 58.832 at width 1,536. The baseline ran earlier, and cache/time effects are uncontrolled. First-case compilation placement differs; both complete worker charges include setup. These are engineering observations, not randomized comparisons, confidence intervals, a measured width-3,072 improvement or a complete-model speedup. Read `validation/v50_profile_audit.json` and `campaigns/csis_neighbor_profile_v50`.

## Next gate

No full-model recovery has been registered or launched. Do not rerun V45, the completed V49/V50 directories, or their controllers. The next useful check is a fresh, bounded real width-3,072 stage feasibility test using the unchanged known development root and fixed numerical target. It must bind actual source extraction, the new backend, complete stage codes, all relevant point/box/Gram controls, memory/CPU use and preserved V45 code-prefix commitments. Inspect supported stage-input APIs and review resource/accounting scope before registration. The synthetic profile cannot supply that admission or replace actual timing. Do not infer a full-model runtime by multiplying one stage time.

Only after that gate should a complete changing-state campaign be prospectively registered. All controls must receive the same shared kernel optimization and equivalent source access. Original normalization, requested membership, quality exclusions and failed outcomes remain fixed. A later campaign has a new identity and prospective resource review; it must not rewrite a failed run or silently relax its limits.

The paper still needs completed useful-scale results and actual-model quality, a second checkpoint, stronger codec controls, certificate/replay ablations, repeated randomized roots/deletion sequences, untouched quality endpoints and a defensible novelty contribution. Preserve all 60 historical quality exclusions. The target remains fixed-anchor calibration membership, not pretraining unlearning, ordinary sequential GPTQ repair or physical erasure.

## Manuscript and continuation

The existing Codex editor file `outputs/second-research-draft.tex` remains the editable master. `reports/manuscript_v50.tex` is its repository snapshot. It now records the larger-run failure and the verified local GPU archive. Built-in compilation succeeds; visual layout review remains unverified. The kernel microprofile is kept in the engineering handoff rather than promoted to a paper result.

All jobs from this continuation are terminal. No scheduled monitor was created. Check actual account resources before another allocation, and preserve unrelated projects' jobs. Published/local/remote commit state is recorded in the accompanying output status; numerical V50 source remains e331812 even when documentation advances.
