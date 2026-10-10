# Current checkpoint after completed native-control experiments

Updated 10 October 2026, after successful V40 completion and local audit.
This document supersedes earlier execution-status notes.

## Current status

V39 and V40 are complete.
All seventeen V39 and twelve V40 complete-stage outputs match exact target codes.
V40 also verifies native/reference source Grams and deleted/fresh retained Gram archives.
Both V40 compressed certificates accept without replay or fallback.
No empirical worker remains active.
No new attempt is registered, reserved, or awaiting execution.
The complete research program and ACL manuscript remain incomplete.

Read these files first:

- `docs/NATIVE_SCALE_RESULTS_V40.md`: every arm, exactness, timing, storage, accounting, and audit limits.
- `docs/SCALE_RESULTS_V39.md`: the previous scale pilot, including its 32-bit refusal and Gram wins.
- `docs/RESEARCH_DECISION_V41.md`: positioning and the next scientific gate.
- `docs/FULL_MODEL_ADMISSION_V41.md`: explicit wide-stage implementation blockers.
- `docs/CLAIM_BOUNDARIES_V41.md`: target contract and proof-to-code obligations.
- `handoff/program_v41.json`: machine-readable restart context.

V40 workflow: https://github.com/priyankjairaj100/second/actions/runs/38025361543.
It completed successfully at 04:58:36 UTC.
Its source commit is `2ba58fcb4e7c8f9e81441f4d2b445bd92e6db717`.
Its registration publication is `43dad849eb61b53b43a6f0c47d58b1babd27ad93`.
Its final evidence commit is `6a7ba25e1a2c11f39377b7a60e492834475ffcd7`.
Its evidence prefix is `campaigns/ci_native_scale_v40`.

## Research interpretation

The target uses source-local fixed nearest-anchor features and original normalization.
It differs from ordinary sequential GPTQ.
It does not remove information from the base checkpoint's pretraining.
The new results cover only the first QKV stage: 2,304 rows, width 768, and 1,769,472 codes.
There is one observation per method and retained size, using exposed development articles.
There is no new population quality or confirmation evidence.

At 768 retained tokens, cached primal takes 23.020064 seconds.
Streamed 40-bit compression takes 25.387995 seconds and saves 20.2372% of the declared payload.
Native Gram deletion takes 30.136403 seconds and stores more payload than either feature route.
At 1,536 tokens, native Gram deletion takes 18.835432 seconds.
The compressed route takes 36.965634 seconds and has 14.3174% larger payload.
The stronger Gram control therefore defeats compression in that larger case.
The useful candidate is a workload-dependent storage/latency tradeoff, not universal speed superiority.

Native source accumulation is 5.833634 times faster than the Python reference within this preparation.
This component ratio is not a complete repair or lifetime speedup.
The streamed implementation preserves exact codes while avoiding a concatenated retained feature matrix.
It is slightly slower than concatenation in both observations.
Its complete-service memory benefit remains unmeasured.

The widest MLP stages have width 3,072.
Current primal budgets refuse them at both tested retained sizes.
At 1,536 tokens, their default token coefficient budgets also refuse.
These are declared admission limits, not hardware impossibility proofs.
Do not launch a uniform full-model extension without resolving them.

## Evidence and accounting

V40 charges 4/122 data CPU seconds and 506/1,700 model CPU seconds.
The four worker charges are 4, 108, 197, and 201 seconds.
All new ledger attempts are settled.
Historical ledgers and unknown historical reservations remain unchanged.
Unused allowances are not transferable grants for future campaigns.
Setup, software checks, publication, and archive analysis are outside empirical ledgers.
The current continuation uses no paid compute.

The local V40 metadata audit checks 132 published text files and 193 source/control files.
It checks commands, receipts, terminal copies, ledgers, payload bytes, ratios, and V39 code commitments.
Forty-six derived V40 binaries are absent locally.
The temporary runner performed actual binary comparisons before shutdown.
Local metadata checks cannot repeat those missing binary comparisons.
V39 likewise has seventy-seven missing derived binaries after recorded CI audits.
Never equate hashes alone with a fresh numerical reproduction.

Twenty-six V40 software checks passed locally and on the empirical host.
No numerical source changed after V40 registration.
New post-run read-only analysis lives under `research_v41`.
No V41 empirical campaign exists.

## Immediate next work

1. Implement stage-specific exact solver dispatch and the final representation contract.
2. Resolve wide-stage admission with reviewed working sets and explicit new resource limits.
3. Build an independent canonical complete-state reconstruction oracle.
4. Register a small complete-model comparison against strong native Gram, cached, and cold controls.
5. Proceed only after exact model/state agreement and interpretable complete costs.
6. Measure successive deletions, complete storage, preparation, fallback, and lifetime break-even.
7. Expand useful regimes to another model, independent roots, and untouched quality evaluation.
8. Freeze the method before randomized confirmation and uncertainty analysis.
9. Finish closest-theorem review, manuscript claims, limitations, and reproduction instructions.

ExecCert's full-text retrieval gap was closed in the previous audit.
Its implementation has not been reproduced here.
Exact-Fun's indexed algorithm and theorem passage narrow its retrieval gap.
Its complete primary proof remains inaccessible in this check.
Read `docs/EXACT_FUN_RETRIEVAL_V41.md`; do not mark full-paper comparison complete.
Fixed features, subtractable statistics, and stability alone do not establish novelty.

## Resume rules

Fetch and inspect actual repository/workflow status before changing anything.
Never rerun old workflows or reuse an attempt directory.
Never rewrite historical numerical sources, ledgers, failures, or source snapshots.
Preserve `src/*.py` and `scripts/run_*.py`.
Put new implementation in a new research directory.
Use fresh registration, paths, runtime identity, resource plan, and ledgers for any empirical continuation.
Preserve all sixty quality exclusions.
Do not tune on future confirmation data or omit losses.
Repository pushes are authorized; paid compute, force-pushes, and subagent delegation are not.
Never push unrelated changes during a future workflow's publication phase.

The following are read-only metadata commands, not experiment launch commands:

```bash
python -B -m research_v41.audit_scale_v40 --output tmp/fresh-v40-metadata-audit.json
python -B -m research_v41.full_model_admission --output tmp/fresh-model-admission.json
```

Both output paths must be unused.
These commands do not restore missing binary artifacts or authorize new model work.
