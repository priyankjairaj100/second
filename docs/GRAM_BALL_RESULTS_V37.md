# Strengthened pooled-Gram component results

Independently audited on 9 October 2026.
This report changes no registered source, receipt, output, or prior result.
No new Gram accumulation, compilation, or quantizer execution occurred during the audit.

## Result

All three arms certified every first-QKV output row.
All 1,769,472 codes match each other and the authenticated retained reference byte-for-byte.
Repaired and independently constructed retained Grams remain canonically equal.
No arm required interval fallback, exact fallback, or refinement.
The registered scientific gate passed.

| Complete first-QKV component arm | Seconds |
|---|---:|
| Original pooled-Gram preparation | 7.983567 |
| Pooled-Gram deletion and reconstruction | 17.724627 |
| Fresh retained-Gram construction and reconstruction | 17.158287 |
| Retained lossless-feature decode and token solver | 1.216621 |

The strengthened pooled-Gram deletion arm took 14.57 times the cached-token arm's time.
Fresh Gram reconstruction took 14.10 times the cached-token time.
Pooled deletion took 1.033 times fresh Gram reconstruction time.
These ratios describe this concrete implementation and one fixed-order stage workload.
They do not establish reliable complete-model superiority or an optimality bound for either representation.

## Compatible baseline strengthening

V36 identified avoidable overhead in the generic interval row kernel.
V37 gives the Gram comparator the same native ball row kernel already available to cached features.
Both Gram arms retain the existing exact accumulator and coefficient certificates.
They use virtual identity features with directed Euclidean coefficient-error bounds.
The identity changes the accumulator representation, not the quantization metric.

The same two archived WikiText records remain in use, with 128 feature tokens each.
Deletion removes article row 17,380 and retains article row 22,925.
All 2,304 rows and 768 coordinates remain included.
Original normalization stays 256, ridge stays 1/100, and grids remain four-bit and base-only.
No candidate-code shortcut or new neural feature generation was used.

The build records identify the same row-kernel binary for all three arms:
`7c327983c5c195132de8224434ffc42d07b0e37ad355fb64a6013427e13ced43`.
Its native source digest and strict compiler flags also agree.
The Gram coefficient kernel remains separately identified from that shared row kernel.

All three arms report 2,304 native-certified rows and 1,769,472 certified-prefix decisions.
All fallback counts and durations are zero.
The mandatory fallback remained available under the registered resource envelope.
Its unused status is an observation, not a removal of the failure safeguard.

## Cost diagnosis

| Measured diagnostic | Pooled deletion | Fresh Gram | Cached features |
|---|---:|---:|---:|
| Coefficient construction and verification | 9.266046 s | 8.844444 s | 0.503930 s |
| Native row verification | 2.567298 s | 2.567884 s | 0.553386 s |
| Exact Gram accumulation | 3.887054 s | 4.037124 s | Not required |
| Exact-to-binary64 Gram enclosure | 1.394124 s | 1.415863 s | Not required |

Coefficient work now represents 52.28% of pooled deletion time.
Native row verification represents 14.48%.
The former interval-kernel asymmetry has been addressed by compatible kernel reuse.
The remaining Gram path operates at width 768; the cached-feature path uses 128 token coordinates.
That dimensional difference is relevant to this workload.
The data do not determine the ranking when retained token counts greatly exceed feature width.

Compared descriptively with V36, pooled deletion dropped from 65.995601 to 17.724627 seconds.
That is a 3.72-fold ratio between the recorded times.
Its native row time dropped from 48.889642 to 2.567298 seconds, a 19.04-fold ratio.
V36 and V37 share the declared arm timing boundary.
They remain separate, unreplicated executions with uncontrolled machine and cache state.
These are adaptive optimization observations, not randomized estimates of the kernel's causal speedup.
V36's 50.77-fold gap must not substitute for V37's strengthened within-run comparison.

Further Gram optimization remains possible.
Examples include its coefficient verifier, arbitrary-integer accumulator, and identity-specialized row execution.
The experiment does not establish the fastest attainable pooled-Gram implementation.

## Complete recorded costs

Shared input verification, capsule parsing, and native compilation took 0.864454 seconds.
Those costs are reported separately from arm totals.
The controller transaction took 45.254049 seconds.
Observed worker CPU was 45.216726 seconds, charged as 46 seconds.
The phase contains one settled debit against its separate 900-second allowance.
No historical allowance or ledger was reset.

Arm totals include required descriptor decoding, numerical work, code verification, packing, diagnostics, and output writing.
Gram arms also include their specified parsing, subtraction, and serialization.
No neural replay, complete-model preparation, or changing-state lifetime experiment is included.
Consequently, this component cannot establish a service-level or lifetime advantage.

## Exact storage contract

| Retained first-stage payload | Bytes |
|---|---:|
| Canonical exact Gram archive | 5,020,445 |
| Lossless feature descriptor | 688,713 |
| Shared complete packed output codes | 884,736 |
| Gram archive plus codes | 5,905,181 |
| Lossless descriptor plus codes | 1,573,449 |

The Gram archive is 7.29 times the descriptor size.
Including equal output-code payloads yields a 3.75-fold payload ratio.
These are explicit stage-payload sums, not implemented complete service-state formats.
They exclude shared weights, other stages, and additional service framing.
The exact Gram bytes are unchanged from V35 and V36.

Pooled deletion here accesses the deleted feature descriptor before erasure.
It recomputes the deleted exact contribution and subtracts it from authenticated pooled moments.
A pooled Gram alone does not support arbitrary identity-only source deletion.
That stricter request contract would need additional retained information or a permitted reconstruction mechanism.

## Independent evidence audit

All 171 registered source bindings passed.
All 65 bound prior ledgers remain byte-identical.
All 22 capsule and dependency bindings passed.
Program, plan, command, resource limits, receipt, CPU settlement, and terminal commitment agree.
The live completion file, sealed copy, and stdout digest agree without a recovery exception.

The auditor read all three actual packed stage-code files.
Each matches the full independently decoded reference from the authenticated stage capsule.
The checks cover every code, not only reported equality flags.
Both retained Gram archives parse canonically and have correct membership, normalization, width, and token count.
They match each other and the corresponding V35 and V36 artifacts byte-for-byte.

The recorded native source strings match their pinned source hashes.
Strict floating-point build flags remain present.
All three recorded row-binary digests match the shared build record.
This audit did not rerun or recompile the native kernel.

| Evidence | SHA-256 |
|---|---|
| Program | `7c4fd95b6645a20adc7b4c1b84f20cc7d354348c4b4061f7ac8e76e887ec29da` |
| Terminal record | `270481550a53cf2eb3963b2623443f6403c9caaedda22952c075f39c53d87447` |
| Each packed stage-code artifact | `689de4350fb28b87b51e0653fc71c694264a8dd6a4ffdb93fce2e4f5c6a9c645` |
| Each retained Gram archive | `cb52f8039e5034f26995d88ab87397fa18be28c7fd7c18ec9d1d682f92c5a252` |

## Research implication

The low-token stage still favors cached exact features after a substantial compatible improvement to the Gram baseline.
That strengthens this narrow representation comparison and removes the identified row-kernel asymmetry.
It does not prove that compressed-feature repair beats the strongest possible Gram method.
It also establishes no full-model speedup, language-model inference acceleration, quality gain, or pretraining erasure guarantee.

The design followed exposed V35 and V36 results.
One request, one stage, fixed order, and one observation per arm provide no timing confidence interval.
Independent confirmation, larger calibration workloads, other stages and models, and complete service accounting remain open.
