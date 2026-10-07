# Current execution: revision 13 complete-state pilots running

Updated 7 October 2026. The user requested continued implementation and empirical execution here.
Read docs/COMPACT_SERVICE_V13.md and pilots/v13/prospective-program.json first.

The factor_identity_v1 family replaces dense Grams with exact retained factors and packed codes.
A complete 24-stage DistilGPT2 state transaction passed.
Its saved state is 29,638,144 bytes, below the 512 MiB limit.
A complete one-record deletion repair also passed.
All 42,467,328 repaired values match the revision 12 retained row-grid model.
The remaining four-method controls and prospective quality control are running serially.

Read current worker receipts and settled budget ledgers before reporting outcomes.
A running worker can have a provisional launch_failed receipt with a reserved debit.
Do not classify that placeholder as a finished failure.
Never launch another empirical worker while any inherited debit remains reserved.
The original cap remains 10,800 CPU seconds, with all revision 10/12/13 charges carried forward.

The box modules prove feature containment and constant codes over supplied boxes.
The current box evaluator still evaluates retained tokens.
It does not establish changed-ancestor feature avoidance.
The identity service correctly reports zero such avoidance.
Repair and indexed_fresh share the same algorithm.
No reliable repair-speed or paper-readiness claim is established.

A common batched token solver passed exact code and directed-bound comparisons.
It is available to every compatible method through --solver-backend batched.
The registered reference quartet retains the reference solver.
Further matched batching pilots are prospectively listed in pilots/v13/prospective-batching.json.

The first revision 13 worker failed after a logging-key collision.
The failure remains archived. The fixed worker completed.
An initial driver misread a reserved receipt; its erroneous derivative report remains separately archived.
A regression check now requires both settled ledgers and settled receipts.

Large state/model arrays remain local and reproducible, with published hashes.
All source snapshots, plans, receipts, software checks, and limitations must be pushed before ending.

---

The following sections preserve historical checkpoints.

# Current execution: revision 12 completed diagnostics

Updated 7 October 2026. The user authorized empirical execution here; the earlier local-only instruction is historical.
Read docs/EMPIRICAL_PILOT_V12.md and pilots/v12/summary.json first.

Twelve bounded attempts are preserved: eleven completed, one failed and subsequently fixed.
Complete column-grid original/retained models and a prospective row-grid retained model were constructed.
Each contains 24 quantized projection stages and 42,467,328 certified code decisions.
The old-target deletion changed 5.637 percent of codes across every stage.

Heldout diagnostics contain only 30 predictions from two validation articles.
Column-grid perplexity was 4.830x base before deletion and 8.102x afterward.
Fixed output-row scaling improved the retained ratio to 1.315x.
An evaluator control reproduced every old-model NLL exactly.
This is a new quantizer target and an exploratory improvement, not a confirmed paper result.
The two evaluation IDs are excluded from future confirmation.

The core suite passed 590 tests; nine additional tests passed for later modules.
The inherited worker budget has 4283 charged CPU seconds and 6517 remaining.
Do not reset it through a new directory, source version, or target variant.

The complete empirical program remains blocked.
The compact path lacks canonical repair state, certified feature transport, and four-method integration.
The specified fully represented dense state needs at least 523.125 MiB, above the 512 MiB single-file cap.
The improved quality diagnostic also remains above the 1.20 screen.
No reliable full-model repair speedup is established.

Read docs/V12_REPAIR_INTEGRATION_AUDIT.md and docs/NEXT_ALGORITHMIC_STEPS_V12.md for next work.
Read docs/COMPACT_EXECUTION_V12.md for bounded commands and explicit target choices.
All attempt sources and receipts are preserved. Large code arrays remain reproducible local artifacts, bound by published hashes.

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
