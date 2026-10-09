# Complete first-stage Gram comparison

Updated 9 October 2026. Read this before older checkpoints.

V35 completed its four-row real-data component experiment. The cached-feature
token solver took 0.501197 seconds, versus 14.830470 seconds for pooled-Gram
deletion. All 3,072 decisions agreed. That small row count limits amortization
of shared coefficient work, so V36 tests every row of the same first QKV stage.

V36 is a new, separately registered development experiment. It evaluates all
2,304 rows, width 768, and 1,769,472 four-bit decisions. The retained record
contains 128 real WikiText tokens; original normalization remains 256.
Ridge remains 1/100. The stage, feature words, grids, and retained reference
are unchanged. No new neural feature generation occurs.

The controller is `scripts/launch_gram_stage_v36.py`.
The campaign is `campaigns/pooled_gram_stage_v36`.
The portable input manifest is `data/gram_v36/wikitext-firststage/manifest.json`.
It authenticates all weight/reference shards and the existing V35 feature capsule.
Read `GRAM_STAGE_REVIEW_V36.md` for independent review and `LOCAL_GRAM_STAGE_V36.md`
for fresh local reproduction. Source hashes and complete input dependencies
are frozen in the program before any numerical experiment.

Current state: complete and independently audited; do not rerun.
Program SHA-256: `28fad1a3e18cad1895eebe54ae7b57b93431d49f644d26b1fd566e5838b05bd2`.
The protocol was published at `bdc17d263cc60b29e05d2e7743592112e4f765fe` before execution.
All three arms certified all 1,769,472 codes. Exact retained Gram bytes also match.
The phase charged 139 CPU seconds, with one settled transaction.
Pooled deletion took 65.995601 seconds; fresh Gram reconstruction took 61.257673 seconds.
The cached-feature arm took 1.299832 seconds. Read `GRAM_STAGE_RESULTS_V36.md`.

The source audit identified avoidable generic interval-kernel work in the Gram row verifier.
Do not present the roughly 51-fold ratio as a comparison against the best possible Gram method.
A new V37 adapter will give the Gram path the existing certified ball-kernel acceleration.
It needs its own review, registration, and publication before any new experiment.
The separate phase permits 900 CPU seconds, with one 880-second CPU worker.
The process uses one CPU and a 3 GiB address-space limit.
No allowance is transferred from or reset in an earlier ledger.

The fixed arms are original Gram preparation, pooled-Gram deletion,
independent retained-Gram reconstruction, and cached-feature token reconstruction.
Each arm pays for its own required feature decoding and output checks.
Shared parsing and compilation are reported separately.
Any narrowly declared certificate refusal commits no model for that arm.
Independent controls continue; integrity or infrastructure failures stop the worker.
Refusal duration is not completed reconstruction latency and earns no speed ratio.
Do not retry the same attempt, replace rows, or change precision after outcomes.

This is one complete stage on a known development request. It cannot establish
complete-model speed, lifetime benefit, a new independent deletion result,
or superiority over every possible Gram algorithm.

The full C4 program remains blocked by the missing required `/proc` runtime
interfaces. Its failed repair and four unstarted trials remain preserved.
Read `ACTIVE_SESSION_V34.md`; do not bypass runtime attestation or retry that campaign.
The complete WikiText evidence and known scientific losses remain in earlier reports.

The broader empirical program and ACL submission remain incomplete.
The strongest candidate contribution is exact code recovery certified from
uncertain compressed feature archives. Fixed features or caching alone do not
establish novelty. Positive speed observations use fixed nearest-anchor features,
not the original sequential quantization target.
