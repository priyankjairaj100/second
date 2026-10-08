# Exact calibration-data unlearning for quantized language models

This project targets an ACL 2027 paper.
It removes calibration records while keeping the base model weights fixed.
The counterfactual target reruns the complete declared sequential quantizer on retained records.
The implementation defines a certified numerical target.
It does not claim native GPTQ or CUDA equivalence.

## Current state

Revisions 20–22 reassess the remaining speed losses and implement a separate fixed-feature calibration target.
The original sequential target still lacks a demonstrated full-model repair advantage.
The [reassessment report](docs/EMPIRICAL_REEVALUATION_V20_V21.md) separates implementation defects from structural limits.

The new target makes retained feature reuse exact.
It changes the original sequential calibration rule explicitly.
A complete DistilGPT2 model passed a tiny, prospectively registered quality screen.
Its aggregate perplexity ratio to the archived sequential model was **0.98167**.
That screen contains only two articles and thirty predictions.
The individual ratios were **0.88282** and **1.09159**.
It does not establish broad quality.

The optional [minimal factor state](docs/FIXED_FACTOR_V22.md) reduced archived storage by **51.34%**.
State size fell from 54,107,392 to 26,326,066 bytes.
All model codes and feature bytes remained equal.
Fresh preparation avoids unused transformer-bound summaries.
The [common evaluator optimization](docs/EVALUATOR_SETUP_V22.md) removes redundant exact-value scans.
The final focused suite passed **49 tests**.

The original route received a complete anchor provider and service.
A real-data witness rejects its current anchor-centered constant-output certificate at the checked stage.
Tightening those radii cannot remove the witnessed contradiction.
This does not reject every target-preserving repair algorithm.

Reliable repair speed, larger quality validation, lifetime cost, and a defensible novel contribution remain open.
Equally indexed reconstruction shares the fixed-feature optimization.
Its expected tie remains visible.
The earlier native kernel improvement also remains available to all compatible comparators.

Start with [RESUME.md](RESUME.md), [verified results](pilots/v21/summary.json), and [remaining tasks](docs/RESEARCH_TODO.md).
All workers are settled.
The original allowance has **25 CPU seconds remaining**.
No complete empirical program or confirmation success is claimed.

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
