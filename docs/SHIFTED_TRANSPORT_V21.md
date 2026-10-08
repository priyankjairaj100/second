# Target-preserving shifted transport: a finite certificate and its cost limit

Date: 8 October 2026.
Status: theoretical design review.
No new empirical worker or model execution supports this note.
The implemented revision 20 provider remains unchanged.

## Decision

A signed affine correction can escape the revision 20 centered-box obstruction.
It is a concrete mathematical option.
It does not yet provide a cheap complete transformer update.

Do not implement a dense correction traversal as the next speed experiment.
That program repeats the main projection work of fresh evaluation.
A target-preserving implementation needs verified sparse or low-rank corrections at later projections.
The present archive does not establish that condition.

The separate fixed-feature target is an explicit redesign.
It must receive its own target identifier, quality evidence, and novelty assessment.
It cannot establish success for the original sequential target.

## 1. Why a shifted center is different

Revision 20 found different exact quantizer outputs at two feature matrices.
Those matrices came from the fixed anchor and the retained-prefix decoder.
The registered sixteen-row check found 252 differing codes among 12,288 codes.
The parent report stores the corresponding bindings and outputs.

Thus no set containing both matrices can certify one complete constant code output.
Every valid box centered at the anchor contains both matrices.
A shifted set can exclude the anchor while containing the retained features.
The obstruction does not apply to such a set.

The actual revised set still needs a sound finite-arithmetic certificate.
A plausible center or observed containment does not provide that certificate.

## 2. A concrete signed affine center

Use token-major inputs, but write each token as a column here.
Let x0 and W0 describe the fixed anchor.
Let x1 and W1 describe the requested prefix.
Let b be the fixed bias.
Let y0 be the stored finite affine output under the anchor.

Suppose a verified predictor provides

\[
x_1=x_0+d+r,\qquad |r|\le\rho.
\]

The vector d contains signed predicted changes.
The nonnegative vector rho bounds their residual.
The identities concern the numerical values of finite operands.
They do not assume equality of signed-zero encodings.

Define the real shifted center

\[
c=y_0+(W_1-W_0)x_0+W_1d.
\tag{1}
\]

This center retains the signed effect of both matrix and input changes.
It differs from the revision 20 construction, which places those effects inside a symmetric radius.

Let e0 bound the anchor's ordered finite error:

\[
|y_0-(W_0x_0+b)|\le e_0.
\]

Let e1 bound the requested execution's ordered finite error:

\[
|y_1-(W_1x_1+b)|\le e_1.
\]

Then

\[
|y_1-c|\le e_0+e_1+|W_1|\rho.
\tag{2}
\]

**Proof.** Subtract Equation (1) from the requested real affine value.
The resulting difference is W1 r minus the anchor finite error.
The requested finite error contributes e1.
The triangle inequality gives Equation (2).

If the computed center chat has a certified error ec, use

\[
|y_1-\widehat c|\le e_0+e_1+|W_1|\rho+e_c.
\tag{3}
\]

Equation (3) can exclude y0 when the signed correction exceeds its radius.
It does not require that exclusion for correctness.

At the first projection, x1=x0 because no quantized ancestor precedes its input.
Therefore d=0 and rho=0 there.
Only the signed sparse matrix correction remains.
This provides the clearest possible first-stage implementation.

## 3. A complete finite error calculation

The real center identity does not replace the finite target schedule.
The target rounds each product and each ordered addition separately.
The following recurrence covers that schedule, including gradual underflow.

Set u=2^-53 and eta=2^-1074.
Let Pi bound the absolute exact product wi xi at coordinate i.
Let Ai be the sum of the first i product bounds.
Initialize A0=E0=0.
For every coordinate, use

\[
A_i=A_{i-1}+P_i,
\]

\[
E_i=(1+u)E_{i-1}+uA_{i-1}
 +(2u+u^2)P_i+(2+u)\eta.
\tag{4}
\]

Then Ei bounds the accumulated finite error after that coordinate.
To see this, separate product rounding from accumulator rounding.
The rounded product error is at most uPi+eta.
The accumulator's exact input magnitude is at most

\[
A_{i-1}+E_{i-1}+(1+u)P_i+\eta.
\]

Adding its rounding error yields Equation (4).
After the final bias addition, use

\[
E_{\rm out}=(1+u)E_d+u(A_d+|b|)+\eta.
\tag{5}
\]

The implementation must reject any possible finite overflow.
This includes product bounds and each displayed accumulator magnitude.
It must also reject a nonfinite outward bound.
Rounding each bound upward to binary64 controls rational bit growth.
The algebra remains valid because every rounding increases the bound.

The anchor can store these scalar bounds during preparation.
The requested projection can obtain Pi from matrix maxima and verified input ranges.
This calculation need not execute token dot products.
Grouping tokens or output rows weakens the bound but preserves validity.

The correction itself needs a separate certified error ec.
One option computes exact dyadic correction sums and rounds their final values outward.
Another option applies Equations (4) and (5) to its declared finite schedule.
Both options must charge their computation and storage.

Matrix subtraction also needs explicit treatment.
A computed binary64 difference is not automatically the exact difference W1-W0.
Exact dyadic subtraction avoids that issue.
Alternatively, store a certified subtraction remainder and include its product contribution in ec.
Dropping that remainder would leave Equation (3) unproved.

