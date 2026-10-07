# Repair integration audit, revision 12

The compact solver can establish exact model codes from supplied retained features.
It does not yet establish a complete repair transaction.
Full-model quantization pilots cannot close the repair, state, quality, or lifetime gates alone.

This audit inspected the current service implementations.
It introduces no empirical result or speedup claim.

## 1. Distinct output contracts

| Method | Required output | Additional required work |
|---|---|---|
| `model_only_fresh` | Complete retained model | Evaluate retained features under each new certified prefix. |
| `repair` | Complete model and canonical retained state | Validate prior state, remove contributions, verify proposals, replay failures, and commit updated state. |
| `indexed_fresh` | Complete model and canonical retained state | Receive the same valid summaries and solve with the same compatible improvements. |
| `direct_fresh` | Complete model and canonical retained state | Reconstruct retained summaries independently and run the retained target directly. |

Common model-code equality is necessary across all four methods.
Canonical state equality is also necessary within each declared service family and response tier.
A compact model archive does not substitute for canonical retained state.

The current aggregate `repair` and `indexed_fresh` methods share `_solve`.
That solver does not access the old model.
Any deletion-only solver advantage therefore needs new evidence or a different algorithm.

## 2. Confirmed implementation blockers

### A. Existing service types still require exact dense objects

`StageSpec` stores exact weight matrices and grids.
`StageOutput` stores exact code matrices.
The service reads and serializes these objects through the existing rational schema.
A read-only binary64 code array cannot directly replace `StageOutput`.
Its exact grid values need a compatible adapter or a new declared schema.

The compact model path and the complete service need the same target binding.
Their encoder changes must not silently change fixed grids, stage order, or normalization.

### B. Fresh paths still construct dense Grams

`AggregateRepairService.fresh` evaluates retained features and calls `_gram` for each record.
`IdentityCacheService.fresh` does the same.
Their `_quantize` methods still call the dense `sequential_oracle`.

Replacing the final solver alone cannot recover token factors from an arbitrary stored Gram cheaply.
The feature-producing path must preserve a valid factor representation before it discards the features.
An exact factorization of a dense rational Gram can itself remain expensive.

### C. The committed aggregate state is dense

`LinearResponseIndex` stores one constant Gram and one cross-response matrix per direction.
It also stores a small scalar matrix for tangent energy.
For response rank $r$, each stage therefore stores approximately $(r+1)d^2+r^2$ rational entries per group.

`ResponseIndex` stores every required affine-feature cross-moment.
Its quadratic tier uses approximately $(r+1)(r+2)d^2/2$ entries per stage and group.
Scalar error moments add further entries.

For six GPT-2 blocks with width 768, the total stage Gram count is

\[
6\left(3\cdot768^2+3072^2\right)=67,239,936.
\]

This is a scalar-slot count for one group and rank zero.
It is not a measured memory requirement.
Multiple groups and nonzero response rank increase this count.

`_empty`, `_add`, `_validate`, `_proposal`, and `_finish` all touch these dense representations.
Deleting contributions still performs exact matrix subtraction.
Several validation paths perform exact PSD checks.
The compact token solver does not remove these operations.

### D. Proof extraction still uses scalar rational jets

`AutomaticResponseProvider.feature_jets` creates `Jet` objects for parameter values and intermediate activations.
Each jet contains a value, a gradient, and a Hessian over the global chart rank.
Extraction evaluates both center jets and region jets.
It then constructs dense response moments and finite-error descriptors.

The accelerated finite linear kernel explicitly rejects jets.
Finite-feature acceleration therefore does not accelerate these proof computations.

The source-independent theorem does not require this particular dense implementation.
The current implementation does require it.
A new compact or tensor proof implementation needs its own arithmetic validation.

The rank-zero box provider avoids nonzero derivative arrays.
It still runs interval jet arithmetic for nontrivial parameter boxes.
Its resulting anchor Gram remains dense.
A box covering every grid value can also produce loose bounds.
No present measurement establishes useful coverage for these full-model boxes.

### E. The new residual certificate has a narrower purpose

`certified_token_codes` certifies quantization for an explicitly supplied exact feature factor.
Its residual bounds cover numerical coefficient errors.
They do not bound feature changes caused by changed ancestor codes.

The aggregate service separately proves a relation between surrogate and true Grams.
Its spectral route uses exact candidate pivots, decision inputs, and prefix energies.
Its interval route processes a dense Gram enclosure.
The compact result currently returns codes and solver diagnostics, not those complete transport witnesses.

A low-rank candidate solve cannot replace the transport certificate without another proved bound.
The shifted linear proposal also contains a diagonal correction.
Its cross-response representation cannot automatically be passed as an ordinary feature Gram.
A structured generalized-metric solver would need an explicit derivation and certificate.

### F. Serialization remains part of the complete cost

`AggregateState.canonical_bytes` constructs nested JSON containing model codes and aggregate matrices.
The moment encoders also construct rational lists and embedded JSON strings.
Hashing and committing can materialize these large byte strings repeatedly.

`_commit_state` writes separate complete state and model artifacts.
Detailed diagnostics can parse the state again.
The parser has explicit limits for bytes, rational entries, widths, and integer digits.
These operations and limits remain relevant after compact model quantization succeeds.

### G. A narrow obstruction from the existing state encoding

The existing monolithic state artifact has a provable size obstruction under specific assumptions.
This obstruction does not prove that compact repair is impossible.

Assume all six DistilGPT2 blocks use the four declared quantized stages.
Assume at least one retained group represents response matrices for every stage.
Assume the state uses the existing dense rational-pair encoding.
Assume the worker writes that canonical state as one uncompressed regular file.

