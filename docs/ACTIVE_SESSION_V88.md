# Second V88: project and temporary storage admission prepared

23 October 2026. The existing 15-minute heartbeat remains ACTIVE. No new monitor,
delegation, paid compute, third-party message or submission. Read the ordered
queue, handoff/program_v88.json and research_v88/PROTOCOL.txt. The pending request
to restore account storage remains unanswered. Do not repeat it while unchanged.

At 10:38 UTC the account queue was empty. All 19 original V80/V81/V82 job outcomes
matched the preserved failures and cancellations. The old ledger hash, full
12602-second reservation and zero-byte completion were unchanged. Numerical
checkout f900999 was clean. GitHub PR1 was OPEN/draft at 41a2d04 before this work.
No old job, source, registration, lock, ledger or partial artifact was modified.

The source review found an uncovered storage domain: the frozen controller's two
worker streams and native compiler trees use the default temporary filesystem.
A project-only quota check cannot admit those files. The new V88 helper checks
both existing write roots and aggregates their requirements if they share a
filesystem. It also checks the actual new-file group when group quotas are
enabled. Existing parent setgid inheritance is respected. Unknown quota,
unsupported project-quota, inconsistent mounts and insufficient capacity refuse.

Read-only host probes observed the project on /dev/sdb1, ext4 with user/group
quotas. The existing /tmp is on /dev/sda4, XFS with explicit noquota. The observed
new-file group has explicit zero limits. The user quota remains exhausted;
neither group status nor free temporary space overrides it. At 10:52 UTC the
final source-bound probe refused even one byte of project headroom. Source ran
in memory with -B; no cluster file was created. Both probe receipts and the
initial helper source before group review are preserved.

Eighteen new pure tests and six existing quota tests pass. Static undefined-name
and syntax checks pass. These do not qualify numerical results, the Linux gate,
a positive host admission, the container's filesystem mapping or a new launcher.
V84 remains unchanged and unregistered with its 101-test Linux gate unexecuted.
All 871 frozen sources and five auxiliary commitments still match their hashes.

research_v88/WRITE_SCOPE_REVIEW.txt identifies the remaining finite write roles.
It distinguishes worker outputs from controller/ledger/entry records, staging,
audit/accounting reports, Slurm logs, compiler/test temporaries and allocation
overhead. The worker file-size limit does not establish a cap on an external
Slurm logging process. A JSON reader limit is not every writer's output limit.
The V87 logical worker bounds remain useful but are not a full-chain allowance.

Next, finish the per-role allowance and host/controller integration locally.
Keep fresh storage admission overhead in the complete transaction and accounting
scopes. Verify the existing container temporary mapping without redirecting files
around the account quota. Then prepare the separately registered recovery under
the unchanged numerical/controller ceilings, carrying the old full reservation.
Only after capacity returns and software qualification passes may a fresh finite
chain be launched. Inspect all old jobs and receipts first. V84's failed upstream
success gates must not be weakened or reused; bind actual new recovered evidence.

V72 science and the V74 manuscript/bundle remain unchanged. The same open source
still matches bf3b7a73cda7b4c62fb7fe6fc7df08a36e949cb15f4c0d9e361fc25a732cc8eb.
No new speedup or transfer result exists. No manuscript edit or repeated native
preview attempt was warranted by these infrastructure findings. Rendered layout
and final delivery choices remain open; the agreed bundle is not yet complete.
