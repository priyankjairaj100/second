# Revision 16: exact speculative quantizer repair

Updated 7 October 2026. This document separates implementation guarantees from empirical hypotheses.

The completed CPU pilots were negative.
Read EMPIRICAL_PILOT_V16.md before using either backend.
The following design does not recommend production activation.

## Design rationale

Optimize the quantizer while retaining exact current factors.
Do not make factor avoidance a prerequisite for every possible speed advantage.
Count quantizer savings separately from neural feature savings.

The current state contract already permits this change.
Each stage still receives its exact retained factors.
Its output remains the same exact dyadic-grid model.
The complete state still contains exact current factors and exact model codes.
The candidate is temporary information, and does not enter the committed state.

The implementation lives in `src/speculative_dyadic_solver.py`.
The proof appears in `docs/SPECULATIVE_QUANTIZER_PROOF_V16.md`.
The fixed-point formulation and parallel scheduling already have substantial prior literature.
Read `docs/NOVELTY_AUDIT_V16.md` before describing any contribution as novel.

## Evidence and remaining uncertainty

Revision 15 stage times combine factor extraction, quantization, and state construction.
They do not identify the main cost by themselves.
Revision 14 records quantizer regions that include code-file output.
Those regions sum to 206.887 seconds within a 255.073-second worker.
That measurement motivates a quantizer experiment.
It does not measure solver time alone.

The earlier deletion changed many individual codes.
A small global change fraction does not imply unchanged complete output rows.
Therefore, the solver can retain verified prefixes when complete rows fail verification.
No measured speed advantage follows from the implementation alone.

## Exact target

Let W have p output rows and d input coordinates.
Let Z contain T retained tokens, with row z_i at coordinate i.
Set beta to the fixed ridge times the fixed original normalization.
Define

\[
G_i=\beta I+\sum_{h\ge i}z_hz_h^\top,
\qquad u_i=G_i^{-1}z_i.
\]

For a grid-valued candidate Q, define

\[
S_{a,i}(Q)=\sum_{h<i}z_h(W_{ah}-Q_{ah}),
\qquad
F(Q)_{a,i}=\operatorname{Round}_a
\bigl(W_{ai}+u_i^\top S_{a,i}(Q)\bigr).
\]

Each rounding cell keeps the existing lower-code tie rule.
The target satisfies Q=F(Q).
The triangular dependency gives a unique fixed point.
Coordinate zero has no earlier-code dependency.
Once coordinates below i agree, coordinate i is uniquely determined.

Thus, a verified fixed point equals exact sequential quantization.
An unverified numerical iteration does not establish a fixed point.

## Directed parallel prefix scan

The solver first encloses each product z_h(W_ah-Q_ah).
It uses the existing directed subtraction and multiplication helpers.
It then computes exclusive prefix intervals with a Blelloch scan.
The scan pads its input with exact zeros.
Its upward pass encloses subtree sums.
Its downward pass encloses each preceding subtree sum.
Every addition uses the existing directed interval helper.
Every intermediate endpoint must remain finite.
Advanced indexing preserves subtree copies before assignments.

This method avoids assumptions about NumPy reduction order.
It also avoids a new relative-error formula for subnormal sums.
Signed zeros denote the same rational factor value.

The coefficient solver remains unchanged.
It provides an approximate coefficient and a certified squared error.
The cell test combines that error with the prefix interval norm.
It retains strict lower endpoints and inclusive upper endpoints.

## Candidate updates and prefix continuation

Fresh quantization starts from ordinary nearest-grid codes.
Repair can start from prior model codes on the same fixed grids.
Both callers use the same scan, certificate, limits, and fallback.

Each speculative pass evaluates all candidate decisions in a batch.
A row passes only when every cell is certified and every proposed code agrees.
That row requires no sequential continuation.

A failed row can still have a certified prefix.
Let k be its first uncertified or changed decision.
The candidate coordinates below k equal the exact target by induction.
The exclusive scan interval at k encloses their exact accumulated residual.
The solver saves those codes and that interval.
Later proposals preserve those proved codes.

After the fixed pass limit, sequential continuation starts at each row's saved k.
Only active suffix rows advance at each coordinate.
Exact fallback receives the saved codes before it evaluates any earlier-code sum.
Thus, interval ambiguity affects work, without changing accepted results.

No finite convergence claim applies to approximate candidate updates.
A fixed pass limit prevents uncontrolled iteration.
The ordinary bounded exact fallback remains the final correctness path.
Exhausted fallback limits abort without committing a model.

## Cost model

Coefficient construction still costs O(d T squared) arithmetic operations.
Ordinary sequential decisions cost O(p d T) operations.
One speculative pass also costs O(p d T) operations.
Its scan uses O(log d) vectorized rounds.
The token dot products use O(T) vectorized rounds.

For saved prefix lengths k_a, continuation costs

\[
O\!\left(T\sum_{a=1}^{p}(d-k_a)\right)
\]

plus cell selection and exceptional exact work.
The certificate still evaluates saved prefixes during speculative passes.
The prefix count measures avoided sequential continuation only.
It does not measure avoided total decisions or neural evaluations.

With output batch size B, scan storage costs O(B d T) values.
The coefficient arrays cost O(d T) values.
The implementation retains full output codes as required by the service.
Batching limits temporary memory, but does not establish a universal memory cap.
The worker must enforce its registered memory bound.

