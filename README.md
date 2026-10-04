# Exact calibration-data unlearning for quantized language models

Research project targeting ACL 2027. The task is to remove calibration documents from a quantized language model while matching the complete retained-data quantization procedure with the original full-precision weights fixed.

**Start/resume here:** [RESUME.md](RESUME.md), [project context](docs/PROJECT_CONTEXT.md), [current status](docs/STATUS.md).

Experiments are paused while the theory and algorithms are revised. Conditional exactness/work theorems must not be presented as empirical wall-clock speedups. Earlier experiment files were removed by workspace maintenance; their reported results and missing-file inventory are documented with explicit provenance.

The latest revision permits changed early quantization decisions through certified feature/covariance transport. It specifies canonical repeated-deletion state and an exact fallback with bounded charged-work overhead.

## Current deliverables

- [17-page theory and algorithm report](output/pdf/theory_algorithm_revision.pdf)
- [LaTeX source](reports/theory_algorithm_revision.tex)
- [Implementation specification](docs/ALGORITHM_SPEC.md)
- [Proof-safe numerical contract](docs/NUMERICAL_CONTRACT.md)
- [Theorem and claim ledger](docs/THEOREM_LEDGER.md)
- [Exact rational decision core](src/exact_core.py) and [implementation status](src/IMPLEMENTATION_STATUS.txt)
- [Independent derivations and review notes](theory_revision/)
- [Copyable restart prompt](docs/RESTART_PROMPT.md)

The local core uses only Python's standard library and exact `Fraction` arithmetic. It checks decision inequalities under caller-proved spectral premises; it does not certify a whole transformer by itself. Static compilation and manual review were completed. No numerical tests or experiments were run in this revision.

To rebuild the PDF with a local LaTeX installation:

```bash
python3 scripts/build_report.py
```

Required LaTeX packages include geometry, lmodern, amsmath/amssymb/amsthm, booktabs, tabularx, xcolor, fancyhdr and hyperref. Full transformer integration remains to be implemented and validated. No model weights, raw calibration corpus, old experiment payloads or credentials are included.
