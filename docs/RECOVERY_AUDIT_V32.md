# Recovery audit and fresh V32 controller

Audited 9 October 2026, UTC. No empirical worker was launched by this audit.

The restored repository starts at `604de5b830bd1386055b394df13275ef7e55475a`.
The previously described independent V31 registrations and local binary outputs did not survive.
Their conversation-only timings cannot replace receipts or ledger settlements.
The full missing phase allowance remains conservatively held elsewhere, without claiming observed use.

## Recovered state

The published V31 preparer matches the final reported hash:
`4997871262bcc8f0a9abc6e5c169fcd180bdce7e3c913ada0aa4f343d0c99e2d`.

The published independent launcher instead has hash:
`e02ef4962651020a2f87de15a5029b952af8108a8e24ac5d9690edd3f839d771`.
It differs from the final conversation-only hash beginning `00496c76`.
Published tests also precede those final review changes.
The ready specifications differ from their current preparer only in the stop-rule wording.
Neither historical specification is rewritten.

The current numerical source inventory matches the completed V31 pilot exactly.
The initial restored Python runtime contract also matches the archived contract.
That contract does not establish identical hardware or timing conditions.
A subsequent interpreter choice must receive its own registration.

Missing binary outputs include:

| Phase | Files | Total bytes |
|---|---:|---:|
| Ordered V30 | 14 | 482,881,141 |
| Compressed V31 | 4 | 166,354,536 |
| Quality extensions V30 | 1 | 22,192,646 |

Base weights and configuration were also absent initially.
A fresh clone must fetch the pinned checkpoint before preflight.

## Fresh recovery design

`scripts/launch_independent_requests_v32.py` creates new, distinct registrations.
It preserves both selected sources, token bytes, numerical policy, trial order, and resource ceilings.
Each corpus keeps seven trials and a separate 1,900 CPU-second cap.
Complete reservations sum to 1,844 seconds per corpus.

The default directories are `campaigns/independent_wikitext_v32` and `campaigns/independent_c4_v32`.
Use `--workspace local_runs/replay-001` for a separate replay after cloning published registrations without their binary outputs.
Existing registrations are never overwritten or reset.
Missing or incomplete attempts block automatic continuation.

Historical evidence is bound by `campaigns/recovery_v32/historical-bindings.json`.
Its pinned hash is:
`bf000726d2b6cc4fa4707745e1dda4d3948e96d05ce5829c8344a59842671b20`.

The controller verifies 279 published metadata files.
It checks pilot registration, plans, receipt metadata, terminal copies, stdout commitments, and settled debit consistency.
It recomputes the prior speed and storage screens from the pinned receipts.
It also checks the three archived matched-quality gates.

This is metadata verification of prior evidence.
It does not reverify unavailable historical model or state binaries.
Historical timings never enter a new V32 comparison.
These checks assume a trusted local archive; hashes alone do not prove scientific correctness.

Each new output receives live artifact, plan, schedule, source, identity, and ledger verification.
New model comparisons use the matching retained cold result within the same root.
Compressed storage compares against the matching complete lossless state.
A fresh measured 48-bit conversion is required for each root.

C4 registration follows complete, settled WikiText execution.
A numerical failure blocks dependent work.
A completed scientific loss remains reportable and does not replace either selected root.
WikiText status remains readable after its approved successor C4 ledger appears.
Other historical ledger mutations or new unapproved ledgers remain detectable.

The primary clock starts after prerequisite and bootstrap checks.
It ends after the worker receipt and receipt hash.
Final comparison checks and scientific-gate sidecar writes fall outside that clock.
Report this explicit boundary; do not call it complete shell-invocation latency.
Preparation and conversion remain additional setup costs.

## Software checks

Run:

```sh
python -m unittest tests.test_recovery_controller_v32 -v
```

All 18 focused fixtures passed during implementation.
They cover source and metadata mutation, relocation, fixed selections, comparator changes, and budget preservation.
They also cover refusal after incomplete attempts, registration ordering, replay namespaces, and nonzero exit after worker failure.
These are software fixtures, not empirical datasets.

Before registration, run:

```sh
python scripts/launch_independent_requests_v32.py --corpus wikitext --preflight
```

The controller provides `--register`, `--run ID`, `--run-next`, and `--status`.
`--run-next` runs exactly one remaining trial, never an automatic retry.
The parent task must complete independent review before registration.

## Scope still open

This recovers the selected independent-request pilot.
It does not finish additional-model experiments, realistic complete-model token scaling, or changing-state lifetime measurements.
The pooled exact-Gram comparator remains open.
The original sequential target still lacks a demonstrated repair speed advantage.
The fixed-feature result must retain its distinct numerical-target description.
