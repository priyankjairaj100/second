# Executable feasibility decisions and lifetime accounting

Revision 9 preparation. Research experiments remain paused.

`src/feasibility_decision.py` applies the unchanged policy in
`configs/feasibility_gates_v1.json`. It adds an executable conditional decision,
not a feasibility result. No real model or dataset was run for this work.
The numerical thresholds remain prospective engineering choices.

## Evidence and trust boundary

`evaluate_feasibility(policy, evidence)` is pure: it performs no file reads,
model execution, archive mutation, or research authorization. It validates
structure and computes exact count, integer-cost, and finite-score comparisons.
Malformed, incomplete, capped, omitted, or ineligible evidence cannot pass.
Missing values never become zero work, perfect coverage, or an absent failure.

The function cannot establish that supplied JSON describes observations.
Hashes in a document do not establish their own correspondence with real files.
An asserted `archive_validation="verified"` is a required input premise, not an
authentication mechanism. A positive result is therefore named
`conditional_promote_to_development`. Every result explicitly sets:

- `empirical_attainment_established=false`
- `research_execution_authorized=false`
- `confirmation_authorized=false`
- `population_speedup_established=false`

Actual use requires artifact-aware verification of the complete frozen schedule,
original observer receipts, output artifacts, source and target identities,
phase debits, and separately bound diagnostics. The measured-analysis loaders
produce `VerifiedMeasuredEvidence` only after inspecting those archives.
Their trusted-local consistency checks do not authenticate hostile storage or
establish real source provenance, sampling independence, or useful NLP quality.
Plain dictionaries must not be substituted for loader-issued measured evidence.

## Public archive bridge

The preferred public entry point is
`src/feasibility_archive.py:evaluate_archive_feasibility(policy, clean, diagnostic)`.
It accepts only loader-issued `VerifiedMeasuredEvidence` snapshots. Its companion
`assemble_feasibility_evidence` emits `assembled-feasibility-evidence-v1`: actual
available facts plus explicit missing premises, not a fabricated complete input.

Clean and diagnostic runs must be frozen together under the same protocol. The
sequence loader's `execution_mode="clean"` and `execution_mode="diagnostic"`
filters select all frozen slots of that profile from the combined inventory.
The assembler matches root, sequence, and repetition; requires matching target,
source, algorithm configuration and ordered deletion requests; rejects extra
diagnostic sequences; and rejects multiple configurations or repetitions per
feasibility root rather than selecting favorable results.

The archive bridge derives:

- Original record/token counts, retained state memberships, the complete target
  graph, per-stage code hashes, exact state/model agreement, and complete matched
  lifetime terms from verified artifacts.
- Changed-ancestor coverage from a matched diagnostic replicate with exact
  predecessor/current code and canonical-state parity. Full `StageAudit` replay
  group membership is checked against complete per-stage event/disposition
  counts and the actual retained target-feature ledger. First/last event samples
  do not stand in for the complete replay list. Missing stages, caps, overflow,
  saturation, event omission, or count disagreement prevent coverage inference.
  Response-service source binding justifies one target evaluation per retained
  record in each replayed group. Unsupported cache-family membership remains
  explicitly unavailable.
- Heldout quality from the separately verified quality artifact, actual heldout
  token file, exact canonical-state bindings, equal positive target counts, and
  a common metric contract. It applies the exact finite-score/log enclosure
  comparison described below; quality worker time is not a primary latency.
- All workers and files under each supplied campaign output root, including
  unselected profile workers, failed or unfinished attempts, observer archives,
  and other nontransaction files. Hardlink aliases are explicit and unique file
  bytes are counted once. Every file is checked against the artifact-size cap;
  all available worker CPU, elapsed time, RSS and configured caps are checked.
- The actual complete shared protocol admission ledger at read time, including
  attempts outside the supplied archives, fully charged pending reservations,
  settled usage and reservation overruns. Unknown workers or reservations stay
  incomplete. Two snapshots of the same ledger or output root must agree; the
  bridge does not silently use an older smaller charge.

The ledger is trusted local protocol admission accounting, not project/global
CPU containment. File accounting covers supplied campaign output roots, not
inputs, allocated filesystem blocks, the full project, or global storage.
Both are bounded read-time snapshots, not an atomic snapshot of the world.
Missing ledgers or storage inventories remain explicit missing evidence.

