# Revision 30 quality results

The registered quality pilot completed successfully.
Fixed-feature calibration passed the prospective development gate against sequential calibration.
It showed similar aggregate quality to sequential calibration.
It improved aggregate quality over nearest rounding.
Full precision still performed better on every article.

The result covers eight new WikiText articles and 1,016 predictions per model.
Each article contains 128 tokens.
All four controls use the same NumPy binary64 evaluator.
The calibrated models still use one retained sixteen-token calibration record.
This experiment expands evaluation length, not calibration length.

## Complete comparison

Lower perplexity is better.
These values describe the registered article prefixes, not the complete WikiText benchmark.

| Model | Mean NLL | Perplexity | Predictions |
|---|---:|---:|---:|
| Full precision | 3.81990950 | 45.600081 | 1,016 |
| Nearest rounding | 4.17238887 | 64.870234 | 1,016 |
| Fixed-feature calibration | 4.05654563 | 57.774392 | 1,016 |
| Sequential calibration | 4.05798098 | 57.857378 | 1,016 |

The primary comparison is fixed-feature calibration against sequential calibration.
Its aggregate perplexity ratio is **0.99856567**.
This is an observed decrease of **0.1434%**.
The descriptive bootstrap interval is **[0.97275066, 1.02323539]**.
This interval includes one.
The pilot therefore does not establish superiority over sequential calibration.
Fixed-feature calibration improves three articles and worsens five articles against that control.

The registered aggregate threshold was 1.05.
The registered threshold for each article was 1.20.
The largest observed article ratio was 1.04167336.
Both registered thresholds passed.
This is a development decision, without a population or confirmation guarantee.

Against nearest rounding, the aggregate ratio is **0.89061482**.
This is an observed decrease of **10.9385%**.
The descriptive interval is **[0.84584850, 0.94268357]**.
Fixed-feature calibration improves seven articles and worsens one article against nearest rounding.

Against full precision, the aggregate ratio is **1.26698002**.
This is an observed increase of **26.6980%**.
The descriptive interval is **[1.23493830, 1.29845966]**.
Full precision performs better on all eight articles.
Passing the sequential comparison does not establish preservation of full-precision quality.

## Article results

The row number identifies the WikiText validation article.
Every row contributes 127 predictions to every model.

| Article row | Fixed-feature / sequential | Fixed-feature / nearest | Fixed-feature / full precision |
|---|---:|---:|---:|
| 2525 | 1.003065 | 0.922460 | 1.186585 |
| 2237 | 0.959194 | 0.837179 | 1.277345 |
| 132 | 1.015748 | 1.043992 | 1.286593 |
| 2115 | 1.037133 | 0.810741 | 1.341045 |
| 2352 | 1.041673 | 0.861783 | 1.296327 |
| 1040 | 1.029499 | 0.917556 | 1.288054 |
| 3636 | 0.965790 | 0.823222 | 1.246437 |
| 1299 | 0.941709 | 0.930308 | 1.219966 |

## Evaluation checks and costs

The evaluator first checked four historical article-model results.
The maximum absolute mean NLL deviation was **1.18424e-14**.
The prospective limit was **1e-8**.
All checks passed before the worker evaluated any new article.
These checks support local agreement, not universal arithmetic equivalence.
The evaluator uses ordinary binary64 NLL without a certificate for numerical error.

The controller transaction took **38.829331821 seconds**.
Observed CPU use was **38.786156 seconds**.
The ledger charged **39 seconds**.
Peak resident memory was **2,658,635,776 bytes**, approximately **2.48 GiB**.
The registered ceilings were 300 CPU seconds, 420 wall seconds, and six GiB.
The transaction includes validation, loading, nearest rounding, inference, summaries, and output.
Nested article timers do not add to the transaction time.
Archived calibration costs remain separate historical costs.
This evaluation time does not measure repair speed.

