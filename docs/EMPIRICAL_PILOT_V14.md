# Revision 14: prospective finer-grid quality control

Updated 7 October 2026. This is a new numerical target and a development pilot.

## Algorithmic change

The fixed power-of-two scale can leave nearly twofold spacing slack.
The new scale removes that slack using at most 24 significant binary digits.
It reads base weights only.
Every code and midpoint remains exactly representable in binary64.
The solver operates in original units and retains exact fallback.
It does not divide weights by arbitrary dyadic scales.
The scale theorem does not guarantee better downstream quality.

## Prospective design

One variant was frozen before either worker ran.
Four new WikiText validation articles provide sixty next-token predictions.
All four controls use the same articles, token IDs, and finite evaluator.
Both calibrated models use the same retained sixteen-token training article.
Original normalization remains thirty-two and ridge remains 0.01.
The current ten evaluation article IDs are excluded from later confirmation.
No variant was tuned on these four articles.

## Observed quality

| Model | Perplexity | Ratio to base |
|---|---:|---:|
| base | 117.698038 | 1.000000 |
| power2_calibrated | 143.887732 | 1.222516 |
| dyadic_nearest | 120.633184 | 1.024938 |
| dyadic_calibrated | 109.223199 | 0.927995 |

Fine calibrated / power-of-two calibrated perplexity: 0.759086.
Fine calibrated / fine nearest perplexity: 0.905416.

These paired observations concern only the four declared articles.
They do not estimate corpus-level quality or support a confidence interval.
The previous power-of-two quality result remains unchanged.
No scientific gate is promoted from this control.

## Execution

| Attempt | Operation | Wall seconds | Charged CPU seconds | Outcome |
|---|---|---:|---:|
| attempt-001 | Fine model construction | 257.248 | 255 | complete |
| attempt-002 | Four-model quality | 768.520 | 767 | complete |

The fine model contains 24 stages and 42,467,328 certified code decisions.
Interval decisions: 42467328; exact fallback decisions: 0.
Every model comparison includes all sixty predictions.
The quality scores use ordinary floating NLL calculations, not certified interval scores.
This pilot makes no timing or repair-state claim.

## Validation corrections

Review found three acceptance gaps.
Quality validation now rejects missing controls, repeated articles, inconsistent exclusions, and mismatched calibration membership.
It also binds generation receipts, plans, progress, checkpoints, and model artifact hashes.
These corrections preceded the quality worker.
Eight rejection tests cover those checks.

A later correction enforces the row-grid budget across all stages.
The completed DistilGPT2 target uses 663,552 entries, below the one-million limit.
The correction changes source-bound constructor hashes but no accepted grid arithmetic.
Archived workers retain their original source and target identities.
New comparisons must regenerate both models under the same source version.
The quality launcher now requires an explicit power-of-two comparator attempt.

The combined focused validation passed 61 tests.
Its source hashes and complete log are archived.
The earlier 590-test full-suite checkpoint remains historical.

## Decision

The finer-grid path is a model-code target without integrated canonical repair state.
It does not provide changed-prefix factor transport.
The existing power-of-two identity service avoids zero changed-ancestor pairs.
Reliable full-model repair speed remains unproven.
A useful successor must satisfy the exact request and lifetime cost conditions.
Those conditions appear in TRANSPORT_BOUNDARY_V14.md.

Do not expand the forty-cell campaign while its feasibility requirements remain unmet.
The inherited worker debit is 8041 CPU seconds, leaving 2759 seconds.
Controller analysis and software checks remain separate overhead.
