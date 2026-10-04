# Exact calibration-data unlearning for quantized language models

Research project targeting ACL 2027: remove calibration documents while matching the complete retained-data sequential quantizer with fixed base weights.

Start with [RESUME.md](RESUME.md), [status](docs/STATUS.md), and [project context](docs/PROJECT_CONTEXT.md).

The latest revision develops **deletable response moments**: stored intrinsic feature responses generate a candidate-dependent Gram, while rigorous uncertainty and discrete decision certificates preserve the original sequential target. A lower-storage tier keeps O(r d²+r²) values per group instead of O(r² d²). Exact replay handles unresolved cases. Canonical state supports repeated deletions.

## Deliverables

- [Consolidated theory report](output/pdf/theory_algorithm_revision.pdf) and [LaTeX source](reports/theory_algorithm_revision.tex)
- [Novelty audit](docs/NOVELTY_AUDIT.md) and [claim ledger](docs/THEOREM_LEDGER.md)
- [Algorithm specification](docs/ALGORITHM_SPEC.md) and [numerical contract](docs/NUMERICAL_CONTRACT.md)
- [Implementation guide](docs/REFERENCE_SERVICE.md), [status](src/IMPLEMENTATION_STATUS.txt) and [validation](docs/VALIDATION.md)
- [Compact service](docs/AGGREGATE_SERVICE.md), [certified provider](docs/CERTIFIED_PROVIDER.md), and [local checkpoint adapter](docs/CHECKPOINT_ADAPTER.md)
- [Independent derivations/review](theory_revision/)
- [Restart prompt](docs/RESTART_PROMPT.md)
- [Complete remaining research program](docs/RESEARCH_TODO.md), with priorities, completion criteria, and decision gates
- [Publication theory](docs/PUBLICATION_THEORY.md) and [claim-to-evidence map](docs/CLAIM_EVIDENCE.md)
- [Target and charts](docs/TARGET_CONTRACT.md), [fair baselines](docs/BASELINES.md), and [local runner](docs/EXPERIMENT_RUNNER.md)
- [Prospective empirical protocol](docs/EMPIRICAL_PROTOCOL.md) and [source selection](docs/SOURCE_SELECTION.md)

## Verification

The reference modules use the Python standard library. The decoder has an explicit Linux CPython/binary64 runtime contract; its manifest pins code, runtime, math library and model state.

```bash
python -m unittest discover -s tests -v
python scripts/build_report.py
```

The PDF build additionally requires a local LaTeX installation and the packages listed in its preamble.

**Revision 4:** compact group state, automatic certified transformer response bounds, and local GPT-2 safetensors loading are implemented. The certified provider defines a separate numerical target, V_cert. It uses rational nonlinear enclosures, mixed Hessian bounds, and explicit finite-error propagation. Unsupported chart changes cause retained replay.

**Revision 5:** fixed target/chart constructors, bounded state loading, a fair indexed solver, atomic local runner, and analysis are implemented.
That checkpoint passed 197 correctness tests.
The prospective protocol keeps failures and missing planned requests in the workload.
The report now conditions fallback completion on successful finite evaluation.

**Revision 6:** fixed-box certificates remove the affine-span requirement for frozen-grid prefixes.
Hybrid midpoint anchors reduce interval feature error and avoid a separate finite evaluation when parameters vary.
Lazy parameter wrappers reduce temporary construction.
Workers enforce comparison-process limits.
Original-only workload scores, inventory checks, exclusive telemetry, and four mechanism controls are implemented.
The full software suite passes **261 correctness tests**.
The report has **31 pages**.
The register contains **24 completed and 54 open required items**, plus 12 conditional extensions.

Read the [box theory](docs/BOX_THEORY.md), [execution controls](docs/EXECUTION_CONTROL.md), and [workload contract](docs/WORKLOAD_CONTRACT.md).
The current prospective protocol is [version 2](configs/protocol_v2.json).

Repair and indexed fresh use the same planner.
The planner ignores the old model.
The current implementation has no deletion-specific solver advantage.
Report indexing savings separately from solver improvements.

The scalar implementation does not establish practical coverage or speed.
Ordinary model candidates exceed default resource planning limits.
The runner provides warm instrumented diagnostic timing.
Real input artifacts, feasible checkpoint execution, complete measurement controls, and remaining baselines remain open.
Correctness tests are not research benchmarks.
Production GPU kernels remain future work.

Research experiments remain paused. Synthetic empirical datasets remain deferred. Earlier experiment payloads were pruned; historical numbers are labeled as reconstructed context. No model weights, raw calibration corpus, credentials or old raw results are included.
