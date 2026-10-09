# Current execution checkpoint

Updated 9 October 2026.

Checkpoint `e18335c1f6f839379725072b540ef29484427e1c` preserves the complete WikiText replication and partial C4 evidence.
WikiText has seven settled transactions, charging 927 CPU seconds.
Its full binary audit is `campaigns/independent_wikitext_v32/analysis-v33.json`.
Both lossless repairs and the selected compressed repair match their complete cold models exactly.
Read `docs/RESEARCH_DECISION_V34.md` for the scientific interpretation and remaining paper requirements.

C4 has two settled transactions, charging 422 of its original 1,900 CPU seconds.
Preparation took 292.064861678 controller seconds.
The first cold reconstruction took 128.609518354 seconds.
No paired C4 repair has completed at this checkpoint.
The first cold result has a preserved stale live-progress copy.
Its completion, controller seal, receipt, stdout, output model, and ledger agree under independent audit.
The original strict verifier still rejects the three-copy discrepancy.
Its cause remains unknown.

The prior process-session identifier became unavailable after the execution surface changed.
The exact Python runtime contract still matches registration.
Model binaries survive, and resource-limit/affinity preflights pass.
Missing `/proc` files do not enter this controller's numerical execution requirements.
The V34 continuation passed independent review and is now registered.
Its SHA-256 is `ce08a60402ec3ea9deba95ed2acfd19966307b0c93140ec409d5e144c6e42a27`.
It binds an explicit compressed-worker adapter whose sole source difference is its evidence-verifier import.
The original numerical source inventory, reference model, and inputs remain unchanged.
No new empirical worker was started before this registration.

Execute the five remaining trials with:

```bash
.venv/bin/python -u scripts/launch_independent_requests_v34.py --execute-remaining
```

Run only process-output waits during the serial experiment sequence.
This precaution does not explain the original metadata incident.
Do not infer registration from a design file.

The intended remaining order is fixed in the original C4 program.
No original evidence, source selection, threshold, code snapshot, timing boundary, or CPU allowance may change.
Any new mismatch or execution failure stops dependent work.

For a new local machine, use `docs/LOCAL_LLM_RESUME_V32.md`.
Fresh local reproduction uses the V32 controller with `--workspace local_runs/replay-001`.
Incident-specific exceptions never apply to new local campaigns.
Archive both successful and failed attempts with `scripts/export_local_evidence_v32.py`.
Preserve binary artifacts separately on durable local storage.

Read historical notes only with their original evidence cutoff.
The latest receipts and explicit continuation registrations take precedence.
