# Asset recovery after the scratch reset

The GitHub checkpoint preserves code, source snapshots, plans, receipts, and selected token records.
It does not contain checkpoint weights or generated binary models and states.
These files were intentionally excluded from Git.

On 9 October 2026, the checkout at `604de5b` had no `tmp` directory.
The two public DistilGPT2 checkpoint files were downloaded again.
Both files match the original hashes and byte counts exactly.
No model inference was used during this recovery.

| Recovered file | Bytes | SHA-256 |
| --- | ---: | --- |
| `tmp/models/distilgpt2/config.json` | 762 | `4ec5947c1d59fee6212cdf3b0ec1a53eac02092554c5ff0a733488cbd2c64f3a` |
| `tmp/models/distilgpt2/model.safetensors` | 352,824,413 | `e1ff18884359fe8beb795a5f414feb85a6ce3d929ad019c0d958c039d2b94a1b` |

The source is `distilbert/distilgpt2`, revision `2290a62682d06624634c1f46a6ad5be0f47f38aa`.
The downloader uses this revision and checks both size and SHA-256.
It rejects existing mismatched files and installs downloads without replacement.

## What the selected experiments actually need

Both selected request roots already contain their complete token arrays:

- `campaigns/independent_requests_v30_draft/wikitext-records.json`
- `campaigns/independent_requests_v30_draft/c4-records.json`

Each root has two sources with 128 tokens each.
The hashes are `3ac30626…` and `d3f140c3…`, respectively.
Do not select documents again or retokenize these files.
Raw WikiText, raw C4, and a tokenizer are unnecessary for these numerical requests.
Their provenance remains in the tracked selection record.

Registration also verifies earlier pilot evidence and reopens its model and state artifacts.
Therefore, checkpoint recovery alone cannot satisfy the unchanged V31 controller.
This is an evidence dependency, not a request for more training data.

## Local audit and checkpoint recovery

From the repository root, run:

```bash
python scripts/recover_assets_v32.py --fetch-checkpoint --checkpoint-only --output local_runs/recovery/checkpoint.json
```

This command exits successfully once both direct checkpoint files match.
Its report explicitly sets `checkpoint_verified` without claiming controller readiness.
Missing historical binaries do not block this checkpoint-only recovery step.
This supports a separate local V32 continuation with a new registration.

For the wider historical inventory, run:

```bash
python scripts/recover_assets_v32.py --fetch-checkpoint --output local_runs/recovery/assets.json
```

The output report must use a new filename.
The command never overwrites a report or historical evidence.
Exit code 2 means some listed historical assets remain unavailable.
It does not mean a verified checkpoint download failed.
The `downloads` field records each checkpoint outcome.

For a read-only audit, omit `--fetch-checkpoint`:

```bash
python scripts/recover_assets_v32.py --output local_runs/recovery/assets-after.json
```

The report lists expected and actual hashes, byte counts, and each referring attempt.
It includes historical plan inputs as well as external output artifacts.
Some historical inputs are not reopened by current registration.
Thus, the full list is a recovery inventory, not a proven minimum restoration set.
The controller remains the final authority on execution readiness.

The initial audit found 30 unavailable paths, representing 15 distinct expected hashes.
Several missing models and states are byte-identical copies from repeated timing trials.
This observation does not supply their missing bytes.

## Missing historical binary families

| Family | Expected identity or scope |
| --- | --- |
| Original calibrated model | `d314870f…`, 22,192,646 bytes |
| Retained calibrated model | `25068a93…`, 22,192,646 bytes |
| Ordered original lossless state | `730212c8…`, 79,592,059 bytes |
| Ordered retained lossless state | `125ef2a1…`, 50,888,817 bytes |
| Scalar original lossless state | `5607f427…`, 79,592,059 bytes |
| Scalar retained lossless state | `9948fb28…`, 50,888,817 bytes |
| V30 compressed original state | `1f4cccd4…`; see its immutable completion record for size |
| V30 compressed retained state | `3303318e…`, 43,925,472 bytes |
| V31 compressed original state | `fe72c60b…`, 73,915,004 bytes |
| V31 compressed retained state | `d3045bcd…`, 48,054,240 bytes |

The inventory also names historical quality-model inputs, prepared pools, and tokenizer bytes.
Their absence does not invalidate preserved receipt metadata.
It prevents any verification which actually requires those bytes.

## Safe reconstruction policy

Prefer a trusted saved artifact whose complete hash and size match the archived descriptor.
Copy matching bytes only into absent destinations.
Never replace an existing mismatch.

If no saved artifact exists, reconstruct it in a new recovery transaction.
Keep its new runtime, source, CPU, and output evidence separate.
Do not rerun workers inside old attempt directories.
Do not reset earlier ledgers or reuse their allowances.
Do not replace old timing observations with reconstruction timing.

Restore an absent historical artifact only after the new bytes match its entire archived SHA-256 and size.
Matching content can restore verification, but cannot recover missing runtime receipts.
A failed match remains a failed reconstruction.
Do not edit archived hashes, paths, provenance, or gates to make it pass.

Canonical states include provenance fields.
Equal model codes alone are insufficient to restore a state.
Use the matching frozen worker and preparation identity for any exact reconstruction.

## Runtime and local paths

The restored environment has CPython 3.12.14, NumPy, GCC, and x86-64.
The initial audit matched the entire registered V31 runtime contract.
It also matched the registered numerical source inventory.
The helper does not add a worker or change that inventory.

For the selected workers, NumPy and a local C compiler are needed.
The safetensors loader is implemented locally and does not require Transformers or PyTorch.
Use `requirements-local.txt` only when broader acquisition or evaluation scripts need its optional packages.
That file is an observed dependency list, not a complete environment lock.

Historical controllers bind absolute paths under `/workspace/scratch/50cc2e342461/second`.
The audit maps those paths for inspection when a clone uses another location.
It does not rewrite any archived descriptor.
Exact archival continuation requires the bound location and runtime.
A different local environment needs a new, reviewed continuation registration.
Its measurements must remain separate from the historical campaign.

This recovery helper never claims experiment completion or submission readiness.
