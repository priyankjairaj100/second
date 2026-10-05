# Exact-order linear kernel diagnostic

This note concerns a diagnostic prototype.
The production decoder remains unchanged.
The prototype changes no coordinate order or rounding boundary.

For token row `t` and output row `a`, the scalar program computes

\[
p_k=\operatorname{RN}_{64}(x_{tk}w_{ak}),\qquad
s_{-1}=+0,\qquad
s_k=\operatorname{RN}_{64}(s_{k-1}+p_k),
\]

then returns `RN64(s[d-1] + bias[a])`.
The prototype performs one multiply ufunc, then one add ufunc, for each coordinate.
It batches only independent token and output entries.
It materializes products before addition.
It uses neither matrix multiplication nor a parallel reduction.

Assume both implementations use binary64 round-to-nearest operations with gradual underflow.
Assume neither implementation contracts the multiply and add into an FMA.
Each vector element starts from the same positive zero.
At coordinate zero, both programs compute the same product and sum.
Induction preserves the accumulator bits at each later coordinate.
The final bias addition therefore returns identical bits.

This argument includes cancellation, subnormal results, and signed zero.
Both implementations reject nonfinite arithmetic.
Rejection timing can differ across independent entries.
No successful output follows an arithmetic error.

The prototype checks subnormal behavior on its NumPy ufunc path.
Six software tests include cancellation, an FMA-sensitive case, underflow, overflow, shapes, and article parsing.
Real diagnostics compare every emitted feature byte with the scalar program.
These checks support the observed platform only.
They do not prove all future NumPy implementations satisfy the arithmetic premises.

`feature_accelerated.py` constructs a function with the existing executor code and a substituted linear kernel.
It leaves production module globals unchanged.
Nonlinear primitives retain the existing certified evaluator.
Proof jets never use the prototype kernel.

The current prototype does not solve dense rational storage or exact factorization costs.
Its diagnostic worker includes input checks, selected parameter loading, features, and feature output.
This boundary is narrower than the complete repair transaction.
One observation per dataset cannot establish reliable speedup.
A feature gain cannot establish a repair gain over equally informed fresh quantization.