Scientific workload provenance is not established by archive consistency.
Consequently this public bridge currently returns an inconclusive decision
unless an observed mismatch requires stopping to repair the implementation.
Known resource and quality failures remain in the report even when another
missing premise prevents a complete gate decision. No assertion-valued JSON
supplement can remove the scientific-provenance blocker or authorize research.

The read-only CLI loads actual inventories and archives, and atomically writes
a report outside the input archives:

```bash
python scripts/evaluate_feasibility.py \
  --clean-inventory /path/to/combined-inventory.json \
  --clean-output /path/to/campaign \
  --diagnostic-inventory /path/to/combined-inventory.json \
  --diagnostic-output /path/to/campaign \
  --output /path/to/feasibility-decision.json
```

The diagnostic pair is optional; omitting it records missing coverage evidence.
The CLI executes no model, accepts no asserted-evidence file, rejects report
paths inside immutable archives (including `..` aliases), and refuses to replace
a different existing report. Exit zero means that a report was written, not
that feasibility passed. The real combined-inventory integration test is a tiny
software correctness fixture and supplies no scientific performance evidence.

## Conditional supplied-evidence interfaces

`evaluate_verified_feasibility(policy, evidence, measured)` is a narrower typed
cross-check adapter for callers that already have conditional evidence.
It requires a `VerifiedMeasuredEvidence` returned by
`load_measured_sequence_evidence(inventory_path, output_root)`. It checks the
complete root/schedule binding, original preparation, clean per-role timings,
stage maps, state artifacts, retained membership, exact lifetime sums, and
measured workers' configured and observed resources against that loader output.
Altered convenience times or resource summaries cannot replace verified values.
The adapter does no further I/O; it consumes the immutable verified snapshot.

Its result distinguishes `measured_sequence_archive_verified=true` from
`supplement_archive_verification_performed=false`. The latter flag is deliberate:
the adapter does not yet verify coverage or quality archive contents, actual
target-graph/group-assignment provenance, all-worker/phase-ledger completeness,
or scientific source provenance. Those supplements remain explicit external
premises, even when their asserted facts satisfy the pure policy checker.
The measured loader's artifact maximum covers the transaction tree; observer
archives and other separately required artifacts need their own accounting.
This adapter therefore never upgrades conditional policy satisfaction into
observed empirical attainment.

The software fixtures deliberately use artificial hashes and tiny integer cost
values to attack the checker. They test decision logic only. Their conditional
passes cannot count as empirical attainment, calibration roots, or speedups.

## Frozen policy and supported interface

The evaluator supports exactly the canonical policy payload whose SHA256 is:

`92af4f2ae5d9b01b51f469830a35ccb4b2521f6351ad286cbdc0e40ce64ac5a2`

This is `digest(canonical_json(policy))`, not the hash of indented file bytes.
Changing a threshold, permitted mismatch, or resource cap requires a prospective
policy revision and an explicit evaluator update. Passing a modified policy to
this version yields an inconclusive invalid-evidence result.

The input schema is `calibration-feasibility-evidence-v1`; the output schema is
`calibration-feasibility-decision-v1`. There are no optional successful defaults.
Required evidence can be explicitly unavailable where the schema permits null.
Missing fields, unexpected fields, duplicate identifiers, invalid hashes,
Boolean counts, negative counts, oversized integers, and contradictory bindings
cannot produce a positive decision.

```python
from src.feasibility_decision import evaluate_feasibility

decision = evaluate_feasibility(policy_payload, assembled_evidence)
# This computes a conditional policy result. It does not validate arbitrary
# supplied JSON against measurement files or authorize a research run.
```

## Top-level evidence schema

The source validators define the exact accepted fields. The following tables
give their meaning; this document is not permission to infer missing values.

