# Numerical contract

Updated 4 October 2026 for revision 4.

The project now implements automatic response certificates for a declared scalar decoder.
The new decoder defines `V_cert`.
It does not certify arbitrary vendor kernels.

## 1. Three distinct targets

| Target | Neural features | Quantization statistics and decisions |
| --- | --- | --- |
| `E` | A pinned historical finite evaluator | Pinned floating accumulation, factorization, and rounding |
| `V` | The pinned host-libm decoder | Exact rational statistics and fixed-grid decisions |
| `V_cert` | The scalar decoder with proved nonlinear primitives | Exact rational statistics and fixed-grid decisions |

`src/transformer_backend.py` implements the current `V` feature evaluator.
Its nonlinear operations use the pinned host's mathematical library.
Its built-in shortcut proves structural identity only.

`src/certified_transformer.py` implements the `V_cert` feature evaluator.
`src/certified_intervals.py` supplies its proved nonlinear primitives.
This program computes correctly rounded binary64 `exp`, `sqrt`, `erf`, and `tanh` results when rounding resolves.
It does not assume that host nonlinear routines return correctly rounded results.

Equality to one target does not establish equality to another target.
The historical `E` results cannot establish correctness or speed for either exact-statistic target.
The checkpoint adapter does not establish identity with Hugging Face or CUDA execution.

For either exact-statistic target, fix the following items before quantization:

- Base weights and parameter conversion.
- Tokenizer, records, masks, and position conventions.
- Evaluator source, runtime, and operation schedule.
- Quantization grids, coordinate order, and tie rule.
- Covariance normalization and positive ridge.

Let `F_l(prefix, record)` denote the selected finite feature evaluator.
Interpret each returned binary64 value as an exact dyadic rational.
The quantizer uses

\[
H_\ell(R)=\lambda_\ell I+M_0^{-1}\sum_{j\in R}
F_\ell(Q_{<\ell}(R),j)F_\ell(Q_{<\ell}(R),j)^\top.
\]

All sums and products in this expression use exact rational arithmetic.
Reverse LDL and fixed-grid decisions also use exact rational arithmetic.
Neural execution remains finite arithmetic.

The implemented decoders process one unpadded token sequence per record.
Positions start at zero.
Dropout, dynamic batching, cached attention, and custom masks are absent.
Their causal mask always includes the current token.
Another evaluator must declare its own record-local execution contract.
Deleting a record and repacking batches can change that contract.

## 2. Runtime requirements and partial execution

Both scalar decoders require CPython with IEEE binary64 arithmetic.
The current runtime guard supports Linux on x86-64 and AArch64.
It checks round-to-nearest mode and gradual underflow.
It rejects flush-to-zero behavior detected by its probes.
The caller must preserve the floating environment throughout execution.

Public decoder evaluations call this guard.
Automatic chart fitting and jet extraction also call it.
A failed runtime guard aborts the operation.
The implementation does not replace the guard with an assumed tolerance.

The base manifest records source, parameters, configuration, Python, loaded libraries, and processor information.
The certified manifest also records both certified source files and the nonlinear schedule.
This binding defines the declared environment.
It does not promise cross-platform bit identity without the same contract.

`V_cert` is a partial finite program.
Its nonlinear routines refine rational enclosures until both endpoints select the same binary64 result.
The routines have explicit precision and resource limits.
An unresolved rounding boundary raises an error.
A nonfinite intermediate, invalid denominator, or failed primitive also raises an error.
No approximate feature substitutes for that failure.

Provider abstention differs from evaluator failure.
A missing certificate permits retained replay under the declared evaluator.
A primitive failure during replay aborts the request.
The service must not return an approximate model as a successful repair.

Exactness assumes that the required fresh execution belongs to the evaluator's successful domain.
Fallback completion also assumes that every required replay succeeds.
The response certificate does not prove that every possible nonlinear rounding problem resolves within resource limits.
Thus, the project does not claim unconditional totality for all finite weights and inputs.

## 3. Provider obligations

For an ideal node `f_theta`, let `E_theta` denote its declared finite implementation.
A sound provider establishes

\[
\|E_\theta(x)-f_\theta(x)\|\le\nu
\]

for every permitted finite input in the supplied region.
It can instead provide outward output intervals.
Its proof must cover parameter conversion, rounding, precision, exceptional values, and the actual operation schedule.
An unavailable proof returns `UNKNOWN` or an unavailable intrinsic descriptor.

Three provider modes remain valid:

