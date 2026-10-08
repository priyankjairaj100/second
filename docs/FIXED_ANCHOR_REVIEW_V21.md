# Revision 21 fixed-feature target review

Status: review completed after the target-isolation fix.
This review uses the same project team.
It is not external verification or proof-assistant verification.
No empirical worker belongs to this review.

## Target distinction

The new target changes the feature rule.
Each stage calibrates against its fixed nearest-anchor features.
Earlier calibrated output codes do not affect those features.
The original sequential target uses earlier calibrated output codes in later feature extraction.
Success for the new target therefore cannot establish success for the original target.

The new constructor binds the original target recipe, decoder, provider, and changed feature rule.
Its digest differs from the original target digest.
It retains the original normalization, grids, and finite feature schedule.
Its output model can differ from the original retained-prefix model.
That difference requires separate model-quality evidence.

## Service review

The model-only branch advances the finite traversal using fixed anchor matrices.
It never sends calibrated output matrices into that traversal.
The stateful branch reads the same fixed factors from trusted prepared leaves.
Both branches apply the same selected exact point solver to those factors.
The resulting code equality follows separately at each stage.
It does not require a sequential dependency induction over calibrated outputs.

Each retained leaf depends only on its record and frozen target configuration.
Deletion restricts the leaf set.
Fresh retained construction produces the same leaves.
Canonical record order and identical exact codes therefore give identical complete state bytes.
The tests cover fresh construction, sequential deletion, combined deletion, no-op requests, and empty retention.

Repair and indexed reconstruction receive the same retained leaves.
They use identical numerical paths.
An operation-count tie between them is expected.
It does not establish a new deletion advantage over that strongest indexed comparator.

## Prepared-route and cost limits

`run_prepared` requires explicit external preparation provenance.
The service records that receipt without verifying its claimed timer or artifact hash.
Its diagnostics state `preparation_receipt_verified_by_service=False`.
The experiment controller must verify the earlier worker and artifact separately.
The service's clock excludes that external preparation.
The external preparation field must remain separate from the measured clock.

Fresh stateful preparation performs neural work.
Its total stage-record work includes both preparation and later traversal counters.
The appropriate sum is

\[
N_{\mathrm{neural}}=
N_{\mathrm{anchor\ preparation}}+N_{\mathrm{traversal}}.
\]

A zero traversal counter does not establish zero total neural work for fresh construction.
State parsing, source checks, context construction, solver work, and output serialization also require explicit charges.
A prepared-model quality screen is not a repair timing experiment.

## Target-isolation issue

The initial target exposed the original stages' sequential dependency metadata.
Consequently, the generic sequential service accepted that target.
It could return sequential codes under the new fixed-feature target digest.
The new target now declares no dependencies on calibrated outputs.
Its original target object remains available separately for nearest-anchor construction.
The final regression verifies that both sequential services reject the fixed-feature target.
The source change occurred before admission of the quality worker.

The fixed-state format wraps an inner anchor container for structural serialization.
The outer fixed-feature header supplies the model semantics.
The inner container is private encoding infrastructure.
It must not appear as a separately valid sequential-model result.

## Scientific boundary

This construction makes retained feature reuse exact by changing the calibration target.
That is a valid research redesign when disclosed.
It does not solve the original changed-prefix transport problem.
Fixed-feature calibration and cached reconstruction require a separate novelty analysis.
The current implementation proves no useful complete-model timing advantage.
Two short development articles cannot establish broad quality or submission readiness.

## Validation and reviewed hashes

Seven fixed-feature tests cover the reviewed target and service.
The provider agent also ran the nine earlier anchor service tests with the revised target.
All 16 service tests passed after the isolation fix.
The final combined log reports 34 passing tests.
That log is `pilots/v21/software-tests.txt`.
These are software fixtures, not empirical quality or timing evidence.

| File | SHA-256 |
|---|---|
| `src/fixed_anchor_target.py` | `09cb327fcbb91fc3a747d4891a1358043356d293927719e586e4344b0146acea` |
| `src/fixed_anchor_service.py` | `96a3e9f90ac7cdd236fa242a3e3a839537df9926c04f7e8c4bcf378b95832d08` |
| `tests/test_fixed_anchor_v21.py` | `08e511decfa527cc76211c31465d0fd658f0a25a633d06c21dd54c7c6225e084` |

No blocking defect remains under the declared trusted-preparation and finite-runtime premises.
This conclusion does not validate untrusted fabricated leaves or externally supplied preparation receipts.
