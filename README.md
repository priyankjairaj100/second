# Exact calibration-data unlearning for quantized language models

This project targets an ACL 2027 paper.
It removes calibration records while keeping the base model weights fixed.
Each target reruns its complete declared quantizer on retained records.
The original sequential target and the later fixed-feature target are distinct.
The implementation defines a certified numerical target.
It does not claim native GPTQ or CUDA equivalence.

## Current state

Revisions 23–24 demonstrate a repeated development speedup for the explicit fixed-feature target.
They do not turn the original sequential-target losses into wins.

| Pair | Complete repair | Cold replay | Speedup |
| --- | ---: | ---: | ---: |
| 1 | 37.16 s | 49.45 s | 1.331× |
| 2 | 37.64 s | 48.87 s | 1.298× |
| 3 | 37.09 s | 49.26 s | 1.328× |

All completed retained model and state artifacts match exactly.
Deletion changes 1,906,485 model codes.
Repair avoids all twenty-four retained neural stage-record traversals.
Equally indexed reconstruction ties repair, as expected.
Warm replay takes 52.44 seconds; complete fresh takes 50.97 seconds.

This is one DistilGPT2 request with two sixteen-token calibration articles and one deletion.
It establishes pilot repeatability, not broad reliable speedup or lifetime superiority.
The [complete report](docs/EMPIRICAL_TIMING_V23_V24.md) preserves controls, exclusions, and evidence incidents.
The [verified summary](campaigns/fixed_feature_v23/summary.json) includes every registered outcome.

The [theory stack](docs/FIXED_COST_THEORY_V23.md) now states exactness, information, state-output, and lifetime bounds.
The [novelty audit](docs/NOVELTY_AUDIT_V23.md) rules out claiming fixed features or caching alone as new.
A [compressed factor codec](docs/FIXED_FACTOR_CODEC_V24.md) provides a tested prerequisite for a stronger contribution.
Exact output certification and complete compressed-repair speed remain unimplemented and unmeasured.
Its real-factor audit projects 11.19% less complete retained state at sixteen bits, including model and metadata.

The earlier quality screen still contains only two articles and thirty predictions.
Its fixed/sequential perplexity ratio was 0.98167, with one improving article and one worsening article.
Broader quality, preparation-inclusive lifetime cost, replication, and confirmation remain open.
The original sequential target still lacks a demonstrated full-model repair advantage.

No empirical worker is running.
The old allowance remains 10,775 / 10,800 CPU seconds.
The separate phase holds 517 recorded plus 122 unknown reserved seconds, leaving 261 / 900.
The incomplete warm attempt stays disclosed; its unavailable timing is excluded.
Thirty-six focused software tests passed.

Start with [RESUME.md](RESUME.md) and [remaining tasks](docs/RESEARCH_TODO.md).
The paper and empirical program are not complete.

## Current implementations

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
