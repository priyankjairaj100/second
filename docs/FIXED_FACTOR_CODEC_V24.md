# Packed source-local factor enclosures

This codec is a prerequisite for compressed evidence with exact model repair.
It does not implement a repair service.
It does not change the fixed-feature numerical target.
It supplies finite boxes for the existing universal dyadic certificate.
Certificate acceptance and complete request speed remain unmeasured.

## 1. Encoding contract

Encode each record-stage factor separately.
The token-major matrix is flattened in row-major order.
A fixed public block size partitions this ordered vector.
The supported signed cell widths are 16 and 24 bits.
Neither the partition nor precision uses aggregate calibration data.

For block $B$, define

\[
 t_B=\max_{x\in B,\,x\ne0}\lfloor\log_2|x|\rfloor,
 \qquad e_{B,b}=\max(t_B-(b-2),-1074).
\]

Use $t_B=-1074$ when every block entry is zero.
The implementation extracts these quantities from binary64 bits.
It never estimates them with floating-point logarithms.

For an ordinary entry, store

\[
 k=\left\lfloor x2^{-e_{B,b}}\right\rfloor.
\]

The implementation computes this integer through exact shifts and remainders.
Negative values use mathematical floor, not truncation toward zero.
The integer fits the declared signed width.
One flag distinguishes exact grid membership from a nonzero remainder.

The decoded interval is

\[
 I_b(x)=
 \begin{cases}
 \{k2^{e_{B,b}}\}, & x=k2^{e_{B,b}},\\
 [k2^{e_{B,b}},(k+1)2^{e_{B,b}}], & \text{otherwise}.
 \end{cases}
\]

Both endpoints are exactly representable finite binary64 values under the rules below.
The decoder constructs their bit patterns directly.
Endpoint construction uses no floating division, rounding adjustment, or native subnormal multiplication.

## 2. Overflow and subnormal rules

Let

\[
 G=(2^{15}-1)2^{1009}.
\]

The exact binary64 encoding of $G$ is `0x7fefffc000000000`.
Every value with $|x|>G$ uses an exact binary64 escape.
The escape rule is identical at both supported precisions.
This handles cells whose coarse upper magnitude could reach $2^{1024}$.

The common escape rule is essential for nested refinement.
A precision-dependent escape could give an exact coarse point and a wider fine interval.
Such a rule would violate the required nesting implication.

The step exponent never falls below $-1074$.
At that minimum step, every finite binary64 source value lies exactly on the grid.
Thus ordinary prepared subnormal entries need no underflow escape.
The decoder can also represent a defensive one-step interval at that scale.
Its finite midpoint is unavailable, so its symmetric enclosure uses the lower endpoint.

Positive and negative source zero both decode to the numeric singleton $\{0\}$.
Its endpoint uses positive-zero bits.
The original factor hash still distinguishes the original signed-zero bytes.
This policy preserves the exact rational feature interpretation used by the quantizer.
It does not promise recovery of every original feature bit from compressed evidence.

## 3. Containment theorem

**Claim.** Every descriptor produced by trusted encoding contains every original finite factor entry.

An escaped entry reconstructs its exact source bits.
An exact-grid entry reconstructs its exact dyadic value.
For every other entry, integer floor gives

\[
 k\le x2^{-e_{B,b}}<k+1.
\]

Multiplication by the positive exact scale establishes containment.
The chosen guard excludes finite endpoint overflow.
The minimum exponent and bounded integer width exclude unrepresentable dyadic endpoints.
Direct bit construction therefore preserves those exact mathematical bounds.

This claim depends on trusted encoding from the defining finite features.
An internally consistent checksum cannot establish that a hostile source supplied the correct features.

## 4. Nested refinement theorem

Fix the exact source matrix and block size.
Encode it separately at 16 and 24 bits.
Then every fine interval is contained in its corresponding coarse interval.

The block maximum and escape predicate are precision-independent.
Every escape therefore remains the same exact point.
For other entries, the fine exponent is no larger than the coarse exponent.
Their grid spacings differ by an integral power of two.
Thus every coarse cell is a union of fine cells.
Mathematical floor assigns the source value to a contained fine cell.
Every exact coarse grid point also belongs to the finer grid.
Its fine interval remains the same singleton.

The result concerns mathematical set inclusion.
It does not imply monotone acceptance by every numerical certificate implementation.
It also does not create missing precision bits from a coarse descriptor.
Refinement requires the original finite factors or trusted recomputation.
Any future service must charge that access and preserve canonical committed descriptors.

## 5. Centers and radii

`descriptor.box()` returns token-major finite endpoints.
Transpose these endpoints before calling the width-by-token dyadic certificate.

`descriptor.center_radius()` returns immutable finite arrays $C,E$ satisfying

\[
 |X-C|\le E.
\]

An exact point has radius zero.
An ordinary cell uses its exact midpoint and half-step radius when representable.
At the smallest subnormal step, the lower endpoint and full-step radius give a safe enclosure.
The direct interval remains at least as tight as this symmetric enclosure.
All center and radius bit patterns are constructed exactly.

These arrays support the separate metric perturbation theory.
They do not certify quantized model codes by themselves.

## 6. Actual packed storage

The file contains a canonical JSON header and binary block payloads.
Each block stores these items in order:

- A signed 16-bit exponent.
- Two flag bits for each entry.
- One signed 16-bit or 24-bit cell integer for each entry.
- One binary64 value for each exact escape.

An escaped entry uses the canonical integer zero.
Reserved flags and nonzero padding bits are rejected.
The decoder rejects unnecessary exact escapes.

