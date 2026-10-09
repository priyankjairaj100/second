# Completed C4 development campaign

Updated 9 October 2026.

All seven registered trials completed successfully.
Both lossless repairs beat their matched cold reconstruction.
Compressed repair passed its registered latency and storage gates.
CI compared all 24 stages and all 42,467,328 model codes exactly.

These results concern fixed nearest-anchor features with original normalization retained.
They do not concern ordinary sequential GPTQ calibration.
They provide development evidence from one small model and one small calibration root.
The paper remains incomplete.

## Execution and evidence

- Workflow: https://github.com/priyankjairaj100/second/actions/runs/37956045572
- Job: `113906696278`, attempt one, successful.
- Execution source: `d33626834aa830604b261b8e196dff9d3b0ca5f4`.
- Registration publication: `d712eeaa5bd35e028f26f018203adc9459ae780c`.
- Final evidence publication: `6f3ccfd987f105366c548bf1d0294a81217b4422`.
- Campaign: `campaigns/ci_v38_setup_fix/independent_c4_v32`.
- CI analysis: `analysis-v38.json` within that campaign.
- Subsequent metadata audit: `validation/ci_c4_metadata_audit_v38.json`.
- GitHub completion record: `validation/ci_c4_github_completion_v38.json`.

The registration preceded every model worker.
Each trial published its settled receipt and actual binary audit before the next trial.
No trial needed recovery, retry, or a terminal-record exception.
All three terminal copies agree for every trial.
The previous setup failure remains preserved under `campaigns/ci_v38`.
Older C4 failures and unresolved historical holds remain unchanged.

The final analysis binds 731 evidence files.
The subsequent audit checked 980 unique files against published or registered hashes.
It recomputed timing ratios, storage differences, source bindings, receipts, and CPU charges.
It also checked native certificate metadata and recorded comparisons between actual model bytes.
It performed no inference and recreated no missing model binaries.

The temporary runner compared the actual model bytes before it ended.
Git stores source snapshots, selected tokens, protocols, receipts, audit records, and full binary hashes.
The twelve derived model and state binaries are absent from this checkout.
Hashes alone do not establish correctness against a hostile execution host.

## Workload and target

The model was DistilGPT2 at revision `2290a62682d06624634c1f46a6ad5be0f47f38aa`.
The base weights remained fixed.
The original calibration contained two real C4 records with 128 tokens each.
Each request removed one record and retained the other.
These were alternative requests from one original state, not successive deletions.

| Request | Deleted record | Retained record | Method order |
|---|---|---|---|
| `c4-delete-0` | `c4:en:shard0:line2172` | `c4:en:shard0:line683` | Cold, then repair |
| `c4-delete-1` | `c4:en:shard0:line683` | `c4:en:shard0:line2172` | Repair, then cold |

The original normalization remained 256 tokens after deletion.
The fixed target hash is `9862b34f861f6155b204d57ea8219d8c8b8ccfe1a06f8053f052afb20f74b496`.
The base target hash is `df62386347772d07b5394ecd47c440282674e67bbf304d275e13fd00a03ddd39`.
The new host constructed these identities before registration.
Static construction performed no neural traversal, Gram product, quantization, or service preparation.

The runner used Ubuntu 24.04, CPython 3.12.14, NumPy 2.3.5, and gmpy2 2.3.2.
Each model worker used one CPU and a 6-GiB virtual address limit.
Recorded runtime manifests contain the detailed machine and library identities.
Operating-system caches remained uncontrolled.
The original numerical backend ran all C4 trials.
The portable metadata cross-check passed on this host but did not replace that backend.

## Complete model results

| Trial | Controller seconds | Charged CPU seconds | Retained neural stage-record pairs |
|---|---:|---:|---:|
| Original lossless preparation | 287.326505 | 287 | 48 |
| Deletion 0: cold reconstruction | 135.817410 | 136 | 24 |
| Deletion 0: lossless repair | 62.307766 | 62 | 0 |
| Deletion 1: lossless repair | 62.312363 | 62 | 0 |
| Deletion 1: cold reconstruction | 134.774331 | 135 | 24 |
| Original archive conversion | 68.670525 | 68 | 0 |
| Deletion 0: compressed repair | 88.974007 | 86 | 0 |

| Comparison | Cold / repair | Exact agreement | Codes changed from original |
|---|---:|---|---:|
| Deletion 0, lossless | 2.179783× | All 42,467,328 codes | 3,678,383 |
| Deletion 1, lossless | 2.162883× | All 42,467,328 codes | 3,623,777 |
| Deletion 0, compressed | 1.526484× | All 42,467,328 codes | 3,678,383 |

