# Revision 17: a common native certificate

Date: 7 October 2026.

## Scope

The new kernel computes the existing exact dyadic target.
It changes neither coefficients nor quantization grids.
It changes only the arithmetic used to certify grid decisions.
Both repair and fresh reconstruction receive this kernel.
This document proves correctness under the stated runtime premises.
It proves no empirical speedup and no deletion-specific advantage.

The source is `src/native_ball_quantizer.py`.
The C source resides inside that Python file.
Existing source snapshots therefore bind the C source automatically.

## Runtime premises

Let binary64 unit roundoff be \(u=2^{-53}\).
Let \(h=2^{-1074}\) be its smallest positive value.
All native operations use round-to-nearest, with ties to even.
The runtime must preserve gradual underflow.
Inputs must remain unchanged during execution.
The feature width and token rank must each be at most \(2^{20}\).
Every accepted intermediate and certificate must remain finite.

The compiler receives these flags:

```
-std=c11 -O3 -shared -fPIC -fno-fast-math
-ffp-contract=off -frounding-math -fexcess-precision=standard
```

The native entry point checks the floating-point format and rounding mode.
It also checks selected gradual-underflow operations.
These checks support the premises; they do not verify the complete hardware implementation.
No BLAS reduction participates in the trusted native certificate.
The coefficient solver remains an untrusted proposal with an existing residual certificate.

Compilation occurs once per process.
Existing compiled caches are not trusted.
Build records include source, binary, compiler, flags, and compilation time.
Complete transaction timing must include compilation when deployment requires compilation.

## Elementary bounds

For a finite rounded result \(y=\operatorname{RN}(x)\), gradual underflow gives

\[
|y-x|\le u|x|+h/2.
\]

Solving this inequality for the exact value gives

\[
|y-x|\le 2u|y|+h.
\tag{1}
\]

This weaker result uses representable constants.
It also covers subnormal results.

Write \(\gamma_n=nu/(1-nu)\).
Repeated application of the elementary model bounds a sequential sum by

\[
\left|\operatorname{RN}\!\left(\sum_{j=1}^n x_j\right)
      -\sum_{j=1}^n x_j\right|
\le\gamma_n\sum_j|x_j|+\frac{nh}{1-nu}.
\tag{2}
\]

The sum notation denotes a fixed left-to-right sequence of additions.
Equation (2) permits cancellation.
Its additive term bounds all amplified underflow errors.

For nonnegative binary64 inputs, a subnormal addition is exact.
Thus their rounded sum \(\widehat A\) satisfies

\[
\sum_j x_j\le\frac{\widehat A}{1-nu}\le2\widehat A,
\qquad n\le2^{20}.
\tag{3}
\]

For products of nonnegative binary64 inputs, a product can underflow.
Applying the same recurrence gives

\[
\sum_j a_j b_j\le2\widehat M+\tau,
\qquad
\widehat M=\operatorname{RN}\!\left(\sum_j\operatorname{RN}(a_jb_j)\right),
\tag{4}
\]

where \(\tau=2^{-1000}\).
Indeed, \((1-2nu)^{-1}<2\) under the rank limit.
The accumulated additive error is smaller than \(4nh\).
The chosen \(\tau\) exceeds that quantity by a large factor.
This conservative floor avoids unrepresentable constants.

## Accumulator certificate

Fix one output row and already certified codes \(q_h\).
For token coordinate \(t\), the exact accumulator is

\[
s_{i,t}=\sum_{h<i}z_{h,t}(w_h-q_h).
\]

The native kernel computes

\[
\widehat d_h=\operatorname{RN}(w_h-q_h),\qquad
\widehat p_{h,t}=\operatorname{RN}(z_{h,t}\widehat d_h),
\]

\[
\widehat s_{i,t}
 =\operatorname{RN}\!\left(\sum_{h<i}\widehat p_{h,t}\right),\qquad
\widehat A_{i,t}
 =\operatorname{RN}\!\left(\sum_{h<i}|\widehat p_{h,t}|\right).
\]

Equation (1) applied twice gives

\[
|z_{h,t}(w_h-q_h)-\widehat p_{h,t}|
\le6u|\widehat p_{h,t}|+h(|z_{h,t}|+2).
\tag{5}
\]

Set \(Z_{i,t}=\sum_{h<i}|z_{h,t}|\).
Equations (2), (3), and (5) then give

\[
|s_{i,t}-\widehat s_{i,t}|
\le
\frac{\gamma_i+6u}{1-iu}\widehat A_{i,t}
 +h(Z_{i,t}+4i).
\]

For \(i\le2^{20}\), define the exactly representable constant

\[
c_i=2(i+6)u.
\]

This constant exceeds the preceding coefficient of \(\widehat A_{i,t}\).
The Python wrapper computes an upward bound \(Z^+_{i,t}\) using directed additions.
It then computes

\[
U_{i,t}=\operatorname{up}\bigl(\tau\operatorname{up}(1+Z^+_{i,t})\bigr).
\]

Because \(\tau/h=2^{74}\), this bounds \(h(Z_{i,t}+4i)\).
Therefore,

