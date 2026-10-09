# Independent review of the V33 terminal recovery

Reviewed on 9 October 2026, before registering the continuation.
No original experiment file was changed.
No empirical worker was run during this review.

| Reviewed file | SHA-256 |
| --- | --- |
| `scripts/launch_independent_requests_v33.py` | `6fe962266a7b9d06b4dc81940ae2aa1841bde56bc8343a148c90dff790b784e1` |
| `scripts/verify_terminal_recovery_v33.py` | `2c88ee87912ce4137517e538330ec8790c5a578aa38909975286fa57347b1a70` |
| `tests/test_terminal_recovery_v33.py` | `0a51e679cd2d108ad13150e4d30939b6dce69884f2065d4e565aad5d49191c92` |

Decision: cleared for the explicit, incident-specific append-only continuation.
The unchanged original verifier still rejects the affected attempt.
The review does not claim that its original three-copy contract passed.

## Independently verified incident

The affected attempt is `wikitext-delete-1-cold` in `campaigns/independent_wikitext_v32`.
Its live progress file contains a running snapshot through `model_write_started`.
Its completion file and controller seal contain identical complete records.
The receipt-bound stdout terminal marker commits that same complete record.

The independent audit passed 23 checks.
These include the registered plan, actual input hashes, command, runtime, limits, receipt, ledger, and complete model.
The retained model parses as all 24 stages and 42,467,328 codes.
The controller duration is 146,184,272,791 nanoseconds.
Its settled worker charge is 147 CPU seconds.

The live phases form an exact prefix of the committed terminal phases.
The terminal adds `model_write_complete` and `complete`, plus the expected final output fields.
All other top-level values agree.
The source of the stale live file remains unknown.
Neither modification times nor similar earlier incidents establish its cause.

The audit is `campaigns/recovery_v32/cold1-incident-independent-audit.json`.
Its SHA-256 is `f55ad83f5b578a04682b31e47aea4dac3f2f3f11e939879a90e74508df01ebf8`.
Thirteen original metadata files were copied unchanged into `campaigns/recovery_v32/cold1-preserved-snapshot`.
Its manifest hash is `bc0b537b21e7e5237bb6f322ca438beea955b895c4e09a44389573ae5fa4a6c3`.
The original live progress, completion, seal, receipt, and timing records remain unchanged.

## Scope of the amended verifier

The exception identifies one exact original attempt path, program hash, and protocol hash.
It also pins the preserved snapshot, independent audit, terminal hash, and stale live hash.
Changing any pinned evidence causes rejection.
Every other attempt uses the unchanged strict verifier.

The exception still checks receipt artifacts, plan identity, stdout commitment, successful exit, CPU settlement, and output hashes.
The enclosing controller independently checks the registered plan, source, command, runtime, limits, and current ledger debit.
It introduces no global monkeypatch and rewrites no progress file.

All four existing attempts passed the new enclosing verification independently.
The first three use their original strict path.
The fourth is accepted only under the disclosed recovery amendment.
That distinction must remain visible in analysis and reporting.

## Continuation constraints

WikiText retains its original program, protocol, source snapshot, and CPU ledger.
The existing 656-second settled charge remains intact.
The phase cap remains 1,900 seconds, with no additional allowance.
Only the three registered, unstarted WikiText trials may run.
Completed trials cannot be repeated.

The amendment binds all surviving prior JSON evidence and its settled debits.
It cannot change sources, thresholds, numerical policy, preparation, or request selection.
Each new WikiText plan binds the append-only amendment hash.

The affected cold model is a comparison reference, not a numerical input to the remaining workers.
Those workers consume unaffected original preparation and first-request evidence.
The compressed comparison still uses the unaffected first cold request.
C4 retains its seven original trials, selected sources, order, and separate 1,900-second allowance.

The primary clock remains unchanged.
It excludes controller bootstrap and post-receipt archival checks, as already documented.
Scientific losses remain preserved and do not prevent the fixed second corpus from running.
Execution, exactness, or new integrity failures still stop dependent work.

## Validation and reporting

All 13 pre-execution recovery tests passed independently in 9.258 seconds.
They cover changed live/terminal/seal evidence, changed snapshot/program/model bindings, unrelated paths, and altered prior debits.
They also cover forbidden budget changes, source changes, reordered trials, and repeated completed trials.
These checks assume the recorded pre-execution state: four completed and three unstarted WikiText trials.

The second WikiText lossless pair must be marked as incident-recovered.
Include a sensitivity summary excluding that pair.
Do not remove the original integrity failure from the archive or interpret recovery as an algorithmic improvement.

The remaining workers should run serially without concurrent filesystem tools or agents.
This is a precaution, not a proven explanation for the incident.
After this review, this reviewer performs no filesystem work during those empirical timings.
