# Second V87: bounded worker outputs; quota still blocks execution

23 October 2026. The existing15-minute heartbeat remains ACTIVE. No new monitor,
delegation, paid compute, third-party message or submission. Read the continuous
queue, handoff/program_v87.json and research_v87/PROTOCOL.txt. The pending storage
question remains unanswered; do not repeat it while the state is unchanged.

At10:09UTC the account queue was empty and all19 V80/V81/V82 allocation outcomes
matched the preserved failures/cancellations. The12602-second unresolved ledger
reservation and zero-byte preparation completion were unchanged. The numerical
checkout was clean at f900999. Raw quota remained1048576004KiB used against the
1048576000KiB hard limit. No old job was retried and no registration was changed.
At10:19UTC the exact V85 quota helper ran in memory on the host, read-only. It
refused even one byte of requested headroom. No cluster file was written. This
is an observed negative-path check, not a passing software or launch gate.

V87 adds a bounded exclusive writer and read-only saved-extent inspector.
Models must have their exact packed extent before file creation; states retain
the1GiB cap. Metadata/completion are bounded at64MiB; at most512progress records
may each use1MiB. Every path is consumed once. Partial writes remain; incomplete
or failed outputs cannot become a successful completion. The complete prospective
matched worker and both audits now use these checks. V80 remains untouched.

Thirteen pure filesystem/refusal tests and14V84 protocol/submission tests pass.
The full101-check pinned-Linux gate remains unexecuted. Six prepared worker tests
now also inspect actual saved extents; these numerical fixtures were not run on
the Mac. No recovery package, registry, Slurm job or empirical result was created.
V84's old upstream success gates are impossible and still refuse; rebind only to
actual separately recovered evidence. The approved1,327,104grid allowance stands.

Per-worker output allowances are recorded for both prospective campaigns. A
ten-worker V80-equivalent recovery has30,432,559,104logical bytes of allowance;
the twenty-worker matched study has61,098,688,512. These are separate bounds,
not expected occupation or a reserved combined quota. They exclude staging,
controllers, logs, compiler temporaries, audit outputs and filesystem overhead.
Those remaining roles need an explicit plan and host/controller integration
before claiming that full-chain storage admission is ready.

Next: continue the recovery/controller integration locally while storage is blocked.
Qualify its separately registered Linux gate only after headroom returns. Keep the
full failed reservation and the preserved
120624numerical/7224controller ceilings; never use scheduler CPU to refund it.
The prospective complete recovery still fits120622/6622including old allowances.
All871frozen sources,5auxiliary commitments and old artifacts must stay unchanged.
V72science and the V74manuscript remain unchanged. Native layout and final delivery
choices remain open; no repeat preview attempt was made on this unchanged wake.
