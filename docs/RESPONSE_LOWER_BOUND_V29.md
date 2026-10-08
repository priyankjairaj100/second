# A model-response storage lower bound for calibration deletion

Status: mathematical result and rational software fixtures, 8 October 2026.
No empirical worker, language-model experiment, or novelty search is part of this note.
The result strengthens the interface-specific counting argument in
[FIXED_COST_THEORY_V23.md](FIXED_COST_THEORY_V23.md), Section 3.
It separates actual quantized-model responses, rather than exact metric responses.
It does not prove a repair latency advantage.

## 1. Target and access contract

Use the repository's exact reverse-LDL quantizer with increasing coordinate order,
nearest-grid rounding, and lower-code midpoint ties.
For a retained feature collection, its metric is

\[
H=I+\sum_{r\in R}X_rX_r^{\mathsf T}.
\]

Thus ridge and fixed normalization both equal one.
The features are exact finite values, interpreted as rationals.
The model has one row and three coordinates, with a four-bit grid.
Its scale is the canonical base-only dyadic row scale implemented by
`src/dyadic_row_quantizer.py`, not a calibration-dependent or freely selected scale.
The mathematical oracle is `src/exact_core.py:sequential_oracle`.
The theorem concerns this target's outputs, not guaranteed termination of a bounded native solver.

The original corpus contains the public, ordered record IDs \(1,\ldots,N\).
An archive is prepared from that corpus before deletion.
For every singleton query \(r\), its decoder must return the exact model for the
original corpus with record \(r\) removed.
Every such query refers to the **same original snapshot**.
The proof does not interpret these as successive deletions from shrinking corpora.

The public information may include \(N\), every ID, the target, base weights,
grids, original exact metric, and original calibrated model.
It may not include additional corpus-dependent information for free.
In particular, retained or removed record contents, features, labels, hashes,
lookup tables, corpus-dependent programs, or externally stored bytes count as
archive information or as explicitly permitted record probes.
IDs are the fixed integers above; they do not encode their records' signs.

The primary result assumes a deterministic, fixed-length \(b\)-bit archive and
no record access at query time.
An archive that occupies at most \(b\) bits may be padded to a fixed-length code
only when its representation supplies a fixed-size or prefix-free convention.
Unrestricted variable-length strings of length at most \(b\) have
\(2^{b+1}-1\) possibilities, so that different convention has a different exact bound.

## 2. A canonical four-bit construction with positive margins

Let \(N=2^m\), where \(1\le m\le51\), and put

\[
\epsilon=\frac1{8N},\qquad
w=\left(\frac14,\frac12-\epsilon,7\right).
\]

Consider every balanced sign assignment

\[
\mathcal A_N=\left\{a\in\{-1,+1\}^N:
\sum_{r=1}^N a_r=0\right\},
\qquad |\mathcal A_N|=\binom N{N/2}.
\]

For assignment \(a\), record \(r\) has the two-column feature matrix

\[
X_r=[x_r\ z],\qquad
x_r=(a_r,1,0)^{\mathsf T},\qquad z=(0,0,1)^{\mathsf T}.
\]

The second column is identical and public for every record.
Deleting a record removes both its columns; its only unknown content remains
the one-bit sign \(a_r\).

All features and base weights in this construction are exact finite binary64 values.
The upper limit \(m\le51\) ensures that \(1/2-\epsilon\) is exactly representable;
at \(m=51\), \(\epsilon=2^{-54}\) is the spacing immediately below \(1/2\).
This is a finite-domain theorem, not an unbounded asymptotic claim about binary64.

The canonical four-bit scale is exactly one.
Indeed, the scale routine must cover base weights on codes \(-8,\ldots,7\),
and the required positive scale is

\[
\max\left(\frac{\max_j w_j}{7},
          -\frac{\min_j w_j}{8},0\right)=1.
\]

One is representable at every allowed scale precision, so canonical upward
rounding leaves it unchanged.
Every coordinate therefore uses the same exact grid
\(\{-8,-7,\ldots,7\}\).
The third coordinate supplies the scale-setting weight without coupling to
the other coordinates.
The public second feature column keeps its metric diagonal on the same scale.

For every \(a\in\mathcal A_N\), the original metric is

\[
H(a)=(N+1)I_3.
\]

The original reverse-LDL factors are diagonal and the original model is

\[
Q(a)=(0,0,7).
\]

Consequently the complete original metric and model are identical throughout
the family, even if supplied free to the repair decoder.
The original decisions have strictly positive distance from every finite
rounding boundary: their minimum margin is \(\epsilon\).

