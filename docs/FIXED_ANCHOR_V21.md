# An explicit fixed-feature calibration track

This track changes the quantization target.
It does not repair the original sequential target.
The change removes the dependence of later features on calibrated output codes.
Its practical quality and speed remain empirical questions.

## 1. Distinct numerical target

Let $T$ denote the original base weights, grids, decoder, and fixed normalization.
Let $A_T$ denote nearest-grid rounding of those base weights.
The anchor model depends on no calibration record.
For source record $r$, define

\[
 Z_{i,T}(r)=\operatorname{Feature}_i(r;A_{T,<i}).
\]

For retained records $R$, concatenate these factors in sorted source order.
Calibrate every stage independently:

\[
 Q_i^{\mathrm{fixed}}(R)=
 \operatorname{DyadicQuantize}_i\left(
 W_i, [Z_{i,T}(r)]_{r\in R}\right).
\]

Every solver uses the original fixed ridge and normalization.
The complete deployed model contains all $Q_i^{\mathrm{fixed}}(R)$.
These calibrated outputs never enter another calibration feature calculation.

The sequential target instead uses its previously calibrated outputs:

\[
 Q_i^{\mathrm{seq}}(R)=
 \operatorname{DyadicQuantize}_i\left(
 W_i,[\operatorname{Feature}_i(r;Q_{<i}^{\mathrm{seq}}(R))]_{r\in R}\right).
\]

The two target laws can agree on some inputs.
Their agreement on one input does not make the target laws identical.
The new target digest always distinguishes the laws.

`build_fixed_anchor_target` binds the base target, decoder, provider, and changed feature rule.
It also binds its constructor source.
It performs no hidden anchor preparation.

## 2. Why deletion becomes local

**Source-local feature theorem.**
For every surviving record, deleting other records leaves each fixed anchor factor unchanged.

The proof follows directly from the feature definition.
Its inputs are the record, fixed decoder, and fixed anchor prefix.
None of these inputs changes when another record is removed.

Therefore retained factors need no transformer transport certificate.
They also need no transformer replay when trusted factors already exist.
Quantization still uses the retained calibration metric.
Every output coordinate can still change after deletion.
The current implementation recomputes all quantization decisions.

**Complete-state theorem.**
Assume deterministic trusted leaf preparation and successful exact point solving.
Fresh construction and any valid deletion history produce identical canonical retained state bytes.

Each retained leaf equals the same source-local preparation function.
Each stage receives the same sorted retained factor matrix.
The exact point solver therefore returns the same stage codes.
Canonical sorting and serialization give the same complete state bytes.
The result includes no-op requests and empty retention.

This theorem concerns the fixed-feature target only.
It does not transfer accuracy or speed guarantees from sequential calibration.

## 3. State and parser separation

The state class is `FixedAnchorState`.
Its family is `fixed_anchor_calibration_v1`.
Its file magic differs from the sequential anchor state's magic.
The state binds both the fixed-feature target and original anchor target.

The original anchor target defines only leaf preparation within this state.
The outer fixed-feature target defines output model semantics.
The internal encoding reuses the existing canonical anchor payload format.
That internal payload is structural storage, not a sequential-model claim.
Consumers must use the outer parser and outer target digest.

The sequential service rejects `FixedAnchorState` objects.
The sequential parser rejects complete fixed-state files.
The fixed service rejects seeds bound to the sequential target.
Fixed-feature stages declare no calibrated-stage dependencies.
Generic sequential services therefore reject this target at construction.
The original sequential dependencies remain available only through the anchor target.
Both parsers retain bounded allocation and canonical encoding checks.

The current state keeps complete source-local anchor leaves.
It therefore retains scalar summaries that this target does not need.
A smaller state could retain exact factors and their bindings only.
That optimization would preserve the target law.
It requires separate storage and preparation measurements.

## 4. Comparison methods and accounting

`direct_fresh` prepares retained leaves and writes complete state.
`repair` reuses trusted retained leaves and writes complete state.
`indexed_fresh` has the same leaf access and numerical path as repair.
`model_only_fresh` computes fixed factors through the shared exact decoder traversal.
It creates no anchor summaries and writes no state.

The model-only traversal always installs nearest-anchor matrices.
It never installs calibrated output matrices into calibration traversal.
Native and reference solvers remain common options.
Prior code proposals are disabled by default.
An explicit warm model-only control receives the same prior model when enabled.

The strongest indexed reconstruction control matches repair's available information.
The current design provides no algorithmic advantage over that control.
It can save transformer work relative to model-only cold reconstruction.
Whether that saves complete transaction time remains unmeasured.

Write a symbolic accounting comparison as

\[
 C_{\mathrm{cold}}=C_{\mathrm{context}}+C_{\mathrm{features}}+C_{\mathrm{solve}}+C_{\mathrm{model}},
\]

\[
 C_{\mathrm{repair}}=C_{\mathrm{context}}+C_{\mathrm{read}}+C_{\mathrm{validate}}
 +C_{\mathrm{solve}}+C_{\mathrm{state}}.
\]

This decomposition identifies the required savings condition.
It does not give a universal wall-time inequality.
The experiment must also charge initial preparation, storage, loading, and output.
Repeated requests must include those initial costs under the declared amortization rule.

## 5. Construction from previously prepared leaves

The public route is:

```python
service = FixedAnchorService(decoder, base_target)
result = service.run_prepared(
    records,
    anchors,
    preparation_receipt={
        'source': 'archived worker and artifact path',
        'artifact_sha256': artifact_sha256,
        'elapsed_ns': archived_preparation_elapsed_ns,
    },
)
```

This route requires exact record membership, unchanged tokens, and matching provenance bindings.
It computes a new complete fixed-feature model.
It does not require an invented previous fixed-feature model.

The service records the external preparation receipt and its elapsed value.
It also records that it did not verify that historical timer.
The current service clock excludes this prior preparation.
Experiment analysis must add or amortize the archived cost explicitly.
The route is labelled `prepared_leaf_construction`.
It is neither an ordinary fresh measurement nor a repair measurement.

## 6. Verification and empirical gates

Seven focused MPFR software tests pass.
The independent oracle restarts the decoder with fixed nearest ancestor matrices at every stage.
It then uses the reference dyadic solver.
The complete service model matches this oracle.

The tests also compare native, reference, warm, fresh, repair, and indexed reconstruction outputs.
They check complete canonical state equality after repeated deletion.
They check format separation, provenance, parser limits, and prepared-leaf accounting.

These tests do not establish model quality or speed.
The first real-data gate must compare fixed-feature and sequential model quality.
The next gate must compare complete transactions with shared optimized solvers.
The strongest indexed reconstruction control must remain visible.
This design change supplies no standalone novelty claim.
