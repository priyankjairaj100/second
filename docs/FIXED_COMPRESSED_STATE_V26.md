# Version 26 compressed fixed-feature state

Revision 26 adds a separate state format for wider compressed factor evidence.
It stores every calibrated model code and every retained source descriptor.
It preserves the existing fixed-feature numerical target.
This component does not implement model repair or prove a speed improvement.

## Interface

`src/fixed_compressed_state_v26.py` provides these objects:

| Object | Purpose |
|---|---|
| `CompressedFactorLeaf(record_id, tokens, descriptors)` | Stores one source and its ordered factor descriptors. |
| `CompressedFactorState(..., stages, anchors)` | Stores provenance, codec settings, complete calibrated codes, and retained leaves. |
| `from_factor_state(state, bits=40, block_size=256)` | Converts trusted exact factors into intrinsic descriptors. |
| `serialize(state)` | Produces canonical immutable bytes. |
| `parse(data, limits=LoadLimits(), expected_sha256=None)` | Loads bounded canonical bytes and checks their bindings. |

The state exposes `record_ids`, `digest`, and `canonical_bytes()`.
These names match the exact factor state interface.
The `anchors` field contains leaves, ordered by source identifier.
Each leaf contains one descriptor for every model stage.
Descriptor order follows the model stage order.

The state fields are:

```python
CompressedFactorState(
    target_sha256,
    anchor_target_sha256,
    decoder_sha256,
    provider_sha256,
    anchor_sha256,
    preparer_sha256,
    codec_sha256,
    bits,
    block_size,
    stages,
    anchors,
)
```

`preparer_sha256` preserves the exact factor preparation binding.
`codec_sha256` identifies the source that encoded the descriptors.
The parser preserves archived bindings.
The repair service must check the bindings against its actual runtime.

## Numerical semantics

Conversion encodes each exact factor separately with the revision 26 codec.
It uses only that factor and its source metadata.
Supported precisions are 16, 24, 32, 40, and 48 bits.
The conversion default is 40 bits, with blocks of 256 values.
It does not inspect any other source during encoding.
Every descriptor keeps the original factor hash.
Its box contains the original factor under the codec's trusted preparation premise.
Conversion preserves each `StageCodes` object without numerical changes.

For a trusted exact state \(S\), let \(C_p(S)\) denote conversion at fixed codec settings \(p\).
Then its complete calibrated code sequence satisfies

\[
\operatorname{codes}(C_p(S))=\operatorname{codes}(S).
\]

For a retained source set \(R\), source-local conversion also satisfies

\[
\operatorname{leaves}(C_p(S)|_R)
=\operatorname{leaves}(C_p(S|_R)).
\]

This equality concerns descriptor bytes and source metadata.
It does not certify the new model after deletion.
The service must compute or certify that model separately.

Temporary refinement must not alter stored intrinsic descriptors.
Otherwise, deletion history could change the canonical state.
The format contains no persistent refinement field.

An empty retained set has no leaves.
Its state still stores the complete calibrated model supplied by the caller.
Conversion does not verify that supplied codes solve the empty calibration problem.
The numerical service has that responsibility.

## Format and validation

The format uses magic `VCFS`, version two.
Its storage schema is `source_local_compressed_factors_v2`.
The numerical family remains `fixed_anchor_calibration_v1`.
This format differs from exact factor state bytes and revision 25 compressed state bytes.
Both compressed parsers reject the other format.
Their leaf types also reject descriptors from the other codec version.

The file contains:

1. Eight magic bytes and an unsigned 64-bit header length.
2. A canonical JSON header.
3. One complete calibrated model payload.
4. One complete codec payload per source and stage.

The header binds all payload sizes and hashes.
It also binds target, anchor, decoder, provider, preparer, and codec provenance.
Each source index binds its identifier, ordered tokens, token hash, and descriptor shapes.
Each descriptor independently binds its target, source, tokens, stage, codec, and original factor hash.

Constructors reject duplicate source identifiers and duplicate stage identifiers.
They reject missing stages, reordered stages, and incompatible widths.
They reject descriptor bindings that disagree with the enclosing state.
They normalize mutable sequence arguments into tuples.
Descriptor payloads and packed model codes remain immutable bytes.

Parsing checks resource bounds before descriptor decoding.
The bounds cover file bytes, header bytes, records, stages, codes, and tokens.
Each leaf also has bounds on encoded descriptor bytes and decoded factor values.
The parser checks all descriptor dimensions before decoding that leaf.
Nested codec bounds also restrict tokens, width, values, block size, and payload size.
The parser rejects trailing bytes and noncanonical ordering.

`max_leaf_bytes` bounds the combined encoded descriptors for one leaf.
`max_leaf_values` bounds the combined decoded values for one leaf.
The containing header has a separate byte bound.
These settings do not estimate process memory or runtime.

## Trust boundary

Hashes detect content changes against a trusted expected digest.
They do not prove how any factor was prepared.
They do not prove containment for unavailable source factors.
A self-consistent artifact can contain false provenance claims.

The trusted caller must establish exact factor preparation before conversion.
An artifact digest must come from that trusted preparation when sources are unavailable.
The service must also reject stale runtime bindings.
Exact fallback must check reconstructed factors against their stored source hashes.
These checks preserve evidence binding; they do not replace the initial trust premise.

## Software checks

`tests/test_fixed_compressed_state_v26.py` uses small software fixtures only.
It checks complete model preservation and source containment after conversion.
It checks canonical parsing, empty states, and unchanged descriptors after source deletion.
It checks sequential and direct source subsets for identical bytes.
It checks all five precisions for containment and complete model preservation.
Dedicated 32-bit and 40-bit cases check canonical deletion states.
It checks the 40-bit default and rejects revision 25 artifacts.
The 16-bit payload test preserves the earlier arithmetic while requiring new provenance bindings.
It checks bounds before descriptor decoding.
It checks corrupted payloads, inconsistent bindings, and invalid codec settings.
It explicitly checks the limit of self-consistent source hashes.

These checks provide software evidence.
They provide no model quality, certificate acceptance, storage benchmark, or repair timing evidence.
Full compressed repair measurements remain a separate task.

## Precision changes and source access

Changing precision within version 26 changes precision metadata and canonical bytes.
The codec source binding stays unchanged because the same source manifest covers every supported precision.
Migration between codec versions also changes the codec source binding.
It does not change the defining fixed-feature quantization target.
The output model must still match the exact factor reference.

The conversion API requires a trusted exact factor state.
It does not reconstruct fine descriptors from coarse descriptors.
A coarse interval usually lacks the exact value needed for finer encoding.
A service must obtain that value from trusted factors or exact source replay.
That work must appear in its preparation or repair accounting.

Wider cells contain more source information and use more bytes.
A complete state also stores model codes, tokens, provenance, and framing.
Factor payload ratios therefore do not equal complete state ratios.
This implementation makes no empirical storage or repair speed claim.
Archive measurement and full service measurement remain separate tasks.

Revision 25 source, format, tests, and measured artifacts remain unchanged.
The existing revision 25 repair service does not automatically accept this format.
