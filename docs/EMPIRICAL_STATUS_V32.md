# Empirical status after runtime recovery

Updated 9 October 2026. This report separates recovered evidence from missing work.
Read `docs/RECOVERY_EVENT_V32.md` before resuming a worker.
Use `docs/LOCAL_LLM_RESUME_V32.md` for restart commands.

## Evidence recovered from GitHub

The durable checkpoint is `604de5b830bd1386055b394df13275ef7e55475a`.
Raw receipts, plans, source snapshots, quality rows, and several completed analyses survived there.
Large model and state binaries were excluded from Git.
Later unpushed results and reviews did not survive the runtime loss.

The new read-only audit verifies 170 metadata files against that checkpoint's manifest.
It checks program, protocol, plan, receipt, worker outcome, and budget bindings.
It recomputes the timing ratios and held-out perplexities from archived observations.
Run `python scripts/audit_published_results_v32.py` to reproduce this check.

This audit does not rerun inference or verify absent model bytes.
It does not repeat the held-out bootstrap.
It does not replace the original numerical certificates or source reviews.
The V31 final analysis file is absent from the restored checkpoint.
The V31 raw completion, scientific gates, worker receipt, and transaction are available.

## Main recovered results

All speed results below concern DistilGPT2 and fixed nearest-anchor calibration features.
They do not solve the original sequential calibration target.
The main retained model has 24 calibrated stages and 42,467,328 codes.
Its recorded SHA-256 is `25068a9373bb477123401124f07d5e02e09939f890fa16670d04d57e052bfce8`.

| Experiment | Recovered result | Supported interpretation |
|---|---|---|
| Ordered lossless repair, pair 1 | 70.638 seconds versus 156.312 seconds cold | 2.213× observed request speedup |
| Ordered lossless repair, pair 2 | 72.441 seconds versus 140.954 seconds cold | 1.946× observed request speedup |
| Ordered lossless repair, pair 3 | 71.414 seconds versus 140.549 seconds cold | 1.968× observed request speedup |
| Three-pair aggregate | Geometric mean 2.039× | Three timings of one deletion workload |
| Equally indexed reconstruction | 73.290 seconds | Same numerical algorithm; no strict algorithmic advantage claimed |
| V30 compressed repair, 40-bit enclosures | 312.327 seconds; 43,925,472-byte state | Smaller state, failed latency gate |
| V31 compressed repair, 48-bit enclosures | 90.623 seconds; 48,054,240-byte state | 1.551× versus fastest earlier cold; 5.570% smaller state than lossless |
| Lossless retained state | 50,888,817 bytes | Faster repair than either compressed pilot |
| Held-out quality, 40 articles | Fixed/sequential perplexity ratio 0.988670 | Prespecified bounded-pool quality gates passed |

The ordered pairs use the same original state and deletion.
They are not three independent requests or a changing-state sequence.
The compressed pilot has one adaptive timing, compared with three earlier cold timings.
No population confidence interval supports its latency result.

V30 accepted 22 stage certificates but still needed 24 retained neural traversals.
V31 accepted all 24 certificates and needed zero retained neural traversals.
Its metadata records the same complete model as the cold reference.
Two mechanisms changed together: enclosure precision and coefficient implementation.
The experiment does not isolate their individual causal benefits.
The 48-bit setting describes stored feature enclosures, not model quantization precision.

## Quality and cost boundaries

The held-out comparison contains 5,080 predictions per model across 40 articles.
Fixed-target perplexity is 65.690597; sequential-target perplexity is 66.443387.
Article comparisons split 20 wins and 20 losses.
The archived bootstrap upper guard is 1.001859, below the prespecified 1.05 threshold.
The maximum article ratio is 1.084730, below the prespecified 1.20 threshold.
These results support bounded-pool quality preservation, not quality superiority.
Full-precision perplexity is 57.083556 and remains better.
All 60 exposed evaluation articles remain excluded from future confirmation.
Use `campaigns/heldout_quality_v30_exclusions.json`; preserve the earlier exclusion registries.

