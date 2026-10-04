# Executable reference service

This is a standard-library research reference for target V. It is designed to make contracts inspectable, not to provide efficient large-checkpoint quantization. Fractions can grow large; neither event counters nor software tests measure latency.

## Modules

| Module | Responsibility | Explicit boundary |
| --- | --- | --- |
| `src/exact_core.py` | Exact reverse LDL, fixed-grid rounding, conditional shape checks | Caller must establish the spectral premise |
| `src/sparse_repair.py` | Changed-code injection and exact coordinate fallback | True target factor and any unverified envelopes are premises |
| `src/response_moments.py` | Exact quadratic response index and canonical deletion | Intrinsic jet provenance/corpus independence are premises |
| `src/response_certificate.py` | Squared remainder descriptors and rational Gram-error bounds | Descriptors must be uniformly sound for the actual finite evaluator |
| `src/linear_response.py` | Lower-storage constant/linear Gram response and PSD-omission bounds | Same jet/remainder assumptions; no automatic neural differentiation |
| `src/repair_service.py` | Fresh quantization, index maintenance, bound validation, selected replay and canonical state | Evaluator/reference/proof callbacks are named trusted boundaries |
| `src/transformer_backend.py` | Deterministic complete decoder, exact dyadic features, logits/generation and service adapter | Explicit architecture/runtime; identity proof only, otherwise UNKNOWN |
| `src/work_scheduler.py` | Weighted race between cooperative exact branches | Packet cost/termination/proof and cleanup contracts supplied by caller |

The response adapter connects supplied intrinsic response payloads to the service proposal interface. Its per-record descriptor representation is a correctness-oriented integration: scanning/parsing all retained descriptors incurs O(N) reads and may store per-record matrix payloads. It is not the compact group-aggregated index promised by the optimal online complexity theorem. That requires a production index implementation. The standalone moment-index arithmetic supports compact aggregate totals; do not conflate these storage layouts.

## Deterministic decoder usage

Construct `DecoderConfig` and `DeterministicDecoder` from explicit weights, then call `make_repair_service(grids_by_stage=..., ridge=..., normalization=..., group_count=...)`. The normalization and grids stay fixed across deletion. Provide token IDs through `Record(id, decoder.record_payload(tokens))`; there is no tokenizer/model download.

```python
service = decoder.make_repair_service(
    grids_by_stage=fixed_grids_by_stage,
    ridge=1,
    normalization=original_token_normalization,
    group_count=4,
)
initial = service.fresh(records)
removed = (records[0],)
retained_by_id = {r.record_id: r for r in records[1:]}
repaired = service.repair(initial.state, removed, retained_by_id.__getitem__)
fresh_retained = service.fresh(records[1:])
assert repaired.state.canonical_bytes() == fresh_retained.state.canonical_bytes()
installed = {stage.stage_id: stage.codes for stage in repaired.state.model}
logits = decoder.logits(evaluation_token_ids, installed)
```

Consult `tests/test_transformer_backend.py` for the complete constructor and precise keyword interfaces. The repaired model is only the promised quantized stages; all frozen model configuration is bound by the job/backend manifest. The example's names are supplied by a caller, not a downloaded checkpoint.

## Complete state and proof semantics

`CanonicalState` contains the target model, retained intrinsic metadata and reference groups. The original object is immutable. Repairs validate request membership/content identity, subtract exact deleted reference contributions, then build a new model under immutable stage prefixes. Each witness binds the job, stage, complete declared ancestor prefix, group/members and candidate Gram. Unsupported types and stale/mismatched bindings raise errors; UNKNOWN triggers replay. A typed witness alone does not prove an arbitrary callback's mathematical assertion.

The state is assumed to originate from the service or an authenticated storage layer. SHA256 digest checks are content binding, not authentication of arbitrary attacker-controlled state. Canonical committed bytes exclude old models, deleted records and transient proof history. Returning a new Python object cannot securely erase the caller's old references or process memory. No physical erasure guarantee is made.

A fresh constructor and repair share the local exact quantizer. Tests additionally compare the local decisions and a changed-prefix pipeline with an independently written constrained Gaussian-elimination oracle. Full decoder tests compare complete state and logits, including a deliberately changed first quantized stage. These are implementation fixtures, not empirical NLP data.

## Numerical target

Every neural feature is a finite binary64 output of a pinned scalar program and is exported as its exact rational value. Grams and rounding are rational. Runtime manifests bind source, architecture, weights, interpreter, loaded math components and execution assumptions. This is V. It does not claim equivalence to PyTorch/GPTQ floating Gram/Cholesky target E, other hosts, or a pretrained architecture with different normalization/position/masking semantics.

The backend can establish equal stage inputs when all relevant finite ancestor weights equal the reference. Any nontrivial parameter drift returns UNKNOWN. A useful changed-prefix fast path requires a concrete certified response or finite-error provider; the abstract mathematics and callback wiring do not supply one automatically.

## Work and fairness

Engine counters count disjoint service events. Callback internals, serialization, runtime manifest checks, arbitrary precision and all backend work must be measured separately for a full cost comparison. The standalone scheduler does not automatically preempt the service or GPU kernels.

Both ordinary fresh and equally indexed fresh construction are required comparisons. An index that enables no-retained-read proposals is also available to indexed fresh construction. Report index construction, deleted-side regeneration, per-record vs aggregated payload storage, output/state costs, all failures and amortization.
