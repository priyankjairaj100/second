# Reproduce the exact pooled-Gram component locally

This component uses the real-data capsule already included in Git.
It does not require the large checkpoint, historical state binaries, or neural feature generation.
It requires Linux, a C compiler, and the Python dependencies in `requirements-recovery-v32.txt`.
The full-model C4 program has separate runtime requirements; read `ACTIVE_SESSION_V34.md` before that work.

From a fresh checkout, install the existing dependencies as described in `LOCAL_LLM_RESUME_V32.md`.
Then use a new campaign directory:

```bash
.venv/bin/python -m unittest tests.test_exact_gram_v35 tests.test_direct_gram_v35 tests.test_gram_protocol_v35 tests.test_archive_capsule_v35
.venv/bin/python scripts/launch_gram_pilot_v35.py --campaign campaigns/pooled_gram_local_v35 --register
.venv/bin/python -u scripts/launch_gram_pilot_v35.py --campaign campaigns/pooled_gram_local_v35 --execute
.venv/bin/python scripts/launch_gram_pilot_v35.py --campaign campaigns/pooled_gram_local_v35 --status
```

Registration performs only input integrity and finite resource admission checks.
It does not form a Gram or compute new codes.
The worker then uses one separate 900-second CPU allowance.
An existing failed or partial attempt stops continuation; preserve it and diagnose the actual failure.
Never erase it to manufacture an automatic retry.

Inspect `program.json`, `attempt/transaction.json`, `attempt/worker/result.json`, and `attempt/outputs/completion.json`.
Success additionally requires `analysis.json` from verified terminal evidence.
Failure produces an explicit receipt and, when available, `attempt/outputs/failure.json`.
Store the generated binary Grams and code arrays on durable local storage.
Their hashes and metadata are tracked, while their reproducible binary files are excluded from Git.

The three arms operate on the same 3,072 decisions and exact retained feature words.
A component result cannot establish complete-model speed, neural replay cost, or lifetime benefit.
Preserve every loss or unresolved certificate.
Do not change precision, source records, row indices, or method order after observing outcomes.

Before publishing local results, update `MANIFEST.sha256` from the reviewed index using `scripts/prepare_github_checkpoint_v34.py`.
That helper prepares a text-only payload; it does not push or move a branch.
Use normal Git authentication to commit and push your reviewed files; do not force-push.
