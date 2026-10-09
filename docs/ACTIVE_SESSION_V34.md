# Current execution checkpoint: C4 stopped on a runtime dependency

Updated 9 October 2026. No empirical worker is running.
Read this before historical execution notes or commands.

## Completed results

WikiText has seven settled transactions, charging 927 CPU seconds.
Its full binary audit is `campaigns/independent_wikitext_v32/analysis-v33.json`.
The two lossless repairs match their complete cold models exactly and have observed ratios of 1.868474 and 1.788250.
Compressed repair also matches exactly, with a 1.071595 observed ratio and 5.5763% smaller service state.
Including the required base checkpoint reduces that storage saving to approximately 0.70%.
Read `docs/RESEARCH_DECISION_V34.md` for scientific interpretation and remaining paper requirements.

C4 preparation and its first cold reconstruction completed numerically.
They used 292.064861678 and 128.609518354 controller seconds, respectively.
Their combined settled charge is 422 CPU seconds.
The cold trial has a preserved stale live-progress copy, admitted only by a reviewed V34 incident-specific recovery.
The original strict three-copy guard still fails.
Its cause remains unknown.
No C4 repair/cold speed comparison is complete.

## Latest failure and exact continuation boundary

The reviewed V34 amendment was published before execution at `d6e20876183435acb099fcf43e0e3cfd5f2d4659`.
Its SHA-256 is `ce08a60402ec3ea9deba95ed2acfd19966307b0c93140ec409d5e144c6e42a27`.
It preserved the original program, numerical source inventory, reference input, order, and ledger.
It explicitly bound a compressed-worker adapter with only a changed evidence-verifier import.

The first resumed trial, `c4-delete-0-repair`, failed during checkpoint loading, before model computation.
The exception is `FileNotFoundError: /proc/self/maps` in `src/transformer_backend.py::_runtime_manifest`.
That manifest also requires `/proc/cpuinfo` to bind hardware dispatch fields.
The controller transaction took 7.032934424 seconds and charged 7 CPU seconds.
The C4 ledger now contains three settled debits totaling 429 of 1,900 CPU seconds.
The unused allowance is 1,471 seconds; it is not permission to retry a failed registered attempt.
Four later trials remain unstarted.
No empirical worker remains active.

This is an infrastructure failure, not a numerical mismatch, latency loss, or certificate rejection.
The software-runtime fingerprint, resource-limit checks, and native fixtures passed earlier.
Those checks did not exercise the deeper checkpoint runtime manifest.
Their earlier positive conclusions must not be interpreted as a full checkpoint preflight.
The append-only failure audit records the correction without rewriting earlier evidence.

Do not rerun `--execute-remaining` here: the controller correctly stops on the failed attempt.
Do not fabricate proc files, copy historical runtime manifests, weaken attestation, edit original receipts, or reset the ledger.
The current execution surface does not expose the runtime interfaces required by this numerical target.
An equivalent portable backend would require a separately reviewed target and new registration.
It is not implemented by this checkpoint.

## Safe local continuation

Use a Linux environment with real readable `/proc/self/maps`, `/proc/cpuinfo`, and the other required proc interfaces.
Run `scripts/preflight_environment_v34.py` before launching any empirical worker.
Follow `docs/LOCAL_LLM_RESUME_V32.md` for dependencies, exact checkpoint recovery, and fresh registration.
A fresh machine uses the original V32 controller with `--workspace local_runs/replay-001`.
Incident-specific exceptions never apply to new campaigns.
The fresh run is a new registered reproduction, not an overwrite or hidden retry of these historical attempts.
Archive every outcome with `scripts/export_local_evidence_v32.py` and keep generated binaries on durable local storage.

Git contains code, selected token inputs, registration, evidence, audit reports, and artifact hashes.
It excludes large weights and derived state/model binaries; the recovery guide explains regeneration.
The full empirical program and ACL submission remain incomplete.
