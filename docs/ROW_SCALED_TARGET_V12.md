# Prospective row-scaled target

This is a new target variant.
It does not replace the original column-grid target or its failed quality observations.
No quality improvement is claimed before measurement.

For bit width $b$, let $h=2^{b-1}$.
For original output row $w_a$, choose

\[
e_a=\max\left\{-1074,
\left\lceil\log_2\max\left(\frac{\max_i w_{ai}}{h-1},
\frac{-\min_i w_{ai}}h,0\right)\right\rceil\right\}.
\]

A zero row uses $e_a=0$.
The exact implementation uses rational comparisons, not a floating logarithm.
The row grid is

\[
\mathcal G_a=2^{e_a}\{-h,-h+1,\ldots,h-1\}.
\]

Every coordinate within row $a$ uses this same grid.
Different output rows can use different grids.
The scales depend only on original base weights.
They must remain fixed for original quantization, every deletion, and every baseline.

## Exact normalization identity

Set $s_a=2^{e_a}>0$ and $\widetilde w_a=w_a/s_a$.
The covariance and reverse-LDL factors do not depend on an output row's scale.
Suppose all earlier codes satisfy $q_{ah}=s_a\widetilde q_{ah}$.
Then the original recurrence gives

\[
\begin{aligned}
v_{ai}
&=w_{ai}+\sum_{h<i}L_{ih}(w_{ah}-q_{ah})\\
&=s_a\left(\widetilde w_{ai}
+\sum_{h<i}L_{ih}(\widetilde w_{ah}-\widetilde q_{ah})\right)
=s_a\widetilde v_{ai}.
\end{aligned}
\]

Nearest-grid rounding therefore gives $q_{ai}=s_a\widetilde q_{ai}$.
Positive scaling preserves the lower-code tie rule and endpoint saturation.
Induction proves every code.
The covariance, ridge, original normalization, and coordinate order remain unchanged.

`src/row_scaled_quantizer.py` implements this identity.
It invokes the existing certified solver on normalized rows and integer grids.
It then restores exact row-scaled codes.
The returned diagnostics describe that normalized solver execution.

## Representability and identity requirements

The supported bit widths are two through eight.
The complete row grid must remain finite in binary64.
Every normalization must be exactly representable in binary64.
An exact inverse power-of-two scaling check detects lost normalization bits.
The helper rejects underflow or overflow that changes represented values.
It also verifies exact restoration of every returned code.

The helper rejects array subclasses and nonfinite weights.
Inputs must remain unchanged during execution.
The supplied exponents must equal the canonical base-only exponents.

The experiment wrapper must declare a distinct target identity.
It must bind the scale policy, exponents, bit width, source hashes, and runtime.
The existing column-grid `StageSpec` cannot silently stand for row-specific grids.
An adapter must represent the row grids explicitly or define an equivalent versioned target.

## Software evidence

Five focused tests compare outputs with the independent dense oracle, one row at a time.
They cover multiple bit widths, zero rows, ties, rank deficiency, and subnormal grids.
They also cover minimal coverage, finite endpoints, foreign scales, and normalization rejection.
All five tests passed before empirical use.
These tests establish software agreement, not language-model quality or repair speedup.
