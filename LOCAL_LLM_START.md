# Current execution: revision 12

Updated 7 October 2026. The user authorized continued empirical execution here.
The revision 11 local-only instruction below is superseded.
Read docs/COMPACT_EXECUTION_V12.md and docs/V12_REPAIR_INTEGRATION_AUDIT.md for the new implementation boundaries.
Read pilots/v12/program.json and each immutable attempt receipt for actual outcomes.

Compact checkpoint storage and exact-order finite execution now work on complete DistilGPT2 forward passes.
The optional MPFR enclosure backend has an explicit, different evaluator binding.
Token-space quantization preserves the exact rational code target under its documented arithmetic premises.
Model-code pilots do not produce canonical repair state or establish repair speed.
Dense committed response state, scalar proof jets, and transport verification remain integration blockers.
Confirmation remains blocked. Preserve failures, CPU debits, and all unstarted experiment cells.

---

The following sections preserve historical checkpoints.

# Start the local empirical program

Updated 5 October 2026. This handoff supersedes earlier execution-location instructions.
The user will run future experiments locally and return evidence for review.
GitHub contains every recovered project file and the current implementation.
Some earlier chat artifacts were lost before reconstruction. PROJECT_CONTEXT.md identifies those gaps.
Model weights, complete datasets, environments, and credentials are intentionally excluded.
Pinned acquisition instructions replace those large inputs.

## Quick start

Use Linux or WSL2 with CPython 3.12. Native Windows execution is unsupported.
The reference target uses CPU exact arithmetic. A GPU does not resolve the current bottlenecks.
Run these commands from the repository root:

```bash
git clone https://github.com/priyankjairaj100/second.git
cd second
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-local.txt
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false
python scripts/local_handoff.py init --workspace local_runs/first
python scripts/check_runtime.py --verify local_runs/first/runtime.json
python -m unittest discover -s tests -v > local_runs/first/software-tests.txt 2>&1
```

Inspect the test exit status. Do not treat an output file as a passing result.
Initialization runs no model and downloads nothing.
It creates a report, checklist, hardware snapshot, and local runtime contract.
It does not create an executable experiment protocol or grant scientific promotion.

Give your local coding assistant this prompt:

> Continue this repository's ACL 2027 calibration-data unlearning project.
> Read AGENTS.md, LOCAL_LLM_START.md, and docs/LOCAL_EMPIRICAL_PROGRAM.md first.
> Then read RESUME.md, docs/TARGET_CONTRACT.md, and docs/EMPIRICAL_PILOT_V10.md.
> Execute the local empirical program in order. Start with compact exact backend admission.
> Preserve V_cert, fixed base weights, sequential calibration, and every declared exact decision.
> Never substitute native GPTQ or approximate BLAS arithmetic without declaring a separate target.
> Give every compatible optimization equally to all comparator methods.
> Preserve archived evidence. Generate new local paths, hashes, runtime bindings, and budget records.
> Never run archived revision 10 launchers against their original output folders.
> Pilot each dataset and experiment before expansion. Preserve losses, failures, and missing cells.
> Explain failures, fix implementation bugs, and repeat affected development pilots under new identifiers.
> Freeze confirmation before outcomes. Never tune using confirmation results.
> Do not use synthetic datasets as empirical evidence. Software fixtures remain allowed.
> Keep results in local_runs/first and maintain its report.json after every completed stage.
> Commit source changes and handoff notes. Exclude datasets, weights, credentials, and caches.
> Send the user a compact report bundle after each decision gate.
> Do not claim a full-model win unless correctness, quality, mechanism, and complete costs support it.

## Reading order

1. `docs/LOCAL_EMPIRICAL_PROGRAM.md`: exact staged program and advancement rules.
2. `handoff/program.json`: machine-readable cells, settings, and blockers.
3. `docs/TARGET_CONTRACT.md`, `docs/PUBLICATION_THEORY.md`, `docs/ALGORITHM_ADVANCE_V7.md`: numerical and theoretical obligations.
4. `docs/MEASURED_COMPARISON.md`, `docs/MEASURED_SEQUENCE.md`, `docs/MEASURED_ANALYSIS.md`: execution and inference contracts.
5. `docs/FEASIBILITY_DECISION.md`, `docs/MANUSCRIPT_EVIDENCE_SLOTS.md`: evidence requirements.
6. `docs/PROJECT_CONTEXT.md`, `docs/RESEARCH_TODO.md`: history and remaining paper obligations.

The revision 7 PDF is historical. Later source contracts take precedence.
The theory supports conditional correctness and cost gains. Empirical practicality remains unproved.

## Return results

Update `local_runs/first/report.json`. Preserve every checklist row, including blocked cells.
Use null for unavailable numbers. State the reason. Do not enter estimated measurements.
Add concise explanations in `local_runs/first/notes.md`.
Then create a bundle:

```bash
python scripts/local_handoff.py pack --workspace local_runs/first --output local_runs/first-return.zip
```

The default bundle contains metadata and reports only.
Add selected sanitized receipts with repeated `--evidence PATH` arguments.
Those paths must remain inside the workspace. The tool rejects common model and dataset filenames.
Inspect the bundle before sharing. An allowlist cannot detect every secret inside arbitrary text.
Keep complete raw experiment archives locally. Publish their hashes and reproducible source changes.
Send the ZIP and the exact Git commit here. Include any uncommitted changes as a reviewed patch.
