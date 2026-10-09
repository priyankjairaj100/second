# Continuation after the preserved V32 evidence discrepancy

Updated 9 October 2026. Read actual receipts before executing any command.
This note concerns the known chat campaign, not a generic recovery policy.

## Durable evidence

Checkpoint `129e94d81eb8f38ddf0f156a43436b81390eb28d` preserves the incident and completed observations.
WikiText completed four numerical transactions before its strict controller stopped.
Their total settled charge is 656 CPU seconds.
The original phase cap remains 1,900 seconds.
The continuation passed independent review and was registered before any remaining worker started.

| Trial | Recorded controller seconds |
|---|---:|
| Original preparation | 287.716525921 |
| Deletion zero, lossless repair | 76.827683858 |
| Deletion zero, cold reconstruction | 143.550496271 |
| Deletion one, cold reconstruction | 146.184272791 |

The first complete pair has a 1.868473564 ratio of cold time to repair time.
All 24 stages and 42,467,328 codes match.
The second cold result has a preserved terminal-copy discrepancy.
Its completion, controller seal, receipt-bound terminal log, model file, and CPU ledger agree.
Its live progress file contains an earlier running prefix.
The cause remains unknown.
The original strict verifier still rejects that discrepancy.

The incident audit and unchanged file copies are under `campaigns/recovery_v32/`.
No original progress, completion, receipt, transaction, model, or timing is rewritten.

## Registered narrow continuation

`scripts/verify_terminal_recovery_v33.py` admits only the exact reviewed incident and bound hashes.
Every other attempt uses the original strict verifier.
`scripts/launch_independent_requests_v33.py` adds an immutable continuation record after independent review.
It retains the original WikiText program, source snapshot, protocol, and CPU ledger.
It adds no allowance and repeats no completed experiment.
The remaining WikiText trials are:

1. `wikitext-delete-1-repair`
2. `wikitext-root-convert`
3. `wikitext-delete-0-compressed`

The controller then registers and runs all seven preselected C4 trials.
C4 retains its separate 1,900-second cap, sources, order, numerical policy, and scientific gates.
Scientific losses remain reportable completed results.
Any new execution failure, model mismatch, or integrity discrepancy stops dependent work.

Registration is complete. Its SHA-256 is `6f59bd64209cbe4f791cdf54569a0bde596d53f935e535d38c4035c3790c25fb`.
The known campaign now uses:

```bash
.venv/bin/python -u scripts/launch_independent_requests_v33.py --execute-remaining
```

Do not register twice or infer registration from this design note.
The actual `campaigns/independent_wikitext_v32/continuation-v1.json` is authoritative.
Run the remaining workers serially in one process.
Use only process-output waits while that process runs.
Do not run concurrent filesystem tools or agents during the timing sequence.
This precaution does not establish the incident's cause.

## Fresh local reproduction

Use the original V32 controller in a new local workspace for a clean reproduction.
It does not grant the incident-specific exception to new runs.
Follow `docs/LOCAL_LLM_RESUME_V32.md` for installation, downloads, execution, analysis, and publication.
Keep binary artifacts on durable local storage.
Published metadata alone cannot resume a campaign whose required binaries are missing.

The full research program remains incomplete after these two roots.
Read `docs/EMPIRICAL_STATUS_V32.md` and `handoff/program_v32.json` for remaining paper requirements.
