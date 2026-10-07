# Exact dyadic row grids in compact state

Revision 15 extends `StageCodes` with the explicit `dyadic_row` grid axis.
This change supports the separately declared dyadic row quantization target.
It does not change any existing power-of-two state bytes.

## Interface and encoding

```python
codes = StageCodes.from_array(
    stage_id, decoded_codes, grid_axis="dyadic_row", bits=4,
    scale_values=tuple(row_scales),
)
```

`scale_values` contains one positive finite Python float per output row.
`scale_exponents` must be empty for this axis.
Existing `row` and `column` grids require empty `scale_values`.
The existing constructor's positional fields remain unchanged.
The new optional field follows `packed_indices`.

Dyadic metadata uses `scale_values_hex` instead of `scale_exponents`.
Every string must equal Python's canonical `float.hex()` representation.
The parser rejects alternative spellings and extra scale fields.
Old power-of-two metadata remains unchanged.
The file family remains `factor_identity_v1` because factors and membership semantics remain unchanged.
An older parser rejects the new grid axis.

## Exact grid validation

Write each positive scale uniquely as `n * 2^e`, with odd positive integer `n`.
Let `h = 2^(b-1)` for bit width `b`.
The constructor requires:

\[
e\ge -1073,\qquad
\operatorname{bitlength}(n(2h-1))\le53,\qquad
e+\operatorname{bitlength}(n)+b-2\le1023.
\]

The first condition makes the smallest half-step representable without underflow.
The second bounds every odd midpoint significand.
It also bounds every code significand after removing powers of two.
The third bounds the largest code magnitude, `h * scale`.
Together, these conditions make every grid code and half-step midpoint an exact finite binary64 value.

Grid codes are `[-h, ..., h-1] * scale`.
Half-step midpoints are `[-h+1/2, ..., h-3/2] * scale`.
The constructor validates these properties independently of the target's scale-selection algorithm.
The service must separately verify that the supplied scales match its declared target.

## No rounded scale division

The state factory never divides a value by its dyadic scale.
It constructs each grid value's binary64 encoding with integer operations.
It then locates input encodings through integer comparisons.
Any unmatched encoding causes rejection.
Negative zero maps to the unique rational-zero index.

Decoding also uses integer grid encodings and index lookup.
It performs no floating scale multiplication.
This preserves subnormal code encodings without arithmetic underflow.
The returned matrix uses immutable little-endian bytes.

## State semantics and validation

Prefix digests include the dyadic metadata and packed indices.
Factors still require exact current-prefix bindings.
Membership, deletion omission, empty-set behavior, and canonical state equality remain unchanged.
Storage still uses `b` bits per code plus row-scale metadata.

Software checks cover all supported bit widths and every code at representative scales.
They include subnormal scales, large finite scales, invalid midpoints, alternate encodings, and off-grid neighbors.
A fixed V13 fixture retains its original 1,963-byte serialization and SHA-256 digest.
These are software checks, not quality or speed experiments.

Existing V13 model states also passed read-only parse/serialize checks.
Both complete files retained their original bytes.

| State | Bytes | Unchanged SHA-256 |
|---|---:|---|
| `pilots/v13/attempt-002/outputs/state.bin` | 29,638,144 | `f1065b1583194c3a93a1b8033e762e80bdf9f4a57287b9d2c74a4f3dbf29514d` |
| `pilots/v13/attempt-003/outputs/state.bin` | 25,500,538 | `85e91a893b978b3a5cde6cd0cc59cd3e534f6286b9dd7e884a0c76b71ed96e05` |
