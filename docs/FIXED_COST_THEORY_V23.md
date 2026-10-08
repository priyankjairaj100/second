# Fixed-feature calibration: cost, information, and quality theory

Status: mathematical analysis, 8 October 2026.
This note adds no empirical observations.
It concerns the revision 21 fixed-feature target and revision 22 state.
It does not establish repair speed for the original sequential target.
The proposed extensions below have no implementation claim.

## 1. Contract and theorem map

The fixed anchor is independent of every deletable calibration record.
Its finite feature computation is deterministic and record-local.
All grid scales, coordinate orders, normalization, and ridge values are fixed.
These assumptions are part of the numerical target.
Freezing a previously calibration-trained anchor would not satisfy the first assumption.

For stage \(i\), let \(X_{ir}\in\mathbb Q^{d_i\times t_r}\) contain record \(r\)'s exact finite anchor features.
Binary64 features are interpreted as exact dyadic numbers after their declared finite computation.
Define

\[
H_i(R)=\lambda_i I+M_{0,i}^{-1}\sum_{r\in R}X_{ir}X_{ir}^{\mathsf T},
\qquad \lambda_i,M_{0,i}>0.
\]

The stage output is the declared reverse-LDL greedy quantizer applied to \((W_i,H_i(R))\).
Its midpoint rule selects the lower code.
The current native solver certifies this rational target or reports unresolved computation.
It does not define ordinary floating-point accumulation as the target.

| Result | Purpose | Scope |
|---|---|---|
| T1: Metric sufficiency | Separate model semantics from stored factor bytes | Same fixed-feature model target |
| T2: Response-information bound | State exactly which deletion queries force storage | Explicit query interface |
| T3: Serialized-state floor | Prevent impossible sublinear transaction claims | Current standalone factor-state schema |
| T4: Lifetime crossover | Count every surviving record across repeated requests | Declared matched work ledger |
| T5: Metric distortion | Measure anchor/deployment reconstruction mismatch | Fixed inputs and certified matrix bounds |
| T6: Guarded selection | Guarantee an anchor-loss improvement opportunity | Explicit optional target change |
| T7: Compressed descriptor repair | Trade intrinsic storage against certification and exact fallback | Proposed state family; same model target |

These statements organize established algebra and interface arguments for this implementation.
They are not independent priority claims.
Their proofs do not establish competitive language quality or measured latency.

## 2. Exact model sufficiency and canonical state

**T1: metric sufficiency.**
Suppose two finite feature collections have the same exact \(H_i\) at every stage.
Their mathematical fixed-feature quantized models are identical.
They need not produce the same revision 22 state bytes.
Successful certified solvers must return that common model.
Equal metrics do not guarantee equal solver work or equal bounded-fallback completion.

**Proof.**
Positive ridge makes every \(H_i\) positive definite.
Reverse LDL with the fixed elimination order therefore has unique positive pivots and unit triangular factors.
The stage recurrence depends only on those factors, fixed weights, and grids.
Induction over coordinates gives identical codes, including all exact midpoint decisions.
Every stage is independent of other calibrated stage outputs.
Thus all emitted model codes agree.

The token-space formula computes the same recurrence through the matrix inverse identity.
Write feature row \(h\) as a token vector \(x_h\).
Its coefficient at coordinate \(j\) is

\[
c_{jh}=x_h^{\mathsf T}
\left(\lambda_i M_{0,i}I+\sum_{k\ge j}x_kx_k^{\mathsf T}\right)^{-1}x_j,
\quad h<j.
\]

Schur elimination of coordinates after \(j\) gives exactly this coefficient in reverse LDL.
Consequently the code recurrence is

\[
v_j=w_j+\sum_{h<j}c_{jh}(w_h-q_h).
\]

This also explains why feature-column permutations do not change the exact model.
The revision 22 schema additionally stores ordered tokens and exact factor bytes.
Equal Gram matrices need not determine those bytes.
For example, flipping every sign in a factor preserves its Gram.
Its serialized factor bytes change.
The same distinction applies to positive and negative zero bytes. \(\square\)

**Canonical moment-state corollary.**
An alternative state may contain exact stage moments, retained membership, and sufficient removed-record access.
Its moment components have the canonical retained-set values after every deletion order.
Canonical deterministic quantization then gives the same model as fresh retained construction.

