# C4 terminal evidence incident

Updated 9 October 2026. This audit performed no neural inference.
It changed no original experiment evidence, source, registration, or ledger.
The original strict three-copy guard still fails.
The cause remains unknown.

C4 preparation finished in 292.064862 controller seconds and charged 293 CPU seconds.
The first cold reconstruction finished in 128.609518 controller seconds and charged 129 CPU seconds.
Its worker exited successfully and its receipt settled normally.
The ledger contains exactly these two settled debits, totaling 422 of 1,900 CPU seconds.
Five registered trials remain unstarted, with 1,478 CPU seconds available.
No repair/cold C4 pair exists yet; there is no C4 speedup result.

The cold reconstruction's completion record and controller seal agree exactly.
The receipt-bound stdout commits their hash.
The live progress record remains an earlier prefix ending at `model_write_started`.
The terminal record appends `model_write_complete` and `complete`.
Shared nonterminal fields agree, including all stage diagnostics.
Only status, phases, and the output manifest changed among shared fields.

| Evidence | SHA-256 |
|---|---|
| Original program | `72a47ecee599217f32a89bddf8ece7dae6273dcb19b49f8bb8cd1c06ab6a842c` |
| Original protocol | `a40135ab93ed716ff655a3dced19cb319b30c00262f1d50364ab55e5b8e66fe1` |
| Completion and seal | `b16ca849e55b8a2558b2cc3e8b609184e61fa1475464763e8b227d68ad3596f5` |
| Preserved stale live record | `e2f76585be4eef13997ead916ce9fb1bc014ba7967eb7008a09b25bf716fcb72` |
| Worker receipt | `b04708c67ea4105d9e0af1b55c879ddfcd4ef10b6e09046b916d9f1c73cd764c` |
| Controller transaction | `5d8d5e16f2d8777e3e4e50210164d3e1f9f43578798024bf068adbb1a0f5ee14` |
| Actual 22,192,646-byte model | `d4cca4f44263e10d682da32f205e81c01583873c04124e172e76539b1e722981` |
| Independent audit | `57df74042ea0313a05d1c006f955aea5fce1ef5b9fee3f2d9fa8836427d3be92` |

The audit verifies actual model bytes, receipt artifacts, stdout, plan, inputs, command, limits, numerical source, and CPU settlement.
It also verifies preparation with the unchanged strict verifier.
It checks both attempts against their original registered design.
The audit reports all original incident JSON hashes without rewriting them.
An unchanged metadata copy lives under `campaigns/recovery_v34/c4-cold0-preserved-snapshot`.
Model bytes were verified but were not duplicated into that snapshot.

The current runtime contract equals the registered runtime exactly.
CPython 3.12.14, NumPy 2.3.5, and gmpy2 2.3.2 are available.
The registered CPU affinity remains available.
The original host-limit checks pass for all five remaining trials.
A minimal subprocess launch succeeds, and the C compiler is available.
`/proc/cpuinfo` and `/proc/self/status` are unavailable.
The reviewed controller and worker paths do not require either file.
These observations do not establish physical host identity, unchanged machine load, or equal cache conditions.
Native numerical kernel preflight was outside this independent incident audit.

The evidence supports a separately reviewed, append-only continuation for this exact incident.
The continuation must pin the original files and preserve the failed strict guard in its disclosure.
It must preserve all five unstarted trials, numerical settings, sample selection, order, and the existing ledger.
It must not rerun either completed trial, reset the budget, or install a generic exception.
A repeated incident does not establish its cause or excuse a future unexplained mismatch.

The audit script is `campaigns/recovery_v34/audit_c4_incident_v34.py`.
The immutable report is `campaigns/recovery_v34/c4-cold0-incident-independent-audit.json`.
The script refuses to overwrite an existing report.
Its final successful audit used 1.036105339 process CPU seconds, outside experimental worker accounting.
Two preliminary schema checks stopped before producing the final report.
They changed only this new audit script, never experimental evidence.