The terminal file, live progress, and sealed progress agree byte-for-byte.
Their SHA-256 is `fa9ddadf0506a4d36378fa32ac4af9bea8b2a543222e0fb6f4458df1cef2fd9b`.
The receipt-bound log contains that terminal hash.
The registration SHA-256 is `bafbbd721435f8f188ddb7a0f834ee6df3f097d62e6189e03023a5828254b95c`.
The result audit checks artifact hashes, model provenance, exclusions, counts, estimators, and bootstrap calculations.
It performs no model inference.

## Uncertainty and exclusions

The bootstrap resamples whole paired articles with seed 30 and 10,000 draws.
It never treats tokens as independent observations.
The intervals describe sensitivity within this small development set.
The fixed article selection does not justify population coverage.
The three comparisons are reported without selecting the most favorable comparison as primary.

All twelve earlier exclusions remain excluded.
The eight new articles also remain excluded from future confirmation.
The complete twenty-article exclusion list is stored in registration and audit files.
The training confirmation reserve remains untouched.
Forty validation articles remain outside the cumulative quality exclusions.
Their availability does not authorize treating them as confirmation without a frozen protocol.

## Next quality expansions

These steps require new registration and complete model artifacts.
They are a proposed sequence, without claimed execution or results.

1. Build matched complete models after the first larger calibration workload passes its numerical and resource checks.
   Preserve the checkpoint, grids, calibration membership, deletion request, and original normalization across calibrated controls.
   Verify the complete repaired model against retained-data reconstruction before evaluating quality.
   First evaluate the existing eight development articles with the shared evaluator.
   Reusing these articles consumes no new confirmation candidates.
   Report this comparison as development evidence after the current results.

2. Compare the small and larger calibration models on those same eight articles.
   Keep full precision and nearest rounding as common controls.
   Measure whether larger calibration reduces the observed full-precision gap.
   Keep the sequential comparison primary when testing the fixed-feature design.
   Report every article and every model, including unfavorable results.
   The present pilot cannot identify insufficient calibration as the cause of that gap.

3. Freeze a fresh eight-article pilot after the larger calibrated models and analysis rules stop changing.
   Select the next eight eligible validation articles using the existing frozen order.
   Preserve all twenty current exclusions.
   Add the new eight exclusions before inference.
   Use 128-token prefixes and the same matched controls first.
   Keep the 1.05 aggregate and 1.20 article thresholds against sequential calibration.
   Define any additional full-precision threshold before inspecting those results.
   A suggested engineering screen is a maximum aggregate ratio of 1.20 against full precision.
   That proposed screen is stricter than the present result and remains unregistered.

4. Test 256-token and 512-token evaluation contexts using already exposed development articles.
   Reconstruct text from the pinned parquet files and tokenizer.
   Check article body hashes and agreement with the cached first 128 tokens.
   Keep positions, causal attention, and prediction counts explicit.
   Register a context-specific memory and CPU ceiling before every pilot.
   Do not concatenate articles or change token weighting to improve results.

5. Repeat matched quality evaluation for additional retained calibration sets and independent deletion requests.
   Include singleton, grouped, and changing-state deletions after their model artifacts exist.
   Use at least three independent calibration sets before selecting a final design.
   Report uncertainty across calibration sets separately from uncertainty across articles.
   Repeated evaluations of one calibrated model do not create independent calibration evidence.

6. Add a second text corpus and a second model after their input inventories pass review.
   Local C4 and LAMBADA inputs need corpus-specific membership and tokenizer checks.
   Use perplexity for C4 text and a separately registered task metric for LAMBADA.
   GPT-2 weights are not currently cached.
   Its configuration file alone cannot support another model experiment.
   Each new corpus and model needs a small matched pilot before expansion.

7. Freeze final confirmation only after the method, calibration workload, and quality margins are fixed.
   Reserve fresh calibration sets and fresh evaluation articles.
   Declare one primary quality comparison and its sampling law.
   Set sample sizes from a prospective precision or power analysis.
   Keep all twenty current exclusions and all future development exclusions.
   Do not reuse development intervals as confirmatory evidence.

The present result closes the registered eight-article development pilot.
It leaves broader quality, practical calibration scale, independent requests, and final confirmation open.
