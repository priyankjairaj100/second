# Exact factor compression baseline

Revision 29 adds a source-local lossless factor codec.
It preserves every binary64 source bit, including signed zeros.
It changes storage only.
The defining calibration factors and quantized model target remain unchanged.

The codec supplies a stronger baseline for compressed enclosure states.
Lossless factors support the existing exact point solver directly.
They do not need interval output certification.
This is established compression machinery, not a standalone novelty claim.
The baseline does not establish optimal lossless compression.

## Deterministic representation

`src/fixed_lossless_codec_v29.py` exposes `LosslessFactorDescriptor` and `encode_factor`.
It also exposes `serialize`, `parse`, `LoadLimits`, `codec_manifest`, and `codec_binding`.
The descriptor provides `binary64()`, `array()`, and `digest`.
`array()` returns an immutable token-major binary64 matrix.

The encoder evaluates three modes for each source-stage factor:

| Mode | Payload |
|---|---|
| 0 | Original little-endian binary64 bytes. |
| 1 | Zlib compression of those bytes. |
| 2 | Zlib compression after separation into eight byte planes. |

Byte shuffling is a reversible permutation.
It places all first bytes together, then all second bytes, and so forth.
The inverse permutation restores every original byte.
No arithmetic rounding occurs.

Zlib uses level six, window bits fifteen, memory level eight, and the default strategy.
The encoder minimizes complete descriptor size.
Ties select the smaller mode number.
All other fields have equal serialized widths across candidate modes.
Therefore, payload length plus its decimal length determines the size ordering.

Each choice uses only one factor and its source metadata.
Deleting other sources cannot change its encoded bytes under the same runtime.
The codec version uses separate magic and schema identifiers.
Previous codec versions remain unchanged.

## Binding and exactness

The descriptor binds target, anchor target, record, tokens, stage, and shape.
It also binds the exact source hash and the codec hash.
The codec hash covers source files, compressor versions, parameters, and the available runtime binary.
For an extension module, that binary is the zlib extension.
For a built-in module, that binary is the Python executable.
The manifest records the runtime kind explicitly.

Byte canonicality applies to the bound encoder and compressor runtime.
It does not promise identical compressed streams across different runtime builds.
Dynamic compressor dependencies also require the enclosing program's runtime record.
Public construction and parsing require the current codec binding.

The process caches at most four runtime binary hashes.
Each key binds resolved path, device, inode, size, modification time, and change time.
Fresh reads and cache hits require matching identities before and after access.
An identity change invalidates reuse.
This avoids repeatedly hashing the 30.9 MB built-in interpreter for every descriptor.
Metadata identity assumes a trusted filesystem.
It does not authenticate hostile storage or prove unchanged content against forged metadata.
Codec source files still receive fresh hashes on each binding request.

For trusted source bytes \(B\), encoding and decoding satisfy

\[
\operatorname{decode}(\operatorname{encode}(B))=B.
\]

Mode zero copies the bytes.
Mode one applies lossless zlib encoding and its inverse.
Mode two composes those maps with a reversible byte permutation.
Mode selection does not affect the equality.

The decoder checks the complete decoded source hash.
It also checks finite binary64 values.
This establishes exact content binding.
It does not prove that the declared calibration pipeline produced those bytes.
Trusted preparation remains necessary for that claim.

## Bounds and canonical validation

The parser bounds input bytes, header bytes, tokens, width, and decoded values.
A hard 128 MiB ceiling also applies to each decoded factor.
That ceiling protects direct descriptor construction.

Zlib decoding permits at most the expected byte count plus one detection byte.
The decoder rejects excess output, missing stream termination, trailing bytes, and concatenated streams.
It verifies exact length before byte unshuffling.
Thus, malformed compressed input cannot request unbounded decoded output through this interface.
This bound does not represent a complete process memory limit.

Metadata uses canonical JSON and rejects duplicate keys.
Public construction and parsing also recompress decoded data.
They reject noncanonical mode choices and alternative compressed streams.
Fresh encoding uses a private trusted path after canonical selection.
It avoids a second compression pass while retaining all metadata checks.

`binary64()` decodes and verifies source bytes without recompression.
The state parser and service must account for every actual validation and decode pass.
Canonical descriptor reuse does not remove those costs.

## Archive probe

The archive probe used validated original and retained exact states from revision 23.
It performed no neural inference, quantization, or service timing.
It consumed 5.01 process CPU seconds outside the empirical worker ledger.
Its report is `campaigns/lossless_probe_v29/summary.json`.

For retained factors, raw bytes total 4,128,768.
Raw zlib uses 3,934,494 payload bytes.
Byte-shuffled zlib uses 3,618,476 payload bytes.
These figures exclude descriptor and complete state overhead.
The shuffled payload reduction is 12.36%.
It remains larger than the 40-bit enclosure payload.

No retained 256-value block had a conservative exact signed width below 57 bits.
Shared exact dyadic packing therefore lacks a clear advantage for these blocks.
This observation does not rule out other lossless transforms.

The code fixtures check finite exponent classes, exact source bytes, and every selected mode.
They check malformed streams, bounded decompression, canonical choices, parser bounds, and provenance fields.
They are software fixtures only.
Actual complete state sizes and full repair costs require separate measurements.
