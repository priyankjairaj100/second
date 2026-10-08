# Explicit ordered finite decoder

`OrderedFiniteDecoder` is an opt-in subclass of `CertifiedDecoder`.
It preserves the declared model target and records its actual implementation separately.
It changes no historical decoder file or global function binding.

## Public interface

```python
decoder = OrderedFiniteDecoder(base, primitive_backend="mpfr_enclosure")
logits = decoder.logits(tokens, prefix)
features = decoder.stage_features(stage_id, tokens, prefix)
stream = decoder.sequential_features(tokens)
prepared = decoder.prepare_prefix(prefix)
logits = prepared.logits(tokens)
```

The standalone generator is `ordered_sequential_features(decoder, tokens)`.
It requires the explicit ordered decoder type.
Each generator advance enters and restores its primitive scope.
The scope does not remain active while the generator is suspended.

The prepared prefix validates immutable installed matrices once.
It then uses the same ordered finite executor for every record.
It does not call the historical prepared executor, which binds the original execution function.

## Activation arithmetic

The implementation batches independent token and MLP coordinates.
It preserves every scalar multiplication, addition, and division within each coordinate.

For the erf activation, it computes these values in order:

\[
h=\operatorname{RN}(0.5x),\quad
a=\operatorname{RN}(x/\operatorname{RN}(\sqrt2)),\quad
e=\operatorname{RN}(\operatorname{erf}(a)),
\]

\[
s=\operatorname{RN}(e+1),\qquad
y=\operatorname{RN}(hs).
\]

The square root retains the existing correctly rounded primitive implementation.
The erf call uses directed endpoint verification or the unchanged fallback.

For the tanh activation, the cubic term retains left association:

\[
p_1=\operatorname{RN}(0.044715x),\quad
p_2=\operatorname{RN}(p_1x),\quad
p_3=\operatorname{RN}(p_2x).
\]

Then it computes

\[
a=\operatorname{RN}\!\left(c\operatorname{RN}(x+p_3)\right),\quad
t=\operatorname{RN}(\tanh(a)),\quad
y=\operatorname{RN}\!\left(\operatorname{RN}(0.5x)\operatorname{RN}(t+1)\right).
\]

The constant \(c\) retains the exact binary64 encoding `0x1.9884533d43651p-1`.
Separate NumPy operations preserve intermediate rounding and prevent contraction.
Nonfinite intermediate results cause refusal.
Signed zeros and permitted subnormal results retain the reference behavior.

## Primitive verification

`batch_rounded_primitive()` supports `exp`, `tanh`, `erf`, and `sqrt`.
The active primitive backend remains authoritative.
The rational backend calls the existing scalar primitive function.

The MPFR backend computes directed 104-bit endpoints in bounded chunks.
It converts endpoints through exact integer ratios and the existing rational rounding implementation.
Equal binary64 encodings prove acceptance.
Ambiguous endpoints and exceptional arguments use the original primitive fallback.
No MPFR-to-float conversion assumption or foreign-library ABI enters this path.

The certificate can complete for inputs where an earlier enclosure exhausted its precision limit.
Thus the claim concerns identical finite values on the common completion domain.
It does not claim identical resource use or identical refusal behavior for all inputs.

## Target and provenance

The inherited `kernel_manifest`, `evaluator_id`, and `reference_id` remain identical to the reference decoder.
These values identify the declared finite model target.
They do not identify the new execution code.

`implementation_manifest` records the new source hashes and the NumPy version.
It also records the arithmetic schedule and the absence of global function replacement.
The property returns an independent copy.

Prepared state must carry the new ordered preparer identity.
It must not claim that the historical preparer executed.
The new ordered services therefore require independently prepared state.
They reject state carrying the old preparer identity.

The model target can remain identical while state bytes change because provenance changed.
Complete model equality remains the required comparison with the old implementation.
Within the ordered service, fresh and repair must still produce identical canonical retained state.

## Verification scope

Twenty-two combined software tests passed in a reported 0.222 seconds.
The set includes attention tests, independent endpoint tests, and decoder integration tests.

The tests verify these properties.

- Every stage feature and complete logits match the original decoder on finite fixtures.
- Both activation forms preserve their scalar operation order.
- Both primitive backends produce matching values.
- Installed-prefix traversal matches the original sequential generator.
- Several blocks and heads preserve causal prefix outputs.
- Prepared prefixes preserve complete logits and immutable installed state.
- Primitive scopes restore correctly across generator suspension.
- Target manifests match while implementation manifests remain separate.
- No historical attention function or finite primitive method is replaced.
- Invalid inputs and nonfinite arithmetic cause refusal.

These tests are software fixtures, not empirical datasets.
They do not establish model-scale speed or complete-program superiority.
The registered empirical identity pilot must precede a new speed claim.

The original attention review remains bound to its earlier source hash.
The extended primitive helper and decoder need review at their final hashes.
