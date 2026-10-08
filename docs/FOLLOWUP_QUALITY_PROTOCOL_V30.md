# Follow-up quality protocol

This adaptive follow-up reuses the eight exposed development articles from revision 30.
It creates no new article exclusions.
All twenty existing exclusions remain excluded from future confirmation.
It does not access the training confirmation reserve.
No result or registration exists until the controller freezes and runs this protocol.

## Primary question

Does the larger fixed-feature calibration protocol preserve quality against the archived smaller fixed-feature protocol?
The new model uses 128 retained calibration tokens.
Its original normalization contains 256 tokens from two articles.
The archived fixed-feature model uses sixteen retained tokens and normalization 32.
Thus, calibration length and normalization both change.
This contrast does not isolate the causal effect of adding calibration tokens.

The safety gate compares `fixed128` against `fixed16` in both registered modes.
The aggregate perplexity ratio must not exceed 1.05.
Every article ratio must not exceed 1.20.
The gate cannot change after results appear.

## Five controls

| Label | Retained calibration tokens | Original normalization | Role |
|---|---:|---:|---|
| `fixed128` | 128 | 256 | New model |
| `fixed16` | 16 | 32 | Primary archived control |
| `sequential16` | 16 | 32 | Unmatched secondary control |
| `nearest_rounding` | None | None | Common quantization control |
| `full_precision` | None | None | Common quality reference |

All models use the same checkpoint and architecture.
All quantized controls use the same four-bit grids.
The new model must come from completed repair after two-record preparation.
The worker checks complete model and state verification flags.
It verifies both target manifests and original normalization 256.
It checks the original articles, retained article, deletion request, and exact token prefixes.
It verifies the generation plan, source snapshot, checkpoint, terminal records, receipt, and model hash.

A matched sequential128 model is optional under a separately selected prospective mode.
The controller must choose that mode before running the follow-up.
The default mode has five models and uses fixed16 as its primary control.
The matched mode has six models and uses sequential128 as its primary control.
The matched comparison uses identical tokens, grids, normalization, and checkpoint.
It requires a completed sequential128 artifact with verified generation evidence.
The same 1.05 aggregate and 1.20 article thresholds apply to that matched comparison.
The fixed16 safety gate remains separate and unchanged.
The worker cannot switch modes after results appear.

A favorable comparison against sequential16 cannot establish superiority over matched sequential calibration.
It cannot replace the primary comparison or promote a scientific claim.

## Shared evaluation

Every model uses the existing NumPy binary64 evaluator without source changes.
The worker checks that evaluator's hash against the completed first quality pilot.
Each article contributes its first 128 tokens and 127 predictions.
The follow-up contains 1,016 predictions per model.
The default mode runs forty model-article evaluations.
The matched mode runs forty-eight model-article evaluations.
The model order rotates through the five labels for each successive article.
These timings do not measure repair speed.

The four archived controls must reproduce all thirty-two previous article losses.
The maximum permitted mean NLL deviation is `1e-8` for each comparison.
Any larger deviation aborts the follow-up.
The worker retains partial outputs after an abort.
There is no automatic retry or retuning.

The primary estimator divides total paired NLL differences by 1,016.
The worker reports every article ratio and every model's complete NLL total.
It resamples whole paired articles for 10,000 bootstrap draws with seed 31.
The reported percentile interval uses endpoints 2.5% and 97.5%.
The intervals describe reused development articles only.
They do not provide confirmation, population coverage, or independent replication.

## Plan interface

The controller invokes `python scripts/run_followup_quality_v30.py /absolute/path/to/plan.json`.
It supplies the standard source hashes, protocol hash, output path, and checkpoint directory.
The default plan uses `policy_for_mode(False)` from the worker module.
The matched plan uses `policy_for_mode(True)`.
The controller must admit the exact command before model loading.

Copy the sixteen existing input descriptors from the first quality registration.
Make their paths absolute.
Keep their original hashes and byte counts.
Add these four descriptors:

| Input key | Required file |
|---|---|
| `first_registration` | `campaigns/quality_v30/registration.json` |
| `first_completion` | `campaigns/research_v30/attempts/quality-001/outputs/completion.json` |
| `new_completion` | Completed repair's `outputs/completion.json` |
| `new_model` | That repair's `outputs/model.bin` |

The matched mode also requires `new_sequential_completion` and `new_sequential_model`.
These descriptors bind the completed sequential128 worker and its complete model.
Both can use registered late binding.
The worker checks the sequential target against the fixed model's bound base target.
It rejects missing, additional, or incompatible mode inputs.

The new completion and model can use the controller's registered late binding.
Their descriptors can omit byte counts because their hashes remain required.
The generation completion supplies the verified model byte count.
The worker derives the generation attempt from its completion path.
It then checks the generation plan and frozen source directory.
It uses the service terminal adapter for all completed attempts.
The adapter verifies named service artifacts without changing their original evidence.
The worker checks every original terminal field after adaptation.
It permits only the adapter's exact derived artifact mapping and description.

Recommended ceilings are 180 CPU seconds, 240 wall seconds, and six GiB for either mode.
Use one thread and one CPU affinity.
These ceilings are admission limits, not guaranteed completion times.
The additional complete models increase memory use above the first quality pilot.
The controller must enforce memory limits and charge the complete transaction.

The worker writes progress and an exclusive synchronized terminal file.
It prints the terminal hash into the captured log.
The controller seals progress and verifies all three terminal copies.
The result includes the unchanged exclusion list and explicit unmatched-comparator flags.

No wider quality or submission-readiness claim follows from this adaptive follow-up.

## Unregistered extension campaign

`prepare_quality_extensions_v30.py` writes an unregistered specification.
It does not freeze sources, create a phase ledger, or launch a worker.
The draft schedules three transactions:

1. Sequential calibration with 128 retained tokens and normalization 256.
2. Original fixed-feature model-only preparation with two 128-token records.
3. Matched six-model quality evaluation on the existing eight articles.

The draft phase ceiling is 2,100 CPU seconds.
Its individual ceilings are 900, 900, and 180 CPU seconds.
The largest complete reservations total 1,986 seconds.
These are separate prospective allowances, without resetting any historical ledger.

The original model-only baseline must match the existing original prepared model exactly.
Its comparison estimates preparation overhead under a model-only output contract.
It does not estimate retained repair speed.
The sequential comparator serves quality evaluation only.
Its different target prevents its time from serving as a fixed-feature repair baseline.

The draft references completed preparation and repair attempts from the existing service campaign.
Registration verifies those attempts and freezes their evidence hashes.
It resolves the new fixed-model inputs from those verified records.
It binds the sequential model through a registered dependency within the new phase.
It refuses input or plan-field replacement during external resolution.

Finish external campaign work before registering this extension.
The launcher freezes all historical ledgers and rejects subsequent changes.
This prevents concurrent phases from silently changing inherited accounting.
The launcher uses the service terminal adapter and preserves original completion bytes.

Preparation command, without inference or registration:

```bash
python scripts/prepare_quality_extensions_v30.py
```

After review and external completion, the root controller can register the draft:

```bash
python scripts/launch_quality_extensions_v30.py --register campaigns/quality_extensions_v30.spec.json
```

Each transaction then requires a separate `--run` command with its registered identifier.
The launcher never starts the next transaction automatically.
Any failure remains recorded and blocks dependent quality evaluation.
