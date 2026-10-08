# Independent adaptive service review

This review checks source behavior and small software fixtures.
It does not execute a research experiment.
It does not establish practical speed, broad model quality, or publication novelty.

The reviewed final services have no remaining blocker within this review scope.
The review found admission and failure-evidence gaps before the final revisions.
The implementation now closes those gaps.
The independent fixtures pass after those changes.

## Findings and repairs

| Finding | Final behavior |
|---|---|
| Fixed preparation started before point admission. | Every point stage receives admission before context or feature preparation. |
| Model-only reconstruction replayed before admission. | Whole-request admission occurs before its first neural traversal. |
| Lossless repair decoded factors before admission. | Whole-request admission occurs before lossless decoding. |
| Fixed and lossless routes lacked explicit cumulative point limits. | Both enforce the declared request cap across all stages. |
| Native point refusal used a broader exception class. | Compressed point handling now catches `LowRankUnresolved`. |
| Fresh compressed refusal lost spent-work details. | It preserves cumulative reservations and nested failure evidence. |
| Compressed construction omitted the declared inner point cap. | Both exact-service constructors receive that cap. |
| Fixed failure details used a different attribute. | The exception now preserves both diagnostic interfaces. |
| Lossless preflight fell outside its service clock. | The outer service clock now includes preflight. |
| Fixed construction delayed some unsupported-configuration checks. | It now rejects unsupported model grids and invalid progress callbacks early. |
| Three matching terminal copies lacked a receipt commitment. | A new verifier checks the terminal digest against receipt-bound stdout. |

Missing nested failure evidence remains unknown.
It never becomes an invented zero for observed work.

## Work admission

The adaptive point dispatcher admits exactly one numerical route.
It does not try another route after numerical refusal.
The token route permits bounded coordinate refinement.
Its exact rational fallback receives zero coordinates and zero rank allowance.
The primal route checks its complete structural schedule before coefficient allocation.

Fixed and lossless services reserve all point stages before retained feature work.
Their cumulative limit does not reset between stages.
Compressed repair maintains separate cumulative limits for certificate and point work.
It also maintains a separate neural traversal limit.

The sparse certificate reserves its initial work before numerical scans.
It reserves each requested preconditioner sweep before running that sweep.
It also reserves the following row retry before coefficient construction.
Coordinate and round limits bound the adaptive loop.
The service never calls the earlier eager all-coordinate preconditioner.

A refused certificate can require exact replay.
The service admits and reserves the point solve before that replay.
Late replay traverses every required ancestor for each affected source.
Source streams retain their last position, which prevents repeated ancestor traversal.
Each successful traversal contributes to the neural counter.

Reservations are structural work limits, not observed operation counts or CPU seconds.
The array allowances are engineering bounds, not complete resident-memory guarantees.
Native compilation and opaque library workspace still need external process limits.
Neither route selection nor admission promises completion or a particular elapsed time.

Nested reservations and clocks describe the same execution at different levels.
Do not add them as separate costs.

## Target and state

The services keep the fixed-feature target and its original normalization.
They retain canonical row scales and the lower-code tie rule.
They do not replace this target with sequential calibration.
They do not use previous model values as hidden proposals.

Prior validation checks complete stage order, dimensions, grid identity, and target identity.
It checks decoder, provider, anchor, and preparer identities.
Compressed validation also checks codec precision, block size, and codec identity.
Membership checks enforce exactly the declared deletion.
Surviving token records must remain unchanged.

Replay checks source hashes and containment for every traversed factor.
Those checks include ancestors whose earlier certificates passed.
Replay does not replace stored source descriptors.
The returned state contains every calibrated stage and each surviving canonical descriptor.
Partial output never becomes a returned model.

Full deletion keeps provenance checks active.
Empty source sets do not bypass decoder or preparation identity checks.
Singleton boxes use the same admitted point dispatcher as reconstruction.

Trusted preparation still establishes the relationship between descriptors and source factors.
A descriptor hash alone cannot establish that relationship.
The service review does not remove that premise.

## Failure evidence and timing

