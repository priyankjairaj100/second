# Offline copied-evidence reporting

V48 reads a relocated copy of an existing V43 or V45 campaign. It checks the frozen program hash, source files, sealed worker receipts, settled ledger, both artifact audits, all eight model/state comparisons, input commitments and reported cost arithmetic. It preserves prior failed charges and adverse comparisons. It performs no inference, source selection, registration, submission, retry or ledger write.

For the completed historical V43 archive, from the repository root:

```bash
.venv/bin/python -B -m unittest research_v48.test_report
.venv/bin/python -B -m research_v48.report \
  local_runs/full-model-v43-20261010-b --profile v43 --require-binaries \
  --output local_runs/NEW-v43-offline-report.json
```

Use a fresh output path. The local validation on 11 October 2026 rehashed all 138 inputs in the supplemental inventory, including available binaries, and checked all eight comparisons. `validation/v48_v43_full_archive.json` contains that report. This is an integrity and arithmetic check of an existing historical run, not numerical reproduction or a new performance measurement. Its 1,720 CPU seconds cover the successful campaign; the prior failed preparation adds 24, for 1,744 in the recorded continuation scope. Registration, software checks, setup and post-run analysis are outside these worker charges.

`campaigns/csis_full_model_v43` can be inspected without `--require-binaries`. Every absent binary commitment appears in `remote_only_binary_inputs`; receipt and source files remain mandatory. This mode cannot establish that those missing bytes are currently retrievable. Even with all binaries present, equality and membership claims rely on the two frozen auditors. Hashes do not independently prove the mathematics or authenticate a hostile host.

## V45 after access returns

V45 has no locally available terminal result as of 11 October 2026. The user confirmed the cluster is unavailable. Do not retry SSH until access is restored. Do not use V43 results as V45 outcomes.

After restoring access, collect a fresh **read-only** scheduler snapshot and preserve it verbatim. The parser expects the output of:

```bash
sacct -n -P -S 2026-10-10 \
  -j 13228,13229,13230,13231,13232,13233,13234,13235 \
  --format=JobIDRaw,State%40,ExitCode
```

Use the actual account and original jobs. Record the collection time separately. Save this output in a fresh local file; the report records its hash but cannot independently authenticate its origin or freshness. Missing accounting rows mean unknown, not success. A failed, cancelled or incomplete job prevents a completed-run report. Preserve partial artifacts and reservations even when the chain fails; do not reset its ledger or increase frozen limits.

Copy the original campaign metadata, including every worker attempt and its sealed JSON artifacts, from `/nfs_home/users/poonam/second-20261010/local_runs/c4-full-model-v45-20261010-a` into a new local archive path. Include both `artifact-audit.json` and `postrun-audit.json` if they exist. If the chain is still running, take a status snapshot only and wait for settled records before collecting a final archive. Do not rerun either audit to manufacture a missing receipt. Preserve the existing source checkout and the data-selection commitments; copy missing prerequisite metadata from their original locations. No download command should overwrite the historical archives.

Once those copies exist:

```bash
.venv/bin/python -B -m research_v48.report \
  local_runs/NEW-v45-copied-evidence --profile v45 \
  --accounting local_runs/NEW-v45-accounting.txt \
  --output local_runs/NEW-v45-offline-report.json
```

The default metadata mode allows only absent `.bin` and `.safetensors` payloads. It lists each one explicitly; all present files are rehashed. Check disk space and actual remote artifact sizes before choosing to copy full binaries. Use `--require-binaries` only after all required payloads are available. A new output report is always required; no historical result is overwritten.

If all eight jobs completed, the report still requires successful sealed receipts for the six workers, exact job/plan identities, both bound audits and settled budget debits. All historical failures and the 60 quality exclusions remain in force. Passing this reporting tool does not establish prediction quality for V45, a practical win, confirmation or ACL readiness.

## Validation boundary

Ten software tests cover missing/duplicate scheduler records, nonzero exits, failed/cancelled/running states, changed artifact bytes, missing comparisons, false membership/model claims, broken primary-audit binding and manipulated timing ratios. Both full-binary and metadata-only modes were exercised on the real copied V43 archive. The V45 end-to-end path remains unexecuted until its actual artifacts can be retrieved. No synthetic success receipt is substituted for it.
