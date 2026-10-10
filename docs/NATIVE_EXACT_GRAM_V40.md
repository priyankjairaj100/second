# Stronger native exact Gram control

Implementation date: 10 October 2026.
This work followed review of the registered V39 controls.
It does not change that completed campaign or its numerical sources.
No V40 empirical run is registered at this checkpoint.

## Reason for the change

V39 removes the row-kernel mismatch between feature and Gram certificates.
Its exact Gram accumulation still loops over Python integers.
That overhead can weaken the Gram baseline.
V39 timing cannot establish dominance over an optimized exact Gram implementation.

`research_v40/native_exact_gram.py` supplies a faster implementation candidate.
It changes exact product accumulation only.
It returns the existing V35 archive, including identical source commitments.
Pooling, subtraction, serialization, outward conversion, and certificates remain unchanged.
Thus it preserves canonical exact state across deletion histories.
This avoids the history-dependent enclosure state of a rounded Gram downdate.

The shared implementation is a baseline improvement available to every compatible method.
It is not claimed as a new mathematical contribution.
Its practical speed remains unmeasured on empirical data.

## Exact arithmetic argument

The existing scanner creates a private binary64 snapshot.
It expresses every nonzero value as an integer times one common power of two:

\[
x_{it}=a_{it}2^e,\qquad |a_{it}|<2^b.
\]

For \(T\) tokens, every partial dot product has absolute value below

\[
T2^{2b}\le 2^{2b+\lceil\log_2T\rceil}.
\]

The native route requires the existing conservative exponent to be at most 255.
Every partial sum therefore fits the signed 256-bit range.
The zero-token case produces an exact zero Gram separately.

Two unsigned 64-bit limbs hold each input magnitude.
The native decoder rejects magnitudes requiring more than 127 bits.
Schoolbook multiplication uses unsigned 128-bit intermediates and four result limbs.
Each intermediate multiply-add fits the unsigned 128-bit range.
Each sum or difference is evaluated modulo \(2^{256}\).
The absolute-sum bound makes its signed interpretation uniquely equal to the exact integer result.
Signed cancellation does not weaken that bound.
No floating-point product or accumulation enters this kernel.

Python reads the four limbs as a signed integer.
The unchanged canonicalizer removes the common power of two.
The unchanged encoder constructs source hashes and canonical archive bytes.
Consequently, accepted results equal the reference factory's exact Gram and archive.
Positive semidefiniteness follows from exact construction of \(XX^\top\).
A checksum or a nonnegative diagonal is not the positivity proof.

The constructor uses the existing private factory seal after this trusted computation.
It never accepts arbitrary caller-supplied Gram entries as trusted data.
Arbitrary in-process code remains outside the established trust boundary.

## Admission and failure policy

Keep the existing feature, product, integer, serialization, and representation bounds.
Add native input storage and both output buffers to the workspace allowance.
Reject dimensions outside the declared native caps.
Reject nonfinite inputs, excessive integer range, or insufficient workspace before native accumulation.
Compiler, allocation, and kernel errors return no trusted object.
The native factory supports only little-endian 64-bit words.
Record source, binary, compiler, flags, and compilation cost for any future experiment.

The explicit array allowance is not a total process-memory guarantee.
Use the existing bounded process controller for empirical execution.
Never infer performance from software fixture timings.

## Software checks

The focused suite compares full canonical archives with the original Python factory.
It also computes every fixture entry through independent rational arithmetic.
It covers zero and empty inputs, signed zero, cancellation, and subnormal values.
It covers products across limb boundaries and the admitted 255-bit boundary.
It checks overflow and workspace rejection before compilation.
It checks exact deletion against independently accumulated retained data.
Generated values are software arithmetic fixtures, not empirical datasets.

Run:

```bash
python -B -m unittest tests.test_native_exact_gram_v40 -v
```

## Next empirical gate

V39 is complete; its results and adverse findings are preserved.
Register a fresh bounded comparison using the same real source-selection rule.
Compare native and Python exact archive bytes before interpreting timing.
Compare the strengthened Gram deletion and fresh controls with the selected cached-feature solver.
Include loading, deleted-feature replay, exact accumulation, certification, and output costs.
Preserve native compilation separately or charge it consistently to all applicable arms.
Use a new campaign, runtime identity, and ledger.
Do not relabel V39 results as measurements of this kernel.