The descriptive geometric mean for lossless repair is 2.171316×.
There is one timing per method and request.
The two requests share their original model, calibration root, and host.
They do not support a population confidence interval.
No new quality evaluation ran in this campaign.

Deletion 0 has model hash `80ddeebaef59109ae2b8a4bea4655987e1ea364d6213dd49254812bd379a73a9`.
Deletion 1 has model hash `6f61d744f4a6ddddfca4a97c58c5ae9581c4997ccae737212036cee33e9defc8`.
Each complete exported model occupies 22,192,646 bytes.

## Compression mechanism and storage

All 24 compressed-stage certificates accepted.
No stage used point solving or retained neural replay.
The conversion audit verified every source hash and every feature enclosure.
Native receipts include coefficient evidence, source identities, compilation costs, and registered work limits.

The earlier WikiText root accepted 23 certificates and required eight neural traversals after one rejected stage.
This C4 result demonstrates a complete request with no such fallback.
Different inputs and hosts prevent a causal timing comparison between these roots.

| Stored state | Bytes |
|---|---:|
| Original lossless state | 79,556,145 |
| Original compressed state | 73,914,323 |
| Retained lossless state, deletion 0 | 50,882,823 |
| Retained compressed state, deletion 0 | 48,053,888 |
| Retained lossless state, deletion 1 | 50,866,783 |
| Common base checkpoint and config | 352,825,175 |

The retained compressed state saves 2,828,935 bytes, or 5.559705%, against its matched lossless state.
Including the common base checkpoint reduces that saving to 0.700738%.
These state formats already contain the calibrated model.
Adding the exported model again would double-count those model bytes.
Audit archives are separate from these deployment-state totals.

Compressed repair takes 42.797620% longer than lossless repair on deletion 0.
It therefore offers a storage–latency tradeoff, not dominance over the lossless cache.
Parser roundtrips verify canonical state encoding.
No independently prepared retained-state oracle was measured in this campaign.

## Timing and complete costs

The primary clock begins after prerequisite and static-bootstrap checks.
It ends after the worker receipt and its hash.
It includes worker startup, loading, numerical work, output, and receipt processing.
Post-receipt agreement checks, scientific gates, and archive analyses are outside that clock.
This is not the elapsed time for the whole command invocation.

Original preparation costs 287.326505 seconds.
Compression adds 68.670525 seconds.
Preparation, conversion, and the first compressed request sum to 444.971037 seconds on their recorded clocks.
This sum excludes the separate setup and analysis costs described above.
It is not a measured lifetime comparison against an equally initialized baseline.
No successive-state or amortized break-even claim follows from repeated requests against one unchanged root.

The seven model workers charged 836 CPU seconds under their separate 1,900-second phase allowance.
Their observed CPU total was 831.751420002 seconds before per-worker rounding.
Static bootstrap charged 12 CPU seconds under its separate 122-second allowance.
Both ledgers are settled, with no unresolved reservation or overrun.
Unused allowances do not authorize rerunning the closed campaign.

The seven binary audits recorded 15.094087 CPU seconds outside the worker ledger.
Final CI analysis recorded another 9.825241 CPU seconds outside that ledger.
Hosted software fixtures recorded 1.143518 child CPU seconds.
The runtime cross-check recorded 1.317452 process CPU seconds and 0.105165 child CPU seconds.
These entries are partial analysis and setup costs, not an exhaustive infrastructure CPU total.
Download, publication, and other controller work are not assigned invented zero costs.
The highest worker RSS reported by the operating system was 1,181,052 KiB.

## Supported paper wording

On one DistilGPT2 C4 calibration root, both registered lossless repairs exactly matched complete retained-data reconstruction.
Observed request times were 62.31 seconds, compared with 134.77–135.82 seconds for reconstruction.
The corresponding speedups were 2.16–2.18×.
Compressed repair matched every code in 88.97 seconds and accepted all 24 certificates without replay.
It reduced retained-state storage by 5.56% while taking 42.80% longer than lossless repair.
These development results use two alternative deletions, 128 retained tokens, and a fixed-feature target.

## Next scientific gates

1. Test real token counts below, near, and above feature width.
2. Compare complete services against dimension-appropriate Gram and factor controls with matched access and kernels.
3. Measure a useful compression frontier, including conversion, fallback, and complete stored state.
4. Measure successive deletions with an independently rebuilt retained-state oracle and preparation-inclusive lifetime costs.
5. Add another model, independent calibration roots, matched ablations, and untouched quality evaluation.
6. Freeze the method before prospective confirmation and retain all 60 exposed quality exclusions.
7. Complete the closest-work comparison and bind every manuscript claim to evidence or a conditional theorem.

See `RESEARCH_DECISION_V38.md` and `handoff/program_v38.json` for the current decision and restart state.
