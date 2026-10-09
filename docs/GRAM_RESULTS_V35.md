# Exact pooled-Gram component results

Independently audited on 9 October 2026.
This report adds an audit; it changes no registered V35 file.

## Result

All three methods produced the same 3,072 exact quantized codes.
Pooled-minus-deleted moments matched independently accumulated retained moments byte-for-byte.
The exact pooled-Gram implementation is correct on this component.
It is much slower and larger than the existing retained-feature cache here.

| Component arm | Seconds |
|---|---:|
| Original pooled-Gram preparation | 7.557861 |
| Pooled-Gram deletion and reconstruction | 14.830470 |
| Fresh retained-Gram construction and reconstruction | 14.180701 |
| Retained lossless-feature decode and token solver | 0.501197 |

Gram deletion took 29.59 times the cached-token component time.
Fresh Gram reconstruction took 28.29 times the cached-token component time.
Gram deletion also took 1.046 times fresh Gram reconstruction time.
These ratios describe one fixed-order development observation, without timing confidence intervals.

## What was tested

The component uses the first DistilGPT2 QKV stage at its complete width of 768.
It evaluates output rows 0 through 3, rather than all 2,304 stage rows.
The two original WikiText records each supply 128 archived real feature tokens.
Deletion removes article row 17,380 and retains article row 22,925.
The original normalization remains 256, with ridge 1/100 and four-bit row grids.
No feature coordinate was cropped.
No neural feature generation was reexecuted.

The preparation arm constructs both exact source Grams, then adds them.
The deletion arm reloads the authenticated pooled Gram and decodes deleted features.
It recomputes the deleted source contribution, subtracts it, and certifies retained codes.
The cold arm independently constructs the retained Gram from retained features.
The cached-token arm independently decodes retained features and uses the existing exact-target solver.
No arm receives the reference codes as candidate proposals.

## Costs and storage

Shared verification, capsule parsing, and native compilation took 0.505609 seconds.
Those costs appear separately from the arm totals above.
The complete controller transaction took 37.815456 seconds.
Its settled CPU observation was 37.797299 seconds, charged as 38 seconds.
The 900-second phase allowance was not exhausted or reset.

Each arm includes its required feature decoding and numerical work.
Gram arms also include their specified parsing, serialization, output writing, and code verification.
Neural replay and original complete-model preparation are absent.
These measurements establish no service or lifetime speedup.

The deletion arm spent 10.712259 seconds in direct-Gram solve and certification.
That represents 72.23% of its component time.
Within that call, coefficient construction took 9.078012 seconds.
Exact-to-binary64 enclosure construction took another 1.542047 seconds.
Its four-row native verification took 0.086621 seconds.
These diagnostics explain the implementation's cost distribution, not a causal optimization result.

| Retained stage representation | Bytes |
|---|---:|
| Canonical exact Gram archive | 5,020,445 |
| Existing lossless feature descriptor | 688,713 |
| Uncompressed feature words | 786,432 |

The Gram archive is 7.29 times the lossless descriptor size here.
It is 6.38 times the raw feature size.
These are stage-representation counts, not complete service-state sizes.
They exclude shared weights and the base checkpoint.
Identity-only deletion still needs stored source contributions or permitted deleted-feature access.
This pilot uses the latter access contract.

## Independent evidence audit

The auditor verified the registered source, input, runtime, and historical ledger bindings.
The controller plan, command, resource limits, receipt, settlement, and terminal commitment also agree.
Actual output files match their reported sizes and SHA-256 digests.
Both retained Gram archives are canonical and equal.
Their source membership, width, token count, and original normalization are correct.
All three packed code artifacts also equal the capsule's independently bound archived reference.
This audit performed no new Gram accumulation or quantizer execution.

| Evidence | SHA-256 |
|---|---|
| Program | `a676d214813f1bd47d55f5bf3629a768826a85b3368a7169309f07e0173fd5fa` |
| Terminal record | `542477b7833e41190f35b7d973fff34662aab639c567434ad3e2a68b4aa110d1` |
| Each packed code artifact | `b0352fd4fdc9224a19f61b3f135cefee016c82fb9b8c458bfe8fabf72b5a523b` |
| Each retained Gram archive | `cb52f8039e5034f26995d88ab87397fa18be28c7fd7c18ec9d1d682f92c5a252` |

The original V35 status command freezes the entire ledger-path inventory.
Adding a separately registered later campaign can therefore make that historical status command reject the new path.
This does not alter the completed evidence or authorize editing its registered controller.
Later audits must preserve every historically bound ledger and verify this terminal record separately.

## Interpretation and next test

This result weakens the practical appeal of this exact pooled-Gram implementation at low retained token counts.
It strengthens the need to compare representations under their actual dimensions and access contracts.
It does not demonstrate universal superiority of feature caching over Gram methods.
It also supplies no new comparison of compressed-feature repair against a complete-model Gram service.

Four rows provide limited amortization of the shared coefficient-construction cost.
A new all-2,304-row QKV pilot directly tests that limitation without changing features or numerical parameters.
That follow-up must be separately registered before observing its outputs.
If certification refuses any row, the result remains unresolved; no approximate acceptance is permitted.
Further complete-model, larger-token, cross-model, and prospective-confirmation work remains necessary.
