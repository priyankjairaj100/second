# Second V93: cost interpretation prepared; experiment still running

24 October 2026. Reporting checkpoint only. V92 remains the complete prepared
transfer implementation. The scheduler is ACTIVE. No V91/V92 package,
registration, fetch, target or new job exists.

At 08:49:46 UTC (14:19 IST), V89 preparation16005 was RUNNING at1:45:36.
All13 source replays,24 stage certificates and48 payload-stage records exist.
No preparation completion/host receipt or either audit exists.16006–16016 are
dependency-pending. Software16004 completed0:0 with162 tests. Old19 outcomes,
the15987-byte unresolved ledger and empty completion remain unchanged;
numerical f900999 is clean. This is partial progress, not a complete model.
Receipt: pilots/reporting-scope-v93-20261024/cluster-reconciliation.json.

Source inspection found two reporting pitfalls, not a measured model failure:
fallback source replay is already inside a stage timer, and optimized cells
combine token-neighbor changes with decoder/cache changes. Do not double-count
extraction or claim an isolated decoder/cache contribution. These records do
not isolate decoder duration. Read docs/COST_SCOPE_REVIEW_V93.txt.

New reporting_v93/cost_scope.py provides pure scalar helpers for a disjoint host
partition and exact per-endpoint ratios. They preserve all eight observations,
including opposing win/loss directions. Six generated tests pass. These helpers
cannot certify actual inputs and have not reduced empirical results. Require
actual terminal closure and terminal-bound receipt verification before use.
They are outside numerical/software launch gates. All934 V89 files,930 local
counterparts,18 V90,33 V91 and38 V92 commitments remain unchanged. V92 retains
its142 local checks and221 unexecuted Linux checks.

Next remains V89 closure and the V82 evidence-based decision. If justified, use
the prepared V91 admission and V92 matched experiment in separate namespaces
under unchanged caps. Never retry a consumed attempt. Reporting preparation
is not launch authorization or evidence of speed, transfer or quality.

The same V74 manuscript is unchanged; no new audited finding warrants a claim
edit. Native rendering remains unresolved after the recent startup failure;
it was not polled again this wake. Final delivery choices and expanded research
remain incomplete. No new monitor, subagent, paid compute or submission.
