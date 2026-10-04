# Durable phase CPU admission

Revision 7 implements cumulative CPU admission for the trusted local comparison worker.
This component does not establish empirical speed or resume research experiments.

## Declared scope

The protocol supplies `resources.phase_cpu_hour_caps`.
Every research execution phase requires an explicit positive cap.
The executor converts decimal hours into seconds and rounds downward.
Software correctness fixtures can use a bounded default.
That default equals their planned worker allowances.

The ledger sits beside the protocol.
Its directory name contains the exact protocol hash.
The identity binds that protocol, source hashes, phase caps, and accounting scope.
Changing only the output directory preserves the same ledger.
Changing the frozen protocol creates a different budget scope.
Cross-protocol project totals require a separate project ledger.
Do not report these scopes as one project-wide cap.

The existing inventory supports development, confirmation, and software-test phases.
Configured feasibility caps need a distinct supported execution phase before they control feasibility work separately.

## Admission and restart

Each worker attempt reserves its allowance before process creation.
The allowance equals its soft CPU limit plus two seconds.
This includes the one-second hard-limit gap and a one-second accounting cushion.

A POSIX advisory lock serializes each ledger read, admission, and update.
Atomic replacement and directory synchronization persist every reservation.
Admission rejects any allowance exceeding the remaining phase cap.
Duplicate attempt identifiers cannot obtain another reservation.

An interrupted controller can leave a pending reservation.
That reservation retains its complete charge.
A retry obtains a new attempt identifier and needs a new allowance.
The old worker cannot receive another allowance through identifier reuse.

The controller records CPU usage with `wait4` when it reaps the worker.
It rounds reported user and system CPU upward to nanoseconds.
Settlement rounds total CPU upward to whole seconds, with a one-second minimum.
An identical settlement is idempotent.
A different second settlement fails.

Missing usage never releases an allowance.
This includes launch failures without an observed worker.
The policy deliberately sacrifices unused capacity after uncertain interruptions.
Successful worker resume returns its verified terminal record without another reservation.
Resume also checks its saved debit against the ledger.

## Observed CPU and containment limits

The worker receives `RLIMIT_CPU`, address-space limits, file-size limits, and CPU affinity.
The controller also enforces a wall timeout and ordinary process-group cleanup.
The supported comparison program does not launch child processes.

`RLIMIT_CPU` limits one process.
It does not contain a hostile process tree.
`wait4` reports the worker and any waited-for descendant usage included by the operating system.
Unwaited or escaped descendants have no complete accounting guarantee here.

Kernel enforcement can overshoot a CPU allowance.
The one-second cushion is not a theorem about every kernel or thread schedule.
Observed overruns enter the ledger without clipping.
An over-cap ledger prevents subsequent admission.
Therefore the cap controls admitted allowances, not an absolute physical CPU ceiling.
Controller CPU and filesystem synchronization remain outside this worker CPU ledger.
Complete-service cost measurements must still include their declared costs.

Let the current debit equal settled charges plus pending allowances.
Each admission requires the new debit to remain within its cap.
Every settlement below its allowance can only decrease that debit.
Thus the debit stays within the cap when every observed charge respects its allowance.
Unknown interruptions preserve this invariant by retaining their allowance.
An observed overrun explicitly invalidates that conditional bound and closes further admission.

The address-space limit is not an RSS limit.
Recorded `wait4` peak RSS is diagnostic Linux accounting.
It does not replace the address-space admission policy.

## Durable outcomes

Budget denial creates a terminal failed worker record without process launch.
The campaign preserves that planned attempt in its failure denominator.
Completed campaign records include the budget snapshot at completion.
Later campaigns can change the shared ledger without rewriting that historical snapshot.

The ledger assumes trusted local storage.
It detects malformed records and mismatched identities.
It does not authenticate hostile edits, restore deleted ledgers, or erase historical state.
The executable source hashes remain checked before dispatch and resume.

## Implementation and tests

- `src/phase_budget.py` implements locked admission and settlement.
- `src/worker_control.py` implements `wait4` accounting and worker integration.
- `src/experiment_campaign.py` resolves caps and shares the protocol ledger.
- `tests/test_execution_budgets_v7.py` checks restart, rounding, exhaustion, overrun, and output-directory reuse.
- Independent review adds concurrent admission and mutation checks.

Methods still share one warm process in the existing campaign executor.
The separate isolated executor instead gives each method its own process.
Read `ISOLATED_COMPARISON.md` for that executor's measured boundary and remaining inventory gate.
Operating-system caches remain uncontrolled in both paths.
