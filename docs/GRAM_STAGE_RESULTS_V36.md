# Complete first-QKV pooled-Gram results

Independently audited on 9 October 2026.
This report changes no registered V35 or V36 evidence.
The audit performed no new Gram accumulation or quantizer execution.

## Result

All three arms certified all 1,769,472 first-stage codes exactly.
Every output artifact equals the independently archived retained reference byte-for-byte.
The repaired Gram equals the independently constructed retained Gram canonically.
No arm refused, and the registered scientific gate passed.

| Full first-QKV component arm | Seconds |
|---|---:|
| Original pooled-Gram preparation | 8.535798 |
| Pooled-Gram deletion and reconstruction | 65.995601 |
| Fresh retained-Gram construction and reconstruction | 61.257673 |
| Retained lossless-feature decode and token solver | 1.299832 |

Pooled-Gram deletion took 50.77 times the cached-token component time.
Fresh Gram reconstruction took 47.13 times the cached-token component time.
Deletion also took 1.077 times fresh Gram reconstruction time.
These comparisons concern the tested implementations and this fixed-order stage workload.
They are not complete-model speed ratios or population estimates.

## Scope and target

The test covers all 2,304 rows and all 768 coordinates of DistilGPT2's first QKV stage.
It extends the earlier four-row component without changing its archived real features.
The original two WikiText records each contribute 128 feature tokens.
Deletion removes article row 17,380 and retains article row 22,925.
Original normalization remains 256, ridge remains 1/100, and grids remain four-bit and base-only.

The source commitments and canonical Gram artifacts are also identical to V35's corresponding artifacts.
Increasing output-row coverage did not change the calibration moments or deletion target.
No neural feature generation was repeated.
No candidate code proposal was supplied.
The cached-token arm certified every row without exact fallback or refinement.

## Cost interpretation

Shared input verification, capsule parsing, and native compilation took 0.899438 seconds.
Those costs are separate from the component totals above.
The controller transaction took 138.288219 seconds.
Observed worker CPU was 138.264466 seconds, charged as 139 seconds.
There is one settled debit against the separate 900-second phase allowance.
Every historically bound ledger remains unchanged.

Each arm includes its own feature decoding and specified numerical work.
Gram arms also include loading, exact accumulation, subtraction where applicable, serialization, and output writing.
All arms include code verification, packing, and diagnostic dataclass conversion.
V35 performed that last diagnostic conversion outside its arm total.
Consequently, V35 and V36 do not form a strictly matched row-scaling timing study.
V36's within-run arm comparisons share the registered timing policy.

| Deletion-arm diagnostic | Seconds |
|---|---:|
| Exact deleted-source Gram accumulation | 3.983864 |
| Exact pooled subtraction | 0.125502 |
| Exact-to-binary64 Gram enclosure | 1.592034 |
| Shared coefficient construction | 10.928831 |
| Native row verification | 48.889642 |

Native row verification alone represents 74.08% of deletion time.
Thus the loss is no longer explained only by amortizing shared coefficients over four rows.
The existing cached-token row verifier took 0.605546 seconds across the complete stage.

This direct-Gram backend reuses a generic interval row kernel with identity features.
That kernel scans width-sized accumulators and explicitly processes identity and zero entries.
A specialized triangular row kernel could remove redundant work.
Its attainable speed remains unmeasured, and this experiment establishes no optimality bound.
The exact Gram accumulator also uses Python arbitrary integers rather than an optimized native accumulator.
These implementation limits preclude claiming superiority over every possible pooled-Gram method.

The retained-token count is 128 while the feature width is 768.
That regime favors a token-space representation structurally.
The observation cannot determine the relative ranking when retained token counts greatly exceed feature width.

## Storage accounting

| Retained first-stage payload | Bytes |
|---|---:|
| Exact Gram archive | 5,020,445 |
| Lossless feature descriptor | 688,713 |
| Shared complete packed output codes | 884,736 |
| Gram archive plus output codes | 5,905,181 |
| Lossless descriptor plus output codes | 1,573,449 |

The Gram archive alone is 7.29 times the descriptor size.
Adding the same output-code payload reduces the ratio to 3.75.
These totals are explicit payload sums, not implemented complete service-state formats.
They exclude shared base weights, other stages, and additional service framing.
The Gram deletion arm also assumes access to the deleted feature descriptor before erasure.
Pooled moments alone do not implement arbitrary identity-only source deletion.

## Independent evidence checks

The auditor verified all 168 registered source bindings and all 64 bound prior ledgers.
All 22 registered capsule and dependency files also passed their byte bindings.
The original program, attempt plan, command, resource limits, receipt, and CPU settlement agree.
The completion file, sealed copy, and stdout terminal commitment agree.

All three actual packed code files contain 884,736 bytes.
Each equals the independently decoded reference from the authenticated stage capsule.
The auditor checked the full arrays, rather than only their reported equality flags.
Both retained Gram archives parse canonically and match byte-for-byte.
Their width, membership, retained token count, and original normalization are correct.
The original and retained Gram files also equal their V35 counterparts exactly.

Recorded native source digests match the pinned source strings.
Their build records retain strict floating-point flags and disabled contraction.
No compiler or numerical worker was rerun during the audit.

| Evidence | SHA-256 |
|---|---|
| Program | `28fad1a3e18cad1895eebe54ae7b57b93431d49f644d26b1fd566e5838b05bd2` |
| Terminal record | `6b28544e10eb06c5aa6081d6a9fe1841e8bc2574cc7aaf1e70ed28e32f0f1c59` |
| Each complete packed code artifact | `689de4350fb28b87b51e0653fc71c694264a8dd6a4ffdb93fce2e4f5c6a9c645` |
| Each retained Gram archive | `cb52f8039e5034f26995d88ab87397fa18be28c7fd7c18ec9d1d682f92c5a252` |

## Research implication

The all-row follow-up resolves the specific four-row coverage objection for this first-stage implementation.
It demonstrates a correct exact pooled-Gram control and preserves its unfavorable cost result.
It supports using the lossless feature cache as a strong practical comparator in this low-token workload.
It does not establish compressed-feature superiority, complete-model Gram inferiority, or unconditional repair speedup.

The arm order was fixed, measurements were not replicated, and OS cache state was uncontrolled.
The request was already exposed and the extension was motivated by V35's result.
This is adaptive development evidence, not independent confirmation.
Further implementation optimization, larger-token workloads, other stages, and complete service accounting remain open.
