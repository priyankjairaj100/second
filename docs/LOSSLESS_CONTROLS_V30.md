# Stronger lossless controls

Revision 30 adds standard Zstandard and official FPC controls.
It checks saved real calibration factors from the existing WikiText request.
It does not execute a model, a quantizer, or a repair service.

Byte-shuffled zlib remains the smallest tested lossless control on every factor.
The new controls therefore do not remove the earlier storage advantage for 40-bit enclosures.
This result does not establish optimal lossless compression.
Official ALP remains unmeasured because its supported compiler is absent.

## Methods and access

Each codec receives one source-stage factor at a time.
Each factor contains the same original little-endian binary64 words.
No codec can combine factors, share a learned dictionary, or inspect another source.
Every original factor has a separate descriptor.
Retained descriptors must remain identical after deletion.

The registered methods are:

| Method | Settings |
|---|---|
| Raw | Exact bytes without compression. |
| Zlib | Level six, default strategy. |
| Shuffled zlib | Eight byte planes, then level six. |
| Zstandard | Levels three and nine, each measured separately. |
| Shuffled Zstandard | Eight byte planes, then each registered level. |
| FPC | Official version 1.1, levels eight and twenty. |

Zstandard uses one thread, a content checksum, and a declared content size.
It does not use a dictionary.
The installed package is python-zstandard 0.25.0, with Zstandard 1.5.7.
The runtime manifest binds the extension binary.

The official FPC source arrived with an email Subject header.
Setup removed that header and added a dated change notice.
It changed no algorithm statement.
The setup used the official recommended command, `gcc -O3 fpc.c -o fpc`.
Its original license notice remains in the compiled source.
The repository stores source URLs, hashes, compiler details, and setup instructions.
It does not redistribute the vendor source or executable.

FPC starts a separate bounded process for each operation.
Each process permits two CPU seconds and five wall seconds.
Its address limit is 256 MiB.
Its output file also has a byte limit.
These process costs prevent direct throughput comparisons with in-process Python extensions.
All child CPU costs appear in the archive report.

## Exactness and canonical validation

The new module is `src/lossless_controls_v30.py`.
It leaves all V29 sources and service behavior unchanged.

The descriptor binds the source, target, record, tokens, stage, shape, method, and runtime.
It also binds decoded bytes and compressed bytes with separate hashes.
Parsing decodes the bytes and then repeats the registered encoding.
The resulting descriptor must match the input exactly.

The transforms preserve every original bit, including signed zeros and finite subnormal values.
The pipeline rejects nonfinite values before encoding and after decoding.
No arithmetic conversion or quantization occurs.

The parser rejects duplicate keys, changed hashes, invalid dimensions, and noncanonical metadata.
It rejects extra Zstandard frames, trailing bytes, missing checksums, and unexpected content sizes.
It bounds decoded factors at 128 MiB.
FPC decoding runs inside the separate process limits.
Canonical recompression rejects alternative FPC encodings, including accepted trailing data.

Hash binding does not establish that a neural model produced the source bytes.
That premise still comes from trusted archived preparation.
Runtime hashes assume trusted local storage.
They do not establish protection against hostile executable replacement during use.

## Archive results

The audit verifies both original and retained states from revision 23.
It checks their preparation plans, original receipts, model hashes, and complete state hashes.
It checks 48 original factors and 24 retained factors.
Across nine controls, all 648 descriptor checks pass.
All 216 retained descriptor pairs remain identical.

The retained factors contain 4,128,768 raw bytes.

| Control | Retained payload bytes | Projected complete state bytes |
|---|---:|---:|
| Raw | 4,128,768 | 26,342,581 |
| Zlib six | 3,934,494 | 26,148,357 |
| Shuffled zlib six | **3,618,476** | **25,832,539** |
| Zstandard three | 3,919,245 | 26,133,108 |
| Shuffled Zstandard three | 3,684,208 | 25,898,271 |
| Zstandard nine | 3,918,207 | 26,132,070 |
| Shuffled Zstandard nine | 3,670,499 | 25,884,562 |
| FPC eight | 3,958,617 | 26,172,455 |
| FPC twenty | 4,048,935 | 26,262,798 |

The source-local selector chooses shuffled zlib for all 48 original factors and all 24 retained factors.
Its retained projection occupies 25,832,540 bytes.
The one-byte difference comes from its index label.

