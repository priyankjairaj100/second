# Independent WikiText and bounded-C4 execution contracts

The selected roots now have complete launcher-ready specifications:

- `campaigns/independent_requests_v30_ready/wikitext.spec.json`
- `campaigns/independent_requests_v30_ready/c4.spec.json`

The original selection, token files, and outcome-blind draft remain unchanged.
The preparer verifies their fixed hashes. The five point-trial dictionaries
are preserved exactly. Conversion and compressed repair are appended without
changing the selected deletion-zero control.

The controller is `scripts/launch_independent_requests_v30.py`. No independent
campaign was registered and no model was evaluated while preparing it.

## Mandatory prerequisites

Registration and every subsequent request recheck the existing ordered model
and timing evidence, scalar/ordered output equality, and matched quality.
Quality requires the fixed-model safety gate, matched sequential gate, historical
control parity, and exact model/target/source provenance.

The registered compressed V30 pilot must additionally have passed its complete
model comparison, storage gate, and fastest-cold timing gate. The independent
program copies the exact successful pilot policy. It cannot retune that policy
using either new root. A failed or unavailable prerequisite blocks registration
before source directories, budgets, or attempts are created.

If the current compressed V30 pilot fails its scientific gate, **these exact
specifications remain blocked**. A later algorithm would need a separately
reviewed prospective amendment; success is not inferred from a new version.

## Preserved schedule and budgets

| Root | First deletion pair | Second deletion pair |
|---|---|---|
| WikiText 17380 / 22925 | Repair, cold | Cold, repair |
| Bounded C4 line2172 / line683 | Cold, repair | Repair, cold |

Both sources contain 128 tokens. Every retained request preserves original
normalization 256. Each deletion is an alternative branch from the same
original state. Every request receives the corresponding original receipt;
the cold worker never receives prior state.

| Transaction per root | CPU ceiling | Wall ceiling |
|---|---:|---:|
| Original preparation | 450 s | 600 s |
| Each of two lossless repairs | 180 s | 240 s |
| Each of two cold reconstructions | 300 s | 400 s |
| Compressed conversion | 120 s | 180 s |
| Selected compressed repair | 300 s | 420 s |

Seven complete reservations total **1,844 seconds**, including seven two-second
reservation margins. Each root has a separate **1,900-second** phase cap. There
are no retries, source replacements, allowance resets, or pooling.

Shape admission on the archived 24-stage model passes for both specifications.
Original preparation reserves 66,280,243,200 point-work units. Each retained
request reserves 21,233,418,240 point-work units. The compressed request admits
all 24 certificate stages with the reviewed independent 1 GiB certificate
allowance; the matched point allowance remains 512 MiB. Details are in
`campaigns/independent_requests_v30_ready/resource-admission.json`.

These checks show that the declared structural schedules fit their budgets.
They do not guarantee certificate acceptance, process memory fit, CPU completion,
or a speed advantage. The timing ceilings have limited headroom on new sources.

## Execution after all prerequisites pass

Register WikiText first:

```sh
python scripts/launch_independent_requests_v30.py --corpus wikitext --register campaigns/independent_requests_v30_ready/wikitext.spec.json
```

Run one transaction at a time with `--corpus wikitext --run ID`, in this order:

1. `wikitext-root-prepare`
2. `wikitext-delete-0-repair`
3. `wikitext-delete-0-cold`
4. `wikitext-delete-1-cold`
5. `wikitext-delete-1-repair`
6. `wikitext-root-convert`
7. `wikitext-delete-0-compressed`

The controller verifies every preceding receipt before admission. It cannot
skip the balanced order or overwrite an existing attempt. A numerical failure
or exact-model mismatch stops later admission and remains preserved.

Only after all WikiText transactions finish and settle, register C4:

```sh
python scripts/launch_independent_requests_v30.py --corpus c4 --register campaigns/independent_requests_v30_ready/c4.spec.json
```

Use `--corpus c4 --run ID` in this order:

1. `c4-root-prepare`
2. `c4-delete-0-cold`
3. `c4-delete-0-repair`
4. `c4-delete-1-repair`
5. `c4-delete-1-cold`
6. `c4-root-convert`
7. `c4-delete-0-compressed`

Sequential registration preserves separate immutable historical-ledger
snapshots. Registering both roots before executing the first is unsupported.

## Output and interpretation

Every attempt preserves a complete process receipt, CPU settlement, controller
clock, canonical output artifacts, and immutable terminal evidence. Model
comparisons and scientific storage/timing gates are recomputed on dependency
reads. A forged sidecar cannot turn a mismatch or loss into a pass. A scientific
loss remains a completed numerical result with a failed gate.

Report every timing and storage result, including adverse and unstarted rows.
Original preparation and conversion remain setup costs. The seven-trial design
omits per-root original model-only preparation, so it cannot establish lifetime
break-even or isolated caching overhead. One root per corpus and two correlated
deletions per root do not support a population confidence interval. These are
development requests, not new quality measurements or confirmation.

Software verification:

```sh
python -m unittest tests.test_independent_campaign_specs_v30 tests.test_independent_campaign_controller_v30 -v
```
