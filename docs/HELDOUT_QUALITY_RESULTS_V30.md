# Held-out bounded-pool quality confirmation, revision 30

Audited 8 October 2026. This report uses archived outputs only; no inference was rerun.

The frozen fixed-feature model passes all three prospectively registered quality guards on the forty previously unexposed articles remaining in the prepared WikiText-2 validation pool. Its aggregate perplexity is 65.6905966211, versus 66.4433866395 for the matched sequential model: a ratio of 0.988670203967 (1.13298% lower). Twenty articles favor each model. The one-sided bootstrap upper ratio is 1.001859166913, which passes the 1.05 tolerance but exceeds one. This is evidence for the specified bounded-pool quality tolerance, not evidence of quality superiority.

## Scope and frozen comparison

This is a census of the fixed forty-article remainder after twenty earlier development exposures, not a uniform random sample of WikiText-2 or natural language. Selection, model bytes, evaluator, thresholds, and analysis were committed before observing these forty outputs. Each article contributes its first 128 tokenizer tokens without an inserted BOS/EOS token, giving 127 scored next-token predictions and 5,080 predictions per model. Four models yield 160 model–article evaluations. No article was replaced or dropped and no early stopping occurred.

The fixed and sequential models use the same DistilGPT2 checkpoint, 128 retained calibration tokens, original normalization 256, stage schedule, and four-bit grids. Their feature policies intentionally differ: fixed nearest-grid ancestor features versus sequential calibrated ancestor features. The archive audit verifies the fixed target's base-target identity equals the sequential target identity, with all 24 stage descriptors and grids matched. That relationship establishes a matched calibration configuration; it does not make the two quantization algorithms identical. Both complete calibrated artifacts contain 42,467,328 codes. Base-checkpoint parameters outside the calibrated stages remain required.

All four models use the same unchanged ordinary binary64 NumPy quality evaluator. These likelihood evaluations are separate from the correctly rounded numerical definition used to generate the quantized models. The preceding eight-article development phase verified exact historical NLL parity on 32 common model–article outputs. No historical article was reused in this forty-article phase.

## Prespecified primary guards

The sole primary contrast is fixed128 divided by sequential128 perplexity. For article NLL sums `L_f,i` and `L_s,i`, the aggregate ratio is `exp(sum_i(L_f,i-L_s,i)/5080)`. Uncertainty resamples paired whole articles, preserving within-article token dependence. The bootstrap uses 20,000 draws of forty articles with replacement, seed 20271008, and the direct ratio's 95th percentile with linear interpolation. Because the evaluation is a fixed-pool census, this is an article-mixture stability guard; no guaranteed population confidence coverage is claimed.

| Guard | Prespecified maximum | Observed value | Result |
| --- | ---: | ---: | --- |
| One-sided bootstrap upper ratio | 1.05 | 1.001859166913 | Pass |
| Observed aggregate ratio | 1.05 | 0.988670203967 | Pass |
| Maximum individual article ratio | 1.20 | 1.084729699423 | Pass |

All three guards pass jointly. The worst article is validation row 3140, where fixed-feature perplexity is 8.47297% higher. Rows with adverse outcomes remain included. No scientific program-wide promotion is implied by a completed worker or these quality gates.

## All model totals

Perplexity is computed from pooled NLL and token counts, not an arithmetic average of article perplexities. Equal article lengths make article and token weights coincide here. NLL is measured in nats.

| Model | NLL sum | Mean NLL | Perplexity | Predictions |
| --- | ---: | ---: | ---: | ---: |
| Fixed features, 128 retained tokens | 21259.575409322 | 4.184955789237 | 65.690596621119 | 5080 |
| Sequential features, 128 retained tokens | 21317.459302240 | 4.196350256346 | 66.443386639500 | 5080 |
| Full precision | 20546.141716787 | 4.044516085982 | 57.083555816488 | 5080 |
| Nearest rounding | 22734.162622066 | 4.475228862611 | 87.814695610706 | 5080 |

## All contrasts

Secondary controls are descriptive and have no additional hypothesis-testing or model-selection role. Fixed features reduce perplexity relative to nearest rounding on all forty articles, but increase it relative to full precision on thirty-nine articles. The full-precision quality gap remains a material limitation.

| Fixed128 divided by comparator | Aggregate PPL ratio | PPL change | Article wins | Article losses |
| --- | ---: | ---: | ---: | ---: |
| Sequential128 (sole primary) | 0.988670203967 | -1.132980% | 20 | 20 |
| Nearest rounding (secondary) | 0.748059264617 | -25.194074% | 40 | 0 |
| Full precision (secondary) | 1.150779689203 | +15.077969% | 1 | 39 |