This corollary requires exact integer or rational accumulation and canonical encoding.
It does not hold for unrestricted floating-point subtraction.
It also requires deleted contributions before erasure, or their trusted recomputation from deleted records.
Record IDs alone generally provide neither.

This alternative preserves model semantics but changes the persistent-state contract.
It cannot claim equality to a revision 22 factor-state file.
An equally indexed constructor receives the same moment access.

## 3. What information must a deletion archive retain?

Fix a finite family \(\mathcal C\) of possible calibration corpora.
Give all corpora the same public record IDs and fixed model metadata.
Let \(\mathcal Q\) be the allowed ID-only deletion queries.
Let \(\operatorname{Ans}(C,q)\) denote the required exact output.
No raw records, features, or other corpus-dependent side information are available at query time.

Define response equivalence by

\[
C\sim C'\iff
\operatorname{Ans}(C,q)=\operatorname{Ans}(C',q)
\quad\text{for every }q\in\mathcal Q.
\]

**T2: response-information bound.**
Any deterministic exact archive must distinguish all response-equivalence classes.
If it uses a fixed \(b\)-bit state, then

\[
b\ge\left\lceil\log_2|\mathcal C/{\sim}|\right\rceil.
\]

**Proof.**
Suppose two inequivalent corpora produce the same archive.
There is a permitted query with different required answers.
The decoder receives identical state, query, and public information for both corpora.
It therefore returns the same answer, contradicting exactness.
The archive needs at least one encoding per equivalence class. \(\square\)

The bound is sufficient information-theoretically if arbitrary tables and unbounded computation are permitted.
One may store the class identifier and use its complete answer table.
That construction offers no efficient algorithm.
Variable-length encodings require their stated coding convention and corresponding counting bound.

**Exact-moment example.**
There are \(N\) named records with scalar features \(a_r\in\{0,\ldots,K-1\}\).
The archive must return the exact retained ridge metric after any deletion set.
The query retaining only record \(r\) reveals

\[
\lambda+M_0^{-1}a_r^2.
\]

Nonnegative \(a_r\) is uniquely determined by that answer.
Every two distinct feature assignments are therefore inequivalent.
An exact ID-only metric archive needs at least \(N\log_2K\) bits.
This is a worst-case interface bound, not a transformer-specific memory lower bound.

**Why that bound does not transfer to model-only output.**
For one-dimensional weights, the positive scalar metric does not change nearest-grid rounding.
The quantized model can be constant across all \(K^N\) feature assignments.
Its response quotient has one class.
Therefore a Gram-query storage lower bound cannot establish a model-query storage lower bound.
Similarly, one deployed model does not establish sufficient information for future deletion queries.
The entire permitted response family determines that question.

This distinction is essential when assessing compressed-state proposals.
Exact model repair may need much less information than exact feature or Gram reconstruction.
Proving that saving requires a target-specific response-separation or certification argument.

## 4. A strict output floor for the current state

Let \(B_X(R)=8\sum_{r\in R}t_r\sum_i d_i\) denote revision 22 factor payload bytes.
Let \(B_Q\) denote emitted packed model bytes.
Additional metadata and token bytes are nonnegative.

**T3: standalone serialization floor.**
Producing a new standalone revision 22 state requires writing at least \(B_X(R)+B_Q\) bytes.
In a byte-access work model, its transaction cost is therefore

\[
\Omega(B_X(R)+B_Q).
\]

**Proof.**
The declared output format contains those literal payloads.
Every payload byte must occupy the new output file.
The bound follows from the output length, independently of the quantization algorithm. \(\square\)

For bounded positive record lengths and fixed stage widths, this is \(\Omega(|R|)\).
Thus complete standalone factor-state repair cannot be sublinear in retained record count.
Avoiding retained neural forwards remains compatible with this lower bound.
Useful constant-factor transaction savings also remain possible.

This statement does not count memory references as copied factor payloads.
Persistent shared leaves, block cloning, or lazy manifests need a different output and storage-access contract.
Their accounting must include referenced objects, authentication, garbage collection, and deleted-object disposal.
Canonical moment-only state also has a different output-size law.
Neither alternative is implemented by revision 22 serialization.

Whole-file validation separately reads every byte when the existing SHA-256 validation path runs.
A checksum does not authenticate arbitrary fabricated factors without a trusted expected digest.
Changing authentication cannot silently remove this trusted-provenance premise.

## 5. Bit cost and the two computational regimes

Exact accumulation is manageable in principle but not free.
Write every finite binary64 feature as \(z=u2^{-1074}\), with integer \(|u|<2^{2098}\).
For \(T\) feature columns, each unnormalized Gram entry has an integer numerator bounded by

\[
\left|\sum_{s=1}^{T}u_{as}u_{bs}\right|<T2^{4196}.
\]

Its required signed width is at most \(4197+\lceil\log_2\max(1,T)\rceil\) bits.
This is a conservative universal binary64 bound.
Observed exponent ranges may permit much smaller exact accumulators.

For rational \(\lambda M_0=p/q>0\), an integer-scaled metric is

\[
q\sum_su_su_s^{\mathsf T}+p2^{2148}I.
\]

The multiplier is positive, so it does not change reverse-LDL rounding coefficients.
Bit widths additionally include those of \(p\) and \(q\).
Updating one scalar total costs arithmetic on this width, not one unqualified machine operation.
Serialization and hashing also scale with encoded bit length.

Exact elimination creates rational coefficients.
Hadamard's determinant bound controls reduced minors of a \(d\)-dimensional integer matrix with \(B\)-bit entries.
Their bit lengths are \(O(d(B+\log d))\).
Fraction-free elimination can exploit these bounds.
This observation does not certify the runtime of the existing bounded fallback implementation.

Two regimes must remain visible:

| Representation and solver | Common scalar arithmetic, before exact fallback |
|---|---|
| Feature factors with \(T\) tokens | \(O(dT^2+pdT)\) for token-space solving |
| Dense exact metric | \(O(d^3+pd^2)\) for dense factorization and rounding |
| Dense metric formation from factors | \(O(Td^2)\) |
| Deleted-side dense metric update | \(O(T_Fd^2)\) |

These counts omit input validation, materialization, and bit-dependent primitive costs.
They also omit unresolved-cell fallbacks.
They describe different implementations of the same exact model target.

When \(T\ll d\), replacing factors with dense moments can increase solver work sharply.
The existing pilot has precisely a small-token regime.
Moment subtraction alone therefore cannot imply a practical improvement.
Any adaptive representation must charge conversion and preserve a shared optimized comparison path.
An unchanged-model certificate may help, but its verification and failure costs also belong in that path.

## 6. Repeated requests and the correct break-even condition

Consider retained sets \(R_1,\ldots,R_m\) from a fixed deletion history.
Use identical model targets, point solvers, and output contracts for every comparison.
Let \(f_r\) be the charged record-local feature preparation work.
Let \(c_r\) be the charged cache access and validation work replacing it.
Let \(s_r=f_r-c_r\); this value may be negative.

Let \(G_t\) include shared solving and common model output at request \(t\).
Let \(O_t\) include every additional indexed-service operation at that request.
Let \(P\) be the additional initial preparation and storage-establishment cost.
All costs refer to the declared work model, not inferred wall-clock timings.

The matched ledgers are

\[
C_{\rm cold}^{\rm life}=\sum_{t=1}^m
\left(G_t+\sum_{r\in R_t}f_r\right),
\]

\[
C_{\rm indexed}^{\rm life}=P+\sum_{t=1}^m
\left(G_t+O_t+\sum_{r\in R_t}c_r\right).
\]

**T4: lifetime crossover.**
The indexed service wins in this work ledger exactly when

\[
\sum_r a_rs_r>P+\sum_{t=1}^mO_t,
\qquad a_r=|\{t:r\in R_t\}|.
\]

**Proof.**
Subtract the two ledgers and interchange finite sums over records and requests. \(\square\)

The coefficient \(a_r\) is each record's number of future retained uses.
It exposes why deletion order and request grouping affect amortization.
This result holds for heterogeneous record lengths and adversarial deletion histories.
No request distribution is assumed.

For equal savings \(s>0\) and \(m\) successive singleton deletions from \(N\) records,

\[
\sum_ra_rs=s\left(mN-\frac{m(m+1)}2\right).
\]

Use this expression only with the actual request and output contract.
Rewriting complete states can make the additional \(O_t\) terms substantial.
Initial factor preparation cannot be charged zero merely because its artifact already exists.

**Comparator equivalence.**
An indexed reconstruction algorithm can execute the same operations as repair when given identical state and requests.
Consequently there is no strict algorithmic advantage over the class of all equally informed constructors.
In the current implementation, repair and indexed reconstruction intentionally share their numerical path.
Their expected tie is a control, not a failed novelty test.
Cold reconstruction and indexed service answer a meaningful different resource question.
They must expose the index's preparation, persistence, and access costs.

If solver choices differ, include their difference in the ledger.
Do not cancel \(G_t\) merely because both methods eventually produce the same model.
Complete measured latency remains an empirical question even when the ledger inequality holds.

## 7. Anchor metric mismatch and a usable quality certificate

Fix one stage and one specified set of examples.
Let \(X\) be its anchor inputs and \(Z=X+D\) its deployment inputs.
They must use matching example order and normalization.
Define

\[
H_X=\lambda I+XX^{\mathsf T}/M_0,
\quad H_Z=\lambda I+ZZ^{\mathsf T}/M_0,
\quad \mathcal R_X(Q)=\operatorname{tr}((Q-W)H_X(Q-W)^{\mathsf T}).
\]

Define \(\mathcal R_Z\) similarly.
These are local ridge reconstruction losses, not token cross-entropies.

**T5: relative distortion.**
If a certified bound satisfies

\[
\rho\ge\|H_X^{-1/2}D\|_2/\sqrt{M_0},
\]

then, for every \(Q\),

\[
\max(0,1-\rho)^2\mathcal R_X(Q)
\le\mathcal R_Z(Q)
\le(1+\rho)^2\mathcal R_X(Q).
\]

**Proof.**
Set \(E=Q-W\) and augment the features:

\[
\bar X=[X/\sqrt{M_0},\sqrt\lambda I],
\qquad \bar D=[D/\sqrt{M_0},0].
\]

Then \(\|E\bar X\|_F^2=\mathcal R_X(Q)\).
Moreover,

\[
\|E\bar D\|_F
\le\|EH_X^{1/2}\|_F\|H_X^{-1/2}\bar D\|_2
\le\rho\sqrt{\mathcal R_X(Q)}.
\]

Apply both triangle inequalities to \(E(\bar X+\bar D)\), then square. \(\square\)

A simpler choice is \(\rho=u/\sqrt{M_0\lambda}\), where \(u\) certifiably bounds \(\|D\|_2\).
This choice can be much looser than direct relative whitening.
A numerically computed singular value alone does not supply a certified upper bound.
Actual deployment inputs or independently proved transport bounds are needed.
Obtaining them has a cost.

More generally, suppose certified constants satisfy \(0<\alpha H_X\preceq H_Z\preceq\beta H_X\).
If a candidate obeys

\[
\mathcal R_X(Q_A)\le\kappa\min_{Q\in\mathcal G}\mathcal R_X(Q),
\]

then

\[
\mathcal R_Z(Q_A)\le\frac{\beta\kappa}{\alpha}
\min_{Q\in\mathcal G}\mathcal R_Z(Q).
\]

The proof applies the upper metric bound, candidate premise, and lower metric bound in that order.
The codebook \(\mathcal G\) must be identical throughout.
Greedy GPTQ supplies no general \(\kappa=1\) premise.
The comparison also holds deployment inputs \(Z\) fixed.
Changing earlier deployed stages can change those inputs and invalidates an unqualified full-model approximation interpretation.

**An a posteriori lower bound.**
Choose any nonnegative diagonal \(D_0=\operatorname{diag}(d_j)\preceq H_X\).
Let \(\delta_{aj}\) be the distance from base weight \(W_{aj}\) to its fixed coordinate grid.
Then

\[
L=\sum_{a,j}d_j\delta_{aj}^2
\le\min_{Q\in\mathcal G}\mathcal R_X(Q).
\]

Indeed, replacing \(H_X\) with \(D_0\) lowers every candidate loss.
The diagonal objective minimizes independently at each nearest grid value.
When \(L>0\), the computable ratio \(\mathcal R_X(Q_A)/L\) is a valid \(\kappa\).
The choice \(D_0=\lambda I\) is always valid but may be weak.
A stronger diagonal minorant needs its own certified matrix inequality.

These bounds do not turn local reconstruction into language-model quality.
For a complete logit comparison, propagation through the actual computation graph must be controlled separately.
Attention, normalization, residuals, and finite-runtime errors cannot be omitted.
Only a proved logit error bound can imply a corresponding cross-entropy bound.
The thirty-prediction development pilot does not supply those premises or population evidence.

## 8. An optional quality guard with explicit target change

The current target always emits its specified greedy result \(Q_G(R)\).
Let \(A\) be the fixed nearest-grid anchor weights for the same stage.
Both candidates belong to the identical codebook.
Define a different stage target by

\[
Q_\star(R)=\operatorname*{argmin}_{Q\in\{A,Q_G(R)\}}
\mathcal R_X(Q;R),
\]

with a fixed candidate tie rule.

**T6: guarded selection and exact deletion.**
This target satisfies

\[
\mathcal R_X(Q_\star;R)
\le\min\{\mathcal R_X(A;R),\mathcal R_X(Q_G;R)\}.
\]

Exact retained moments and exact candidate construction reproduce its complete model after every valid deletion history.

**Proof.**
The first conclusion follows from selection over the two candidates.
T1 makes each greedy candidate a function of exact retained moments.
The two candidate losses are functions of those same moments and fixed weights.
Their exact comparison and fixed tie rule therefore reproduce fresh retained selection. \(\square\)

The candidate bank may include more predefined algorithms with complete deterministic semantics.
All candidate generation and selection costs must be charged.
A candidate fitted outside the declared retained pipeline would invalidate the target claim.

This guard guarantees local anchor-loss dominance only.
It does not guarantee better actual deployment loss or perplexity.
The target digest must distinguish it from revision 21.
It should not be implemented merely to remove an adverse paper result.
An independent quality pilot must justify its additional work.

## 9. Proposed compressed state with the same model target

This extension changes state representation while preserving revision 21 model semantics.
It is not implemented by the revision 22 service.
It is a stronger research candidate than presenting ordinary cached factors as new.
Its novelty and useful cost regime still need investigation.

### 9.1 Source-local descriptor contract

For each record, prepare a deterministic compressed descriptor \(D_r\).
It depends only on that record and fixed public encoding parameters.
It reconstructs a center \(C_{ir}\) and entrywise intervals

\[
B_{ir}=\{X:|X-C_{ir}|\le E_{ir}\}
\quad\text{with}\quad X_{ir}\in B_{ir}.
\]

The inclusion follows from trusted exact feature preparation and verified outward encoding.
Checksums alone cannot establish it for a hostile descriptor.
The descriptor also binds tokens or a declared retained-record retrieval source for fallback.
Encoding decisions fitted to the aggregate deletable corpus violate source-locality unless their selection is also repaired.

A concrete encoding uses a fixed dyadic range \([-A_i,A_i]\) and \(b_i\)-bit cell indices.
Its equal-width dyadic cells have width \(2A_i2^{-b_i}\).
The center error is at most \(A_i2^{-b_i}\) per coordinate.
Boundary conventions and out-of-range values require fixed rules.
An exact escape representation can handle out-of-range values while charging its bytes.
Cell indices, escape bytes, dimensions, and bindings all contribute to storage.
Allowed center exponents must satisfy the chosen finite solver's input requirements.
Alternatively, an exact rational verifier may accept rational centers directly.

Deleting another record leaves every surviving descriptor unchanged.
Construct a canonical compressed state from the sorted descriptors and exact target model codes.
Use a new state family and file magic.
Do not call this state byte-identical to the factor-state schema.

### 9.2 Certificate and fallback correctness

Suppose a verifier receives a candidate \(Q_i\) and the concatenated retained interval \(B_i(R)\).
Its acceptance guarantee is

\[
\operatorname{Accept}(Q_i,B_i(R))
\Longrightarrow
Q_i=\operatorname{Quantize}_i(W_i,X)
\quad\text{for every }X\in B_i(R).
\]

Numerical verification must use exact rational arithmetic or proved outward enclosures.
Candidate centers, floating solves, and empirical margins are not certificates by themselves.
The existing point and box verifiers provide relevant components, not this complete storage service.

**T7: compressed-state exact repair.**
Assume trusted intrinsic descriptors, a sound universal verifier, and exact fallback when certification remains unresolved.
Each accepted candidate equals the fixed-feature target stage.
Each fallback stage also equals that target.
The resulting complete model equals fresh fixed-feature construction.
Keeping only the original intrinsic descriptors yields canonical state across all deletion orders.

**Proof.**
Every true retained factor lies in its prepared interval.
Concatenation preserves the inclusion under the fixed source ordering.
The verifier's universal implication therefore applies to the true retained matrix.
Fallback evaluates the defining finite factors and exact point target directly.
No calibrated stage output changes another stage's fixed feature law.
Thus every output stage equals its fresh target independently.
Sorted source-local descriptors depend only on retained membership.
Together with the identical target codes, they give identical canonical compressed state. \(\square\)

Use request-local refinement only, then discard its temporary factors.
Persisting a history-dependent refinement cache would invalidate the stated canonical-byte conclusion.
A separately specified canonical cache policy could restore that conclusion.
Its cost and storage would need new accounting.

Unbounded exact rational fallback ensures mathematical completion for finite features and positive ridge.
The actual implementation has bounded fallback budgets.
It may report unresolved computation without committing an incorrect model.
T7 must not be read as proving completion of every current bounded worker.

### 9.3 An explicit storage-to-margin condition

Suppress stage indices and concatenate retained centers and entrywise error bounds as \(C,E\).
Choose certified nonnegative bounds

\[
h\ge\|C\|_2/\sqrt{M_0},
\qquad e\ge\|E\|_F/\sqrt{M_0}.
\]

Every represented factor is \(X=C+\Delta\), with \(\|\Delta\|_2/\sqrt{M_0}\le e\).
Consequently

\[
\|H_X-H_C\|_2\le2he+e^2=\delta.
\]

Since \(H_C\succeq\lambda I\), define \(\eta=\delta/\lambda\).
When \(\eta<1\), all represented metrics obey

\[
(1-\eta)H_C\preceq H_X\preceq(1+\eta)H_C.
\]

**Proof.**
Expand the Gram difference as
\((C\Delta^{\mathsf T}+\Delta C^{\mathsf T}+\Delta\Delta^{\mathsf T})/M_0\).
Submultiplicativity gives the operator bound.
The ridge floor gives \(\delta I\preceq\eta H_C\), establishing both Loewner inequalities. \(\square\)

Factor the normalized center metric as \(H_C=L^{\mathsf T}\operatorname{diag}(t)L\), using reverse LDL.
Let the exact center quantizer have decision inputs \(v_{aj}\) and codes \(q_{aj}\).
Define inverse pivots and pre-decision prefix energies by

\[
g_j=1/t_j,
\qquad P_{aj}=\sum_{h<j}(v_{ah}-q_{ah})^2/g_h.
\]

The relative-metric decision theorem gives conditional squared displacement

\[
|v_{aj}(H_X)-v_{aj}(H_C)|^2
\le\frac{\eta^2}{1-\eta^2}\,g_jP_{aj}.
\]

Its exact recurrence and conservative cell test appear in [src/exact_core.py](../src/exact_core.py).
The underlying result and implementation obligations also appear in [PUBLICATION_THEORY.md](PUBLICATION_THEORY.md).

Its condition is equality of earlier codes for that row.
Coordinate induction supplies that condition when all earlier cells certify.
Let \(m_{aj}\) be the minimum distance to the finite boundaries of the center's selected grid cell.
For positive-energy decisions with positive margins, set

\[
\tau^2=\min_{a,j:P_{aj}>0}\frac{m_{aj}^2}{g_jP_{aj}}.
\]

A sufficient strict condition for all these decisions is

\[
\eta^2(1+\tau^2)<\tau^2.
\]

Zero-energy decisions have zero certified displacement.
Their exact tie behavior follows the ordinary lower-code rule.
For saturation, omit the nonexistent infinite boundary.
If no positive-energy decisions exist, every decision has zero displacement under this bound.
Positive-energy midpoint decisions can make this particular sufficient condition unavailable.
They require sharper one-sided verification or exact fallback.

For the fixed-range encoding without escapes,

\[
e\le A\sqrt{dT/M_0}\,2^{-b}.
\]

Thus increasing stored precision decreases this explicit input-error term exponentially.
The resulting bound connects descriptor bits, ridge, feature magnitude, token count, and quantizer margins.
It does not promise acceptance at a fixed bit rate on real data.
The candidate center and its margins can also change when precision changes.
Positive true decision margins and continuity guarantee a sufficiently fine mathematical neighborhood.
Zero margins preclude that general neighborhood argument.

Nested interval refinements monotonically enlarge the set of universally certifiable instances.
A specific numerical verifier need not show monotone success unless it preserves earlier valid certificates.
Its implementation must distinguish mathematical set inclusion from its own enclosure tightness.

These intervals surround the true fixed-feature factors.
They need not contain the different old-anchor endpoint from the revision 20 sequential-transport witness.
Therefore that witness does not reject this encoding proposal.
The same universal-certificate obstruction still applies whenever two factors inside one compressed interval have different exact codes.

### 9.4 Full-model fallback work

Accepted certificates require no retained neural execution themselves.
However, fallback for one late factor may execute earlier accepted stages as prerequisites.
Those operations cannot be counted as avoided.

Let \(\mathcal U\) be the unresolved record-stage factors selected for exact refinement.
Let \(\operatorname{Anc}(\mathcal U)\) contain every fixed-anchor operation required to regenerate them.
With shared traversals, the complete charged request has the form

\[
C= C_{\rm read}+C_{\rm validate}+C_{\rm candidate}+C_{\rm certify}
+C_{\rm replay}(\operatorname{Anc}(\mathcal U))
+C_{\rm exact\ solve}+C_{\rm state}+C_{\rm output}+C_{\rm disposal}.
\]

Initial preparation and compression remain separate lifetime costs.
The avoided neural work is outside the replay dependency closure.
Counting accepted quantization stages alone overstates the saving.
If all stages certify, no retained neural replay is needed.
If every record requires its last-stage factor, almost a full anchor traversal may remain necessary.
An intermediate checkpoint cache changes this closure only by supplying explicitly stored and charged state.

Compressed standalone output still costs its full retained descriptor length.
For fixed positive bits per feature, it remains linear in retained record count.
T7 offers a storage-versus-certification tradeoff, not an automatic sublinear complete transaction.
The matched indexed constructor receives the same descriptors, certificates, and fallback access.

## 10. Publication implications and next algorithm decisions

The strongest current exact claim is complete fixed-target reproduction with source-local reusable factors.
The strongest current storage result is the verified revision 22 representation reduction.
Neither fact establishes reliable full-model speed or a new quantization principle.

The next cost test should preserve three controls: cold replay, indexed reconstruction, and repair.
It should use the same factor backend and numerical solver wherever compatible.
Complete transactions should report model-only and persistent-state contracts separately.
Their numerical model outputs must remain comparable.

A moment backend is justified when its measured retained-scan savings exceed its dense numerical and bit costs.
A persistent-leaf backend is justified when standalone state output dominates the complete transaction.
Both need precise new state contracts and equivalence tests.
Certified compression needs a proof for the requested model response, not an inherited Gram-storage claim.

The optional guard addresses reconstruction quality without pretending greedy quantization solves a global lattice optimization.
Its language-quality value remains unknown.
None of these routes erases the original sequential-target loss.

## 11. Attribution and limits

Cao and Yang's 2015 work already develops unlearning through subtractable transformed-data sums.
Moment subtraction and its basic asymptotic benefit therefore are established ingredients.
Source: [Towards Making Systems Forget with Machine Unlearning](https://www.yinzhicao.org/unlearning/UnlearningOakland15.pdf).

AdaQuant explicitly distinguishes independent calibration from predecessor-dependent sequential calibration.
Freezing each layer's calibration inputs is therefore not a new quantization principle.
Source: [Accurate Post Training Quantization With Small Calibration Sets](https://proceedings.mlr.press/v139/hubara21a/hubara21a.pdf), equations 2 and 3.

Matrix inverse identities, exact accumulation, counting arguments, output-size lower bounds, and norm perturbation inequalities are classical.
Their adaptation here clarifies the service's claims and design choices.
This note does not claim literature priority for those adaptations.
Read the revision 23 novelty audit before selecting a paper contribution.

The conclusions depend on the stated target, trust model, query interface, and output contract.
Changing any of these can change both the proof obligations and the practical comparison.