| Field | Required meaning |
| --- | --- |
| `schema`, `policy_payload_sha256` | Exact supported schema and frozen policy binding |
| `target_manifest_sha256` | Common complete `V_cert` target, including original normalization |
| `configuration_sha256` | Frozen algorithm configuration, excluding only the explicitly separate clean/diagnostic execution profile |
| `protocol_sha256`, `inventory_sha256` | Actual frozen protocol and complete planned sequence inventory |
| `source_sha256` | Nonempty mapping from bounded source names to their hashes |
| `evidence_kind` | `research` or `software_test`; fixtures never become research evidence |
| `provenance` | Producer hash, required artifact bindings, archive-verification disposition, and scientific-provenance disposition |
| `target` | Complete topological stage order and direct-parent graph |
| `measurement_contract` | Full boundary, all required cost categories, symmetric external-oracle accounting, and disjoint method costs |
| `roots` | Every planned root, including failed or incomplete evidence |
| `resources` | Complete planned worker inventory, observations, configured limits, and phase charge |

The six required provenance artifact roles are `measured_lifetime`, `coverage`,
`quality`, `resource_ledger`, `workload_provenance`, and `exactness`.
Additional uniquely named artifacts are allowed. Each role names an actual
artifact hash once it is assembled by an external verifier.
Research provenance must explicitly attest a verified real workload; the pure
evaluator still does not establish that attestation's truth.

The target graph must contain every declared stage exactly once. Direct parents
must precede their child. The evaluator computes transitive ancestor closures;
a producer cannot substitute an arbitrary list of supposedly affected stages.
The independently verified target must establish that this graph is the actual
quantization dependency graph.

## Root, schedule, and exactness evidence

The policy requires two roots, eight original records per root, 32 tokens per
record, and exactly three ordered requests per root. A root contains:

| Field | Meaning |
| --- | --- |
| `root_id`, `records` | Unique root ID and complete `{record_id,tokens}` list |
| `record_groups` | For every stage, the original assignment of every record to its fixed group |
| `initial_stage_codes` | Complete original model's per-stage code hashes |
| `preparation` | One indexed preparation shared by repair and indexed fresh, plus separate model-only preparation |
| `planned_request_ids` | The exact frozen order of three unique requests |
| `requests` | One entry for every planned request in that order |

Every request supplies its ID, newly deleted IDs, model comparisons, canonical
state comparisons, coverage, quality, and complete timing terms. Deletion IDs
must belong to the current retained set. Previously removed IDs cannot be
deleted again. Empty deletions are allowed. Membership is updated sequentially
from the original root; every timing and diagnostic binding must match it.

`models` contains full per-stage code-hash maps for `repair`, `indexed_fresh`,
`direct_fresh`, and `model_only_fresh` under the same retained set. The maps
must have exactly the complete target stages. `states` contains same-family
canonical-state hashes for repair, indexed fresh, and direct fresh.
The original and predecessor models may differ from the current model.
They are never included in a false same-model equality requirement.

A known stage or state mismatch takes priority over missing numerical evidence.
It yields `stop_and_repair_implementation`. Missing models, stages, or state
artifacts remain inconclusive. Digest equality relies on verified artifact
construction and the stated collision assumption; unsupported state families
cannot be made comparable by merely giving them the same label.

## Changed-ancestor feature avoidance

For a request, the evaluator derives the set of actually changed stages from
the complete predecessor and current stage-code maps. It then considers every
occupied retained group at every stage. A group enters the denominator exactly
when at least one of its stage's transitive ancestors changed.

This construction excludes empty retained groups and unchanged-ancestor groups.
Changing a stage's own code does not make that stage's input depend on itself.
The predecessor of request two is request one's committed repair model, not
the original model. The predecessor graph and record-group assignments remain
fixed throughout the sequence.

For each occupied retained group, `coverage.groups` records its `stage_id`,
`group_id`, and actual `retained_target_feature_evaluations`. The numerator
counts eligible groups whose evaluation count is exactly zero. Source reads,
resident payloads, cache hits, certificate counts, and unchanged-ancestor
acceptance are not substitutes for this count. Repeated evaluations remain
positive and cannot count as avoidance.

The group inventory must be complete. `complete=true`, `omitted_events=0`,
`capped=false`, and `counter_saturated=false` are all required. The evaluator
rejects duplicate, unexpected, and empty groups, and refuses Boolean or negative
evaluation counts. Missing group rows or incomplete predecessor codes make
coverage inconclusive. It never divides a favorable observed subset by itself.

Coverage comes from a separately bound diagnostic replicate, since clean timing
disables the detailed funnel. `coverage.replicate` binds:

- Diagnostic receipt and worker receipt/ID.
- Target, algorithm configuration, and complete source-map digest.
- Root, request, retained membership, and predecessor stage-map digest.
- Actual diagnostic stage-code map and canonical-state hash.
- `execution_mode="diagnostic"`.

The evaluator checks parity with the clean request's complete stage maps and
state. A missing or mismatched replicate leaves coverage inconclusive. This
check does not create otherwise absent per-group event coverage: the producer
must verify the diagnostic archive and all its omission and saturation flags.
The bounded v8 funnel can remain insufficient for this purpose. Its success
return code does not establish a complete denominator or numerator.

Counts accumulate over all three requests on each root. The exact requirement
is `4 * numerator >= denominator`. A zero denominator is inconclusive because
the changed-ancestor mechanism was not demonstrated. Every root must meet the
threshold; a strong root cannot compensate for another root's failure.

## Quality evidence and numerical threshold

Each request has a `quality.binding` that identifies the separate quality
receipt and worker, target, root, request, and retained model's full stage-map
digest. The evaluator checks this model against model-only fresh.
Quality and coverage may share one explicitly recorded diagnostic worker.
They cannot share a worker with a clean measured transaction.

`quality.base` and `quality.retained_fresh` each provide `heldout_sha256`,
`evaluator_sha256`, `scored_tokens`, and finite nonnegative `nll_sum`.
Both samples must use identical heldout tokens, evaluator, and positive token
count. This is checked separately for every root and request. Missing values,
nonfinite scores, zero tokens, or mismatched counts remain inconclusive.

The observed finite scores are converted exactly to rational values. Let

\[
\Delta=\frac{L_R}{n}-\frac{L_B}{n},\qquad x=\frac1{11}.
\]

The threshold uses the exact series

\[
\ell_m=2\sum_{k=0}^{m-1}\frac{x^{2k+1}}{2k+1},\qquad
\ell_m<\log(6/5)\le
\ell_m+\frac{2x^{2m+1}}{(2m+1)(1-x^2)}=u_m.
\]

For `m=32`, `Delta <= ell_m` passes and `Delta > u_m` fails.
A value in the remaining enclosure is inconclusive. The positive-series tail
bound follows by replacing every remaining denominator with `2m+1` and summing
the geometric series. No host `log` rounding assumption enters the comparison.

This exact comparison concerns the saved finite NLL observations only. It does
not certify the underlying loss computation, establish native inference
equivalence, or prove population language quality. Task metrics and real-model
validation remain separate requirements.

## Complete timing and resource evidence

Every preparation and request timing term binds:

| Fields | Required interpretation |
| --- | --- |
| `status`, `wall_ns`, `receipt_sha256` | Complete original observation with positive integer nanoseconds |
| `output_contract` | `canonical_state` for repair/indexed fresh; `model_only` for ordinary fresh |
| `boundary` | Exact complete external-observer boundary from `TRANSACTION_TIMING.md` |
| `cache_mode` | `fresh_transaction_os_cache_uncontrolled` |
| `execution_mode`, `instrumentation_disabled`, `profiler_active` | Clean profile, disabled supported diagnostic instruments, no profiler |
| `new_latency_observation`, `source_inputs_unchanged` | Original fresh observation and verified input/source stability |
| `worker_id`, `worker_receipt_sha256` | Actual measured child worker and its resource receipt |
| `target_manifest_sha256`, `configuration_sha256`, `retained_ids_sha256` | Matched target, algorithm, and canonical sorted retained-ID binding |

The instrumentation Boolean concerns the supported Python/profile/trace and
allocation instruments checked by the measured loader. External native
profiling remains unobserved; this is not a proof of universal instrumentation
absence. An archived receipt may be loaded to recover its original observation;
the same observation must never be presented as another repetition or role.

Repair and indexed fresh receive the same original prepared index and its cost.
Their preparation evidence must be identical; the cost is counted once within
each system's lifetime. The ordinary comparator separately constructs the
original model with no deletion index. Its preparation must bind all original
records and have a positive complete clock. Zero, null, already-deleted, or
full-state preparation cannot stand in for this model-only preparation.

All three requested repair/indexed/model-only roles have separate complete
timing terms. No receipt or worker can occupy two distinct terms. The full-state
oracle remains external research verification; its cost is tracked separately
and symmetrically. Whole-comparison clocks and nested service counters cannot
be substituted for these complete method clocks.

