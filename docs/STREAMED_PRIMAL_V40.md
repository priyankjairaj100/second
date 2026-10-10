# Streamed feature-space certificate

Implementation date: 10 October 2026.
No empirical result existed for this adapter when this review was written.

The V39 feature-space adapter concatenates every retained feature block.
That array still grows with the total token count.
The V40 adapter reads bounded blocks and accumulates a directed Gram enclosure.
It then uses the same residual coefficient verifier and shared row kernel.
The mandatory interval fallback remains unchanged.

For a concatenation \(X=[X_1,\ldots,X_k]\),

\[
XX^\top=\sum_{j=1}^k X_jX_j^\top.
\]

Each block enclosure contains every allowed realization of its Gram.
Outward additions therefore enclose the complete retained Gram.
Each realized sum is positive semidefinite.
Its ridge-shifted suffix systems retain the same positive eigenvalue lower bound.
Thus the V39 residual and rounding argument applies without a concatenated feature matrix.
Accepted output codes match the same finite target for every allowed block realization.
Changing block grouping may change certificate tightness or acceptance.
It cannot change the exact codes of an accepted result.

The interface requires the exact token count before numerical allocation.
It also bounds tokens per block and the number of blocks.
Every block must be nonempty.
Missing tokens, excessive tokens, or excessive blocks cause refusal without a result.
The native and NumPy arithmetic checks remain mandatory.
Each supplied block is copied before numerical use.
The caller must keep its endpoints unchanged during that copy.

For width \(d\), output rows \(R\), total tokens \(T\), and block limit \(B\), explicit workspace is

\[
O(d^2+dB+Rd).
\]

This excludes caller-owned source storage and whole-process overhead.
Caller code must supply an actual stream to realize that bound.
Structural work remains \(O(d^2T+d^3+Rd^2)\), plus bounded block additions.
The admission calculation includes both complete row passes and every allowed block sum.
This is not a wall-time guarantee.

Seven focused software fixtures cover rational oracle agreement, nonpoint boxes, exact ties, and empty retention.
They also cover token and block limits, admission before iteration, and workspace independence from total tokens.
They use small arithmetic fixtures, not synthetic empirical datasets.

The adapter has not yet entered a complete model service.
It does not reduce the stored descriptor payload by itself.
It does not establish a full-model runtime or memory result.