For block counts $n_j$ and total escape count $s$, payload size is

\[
 \sum_j\left(2+\left\lceil\frac{n_j}{4}\right\rceil+
 \frac{b}{8}n_j\right)+8s\quad\text{bytes}.
\]

Header bytes are additional and fully charged.
This is actual packed storage, not a compressed-size estimate from floating arrays.
Many escapes can make the descriptor larger than exact factor storage.
No uniform storage-saving theorem follows for all finite inputs.

The header binds both numerical targets, record ID, token digest, stage ID, dimensions, settings, and codec source.
It also binds original factor bytes and compressed payload bytes.
The parser accepts explicit limits before allocating decoded arrays.
It checks payload lengths, hashes, finite endpoints, flags, canonical metadata, and trailing bytes.
Whole-descriptor authentication requires a trusted expected digest.

Parsing checks structural canonical serialization.
It cannot prove that a descriptor is the unique encoder output for an unseen source matrix.
For example, altered exponents or flags can describe different valid cells.
The source hash alone does not establish containment.
The caller must verify trusted preparation, expected source bindings, and the supported current codec binding.
The archive audit performs those checks against the saved exact factors.

## 7. Software verification

Eight focused tests passed.
They cover every finite binary64 exponent class with signed mantissa edge cases.
They cover 131,072 positive and negative low-subnormal bit patterns.
They compare integer floor and endpoint encodings with exact rational arithmetic.
They check nested precision, overflow escapes, signed-zero policy, and center-radius containment.
They also check real packing, immutable arrays, parser limits, corruption, and invalid settings.

These are arithmetic software fixtures.
They are not empirical datasets or evidence of repair speed.
The real archive compression audit must run separately from active timing workers.

## 8. Remaining integration

A future service must retain only source-local descriptors after deletion.
It must certify the exact fixed-feature output over their concatenated boxes.
It must regenerate unresolved retained factors under a bounded policy.
It must charge rejected certificates, source replay, storage, and disposal.
Its equally indexed comparator must receive the same descriptors and optimization.

This component implements none of those service transitions.
It does not establish novelty for block quantization or interval arithmetic.
The prospective contribution remains the measured storage, margin, and fallback tradeoff for exact calibration-data removal.

## 9. Saved-factor compression audit

The audit used the completed revision 23 preparation and first repair states.
It loaded no model checkpoint and evaluated no model.
Both original records supplied 48 source-stage factors.
The retained record supplied another 24 factors.
Both precisions were encoded for every factor, giving 144 descriptors.

All finite endpoint containment checks passed.
Another 36,288 selected checks used exact rational comparisons.
All 16-to-24-bit interval inclusions passed.
All descriptors survived canonical roundtrip checks.
All 48 surviving descriptors matched their original-corpus encodings byte-for-byte.
No entry required an exact escape.

The audit verified trusted state hashes and completed worker receipts.
It also verified plans, frozen sources, model artifacts, and the current preparer binding.
Every descriptor matched its exact source bytes and current codec binding.

Actual factor and descriptor sizes are:

| Representation | Original two records | Retained record |
|---|---:|---:|
| Exact factor payload | 8,257,536 bytes | 4,128,768 bytes |
| 16-bit packed payload | 2,330,496 bytes | 1,165,248 bytes |
| 16-bit complete descriptors | 2,369,388 bytes | 1,184,682 bytes |
| 24-bit packed payload | 3,362,688 bytes | 1,681,344 bytes |
| 24-bit complete descriptors | 3,401,580 bytes | 1,700,778 bytes |
| Zlib level 6 payload | 7,864,537 bytes | 3,934,494 bytes |
| Zlib payload plus factor bindings | 7,895,701 bytes | 3,950,064 bytes |

Zlib compresses each identical source-stage byte string separately.
Its roundtrip restored every exact source byte.
The audit field `lossless_roundtrip` refers only to this zlib comparison.
The field `canonical_roundtrip` refers to descriptor serialization.
It does not mean that interval descriptors reconstruct exact source factors.
Its bound descriptor accounts for dimensions, target, source, record, token, stage, and codec metadata.
It retains more information than the interval descriptors.
The interval descriptors require a future certificate or exact fallback to recover target model codes.

Complete state projections include the 22,192,646-byte model artifact.
They also include all descriptor headers, a canonical record index with tokens, and 16 framing bytes.

| Complete state accounting | Original two records | Retained record |
|---|---:|---:|
| Actual exact-factor state | 30,458,753 bytes | 26,326,066 bytes |
| Projected 16-bit state | 24,569,232 bytes | 23,381,328 bytes |
| Projected 24-bit state | 25,601,424 bytes | 23,897,424 bytes |
| Projected bound zlib state | 30,095,548 bytes | 26,146,713 bytes |

These complete compressed states are accounting projections.
No compressed service format or repair transition exists yet.
The model artifact limits the complete-state saving despite substantial factor compression.
For the retained record, the 16-bit projection saves 11.19 percent of complete state bytes.
The 24-bit projection saves 9.23 percent.
This is not a latency result.

Run `python scripts/analyze_fixed_codec_v24.py` to reproduce the archive audit.
The report is `campaigns/fixed_feature_v23/codec-audit-v24.json`.
The analysis used 19.741 CPU seconds and 19.831 wall seconds.
Those costs remain separate from empirical worker ledgers.
An initial archive-path error stopped before compression.
Its report remains in `codec-audit-v24-incomplete-001.json` beside the completed audit.
