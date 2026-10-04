# Artifact-verified transaction and lifetime analysis

`src/measured_analysis.py` analyzes the frozen v9 measured inventories. It performs
no model execution. Research remains paused. Software fixtures establish analysis
behavior, not empirical speed, quality, scientific provenance, or power.

```
python scripts/summarize_measured.py INVENTORY.json CAMPAIGN_OUTPUT
python scripts/summarize_measured.py INVENTORY.json CAMPAIGN_OUTPUT --sequence
```

The inventory is mandatory. Its complete planned slots, sources, normalized
manifests, target, runtime contract, method orders, protocol and analysis groups
are validated before reading outcomes. Missing runs and unsealed attempts remain
explicit outcomes. Reading a missing output does not create a run directory.
Malformed or mutated sealed evidence raises an error; it cannot produce a ratio.
The older `result_analysis.py` retains its separate warm/state-only contract.

## What is verified

The engine verifier checks the sealed archive, observer tree, child artifacts,
source/input bindings and phase-budget evidence. Analysis then rereads each
observer and child receipt, checks its complete accounting partition, and obtains
model bytes from the actual output. Common model equality means the frozen target
digest plus every ordered stage code. State equality applies to the three methods
that return the same declared canonical state. Model-only fresh has no deletion
state equality obligation. All four methods must supply the matching oracle
artifacts before an exact timing pair is usable.

Asserted `exact_model_equal`, `complete_wall_time_ns`, a shared output hash, or an
`outcome=complete` convenience field alone is insufficient. The public analysis
accepts `VerifiedMeasuredEvidence` issued by the artifact-aware loaders. The
separate `validate_measured_evidence_structure` checks shape and arithmetic only;
it does not issue verified evidence. Its
payload is a detached copy; a naked JSON dictionary is not accepted. This interface
is not a security capability against arbitrary Python code or hostile storage.
Hashes establish consistency within the trusted local archive, not authenticity
if an adversary can rewrite the entire archive and its bindings.

Each original observer identity and attempt occupies only one planned role.
Reopening a sealed original receipt is allowed and preserves its original clock.
Copying that observation into another root, repeat or method is rejected. No
resume wrapper duration is treated as an independent repetition. Indexed and
repair lifetime totals deliberately share one initial preparation observation;
that observation is loaded once and added once to each system's own total.

Clean eligibility requires explicit `execution_mode=clean` and both child and
observer instrumentation receipts. Optional Python profiling, tracing, allocation
tracing, monitoring allocations and detailed telemetry must all be disabled.
Required arithmetic counters remain charged. Absence of external native profilers
is unobserved and is not asserted. Diagnostic results retain exactness and outcome
information but cannot enter clean latency ratios.

## Three distinct comparisons

| Comparison | Baseline | Interpretation |
|---|---|---|
| Ordinary model output | `model_only_fresh` | Fresh retained quantization versus repair with its declared state |
| Equally indexed maintenance | `indexed_fresh` | Same available index/cache and output-state contract |
| Canonical state reconstruction | `direct_fresh` | Full retained canonical-state reconstruction; not ordinary requantization cost |

The complete method clock is the external observer's declared transaction:
source validation through child exit, controller commit/cleanup and output
validation. Its contiguous spans must sum exactly to the observed duration.
Nested child clocks are never added. Observer bootstrap and final observer receipt
writes remain outside this boundary. These are explicit exclusions, not a claim
that all conceivable delivery costs are measured. OS caches remain uncontrolled.

For ordered sequences, each system's lifetime is recomputed from its actual
initial preparation plus every scheduled request. Repair and indexed fresh use
the indexed original preparation. Model-only fresh uses a distinct original
model-only quantization. A failure or missing request makes the lifetime incomplete.
Direct-state oracles, equality checks, quality workers and sequence coordination
are separately recorded research/coordination costs and are not added to those
production totals. These lifetime totals use the declared method transaction
boundary; they are not a wall clock of the entire comparison campaign.

## Inference and failure accounting

For each configuration and request, all planned repeats of both compared methods
must finish exactly under clean clocks. Reduce repeats by each method's median
nanoseconds, form the log baseline/repair ratio, average request logs within each
root, then average roots equally. The deterministic percentile bootstrap resamples
roots only, using the frozen protocol's seed, draws and confidence. Timing repeats
and multiple requests from the same root are not independent samples. Root
independence remains the assumption of the frozen root-sampling design.

