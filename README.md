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

## Verification

The reference modules use the Python standard library. The decoder has an explicit Linux CPython/binary64 runtime contract; its manifest pins code, runtime, math library and model state.

```bash
python -m unittest discover -s tests -v
python scripts/build_report.py
```

The PDF build additionally requires a local LaTeX installation and the packages listed in its preamble.

**Revision 4:** compact group state, automatic certified transformer response bounds, and local GPT-2 safetensors loading are implemented. The certified provider defines a separate numerical target, V_cert. It uses rational nonlinear enclosures, mixed Hessian bounds, and explicit finite-error propagation. Unsupported chart changes cause retained replay.

The scalar implementation does not establish practical coverage or speed. Metadata scans, preparation, memory, and output costs remain explicit. Correctness tests are not research benchmarks. Production GPU kernels remain future work.

Research experiments remain paused. Synthetic empirical datasets remain deferred. Earlier experiment payloads were pruned; historical numbers are labeled as reconstructed context. No model weights, raw calibration corpus, credentials or old raw results are included.