Numerical refusal returns no model or state.
Its diagnostics preserve the relevant reservations and attempted point work.
Known replay counts remain available after point refusal.
Unknown nested counts remain explicitly unknown.
The complete worker receipt still charges actual CPU use after a failed attempt.

Lossless service diagnostics now separate the inherited clock from the complete service clock.
The complete clock includes its early admission work.
Serialized input parsing and output remain outside the in-memory service clock.
The registered transaction clock must include those external costs.

## Terminal evidence verifier

`src/terminal_evidence_v30.py` exposes `verify_completed(attempt)`.
It returns the verified terminal record without changing files.

The verifier checks these bindings:

1. Transaction receipt hash and successful worker outcome.
2. Every artifact declared by the worker receipt.
3. Worker identity, request identity, and exact plan hash.
4. Settled CPU use, rounded charge, and transaction settlement.
5. Exact equality among completion, progress, and sealed progress.
6. Terminal digest printed into receipt-bound stdout.
7. Every declared output hash and byte count.

It supports both terminal marker formats already used by V30 workers.
It rejects missing or duplicate terminal markers.
It rejects unsafe filenames, symlinks, changed bytes, and incomplete evidence.
The verifier hashes large output files incrementally.

The enclosing controller must still verify its registered program and inputs.
The verifier establishes consistency within trusted local evidence.
It does not authenticate hostile storage or prove model correctness from hashes.

The existing registered launcher remains unchanged.
The new verifier can check its completed attempts after execution.
It successfully checked `quality-001`, `scaling-128`, and `scaling-1024`.
Those checks changed no original receipt, terminal file, or registration.

## Independent fixtures

`tests/test_adaptive_service_review_v30.py` contains six independent service checks.
They test early admission, cumulative point limits, and native refusal diagnostics.
All six pass.

`tests/test_terminal_evidence_v30.py` contains nine evidence checks.
They include coherent rewriting of all three terminal files.
The receipt-bound stdout commitment rejects that rewrite.
All nine checks pass.

The existing service suite separately checks canonical histories, source containment, and full-deletion provenance.
Those tests support the review but do not replace source inspection.

```bash
python -m unittest discover -s tests -p 'test_adaptive_service_review_v30.py' -v
python -m unittest discover -s tests -p 'test_terminal_evidence_v30.py' -v
```

## Reviewed source hashes

These hashes identify the final inspected snapshots.
Changes to these files require an appropriate review update.

| File | SHA256 |
|---|---|
| `src/adaptive_calibration_v30.py` | `88cfa106918f65ca77052f633202240e231751b76be681daf9ad0b2bd89a543f` |
| `src/adaptive_fixed_service_v30.py` | `b1cd457459c6c51169eefc64d6c697aa7bb59f8f14fff707dfddfc533ecaa0bf` |
| `src/adaptive_lossless_service_v30.py` | `7c7d87677e7fa11b526c00eb6abf1de04b6da225ca8f4abb4a56a6980fc002bd` |
| `src/adaptive_compressed_service_v30.py` | `4e6b4e27ae2266357d8468726887f36bd7d08dee8088f0b412ee357f3b3cb9cc` |
| `src/sparse_box_certificate_v30.py` | `0d44c381f0abcbfab6a0de46836c3b33a419371b773b5befec71101f648008b7` |
| `src/primal_certificate_v30.py` | `d5510446c7bd4e486fe7940553e139b0c314c4bf820af14a8bff311538d6bb80` |
| `src/terminal_evidence_v30.py` | `2dbd79abb86c3eb71f7eb08af3ed7b93dfb99612e432b4926534a64c997cb3be` |
| `scripts/launch_research_v30.py` | `340cbdeec721c6ee10b2ac6c9afcfc23a0b678f5ef7a44b5b59d23315b095a8b` |
| `tests/test_adaptive_service_review_v30.py` | `17c01146c3dcd3c7e4c026e17221fa5c5e6b9210e95b27fc2db14e415d4a16e4` |
| `tests/test_terminal_evidence_v30.py` | `bab71aef9d73071487116555ebc48a90bdf51c75a6d7908225a94a8b007b8755` |
