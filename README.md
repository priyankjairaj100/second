# Exact calibration-data unlearning for quantized language models

This ACL 2027 project removes calibration documents while matching complete retained-data sequential quantization with fixed base weights.
Start with [RESUME.md](RESUME.md), [status](docs/STATUS.md), and the [task register](docs/RESEARCH_TODO.md).

Research experiments remain paused.
Revision 7 develops algorithms, controls, execution infrastructure, and software correctness evidence.
It does not establish practical model feasibility, useful certificate acceptance, or reliable full-model speedup.

## Current contribution

Fixed intrinsic response moments generate candidate-dependent Gram matrices without changing the sequential target.
Sound uncertainty bounds and exact decision certificates justify accepted stages.
Unresolved stages use exact retained replay.
Canonical state supports repeated deletion.

The compact response tier stores O(r d²+r²) rational slots per group.
The full quadratic control stores the complete Gram polynomial of the same affine feature response.
Fixed parameter boxes provide another domain construction without an affine-span restriction.
They do not guarantee useful numerical bounds.

Revision 7 adds a ridge-aware interval verifier after spectral rejection.
The portfolio preserves existing spectral acceptances when its arithmetic completes.
Signed covariance intervals, ridge-safe reverse elimination, and exact rounding-cell checks can admit additional candidates.
A mathematical fixture establishes strict certificate improvement.
It does not establish real-model acceptance frequency or speed.

An optional identity-cache family stores true sequential Grams under the current quantized model.
It subtracts deleted contributions when every relevant old and new ancestor agrees.
Changed ancestors require retained replay.
Each successful request refreshes canonical cache state.

## Deliverables

- [Consolidated theory report](output/pdf/theory_algorithm_revision.pdf) and [LaTeX source](reports/theory_algorithm_revision.tex)
- [Revision 7 theory and algorithm](docs/ALGORITHM_ADVANCE_V7.md), [publication theory](docs/PUBLICATION_THEORY.md), and [claim evidence](docs/CLAIM_EVIDENCE.md)
- [Original-model cache](docs/IDENTITY_CACHE.md), [quadratic control](docs/QUADRATIC_CONTROL.md), and [box theory](docs/BOX_THEORY.md)
- [Ordered deletion execution](docs/SEQUENCE_EXECUTION.md), [isolated comparison](docs/ISOLATED_COMPARISON.md), and [CPU admission](docs/EXECUTION_BUDGETS.md)
- [Target contract](docs/TARGET_CONTRACT.md), [numerical contract](docs/NUMERICAL_CONTRACT.md), and [fair baselines](docs/BASELINES.md)
- [Empirical protocol](docs/EMPIRICAL_PROTOCOL.md), [source selection](docs/SOURCE_SELECTION.md), and [prospective protocol version 3](configs/protocol_v3.json)
- [Validation](docs/VALIDATION.md), [independent review](theory_revision/), [project history](docs/PROJECT_CONTEXT.md), and [restart prompt](docs/RESTART_PROMPT.md)

## Verification and status

The reference modules use the Python standard library.
The certified decoder declares its scalar binary64 runtime, operation order, model, and source bindings.

```bash
python -m unittest discover -s tests -v
python scripts/build_report.py
```

The PDF build also requires LaTeX and the packages listed in its preamble.
The final revision records **340 correctness tests** and a **35-page report**.
The register contains **28 completed and 50 open required tasks**, plus **12 conditional extensions**.
The experiment-ready gate G0 remains open.

The response solver ignores old model codes.
The identity-cache solver uses its previous quantized model to justify feature reuse.
Indexed fresh receives the same valid information and solver within each family.
Neither family establishes a deletion-exclusive solver advantage.
Extra split-interface validation or serialization cannot support such a claim.

Separate-process comparisons include setup and three method workers with explicit limits and durable receipts.
Their clocks include the declared worker boundary, not the complete parent transaction.
Operating-system caches remain uncontrolled.
CPU admission applies to workers sharing one frozen protocol ledger.
It is not an absolute hardware, hostile-process-tree, or cross-protocol cap.

Local sequence execution supports successive, empty, and complete deletion with restart verification.
Bulk sequence campaign admission remains open.
Isolated confirmation inventory support and isolated quality evaluation remain open.
Feasible real inputs, complete timing, transient arithmetic diagnostics, statistical precision, and empirical evidence also remain open.

The latest request seeks further progress and “maximum revenue.”
We interpret that phrase as research value within this paper program.
No monetary return is predicted or guaranteed.

Synthetic empirical datasets remain deferred.
No model weights, raw calibration corpus, credentials, or missing historical raw results are included.
Earlier measurements appear only as explicitly reconstructed context.
