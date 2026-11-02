# Terminal chain: exactness and GPU parity pass; CPU quality fails

Updated 13 October 2026. V58 is an archive and analysis checkpoint, not a new
numerical experiment. Resume from this file and `handoff/program_v58.json`.
The previous V57 access cutoff is historical.

## Completed work

The read-only cluster snapshot at 09:05:30 UTC (14:35:30 IST) shows every job in
the existing V54/V55/V56 dependency chain completed with exit 0:0. No jobs in
that chain remain active or pending. No worker was restarted or resubmitted.

Both V54 final audits report verified complete artifacts. Eight comparisons
cover four arms and two requests, all 24 stages and 42,467,328 model codes.
Actual model and representation-specific canonical-state bytes match fresh
retained-input reconstruction. The oracle shares the numerical implementation;
it is not an independent implementation. The supplemental audit binds the
primary receipt and checks actual model exports, targets, membership/provenance,
trust sidecars and storage. Numerical binaries remain on the cluster.

V54 uses the same DistilGPT2 checkpoint and adaptive C4 root as registered:
13 original records, 1664 original tokens, then 1536 and 768 retained tokens.
Do not describe this as another checkpoint or independent confirmation.

## Results and decision

- Compression versus cache takes 1.192912 and 1.414314 times the two request
  times. It saves 9.2614% and 8.7148% live-state bytes, or only 4.7252% and
  3.1056% deployment bytes when including the shared checkpoint.
- Hybrid is both faster and smaller than compression at 1536 tokens. At 768,
  compression is faster and smaller than hybrid, but cache remains faster.
  No source replay or failed-stage fallback occurs for compressed repair.
- Common plus representation-specific preparation and complete worker
  transactions give attributed two-request paths of 10494.864 s (cache),
  12511.452 s (cold), 11657.471 s (hybrid), and 12298.118 s (compressed).
  Shared preparation overhead and audits remain separately reported.
  These are observed attributed paths, not repeated measurements or a general
  lifetime break-even result. V57 overlapped cold on the same CPU node.
- V55's pooled fixed/sequential perplexity ratio is **1.0592208**, failing the
  frozen **1.05** limit. PPL is 55.14666 fixed versus 52.06342 sequential.
  Fixed is worse on all eight exposed articles. The worst article ratio,
  1.1742804, passes the separate 1.20 limit; overall quality still fails.
  Full precision is 45.60008 and nearest rounding 64.87023.
- All sixteen historical full-precision/nearest loss controls pass. All sixty
  quality exclusions remain intact. These are eight already exposed articles,
  1016 predictions per model, not untouched quality evaluation.
- V56 passes all 32 same-model CPU/GPU mean-NLL comparisons; maximum absolute
  deviation is 1.2084821332612728e-14 against 1e-8. The 150 parameter transfers
  preserve binary64 words. This is likelihood parity, not exact GPU calibration.

All four service arms return the same fixed-anchor model. The quality failure
therefore concerns the target relative to matched sequential calibration, not
compression error. Do not relax thresholds, drop stronger controls or rerun for
a more favorable result. Read `docs/RESEARCH_DECISION_V58.md` before further
numerical work. The second-checkpoint checklist is not an admission or launch.

## Resource accounting

The six V54 numerical workers charged 6640, 4892, 6898, 5832, 6023 and 8367 CPU
seconds (prepare, cached, cold, hybrid, compressed, oracle): total **38652**.
Including the earlier failed preparation adds 4801, giving 43453. V55 charges
1595 and V56 charges 73 CPU seconds under separate budgets. Final audit and
software/runtime costs remain separate; do not add Slurm wall times as CPU
debits. All registered reservations are settled with no over-cap result.

## Archive and verification scope

`campaigns/csis_terminal_v54_v56_metadata_20261013.tar.gz` contains 833 copied
metadata files plus its collection manifest. SHA-256:
`9def1cc4d01ea52930601ec0a457bc13755077ad0af77fddf9732bfc507b992e`.
The archive is 1133669 bytes. It includes programs, registrations, progress,
completion and audit receipts, controller logs and terminal ledgers. It excludes
large model/state/checkpoint binaries and is not a complete numerical replay.

Extract into a fresh directory and run
`python3 -B validation/check_v58_terminal_metadata.py EXTRACTED_DIRECTORY`.
The checker validates available file/source hashes, bound audit chains,
controller receipts and ledgers, and descriptive result arithmetic. Its JSON
report distinguishes verified metadata from the failed CPU quality guard and
successful GPU parity. The local check verifies 177 available bound inputs and
all eight worker seals; thirty uncopied binary inputs remain remotely audited
rather than locally revalidated. All historical metadata inputs are available
through explicit hash-matched repository copies. A copied-registration tamper
was rejected. The original audit assumes trusted execution.

The open manuscript remains the existing `outputs/second-research-draft.tex`.
Its V58 snapshot is `reports/manuscript_v58.tex`. The manuscript describes the
adverse cost and quality findings and remains a working draft. Successful
compilation is not a complete visual review or ACL submission-readiness check.

## Next work

Close this frozen numerical program with these outcomes. No pending work needs
resubmission. Before model/root expansion, reconsider whether a source-local
target can meet the unchanged useful-quality requirement, or narrow the paper
to the demonstrated methodological result. Any new target or representation
requires a new development protocol and matched controls before numerical work.
Independent roots, second-checkpoint transfer, untouched quality, randomized
repetition, mechanism ablations, and a defensible submission contribution remain
unresolved. Do not interpret an engineering audit as acceptance of those gates.

The SANW2 semantic-negative-weighting reviews are about a separate manuscript.
No SANW2 change belongs in this project's empirical record.
