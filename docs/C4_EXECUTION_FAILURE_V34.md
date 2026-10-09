# C4 execution failure and corrected preflight scope

This record supersedes the earlier V34 recommendation to execute the remaining C4 trials.
The first resumed trial failed before neural inference.
The campaign is blocked, and no automatic retry is permitted.
The earlier incident audit and continuation review remain unchanged for transparency.

The failed attempt is `campaigns/independent_c4_v32/attempts/c4-delete-0-repair`.
Its input verification passed, then checkpoint construction raised:

```text
FileNotFoundError: [Errno 2] No such file or directory: '/proc/self/maps'
```

The traceback identifies `transformer_backend._runtime_manifest`, called while constructing the checkpoint decoder.
This function needs procfs to identify actual loaded libraries and CPU dispatch properties.
No stage computation began.
No completion, model, or state output exists.
The preserved failed progress and controller seal agree.
The worker exited with code 1, and its failed outcome was sealed successfully.
A receipt-level `status: complete` describes sealing; its `outcome.status` correctly says `failed`.

The controller recorded 7.032934424 seconds.
Observed worker CPU was 6.324538 seconds, producing a settled seven-second charge.
C4 now has three settled debits totaling 429 of 1,900 CPU seconds.
There are no unsettled reservations.
The remaining allowance is 1,471 seconds, but it does not authorize retrying this failed attempt.
Four registered trials remain unstarted:

- `c4-delete-1-repair`
- `c4-delete-1-cold`
- `c4-root-convert`
- `c4-delete-0-compressed`

The independent failure audit verifies the receipt chain, full logs, plan, inputs, registered schedule, source, and ledger.
It verifies the absence of completed outputs and unexpected attempts.
It also verifies that the earlier incident evidence and immutable audits remain unchanged.
The failure report is `campaigns/recovery_v34/c4-repair0-procfs-failure-audit.json`.
Its SHA-256 is `110e8dafde9225872eb32bdd6fec58eae376eae38a6c74a130fcde3359cc8c8d`.
The reproducible read-only script is `campaigns/recovery_v34/audit_c4_failed_repair_v34.py`.
It refuses to overwrite its report.

## Correction to the previous preflight

The previous review checked portable runtime identity, worker limits, subprocess launch, compiler availability, and four native numerical fixtures.
Those checks passed and remain valid within their stated scope.
They did not invoke the checkpoint decoder's runtime manifest.
They therefore did not establish that a complete model worker could start.
The earlier inference that missing procfs would not block this workload was too broad.
The actual execution demonstrates the missing prerequisite.

The C4 stale-progress incident and this failure are distinct.
The reviewed adapter addressed the stale cold reference's evidence verification.
This new failure occurred earlier, in an ordinary lossless repair worker that did not use that adapter.
The cause of the stale-progress incidents remains unknown.
The cause of this new startup failure is the unavailable procfs file named in the traceback.

## Procfs requirements for local continuation

| Module | Required access | Purpose |
|---|---|---|
| `transformer_backend._runtime_manifest` | `/proc/self/maps`, `/proc/cpuinfo`, mapped library files | Bind actual libm, Python libraries, and CPU dispatch fields during decoder construction |
| `finite_primitives._primitive_manifest_bytes` | `/proc/self/maps`, mapped GMP/MPFR/MPC files | Bind the `mpfr_enclosure` primitive implementation |
| `transaction_timing` full observer | `/proc/self/status`, `/proc/<pid>/status`, `/proc/self/task` | Identify descendants and validate the subreaper observer |
| `arithmetic_audit._rss` | `/proc/self/statm` | Optional RSS diagnostic; absence is caught and disclosed |

The command-admission-only path does not use the full observer's procfs helpers.
That distinction did not eliminate the decoder's separate mandatory dependency.

Use a normal supported Linux environment with readable procfs and the actual mapped library files.
Run both decoder-runtime and MPFR-manifest preflight before registering a fresh local reproduction.
Do not invent CPU fields, copy another process's maps, suppress missing provenance, or edit historical evidence.
Keep this failed attempt and its charge.
For another machine, use a fresh registration and matched comparisons on that machine.
Do not combine historical cold timings with a new local repair as a reliable speedup claim.

This is an execution-environment failure, not a repair-speed observation or a numerical correctness failure.
No completed C4 repair/cold pair exists.
The broader research program remains incomplete.
