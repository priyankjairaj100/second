# Reuse complete rows and shared coefficient certificates

Revision 28 preserves the exact dyadic target and every revision 27 source file.
It changes how unresolved rows receive additional verification.
The algorithm and proof below were reviewed before empirical execution.
The later [complete empirical report](EMPIRICAL_COMPRESSION_V25_V28.md) records exact repair and a cold-replay timing tie.

## Algorithm

First, construct one ridge coefficient certificate for the complete feature box.
Run the existing native ball kernel over all output rows.
Retain every completely certified row.
Discard every incomplete row's partial codes.

Next, apply the native interval verifier only to unresolved rows.
Reuse the original coefficient proposals and certified square-root error bounds.
A Euclidean coefficient bound also bounds every individual coefficient component.
This conversion requires no new coefficient solve or preconditioning.

The interval verifier tracks each row's accepted codes when constructing its accumulator.
Its accumulator enclosure can therefore be tighter than the ball verifier's shared discrepancy bound.
It evaluates each selected row from its first coordinate.
It retains the complete original coordinate order and feature box.

Only remaining unresolved rows trigger preconditioning.
Construct the stronger coefficient certificate once for the common feature box.
Apply its paired proposals and component radii to those rows only.

Optional Python universal fallback receives only the still-unresolved rows.
It receives their original row scales, complete width, ridge, normalization, and complete feature box.
Positive-width boxes never use pointwise exact fallback.
Singleton boxes retain the common native point solver.

The public entry point remains `certify_ball_dyadic_box`.
Its argument contract matches revision 27.
Its backend identifier is `native_ball_sparse_interval_box`.

## Exact assembly proof

Fix a finite feature box \(\mathcal B\).
For each output row \(r\), the exact quantizer defines a row function \(Q_r(X)\).
That function uses the complete coordinate order and its fixed row grid.
Other output rows do not enter its recurrence.

Suppose one verifier proves

\[
\forall X\in\mathcal B,\qquad Q_r(X)=q_r.
\]

Different rows may use different sound verifiers.
Every verifier still quantifies over the same complete box.
Taking the conjunction of their conclusions gives

\[
\forall X\in\mathcal B,\qquad
Q(X)=\begin{bmatrix}q_1\\\vdots\\q_m\end{bmatrix}.
\]

No independence assumption is needed.
Feature correlations discarded by the box remain conservatively covered.

Selecting output rows preserves their scales because scales depend only on each original weight row.
Selecting rows never selects input coordinates or feature entries.
The exact target therefore remains unchanged.

The initial ridge certificate proves

\[
\|c_i(X)-p_i\|_2^2\le E_i
\quad\text{for every }X\in\mathcal B.
\]

The checked square-root radius supplies

\[
|c_{ik}(X)-p_{ik}|\le\rho_i,
\qquad \rho_i^2\ge E_i.
\]

These component radii remain paired with the original proposals.
The native interval verifier can reuse them across every output row.
Preconditioned proposals receive only their own verified component radii.

## Partial outputs and failures

The first kernel returns a failure coordinate for every unsuccessful row.
Those rows remain scratch space until a verifier replaces the entire row.
Successful prefixes never enter the final model by themselves.

Each interval call handles one unresolved row.
This prevents its first unresolved row from hiding another row's potential success.
Receipts map local failures back to original row indices.
The optional Python verifier processes the remaining subset together.

Any remaining uncertainty aborts the entire result.
Native runtime or allocation failures also abort.
The final candidate check applies after complete model assembly.
The returned array uses immutable bytes as its owner.

## Cost and provenance

Ridge coefficients are constructed once per uncertain-box call.
The interval ridge pass reuses them.
Preconditioning is conditional on a still-unresolved row.
Compilation of the interval kernel is conditional on an initial failed row.

Every repeated row traversal appears in native counters.
The initial pass records all failed row indices and their coordinates.
Sparse interval receipts record their original row and full-call duration.
Native kernel duration remains a separately identified subset.

Result counts partition the final model into four routes:

- Rows completed by the initial ball pass.
- Rows completed by shared ridge intervals.
- Rows completed by shared preconditioned intervals.
- Rows completed by Python universal fallback.

Complete elapsed time includes validation, copies, bound construction, compilation, every verifier, and final assembly.
Separate fields identify coefficient, feature, ball, interval, kernel, and Python fallback costs.
Per-pass durations overlap their reported native kernel durations.
They must not be added twice.

Singleton point durations include their own compilation.
That separately reported compilation time must not be added again.
Failed attempts expose `native_diagnostics`, including every completed route and the complete elapsed duration.

`max_coefficient_error_squared` reports the largest bound observed across every invoked coefficient construction.
This includes stronger proposals and Python fallback results when present.
It is a diagnostic bound, not a model error estimate.

Per-decision dependence on preconditioning is not measured across the assembled routes.
Its inherited count remains zero and its measurement flag remains false.
The explicit route counts identify how each row was certified.

Receipts bind the ball kernel, interval kernel, their compiled binaries, and this wrapper.
The registered source snapshot must also bind imported arithmetic and coefficient modules.
Both native inputs require aligned contiguous binary64 storage.
The original runtime and dimension restrictions remain enforced.

## Verification

Eight focused software fixtures exercise the new selection logic.
An actual small box produces one failed ball row among three rows.
The shared ridge interval verifier resolves only that row.
The test forbids preconditioning and Python fallback.
It confirms that ridge coefficients were constructed exactly once.

Another test poisons every incomplete native row with NaNs.
Correct complete-row replacement removes all poisoned entries.
Further tests exercise preconditioning, selected Python fallback, and global failure identities.

Accepted results match independent exact rational quantization at every small-box corner.
Tests also cover immutable outputs, candidates, empty rank, unaligned buffers, read-only inputs, and runtime rejection.
No real calibration data or model experiment ran during implementation.
