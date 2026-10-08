# Revision 22 fixed-factor and evaluator review

Status: review completed under the stated finite-runtime and trusted-preparation premises.
This is an internal project review.
It is not external verification or proof-assistant verification.
No empirical worker belongs to this review.

## Numerical target

The minimal state must retain the revision 21 fixed-feature target digest.
It must not replace that target with the original sequential target.
Changing the stored representation does not change the fixed feature law.
Each stage still receives features from the complete nearest-anchor prefix.
Calibrated output codes never enter that feature traversal.

## Exact factors and canonical state

The new leaf stores complete token-major binary64 factors.
It omits the scalar operation tape and affine summaries.
It retains immutable byte storage, record tokens, stage names, and factor dimensions.
The state binds the fixed target, anchor target, decoder, provider, anchor model, and preparer.
The preparer binding includes both its module and the finite traversal module.

Direct preparation follows the declared scalar finite traversal.
Conversion copies the existing trusted anchor factor bytes into the new representation.
Signed-zero encodings remain part of these factor bytes.
The model's exact rational metric identifies both zero signs.
That numeric fact alone does not prove equality between serialized factor states.
The preparation and conversion paths must preserve the same signed-zero outcomes separately.

The finite schedules use the same ordered products, sums, divisions, and primitives.
Array batching groups independent coordinates without changing their operation order.
The attention maximum can select a different zero sign on a tie.
The next exponential maps either signed zero to the same positive one.
Thus that tie cannot change an attention output's sign or value.
The tests compare direct and converted factor bytes for all fixture stages.
They also check that immutable raw factor storage preserves both signed-zero encodings.

Deletion selects retained leaves and omits deleted leaves.
The final state contains no old scalar tape or affine summary.
Fresh retained preparation must produce the same leaf bytes as valid repeated deletion.
The canonical parser must reject inconsistent hashes, dimensions, bindings, record order, and trailing bytes.
Trusted preparation remains a premise.
Hashes do not authenticate fabricated factor values.

## Prepared evaluator

`PreparedFinitePrefix` skips repeated scalar validation only for exact-type `CompactDyadicMatrix` inputs.
The matrix's immutable storage already validates every encoded value as finite.
Its shape and named decoder stage still receive explicit checks.
Ordinary inputs retain the original scalar type validation.
Subclasses must also retain that validation.

The fast path returns the same compact float view as the original validated path.
Both views convert every encoded signed zero to positive zero.
Both views preserve every other finite encoded value exactly.
F16, BF16, F32, and F64 values have exact binary64 representations.
Allowed strides select the same validated byte positions.
Captured immutable storage therefore preserves the same installed matrix and finite logits.

This optimization removes repeated validation work.
It does not change model weights, the finite decoder schedule, or quality outputs.
It must reach every compatible comparison method.
No measured latency improvement follows from the implementation alone.

## Evidence and remaining limits

Seven minimal-state tests passed.
They compare direct preparation with conversion of full anchor leaves.
They compare exact model codes across both state backends and both point solvers.
They also cover deletion history, empty retention, stale preparers, parser limits, and immutable factor bytes.

Eight evaluator tests passed.
The saved log is `pilots/v22/evaluator-software-tests.txt`.
They check all four storage formats, reversed strides, mixed representations, shape errors, and subclass rejection.
They compare complete output bits with the original evaluator.
These are software fixtures, not new empirical datasets or latency measurements.
The final combined log reports 49 passing tests.
That log is `pilots/v22/software-tests.txt`.

The archived-state audit compares 24 complete factors and all packed model codes.
It reports identical factor bytes, identical code bytes, and a canonical parser roundtrip.
The complete stored representation decreases from 54,107,392 bytes to 26,326,066 bytes.
The audit is `pilots/v22/factor-storage-audit.json`.
This is a storage conversion result for one archived state.
Its conversion timer is not a model-repair latency measurement.

Repair and indexed reconstruction must retain identical access and numerical paths.
Storage reduction does not establish superiority over indexed reconstruction.
Fresh preparation, serialization, loading, and later requests still require complete cost accounting.
This revision does not complete the broad empirical program.

No blocking defect remains in the reviewed implementation under its declared premises.
The implementation does not authenticate fabricated factor values or unverified external preparation receipts.

## Reviewed hashes

| File | SHA-256 |
|---|---|
| `src/fixed_factor_state.py` | `e71477de4e0bb048c7c068e0a087587b37cb59d766e18d0d87cff5c3dc23c71f` |
| `src/fixed_anchor_service.py` | `3aa12be78b03b6be1887e5cc3b5ecbe12ca0a1f61584d1b299ca3d429e6a7278` |
| `src/prepared_finite.py` | `638ce87d51c49c682e02ea3e11891f3bc1d922cce55c0501ab1b5ddfc92e22e4` |
| `tests/test_fixed_factor_v22.py` | `af0d4bcacbbe9e2516d0d822f8801a394020fc28e23d5d4d4f4bf76bf8b20b2a` |
| `tests/test_prepared_finite_v22.py` | `b5c3872819cb37e6d8debee2ff52d117370b6ac0fd73df95d83a88c83b592a3e` |