The resource inventory contains every planned worker, including setup, clean
methods, diagnostics, quality, and external research-oracle work. Every timing
and diagnostic worker must occur in that inventory with its exact receipt.
Additional declared workers are allowed; unplanned or duplicate workers and
reused resource receipts are rejected. A worker's observed elapsed time cannot
exceed its complete enclosing transaction time.

Each worker records configured wall, CPU, address-space, and file-size limits,
plus observed wall/CPU nanoseconds, peak RSS, and maximum artifact bytes.
Configured limits and observations are checked against the frozen limits;
finishing quickly under a retrospectively enlarged allowance does not pass.
An absent observation or unresolved attempt is inconclusive, not zero usage.
Phase charge must cover observed worker CPU and remain within three worker CPU
hours, including each worker's upward whole-second settlement with a one-second
minimum. The phase ledger and its completeness must be independently verified.

Every original preparation must finish within 900 seconds. Each compared
system's complete three-request lifetime must remain within 3,600 seconds.
The evaluator conservatively applies this undeclared-method resource ceiling
to all three compared lifetimes; it does not hide a failed baseline.
This does not change the primary strict-gain comparison against model-only
fresh. Admission remains scoped to one protocol ledger, not controller CPU,
separate protocols, arbitrary descendants, or global physical use.

## Decision order and equal-information comparison

The evaluator follows the frozen policy's priority:

1. Known exactness mismatch: stop and repair the implementation.
2. Missing required evidence: leave the gate open.
3. Resource failure: redesign within the remaining allowance or narrow scope.
4. Quality failure: revise configuration prospectively or narrow scope.
5. Zero changed-ancestor denominator: mechanism not demonstrated.
6. Insufficient coverage: redesign the certificate or narrow scope.
7. No strict lifetime gain on any root: redesign cost or narrow scope.
8. All conditions satisfied: conditional promotion to development only.

Structural contradictions produce an inconclusive invalid-evidence decision.
They never permit performance interpretation. A malformed record does not
authenticate a reported mismatch either; the artifact verifier must resolve it.

The result separately reports each root's `indexed_fresh - repair` lifetime
cost. A tie or loss blocks a deletion-exclusive solver claim. Even a positive
complete-service difference does not isolate solver work: index maintenance,
validation, or interface costs may explain it. The evaluator therefore never
sets `deletion_exclusive_solver_claim_supported=true`.

## Exact lifetime break-even identity

Fix a prospective horizon `H`, complete output contracts, and a common measured
boundary. Let `P_R` include original model plus index preparation, and let `P_F`
include original model-only construction. For request `h`, let `R_h` include
repair and required live-state maintenance, and let `F_h` include retained
model-only construction. Required online work belongs in these terms; shared
external research validation has separate symmetric accounting.

Define preparation debt and request savings:

\[
D_0=P_R-P_F,\qquad s_h=F_h-R_h,\qquad
D_k=D_0-\sum_{h=1}^k s_h.
\]

Then, exactly,

\[
T_R(H)-T_F(H)=D_H.
\]

Strict lifetime improvement holds if and only if
`sum_h s_h > P_R - P_F`. Equality is a failure of the frozen strict-gain gate.
This identity sharpens vague amortization statements because both systems pay
for the original output they actually require. Comparing repair with repeated
full-state oracle construction cannot establish this condition.

For a required factor `q > 1`, the exact stronger condition is

\[
T_F(H)>qT_R(H)
\iff
\sum_{h=1}^H(F_h-qR_h)>qP_R-P_F.
\]

If all request costs are nonnegative, a necessary condition for strict gain is
`P_R - P_F < sum_h F_h`. Even free repair requests cannot pay a preparation
debt at least as large as every avoided fresh request combined.

Suppose every request saving is bounded above by `u>0` and the preparation debt
is nonnegative. A necessary horizon is
`H >= floor((P_R-P_F)/u)+1`. If instead every saving is bounded below by `l>0`,
the same expression with `l` gives a sufficient horizon. These statements need
justified per-request bounds under the actual sequential prefixes. An observed
average, a source-cache hit, or certificate coverage does not supply such bounds.

