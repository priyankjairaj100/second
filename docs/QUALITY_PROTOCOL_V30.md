# Revision 30 quality protocol

This prospective development pilot compares four complete DistilGPT2 variants.
It does not run calibration, deletion, or confirmation.

The variants are full precision, nearest rounding, fixed-feature calibration, and sequential calibration.
All calibrated variants use the archived four-bit grids.
All controls preserve embeddings, positions, norms, biases, and the language-model head.
The two calibrated models used one retained article with sixteen calibration tokens.
Their original normalization contains thirty-two tokens.
This pilot expands evaluation length, not calibration length.

## Fixed input selection

The script verifies the historical token pool and tokenizer hashes.
It preserves all twelve prior article exclusions.
It selects the next eight eligible validation articles from the frozen pool order.
Each article contributes its first 128 tokens and 127 next-token predictions.
The pilot contains 1,016 predictions per model.
All eight selected articles become excluded from future confirmation before inference.
The training confirmation reserve remains untouched.
Selection does not use model losses, article subjects, or observed wins.

`prepare_quality_v30.py` previews the selection by default.
The `--freeze` option creates an immutable registration file.
The script refuses to overwrite that file.
The controller must freeze source snapshots and resource admission before launching the worker.

## Shared inference arithmetic

PyTorch and Transformers are absent from the local environment.
The worker therefore uses NumPy binary64 matrix operations for every model.
It implements the same architecture with a different floating-point schedule.
It resets positions for each article and applies inclusive causal attention.
It uses no padding, generation, dropout, or cross-article cache.
Its output uses ordinary finite NLL, without an interval certificate.

This evaluator does not replace the finite calibration target.
The archived calibrated codes remain unchanged.
The worker checks model hashes, complete stage coverage, matching grids, generation receipts, and calibration membership.
The worker verifies both calibration plans against the same checkpoint.
It records the runtime and the evaluator source hashes.

Before new inference, four historical article-model comparisons must pass.
These comparisons use both previously evaluated articles and both archived calibrated models.
Each absolute mean NLL deviation must be at most `1e-8`.
The threshold remains fixed before execution.
Failure stops the worker before any new article inference.
Passing this check establishes local agreement on those four comparisons only.
It does not prove global arithmetic equivalence.

Software fixtures also compare tiny decoder outputs against the finite decoder.
They cover both GELU variants, multiple heads, biases, installed matrices, and causality.
These fixtures are software checks, not synthetic empirical datasets.

## Comparison and uncertainty

The primary comparison uses fixed-feature calibration versus sequential calibration.
Secondary comparisons use nearest rounding and full precision.
The worker saves each article's NLL sum and prediction count for every model.
It divides total paired NLL differences by total prediction counts.
It exponentiates this difference to obtain the aggregate perplexity ratio.
It also reports article ratios and the mean article NLL difference.

The worker resamples whole paired articles for 10,000 bootstrap draws.
It uses NumPy PCG64 with seed 30.
It reports percentile endpoints at 2.5% and 97.5%.
Tokens never serve as independent resampling units.
Eight articles give weak uncertainty estimates.
The fixed development selection does not justify population coverage or confirmation claims.
The bootstrap intervals describe development sensitivity only.

The prospective development gate keeps the earlier thresholds.
The aggregate ratio must not exceed 1.05.
Every article ratio must not exceed 1.20.
The worker reports observed wins separately from this gate.
It preserves all losses and does not retune after a failed gate.
No secondary comparison replaces the primary comparison after results appear.

## Resource and evidence contract

The plan reserves 300 CPU seconds and a 420-second wall limit.
The process limit is six GiB, with one thread and one CPU affinity.
The worker performs four historical checks and thirty-two new model-article evaluations.
The largest single logits array contains `128 * 50257 * 8 = 51,463,168` bytes.
That value excludes checkpoint arrays, prefixes, temporary arrays, and process overhead.
It is not a complete memory bound.
The controller enforces the process limit separately.
The CPU and wall limits are abort ceilings, not predicted completion times.

Complete cost includes input checks, model loading, nearest rounding, inference, summaries, and output writes.
Article timers are nested diagnostics.
Archived model preparation costs remain historical external costs.
This quality pilot cannot establish repair speed or lifetime savings.

The worker writes progress after every article-model result.
Successful completion also writes an exclusive, synchronized terminal file.
It prints the terminal hash into the controller-bound log.
The controller must compare progress, terminal bytes, and its sealed receipt.
Partial runs remain incomplete and retain their original evidence.
There is no automatic retry or threshold adjustment.

## Commands and plan fields

Preview without inference:

```bash
python scripts/prepare_quality_v30.py
```

Freeze after review:

```bash
python scripts/prepare_quality_v30.py --freeze
```

The worker command is `python scripts/run_quality_v30.py /absolute/path/to/plan.json`.
The controller supplies `source_sha256`, `protocol_sha256`, `output`, and `checkpoint`.
It also supplies the registration descriptor and absolute bound input descriptors.
Every descriptor contains `path`, `bytes`, and `sha256`.
The registered relative input paths become absolute paths in the plan.
The controller must admit the exact worker command through `verify_command_admission`.

No broader quality result exists until the complete registered worker succeeds.
Further calibration workloads, models, corpora, and independent deletion requests remain necessary.
