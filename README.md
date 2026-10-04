# Exact calibration-data unlearning for quantized language models

This ACL 2027 project removes calibration documents while matching complete retained-data sequential quantization with fixed base weights.
Start with [RESUME.md](RESUME.md), [status](docs/STATUS.md), and the [revision 8 note](docs/REVISION_8.md).

Research experiments remain paused.
Revision 8 improves comparison contracts, execution controls, feasibility decisions, and diagnostics.
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
These conditional certificate improvements do not guarantee practical acceptance or lower service cost.

The optional identity-cache family stores true sequential Grams under the current quantized model.
Matching transitive ancestors permit exact deleted-contribution subtraction.
Changed ancestors require retained replay.
Each successful request refreshes canonical cache state.

Revision 8 adds ordinary model-only fresh requantization as a separate control.
It constructs no response chart or deletion index.
The full-state direct oracle remains necessary for canonical state equality.
Faster full-state reconstruction alone cannot establish faster ordinary requantization.
Indexed fresh receives the same valid information and solver as repair within each family.
Neither family has an established deletion-exclusive solver advantage.

## Current deliverables

- [Revision 8 summary](docs/REVISION_8.md) and [complete task register](docs/RESEARCH_TODO.md)
- [Model-only comparison](docs/MODEL_ONLY_FRESH.md), [feasibility decisions](docs/FEASIBILITY_GATES.md), and [transaction timing](docs/TRANSACTION_TIMING.md)
- [Isolated campaigns](docs/ISOLATED_CAMPAIGN.md), [sequence campaigns](docs/SEQUENCE_CAMPAIGN.md), and [CPU admission](docs/EXECUTION_BUDGETS.md)
- [Arithmetic endpoint audit](docs/ARITHMETIC_AUDIT.md) and [bounded certificate diagnostics](docs/CERTIFICATE_DIAGNOSTICS.md)
- [35-page revision 7 theory report](output/pdf/theory_algorithm_revision.pdf) and [LaTeX source](reports/theory_algorithm_revision.tex)
- [Interval theory](docs/ALGORITHM_ADVANCE_V7.md), [publication theory](docs/PUBLICATION_THEORY.md), and [claim evidence](docs/CLAIM_EVIDENCE.md)
- [Original-model cache](docs/IDENTITY_CACHE.md), [quadratic control](docs/QUADRATIC_CONTROL.md), and [box theory](docs/BOX_THEORY.md)
- [Target contract](docs/TARGET_CONTRACT.md), [numerical contract](docs/NUMERICAL_CONTRACT.md), and [prospective protocol version 4](configs/protocol_v4.json)
- [Validation](docs/VALIDATION.md), [independent review](theory_revision/), [project history](docs/PROJECT_CONTEXT.md), and [restart prompt](docs/RESTART_PROMPT.md)

The consolidated PDF remains the unchanged 35-page revision 7 report.
Read the revision 8 note and linked contracts for current execution and comparison details.

## Verification and status

```bash
python -m unittest discover -s tests -v
```

The final revision records **417 correctness tests**.
The register contains **29 completed and 49 open required tasks**, plus **12 conditional extensions**.
C04 now closes the written feasibility-policy requirement.
C05, D04, and D05 remain partial under their complete criteria.
The experiment-ready gate G0 remains open.

Frozen isolated campaigns now support inventory-verified confirmation dispatch and an optional dedicated quality worker.
Frozen sequence campaigns bind ordered requests, predecessor lineage, complete products, and durable failure evidence.
Feasibility now has its own supported phase and explicit CPU allowance.
No current protocol authorizes research execution.

The external observer measures declared child transactions through final child commitments, cleanup, and output verification.
Its own final timing receipt remains outside the clock.
Model-only, canonical-state, comparison, and sequence output contracts remain separate.
Primary full-clock campaign integration and model-only confirmation inventory remain open.

Arithmetic audits observe rational endpoints and available process memory without changing numerical operations.
Embedded profiling flags exclude those runs from clean timing ratios.
The certificate funnel reports bounded numerical detail and disposition counts for recorded stages and events.
Omission and saturation counters expose lost detail.
Hidden arithmetic intermediates and unavailable provider internals remain outside these diagnostics.

Real inputs, feasible model execution, frozen settings, actual partitions, precision, and empirical evidence remain outstanding.
The three-request lifetime gate compares all required preparation and request costs against model-only fresh construction.
Its thresholds are prospective engineering choices.
No current result passes or tests that gate on real data.

The user's “maximum revenue” request is interpreted as research value within this paper program.
No monetary return is predicted or guaranteed.
Synthetic empirical datasets remain deferred.
No model weights, raw corpus, credentials, or missing historical raw results are included.
