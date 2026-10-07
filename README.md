# Exact calibration-data unlearning for quantized language models

This project targets an ACL 2027 paper.
It removes calibration records while keeping the base model weights fixed.
The counterfactual target reruns the complete declared sequential quantizer on retained records.
The implementation defines a certified numerical target.
It does not claim native GPTQ or CUDA equivalence.

## Current state

Revision 16 implements and reviews two exact speculative quantizers.
Twenty completed real-data stage comparisons matched their sequential reference.
Every completed speculative variant was slower on this CPU.
Eight further registered cells remained unstarted after a worker timeout.
The block successor completed both WikiText and bounded C4 pilots.
Reference quantization remains the default.

Revision 15 still provides complete finer-grid model and canonical-state repair evidence.
All 42,467,328 retained codes matched the earlier quality model.
That quality pilot used four new articles and sixty predictions.
Its positive signal remains exploratory.

Reliable full-model repair speed, useful factor transport, and confirmation remain unresolved.
The forty scientific cells remain unpromoted.
The novelty audit attributes fixed-point and parallel quantization principles to prior work.

Start with [RESUME.md](RESUME.md), [current results](docs/EMPIRICAL_PILOT_V16.md), and [remaining tasks](docs/RESEARCH_TODO.md).
Read [the proof](docs/SPECULATIVE_QUANTIZER_PROOF_V16.md) and [the novelty audit](docs/NOVELTY_AUDIT_V16.md).
All workers are settled. The inherited remaining allowance is 977 CPU seconds.
The final focused regression passed 58 tests.

## Current implementations

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
