# Reproduce the complete first-stage comparison

This experiment requires only the committed real-data capsules, Linux, a C compiler,
and the Python dependencies in `requirements-recovery-v32.txt`.
It does not require downloading the complete model or rebuilding neural features.
Use `LOCAL_LLM_RESUME_V32.md` to create the environment in a fresh clone.

Use a new campaign path. Published registrations and attempts are historical evidence.

```bash
.venv/bin/python -m unittest tests.test_gram_stage_v36
.venv/bin/python scripts/launch_gram_stage_v36.py --campaign campaigns/pooled_gram_stage_local_v36 --register
.venv/bin/python -u scripts/launch_gram_stage_v36.py --campaign campaigns/pooled_gram_stage_local_v36 --execute
.venv/bin/python scripts/launch_gram_stage_v36.py --campaign campaigns/pooled_gram_stage_local_v36 --status
```

Registration verifies inputs and admits resources without forming a Gram or
computing new codes. Publish the reviewed protocol before measured execution.
Run the worker alone, with no concurrent tests, archive analysis, or other experiments.
The experiment has one 880-second CPU worker within a separate 900-second phase.
It has a 1,100-second wall limit and a 3 GiB address-space limit.

The four fixed arms cover preparation, pooled-Gram deletion, retained-Gram
reconstruction, and cached-feature reconstruction. Every certified arm must
match all 1,769,472 archived reference codes. Repaired and independently rebuilt
retained Gram bytes must match exactly.

Read the actual `program.json`, `attempt/transaction.json`, worker receipt,
sealed completion, and `analysis.json`. A completed worker may still have a
scientific refusal. Inspect `scientific_gate_passed` and every `arm_outcomes`
entry. A refused arm commits no code artifact. Its elapsed time cannot be used
as a complete reconstruction speed measurement.

Preserve losses, refusals, failed attempts, raw binary artifacts, and CPU receipts.
Do not automatically retry failures. Binary artifacts remain excluded from Git;
store them durably alongside the published metadata and hashes.
The exact input capsules are already committed and support fresh reproduction.

This is a complete-stage development comparison, not complete-model confirmation.
It excludes neural replay and cannot resolve the separate full C4 runtime blocker.
Never substitute cached historical runtime facts for current neural attestation.
