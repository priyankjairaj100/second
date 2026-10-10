# Exposed quality diagnostic: V44

The one-use diagnostic completed and both prospective development guards passed. Fixed-anchor perplexity is 1.70556% higher than matched sequential calibration on this eight-article pool. This is a tolerance pass, not superiority, untouched confirmation, or ACL readiness.

## Identity and scope

Source commit: `db95069b2c3484ac615052fb1c1a711c8c773c2d`. Program SHA-256: `e3d7b6dfd1ad9199a180aac2e706ef8b2334c709947b2b8b6e90e4a81dc3e02c`. Registration job 13214; numerical job 13215, both completed with exit 0. The actual audited V43 final model has 32 retained calibration tokens, original normalization 96, ridge 1/100, dyadic row grids with 24 significant bits, four-bit codes, and all 24 calibrated affine stages / 42,467,328 code indices. Its model SHA-256 is `941edda96b1bec3a30bb467f39641bd44fa1dd03752f71ed6b3c4549867e9ae0`.

The matched sequential model uses the same retained tokens, checkpoint, grids, order, lower midpoint ties and normalization, but features depend on sequentially quantized predecessors. It is a distinct calibration target; this quality comparison does not establish a sequential repair speedup. Its packed export SHA-256 is `9b2b3cc21d4e6db822aff61ab86881b95d1b511e6d8f6e5273aae5d1ab2baab4`.

The evaluator is the unchanged ordinary NumPy binary64 implementation, not certified finite inference. All sixteen full-precision and nearest-rounding historical article losses passed the preregistered absolute mean-NLL tolerance 1e-8 before any new model loss was evaluated. Maximum deviation: 5.37103170338e-15. The evaluator SHA-256 is `db1253faa8a7d99fc2edf63405d6efe493e8e1a5783f3b4b1c6d970e88137d0d`. The `gelu_new` route uses NumPy tanh; the registered absence of optional SciPy does not change this numerical route.

All eight 128-token WikiText validation articles were already exposed in V30. There are 127 next-token predictions per article, 1,016 per model. All sixty historical exclusions remain bound and preserved; no new quality inputs were consumed. No article was replaced, no confidence interval is claimed, and no threshold was revised after outcomes.

## Complete descriptive results

| Model | Summed NLL | Mean NLL | Perplexity |
| --- | ---: | ---: | ---: |
| fixed_feature | 4047.449143296 | 3.983709787 | 53.715939730 |
| full_precision | 3881.028047691 | 3.819909496 | 45.600081133 |
| nearest_rounding | 4239.147095733 | 4.172388874 | 64.870233956 |
| sequential | 4030.266768828 | 3.966798001 | 52.815145745 |

Fixed/sequential pooled perplexity ratio: **1.017055599718**, below the frozen 1.05 guard. Worst article ratio: **1.053211385860**, below the frozen 1.20 guard. Fixed is worse on six articles and better on two. Fixed/full-precision ratio is 1.177979039; this 17.8% gap remains material. Fixed/nearest-rounding ratio is 0.828052197. These are observed ratios on this exposed pool.

| WikiText validation article row | Fixed/sequential perplexity ratio |
| --- | ---: |
| 1040 | 1.052425591 |
| 1299 | 1.039124171 |
| 132 | 1.053211386 |
| 2115 | 1.004874872 |
| 2237 | 1.005618421 |
| 2352 | 1.009731637 |
| 2525 | 0.986799632 |
| 3636 | 0.987195168 |

## Resource and failure history

The worker took 92.767495 seconds; the complete controller transaction took 94.105768 seconds. Matched sequential construction took 44.008997 seconds inside that worker. Peak RSS was 2,289,192 KiB. The fresh 1,202-CPU-second phase charged **94 CPU seconds**, with its sole reservation settled. This is separate from V43's 1,744 CPU seconds, which includes the preserved failed preparation. No allowance is transferred or reset. Setup, registration, software checks, read-only audits, and controller CPU are outside empirical worker charges.

Initial registration job 13211 failed while fingerprinting an absent SciPy package, before creating a campaign, reserving budget, or evaluating losses. Its dependent 13212 was cancelled. Source `db95069` records optional absence and rejects any missing required package or broken internal dependency. Software job 13213 passed nine tests; fresh registration 13214 and worker 13215 completed. The failed log and cancelled status remain published. No numerical retry occurred.

Actual sequential model bytes are retained locally and on the cluster under `local_runs/exposed-quality-v44-20261010-b/`. GitHub publishes `campaigns/csis_exposed_quality_v44/` text receipts, raw per-article losses, targets, model metadata, progress, ledger, and hashes, plus `validation/v44_local_archive.json`. That local check rehashed all seven output artifacts, six sealed worker artifacts, 13 bound inputs, and 316 registered source files; it recomputed summaries without repeating inference. Hashes alone do not restore a missing binary.

## Decision

The current 32-token endpoint clears the narrow exposed-data diagnostic. Proceeding to a larger independent full-model development root is scientifically reasonable, but requires a new reviewed resource admission and registration. Useful-scale performance, another actual checkpoint, stronger lossless compression controls, repeated randomized deletion sequences, mechanism ablations, and untouched quality on a frozen candidate remain open. Read `NEXT_SCIENTIFIC_GATES_V43.md` for the proposed designs. No further empirical worker is registered or active at this handoff.
