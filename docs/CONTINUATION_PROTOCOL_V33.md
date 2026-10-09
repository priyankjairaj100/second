# V33 continuation after an exact terminal-copy discrepancy

Dated 9 October 2026, UTC.

The original V32 three-copy validation fails for `wikitext-delete-1-cold`.
Its live progress file contains an earlier `running` record.
Its completion and controller-sealed records agree byte-for-byte.
The receipt-bound stdout marker commits to those terminal bytes.
The recorded model bytes, plan, command, source, schedule, and settled debit also verify.
The cause of the stale live file remains unknown.

Original evidence is preserved under its original paths.
An independent audit and unchanged metadata snapshot appear under `campaigns/recovery_v32/`.
Do not rewrite the live progress file or describe the original contract as intact.

## Exact scope

`scripts/verify_terminal_recovery_v33.py` permits one exact reviewed discrepancy.
It pins the original attempt path, program, protocol, independent audit, and preserved snapshot.
It checks all thirteen original metadata bindings against the preserved snapshot.
It requires the original stale-live bytes and matching completion/seal bytes exactly.
It retains stdout, receipt, identity, plan, settlement, and actual model-byte checks.
Every other attempt uses the unchanged strict verifier.
A new discrepancy is refused.

The enclosing V33 controller also verifies the registered plan and exact inputs.
It checks the literal worker command, runtime, resource limits, source inventory, and current ledger debit.
The recovered terminal dictionary remains the original dictionary.
Recovery provenance is recorded separately, never inserted into original evidence.

## Preserved experiment

WikiText keeps its original program, protocol, numerical source snapshot, and CPU ledger.
The four existing transactions are not repeated.
Their settled charge remains 656 CPU seconds.
The original cap remains 1,900 seconds, with no new allowance.

Only these unstarted WikiText trials may continue:

1. `wikitext-delete-1-repair`
2. `wikitext-root-convert`
3. `wikitext-delete-0-compressed`

The append-only `continuation-v1.json` binds the prior ledger, all prior metadata, and the amended controller hashes.
Each new WikiText plan binds that continuation digest.
The worker still executes the originally frozen numerical source and original resource policy.

C4 retains all seven originally selected trials and both source records.
Its fresh program binds the V33 controller and the WikiText recovery digest.
C4 registration requires complete, settled WikiText evidence under this explicit recovery protocol.
A completed scientific loss never causes source replacement or omission.

The second WikiText lossless pair uses the recovered cold terminal.
Report that pair as incident-recovered and show a sensitivity summary excluding it.
The compressed comparison uses the unaffected deletion-zero cold trial.
This recovery must not erase the original integrity failure from reports.

## Execution

Complete code review and software checks before registration.
Run the following first:

```sh
.venv/bin/python scripts/launch_independent_requests_v33.py --preflight-continuation
.venv/bin/python -m unittest tests.test_terminal_recovery_v33 -v
```

Then register once, inspect the new amendment, and publish its checkpoint:

```sh
.venv/bin/python scripts/launch_independent_requests_v33.py --register-continuation
```

After that checkpoint, execute the remaining program in one serial process:

```sh
.venv/bin/python scripts/launch_independent_requests_v33.py --execute-remaining
```

The process flushes an outcome after each transaction.
It stops after any execution failure, mismatch, new integrity discrepancy, or unresolved reservation.
It performs no automatic retry.

During timed execution, use only process-output waits.
Do not run concurrent filesystem tools or agents.
This is a scheduling precaution, not an established explanation of the earlier discrepancy.

The primary clock boundary is unchanged.
It excludes prerequisite/bootstrap checks and final comparison, gate, and sidecar analysis.
Preparation and conversion remain separate setup costs.
No complete shell-invocation latency claim follows.

## Local reproduction

V33 is a narrow continuation of the preserved incident campaign.
It requires the original binary outputs and bound paths.
A fresh Git clone without those binaries must use a new V32 reproduction workspace.
Do not manufacture the incident state or overwrite a published registration.
Follow `docs/LOCAL_LLM_RESUME_V32.md` for that fresh reproduction.