1. Execute the pinned finite program and use its returned bits as exact data.
2. Apply a proved analytic bound for the actual finite schedule.
3. Compose outward intervals with proved primitive bounds.

An unspecified vendor approximation does not satisfy these obligations.
A small observed error does not establish a uniform bound.
A typed witness binds provenance but is not a formal proof-assistant object.

For reference and candidate discrepancy `D`, ordinary node transport gives

\[
D'\le LD+P+\nu_{\rm candidate}+\nu_{\rm reference}.
\]

Here `L` bounds input sensitivity.
The term `P` bounds changed parameters.
Both finite error terms generally remain necessary.
For example, an affine node permits

\[
D'\le\|A'\|_2D+\|(A'-A)x\|_2+\|b'-b\|_2
+\nu_{A',b'}+\nu_{A,b}.
\]

Residual branches use their actual graph topology.
All norm estimates must round outward.

## 4. Implemented finite error bounds

The automatic provider follows the same scalar graph as `V_cert`.
Each jet stores an ideal value interval, first derivatives, mixed second derivatives, and a finite error bound.
It preserves all mixed derivative terms.

For basic binary64 operations, define

\[
u=2^{-53},\qquad t=2^{-1075}.
\]

Within the proved finite range, the provider uses

\[
|\operatorname{fl}(z)-z|\le u|z|+t.
\]

The absolute term covers gradual underflow.
The proof rejects a region whose exact operation magnitude can exceed the largest finite binary64 value.
Multiplication propagates both input errors and their product.
Division requires both ideal and expanded finite denominator intervals to exclude zero.
Nonlinear transport uses derivative bounds over the expanded input region.

These bounds cover the declared scalar schedule only.
They do not cover TF32, mixed precision, fused operations, or reassociated reductions without another proof.

A separate relative-error provider can use

\[
\gamma_m=\frac{mu}{1-mu},\qquad mu<1.
\]

For a sequential length-`n` dot product followed by bias addition, `m=2n+1` is conservative.
That relative model requires normal intermediates or exact zero.
It also requires no overflow.
It does not silently extend to subnormal arithmetic.

Under those premises, an affine bound is

\[
|E_{A,b}(x)-(Ax+b)|\le\gamma_m(|A||x|+|b|).
\]

For `q` token columns, this gives

\[
\nu_F\le\gamma_m
\left(\||A|\|_2\|X\|_F+\sqrt q\|b\|_2\right).
\]

The implemented automatic provider instead uses its explicit absolute-plus-relative arithmetic bound.

## 5. Stable softmax

The finite schedule computes its largest finite score first.
It subtracts that maximum from each score.
It then computes correctly rounded exponentials, a sequential sum, and division.

Every shifted finite score is nonpositive.
At least one shifted score is exactly zero.
Its exponential is exactly one.
Each exponential lies between zero and one.
The finite denominator therefore remains at least one.
For `n <= 2^53`, monotonic rounding bounds each partial sum by its integer length.
This also excludes denominator overflow.

The proof uses the smooth ideal softmax.
It does not differentiate the finite maximum branch.
The ideal Jacobian is

\[
J(p)=\operatorname{diag}(p)-pp^\top.
\]

Its row and column absolute sums equal `2 p_i (1-p_i)`.
Thus, its induced 1-, 2-, and infinity-norms are at most `1/2`.
The provider uses the infinity-norm bound for finite score errors.

Let `D` bound every score's finite error.
Let `S` bound the span across expanded finite score intervals.
The provider requires `S` not to exceed the largest finite binary64 value.
This requirement excludes possible overflow during maximum subtraction.

The implemented conservative bounds are

\[
a=uS+t,\qquad b=a+u+t,
\]

\[
c=nb+n^2u(1+b)+nt,
\]

\[
\delta_{\rm softmax}\le\frac D2+b+c+u+t.
\]

The term `a` covers score subtraction.
The term `b` also covers exponential rounding.
The term `c` covers exponential errors and denominator accumulation.
The final terms cover division.
The implementation rounds the resulting rational bound upward.
For one score, softmax returns exactly one.

Ideal derivative enclosures use a fixed interval shift.
The proof includes the covariance of all score gradients in the second derivatives.
An interval denominator that includes zero makes the descriptor unavailable.
This can happen despite the positive actual denominator.
Such interval overestimation reduces certificate coverage without changing the accepted guarantee.

## 6. LayerNorm and activation schedules

Ideal LayerNorm uses

\[
f(x)=\gamma\odot\frac{Px}{\sqrt{\|Px\|_2^2/n+\epsilon}}+\beta,
\qquad P=I-\mathbf1\mathbf1^\top/n.
\]

For positive epsilon, a global ideal Lipschitz bound is

\[
L\le\|\gamma\|_\infty/\sqrt\epsilon.
\]

The automatic provider follows the actual mean, centering, square, variance, square-root, division, scale, and bias schedule.
Its square operation preserves interval nonnegativity.
It requires a positive expanded square-root input.
A denominator enclosure that includes zero makes the descriptor unavailable.
The ideal epsilon alone does not certify an unrelated vendor variance formula.

The certified decoder supports erf-GELU and the explicit tanh-GELU schedule.
The latter binds its coefficient as binary64 hexadecimal `0x1.9884533d43651p-1`.
It also binds the finite value of `0.044715`.
Its multiplication schedule is explicit in the source.
It does not claim bit identity with the host-libm GELU schedule.

## 7. Automatic response descriptors

The chart has fixed rational directions and a fixed coefficient box.
The caller must select it independently of the deletable corpus.
The manifest records this provenance claim.
The implementation cannot verify that historical selection process.

The provider first converts installed codes using the target's parameter conversion.
It then solves an exact rational system for the finite ancestor weights.
It rejects every nonzero residual and every coefficient outside the box.
It sets free variables to zero.
This choice can reject another feasible representation.
That rejection affects coverage only.

The provider differentiates the ideal feature map on this chart.
It does not differentiate through quantization decisions or the discontinuous finite program.
Center intervals supply response matrices `Z_0, ..., Z_r` and approximation errors `e_0, ..., e_r`.
Box-wide intervals supply a mixed Hessian bound `H` and a finite error bound `nu`.
They establish

\[
\left\|F_{\rm finite}(a)-Z_0-\sum_t a_tZ_t\right\|_F
\le\nu+e_0+\sum_t|a_t|e_t+\tfrac12H\|a\|_2^2.
\]

The omitted-direction term is zero because exact chart fitting rejects unrepresented changes.
No caller supplies an arbitrary numerical tolerance.
The compact service stores grouped response statistics and grouped error statistics.
It does not retain each record's jets or source payload.

Useful coverage remains an empirical question.
Large charts can make derivative extraction expensive.
Deep graphs can produce wide intervals.
Neither exact arithmetic nor a sound bound guarantees a speedup.

## 8. Exact decisions, replay, and audit

Positive rational ridge makes each retained Gram positive definite.
Reverse LDL uses rational arithmetic and positive rational pivots.
Its conditional quantization inputs are rational.
Exact comparisons decide ties under the declared tie rule.
This avoids indefinite interval refinement at quantization boundaries.
It does not remove nonlinear primitive limits from feature execution.

Every repair stage follows this sequence:

1. Bind the evaluator, quantizer, provider, and certified ancestor prefix.
2. Fit the prefix to the fixed chart.
3. Contract intrinsic grouped statistics and certified error bounds.
4. Certify all proposed rounding decisions.
5. Replay required retained groups when a certificate remains unavailable.
6. Abort if the declared finite target cannot execute.
7. Commit the complete canonical state only after successful repair.

Replay uses the same feature target as fresh quantization.
It does not replace `V_cert` with `V` or `E`.
The work ledger includes proof work, source reads, replay, exact arithmetic, state maintenance, and output.
Integer bit growth and serialization costs remain explicit.

Audit data must identify the selected target and provider.
It must distinguish provider abstention from target execution failure.
History-dependent transcripts cannot remain in a state claimed to equal canonical fresh construction.

## 9. Local checkpoint imports

`src/checkpoint_adapter.py` loads local GPT-2 safetensors into `DeterministicDecoder`.
It maps weights and architecture into `V`.
Wrapping that decoder with `CertifiedDecoder` explicitly selects `V_cert`.
Neither step establishes equality with the original checkpoint's vendor execution.

The loader validates shapes, tensor names, attention options, activations, and tied embeddings.
It records configuration and weight hashes.
It downloads no models or tokenizers.
The input manifest must separately bind the tokenizer and tokenized records.

Checkpoint loading remains an eager reference implementation.
Its Python objects can require much more memory than the stored checkpoint.
Its setup reads and conversions belong in complete cost accounting.
No pretrained-model coverage, quality, or latency claim follows from the completed software tests.

See `docs/CERTIFIED_PROVIDER.md`, `docs/AGGREGATE_SERVICE.md`, and `docs/CHECKPOINT_ADAPTER.md` for implementation details.
