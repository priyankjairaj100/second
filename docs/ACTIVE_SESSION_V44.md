# Active session V44: local and cluster continuation

Updated 10 October 2026. The local/cluster setup, complete V43 integration pilot, both byte audits, and V44 exposed quality diagnostic are complete. All new empirical reservations are settled; no worker remains active and no further empirical campaign is registered. The broader research program and ACL submission remain incomplete.

## Start here

The authoritative starting point was GitHub main `fbcc98c6559de4b88ffc9c8b960cf680d89e29d3` and ChatGPT chat **second**. The fresh checkout is `/Users/priyankjairaj/Downloads/ACL/Second`; the cluster checkout is `/nfs_home/users/poonam/second-20261010`. Continue on `codex/second-cluster-v42`. The old local `Two` folder and old remote `acl2027-second` were not used for continuation.

Read `COMPLETE_SERVICE_RESULTS_V43.md`, `EXPOSED_QUALITY_RESULTS_V44.md`, `LITERATURE_UPDATE_V43.md`, and machine-readable `../handoff/program_v44.json`. The current working manuscript is `../reports/manuscript_v44.tex`. Historical handoffs remain historical; this file supersedes their current-status statements.

## What is now established

V43 exercises two actual complete-model successors: 96 original tokens, then 64 and 32 retained. All four arms' eight model exports and canonical states match fresh retained-token execution across 24 affine stages and 42,467,328 codes. Both actual-payload audits pass; the supplemental audit binds exported codes, registered records, execution targets, sealed receipts and recomputed byte accounting. All 48 compressed certificates accept without replay or fallback. The fresh oracle shares numerical and codec implementations; these are not independent mathematical implementations or remote attestation.

Compression saves 9.40% / 5.83% of live state but only 0.905% / 0.462% of deployment bytes including the checkpoint. It is 1.79x / 1.60x slower than cached requests. Attributed preparation plus transaction is 34.1% higher than cached and 1.5% higher than cold; attribution is not an independently measured standalone lifetime. Preserve these adverse findings. The hybrid Gram control loses badly at this tiny scale; historical first-stage V40 Gram wins at 1,536 retained tokens remain relevant.

V44 evaluates the actual final model against a newly generated matched sequential model and unchanged full-precision/nearest controls on eight already exposed articles. All sixteen historical parity checks pass. Fixed PPL 53.715940 versus sequential 52.815146 gives ratio 1.0170556; worst article ratio 1.0532114. Both preset guards pass (1.05 pooled, 1.20 every article), while fixed loses to sequential on six of eight articles and retains a 17.8% full-precision PPL gap. This is diagnostic tolerance evidence only; no untouched article or confidence interval was added.

## Runtime, receipts and failures

Exact experiments run through Slurm on `csis.mn1` in the SHA-pinned Bookworm image, CPython 3.12.14, NumPy 2.3.5, gmpy2 2.3.2, one CPU/thread and 16 GiB caps. See `../cluster_setup/README.md`. A100 access was verified by synthetic smoke job 13149. No GPU arithmetic replaced the exact CPU target; GPU quality needs a separate parity gate. Local Mac fixtures do not reproduce the Linux numerical contract.

V43 numerical source is `304a9cc`; primary audit job 13206 and supplemental job 13210 passed. The empirical charge is 1,744 CPU seconds, including failed preparation job 13197 (24 seconds). Failed software jobs 13193 (node user resolution) and 13207 (NFS metadata drift) are preserved; dependent 13208 was cancelled. Supplemental source `38ff2ae` uses actual final content rehashing.

V44 source is `db95069b2c3484ac615052fb1c1a711c8c773c2d`. First registration 13211 failed before creating a campaign or evaluating a loss because it required absent, unused SciPy; dependent 13212 was cancelled. The fixed runtime fingerprint records optional absence without changing the pinned NumPy `gelu_new` evaluator. Nine Linux software tests passed in 13213, fresh registration 13214 succeeded, and worker 13215 completed. Its fresh ledger charged 94 CPU seconds and is settled. Setup, tests, registration, audits and controller CPU remain outside empirical worker charges. Total new empirical charge across V43 and V44 is 1,838 CPU seconds.

Read `../campaigns/csis_continuation_v44/slurm-terminal-accounting.txt` and its software logs. Each registered run preserves its own source hash and runtime identity. Do not reset ledgers, reinterpret cancelled jobs as evaluated results, or reuse unused allowance.

## Actual artifact locations and continuation

The fresh local and cluster checkouts both retain `local_runs/full-model-v43-20261010-b/` (1,269,053,685 binary bytes) and `local_runs/exposed-quality-v44-20261010-b/` (21,233,664 sequential model bytes). The failed A receipts remain in `campaigns/csis_v43_attempt_a/`. Published text evidence lives in `campaigns/csis_full_model_v43/` and `campaigns/csis_exposed_quality_v44/`; local-copy audits are in `validation/v43_local_archive.json` and `validation/v44_local_archive.json`. Hash-only clones do not recreate missing binaries. No credentials are stored in repository files.

Do not rerun completed one-use campaign commands. New numerical work must use a fresh program, directory, runtime/source identity, admission and bounded ledger. Review the proposed larger-root resource design before requesting compute. Preserve `src/*.py`, historical `scripts/run_*.py`, source membership, all sixty exclusions, failures and negative findings. The current method repairs calibration membership for fixed source-local nearest-anchor features; it does not remove pretraining data or reproduce ordinary sequential GPTQ repair.

## Remaining scientific gates

1. review and register an independent full-model 1664 -> 1536 -> 768 token sequence.
2. execute actual second-checkpoint repair with complete byte audits.
3. strong lossless codec controls and certificate/replay ablations.
4. randomized repeated roots and longer deletion sequences.
5. prospective untouched quality on frozen useful models.
6. independent proof/novelty review and submission-format manuscript revision.

The candidate contribution is exact adaptive code recovery from uncertain compressed evidence with canonical successor-state accounting. Fixed features, cached statistics, stability, and certificate-gated decisions alone are not new. The Exact-Fun primary proof gap is closed, and ExecCert's finite-codebook overlap is acknowledged. No useful-scale or ACL-readiness claim follows from the current tiny development run.

## Manuscript preview status

The saved standalone source was submitted to the built-in Codex LaTeX compiler. Compilation timed out while fetching `amsbsy.sty`: the package relay had network/DNS failures. The source is preserved; successful compilation, rendered layout inspection, and PDF export are unverified. This infrastructure failure does not change empirical results. See `../validation/manuscript_compile_v44.json`.
