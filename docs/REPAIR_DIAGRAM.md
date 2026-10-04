# Sequential repair method figure

Status: deterministic method diagram, revision 7.
This figure contains no empirical observations.
It closes J04 at the method-illustration scope.

## Files and rebuilding

- `scripts/build_repair_diagram.py` generates the figure without reading models, records, or experimental results.
- `output/figures/sequential_repair.svg` is the editable vector source.
- `output/figures/sequential_repair.pdf` is the vector publication export.
- Review PNG files stay under `tmp/figures/` and need not be published.

Run:

```bash
python scripts/build_repair_diagram.py --pdf --preview
```

SVG generation uses the Python standard library only.
Optional PDF and PNG exports require Inkscape.
PDF metadata normalization also requires `pypdf`.
The script fixes `SOURCE_DATE_EPOCH` and removes volatile PDF creation timestamps.
The PDF converts text into paths to preserve typography across machines.
Its content remains vector geometry, with no embedded raster image.
The SVG retains accessible title, description, and editable text.

## Proposed paper caption

**Exact calibration deletion follows the newly certified ancestor prefix.**
Deleting records first subtracts their regenerated intrinsic contributions from the canonical index.
Each stage queries retained aggregates under its current certified prefix.
The spectral certificate runs first.
The optional interval certificate adds a second exact decision check.
Unresolved groups replay retained features under that same prefix.
Complete replay supplies the exact covariance and permits exact target quantization.
Installed stage codes determine downstream feature maps.
The transaction commits only after every stage and the complete canonical retained state succeed.
A required finite-evaluator failure aborts without an approximate committed model.
All extraction, proof, replay, verification, and output costs remain charged.

## Interpretation

The loop follows dependency order, including changed ancestor codes.
It does not assume that an earlier quantized model remains unchanged.
The first stage has an empty quantized ancestor prefix.
Later stages use their required ancestors, not necessarily every preceding stage.

The blue aggregate route reads retained summaries and metadata.
It avoids retained feature evaluation only while its certificates suffice.
The amber route explicitly reads retained records and evaluates their current-prefix features.
Its exact group Gram tightens the remaining uncertainty.
When every group has replayed, direct exact quantization completes the stage.
Unknown proof data require replay and cannot become a certificate.

The dashed route carries the retained canonical index into the complete state.
It does not store request-specific replay features as hidden canonical state.
The green stage box denotes exact installed codes.
The final green box denotes successful complete-state construction and commit.
Durable archive retention and physical erasure remain separate storage questions.

The figure summarizes the declared algorithm.
It does not claim production-cold timings or an observed cost advantage.
Its optional interval policy is `spectral_or_interval`.
The default service policy remains `spectral`.
The figure does not imply that a multi-domain bank is already implemented.

## Visual verification

The SVG preview and the rendered PDF were inspected at full figure scale.
The final figure has no clipped labels or overlapping text.
The PDF has one page and zero embedded raster images.
A repeated build checks deterministic vector output under the installed converter.
Both SVG and PDF hashes matched across the final repeated build.
The figure preserves its meaning in grayscale through labels, arrows, and separate boxes.
Color is supplementary.
