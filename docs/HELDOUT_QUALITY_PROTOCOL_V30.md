# Prospective held-out validation quality

This protocol evaluates every remaining article in the fixed prepared validation pool.
The pool contains sixty eligible WikiText validation articles; twenty have already informed development.
The forty remaining articles provide the complete held-out remainder for this phase.
No pilot, model selection, or threshold tuning occurs within that remainder.

The phase confirms a prespecified claim within this bounded pool.
It does not establish corpus-wide generalization, uniform sampling, or guaranteed population coverage.
Existing pretraining contamination is outside the identifier audit's scope.

## Frozen methods and primary question

The primary contrast is fixed-feature128 versus matched sequential128 calibration.
Both models use the same checkpoint, four-bit grids, retained 128 tokens, and original normalization 256.
Their ancestor feature rules differ.

| Model | Complete model SHA-256 |
|---|---|
| Fixed128 | `25068a9373bb477123401124f07d5e02e09939f890fa16670d04d57e052bfce8` |
| Sequential128 | `1789cbcc2197c43ecf3ec0a33f72a1dc3c398358fc147f0cf945b0e72cffb700` |

Full precision and nearest rounding provide descriptive secondary controls.
Neither can replace the primary comparator after results appear.
Certificate, codec, and execution implementations may evolve while preserving these exact model outputs.
Compression latency does not determine eligibility for this quality phase.

The previous development follow-up must have passed all three quality and parity gates.
Its exact model provenance must match the two frozen outputs above.
The selector and worker verify this condition independently.

## Article selection and contamination checks

Use all forty remaining validation articles in the existing deterministic prepared-pool order.
Each article contributes its first 128 tokens, with no BOS, EOS, repacking, or cross-document context.
The evaluator scores 127 predictions per article, totaling 5,080 predictions per model.
The complete phase contains 160 model-article evaluations.

The preparation audit inspected experiment JSON metadata outside redundant source and worker copies.
Twenty-six files referenced validation identifiers; their union contained only the twenty exposed articles.
No remaining identifier appeared in that historical metadata.
The audit binds every such metadata file and the prepared-pool and tokenizer hashes.
Registration repeats the exposure check, excluding only this phase's own prospective files.

The training confirmation reserve remains outside the selected data.
The original twenty exclusions remain intact.
All forty selected identifiers receive prospective exclusions from future confirmation, producing sixty total.
Partial failures do not release selected identifiers for later outcome-driven reuse.

## Single primary decision rule

Let each article provide the paired fixed128 minus sequential128 NLL sum.
Divide their total by 5,080 and exponentiate to obtain the aggregate perplexity ratio.
Lower ratios favor fixed128.

Resample forty whole paired articles with replacement for each bootstrap draw.
Use 20,000 draws, NumPy's default random generator, and seed `20271008`.
For each draw, exponentiate its paired NLL difference divided by 5,080.
The upper statistic is the 95th percentile of those ratios, using linear quantile interpolation.
It is computed directly on ratios, rather than exponentiating an interpolated log quantile.

The primary gate requires all three guards:

1. The one-sided bootstrap upper ratio is at most 1.05.
2. The observed aggregate ratio is at most 1.05.
3. Every observed article ratio is at most 1.20.

There is only one primary contrast and one conjunctive decision rule.
Report all guards separately, including any failures.
Report every article result, all four aggregate losses, and both descriptive secondary contrasts.
Do not switch controls, omit unfavorable articles, or replace a failed threshold.

The fixed forty-article pool is evaluated exhaustively.
Its bootstrap statistic assesses sensitivity to the article mixture within that pool.
The nominal one-sided 95% percentile guard does not guarantee population confidence coverage.
A passing result supports the bounded-pool criterion, not universal noninferiority or quality superiority.

## Shared evaluation and evidence

Use the unchanged `NumpyQualityDecoder` from `scripts/run_quality_v30.py`.
Its SHA-256 is `db1253faa8a7d99fc2edf63405d6efe493e8e1a5783f3b4b1c6d970e88137d0d`.
The preceding development follow-up reproduced all thirty-two historical control losses exactly.
This phase evaluates no previously exposed article again.

The worker checks complete models, checkpoint identities, stage grids, target equations, and frozen output hashes before inference.
It rotates the four-model order by article index, giving each model ten occurrences in each position.
The evaluator uses ordinary NumPy binary64 arithmetic; NLLs are not certified intervals.

The controller freezes sources, policy, inputs, runtime, and earlier ledgers before execution.
It binds the exact worker command and verifies receipt artifacts and matching terminal copies.
The worker's `confirmation` flag and controller's `confirmation` flag are both true.
The budget phase remains named `feasibility`; that name controls accounting rather than scientific scope.
No automatic scientific or submission-readiness promotion follows.

## Resource plan and failure handling

The worker ceiling is 540 CPU seconds and 720 wall seconds.
The separate phase ceiling is 600 CPU seconds, including complete reservation margins.
Use one CPU, one thread, and six GiB address-space limits.
The earlier forty-eight-evaluation follow-up took 52.8 seconds.
Simple count scaling suggests roughly 176 seconds for this phase, but does not guarantee completion.

Measure the entire controller transaction, including validation, model loading, evaluation, writes, and exit.
Preserve partial results and all costs after any interruption or failure.
No outcome-driven early stopping, automatic retry, retuning, or article replacement is permitted.
Any technical recovery requires a separate explicit protocol preserving frozen models and revealing all prior exposure.

## Prepared files and checks

The draft is `campaigns/heldout_quality_v30_draft/specification.json`.
Its SHA-256 is `04464f5d880952babc65eb121ed96977518f039fca187fcf2938a647aa834553`.
The selection SHA-256 is `43bdbba7a74bf184dc2d59e9981557ab1a94b02312fbd81a09647e55db831d6d`.

The actual archive preflight verified model identities, target equations, grids, source hashes, and the complete held-out remainder.
It used 1.760711528 CPU seconds without model inference.
Its file is `campaigns/heldout_quality_v30_preflight.json`.
Its SHA-256 is `12fdce6c354c495d2f62a538665625bacb7751da12da47011cb0e10c6b5b5822`.
Six software fixtures passed before registration.

Preparation creates an unregistered draft and never evaluates a model:

```bash
python scripts/prepare_heldout_quality_v30.py --output /absolute/new/draft-directory
```

After review and settlement of prior active phases, the root controller may register and execute:

```bash
python scripts/launch_heldout_quality_v30.py --register campaigns/heldout_quality_v30_draft/specification.json
python scripts/launch_heldout_quality_v30.py --run quality-40
```
