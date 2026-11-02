# Second V90: transfer wiring fixes and bounded storage components

24 October 2026. Existing scheduler ACTIVE. Read the ordered queue and
handoff/program_v90.json. No new registration, upload, fetch or job in this
checkpoint. The running V89 program and all934bound files remain immutable.

At07:38:21UTC(13:08IST),16005was RUNNING34:11with all13source replays and3of24
stage certificates.16006--16016were dependency-pending;16004remains COMPLETED0:0
with162Linux checks. No preparation completion, primary audit or supplemental
audit yet. The old19outcomes,15,987-byte ledger/hash and zero-byte completion
were unchanged. Numerical checkout remained clean f900999. The cluster receipt
is pilots/transfer-engineering-v90-20261024/cluster-reconciliation.json.
Never rerun prepare.py or either V89 submission mode. Require both actual audits
and the frozen terminal reporter before any new scientific conclusion.

Independent source work found two real prospective-transfer wiring defects:
1. V82 target_worker imports its command verifier from src.worker_control, where
   that function does not exist.
2. V82/V84 ledger producers use program_sha256/sources_sha256 while the historical
   verifier expects protocol_sha256/source_sha256. Fixing only the import would
   still refuse admission. Existing tiny worker fixtures mock this verifier.
These are source/local-fixture findings, not causes inferred from the cancelled
jobs and not evidence against model transfer. V89 uses the matching historical
ledger identity and is unaffected. All frozen files remain unchanged.

research_v90 now contains separate bounded RunStore/PhaseBudget/worker_control
forks, an exact-command read-only admission contract shared with future ledger
producers, a finite exclusive metadata writer and a source-bound progress census.
Unknown CPU stays charged; worker roots/attempts cannot be reused. Metadata is
bounded before writes. Scientific state/model limits and full diagnostics stay
unchanged. Progress uses1714maximum files across20workers instead of10240,
removing8.326GiB of unused logical allowance. Per-record1MiB and complete JSON
64MiB limits remain. Every phase/certificate/fallback diagnostic is retained;
unexpected output refuses the new attempt, never truncates into success.

48pure local checks pass on Python3.12.7; static undefined-name and source syntax
checks pass. Three generated Linux child/ledger checks are prepared, NOT run.
A read-only recovery gate now binds the actual V89 terminal schema, all13jobs,
both audits, all eight comparisons, registered input bytes and preserved failures.
Its seven tests use synthetic report structures; no actual V89 success exists.
The initial Python3.9.6 invocation produced9errors from unsupported Path.stat
arguments; that local failure is recorded. No model executed locally. Read
research_v90/PROTOCOL.txt and local-validation.json for scope and source hashes.

The prospective complete write census covers both admission and full transfer,
including source staging, GPT2 partial fetch, all22workers, controller replacement,
metadata, logs, audits, temporaries and allocation/inode margins. It totals
73,550,418,439project bytes(68.50GiB) plus17,263,765,504temporary bytes(16.08GiB).
It is NOT a measured peak, reserved space, formal disk bound or launch admission.
The explicit eligible_for_storage_admission flag is false. The new packager,
host, entry, target/complete worker, submit, fetch, seal/audit and terminal callers
still need integration and separate pinned-Linux qualification. Do not substitute
these components or their lower allowance into the registered V89 run.

Next work:
- Close the existing V89 chain from actual receipts, then apply the preserved
  research_v82/DECISION_RULES.txt. No new speed/transfer/negative claim yet.
- Prepare a new transfer orchestration using the shared V90 admission identity
  and bounded writers. Preserve selection/work/order/caps and the two failed
  old registrations. Bind actual V89 terminal evidence and old failure carry.
  Host controller allowance for the20-worker screen stays302seconds each,
  6040total; do not copy V89's602per worker. Include the actual V81 transfer
  suites and real child-command qualification, not only mocked fixture paths.
- Only after complete source/callsite review and fresh V85/V88 capacity checks
  may a separately registered software/admission chain launch. After actual
  target closure, register the20-worker/16comparison screen if justified.

The same V74 manuscript SHA remains
bf3b7a73cda7b4c62fb7fe6fc7df08a36e949cb15f4c0d9e361fc25a732cc8eb.
No source edit or new compile was needed. A single native-preview access attempt
failed at service startup and was not repeated. Layout and final delivery choice
remain unresolved. V72's verified bounded storage/access/latency story stands;
the expanded campaign and agreed submission bundle remain incomplete.