The stages contain

\[
P=6(3+1+4+4)768^2=42,467,328
\]

model code entries.
The fully represented rank-zero response matrices contain

\[
G=6(3\cdot768^2+3072^2)=67,239,936
\]

Gram entries in one group.
Higher response ranks contain at least these entries.
Additional represented groups add further entries.

`repair_service._q_json` and `response_moments._encoded_matrix` encode each rational as `[numerator,denominator]`.
The numerator needs at least one byte.
The positive denominator needs at least one byte.
The brackets and internal comma need three more bytes.
Therefore each rational requires at least five bytes.

`StageOutput._json` includes every model code entry.
`LinearResponseIndex.canonical_bytes` includes every constant Gram entry.
The quadratic response schema also includes this constant Gram.
Embedding moment JSON inside a JSON string cannot shorten these ASCII pairs.
Its escaping and surrounding metadata only add bytes.

Consequently,

\[
\begin{aligned}
|\mathrm{state}| &\ge 5(P+G)\\
&=548,536,320\ \mathrm{bytes}\\
&=523.125\ \mathrm{MiB}\\
&>512\ \mathrm{MiB}.
\end{aligned}
\]

This lower bound ignores inter-entry commas, rows, metadata, error moments, and longer integers.
It therefore holds even when every represented Gram entry is zero.
Streaming the same bytes cannot remove this file-size obstruction.
The current single-file commit cannot satisfy a 512 MiB `RLIMIT_FSIZE` under these assumptions.

The qualifications matter:

- An absent stage contract can produce `response=None`; that stage does not contribute the assumed Gram count.
- An unavailable extraction does not necessarily remove a matrix.
- With an existing contract, `_empty` still creates dense zero matrices, and failures increment `unavailable_count`.
- Thus unavailable contributions alone do not invalidate the bound when every stage retains its matrix representation.
- An empty retained set can remove aggregate groups, so this response-state count need not apply.
- Selective stage contracts require a new count using only represented matrices.
- The present identity-cache schema independently stores one dense Gram per stage and every model code.
- It therefore has the same numerical lower bound when those matrices are present.
- A factorized identity cache or another compact family can avoid this dense-entry count.
- Packed codes, compressed transport, or multiple files can also avoid this particular single-file obstruction.

Those alternatives require declared encodings, validation, loading, and complete cost accounting.
They cannot be presented as the unchanged current artifact interface.
The bound concerns encoded output size, not an unavoidable memory requirement or universal computational lower bound.

## 3. Two integration routes

### Route A: preserve the existing canonical schema

Implement lazy exact matrix views and bounded serialization first.
Preserve the existing canonical bytes exactly when comparing historical state digests.
Streaming must preserve ordering, punctuation, integer encoding, and nested-string escaping.
Bind any change to target identity or service identity explicitly.

This route can reduce temporary memory.
It cannot eliminate the amount of dense output required by the schema.
It also cannot eliminate scalar jet extraction or dense transport verification by itself.

### Route B: declare a new compact service family

Define a canonical factor representation and packed code encoding.
Specify ordering, normalization, grid identity, record membership, and exact content hashes.
Prove that decoding represents the same rational target and required retained summaries.

A concatenation of record feature factors can represent a Gram exactly.
However, retaining these factors changes the existing aggregate-only storage contract.
Its size depends on retained tokens and possibly response rank.
It can also require retained-factor scans during a query.
These costs must enter the new theorem statement and every baseline.

Factorization nonuniqueness creates a separate canonicalization problem.
Incremental downdates must produce the same declared bytes as a fresh retained construction.
A deterministic record-and-token order can help, but it changes the state design.
It does not justify silently calling the result an existing aggregate state.

A new identity-cache family is simpler than the full response family.
It can reuse a factor only when all relevant ancestor codes agree.
It must replay retained features after a changed ancestor.
It therefore cannot establish changed-ancestor feature avoidance by itself.

## 4. Required next steps

1. Complete the bounded real model-code pilot under the new source and runtime binding.
2. Compare its codes with the declared target wherever an independent reference is practical.
3. Freeze a complete service representation before starting repair timing.
4. Implement identical compact solver access for all compatible methods.
5. Connect retained replay to feature factors without changing the finite neural program.
6. Resolve aggregate storage, exact deletion updates, validation, and canonical serialization.
7. Implement a structured transport certificate or retain and measure the existing complete verifier.
8. Validate one complete repair against an independently constructed retained model and state.
9. Validate repeated deletion against combined deletion under the same state schema.
10. Run the four-method pilot with loading, setup, verification, replay, output, and cleanup charged.
11. Measure changed-ancestor avoidance with the frozen denominator.
12. Measure heldout quality before applying the feasibility promotion rule.

Each failed or unresolved step remains in the evidence register.
A complete-model quantization result must retain its narrower label until these steps pass.

## 5. Acceptance evidence

The next complete repair report must contain:

- The numerical target and service-schema identity.
- The original and retained membership hashes.
- Exact model agreement across the four methods.
- Exact canonical state agreement within the declared family.
- Sequence-versus-combined state agreement.
- Certificate acceptance, replay, and changed-ancestor coverage counts.
- Complete preparation and request times, including failures.
- Peak memory, state bytes, model bytes, and exact-fallback counts.
- Heldout token counts and quality measurements.
- Every planned run, including failed and unstarted runs.

This audit does not authorize changing frozen scientific gates retrospectively.
New implementations require prospective bindings and appropriate resource policies.
