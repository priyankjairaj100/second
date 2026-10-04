# Fixed target and chart construction

Updated 4 October 2026.
This contract selects V_cert for the reference program.
The constructor defines a project quantizer.
It makes no numerical equality claim about Hugging Face or GPTQ.

## Target recipe

`TargetRecipe` requires the original calibration token count.
The runner must verify this count against the original record manifest.
Every deletion keeps this count fixed.
The default ridge is exactly `1/100`.
The default grid uses four bits.
The default group count is eight.
All choices enter the target digest.
Calibration records cannot change the grid, ridge, order, or grouping rule.

Each input coordinate has its own fixed grid.
Let `b` denote the bit count, with `2 <= b <= 8`.
Let `K = 2**(b-1)`.
The integer codes are `-K, ..., K-1`.
Thus, each grid has exactly `2**b` codes, including zero.
Each grid uses a power-of-two step.

For column weights `w`, choose the smallest power-of-two step that satisfies:

\[
\Delta\ge\max\left\{\frac{\max_i w_i}{K-1},
\frac{-\min_i w_i}{K},0\right\}.
\]

For an all-zero column, set the step to one.
Clamp the step below by `2**-1074`.
This clamp preserves distinct finite grid values for subnormal columns.
Reject any grid with nonfinite or inexact binary64 codes.
Reject quantized base weights that differ from their binary64 conversions.
The supported safetensors storage types satisfy this parameter condition after import.
This condition does not validate any particular pretrained checkpoint.

Quantization uses exact rational Grams and exact reverse LDL factors.
It visits input coordinates in ascending order.
It visits output rows in ascending order.
It visits stages in the decoder's declared order.
Equal rounding distances select the smaller code.
The program performs no activation ordering or calibration-based scale fitting.

The decoder resets positions for each nonempty record.
Attention uses an inclusive causal mask within each record.
The token program has no padding or cross-record attention.
Embeddings, positions, norms, biases, and the final head remain fixed.
Tokenization rules and dataset hashes belong to the separate record manifest.
Those rules must be concrete before an experiment begins.

The request supplies deleted record payloads for checked subtraction.
The output contains every quantized stage matrix and canonical aggregate state.
Proof rejection causes retained replay.
A finite evaluator failure aborts the request before commit.

## Source and state binding

`build_target` binds the decoder, recipe, stage dimensions, parameters, grids, and source files.
Its digest also binds the exact quantizer and service proof modules.
`TargetManifest.make_job` embeds this digest in the numerical contract.
Thus, source changes also change the service manifest.
`make_service` reconstructs the target and chart before use.
It rejects edited parameters, grids, rules, directions, radii, precision, and source versions.
These checks assume trusted source files and storage.
They do not authenticate hostile program code.

## Chart recipes

`build_chart` accepts only a decoder, generated target, and fixed recipe.
It accepts no calibration corpus, calibration outputs, fitted factors, or deletion request.
The chart digest binds the constructor source and exact directions.
Thus, corpus independence follows from this constructor's input contract.
It does not depend only on a supplied provenance sentence.

The default `stage-rtn` mode computes ordinary nearest-grid rounding from the base weights.
Each relevant ancestor stage contributes its rounded matrix minus its finite base matrix.
Zero directions are omitted.
The default coefficient radius is one.
Each nonzero stage direction receives its own coefficient.
The final stage needs no direction because no calibration stage follows it.

This chart contains the complete ordinary-rounding prefix.
It generally does not contain the complete sequentially quantized prefix.
Different entries can require different corrections.
One coefficient per stage cannot represent those changes in general.
The program rejects any nonzero representation residual.
A small deletion does not ensure chart membership.
The test uses the complete installed prefix, relative to the fixed base.
It does not use only the change from the previous quantized model.

The optional `coordinate` mode uses one direction for each entry of each relevant ancestor matrix.
Each direction changes its entry by that coordinate's grid step.
Its radius covers both grid endpoints relative to the base entry.
This chart contains every possible installed grid prefix.
Membership does not prove useful curvature bounds or successful certification.
The dense implementation can require prohibitive storage and arithmetic.
This mode is a completeness control for affordable cases.
It is not the default for language models.

The optional `none` mode has zero rank.
It supports only an unchanged finite ancestor prefix.
Unsupported prefixes cause replay.

## Resource checks

`preview_chart` counts resources before it allocates direction matrices.
The preview reports rank, direction entries, aggregate entries, and scalar components per jet.
The preview also reports grid entries and the nominal packed size of quantized codes.
The implementation currently stores code matrices as rationals.
It does not produce the nominal packed artifact.

With rank `r` and stage input width `d`, each group stores:

\[
(r+1)d^2+r^2+\frac{(r+3)(r+4)}{2}
\]

The final term counts the scalar remainder moments.
The implementation uses the global chart rank at every stage.
The preview sums all stages and multiplies by the group count.
Coordinate mode allocates dense direction matrices.
Its direction count is therefore the sum of squared ancestor matrix sizes.

Default limits are 64 directions, one million direction entries, and five million aggregate rational entries.
The grid constructor also limits total grid entries to one million.
`preview_chart` reports each exceeded chart limit.
`build_chart` rejects the recipe before dense allocation when any chart limit fails.
Many real checkpoints can fail these default limits.
Such failure is a feasibility result for the recipe, not an implementation success.
Raising a limit requires an explicit resource decision.

Counts exclude rational bit lengths, Python objects, record metadata, temporary values, and execution time.
They are not memory guarantees.
The service reconstructs inputs for validation and can temporarily hold duplicate structures.
Checkpoint import already allocates parameters before this preview.
The runner must apply separate checkpoint and process limits.

## API

```python
from fractions import Fraction
from src.target_manifest import TargetRecipe, build_target
from src.chart_construction import ChartRecipe, preview_chart, build_chart, make_service

recipe = TargetRecipe(original_token_count=4096, bits=4, ridge=Fraction(1, 100))
target = build_target(certified_decoder, recipe)
chart_recipe = ChartRecipe(mode="stage-rtn")
preview = preview_chart(certified_decoder, target, chart_recipe)
if not preview.feasible:
    raise ValueError(preview.over_budget)
construction = build_chart(certified_decoder, target, chart_recipe)
service = make_service(certified_decoder, target, construction)
```

The example specifies a configuration only.
It does not create records or run an experiment.
The runner must match `original_token_count` to its original record manifest.
Both recipe classes provide strict `from_payload` methods and canonical `payload` descriptions.
Target and chart constructions provide canonical bytes and SHA-256 digests.

## Remaining empirical gates

No real checkpoint has passed this target and chart program yet.
The first gate checks import, resource limits, and complete finite evaluation.
The next gate checks useful chart membership and certificate coverage.
Neither the constructor nor its correctness tests establish model quality or latency.
Experiment claims must include preparation, validation, retained replay, output, and state costs.
