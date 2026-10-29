# Verified GPU likelihood evaluator: V47

All 32 matched per-article mean-NLL comparisons pass the frozen 1e-8 absolute tolerance. Maximum deviation is 1.208482133261273e-14. The first actual full-precision batch passed before further inference. This establishes observed evaluator agreement on the existing V44 pilot, not new quality evidence or exact GPU calibration.

The experiment uses all four V44 models and the same eight exposed128-token articles: full precision, nearest rounding, actual V43 final fixed model, and V44 sequential comparator. All 60 historical quality exclusions remain intact. No heldout data, revised threshold or replacement model was used.

The unchanged eager TorchQualityDecoder uses float64, explicit causal attention and gelu_new, deterministic algorithms, CUBLAS4096:8, and no TF32/AMP. All 150 host/device/host parameter transfers preserve binary64 words. GPU: NVIDIA A100 80GB PCIe; PyTorch 2.10.0+cu128; Python 3.10.19; CUDA build 12.8. Peak CUDA allocated/reserved bytes: 1494948864 / 1562378240. Host worker peak RSS: 2938036 KiB. These are observations under the 16 GiB Slurm host cap and 8 GiB GPU allocator cap. The 128 TiB address-space allowance permits CUDA virtual mappings and is not a RAM allowance.

The CPU decoder remains in the SHA-pinned Python 3.12.14 container. It exported 78 arrays with per-array shape/type/word commitments, verified by full readback. No inference ran during export. Parameter archive: 964501350 bytes, SHA256 `c5cc19cde2e526bb3098efaec5c7709ac3714bd781f8753c1c5b77f6c4a67f2b`. Its declared physical storage is additional engineering-evaluator data, separate from V43/V45 deployment state accounting. The archive remains on the cluster at `local_runs/cpu-parameters-v47-20261010-a/outputs/parameters.npz`; it was not copied locally or included in GitHub/ZIP.

Frozen source: `c811decaedc5648aed099d445d9a247f5875c17c`. CPU export program: `1803adfd4b9548a605dc468a7c982d077abaaa43f36df6bfce8c4098a7170915`. GPU program: `620076c67ae79ee56de784ecd4c6e49ef3b4b22f45742f72956821b1e416cf54`. Completed export 13247 charged 19 CPU seconds; completed GPU 13250 charged 22. Both fresh ledgers are settled. The GPU worker clock is 16.898786s including 10.013671s context; Slurm elapsed27s also includes validation/controller overhead. These are single engineering observations, not a controlled CPU/GPU speed ratio or token-use measurement.

## Preserved failures and software checks

V46 registration 13240 failed before any campaign or reservation because GPU Python 3.10 lacks hashlib.file_digest. Its dependent 13241 was cancelled. V46-local streamed hashing fixed the compatibility issue; no old CPU source was changed. The next registered V46 attempt 13244 failed before any likelihood when the certified CPU loader could not identify its loaded libm on the GPU host. Its22 CPU-second charge is settled and preserved in `../campaigns/csis_cuda_failure_v46/`. The guard was not bypassed. V47 instead imports exact CPU-exported arrays into a separate ordinary numerical evaluator.

GPU tests 13239 passed 7 tests; corrected GPU tests 13242 passed 8. CPU export software 13245 passed 2 and skipped the cluster-archive check scheduled for later. After export, GPU software 13248 passed 11 tests including actual archive validation, causal masking, corrupted-commitment rejection and full synthetic decoder batches on CUDA. All software/registration and controller CPU are outside empirical worker charges. Additional worker charge across failedV46 and successfulV47 is 63 CPU seconds. Prior allowances are not recycled.

## Evidence and limits

The copied-evidence audit `../validation/v47_local_archive.json` rehashes 304 registered sources, 13 locally copied bound inputs and 13 inherited V44 inputs, verifies 18 sealed worker artifacts across failed/export/GPU attempts, and recomputes all 32 deviations from reported raw losses. It checks all 32 progress records and settled charges. The remote-only NPZ is explicitly not rehashed locally; CPU export and GPU worker report all array-word checks. No independent inference, hostile-host attestation or portable universal equality is claimed.

Published text receipts are in `../campaigns/csis_cpu_parameter_export_v47/`, `../campaigns/csis_cuda_parity_v47/`, and `../campaigns/csis_continuation_v47/`. The manuscript source compiles successfully in the built-in editor; visual layout review and separate PDF export are not completed.
