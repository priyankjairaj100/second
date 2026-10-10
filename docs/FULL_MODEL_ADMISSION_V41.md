# Full-model admission audit after the scale pilots

Updated 10 October 2026.
This is read-only shape analysis, not an empirical run or a new resource allowance.

The first-stage solver cannot simply be applied uniformly across the model under the current budgets.
The 24-stage target includes six MLP down projections with input width 3,072.
The first-stage pilot has width 768.
This difference changes both numerical work and workspace.

The audit reads the published target and calls the existing admission functions.
It allocates no feature or model arrays.
Results are in `validation/full_model_shape_admission_v41.json`.
Code is in `research_v41/full_model_admission.py`.

| Stage shape: rows × width | Retained tokens | Direct Gram | Streamed primal | Token point coefficients | Token box coefficients |
|---|---:|:---:|:---:|:---:|:---:|
| 2,304 × 768 | 768 | Pass | Pass | Pass | Pass |
| 2,304 × 768 | 1,536 | Pass | Pass | Pass | Refuse |
| 768 × 768 | 768 | Pass | Pass | Pass | Pass |
| 768 × 768 | 1,536 | Pass | Pass | Pass | Refuse |
| 3,072 × 768 | 768 | Pass | Pass | Pass | Pass |
| 3,072 × 768 | 1,536 | Pass | Pass | Pass | Refuse |
| 768 × 3,072 | 768 | Refuse | Refuse | Pass | Pass |
| 768 × 3,072 | 1,536 | Refuse | Refuse | Refuse | Refuse |

Primal admission uses V40's 512-MiB explicit-array budget and six-billion-unit structural work limit.
Token coefficient admission uses the existing 512-MiB and two-billion-unit defaults.
The work proxies differ and are not directly comparable runtime estimates.
Token entries admit coefficients only, excluding the complete row solver and its fallback.
No table entry guarantees process fit, certificate completion, latency, or whole-service admission.

For width 3,072, direct Gram's explicit-array envelope is 3,663,470,592 bytes.
The streamed envelope is 4,431,028,224 bytes.
Direct Gram's work proxy is 43,514,880,000 units before exact accumulation.
The streamed proxy includes additional feature products and block sums.
At 1,536 tokens, point coefficient arrays require an allowance of 604,274,688 bytes.
The box coefficient allowance is 830,963,712 bytes.

These refusals follow declared policies; they are not proofs of hardware impossibility.
Raising a budget requires a fresh reviewed process and work plan.
A larger allowance alone supplies no speed or completion guarantee.
Whole-model residency, exact Gram archives, parsing, replay, state, and output still need accounting.

## Implementation consequence

Use stage-specific solver selection based on declared dimensions and access.
At 768 retained tokens, existing token coefficient paths remain possible for the wide MLP stages.
The narrower stages can use the stronger Gram or streamed routes.
All routes must implement the same exact metric, grids, and midpoint rule.
Proof of target equivalence follows the fixed-target metric-sufficiency argument.
Their completion, runtime, and memory behavior remain separate empirical questions.

Before another complete-model run:

1. Implement the dispatcher and give compatible optimizations to every comparator.
2. Admit all stage operations, replay ancestors, live state, and output under one process plan.
3. Select explicit larger budgets or reduce the wide-stage working set, with arithmetic review.
4. Verify independent canonical successor states under the final representation.
5. Register a small real-data full-model pilot before expanding roots or models.

Do not describe the completed first-stage pilot as resolving these blockers.
Do not extrapolate its speed ratio over all 24 stages.