## 3. Singleton model responses reveal the assignment

Deleting record \(r\) gives

\[
H^{-r}(a)=
\begin{pmatrix}
N&-a_r&0\\
-a_r&N&0\\
0&0&N
\end{pmatrix}.
\]

Its eigenvalues are \(N-1,N+1,N\), all positive for \(N\ge2\).
No nonidentifiability or singular-metric argument is needed.
The original metric has condition number one, and every retained metric has
spectral condition number \((N+1)/(N-1)\le3\).
Consequently this storage bound does not require ill-conditioned metrics.

For the two-coordinate block, reverse LDL gives

\[
L_{21}=H^{-r}_{21}/H^{-r}_{22}=-a_r/N.
\]

The first decision is \(v_1=1/4\), hence \(q_1=0\).
The declared recurrence is therefore exactly

\[
v_2=w_2+L_{21}(w_1-q_1)
=\frac12-\frac1{8N}-\frac{a_r}{4N}.
\]

If \(a_r=+1\), then \(v_2=1/2-3/(8N)\), and \(q_2=0\).
If \(a_r=-1\), then \(v_2=1/2+1/(8N)\), and \(q_2=1\).
Both inputs lie between \(0\) and \(1\); no saturation boundary is involved.
The third coordinate remains uncoupled, with \(v_3=q_3=7\).
Thus

\[
Q^{-r}(a)=
\begin{cases}
(0,0,7),&a_r=+1,\\
(0,1,7),&a_r=-1.
\end{cases}
\tag{1}
\]

Every retained model decision has margin at least \(1/(8N)\).
This construction does not depend on a midpoint tie.
Its distinguishing margins shrink with \(N\); it does not establish a
constant-margin lower bound independent of corpus size.
Recovering the second output coordinate for all \(N\) fixed singleton queries
recovers the complete sign assignment.

## 4. Exact archive theorem

**Theorem 1: quantizer-specific response information.**
Under the no-record-access contract in Section 1, every deterministic archive
that returns all exact singleton-deletion model responses in (1) needs

\[
b\ge\left\lceil\log_2\binom N{N/2}\right\rceil
\tag{2}
\]

bits in its original fixed-length persistent state.
This remains true when the common original model and exact metric are free.