Available-pair summaries are explicitly conditional. Failed and missing slots
remain in outcome counts and the denominator, even when a conditional interval is
available. A confirmation timing rule requires a frozen unblocked confirmation
protocol, the primary analysis group, all planned exact clean completions, at least
two available roots, and a lower interval bound strictly above the frozen speed
threshold. Only the protocol's declared sole primary baseline/candidate receives
confirmation flags; indexed and full-state intervals remain secondary descriptions.
When there are multiple confirmation configuration/target strata, a frozen
`primary_configuration` string must select exactly one stratum; otherwise every
confirmation flag stays false.
No additional confirmatory comparisons are enabled without an explicit multiplicity
implementation. This rule does not establish workload provenance, quality, feasibility
coverage, resource feasibility, statistical power, or readiness to publish.

The loaders expose typed evidence for later policy assembly. Coverage denominators,
held-out quality, complete resource ledgers and real workload provenance require
their own bound artifacts; none is inferred from a favorable timing ratio.

Sequence loaders optionally select `execution_mode="clean"` or `"diagnostic"`
from the frozen inventory. The selected mode is bound in the returned payload and
every matching planned slot remains present. This permits paired diagnostic and
clean configurations under one protocol/inventory without arbitrary run selection.
The default includes both profiles and stratifies their timing analyses.

## Verified projections for conditional policy assembly

Successful child projections expose the target DAG only after the canonical target
payload hashes to the frozen target digest. Actual stage code hashes, retained IDs,
record-to-group assignments and canonical group membership come from verified model
and state bytes. The identity cache has no response-group assignment and reports
that projection as unavailable. Bound calibration artifacts supply original token
counts without model execution. A copied provenance label is explicitly an asserted
label, not independent proof of a real source or sampling law.

Diagnostic children expose their committed StageAudit rows, including replayed and
unknown groups, their exact work ledgers, and the original bounded telemetry payload.
Omission, saturation and unavailable fields are preserved. Clean children normally
have no StageAudit diagnostic rows and retain only required work ledgers; those
missing rows do not become empty replay lists or zero feature calls. Per-stage
coverage still requires a matched diagnostic replicate and complete relevant
denominators. The loader does not interpret a truncated funnel as exhaustive.

Requested quality workers are projected separately with their observer/worker
receipts, committed metric artifact, target and heldout bindings, and exact state
references. Successful metrics must refer to the original, current direct-fresh and
current repair states and use the token denominator derived from the bound heldout
artifact. Failed or unstarted quality stays explicit. Quality observations never
enter production lifetime sums, and diagnostic or clean quality does not by itself
establish native-framework equivalence or scientific provenance.

## Read-only protocol and archive resource snapshots

`read_budget_snapshot` in `src/phase_budget.py` reads the actual canonical shared
ledger without constructing `PhaseBudget`, creating directories/locks, or changing
admission. Its expected identity and caps come from the verified inventory and
protocol. A missing ledger is explicitly unavailable, with unknown attempts and
usage; it is never reported as zero consumed budget. The reader is bounded to
16 MiB and 100,000 attempts and rejects malformed debits, excessive integers,
symbolic paths and a file that changes during its read.

The evidence payload's `phase_budget_snapshot` includes every recorded attempt,
settled charge, unknown reservation, reservation overrun and phase over-cap flag,
not only selected analysis slots. Actual archived worker identities link their
budget attempt IDs and exact debit rows to that snapshot. Attempts outside this
campaign archive remain explicit. The ledger is reread after the archive scan to
reject concurrent changes. This is the complete trusted protocol ledger at read
time, not a project-wide, cross-protocol, physical CPU or hostile-host accounting
claim. Controller CPU remains outside its admission scope.

`archive_storage_snapshot` hashes every regular file under the supplied campaign
output root, including nontransaction receipts, logs, lineage, and failed/partial
archives. It records file sizes and separate transaction/nontransaction byte sums;
hardlink aliases count once per file object. These are serialized file bytes, not
allocated disk blocks or physical memory. Limits are 200,000 paths, 1 GiB per file,
and 64 GiB of unique-file bytes. Missing roots stay unavailable; symlinks, special
files and concurrent tree changes are rejected. Snapshot membership is the actual
output-root tree, not all input artifacts or every project file. No storage or
ledger snapshot removes the independent real-source provenance requirement.