## 4. First-projection savings are possible

Suppose W1-W0 has s nonzero entries.
Suppose the record contains n tokens.
Computing its signed product with the stored x0 requires approximately ns scalar product terms.
A dense m-by-d projection requires nmd terms.
The correction therefore has a smaller arithmetic count when s is much smaller than md.

A complete charge must also include these costs:

- Reading the changed matrix and identifying its nonzero entries.
- Reading stored anchor inputs and affine outputs.
- Computing finite error bounds and output intervals.
- Preparing and maintaining the larger anchor state.
- Executing downstream attention and all later required updates.

The previous 95-percent candidate agreement used a different code comparison.
It compared old calibrated codes with retained calibrated codes.
It does not establish the sparsity of retained codes relative to fixed nearest codes.
The latter count must be measured separately before any first-projection saving claim.

The revision 20 leaf does not retain every affine output.
A shifted implementation needs those additional outputs or another certified center representation.
Their preparation and persistent bytes cannot be omitted.

## 5. The next projection usually restores the dense cost

After attention changes, the next affine input generally changes in many coordinates.
Its signed correction requires both terms

\[
(W_1-W_0)X_0^\top+W_1D^\top.
\tag{6}
\]

Sparsity of W1-W0 reduces only the first term.
It does not reduce the second term when D is dense.
A direct evaluation of that second term uses the same nmd product count as fresh projection.
It then adds matrix-change work, bound construction, and state reads.

This is an operation-count comparison for the specified dense correction algorithm.
It is not a universal lower bound on all transformer update methods.
It does not rule out a different exact data structure or fast algebraic representation.

A Jacobian-vector predictor has the same issue.
Its affine derivative still applies a dense matrix to the propagated input change.
The derivative computation also needs nonlinear intermediates and a certified remainder.
Calling this operation a derivative does not remove its work.

## 6. A low-rank condition that would be sufficient

Suppose a verified token-major correction has

\[
D=LR^\top+E,
\qquad L\in\mathbb R^{n\times r},
\quad R\in\mathbb R^{d\times r}.
\]

The predictor computes

\[
W_1D^\top\approx(W_1R)L^\top.
\]

Its multiplication count is approximately mdr+mnr.
It can beat nmd when r is sufficiently smaller than n.
The residual contributes |W1| |E| to Equation (3).
Constructing the factors and proving the residual must fit within the same saving.

The trivial rank bound r<=n does not guarantee a saving.
At r=n, the first multiplication already has the original nmd cost.
A numerical low-rank approximation requires a finite residual certificate.
Observed singular-value decay alone does not certify the complete quantized output.

Nor does an early low-rank change remain low-rank through arbitrary attention.
Entrywise exponential can increase rank.
For example, consider a rank-one real score matrix S with

\[
S_{ij}=(i-1)\log(t_j),
\]

where the positive tj values are distinct.
Its entrywise exponential has entries tj^(i-1).
This Vandermonde matrix has full rank.
Normalizing its rows multiplies it by an invertible diagonal matrix.
The normalized matrix still has full rank.

This example concerns real unmasked softmax.
It refutes a general algebraic claim that softmax preserves low rank.
It does not prove that this particular model or finite causal update attains maximal rank.
The archived changed-prefix note addresses additional structural examples.
The required low-rank property remains a separate hypothesis for the actual finite program.

## 7. Complete-model admission condition

For projection j, let sj count changed matrix entries.
Let rj be a certified predictor rank.
Let nj, dj, and mj describe its dimensions.
Let Tnonlinear include attention, normalization, activation, and residual update work.
Let Tproof include all certified remainder and quantizer checks.
Let Tstate include preparation amortization, reads, writes, and deletion maintenance.

The proposed shifted method has the approximate algebraic work

\[
T_{\rm shift}\approx
\sum_j(n_js_j+m_jd_jr_j+m_jn_jr_j)
+T_{\rm nonlinear}+T_{\rm proof}+T_{\rm state}.
\]

Fresh evaluation has projection work

\[
T_{\rm projection,fresh}\approx\sum_jn_jm_jd_j.
\]

A useful full-model claim requires the complete measured shifted cost below the strongest compatible reconstruction cost.
It also requires sufficiently narrow certified residuals at every accepted stage.
A failure must include its complete replay cost.
The first-projection inequality alone cannot establish that result.

No current theorem proves small rj, small residuals, or cheap nonlinear updates for this model.
No current evidence establishes the displayed complete-model advantage.

## 8. Practical disposition

Keep the original sequential target and its adverse outcomes in the record.
Retain shifted transport as a conditional research route.
Do not spend the remaining pilot allowance on an unstructured dense correction implementation.

A future screen should first inspect archived matrix-change sparsity.
It should then test one predetermined low-rank representation of a later input correction.
That representation needs a certified finite residual and a complete work estimate.
Only a successful screen should trigger a full shifted traversal implementation.

The fixed-feature redesign can proceed in parallel under its distinct contract.
It offers a direct retained-feature saving.
Its model quality, complete latency, and novelty remain separate scientific requirements.