The previously exposed eight-article development result (ratio 0.9818058521) is reported separately in `docs/FOLLOWUP_QUALITY_RESULTS_V30.md`; it is not pooled into this confirmation estimate. No fixed16 comparison was included in the held-out phase. Quality was not conditioned on whether compressed repair won its separate runtime comparison, and that adverse runtime result remains preserved.

## All forty article outcomes

IDs below abbreviate `wikitext2:validation:article-row-`. Every row has 127 predictions. The four NLL columns are article sums, and the final ratio is `exp((fixed NLL - sequential NLL)/127)`. Rows follow the prospectively selected order. Full-precision and nearest individual ratios are retained in the machine-readable audit.

| Article row | Fixed128 NLL | Sequential128 NLL | Full-precision NLL | Nearest NLL | Fixed / sequential PPL |
| --- | ---: | ---: | ---: | ---: | ---: |
| 662 | 567.851479930 | 576.294894319 | 563.620748851 | 608.116955582 | 0.935678281569 |
| 759 | 620.568986946 | 619.609816189 | 594.159278579 | 639.354385506 | 1.007581117901 |
| 3582 | 617.820001856 | 617.170553030 | 598.906405491 | 661.842413573 | 1.005126867920 |
| 3417 | 588.563128587 | 595.181758507 | 559.412199953 | 610.846640271 | 0.949219514039 |
| 3490 | 445.928417460 | 452.069567287 | 440.038990136 | 515.717656038 | 0.952794998277 |
| 470 | 467.476407608 | 466.063373973 | 448.551067550 | 495.753348813 | 1.011188376006 |
| 2450 | 512.689988558 | 510.829846863 | 488.636781711 | 553.473144161 | 1.014754574771 |
| 1098 | 388.032230021 | 392.992097654 | 373.186010866 | 459.289899762 | 0.961698703069 |
| 3265 | 549.175673754 | 555.526641793 | 544.459367176 | 581.286785594 | 0.951222173925 |
| 3200 | 546.262951848 | 543.934215149 | 545.145768653 | 596.279319803 | 1.018505655498 |
| 429 | 465.055850882 | 459.274308070 | 433.513815930 | 517.760762511 | 1.046576079382 |
| 103 | 429.284480946 | 423.014081263 | 402.844939558 | 453.362017644 | 1.050612393280 |
| 3117 | 620.389870745 | 627.615715112 | 586.774319153 | 662.145862385 | 0.944691922724 |
| 3714 | 568.966632829 | 575.659800187 | 558.241889677 | 617.602312326 | 0.948662572054 |
| 2594 | 565.628931789 | 568.084026154 | 552.612441489 | 601.419186994 | 0.980854202574 |
| 1 | 532.017387270 | 529.611625172 | 502.682879072 | 564.468659765 | 1.019123565731 |
| 3347 | 483.811176295 | 475.114019078 | 465.553745561 | 531.707380309 | 1.070880870106 |
| 695 | 501.227444089 | 498.817861529 | 485.450578943 | 569.255221914 | 1.019154223848 |
| 1826 | 509.809974438 | 510.648794890 | 491.962503099 | 550.688430778 | 0.993416878859 |
| 1625 | 612.840383182 | 630.788957318 | 615.879364345 | 617.105584250 | 0.868205053560 |
| 3284 | 527.705656786 | 521.572593315 | 506.818124675 | 583.265113340 | 1.049476888247 |
| 1795 | 506.979994931 | 509.852780167 | 490.365537821 | 538.038544258 | 0.977633565862 |
| 602 | 518.853174794 | 511.769403482 | 491.643025161 | 555.074285189 | 1.057362634310 |
| 1065 | 564.261428866 | 575.563897773 | 551.612020783 | 605.429260430 | 0.914849399317 |
| 78 | 572.956064591 | 568.945163302 | 543.376989055 | 590.885059414 | 1.032085899883 |
| 2975 | 490.172618913 | 486.766102037 | 467.242746027 | 525.622068848 | 1.027185941401 |
| 554 | 546.965226415 | 550.615412098 | 511.055161674 | 557.411816505 | 0.971667491921 |
| 346 | 533.901476922 | 544.294499811 | 514.501189865 | 559.738203200 | 0.921424141535 |
| 1321 | 632.154386699 | 625.810063546 | 614.166744021 | 675.997052028 | 1.051224106051 |
| 873 | 499.305464303 | 501.643077703 | 488.276319960 | 536.906721481 | 0.981761958572 |
| 1977 | 602.930968739 | 606.790000554 | 587.445411768 | 637.391141593 | 0.970070938884 |
| 814 | 559.643496046 | 572.189649841 | 549.976669237 | 591.054377825 | 0.905934190890 |
| 47 | 485.782192195 | 482.945141608 | 456.185100919 | 507.052093238 | 1.022590364429 |
| 2071 | 557.716880698 | 558.968017456 | 538.382443948 | 587.405360966 | 0.990196896241 |
| 1757 | 524.565729450 | 523.947065256 | 508.267155568 | 565.132154471 | 1.004883256027 |
| 2320 | 502.406146064 | 498.469014890 | 489.227840381 | 526.674548513 | 1.031486569280 |
| 3140 | 579.335068174 | 569.006052637 | 556.414881577 | 623.551851059 | 1.084729699423 |
| 2018 | 465.790959747 | 476.249693935 | 455.039864746 | 514.689193833 | 0.920947509123 |
| 2722 | 525.107448238 | 522.601562585 | 517.836918903 | 547.307774671 | 1.019927333501 |
| 1221 | 469.639627718 | 481.158156705 | 456.674474905 | 498.060033225 | 0.913294325362 |

