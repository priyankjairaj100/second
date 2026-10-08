# Matched larger-calibration quality follow-up

All three prospective development gates passed. The matched aggregate favors fixed-feature calibration by 1.8194%.
The descriptive article interval crosses one, so these data do not establish quality superiority over matched sequential calibration.

This follow-up reuses eight exposed WikiText validation articles, with 128 tokens and 127 predictions each.
Each model therefore contributes 1,016 predictions. All twenty existing exclusions remain excluded from confirmation.
No new article was evaluated in this phase.

## Gates

| Gate | Observed result | Prospective requirement | Outcome |
|---|---:|---|---|
| Fixed128 / sequential128 aggregate | 0.9818058521 | ≤ 1.05 | Pass |
| Largest fixed128 / sequential128 article ratio | 1.0351350476 | ≤ 1.20 | Pass |
| Fixed128 / fixed16 aggregate | 0.8914135117 | ≤ 1.05 | Pass |
| Largest fixed128 / fixed16 article ratio | 0.9378064831 | ≤ 1.20 | Pass |
| Historical mean NLL parity, 32 comparisons | 0 | ≤ 1e-8 | Pass |

## Complete controls

| Model | Retained calibration tokens | Original normalization | Total NLL | Perplexity |
|---|---:|---:|---:|---:|
| full_precision | — | — | 3881.028047691 | 45.600081133 |
| nearest_rounding | — | — | 4239.147095733 | 64.870233956 |
| fixed16 | 16 | 32 | 4121.450357137 | 57.774391687 |
| sequential16 | 16 | 32 | 4122.908678714 | 57.857378043 |
| fixed128 | 128 | 256 | 4004.664346679 | 51.500873383 |
| sequential128 | 128 | 256 | 4023.319830585 | 52.455251994 |

Fixed128 and sequential128 use identical calibration tokens, checkpoint, four-bit grids, and original normalization.
They differ in the ancestor feature rule. The sequential worker preserves the original sequential numerical target.
The ordered implementation has separate source provenance and correctly rounded finite operations.
Quality evaluation uses the unchanged shared NumPy binary64 evaluator. Its NLL values are ordinary numerical estimates.

## All contrasts

Ratios divide fixed128 perplexity by the listed control. Lower ratios favor fixed128.
Intervals resample whole paired articles 10,000 times with seed 31.
These two-sided percentile intervals describe the reused development set; they are not confirmatory population intervals.

| Control | Ratio | Percent change | Descriptive 95% interval | Article wins / losses |
|---|---:|---:|---|---|
| sequential128 | 0.9818058521 | -1.8194% | [0.9580324523, 1.0077142145] | 5 / 3 |
| fixed16 | 0.8914135117 | -10.8586% | [0.8623969360, 0.9171024734] | 8 / 0 |
| sequential16 | 0.8901349339 | -10.9865% | [0.8713641237, 0.9093053115] | 8 / 0 |
| nearest_rounding | 0.7939060836 | -20.6094% | [0.7469561064, 0.8418668820] | 8 / 0 |
| full_precision | 1.1294031086 | +12.9403% | [1.1011013005, 1.1561556374] | 0 / 8 |

Fixed128 beats matched sequential128 on five articles and loses on three.
The largest matched article degradation is 3.5135%; the registered tolerance was 20%.
The aggregate gate is a development tolerance check, not a proved population noninferiority result.
Fixed128 improves over nearest rounding on all eight articles, with 20.6094% lower aggregate perplexity.
Full precision remains better on every article; fixed128 perplexity is 12.9403% higher overall.
The fixed16 comparison changes calibration length and normalization together. It cannot isolate either causal effect.
The sequential16 comparison is an unmatched secondary contrast.

## Article results

Each row contains 127 predictions. Article suffixes refer to the unchanged WikiText validation identifiers.

| Article row | Fixed128 NLL | Sequential128 NLL | Fixed128 / sequential128 | Fixed128 / fixed16 |
|---|---:|---:|---:|---:|
| 2525 | 509.670813753 | 507.289592898 | 1.0189266512 | 0.9275263955 |
| 2237 | 449.616586608 | 454.294703745 | 0.9638346076 | 0.9165438422 |
| 132 | 416.076853820 | 412.926003262 | 1.0251201722 | 0.8488192694 |
| 2115 | 561.028957073 | 565.845954113 | 0.9627811895 | 0.8743604389 |
| 2352 | 526.886867216 | 530.209698227 | 0.9741752887 | 0.8164269123 |
| 1040 | 516.315024195 | 511.929473031 | 1.0351350476 | 0.9040891011 |
| 3636 | 473.413351856 | 480.762913972 | 0.9437720940 | 0.9128652471 |
| 1299 | 551.655892158 | 560.061491339 | 0.9359569283 | 0.9378064831 |

The machine-readable audit retains every article NLL for all six models.

## Complete cost and evidence

| Transaction | Controller seconds | Observed CPU seconds | Charged CPU seconds | Peak RSS bytes |
|---|---:|---:|---:|---:|
| sequential-128 | 138.228381253 | 137.839139000 | 138 | 770445312 |
| matched-quality-128 | 52.804748343 | 51.986074000 | 52 | 3446587392 |

The phase charged 190 of its 1,200 CPU seconds. Both reservations are settled.
The archive-only audit used 3.297300444 CPU seconds separately from worker accounting.
Three analyzer fixtures passed; no model inference was repeated during analysis.
The sequential comparator measures a different target and cannot serve as a fixed-feature repair-speed baseline.

The strict audit checked frozen source inventories, registration bindings, exact commands, resource limits, and both execution receipts.
It checked all terminal copies, output hashes, final accounting, external equality gates, and complete calibrated model grids.
It independently recomputed article ratios, aggregate estimates, bootstrap intervals, parity, and all three gates.

| Evidence | SHA-256 |
|---|---|
| Sequential128 completion | `4ed0de36a5db128e8a6f62a65b763a4fc2132e24c00f89849c450a4eda04212b` |
| Quality completion | `79ee4d7db89a43642aeb04227c7f17163197dc44c357b42739c932621b53cf98` |
| Fixed128 model | `25068a9373bb477123401124f07d5e02e09939f890fa16670d04d57e052bfce8` |
| Sequential128 model | `1789cbcc2197c43ecf3ec0a33f72a1dc3c398358fc147f0cf945b0e72cffb700` |
| Audit JSON | `ce8cfee3fe5ac261c1b30d0a8732aaeafe496be2449728b09c82aedc6fa519c2` |

Audit: `campaigns/quality_extensions_v30_summary.json`.
Reproduction: `scripts/analyze_quality_extensions_v30.py --output /absolute/new/audit.json`.
The analyzer refuses an existing output path and never evaluates a model.

## Scope and next decision

This result closes the larger matched-quality development gate for the current fixed128 model.
It does not establish broad quality, another model, another corpus, independent confirmation, or original sequential repair speed.
The twenty exposed articles remain excluded from any held-out phase.
The next proposed quality phase must freeze the current model outputs before exposing the remaining forty validation articles.
Compression implementations may change while preserving those exact model bytes.
A quality confirmation phase need not depend on unrelated compression latency.