\[
\boxed{|s_{i,t}-\widehat s_{i,t}|\le c_i\widehat A_{i,t}+U_{i,t}.}
\tag{6}
\]

The kernel uses \(U_i=\max_t U_{i,t}\).
This removes per-token directed rounding from its inner loop.

## Decision certificate

The existing coefficient routine supplies \(\widehat v_i\) and \(e_i\), with

\[
\|v_i-\widehat v_i\|_2^2\le e_i.
\]

The wrapper supplies \(\rho_i\ge\sqrt{e_i}\).
It checks this inequality with exact rational squaring.
It therefore does not trust the square-root library for certificate validity.
The wrapper also supplies \(L_i\ge\|\widehat v_i\|_1\).

The native decision center is

\[
\widehat x_i=\operatorname{RN}\!\left(w_i+
  \sum_t\operatorname{RN}(\widehat v_{i,t}\widehat s_{i,t})\right).
\]

Define the following nonnegative native reductions:

\[
\widehat P_i=\operatorname{RN}\!\left(\sum_t
 |\operatorname{RN}(\widehat v_{i,t}\widehat s_{i,t})|\right),
\]

\[
\widehat M_i=\operatorname{RN}\!\left(\sum_t
 \operatorname{RN}(|\widehat v_{i,t}|\widehat A_{i,t})\right),
\]

\[
\widehat S_i=\operatorname{RN}\!\left(\sum_t|\widehat s_{i,t}|\right),
\qquad
\widehat B_i=\operatorname{RN}\!\left(\sum_t\widehat A_{i,t}\right).
\]

Equations (3), (4), and (6) yield the accumulator contribution

\[
R_{\mathrm{acc}}=c_i(2\widehat M_i+\tau)+U_i L_i.
\tag{7}
\]

They also give

\[
\|s_i\|_2\le\|s_i\|_1
\le2\widehat S_i+2c_i\widehat B_i+TU_i.
\]

Thus the coefficient contribution is

\[
R_{\mathrm{coef}}=\rho_i
 (2\widehat S_i+2c_i\widehat B_i+TU_i).
\tag{8}
\]

Let \(d_T=4(T+3)u\).
Applying (1) to products and (2) to the cancelling sum gives

\[
R_{\mathrm{arith}}=d_T(|w_i|+\widehat P_i)+\tau.
\tag{9}
\]

For example, the coefficient of \(\widehat P_i\) is at most \(2\gamma_T+4u\).
It is smaller than \(d_T\) under the rank limit.
The remaining underflow error is smaller than \(\tau\).

The native program evaluates (7)--(9) with outward rounding.
Multiplication by two is exact unless it overflows.
Overflow invalidates the native certificate.
It computes an upward total radius

\[
R_i\ge R_{\mathrm{acc}}+R_{\mathrm{coef}}+R_{\mathrm{arith}}.
\]

Consequently, the exact target input lies inside

\[
x_i\in[\operatorname{down}(\widehat x_i-R_i),
        \operatorname{up}(\widehat x_i+R_i)].
\tag{10}
\]

## Codes, ties, and fallback

The dyadic grid and every midpoint are exact binary64 values.
A cell excludes its lower boundary and includes its upper boundary.
This implements the existing lower-code rule at midpoint ties.
The native program accepts a code only when (10) lies inside its cell.
Induction over coordinates proves every accepted row equals the exact target.

A supplied candidate changes only the first cell tested.
It does not change the center or radius.
If that cell fails, the program locates another cell and verifies it identically.
Candidate membership is checked before native execution.

The program stops a row at its first uncertified decision.
The wrapper collects every stopped row into one existing solver call.
That call reconstructs each stopped row from its first coordinate.
Its exact and refinement budgets apply jointly to all stopped rows.
The fallback can raise an unresolved exception.
The wrapper then returns no model.

This fallback repeats work deliberately.
Its time appears separately and remains inside total quantizer time.
Attempted native decisions include the first failed decision in each stopped row.
Certified native prefixes include successful decisions later repeated by fallback.
It avoids introducing an unreviewed continuation interface.
Complete native rows and exact fallback rows share the same numerical target.

## Cost and interpretation

The native kernel uses \(O(pdT)\) arithmetic for \(p\) output rows.
Its temporary native state contains \(O(T)\) values.
It avoids the speculative tensor scan and per-token interval endpoints.
It still visits every code and every token coordinate.
It also retains all coefficient, feature, and state costs.

Candidate hits avoid a grid search only.
They do not avoid decision arithmetic or retained feature evaluation.
An implementation speedup over Python is therefore a common backend result.
A repair claim must compare against fresh reconstruction using this same kernel.
A warm model-only comparator must receive the same prior codes.
No full-model or preparation-inclusive speedup follows from this proof.

## Validation boundary

The focused software tests include independent dense rational oracles.
They include subnormal grid values and exact midpoint ties.
They also include coefficient conditioning, bounded fallback, and candidate rejection.
These tests are software fixtures, not empirical datasets.
They do not establish throughput or scientific novelty.