The method changes constant factors and parallel depth.
It does not improve the general arithmetic order of a complete quantization.
Failed speculative passes can increase total work.

## Fair comparison and complete service costs

The strongest fresh comparator receives this solver with nearest-grid initialization.
It also receives every shared kernel improvement.
The sequential solver remains a separately reported control.
Repair receives prior codes only when the service already stores those codes.
Loading, validating, and decoding them remains charged.
An ordinary deployment also stores its previous quantized model.
A warm model-only reconstruction control must therefore receive the same prior codes.
Warm initialization alone cannot establish a deletion-exclusive algorithmic advantage.

Let C denote complete model-only fresh cost with its best registered compatible solver.
Let A_q denote net quantizer savings before repair-specific overhead.
Let A_f denote neural feature savings.
Let H include state output, prior validation, failed checks, and other extra work.
Then the request cost is

\[
C_R=C-A_q-A_f+H.
\]

A ratio above rho requires

\[
A_q+A_f-H>(1-1/\rho)C.
\]

The same inequality must include preparation differences across a deletion sequence.
This method can have A_f=0.
That fact does not imply either success or failure of its quantizer cost advantage.
The registered feature-avoidance gate remains unmet when A_f=0.
A successor study must report that gate explicitly.

## Implementation interface

Call `speculative_quantize_dyadic_rows` with the ordinary dyadic solver arguments.
The new options are `candidate`, `max_sweeps`, and `row_batch_size`.
The default pass limit is two.
The default output batch size is 128.
Zero passes use sequential continuation from coordinate zero.
Inputs must remain unchanged throughout the call.

The result extends `CertifiedTokenResult` with these fields:

| Field | Meaning |
|---|---|
| `speculative_sweeps` | Total executed batch passes |
| `speculative_decision_checks` | Decision checks across all speculative passes |
| `speculative_certified_rows` | Rows requiring no sequential continuation |
| `sequential_fallback_rows` | Rows requiring sequential continuation |
| `prefix_verified_decisions` | Unique output coordinates proved before continuation |
| `fallback_decisions` | Unique output coordinates produced during continuation |
| `coefficient_elapsed_ns` | Time inside common coefficient construction |
| `speculative_elapsed_ns` | Time inside proposal construction and speculative passes |
| `fallback_elapsed_ns` | Time inside sequential continuation |
| `candidate_source` | Nearest-grid initialization or supplied codes |

The two unique decision counts sum to the output size.
They exclude repeated speculative checks from their total.
`speculative_sweeps` is not a global iteration depth.
The external timer must include validation, setup, and all other solver work.

## Validation and empirical gate

Ten focused tests pass in `tests/test_speculative_dyadic_solver_v16.py`.
They compare complete outputs with an independent dense rational oracle.
They cover exact prefix containment, cancellation, subnormals, and non-power-of-two scan widths.
They cover invalid candidates, finite failure, ties, and exact fallback limits.
They cover unequal saved prefixes and nonzero saved accumulators.
A forced exact fallback checks saved-code initialization after prefix acceptance.
These fixtures are software checks, not empirical datasets.

The next pilot must compare sequential, fresh speculative, and prior-code speculative methods.
It must retain every registered pass limit and every failed result.
The initial stage pilot cannot establish a complete-model speed advantage.
Only a complete service comparison can include state costs and later changed-prefix stages.
Preserve a negative result if speculative verification costs exceed its savings.

## Implemented service API

`CompactIdentityService` accepts two optional dyadic-only backends:

```python
service = CompactIdentityService(
    decoder, target, solver_backend="block_speculative",
    max_sweeps=1, row_batch_size=4096, block_width=32,
)
repair = service.run(retained_records, method="repair", prior=prior_state,
                     deleted_ids=deleted_ids)
indexed = service.run(retained_records, method="indexed_fresh", prior=prior_state,
                      deleted_ids=deleted_ids)
seed = CompactState(target.digest, prior_state.stages, ())
warm = service.run(retained_records, method="model_only_fresh", initial_model=seed)
cold = service.run(retained_records, method="model_only_fresh")
```

The whole-row backend is named `speculative`.
Its default pass limit is two and default row batch is 128.
The block backend defaults to one pass, width 32, and row batch 4096.
Plans must record the chosen options before measured execution.
Legacy backends retain their original defaults and behavior.

A warm model-only seed must contain complete stage codes and no factor payloads.
The service validates its target, grids, dimensions, and stage order.
Candidate membership is checked again inside each solver.
A seed can be an imperfect proposal without compromising exact accepted outputs.
Repair and indexed fresh receive identical prior stage proposals.
No seed becomes part of the committed retained state.

Service diagnostics distinguish validation, features, factor packing, candidate preparation, solver work, and code packing.
They report seed provenance and stage certificate diagnostics.
The whole service clock includes internal bookkeeping.
Individual phase clocks do not claim an exhaustive exclusive decomposition.
Aggregated counters and nested clocks must not be summed together.
Checkpoint loading, serialized file output, and external process work remain outside this service clock.
A complete empirical transaction must charge those costs separately.

Fixture tests establish model and canonical-state equality across these options.
No real full-model speculative transaction ran in revision 16.
The losing stage pilots prevent promotion into larger empirical runs.
