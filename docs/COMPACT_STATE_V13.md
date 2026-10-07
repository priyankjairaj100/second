# Canonical factor identity state

This document defines the new `factor_identity_v1` state family.
It does not change the aggregate state family or either quantization target.
The state stores exact current-prefix factors and packed grid indices.
It does not store dense Grams, feature boxes, Taylor witnesses, or stale anchors.

## Contract

`CompactState(target_sha256, stages, factors)` contains an ordered stage sequence.
The sequence follows the target's declared execution order.
The target digest binds the model, recipe, runtime, and quantizer through an external target manifest.
The state parser checks digest syntax, not the external manifest's scientific completeness.

Each `StageCodes` stores a matrix shape, grid axis, bit width, scale exponents, and packed indices.
The grid axis is `row` or `column`.
The grid contains `[-2^(b-1), ..., 2^(b-1)-1]` times a positive power of two.
The supported bit widths are two through eight.
The state supports the existing fixed power-of-two grid targets.
It does not claim support for arbitrary nonuniform grids.

Each `RecordFactor` stores one retained record's complete token-major feature matrix for one stage.
It binds the record identifier, token sequence digest, token count, stage identifier, and exact preceding code sequence.
The prefix digest includes the target digest and every preceding stage's code identity.
This conservative binding permits reuse only when all preceding code identities remain unchanged.
It does not certify that equal hidden features follow from changed ancestors.

Every retained record needs one factor at every stage.
Each record must have the same token identity and token count at every stage.
Factors use stage order first and lexicographic record order second.
Feature rows retain the original token sequence order.
The service must compare token digests with the actual retained tokens.

The empty retained set has no factors.
Its state still contains the complete quantized model.
The service must compute these codes under the target's empty-set rule.

## Exactness and canonical bytes

Binary64 factors use immutable little-endian bytes in row-major order.
The factory rejects nonfinite values.
It normalizes negative zero to positive zero.
Both encodings denote the same exact rational factor.
The parser rejects negative zero to preserve one rational-zero encoding.

Grid indices use exactly `b` bits each in row-major order.
Bit order is least significant bit first within each index and byte.
The last byte's unused high bits must be zero.
The grid factory rejects values outside the grid or values that require rounding.
Code arrays and factor arrays expose immutable byte-backed NumPy views.

The file contains an eight-byte magic, an eight-byte header length, a canonical JSON header, and raw payloads.
The magic bytes are `56 43 46 49 01 00 00 00`.
The header length is an unsigned little-endian integer.
The header uses sorted keys, ASCII escaping, and no unnecessary whitespace.
It lists code payloads first, then factor payloads.
Each payload has a byte count and a SHA-256 digest.
The entire file also has a SHA-256 digest.

The parser rejects duplicate members, unknown fields, inconsistent lengths, invalid hashes, noncanonical order, and trailing bytes.
It also rejects stale prefix bindings and incomplete retained membership.
`LoadLimits` bounds file size, header size, stage count, record count, factor count, and element totals.
Default file size is 512 MiB.
The caller supplies already-loaded bytes.
The file reader must apply its own size limit before reading those bytes.

Internal hashes detect corruption, not malicious replacement of a file and every corresponding hash.
Use `parse(data, expected_sha256=trusted_digest)` when a trusted receipt exists.
Collision resistance remains an explicit cryptographic assumption.
The parser cannot prove that a declared factor came from the certified decoder.
That execution guarantee belongs to the service and its checked inputs.

## State equality

Suppose fresh and repaired runs use the same target, ordered stages, retained records, and token identities.
Suppose their grid indices and exact normalized factor values also match.
Their canonical headers and payloads then match field by field.
Therefore, their serialized states match byte for byte.
No invocation history, timing field, fallback count, or deleted factor enters the state.

This result concerns representation equality under matching values.
It does not prove that an arbitrary repair algorithm computes those matching values.
A changed prefix requires exact factor recomputation or a separate proof that returns exact factors.
A feature box alone cannot produce this family's exact current-prefix state.
Transport with stale anchors requires a distinct state contract.

Deleted records have no factor entries in the resulting state.
Services must construct the new membership explicitly.
Removing old factors alone does not update quantized codes.
The target digest can still bind original normalization and other permitted deletion-invariant parameters.

## Storage and costs

For stage `s`, let `P_s` be its code count and `b_s` its bit width.
Let `d_s` be its input width and `T_r` a retained record's token count.
The raw payload size is exactly:

\[
\sum_s \left\lceil P_s b_s/8\right\rceil
+8\sum_s\sum_{r\in R} d_s T_r.
\]

The header adds identifiers, exponents, dimensions, digests, and membership metadata.
No payload requires `d_s^2` entries.
Serialization temporarily allocates its output file.
Parsing copies payload bytes into immutable members.
Peak memory can exceed the final file size.

Four-bit DistilGPT2 codes occupy 21,233,664 bytes for 42,467,328 indices.
DistilGPT2's 24 stage widths sum to 32,256.
At 32 retained tokens, factors occupy 8,257,536 bytes.
The combined raw payload is 29,491,200 bytes, about 28.13 MiB.
This arithmetic is a size calculation, not an empirical measurement.

The state discloses complete retained feature factors.
It is not a privacy-preserving representation of retained calibration records.
Storage, validation, load, and output costs belong in every method's cost accounting.

## API example

```python
from src.compact_state import (
    CompactState, RecordFactor, StageCodes, parse,
    prefix_digest, serialize, token_digest,
)

codes = StageCodes.from_array(
    stage_id, decoded_codes, grid_axis="row", bits=4,
    scale_exponents=row_exponents,
)
factor = RecordFactor.from_array(
    stage_id, record_id, token_major_features,
    prefix_sha256=prefix_digest(target_digest, preceding_stages),
    token_sha256=token_digest(tokens),
)
state = CompactState(target_digest, tuple(all_stages), tuple(all_factors))
data = serialize(state)
loaded = parse(data, expected_sha256=state.digest)
assert serialize(loaded) == data
```

## Validation scope

`tests/test_compact_state_v13.py` uses software fixtures only.
It covers both grid axes, all supported bit widths, packing boundaries, subnormals, and large finite scales.
It checks fresh/repair byte equality, deletion omission, the empty set, immutability, bounds, corruption, and stale prefixes.
These checks do not establish model quality, retained feature avoidance, or repair speed.
