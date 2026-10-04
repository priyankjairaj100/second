# Fixed target and chart construction

Updated 4 October 2026, revision 6.
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
`make_service` reconstructs the target and selected proof domain before use.
It rejects edited parameters, grids, rules, directions, radii, precision, and source versions.
These checks assume trusted source files and storage.
They do not authenticate hostile program code.

## Chart recipes

`build_chart` accepts only a decoder, generated target, and fixed recipe.
It accepts no calibration corpus, calibration outputs, fitted factors, or deletion request.
The domain digest binds constructor source and exact directions or interval endpoints.
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

## Parameter-box recipe

The optional `grid-box` mode defines independent intervals for ancestor weight coordinates.
Each interval contains the finite base value and every installed value from its frozen grid.
Construction applies the decoder's binary64 conversion before selecting interval endpoints.
The final quantization stage needs no interval because no calibration stage follows it.
The recipe accepts only `radius=1`.
It represents the complete fixed grid domain without affine directions.

Every possible installed grid prefix belongs to this domain.
Membership therefore avoids the affine representation failure described above.
Membership does not establish a useful feature bound or an accepted decision certificate.

`BoxResponseProvider` executes the same scalar graph with rank-zero interval jets.
Each jet retains an ideal interval and a proved finite execution error.
A nonconstant domain uses the midpoint of each feature interval as its anchor.
Its coordinate error equals the interval half-width plus the finite execution error.
The provider sums squared coordinate errors and rounds the square root upward.
It stores one anchor Gram and six scalar error moments per group and stage.

A domain containing only the finite base ancestors uses exact finite feature anchors.
Their error is zero because identical ancestors execute the identical finite program.
Other domains do not require a separate finite base feature evaluation.
Proof failure marks the record descriptor unavailable and permits retained replay.
Finite target failure during required replay still aborts the request.

Midpoints minimize each supplied interval's maximum coordinate distance.
They do not guarantee smaller Gram error or better decisions for every request.
Uniform box errors need not shrink when the deletion size shrinks.
See `docs/BOX_THEORY.md` for the proved statements and limits.

## Resource checks

`preview_chart` counts resources before it allocates direction matrices.
The preview reports rank, domain entries, aggregate entries, and scalar components per jet.
For `grid-box`, `direction_entries` counts stored interval endpoints.
Its `domain_storage_kind` identifies these endpoint rationals.
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
For `grid-box`, rank is zero and each stage stores `d**2 + 6` aggregate rationals per group.
The domain stores two endpoints per relevant ancestor parameter.
Coordinate mode allocates dense direction matrices.
Its direction-entry count is the sum of squared ancestor matrix sizes.

Default limits allow 64 directions, one million domain entries, and five million aggregate rational entries.
The grid constructor also limits total grid entries to one million.
`preview_chart` reports each exceeded chart limit.
`build_chart` rejects the recipe before dense allocation when any chart limit fails.
Many real checkpoints can fail these default limits.
Such failure is a feasibility result for the recipe, not an implementation success.
Raising a limit requires an explicit resource decision.

Counts exclude rational bit lengths, Python objects, record metadata, temporary values, and execution time.
They are not memory guarantees.
The service reconstructs inputs for validation and can temporarily hold duplicate structures.
The runner first applies a configuration-only plan before eager checkpoint import.
That plan reads no tensor files.
It counts the largest parameter-stage wrapper under the lazy execution schedule.
Finite, affine, and box execution now allocate wrappers only for the currently accessed stage.
The scalar operation order remains unchanged.
Eager base parameters, feature activations, and temporary exact integers still require memory.
Planning bytes are estimates, not proved bounds or measured peaks.

The campaign worker separately enforces address-space, CPU, file-size, and wall-time limits.
Address-space limits apply per process and do not measure physical memory.
The direct single-run command does not create this worker boundary.
Many ordinary checkpoints still exceed the default resource plan.

## API

```python
from fractions import Fraction
from src.target_manifest import TargetRecipe, build_target
from src.chart_construction import ChartRecipe, preview_chart, build_chart, make_service

recipe = TargetRecipe(original_token_count=4096, bits=4, ridge=Fraction(1, 100))
target = build_target(certified_decoder, recipe)
chart_recipe = ChartRecipe(mode="grid-box")
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
The next gate checks useful proof bounds and certificate coverage.
Affine recipes also require useful prefix membership.
Grid-box membership alone does not close the coverage gate.
Neither the constructor nor its correctness tests establish model quality or latency.
Experiment claims must include preparation, validation, retained replay, output, and state costs.
