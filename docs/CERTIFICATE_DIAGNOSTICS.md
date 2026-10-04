# Bounded numerical certificate diagnostics

Revision 8 adds an external diagnostic funnel to the aggregate response service.
It does not change any numerical decision, proposal, proof condition, or replay selection.
Research experiments remain paused.

The existing collector now exports `certificate_funnel` under schema `certificate-funnel-v1`.
The enclosing telemetry schema remains `service-telemetry-v1`.
The additional field is diagnostic metadata, not canonical live state.
Instrumented and uninstrumented calls produce identical canonical bytes under the same source-bound service.
Source changes still change applicable provenance hashes.

## Collection interface

```python
from src.service_telemetry import DiagnosticLimits, ServiceTelemetry

collector = ServiceTelemetry(diagnostic_limits=DiagnosticLimits(
    max_stage_records=256,
    max_event_kinds_per_stage=32,
    max_cell_samples=4,
    max_integer_bits=256,
    max_text_length=192,
))
result = service.repair(old_state, deleted_records, retained_source,
                        telemetry=collector)
diagnostics = collector.payload()["certificate_funnel"]
```

Read the payload only after the operation finishes or raises.
Repeated collector use assigns a new operation index to each service operation.
This separates index preparation from subsequent indexed construction.
Each stage record also includes the stage identity and its digest.

No record payload, token sequence, source identifier, feature matrix, or Gram matrix enters this funnel.
Group identifiers and aggregate counts can appear.
Sampled decision inputs and margins are derived numerical statistics.
They remain part of the external research archive.
This archive has no physical-erasure guarantee.
Provider reason strings remain trusted diagnostic text and are truncated before storage.
The module does not inspect their semantic content for private information.

## Observation structure

Each operation reports its name, sequence index, completion status, failure type, and complete-model production flag.
Both state-bearing results and the model-only fresh result can report complete-model production.
A successful index update does not claim complete-model production.
A failed operation cannot claim a produced complete model.
The flag concerns the returned service result, not the caller's later durable transaction.

Each stage reports `observed`, `running`, `complete`, or `failed`.
A failed operation marks its running stages as failed.
Completed earlier stages can remain complete even when a later stage aborts.
Therefore stage completion alone never establishes complete-model success.
A stage seen only during intrinsic extraction can remain `observed`.

Each event kind retains its count, first observation, and last observation.
Intermediate observations are not retained as full records.
Separate disposition counters preserve observed status, proposal, role, acceptance, and contract-availability counts.
These counts cover recorded stages and event kinds only.
Rejected stage or event-kind observations contribute omission counts without per-disposition detail.
Selected totals preserve record counts, unavailable descriptors, checked cells, failed cells, and completed replay evaluations.
These totals include repeated attempts where the same event occurs repeatedly.
They do not identify independent statistical samples.

## Recorded funnel

| Step | Observations | Interpretation |
| --- | --- | --- |
| Intrinsic extraction | Available or unavailable descriptor, extraction role, term counts, constant error moment | Missing internal provider causes remain explicitly unavailable |
| Retained evidence | Group record count, unavailable record count, contract presence | Available descriptors do not imply accepted transport |
| Identity control | Missing reference, unequal base ancestors, or equal base ancestors | This records the response family's base-reference control |
| Domain query | Provider unknown, explicit coefficient-radius failure, or accepted provider query | Generic unknown evidence is not relabeled as proved domain failure |
| Finite Gram bound | Proposal type, signed raw error magnitudes, available component bounds | Raw units remain separate from original normalization |
| Relative enclosure | Original normalization, ridge, lower and upper scales, remaining groups | Nonpositive lower scale skips the spectral certificate |
| Spectral decisions | Accepted status, checked and failed counts, bounded cell samples | Samples prefer the first failed cells |
| Interval decisions | Accepted status, interval margins, checked and failed counts | Interval abort differs from an ordinary rejected certificate |
| Replay | Group choice reason, started groups, completed groups, feature evaluations | Counts reflect actual evaluator calls, not only source reads |
| Stage output | Selected route, certificate attempts, replayed and unknown group counts | Every stage must finish before complete-model production |

Query type, binding, coefficient-count, and proposal-PSD failures have explicit invalid-evidence reasons.
Evaluator and extraction exceptions record their exception type at the observed stage.
Final operation failure remains visible even if a stage has no completed numerical trace.

## Exact values and decision margins

Ordinary exact values use

```json
{"encoding":"rational","numerator":1,"denominator":7}
```

Integers within the configured bit cap remain JSON integers.
Rationals above that cap use only their sign and numerator and denominator bit lengths.
Large integers similarly use their sign and bit length.
The encoder never converts an oversized numerator into a decimal string.
Magnitude summaries cannot reconstruct the original value.
They must not be used as numerical certificates or exact plotting coordinates.

Spectral samples include the candidate conditional input, squared displacement radius, finite cell boundaries, and signed boundary margins.
A missing endpoint has an explicit unbounded flag.
Positive-radius spectral checks retain the existing conservative strict containment rule.
Zero displacement retains exact lower-code ties.
No sample changes that predicate.