**Proof.**
Suppose distinct balanced assignments \(a,a'\) have the same stored state.
They differ at some public ID \(r\).
The decoder receives the same state, public data, and singleton query in both
cases, so it returns the same model.
Equation (1) requires different second codes, contradicting exactness.
Thus the archive map is injective on \(\mathcal A_N\).
Its \(2^b\) possible states must accommodate \(\binom N{N/2}\) inputs. \(\square\)

The bound is close to one bit per record.
Since the central binomial coefficient is the largest of the \(N+1\) binomial
coefficients whose sum is \(2^N\),

\[
\log_2\binom N{N/2}\ge N-\log_2(N+1).
\]

The bound is information-theoretically tight for this response family.
An encoder can store the lexicographic rank of the balanced assignment using
\(\lceil\log_2\binom N{N/2}\rceil\) bits.
An unbounded decoder recovers the signs and returns (1).
This upper bound promises neither efficient encoding/decoding nor a useful
general-purpose repair implementation.
It addresses responses from an original snapshot; it does not establish
post-deletion archive erasure, canonical evolving state, or privacy properties.

## 5. A cumulative record-probe tradeoff

Now permit exact probes of individual signs \(a_r\).
One probe reveals one bit; the rest of each two-column feature matrix is public.
The decoder may choose the probed ID adaptively.
Run the fixed singleton query sequence \(1,\ldots,N\), with every requested
model still defined relative to the original snapshot.
The decoder may reuse previous work and probe results.
Let \(k\) bound the **total** number of such probes across this complete query
sequence, on every input and branch.
No other corpus-dependent side channel is available.

**Theorem 2: archive plus response probes.**
For a deterministic exact procedure under this contract,

\[
b+k\ge\left\lceil\log_2\binom N{N/2}\right\rceil.
\tag{3}
\]

**Proof.**
Fix a stored \(b\)-bit state.
All later behavior is a deterministic function of that state and its observed
probe answers; probe IDs and model outputs reveal no additional information
beyond those inputs.
The adaptive procedure is a binary decision tree of depth at most \(k\), with
at most \(2^k\) leaves.
Each leaf determines the complete response vector.
By (1), two distinct balanced assignments cannot both be correct at the same
leaf of the same state.
The \(2^b\) states and their trees can therefore answer at most \(2^{b+k}\)
assignments correctly.
Exactness for all assignments proves (3). \(\square\)

This is not a per-request probe lower bound.
If a service permits \(k_0\) probes for **each** independent singleton query,
the immediate consequence is only \(b+Nk_0\ge\log_2\binom N{N/2}\).
The theorem also does not assert that every \((b,k)\) satisfying (3) is achievable.
The no-probe enumerative construction establishes tightness only for (2).
Record probes are an information measure, not transformer-forward or wall-time units.

## 6. Randomness and finite-probability guarantees

Suppose encoder and decoder may use randomness independent of the assignment,
using the fixed-length \(b\)-bit encoding convention of Section 1 and at most
\(k\) cumulative one-bit probes on every run.
Include all random tapes in one auxiliary random variable.
For any fixed tape, the previous decision-tree argument shows that at most
\(2^{b+k}\) balanced assignments can receive the entire response vector correctly.

If every assignment has probability at least \(1-\delta\) of **all \(N\)
responses being correct together**, averaging over uniform assignments and
random tapes gives

\[
(1-\delta)\binom N{N/2}\le2^{b+k}.
\tag{4}
\]

Thus \(b+k\ge\lceil\log_2((1-\delta)\binom N{N/2})\rceil\), together with
the trivial nonnegativity bound, whenever \(0\le\delta<1\).
The same argument applies if joint success is only an average over the uniform
assignment family.
Zero-error randomized procedures retain (3).
For this fixed worst-case information budget and whole-vector success criterion,
direct counting is sufficient; a weaker Fano inequality is unnecessary.

A per-query success statement must not be substituted for joint success.
If each of the \(N\) singleton responses has error probability at most
\(\eta\), a union bound supplies only \(\delta\le N\eta\); it is useful here
only when \(N\eta<1\).
No independence of errors is assumed.
Expected-length archives, expected probe budgets, approximate numerical outputs,
or a different error criterion require their own coding assumptions and bounds.

## 7. Rational and two-coordinate variants

For any even \(N\ge2\), the same construction and proof hold over exact rational
weights with \(\epsilon=1/(8N)\).
Its base-only grid remains the integer grid because of the third weight seven,
but the shifted weight need not be a binary64 number.
Consequently this rational extension is not automatically an input to the
repository's binary64 row-scale API.
An arbitrary-precision dyadic version permits all power-of-two \(N\), without
the binary64 upper limit in Section 2.

If one supplies an arbitrary fixed integer grid directly to `exact_core`, the
third coordinate and its now-zero public filler column can be omitted.
Then the original metric is \((N+1)I_2\) and the retained metric has condition
number at most three.
Scale one is **not** the automatically derived canonical row scale of the
literal two-coordinate row; the two-dimensional variant has a different
explicit-grid contract.

The still simpler tied choice \(w_2=1/2\) gives
\(v_2=1/2-a_r/(4N)\).
Its original model is constant only after specifying lower-code midpoint
rounding.
Sections 2–4 use the untied construction so that this tie is unnecessary.

## 8. Meaning and limitations

The previous one-dimensional exact-metric example cannot prove a model-response
bound because a scalar metric leaves nearest-grid codes unchanged.
This construction closes that logical gap: the **requested model alone**
separates all balanced assignments, although its original metric and model do not.
It supplies a nontrivial lower bound for one legal fixed-feature quantization
family with canonical row scales and positive decision margins.

The result does not show that real transformer activations realize these feature
assignments, that practical archives need their full factor bytes, that the
current compression codec is optimal, or that exact-factor replay is necessary.
It does not lower-bound full-model wall time, certify publication novelty,
or establish the original sequential GPTQ target.
The source-local features, fixed normalization, and original-snapshot query
interface are essential declared premises.

The counting and binary decision-tree methods are elementary information
arguments, not claimed new information theory.
The contribution of this note is the explicit response-separating instance for
the stated quantizer and the resulting precise scope of its storage claim.
Publication priority still needs a dedicated literature assessment.

## 9. Software fixtures

`tests/test_response_lower_bound_v29.py` independently forms exact ridge metrics
from record features and runs the existing dense rational oracle.
For small balanced families it checks identical original metrics and models,
every singleton response, exact decision values, strict margins, and injectivity
of the complete response vectors.
It separately checks canonical scale one and exact binary64 weights at the
declared domain endpoints.
The fixtures do not implement a new rounding recurrence.
They are regression checks of the declared theorem instance, not a substitute
for the counting proof and not synthetic empirical datasets.