## Exposure accounting

All sixty validation-pool articles are now excluded from future confirmation. The forty rows above are added to the twenty earlier exclusions: 1040, 1299, 132, 1415, 1606, 1657, 1877, 2115, 2154, 2188, 2237, 2352, 2525, 2694, 3164, 3636, 571, 850, 955, 979. The historical twenty-article registration remains unchanged. A separate additive registry, `campaigns/heldout_quality_v30_exclusions.json`, binds all sixty exact IDs to this completion and audit. Exclusion does not depend on whether a guard passes. The separate training confirmation reserve was not selected or consumed.

The prospective metadata contamination audit found no earlier result exposure among these forty rows in the repository records it inspected. Its scope is available archived metadata; it cannot prove absence of unrecorded exposure elsewhere. The pool is exhausted for future untouched quality confirmation. Further confirmation requires prospectively chosen unexposed material and its own protocol.

## Execution and archive verification

The controller elapsed time was 115.506718715 seconds; recorded worker CPU was 115.399252000 seconds. The settled charge is 116 CPU seconds against the separate 600-second phase allowance, with no unsettled attempt or phase overrun. Peak worker RSS was 2,616,770,560 bytes. These are costs for all four model evaluations and validation work, not a repair-speed measurement.

The read-only analyzer independently recomputed every NLL aggregate, all forty article ratios, win/loss counts, the 20,000-draw bootstrap, and each guard. It checked 286 evidence-file bindings, frozen source snapshots and registration, exact command/resource admissions, terminal triplicates, sealed receipts, phase settlement, historical ledgers, calibration/model targets, complete stage grids, checkpoint/model hashes, and earlier exclusion bindings. The archive analysis took 1.739689669 CPU seconds, separately disclosed from worker accounting. Two analyzer fixtures passed. The audit is reproducible through `scripts/analyze_heldout_quality_v30.py`; its immutable outputs are never overwritten.

| Evidence | SHA-256 |
| --- | --- |
| Registered program | `44c5225d0f10d7c16422dd16329db1b9da497e2a367d0aad2266b06391692f5e` |
| Terminal completion | `8cddf9ad559d0694d30658f42d566210172657774af4a1aeffce63e186cf8591` |
| Fixed128 model | `25068a9373bb477123401124f07d5e02e09939f890fa16670d04d57e052bfce8` |
| Sequential128 model | `1789cbcc2197c43ecf3ec0a33f72a1dc3c398358fc147f0cf945b0e72cffb700` |
| Strict audit JSON | `d679554adf87bc9d2950ca6b66a2ff60d1ecc4776f77e89345dfcad6d118ba18` |
| Sixty-exclusion registry | `3a620e938c40d35daed69674f703bcb16840178cc7d9527427650a6e0de28876` |

The machine-readable audit is `campaigns/heldout_quality_v30_summary.json`. The original completion is `campaigns/heldout_quality_v30/attempts/quality-40/outputs/completion.json`. The prospective protocol is `docs/HELDOUT_QUALITY_PROTOCOL_V30.md`. Frozen registrations, workers, receipts, and earlier reports were not modified by this analysis.

## Claim that this result supports

For one frozen DistilGPT2 calibration/deletion configuration and the complete forty-article unexposed remainder of the prepared validation pool, fixed-feature quantization meets the prespecified 5% aggregate and bootstrap tolerances and 20% article tolerance relative to matched sequential quantization. It substantially improves this pool's perplexity relative to nearest rounding and remains worse than full precision. This result supplies bounded held-out quality evidence for the chosen output model; it establishes neither broad population quality, superiority over sequential quantization, cross-model generality, an original-sequential-target repair speedup, nor submission readiness of the entire paper.