`lifetime_break_even` implements the exact prefix arithmetic. A first crossing
of `D_k<0` need not persist: later request savings can be negative. Persistence
requires a separate nonnegative-future-savings premise. Reporting only the best
crossing and dropping later costly deletions would change the frozen horizon.

## Conditional full-cost sufficient bound

For a specified request decomposition, suppose

\[
F_h^{\rm fresh}=A_h+B_h,\qquad
R_h\le s_h A_h+U_h+B_h,
\]

where `A_h` is genuinely avoidable fresh computation, `B_h` is the comparable
remainder, and `U_h` includes every repair excess: proof attempts, repeated
factors, deleted evidence, state maintenance, differing output, and extra
verification. Merely assigning costs to `B_h` does not prove they are shared.

For `A=sum_h A_h>0`, define

\[
\bar s=\frac{\sum_hs_hA_h}{A},\qquad
\bar u=\frac{P_R-P_F+\sum_hU_h}{A},\qquad
\gamma=\frac{P_F+\sum_hB_h}{A}.
\]

Then `bar_s + bar_u < 1` is sufficient for a strict lifetime gain. When the
upper bound on repair lifetime is positive,

\[
\frac{T_F}{T_R}\ge
\frac{1+\gamma}{\bar s+\bar u+\gamma}>1.
\]

This is the preparation-inclusive version of the conditional cost theorem.
It requires cost-weighted avoided computation, not the fraction of accepted
groups or documents. A large number of cheap avoided groups can coexist with
an expensive replayed group and no lifetime gain. Equal-information fresh
receives the same summaries and solver; these inequalities establish no
deletion-exclusive solver advantage.

## A sound prospective cost screen

After `k` requests, suppose independently justified bounds satisfy
`l_h <= F_h - R_h <= u_h` for every remaining request under every relevant
future prefix. Then:

\[
\sum_{h>k}u_h\le D_k
\implies\text{strict horizon gain is impossible},
\]

\[
\sum_{h>k}l_h>D_k
\implies\text{strict horizon gain, conditional on completion and the bounds}.
\]

These implications follow by substituting the bounds into `D_H`.
`remaining_cost_decision` implements this interval screen. Unknown future
bounds yield an inconclusive result. Worker CPU limits are not automatically
upper bounds on complete external transaction wall time. Diagnostic timings
and previously observed means are not deterministic future bounds either.

A futility stop can save a predeclared research allowance, but it leaves later
planned requests unstarted and visible. It cannot become a feasibility pass:
the policy requires complete exact artifacts, quality, resources, and coverage
for every planned request. The conditional lower-bound result does not dispense
with those requirements. An adapted stop rule also cannot be retroactively
treated as a fixed confirmatory sample.

## Reliability remains a separate empirical statement

Let `E` be the joint root-level event that all `H=3` requests complete exactly
within budget and the complete model-only comparison exceeds the chosen speed
factor. Deterministic arithmetic establishes the event only for its supplied
observations. A population claim requires a justified sampling law and a
probability for that event.

Even under independent identical root-level Bernoulli trials, two successful
roots provide little reliability evidence. If all `n` roots succeed, inversion
of `Pr_p(all n succeed)=p^n` gives the one-sided level `1-alpha` lower endpoint
`alpha^(1/n)`. For `n=2` and `alpha=.05`, this is approximately `.224`.
Requests and timing repeats inside those two roots do not increase `n`.
This illustrative endpoint concerns a success probability, not the separate
confidence interval for a latency ratio.

The frozen feasibility policy promotes engineering development, not
confirmation. It does not justify the later root count, solve clustering,
replace failure-aware analysis, or establish the prescribed lower speed bound.
The accounting lemmas here are elementary consequences of complete costs and
explicit assumptions; they are not independent novelty or priority claims.

## Remaining evidence obligations

The archive bridge can derive coverage when the bounded funnel explicitly
reports complete relevant counters and the full replay audit agrees. It cannot
recover omitted counters or hidden provider causes, prove actual source
independence, or turn clean clocks into useful real-model results. C05 and D05
remain partial.
Measured sequence integration and artifact-aware analysis must retain every
planned failure, fresh-observation identity, preparation term, and predecessor.
Actual feasibility, quality, useful feature avoidance, preparation amortization,
memory fit, and reliable speedup remain unmeasured.
