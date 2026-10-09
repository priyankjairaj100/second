# Exact pooled-Gram comparator

This component closes an implementation gap identified in `POOLED_GRAM_CONTROL_V30.md`.
It does not yet implement or benchmark a complete-model Gram service.
The underlying algebra is a control, not a new novelty claim.

## Exact maintained state

Let each trusted fixed feature matrix be \(X_s\in\mathbb{R}^{d\times n_s}\), with finite binary64 entries.
The state stores the packed lower triangle of

\[
G_S=\sum_{s\in S}X_sX_s^\top.
\]

Every entry of a source matrix has an exact representation \(z_{it}2^e\), using a common exponent and integers.
The implementation accumulates integer products without floating-point summation.
It then removes the greatest common power of two from all nonzero entries.
The zero matrix has exponent zero.
This produces a canonical numeric representation.
Source membership and the original normalization remain separate state metadata.

For authenticated source contributions and \(D\subseteq S\), exact subtraction gives

\[
G_S-G_D=\sum_{s\in S\setminus D}X_sX_s^\top\succeq0.
\]

The PSD premise follows from trusted accumulation and verified subset lineage.
Symmetry, a positive diagonal, or an arbitrary checksum does not establish it.
Ordinary parsing returns untrusted state.
Restoring a trusted archive requires an independently authenticated digest and expected source commitments.
This is a trusted-process model, not protection against arbitrary malicious Python code.

For feature integers with magnitude less than \(2^B\), summing \(n\) products needs at most
\(2B+\lceil\log_2 n\rceil\) magnitude bits.
Packed storage contains \(d(d+1)/2\) entries.
Admission bounds integer width, product count, serialized bytes, and explicit representations before accumulation.
These bounds do not replace process memory or CPU limits.

## Direct recovery of the existing codes

The quantizer uses the unchanged original normalization \(N_0\) and ridge \(\lambda>0\).
Set \(\beta=\lambda N_0\).
For a coordinate suffix \(J\), the relevant system is \(M=G_{JJ}+\beta I\).
Floating-point proposals \(u\) are checked through an outward-rounded residual enclosure for
\(r=e_1-Mu\).
Because \(G\succeq0\),

\[
\|M^{-1}e_1-u\|_2\le\frac{\|r\|_2}{\beta}.
\]

For a preceding-coordinate response \(c_h=G_{hJ}M^{-1}e_1\), either bound may be used:

\[
|c_h-G_{hJ}u|^2\le
\min\left\{
\frac{\|G_{hJ}\|_2^2\|r\|_2^2}{\beta^2},
\frac{G_{hh}\|r\|_2^2}{4\beta}
\right\}.
\]

The second follows by writing the PSD Gram as feature inner products and bounding
the singular values of \(A(A^\top A+\beta I)^{-1}\) by \(1/(2\sqrt\beta)\).
The unchanged V30 native certificate also encloses the response dot product's arithmetic error.
Existing row verification accepts only intervals wholly contained in the prescribed rounding cell.
It preserves coordinate order, base-only row scales, saturation, and lower-code ties.
An unresolved certificate produces no accepted model.

The new entry point accepts the trusted exact Gram, rather than regenerating it from retained feature arrays.
It reuses the existing strict native coefficient and row kernels.
No original numerical source or historical experiment is modified.

## Pilot scope and access contract

The pilot uses two existing real WikiText source records, each contributing 128 tokens.
It evaluates rows 0–3 of the first QKV matrix at full width 768.
It preserves the original normalization of 256 and ridge of 1/100.
The reference codes come from the already audited retained model.
The four-row output contains 3,072 decisions; this is not the 42.5-million-code complete model.

The compared paths are exact pooled subtraction, independent retained-Gram reconstruction, and the existing cached-feature token solver.
All arms use exact archived feature words and the same weight rows, scales, and reference.
Original Gram preparation, serialization, deleted-source decoding and contribution formation are charged explicitly.
Shared verification, archive parsing, weight loading, and native compilation are reported separately.
No neural feature replay is performed or priced by this component test.
It therefore cannot establish identity-only service latency or complete-model speed superiority.

The 1.87 MB JSON capsule preserves the original lossless descriptor payloads and their source-word hashes.
It also contains exact weight rows and previously observed reference indices.
Export verifies the original full archives and exact roundtrip equality.
The portable reader verifies bounded decoding and exact bytes without claiming that a different machine reproduces the historical encoder.
Its trust premise is the registered capsule digest and disclosed extraction provenance.
It neither relaxes the original decoder runtime contract nor fabricates unavailable machine facts.

The pilot is one development observation with a fixed method order.
Correctness permits planning a larger comparator, but an observed timing win does not trigger automatic expansion.
Losses, certificate refusals, and infrastructure failures remain part of the evidence.
