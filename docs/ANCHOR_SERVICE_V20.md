# Complete source-local anchor state and exact service

This document specifies an alternative state family.
It does not establish practical repair speed.
Its complete model target remains the fixed dyadic sequential quantizer.

## 1. State contract

For each retained record, prepare its nearest-grid anchor independently.
The anchor uses fixed base weights, fixed grids, and that record's tokens.
It does not use calibration statistics or other records.
The complete state contains these anchor leaves and the exact output model.

Write the leaf function as $L_T(r)$.
Here $T$ binds the original normalization, grids, decoder, and model weights.
Let $M_T(R)$ denote the complete retained-corpus quantization output.
The canonical state is

\[
 S_T(R)=\operatorname{Encode}\left(
 T,\operatorname{Provider},M_T(R),
 (L_T(r))_{r\in\operatorname{Sort}(R)}\right).
\]

Its family identifier is `source_local_anchor_v1`.
It differs from `factor_identity_v1`.
Anchor state does not store current-prefix factors.
It also does not claim equality with current-prefix factor-state bytes.

The immutable leaf stores tokens, scalar summaries, fixed factors, and affine summaries.
The leaf binds the target, decoder, provider source, and nearest-grid anchor model.
The outer state binds the same values.
The output model reuses the existing canonical packed-code format.

Source removal selects retained leaves.
It never copies deleted leaves into the returned state.
The service requires exact retained membership and unchanged tokens.
Trusted previous state supplies the leaf provenance.
Hashes detect corruption but cannot authenticate a hostile replacement.

## 2. Exactness implication

Assume the provider's finite transformer enclosure theorem.
Assume trusted leaf preparation and the declared numerical runtime.
Assume the direct dyadic box certificate and exact point solver succeed.
Then the service returns $M_T(R)$.

Proof proceeds by stage induction.
The empty prefix agrees with the target.
At stage $i$, preceding output codes therefore equal the exact target prefix.
The provider encloses each retained feature matrix under that prefix.
An accepted box certificate gives one code matrix throughout the enclosed box.
Those codes equal the target codes at the actual retained features.
A singleton box uses the shared exact point solver directly.
An unresolved box triggers exact retained replay and the same point solver.
Each branch therefore preserves the induction premise.

The exact replay uses one generator for each retained record.
Each generator installs the already verified preceding codes.
Later replay can traverse stages that earlier box certificates accepted.
The service counts those traversed stages as source work.

Suppose two request histories end with identical retained records.
Each history returns the same exact model by the induction result.
Each retained leaf equals the same source-local preparation function.
Canonical sorting and encoding therefore give identical complete state bytes.
This includes sequential deletion, combined deletion, no-op requests, and empty retention.

The claim is conditional on successful bounded exact solving.
Exhausted exact budgets abort without committing a state.
Invalid bindings and contradictory fallback values also abort.
No completed output depends on an unproved feature box.

## 3. Bounded policy

`AnchorService` supports the following deterministic limits:

| Option | Default | Meaning |
|---|---:|---|
| `max_box_stage_attempts` | 4 | Maximum stages with a box attempt |
| `max_box_tokens` | 64 | Maximum total retained tokens per attempted stage |
| `max_box_decisions` | 65536 | Maximum quantization coordinates per attempted stage |

These limits bound the admitted box problem dimensions.
They are not wall-time guarantees.
Provider preparation and parsing also enforce their own finite limits.
Rejected or skipped boxes use exact replay.
The service does not run an unbounded refinement search.

For numerical failures, the service records the exception and uses exact replay.
For binding failures, the service aborts.
When replay follows a supplied box, it checks exact feature containment.
This check can expose a bug in a rejected box.
It does not establish validity for accepted boxes.
The provider proof supplies that validity.

## 4. Comparison methods

| Method | Anchor preparation | Persistent output |
|---|---|---|
| `direct_fresh` | Prepares every retained leaf | Complete anchor state |
| `repair` | Reuses retained trusted leaves | Complete anchor state |
| `indexed_fresh` | Reuses retained trusted leaves | Complete anchor state |
| `model_only_fresh` | None | Exact model only |

`repair` and `indexed_fresh` currently use identical numerical paths.
Set `use_bounds=False` for a shared exact-replay control.
Both native and reference point solvers are supported.
All methods use the same exact feature traversal.

Prior model proposals are disabled by default.
The revision 17 pilot found that these proposals added cost.
Set `use_candidates=True` to test them explicitly.
The model-only control then accepts the same complete prior model.
Its seed must be a factor-free `CompactState`.
Candidate decoding time remains charged.
The model-only control never reads anchors or prepares an anchor context.

## 5. Accounting

The service clock includes membership checks, context preparation, and leaf preparation.
It includes all bound calls, rejected certificates, exact replay, and code packing.
It also includes complete state construction.
External checkpoint loading and serialized output remain outside this clock.
Experiment workers must add those external costs separately.

Each bound call returns its work counters.
The service stores per-record counters and their stage sums.
The context records initial matrix processing.
Anchor preparation records complete stage-record pairs and stored values.
Exact replay records every traversed stage-record pair.

An accepted early box does not imply saved traversal.
The final avoidance count subtracts every pair that later replay visited.
The changed-prefix avoidance count also requires an actual nearest-anchor prefix change.
No timing result follows from either count alone.

## 6. Canonical parser

The parser accepts immutable bytes and explicit finite limits.
It limits the outer file, JSON header, record count, and each leaf.
It also limits model elements, leaf nodes, leaf values, and leaf tokens.
It rejects inconsistent hashes, metadata, bindings, ordering, and trailing payload.
It rejects noncanonical encodings by canonical reserialization.
An optional trusted whole-state digest binds the complete file.

Signed-zero factor bytes require no equality claim here.
The persistent factors belong to fixed source-local anchor execution.
The model format canonicalizes grid zero.
Current-prefix singleton boxes prove numeric features for model solving only.

## 7. Verification scope

`tests/test_anchor_service_v20.py` compares complete model outputs with the existing reference service.
It compares complete state bytes across fresh, combined, and sequential removal.
It also checks no-op requests, empty retention, warm controls, and parser corruption.
It checks budget fallback, accounting, contradiction detection, and two-block dependencies.

These checks use small software fixtures.
They are not empirical datasets or speed evidence.
Useful real-data box acceptance remains a separate requirement.