Interval samples include the conditional input interval and its lower and upper cell margins.
The original cells remain `(lower, upper]`, with unbounded saturation endpoints.
A zero upper margin can therefore be valid for this verifier.
A zero lower margin does not establish lower-bound containment.
Rejected cells remain abstentions, not proof that the true quantized code changed.

## Component availability

The quadratic tier exposes its complete affine-response energy and combined squared feature-error bound.
The fixed-reference control exposes residual error, omitted tangent energy, combined feature error, and anchor energy.
The compact tier exposes its omitted tangent trace and response Gram-error term.
Its existing bound object does not expose a separate squared feature-error value.
The diagnostic records that field as unavailable rather than recomputing hidden arithmetic.

The constant intrinsic error moment combines provider-specific finite and approximation terms.
The automatic affine provider does not separately expose finite error and center interval error through this interface.
The box provider also combines interval half-width and finite error.
Those subcomponents remain inseparable in the recorded moment.
Provider-internal Hessian entries, failed interval denominators, and exact chart-fit residuals are not exposed.
A provider's generic unavailable result remains labeled `provider_returned_unavailable`.
These limitations constrain root-cause analysis but do not weaken accepted numerical guarantees.

## Control semantics

`full_replay` explicitly bypasses domain checks, bound queries, and decision certificates.
It records feature and group replay counts without fabricated acceptance statistics.
Direct fresh similarly marks proof queries as bypassed.
Its extraction events describe state preparation, not successful online certification.

`fixed_reference` reports its actual triangle-bound proposal.
`identity_only` reports whether the constructor's base ancestors agree.
A failed identity gate does not claim a tested affine chart or parameter box.
The original-model cache belongs to a separate service family.
This response funnel does not fabricate response certificates for that family.
Its existing cache ledger and audit remain the source of its mechanism diagnostics.
The separate model-only fresh baseline currently reports operation completion without this response-specific stage funnel.

Empty retained sets can complete without feature evaluations or decision-certificate attempts.
Complete-model production still requires successful fixed-target quantization and canonical state construction.
A failed required finite evaluator aborts without an approximate committed result.

## Storage limits and truncation

The default limits retain at most 256 operation-stage records and 32 event kinds per stage.
Each kind stores only its first and last observation.
At most four decision cells appear in each sampled observation.
Each value object retains at most 24 fields and five nested container levels.
Text retains a bounded prefix and a digest when truncated.
Exact numerical values retain at most 256 bits per numerator or denominator.
Supported cell, integer, and nesting caps also have hard upper limits.

Event, reason, timing, disposition, and selected-total dictionaries have configured key caps.
Each may add one `__other__` overflow bucket beyond its cap.
Timing categories reserve their slots before nested spans begin.
This prevents nesting from bypassing the category limit.
Stored observation and event counters saturate at `2**64-1` where applicable.
A separate saturation count records that loss of exact count precision.

Dropped stage observations, dropped event kinds, truncated fields, omitted samples, summarized numbers, and encoding failures have explicit counters.
Once a stage or event-kind cap prevents storage, its lazy numerical builder does not execute.
Therefore discarded records cannot trigger an unnecessary full cell-summary scan.
A caller can lower the limits for a stricter diagnostic budget.
Increasing limits requires corresponding memory and output accounting.
These bounds constrain retained diagnostic cardinality and numerical payload sizes.
They do not make total diagnostic runtime independent of model dimensions or attempt counts.

Payload export returns detached objects.
Editing an exported payload cannot alter later observations or the canonical model.
Counter saturation and omitted observations must remain visible in any analysis.
A truncated funnel cannot justify a claim of exhaustive untruncated detail.

## Cost and failure accounting

The `certificate_diagnostics` timing category measures numerical record construction and encoding inside each service operation.
Nested timing remains exclusive.
The service ledger counts attempted, recorded, and omitted diagnostic observations.
The collector separately counts encoding failures and truncation.
Cell summaries scan existing certificate checks to count failures.
They perform additional exact margin arithmetic only for the bounded selected samples.
That work is diagnostic overhead and remains charged.

Summary-builder or encoder exceptions produce diagnostic-failure records.
They do not turn valid target arithmetic into an artificial model failure.
The original numerical exception still propagates when required proof or evaluator code fails.
Resource exhaustion can prevent later output or durable logging, as with the existing runner.

Export copying and final diagnostic JSON serialization occur at the caller's chosen boundary.
They are not included automatically in the named in-service diagnostic span.
The experiment's complete-cost contract must account for that output work separately.
This addition therefore does not close every remaining end-to-end timing requirement.

## Correctness validation

The dedicated tests verify canonical equality with telemetry enabled and disabled.
They distinguish unavailable descriptors, provider-unknown queries, and explicit radius rejection.
They check exact bound units, original normalization, cell margins, and interval acceptance and rejection.
They verify honest replay controls, actual feature counts, complete deletion, and evaluator-abort status.
They exercise stage and event caps, oversized exact numbers, disposition counts, and detached payloads.
Independent tests cover nested timing caps and diagnostic-builder failure isolation.

These are software correctness fixtures.
They establish no real-model coverage, latency, quality, or statistical reliability.
