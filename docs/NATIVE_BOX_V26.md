# Native universal box decisions

This module changes implementation, not the exact dyadic target.
It has software verification only.
No runtime improvement follows from these tests.

## Public contract

`src.native_box_certificate.certify_native_dyadic_box` accepts the existing dyadic box arguments.
Its additional `allow_python_fallback` argument defaults to `True`.

A successful uncertain-box result certifies every feature matrix within the supplied inclusive box.
Every matrix uses the same output codes.
Source containment remains the caller's responsibility.
Caller-owned arrays must remain unchanged throughout the call.

The result never exports partially certified codes.
An unresolved box raises `TokenBoxUnresolved`.
Positive-width boxes never use a pointwise solver or endpoint sampling.
Singleton boxes use the common native point solver.
Their `backend` field explicitly records this path.

Canonical row scales, bit widths, exact boundaries, and lower-code ties remain unchanged.
Candidate codes only check the completed certified result.
They never supply evidence for acceptance.

## Two certificate passes

The first pass constructs the existing ridge coefficient bounds in Python.
Those bounds establish

\[
\|c_i-p_i\|_2^2\le E_i.
\]

The common square-root routine verifies a binary64 radius using exact rational comparison.
Thus each coefficient component satisfies

\[
|c_{ik}-p_{ik}|\le\rho_i,
\qquad \rho_i^2\ge E_i.
\]

This uniform component bound avoids preconditioning when sufficient.
It can be looser than the Python ridge decision bound.

Native rejection triggers a second pass with the reviewed `_coefficient_bounds` function.
That function verifies componentwise radii using directed residual and contraction checks.
Its proposals remain untrusted until those checks succeed.

The second pass restarts all native rows.
It does not reuse speculative codes from the first pass.
Both coefficient constructions and native passes remain charged.

If both native passes reject, the default invokes the existing Python universal verifier.
This retains its independent ridge certificate and potentially tighter decision bounds.
That fallback can repeat coefficient construction.
Its full cost remains charged.
Disabling Python fallback exposes native acceptance alone.

## Native proof

For each row, the accumulator denotes the exact vector

\[
s_i=\sum_{j<i}(w_j-q_j)x_j.
\]

Directed interval operations construct an enclosure \([s_i^-,s_i^+]\).
Suppose the coefficient certificate proves \(|c_i-p_i|\le e_i\).
Then

\[
\left|(c_i-p_i)^Ts_i\right|
\le\sum_k e_{ik}\max(|s_{ik}^-|,|s_{ik}^+|).
\]

Every product and sum receives outward rounding.
This radius enlarges the enclosure of \(w_i+p_i^Ts_i\).
The resulting interval encloses every exact decision value.

Acceptance requires containment within one rounding cell.
The lower boundary is strict.
The upper boundary is inclusive.
These comparisons preserve lower-code ties.

Accepted codes then update the accumulator using interval multiplication and addition.
Induction proves every subsequent decision's enclosure.
The final result therefore applies to the complete feature box.

A missing component certificate normally rejects the coordinate.
An exactly zero accumulator provides one sound exception.
Its coefficient contribution is exactly zero, regardless of the coefficient.
The decision then depends only on its original weight.

## Arithmetic assumptions

The native code requires binary64 elementary arithmetic with round-to-nearest and gradual underflow.
Runtime checks test the binary format, rounding mode, subnormals, and a round-to-even example.
Every native invocation repeats these checks.

Products consider all four endpoint combinations.
`nextafter` expands rounded extrema toward the corresponding infinity.
Addition similarly expands both endpoints.

Exact zero operands preserve exact zero products.
An exact zero interval addend preserves the other interval.
Equal singleton opposites cancel exactly.
These identities remain valid for signed zeros and subnormal values.

Nonfinite decision intervals, radii, or accumulators cause rejection.
Compilation disables fast math and floating contraction.
It requests standard excess precision and respects the rounding environment.
This relies on a conforming C compiler and elementary binary64 runtime.
The runtime tests cannot prove compiler conformance themselves.

All C input pointers are const.
Python keeps their owning arrays alive throughout the call.
Noncontiguous or unaligned inputs receive aligned contiguous copies.
The singleton point solver receives aligned inputs too.
The C accumulator allocation is bounded by the supplied rank.
No partial native output escapes rejection.

## Provenance and cost

`prepare_native_box` compiles fresh source once per process.
It never loads an existing binary cache.
The receipt records C source, wrapper, coefficient source, and binary hashes.
It also records compiler identity, flags, and compilation time.

Complete calls include validation, coefficient construction, native evaluation, fallback, and result assembly.
Returned metadata separates compilation, coefficients, native kernels, and fallback.
Each native pass records its policy, status, work counters, failure location, and measured times.
Counters include repeated work across passes.

`total_elapsed_ns` is the whole call's elapsed duration.
Component timings overlap only for singleton point calls.
For those calls, `fallback_elapsed_ns` includes the complete point solver, including its compilation.
Do not add singleton compilation twice.

Failed certificates expose `native_diagnostics` on their exception.
This includes completed pass receipts, fallback duration, and total duration.
Compilation failures still expose the overall failed-call duration.

Native component evaluation does not measure per-decision dependence on preconditioning.
Its inherited `decisions_requiring_preconditioner` value remains zero.
The accompanying `decisions_requiring_preconditioner_evaluated` field remains false.
Python fallback supplies the existing measured value and sets that field true.

## Software verification

`tests/test_native_box_v26.py` contains twelve focused tests.
The first complete run passed in 0.388 seconds, including native compilation.
This is software-test duration, not an empirical speed measurement.

The tests compare accepted boxes with exact rational quantization at every small-box corner.
They also check interior points, ties, subnormal arithmetic, and exact-zero propagation.
Additional tests exercise both native passes, Python fallback, singleton dispatch, and actual ambiguity rejection.
Validation rejects nonfinite inputs and unsupported runtime premises.
Additional fixtures exercise unaligned, read-only, and noncontiguous inputs.
Build tests verify source bindings and required compiler flags.

The tests use small software fixtures.
They are not empirical datasets.
No real model or calibration experiment ran during this implementation.
