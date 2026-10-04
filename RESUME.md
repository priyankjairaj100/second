# Resume this ACL 2027 calibration-unlearning project

Last revision: 4 October 2026, v4 implementation blockers.
Repository: https://github.com/priyankjairaj100/second

Read docs/STATUS.md, docs/PROJECT_CONTEXT.md, docs/VALIDATION.md, and docs/REFERENCE_SERVICE.md first.
Then read the consolidated report and AGENTS.md.
The user authorized repository pushes and complete restart notes.
Do not force-push or remove unrelated remote changes.

## Scientific target

Fix base weights W.
Delete calibration documents F.
Reproduce the complete retained-data sequential quantizer, including changed downstream features.
Fixed grids, ridge, normalization, order, and feature execution define the target.
This task does not remove knowledge learned in W.

Three numerical targets remain distinct.
Legacy V uses pinned finite library-math features and exact rational statistics.
New V_cert uses certified scalar nonlinear primitives and exact rational statistics.
Historical E uses floating Gram reductions and factorization.
No equality between these targets is assumed.

## Current request and phase

User: "Proceed on the remaining implementation blockers."
Research experiments remain PAUSED.
Software correctness tests are allowed.
Do not download models, start benchmarks, launch cloud jobs, or create synthetic empirical datasets without resumed authorization.

## Revision 4 implementation

- `aggregate_response_service.py` stores group sums instead of individual record matrices.
- It regenerates deleted contributions, verifies digests, subtracts exact sums, and commits canonical retained state.
- Proposal queries use aggregate statistics without retained descriptor scans.
- Record and stage metadata still require O(NL) storage and scans.
- `certified_intervals.py` supplies rational enclosures and certified binary64 nonlinear rounding.
- `certified_transformer.py` supplies automatic interval jets, full mixed Hessians, and finite-error bounds.
- A fixed affine chart constrains supported ancestor changes.
- Unsupported chart or proof conditions cause exact retained replay.
- A failure inside the finite evaluator aborts the request without committing a result.
- `checkpoint_adapter.py` imports local GPT-2 safetensors, including shards and default gelu_new.
- Checkpoint mapping does not establish native Hugging Face numerical equality.

Read docs/AGGREGATE_SERVICE.md, docs/CERTIFIED_PROVIDER.md, and docs/CHECKPOINT_ADAPTER.md for APIs and limits.
Read docs/VALIDATION.md for the final test result and source hashes.
Independent review is in theory_revision/implementation_review_v4.txt.

## Theory retained from v3

Intrinsic response jets let the surrogate follow the new certified prefix.
The complete remainder includes mixed curvature, jet approximation, residuals, and finite arithmetic.
The compact tier stores constant/linear Gram matrices plus scalar tangent moments.
Its per-group response storage is O(r d²+r²), with second-order uncertainty under stated conditions.
Shifted PSD proposals preserve the ridge floor during adaptive replay.
Local margin and error conditions imply whole-model zero retained replay.
These conditions do not establish practical coverage.

## Remaining boundaries

Realistic chart coverage, preparation costs, useful storage, latency, and NLP quality remain unmeasured.
Full-dimensional charts can be prohibitively expensive.
The scalar reference implementation is not a production GPU implementation.
The scheduler remains a separate cooperative utility.
An equally indexed fresh solver can use the same summaries.
No universal deletion-exclusive speedup is claimed.

The sharp shape constant is classical matrix geometry.
Derivative sketches, Taylor verification, and polynomial sufficient statistics have prior work.
Claim the narrow exact sequential decision and canonical-state contribution.
Do not claim exhaustive novelty or formal proof-assistant verification.
Canonical state means logical serialized state under trusted storage.
It does not mean physical Python-memory erasure.

Earlier raw experiments were pruned and remain unavailable.
PROJECT_CONTEXT labels historical metrics as reconstructed conversation evidence.
Never present them as recovered or rerun measurements.

Continue from these files.
Keep all substantive code, reports, tests, and restart context in the authorized repository.
