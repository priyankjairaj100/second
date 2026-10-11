# Cold reconstruction completed; hybrid comparison running

Snapshot: 2026-10-11T16:10:07.368558+00:00. Preparation 13310, cached repair 13311 and cold
reconstruction 13312 are complete. Hybrid 13313 is running; compressed 13314,
fresh oracle 13315, final audits 13316--13317, CPU quality 13325--13327 and GPU
parity 13329 remain queued. Do not resubmit the one-use chain.

Cold finished both requests with scheduler exit 0:0 and wall time 1:55:36.
`validation/v57_cold_metadata_check.json` verifies 136 copied metadata files,
386 source commitments, sealed controller artifacts, declared/applied limits,
request and budget bindings, and the selected settled 6,898-CPU-second debit.
The three completed numerical worker charges total 18,430 CPU seconds.
The existing 11,532-CPU-second V57 prefix audit still covers preparation/cache
only; its scope is not extended to cold artifacts by this bookkeeping check.

Cold completion metadata reports 24 stages per request, 1,536/768 retained
tokens, 288/144 neural stage-record pairs and request times 5,355.650652324 /
1,547.697139420 seconds. These are two different requests, not replications.
The controller seal does not bind the completion JSON or reported model hashes.
No output binary was copied, rehashed or parsed here, and no fresh-oracle
comparison or full-campaign success is claimed. Both final V54 audits remain
mandatory before interpreting complete model/state or speed/storage results.

The immutable metadata-only archive is
`campaigns/csis_cold_v54_metadata_20261011.tar.gz` (SHA-256
`a62863548c6007c8b2be99788bdf1bb05d95f1d60ecb6281300467cde5710c8d`). Extract it into a fresh temporary directory and
run `python3 -B validation/check_v54_cold_metadata.py EXTRACTED_DIRECTORY` from
this checkout to repeat the offline metadata checks. This performs no inference
or calibration. Its copied ledger is a historical snapshot with a later active
reservation, not the current live ledger. The collection manifest preserves
its original scheduler snapshot, including then-unavailable aggregate CPU time.
`validation/v57_cold_live_snapshot.json` records the later scheduler observation.

All 386/399/409 frozen V54/V55/V56 source commitments still match. Frozen sources,
registrations, ledgers and thresholds were not edited, and no empirical job was
added. CPU quality and GPU audits can verify valid adverse outcomes; inspect
`development_guards_pass` and `parity_passed` separately from scheduler/audit
success. The manuscript keeps its earlier evidence cutoff while final results
are pending. It is not submission-ready. Earlier negative evidence and all 60
quality exclusions remain intact.

---

# Active session: completed preparation/cache prefix, remaining comparisons running

Updated 11 October 2026, snapshot 2026-10-11T14:53:48.314278+00:00. Read `handoff/program_v57.json`
and `validation/v57_prefix_archive_audit.json`. Earlier handoffs retain historical cutoffs.

V54 preparation 13310 completed in 1:51:13 scheduler wall time and cached 13311 in
1:21:59. Their sealed numerical debits are 6,640 and 4,892 CPU seconds, total 11,532.
These are measured charges; the original 81,012 phase allowance is unchanged.
At this snapshot, cold 13312 is running; hybrid 13313, compressed 13314, oracle 13315,
and final audits 13316--13317 remain pending. Quality 13325--13327 and GPU 13329
remain conditional. Do not restart or resubmit them. A failed prerequisite
cancels dependent work. No new empirical phase was launched in this continuation.

Read-only audit 13352, source `a13a0c83fb6b1de7f3284047f81c62dd6cbbc83a`, passed all five Linux artifact/receipt
fixtures with zero skips, then verified the completed prefix. It rehashed actual
outputs, parsed all three original representation states and both cached
successors, compared their packed code exports with all 24 stages/42,467,328
state codes, checked registered retained tokens/provenance and unchanged source
descriptors, and validated literal worker commands/limits, seals and settled
CPU debits. Audit CPU was 279.516 seconds, separately reported outside
numerical worker accounting; scheduler totals include software/runtime/setup.
The audit ran concurrently with cold 13312 on the same CPU node. Existing
single-observation timings have uncontrolled shared-node/cache effects; do not
interpret timing differences causally.

Both cached requests executed zero neural stage-record pairs. Recorded request
times are 3,986.584 seconds for 1,536 retained tokens and 899.972 seconds for 768 retained
tokens. These are two different request sizes, not repeated measurements or a
speedup comparison. No compressed repair, cold comparison, independent fresh
oracle equality or actual-model quality was verified by this partial audit.
All original targets, source versions, phase allowances and 60 quality exclusions
remain unchanged. Source commitments 386/399/409 for V54/V55/V56 still match.

Archive: `campaigns/csis_completed_prefix_v57`. The local check verifies copied
metadata against the remote audit's input hashes; large state/model/checkpoint
binaries remain on the cluster. It is not an independent local numerical replay.
Only about 2 GiB local disk was free at inspection; do not blindly copy multi-GiB
artifacts. The current master stays open in the Codex task's existing
`outputs/second-research-draft.tex`; its committed snapshot is
`reports/manuscript_v57.tex`.

Next: allow the existing chain to finish and inspect terminal receipts and actual
artifacts. V57 never replaces final V54 artifact-audit.json/postrun-audit.json,
which V55 registration requires. V56 still admits valid negative CPU quality.
After these results, second-checkpoint transfer, stronger codecs, ablations,
lifetime accounting, independent roots/deletions, randomized repetition and
untouched quality remain separate scientific gates. The manuscript is not
submission-ready. Earlier adverse findings and failed attempts remain preserved.
No recurring monitor was created and no unrelated cluster job was changed.
