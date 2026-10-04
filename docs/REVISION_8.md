# Revision 8: complete comparisons and controlled execution

Date: 4 October 2026.
Research experiments remain paused.
This revision develops software, accounting, and prospective decisions.
It does not supply empirical observations.

## Scientific correction

The direct fresh oracle returns the retained model and its canonical deletion state.
That output requires constructing response summaries or a Gram cache.
Ordinary requantization only needs the retained model.
A comparison must respect this difference.

The new model-only control constructs every stage under its newly computed ancestors.
It uses the same certified finite evaluator and exact quantizer.
It creates no response chart or deletion index.
Common target digests and stage codes permit comparisons across state families.
The full-state oracle still checks canonical state equality.

This distinction strengthens the paper's cost claim.
A gain against rebuilding an unnecessary index cannot establish faster ordinary requantization.
The equally indexed comparator still receives all valid retained information.
The response and cache families still share their solvers with that comparator.
No deletion-exclusive solver advantage is established.

## Lifetime decision

For a fixed request horizon H, compare:

\[
T_{\mathrm{repair}}(H)=P_{\mathrm{index}}+\sum_{h=1}^{H}R_h,
\qquad
T_{\mathrm{fresh}}(H)=P_{\mathrm{model}}+\sum_{h=1}^{H}F_h.
\]

Here, every term uses its declared complete transaction boundary.
Preparation includes the original output that each system actually needs.
Repair also pays for retained state maintenance.
Model-only fresh pays for each retained requantization.
Required online verification, input loading, output, commitment, and cleanup remain charged.
External research oracle checks receive separate accounting.
They cannot be charged asymmetrically to create an apparent service advantage.

The first feasibility decision uses H=3.
The repair lifetime must be smaller on every feasibility root.
Missing timing or an unsupported boundary leaves that decision open.
Passing this engineering gate does not establish population speedup.
Confirmation still needs independent roots, a frozen inventory, and justified precision.

## Implemented execution paths

Frozen isolated campaigns bind configurations, roots, requests, repeats, methods, and source code.
Confirmation workers verify their inventory evidence before execution.
Optional quality evaluation uses a separate worker and the same CPU ledger.
Its finite NLL measurements remain separate from method clocks.

Frozen sequence campaigns bind complete ordered requests and predecessor lineage.
One limited worker executes each sequence.
It prepares original state once and validates every retained state.
Failures and unstarted requests remain visible.
Sequence methods remain warm inside that worker.
Operating-system caches remain uncontrolled.

The external observer measures a complete child transaction through output verification and cleanup.
Its final observer receipt lies outside the measured interval.
The declared components form a disjoint partition of that interval.
Separate output contracts prevent mixing model-only, state, comparison, and sequence measurements.
A full comparison clock cannot substitute for a single method clock.
Supported isolated child roles expose complete individual state transactions.

Research model-only execution requires a live protocol admission record for its exact command.
Model-only confirmation still needs a compatible frozen inventory.
No current protocol authorizes research execution.

## Diagnostic evidence

The optional arithmetic audit observes standard Fraction construction in the current thread and process.
It records numerator and denominator bit lengths without retaining rational values.
It records available traced memory, process RSS, and artifact sizes.
Child processes and hidden integer intermediates remain outside its scope.
An incomplete observation cannot become a zero-work claim.

The runner marks profiled observations internally.
The speed analyzer excludes those observations even when the external audit report is absent.
Exact model and state checks remain valid under profiling.
Profiled times remain diagnostic.

The certificate funnel records domains, available descriptors, bounds, decision checks, and replay.
Disposition counts cover recorded stages and events.
Omission and saturation counters expose lost detail.
Large exact values receive bounded sign and bit-length summaries.
The numerical target and canonical state remain unchanged.
Provider internals can still remain unavailable.

## Remaining scientific work

The frozen feasibility policy now specifies resource, coverage, quality, preparation, and lifetime decisions.
Its thresholds are engineering choices.
Actual model feasibility and useful certificate coverage remain unmeasured.
Real inputs, source partitions, frozen configurations, and statistical precision remain unresolved.
The next empirical stage still requires the user's instruction to resume experiments.

The paper must eventually establish exactness, useful avoided computation, full costs, and language quality on real workloads.
Until then, the strongest supported result is a reviewed reference implementation under explicit contracts.
