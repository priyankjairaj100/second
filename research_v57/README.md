# Read-only completed-prefix audit

This audit inspects only V54 program03a6181b's completed preparation and cached
arm while other jobs remain active. It never edits historical sources, input
artifacts, worker receipts, schedules or budget files, and never calibrates or
runs neural inference. It writes one fresh audit directory.

Five miniature artifact/receipt fixtures must pass first. The audit then verifies
actual sealed commands/limits, complete artifact inventories, registered retained
tokens/provenance, unchanged retained descriptors, all24 stages/42,467,328 packed
codes across the three prepared representations and both cached successors,
literal storage and settled debits. It records mutable ledger snapshots before
and after the audit and requires selected completed debits to stay unchanged.
Other reservations may remain live; they are not called failed or settled.

This is partial artifact verification, not the final campaign audit. It does not
assert fresh-oracle equality, a compressed-service advantage, quality, independent
numeric reconstruction or ACL readiness. All earlier failed attempts remain.

Run only under the pinned CPU container via Slurm:1 CPU,16GiB,30minute wall bound.
The audit additionally sets1200/1201 CPU seconds,16GiB address space and64MiB
output-file limits. Software and read-only audit CPU are outside the immutable
empirical worker ledger and reported separately. Do not overwrite an old receipt.

Command: python -B -m research_v57.run V54_DIRECTORY FRESH_AUDIT_DIRECTORY
