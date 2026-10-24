# Complete-model successive-deletion development results: V43

The frozen numerical campaign completed, and both artifact audits verified all eight comparisons across four arms and two successive deletions. The local archive check rehashed 57 copied declared artifacts and confirmed the eight model/state comparisons using the actual local payloads. Supplemental job 13210 additionally verified exported codes against parsed state codes, registered source provenance, execution bindings, sealed worker receipts, and storage accounting. Its receipt SHA-256 is `cd03e4c347464f13c39b528ea022313f2b3858c1ad8ca0bbff665cd5623aa99b`.

## Target and design

The numerical source commit is `304a9cc73b3c263032f3ef6a02487b4d2df40fbe`; the program SHA-256 is `e350109ae0771afcd9bb94abf6bf40a8082110a76c33bcaaf7e23922a107ce4d`.

The campaign uses one development root: the first 32 tokens from each of three previously exposed WikiText training articles, with original normalization 96 and ridge 1/100. The actual sequence is 96 → 64 → 32 tokens, deleting one complete identified record per request. Fixed nearest-grid anchors, dyadic row scales with 24 significant bits, four-bit codes, original normalization, finite ordered CPU features, and lower midpoint ties remain unchanged.

All 24 calibrated affine stages across DistilGPT2's six transformer blocks are covered, comprising 42,467,328 code indices. Other checkpoint components remain unchanged and are still required for deployment. Each packed model-code artifact contains 21,233,664 bytes. The target is fixed-anchor calibration; these results do not establish ordinary sequential GPTQ equivalence or pretraining-data unlearning.

The cached arm retains lossless source factors; the compressed arm uses 40-bit factor descriptors. The hybrid stores native exact Grams for 18 stages of input width 768 and lossless factors for six stages of input width 3,072. The cold arm reconstructs from retained tokens. A separate oracle also reexecutes retained tokens and builds fresh states for every representation. That oracle shares the solver and codec implementations, so it provides a fresh execution rather than an independent implementation of the mathematics.

## Verified observations

Every exported repaired model equals the corresponding fresh oracle export byte for byte, and every complete state equals its fresh counterpart within that representation. Both actual successors are exercised. All 48 compressed stage certificates accept, with no source replay or fallback. The hybrid arm replays the deleted source through all 24 stages per request to obtain its Gram contributions; this is part of its ordinary access cost, not certificate fallback.

The first deletion changes 2,774,109 code indices; the second changes 2,337,980. The local archive check counts unequal four-bit indices in the actual adjacent complete model files. Thus, both requests produce changed models.

| Arm | Retained tokens | Request seconds | Live state + trust bytes | State + trust + checkpoint bytes | Neural stage-record pairs |
| --- | ---: | ---: | ---: | ---: | ---: |
| cached | 64 | 36.161499 | 37,599,262 | 390,424,437 | 0 |
| cached | 32 | 25.545741 | 30,386,821 | 383,211,996 | 0 |
| compressed | 64 | 64.713257 | 34,065,453 | 386,890,628 | 0 |
| compressed | 32 | 40.959253 | 28,614,690 | 381,439,865 | 0 |
| hybrid | 64 | 403.979928 | 125,546,927 | 478,372,102 | 24 |
| hybrid | 32 | 397.421592 | 119,987,469 | 472,812,644 | 24 |
| cold | 64 | 86.999333 | 37,599,262 | 390,424,437 | 48 |
| cold | 32 | 49.927669 | 30,386,821 | 383,211,996 | 24 |

The shared configuration and checkpoint occupy 352,825,175 bytes. Runtime/system installation and audit archives are excluded from the deployment subtotal. Tokens, provenance, target manifests, and model codes are included in the state. Exported model files duplicate codes already embedded there and are counted separately only in audit history.

At 64 and 32 retained tokens, respectively, compression saves 9.3986% and 5.8319% of live state relative to the cached arm, and 0.9051% and 0.4624% of the declared deployment total. Compressed request times are 1.7896× and 1.6034× the cached request times. Compression is faster than cold reconstruction on both requests, but its attributed preparation plus measured transaction total is 1.0152× the cold total and 1.3413× the cached total. This accounting is defined below; it is not a separately measured standalone lifetime.

The hybrid Gram control is much slower and larger in this small-token setting. Historical V40 evidence for native Gram at 1,536 tokens concerned only the first affine stage. Neither result establishes general method dominance or a full-model scaling advantage.

## Preparation and observed sequence costs

