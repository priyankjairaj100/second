# Exact calibration-data unlearning for quantized language models

This project targets an ACL 2027 paper.
It removes calibration records while keeping the base model weights fixed.
Each target reruns its complete declared quantizer on retained records.
The original sequential target and the later fixed-feature target are distinct.
The implementation defines a certified numerical target.
It does not claim native GPTQ or CUDA equivalence.

## Current state

Revision 28 implements exact complete repair from compressed source-local evidence.
It uses the explicit fixed nearest-grid feature target.
It does not establish faster repair of the original sequential target.

| Complete transaction | Time | Result |
| --- | ---: | --- |
| V27 compressed repair | 90.496 s | Exact model and complete state |
| V28 compressed repair | 51.232 s | Exact model and complete state |
| Matched cold reconstruction | 51.180 s | Exact model only |

Selective verification retries six unresolved rows instead of repeating whole-stage work.
All 24 stages and 42,467,328 model codes match the retained reference.
Repair executes zero neural stage-record traversals.
The retained complete state is 24,930,099 bytes, 5.3026% smaller than exact-factor state.
The common base checkpoint remains required for uncalibrated parameters.

This is a latency tie, not a demonstrated compressed-repair speed advantage.
It is one adaptive development retiming against an earlier same-session cold comparator.
The cold run has contradictory live progress metadata.
Its sealed receipt, completion logs, and verified model support completion; the discrepancy remains disclosed.
Read the [complete report](docs/EMPIRICAL_COMPRESSION_V25_V28.md) and [bound summary](campaigns/compressed_summary_v25_v28.json).

The exact-factor V23 route retains its three observed 1.298–1.331× cold-reconstruction speedups.
Equally indexed reconstruction ties repair because it shares the same information and algorithm.
Those results use a larger saved state and the same tiny DistilGPT2/WikiText request.
They do not establish broad superiority, lifetime benefit, or a compressed-service win.
See the [earlier timing report](docs/EMPIRICAL_TIMING_V23_V24.md).

The [theory stack](docs/FIXED_COST_THEORY_V23.md) states conditional correctness, information, state-output, and lifetime bounds.
The [novelty audit](docs/NOVELTY_AUDIT_V23.md) rules out claiming fixed features or caching alone as new.
The compressed service now supplies universal output certificates and bounded replay fallback.
The [sparse verification argument](docs/BALL_BOX_V28.md) preserves exactness when combining complete certified rows.

Quality evidence still contains only two articles and thirty predictions.
Broader quality, realistic calibration sizes, additional models, independent requests, lifetime costs, and confirmation remain open.
All twelve evaluated articles remain excluded from future confirmation.
The paper and empirical program are not complete.

No empirical worker is running. No further empirical run fits the remaining phase allowance.
The original ledger remains 10,775 / 10,800 CPU seconds.
The separate phase holds 898 / 900 seconds: 776 recorded and 122 unknown reserved.
The allowances are not pooled or reset.
The final focused suite passed all [140 software tests](campaigns/compressed_software_check_v28.json).
Start with [RESUME.md](RESUME.md) and [remaining tasks](docs/RESEARCH_TODO.md).

## Current implementations

- [Compressed complete repair with sparse verification](docs/FIXED_COMPRESSED_SERVICE_V28.md)
- [Canonical compressed state](docs/FIXED_COMPRESSED_STATE_V26.md)
- [Wider dyadic enclosure codec](docs/FIXED_FACTOR_CODEC_V26.md)
- [Sparse row certificate and proof](docs/BALL_BOX_V28.md)

- [Complete sequential anchor provider](docs/ANCHOR_TRANSFORMER_V20.md)
- [Canonical sequential anchor service](docs/ANCHOR_SERVICE_V20.md)
- [Explicit fixed-feature target and service](docs/FIXED_ANCHOR_V21.md)
- [Minimal fixed-factor state](docs/FIXED_FACTOR_V22.md)
- [Shared evaluator setup](docs/EVALUATOR_SETUP_V22.md)

- [Canonical compact state](docs/COMPACT_STATE_V13.md)
- [Exact dyadic state encoding](docs/COMPACT_DYADIC_STATE_V15.md)
- [Complete dyadic identity service](docs/DYADIC_COMPACT_SERVICE_V15.md)
- [Complete repair and four comparison methods](docs/COMPACT_SERVICE_V13.md)
- [Finite transformer boxes](docs/FINITE_FEATURE_BOXES_V13.md)
- [Exact codes over feature boxes](docs/TOKEN_BOX_CERTIFICATE_V13.md)
- [Common solver batching](docs/BATCHED_TOKEN_SOLVER_V13.md)
- [Original token-space solver](docs/TOKEN_SPACE_SOLVER_V12.md)
- [Fixed output-row grids](docs/ROW_SCALED_TARGET_V12.md)
- [Fine dyadic row grids](docs/DYADIC_ROW_TARGET_V14.md)
- [Revision 12 diagnostic report](docs/EMPIRICAL_PILOT_V12.md)

## Reproduction

Install `requirements-local.txt` and restore pinned inputs with `scripts/acquire_pilot_inputs.py`.
These certified workers currently use CPU execution.
The commands show dependency order; admission remains subject to the inherited allowance.
Use fresh attempt IDs.
Never overwrite published attempts or reuse their clocks as new observations.
Later validation guards changed source-bound target hashes.
Regenerate preparation and comparators under one source version, or use the exact archived snapshots.

```bash
python scripts/launch_compact_service_pilot.py --revision v15 --grid-axis dyadic_row --solver-backend batched --id replica-001 --method direct_fresh
python scripts/launch_compact_service_pilot.py --revision v15 --grid-axis dyadic_row --solver-backend batched --id replica-002 --method repair --delete-index 0 --prior-attempt replica-001
python scripts/launch_compact_service_pilot.py --revision v15 --grid-axis dyadic_row --solver-backend batched --id replica-003 --method model_only_fresh --delete-index 0
python scripts/launch_compact_service_pilot.py --revision v15 --grid-axis dyadic_row --solver-backend batched --id replica-004 --method indexed_fresh --delete-index 0 --prior-attempt replica-001
python scripts/launch_compact_service_pilot.py --revision v15 --grid-axis dyadic_row --solver-backend batched --id replica-005 --method direct_fresh --delete-index 0
```

Use `--solver-backend batched` equally for every compatible method when comparing that implementation.
The inherited CPU allowance applies across later revision directories.
The launcher rejects overlapping workers and unsettled prior reservations.
Model arrays and complete state arrays remain local.
Published hashes bind those reproducible artifacts.
A fresh clone must regenerate them before using a previous state.

The forty-cell scientific program and its original gates remain in [the empirical plan](docs/LOCAL_EMPIRICAL_PROGRAM.md).
The user authorized execution here after that older local handoff.
Large campaigns require the remaining scientific conditions.
The current identity cache cannot satisfy the changed-ancestor avoidance condition.