V31 preparation plus conversion costs 382.794 seconds.
Preparation, conversion, and one repair cost 473.418 seconds.
Original model construction plus the fastest cold deletion costs 427.445 seconds.
Thus the first compressed request has no demonstrated lifetime advantage.
Do not infer changing-state lifetime savings from repeated identical requests.

Every method still needs the common 352,825,175-byte base checkpoint.
Adding it gives 400,879,415 bytes for retained V31 compressed state and base weights.
The lossless counterpart uses 403,713,992 bytes.
Complete state already includes the calibrated model; do not count that model twice.
Audit archives and source datasets are separate disclosed costs.

## Recovery and independent requests

The interrupted session reportedly started an independent WikiText phase.
Its unpushed registration, receipts, ledger, and binaries are unavailable.
Do not treat conversation timing reports as recovered evidence.
The entire reported 1,900-second allowance remains an unresolved recovery hold.
This is a conservative hold, not measured CPU use.
It remains separate from the archived 15,318 charged or reserved CPU seconds.
The older 122-second unknown reservation remains within that archived total.

V32 repeats the preserved selection under a new runtime and registration.
It must preserve the numerical target, request order, precision, and stop rules.
It must use newly matched within-root timing comparisons.
This is development replication after infrastructure loss, not untouched confirmation.

| Root | Preserved selected sources | Current evidence boundary |
|---|---|---|
| WikiText | Training article rows 17380 and 22925 | V32 execution and audit pending |
| C4 | Shard-zero lines 2172 and 683 | V32 execution and audit pending |

Each source contributes 128 tokens; original normalization remains 256.
Both deletion directions are alternative requests from the same original state.
The compressed request was selected before the root's results.
Do not replace sources because a result loses.
C4 uses a bounded historical prefix, not a corpus-uniform sample.
Its source frame contained 2,278 complete records and 1,678 eligible records.

Update this section only from durable V32 completion receipts and analyses.
The original V30 and V31 registrations must remain unchanged.

## Remaining work before a broad ACL claim

| Priority | Open item | Completion evidence required |
|---|---|---|
| 1 | Finish independent WikiText and C4 roots | Every registered receipt settled; paired cold models agree; losses retained |
| 2 | Review the V32 controller and archive analysis | Runtime and input bindings; precise costs; no missing successful trials |
| 3 | Measure complete-model calibration scaling | At least one larger real-token workload; matched exact oracle; admission before execution |
| 4 | Measure the exact pooled-Gram control | Same fixed target; explicit access contract; exact accumulator costs and bit widths |
| 5 | Add another complete model | Independent checkpoint; frozen protocol; quality and exactness gates before expansion |
| 6 | Measure changing-state request sequences | Real successor states; preparation and storage costs; valid cold counterfactual at every step |
| 7 | Broaden request structure | More source counts and deletion fractions, fixed before outcomes |
| 8 | Isolate algorithmic contributions | Matched precision and backend ablations; certificate failures and replay charged |
| 9 | Run prospective confirmation | New excluded-from-development sources; frozen method; independent request units |
| 10 | Finish related-work comparison | Direct comparison with close compression, archive-unlearning, and certificate methods |
| 11 | Complete paper and reproducibility package | Claims linked to receipts; complete limitations; executable fresh-machine instructions |

The 1,024-token result is currently a component result, not a complete-model result.
Its stronger comparator reduces the reported component advantage to about 1.556×.
The pooled-Gram control remains unimplemented and unmeasured.
Read `docs/POOLED_GRAM_CONTROL_V30.md` before claiming baseline dominance.
No successful fixed-feature result removes the original sequential-target negative result.
That original complete repair took 84.225 seconds, versus 71.860 seconds cold.

Theoretical correctness remains conditional on trusted feature containment and accepted universal certificates.
Exact fallback can refuse when the declared resource budget is insufficient.
There is no unconditional wall-time speedup theorem or generic privacy guarantee.
The strongest novelty candidate concerns exact discrete output recovery from uncertain stored enclosures.
Frozen features, cached factors, and quantization stability alone are insufficient novelty claims.
The program has promising exactness, speed, and quality evidence, but remains incomplete for broad publication claims.