| Arm | Attributed preparation seconds | Complete two-request transaction seconds | Attributed preparation + transaction seconds | Worker peak RSS KiB |
| --- | ---: | ---: | ---: | ---: |
| cached | 146.755561 | 90.453349 | 237.208910 | 963,152 |
| compressed | 184.107058 | 134.055168 | 318.162226 | 1,163,736 |
| hybrid | 186.595038 | 829.815719 | 1,016.410758 | 1,304,052 |
| cold | 146.755561 | 166.654198 | 313.409759 | 940,192 |

The shared preparation worker took 242.218920 seconds; its complete controller transaction took 243.353767 seconds. The separate fresh-oracle worker took 261.443517 seconds. Attributed preparation includes common context loading, source extraction, original-model construction, and disposal, plus preparation of the selected representation. It excludes shared admission and terminal-receipt overhead, which remain included in the full preparation transaction.

Each arm's two-request transaction was measured directly and includes context loading and controller overhead outside the request clocks. Its attributed preparation plus transaction total combines that measurement with an allocation from the single shared preparation run. The campaign did not independently measure a standalone preparation-and-deletion pipeline for each arm. No extrapolated break-even or general lifetime advantage is claimed.

## Accounting, failures and reproducibility

The empirical continuation charges 1,744 CPU seconds: 24 from the preserved failed first preparation and 1,720 from the six successful workers. All reservations are settled. The overall cap of 13,000 CPU seconds was preserved by subtracting the first failure from the second registration, leaving a cap of 12,976 CPU seconds for attempt B. Setup, tests, and read-only audits are outside that empirical ledger. Unused allowance is not transferred to a later campaign.

Attempt A (`604445d`) failed in progress logging before calibration feature extraction. Its 24-second debit, original source, and receipts remain in `campaigns/csis_v43_attempt_a/`. Attempt B uses corrected source `304a9cc`. Software job 13193 failed in the `cn1` user-resolution environment before tests; later work used `csis.mn1` through Slurm.

Supplemental software job 13207 exposed a failure in metadata-only file-change detection on NFS. Source `38ff2ae` adds actual content rehashing and preserves the failing regression. The failed job 13207 log and cancelled dependent job 13208 remain part of the history. The fresh Linux software job 13209 passed all 28 tests; supplemental artifact-audit job 13210 subsequently passed all eight comparisons. These software and audit steps do not rerun or replace the numerical campaign.

The CPU runtime uses CPython 3.12.14 in the pinned Bookworm Singularity image (`10ffb205f553197e110472e208522d0c73bcaf62e1a0571b860bf7bae49933b1`), NumPy 2.3.5, and gmpy2 2.3.2. Each worker has one CPU/thread, a 16 GiB virtual-address cap, and a matching Slurm RAM allocation. The A100 setup smoke test remains separate engineering evidence; no GPU arithmetic replaces this exact CPU target.

Read `campaigns/csis_full_model_v43/artifact-audit.json`, all six worker transactions and completions, and `validation/v43_local_archive.json`. The supplemental receipt is `campaigns/csis_full_model_v43/postrun-audit.json`; it binds the primary receipt and all actual file contents. These audits assume the recorded execution is trustworthy; they do not provide remote attestation. Actual model/state binaries are retained at `local_runs/full-model-v43-20261010-b/` in the fresh local and cluster checkouts. The local archive receipt records 1,269,053,685 binary bytes, approximately 1.27 GB. GitHub tracks text evidence and artifact commitments rather than these derived binaries. Copying receipts alone does not reproduce the payloads. Never rerun the registered one-use campaign; use a fresh explicit registration for numerical reproduction.

## Scope

This campaign covers one exposed root, 32-token contexts, one observation per arm and deletion step, a fixed order of method execution, and uncontrolled shared-machine and OS-cache conditions. It supports no confidence interval, useful-scale claim, held-out quality conclusion, or ACL-readiness claim. Original normalization 96 changes the target from the historical quality campaign's normalization of 256, so those earlier quality results do not transfer.

The separate V44 diagnostic completed on eight already exposed articles and passed its preset tolerances; fixed/sequential perplexity was 1.0170556. See `EXPOSED_QUALITY_RESULTS_V44.md` for all controls, losses, adverse differences, and scope. This adds no untouched quality evidence. Larger independent roots, useful context lengths, a real second model, stronger compression controls, randomized repeated sequences, untouched quality evaluation, and a defensible novelty claim remain required.
