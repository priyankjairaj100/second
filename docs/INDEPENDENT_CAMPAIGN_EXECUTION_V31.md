# Conditional independent requests with native 48-bit certificates

The V30 compressed pilot failed its latency gate: 312.326876080 seconds against
140.549491491 seconds for the fastest of three optimized cold observations.
Its complete state was smaller and its output was exact. The original V30
independent specifications remain unchanged and blocked; they are not promoted
by a later algorithm's result.

The separate V31 derivative is available in:

- `campaigns/independent_requests_v31_ready/wikitext.spec.json`
- `campaigns/independent_requests_v31_ready/c4.spec.json`
- `scripts/prepare_independent_campaigns_v31.py`
- `scripts/launch_independent_requests_v31.py`

These are unregistered metadata, not completed experiments or execution
authorization. Preparing them ran no neural inference and froze no campaign.

## Conditions for activation

The derivative requires the separately registered V31 `repair-128-48` pilot to
pass exact full-model agreement, complete-state storage reduction, and its
fastest-of-three optimized cold timing screen. Its draft specification is bound
to SHA-256 `94442128d5610386af241da2e68d25968ed3ec85faec7aaa77e6606af652e024`.
The preparer rejects changed metadata rather than silently adopting new policy.
The timing screen is a conservative promotion rule, not a confidence interval.

Registration and each request also verify all completed ordered timing/model
receipts, scalar/ordered model parity, matched quality, historical control
parity, fixed-model safety, and exact model/target/source provenance. Neither a
completed conversion nor a numerically correct but slow repair satisfies the
scientific prerequisite. Every numerical source and the runtime contract must
still match the successful V31 pilot. No policy retuning is permitted using the
new roots. The full derivative design is checked, including its preparation
edges and scientific comparators; removing a prerequisite flag is rejected.

## Preserved data and schedule

The original V30 outcome-blind selection and token files are reused byte for
byte. Each root has two 128-token sources; every request retains normalization
256. Deletions are alternative branches from the same original preparation.
The first five point-trial dictionaries are unchanged.

| Root | Source IDs | Deletion-zero order | Deletion-one order |
|---|---|---|---|
| WikiText | Article rows 17380, 22925 | Repair, cold | Cold, repair |
| Bounded C4 | Shard 0 lines 2172, 683 | Cold, repair | Repair, cold |

The selected compressed request remains deletion zero. It uses native sparse
certification with 48-bit/block-256 factors, an independent 1 GiB certificate
workspace allowance, the unchanged 512 MiB point allowance, and the successful
pilot's remaining numerical policy. Its state is produced by a **new measured
48-bit conversion of this root's own original lossless state**. It cannot reuse
the old 40-bit conversion or either pilot root's state.

| Transaction per root | CPU ceiling | Wall ceiling |
|---|---:|---:|
| Original lossless preparation | 450 s | 600 s |
| Each of two lossless repairs | 180 s | 240 s |
| Each of two cold reconstructions | 300 s | 400 s |
| New 48-bit conversion | 120 s | 180 s |
| Native compressed repair | 300 s | 420 s |

Seven complete reservations total **1,844 seconds** including the two-second
margin per transaction, within a separate **1,900-second** cap per root. Process
memory remains 6 GiB and execution uses one CPU. There is no allowance pooling,
reset, source replacement, automatic retry, or automatic change of method.
These ceilings are prospective abort limits. Passing the larger pilot ceilings
does not guarantee that a new source completes within these smaller limits.

`resource-admission.json` records archive-only shape checks for both roots and
all 24 certificate stages. Such admission establishes neither acceptance nor
speed, whole-process memory fit, or completion within the CPU cap.

## Execution after prerequisites and review

Register and finish WikiText before registering C4. This preserves separate
immutable historical-ledger snapshots. The controller checks all preceding
receipts and settlements and will not skip the balanced order.

```sh
python scripts/launch_independent_requests_v31.py --corpus wikitext --register campaigns/independent_requests_v31_ready/wikitext.spec.json
```

Use `--corpus wikitext --run ID` for these seven IDs, in order:

1. `wikitext-root-prepare`
2. `wikitext-delete-0-repair`
3. `wikitext-delete-0-cold`
4. `wikitext-delete-1-cold`
5. `wikitext-delete-1-repair`
6. `wikitext-root-convert`
7. `wikitext-delete-0-compressed`

After all WikiText attempts complete and settle:

```sh
python scripts/launch_independent_requests_v31.py --corpus c4 --register campaigns/independent_requests_v31_ready/c4.spec.json
```

Use `--corpus c4 --run ID` in this order:

1. `c4-root-prepare`
2. `c4-delete-0-cold`
3. `c4-delete-0-repair`
4. `c4-delete-1-repair`
5. `c4-delete-1-cold`
6. `c4-root-convert`
7. `c4-delete-0-compressed`

The second prospectively selected root is retained irrespective of a completed
scientific loss on the first; there is no replacement by a more favorable root.
A numerical failure prevents subsequent admission until separately reviewed.
Every adverse result, refusal, or unstarted row remains reportable.

## Claims and accounting

Each compressed result is compared to its own deletion-zero cold model and
clock, and its own lossless retained state size. All comparisons are recomputed
from verified terminal evidence; changed sidecars are rejected. A scientific
loss remains a numerically completed result with a failed gate.

Report preparation and conversion as additional setup costs. This seven-trial
design does not include original model-only preparation for each new root, so
it cannot establish lifetime break-even or isolated caching overhead. One root
per corpus and two correlated deletion branches per root do not justify a
population confidence interval. These are development requests, not held-out
quality measurements or confirmation. A combined change of precision and
native coefficients is not an isolated causal test of either intervention.

Software checks:

```sh
python -m unittest tests.test_independent_campaign_specs_v31 tests.test_independent_campaign_controller_v31 -v
```

The focused suite contains 21 fixtures, including unchanged V30 file hashes,
fresh-conversion requirements, source/runtime drift rejection, failed-pilot
refusal, exact policy binding, scientific-sidecar recomputation, and prevention
of weakened quality/storage/timing gates.
