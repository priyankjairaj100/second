# Exact calibration-data unlearning for quantized language models

This ACL 2027 project removes calibration documents while matching complete retained-data sequential quantization with fixed base weights.
Start with [RESUME.md](RESUME.md), [status](docs/STATUS.md), and the [revision 9 note](docs/REVISION_9.md).

Research experiments remain paused.
Revision 9 completes another preparation pass on measured comparisons, ordered lifetime costs, runtime and instrumentation contracts, conditional feasibility decisions, and provider diagnostics.
It does not establish practical model feasibility, useful certificate coverage, language quality, or reliable full-model speedup.

## Scientific program

Fixed intrinsic response moments generate candidate-dependent Gram matrices without changing the sequential target.
Sound uncertainty bounds and exact decision certificates justify accepted stages.
Unresolved stages use exact retained replay.
Canonical state supports repeated deletion.

The compact response tier stores O(r d²+r²) rational slots per group.
The full quadratic tier stores the complete Gram polynomial of the same affine feature response.
Fixed parameter boxes provide another domain construction without an affine-span restriction.
A spectral-first, ridge-aware interval verifier can certify additional decisions after spectral rejection.
These conditional improvements do not guarantee useful acceptance or lower service cost.

The optional identity-cache family stores true sequential Grams under the current quantized model.
Matching transitive ancestors permit exact deleted-contribution subtraction; changed ancestors require retained replay.
Each successful request refreshes canonical cache state.
The response solver ignores old model codes; the cache solver uses the previous model.
Indexed fresh receives identical valid information and solver policy within each family.
Neither family establishes a deletion-exclusive solver advantage.

Ordinary model-only fresh requantization constructs no response chart or deletion index.
It is the primary ordinary-speed baseline.
The direct full-state oracle supplies canonical-state correctness, and equally indexed fresh supplies a separate maintenance comparison.
A gain against rebuilding deletion state alone cannot establish faster ordinary requantization.

## Current deliverables

- [Prospective manuscript](docs/MANUSCRIPT_DRAFT.md), [evidence slots](docs/MANUSCRIPT_EVIDENCE_SLOTS.md), and [primary-source citation check](docs/CITATION_CHECK_V9.md)
- [Revision 9 summary](docs/REVISION_9.md) and [complete task register](docs/RESEARCH_TODO.md)
- [Measured comparisons](docs/MEASURED_COMPARISON.md), [frozen campaigns](docs/MEASURED_CAMPAIGN.md), [ordered sequences](docs/MEASURED_SEQUENCE.md), and [artifact-verified analysis](docs/MEASURED_ANALYSIS.md)
- [Model-only control](docs/MODEL_ONLY_FRESH.md), [feasibility policy](docs/FEASIBILITY_GATES.md), and [conditional decision evaluator](docs/FEASIBILITY_DECISION.md)
- [Transaction timing](docs/TRANSACTION_TIMING.md), [verified diagnostic breakdown](docs/DIAGNOSTIC_BREAKDOWN.md), [CPU admission](docs/EXECUTION_BUDGETS.md), and [prospective protocol version 5](configs/protocol_v5.json)
- [Provider diagnostics](docs/PROVIDER_DIAGNOSTICS.md), [certificate diagnostics](docs/CERTIFICATE_DIAGNOSTICS.md), and [arithmetic endpoint audit](docs/ARITHMETIC_AUDIT.md)
- [35-page revision 7 theory report](output/pdf/theory_algorithm_revision.pdf) and [LaTeX source](reports/theory_algorithm_revision.tex)
- [Interval theory](docs/ALGORITHM_ADVANCE_V7.md), [publication theory](docs/PUBLICATION_THEORY.md), and [claim evidence](docs/CLAIM_EVIDENCE.md)
- [Original-model cache](docs/IDENTITY_CACHE.md), [quadratic control](docs/QUADRATIC_CONTROL.md), and [target contract](docs/TARGET_CONTRACT.md)
- [Validation](docs/VALIDATION.md), [project history](docs/PROJECT_CONTEXT.md), and [restart prompt](docs/RESTART_PROMPT.md)

The consolidated PDF remains the unchanged 35-page revision 7 report.
Read the revision 9 note and current contracts for later implementation and measurement changes.

## Verification and status

```bash
python -m unittest discover -s tests -v
```

The final revision records **524 correctness tests**.
The register contains **29 completed and 49 open required tasks**, plus **12 conditional extensions**.
G0 remains open.
C04 closes the written feasibility-policy requirement; software decision logic does not establish policy attainment.
C05 and D05 remain partial under their full criteria; the final register records the D04 review disposition.

Frozen measured campaigns now bind all four methods, actual runtime, source and input hashes, complete planned products, clean or diagnostic execution, and model-only confirmation membership.
Each method has a fresh limited process and an external transaction observer.
Ordered measured sequences separately charge indexed original preparation and ordinary original model construction, then every actual request.
Repair and indexed fresh share one preparation observation without treating it as independent evidence.
The charged predecessor check uses the state-producing child receipt and artifacts; external research lineage and oracle checks remain separate.

Artifact-aware analysis verifies clocks and exact outputs, retains missing and failed slots, and rejects duplicated original observations across repetitions.
It clusters inference by calibration root.
Only the sole registered primary comparison and configuration can receive confirmation timing flags.
Secondary indexed and full-state ratios remain separate descriptions.
Clean mode disables optional Python diagnostics while retaining required exact ledgers and correctness work.
Native profiling is unobserved, and operating-system caches remain uncontrolled.

The observer includes child commitments, cleanup, worker accounting, and output validation.
Its bootstrap and final observer receipt remain excluded.
Lifetime sums use this declared transaction boundary; they are not the elapsed wall time of the research harness.
CPU admission covers trusted local children under one protocol ledger, excluding controller CPU and cross-protocol physical guarantees.

The feasibility evaluator computes conditional decisions from the frozen policy.
The public bridge derives available lifetime, coverage, quality, and resource facts from verified clean and diagnostic archives.
It includes the full protocol-ledger snapshot and archived transaction/nontransaction files, with explicit read-time scope.
Missing scientific provenance, unmatched diagnostics, failed observations, or incomplete accounting remain inconclusive.
No current real-data result tests or passes that policy.
Provider diagnostics expose available proof components with bounded omissions; hidden arithmetic intermediates and exhaustive primitive traces remain outside scope.

Actual inputs, a resource-feasible model, primary configuration, source pools, workloads, empirical inventories, precision justification, experiments, and manuscript completion remain outstanding.
The user's “maximum revenue” phrase means research value within this paper program, without monetary guarantees.
Synthetic empirical datasets remain deferred.
No model weights, raw corpus, credentials, or missing historical raw results are included.