Payload totals exclude descriptors, indexing, tokens, and model codes.
Complete projections include those costs through a declared canonical accounting envelope.
The common base checkpoint remains required and excluded.
These projections are not implemented service artifacts or deployment totals.

The actual V29 retained lossless state occupies 25,832,592 bytes.
The new shuffled-zlib projection differs slightly because its metadata format differs.
Use the actual V29 state for the existing complete-service comparison.
Its 40-bit counterpart occupies 24,930,099 bytes.
That retains the previously measured 3.4936% complete-state saving against the actual lossless state.
No new latency claim follows from this archive comparison.

FPC twenty produces larger output than FPC eight on this request.
Zstandard nine improves on Zstandard three but does not beat shuffled zlib.
These adverse observations remain in the complete report.

## Costs and evidence

The archive analysis used 11.801764519 combined CPU seconds.
Parent work used 8.281878519 seconds.
Child codecs used 3.519886 seconds.
Wall time was 12.368321814 seconds.
The clocks exclude final report serialization and writing.
Nested per-factor clocks include encoding, decoding, hashes, and canonical recompression.
They are diagnostic clocks, not matched throughput benchmarks.

The separately recorded FPC setup used 0.883839389 combined CPU seconds.
Its wall time was 19.68768666 seconds, including source retrieval.
Software verification has a separate receipt.
All nine software fixtures pass with the official FPC executable enabled.
These costs remain outside empirical worker ledgers.
No old empirical allowance was reset or charged by this archive audit.

Read these files for exact evidence:

- `campaigns/lossless_controls_v30/plan.json`
- `campaigns/lossless_controls_v30/summary.json`
- `campaigns/lossless_controls_v30/fpc_setup.json`
- `campaigns/lossless_controls_v30/software_check.json`

The campaign preserves every bound analysis source.

## ALP status

The checked official ALP commit is `31ca0ed11c93c99d3f5b5c30e01a3e1c3832d3ce`.
Its CMake configuration requires Clang.
No `clang++` executable is available on the current PATH.
We did not replace its algorithm or report a home-built approximation as ALP.

Its supported build and source-local adapter remain open tasks.
The adapter must preserve all binary64 bits and include its vector and group metadata.
It must reset compression state at source boundaries.
It must include preparation, decoding, validation, and complete storage costs.
It must check signed zeros before any full service comparison.

## Reproduce

Use Python with NumPy and python-zstandard 0.25.0.
The commands require the archived V23 binary states and model artifacts.
Those large artifacts remain outside Git.
The existing preparation protocol can reconstruct them.

```bash
python scripts/analyze_lossless_controls_v30.py --prepare-fpc /tmp/fpc-v30
git clone https://github.com/cwida/ALP.git /tmp/alp-v30
git -C /tmp/alp-v30 checkout 31ca0ed11c93c99d3f5b5c30e01a3e1c3832d3ce
python scripts/analyze_lossless_controls_v30.py \
  --fpc-dir /tmp/fpc-v30 --alp-dir /tmp/alp-v30 \
  --output-dir campaigns/lossless_controls_v30_reproduction
V30_FPC_BINARY=/tmp/fpc-v30/fpc python -m unittest discover \
  -s tests -p test_lossless_controls_v30.py -v
```

The script records an availability change if Clang exists.
Review that change and implement ALP before treating the missing-control gate as closed.

## Primary references

The official [FPC page](https://userweb.cs.txstate.edu/~burtscher/research/FPC/) documents version 1.1 and its table-size parameter.
The [FPC license](https://userweb.cs.txstate.edu/~burtscher/research/FPC/FPClicense.pdf) supplies the research-use terms.

The official [ALP repository](https://github.com/cwida/ALP) supplies the algorithm and benchmark implementation.
Its [benchmark guide](https://github.com/cwida/ALP/blob/main/how_to_benchmark_your_dataset.md) describes vectors and row groups.
Its [pinned build file](https://github.com/cwida/ALP/blob/31ca0ed11c93c99d3f5b5c30e01a3e1c3832d3ce/CMakeLists.txt) requires Clang.

The python-zstandard [compression documentation](https://python-zstandard.readthedocs.io/en/latest/compressor.html) defines the parameters.
Its [decompression documentation](https://python-zstandard.readthedocs.io/en/latest/decompressor.html) defines frame handling.

This report makes no compression priority claim.
The remaining research question concerns exact quantized outputs from smaller, incomplete numerical evidence.
