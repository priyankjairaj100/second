# Complete finite anchor bounds for calibration features

Date: 8 October 2026.
Status: implementation and software checks.
This document makes no empirical speed or acceptance claim.

## Scope

`src/anchor_transformer.py` implements every calibration input stage in the declared decoder.
It covers normalization, causal attention, both GELU schedules, projections, and residual addition.
It stops at the final calibration input.
It does not evaluate the final projection output or language-model head.
Those outputs cannot affect a later calibration input.

The numerical target remains the existing finite decoder and fixed dyadic row grids.
The anchor model uses nearest rounding on those grids.
An exact midpoint selects the lower code.
Anchor selection uses only base weights and target configuration.
It does not use the calibration corpus.

## Canonical preparation

`prepare_context` creates the complete anchor model once.
`prepare_anchor` executes its finite schedule once for one record.
Preparation stores immutable stage factors and an ordered operation tape.
Each tape node stores these scalar values:

- Its operation and earlier operand indices.
- The smallest and largest anchor output.
- The smallest absolute anchor output.
- An affine summary index, when applicable.

Affine summaries follow the revision 19 construction.
They store input maxima, product maxima, and ordered accumulator maxima.
They do not store intermediate input arrays.
The persistent affine output field is empty.
The stage factors contain the requested anchor outputs separately.

The record binds tokens, record identity, target, decoder, provider, and anchor model.
The decoder binding includes the primitive implementation and parameter identity.
The provider binding includes its source and helper sources.
Serialization uses sorted ASCII JSON, hexadecimal floats, and little-endian binary64 arrays.
Repeated preparation produces identical bytes under the same bindings.

Hashes detect changed content.
They do not prove that an untrusted party executed the preparation correctly.
The service requires trusted state provenance.
A user-supplied tape is not an authenticated certificate.

## Finite perturbation theorem

Let the stored anchor operand be a.
Let the current finite operand be a'.
Each node propagates an upper bound d satisfying |a'-a| <= d.
A node groups independent entries with the same finite operation schedule.
Its bound applies to every entry in that group.

Set u = 2^-53 and eta = 2^-1074.
For a finite binary64 rounding operation, use

\[
|\operatorname{RN}(x)-x|\le u|x|+\eta.
\]

Suppose real operation results differ by at most D.
Suppose the absolute anchor real result is at most M.
Then their finite results differ by at most

\[
B(D,M)=D+u(2M+D)+2\eta.
\]

The implementation rejects M+D above the largest finite binary64 value.
When D=0, deterministic equality gives an exact zero error.
The equality concerns numerical values.
The proof does not require identical signed-zero bytes.

For addition and subtraction, use

\[
D=d_a+d_b,\qquad M=M_a+M_b.
\]

For multiplication, use

\[
D=M_a d_b+M_b d_a+d_a d_b,\qquad M=M_aM_b.
\]

For division, let m be the smallest absolute anchor denominator.
Require m>d_b.
Use

\[
D=\frac{d_a}{m-d_b}+\frac{M_a d_b}{m(m-d_b)},
\qquad M=\frac{M_a}{m}.
\]

Selections, reshapes, and joins preserve the relevant maximum error.
The maximum operation is one-Lipschitz in the infinity norm.
It therefore preserves the maximum input error.

A correctly rounded primitive with Lipschitz bound L uses

\[
L d+2uR+2\eta,
\]

where R bounds both exact primitive outputs in absolute value.
For tanh, use L=1 and R=1.
For erf, use L=2 and R=1.
The erf constant is conservative.
For exp, evaluate an outward upper endpoint U.
Use L=R=exp(U).
The implementation bounds this exact value from its correctly rounded value:

\[
\exp(U)\le
\frac{|\operatorname{RN}(\exp(U))|+\eta}{1-u}.
\]

Square-root arguments must remain nonnegative.
A positive lower bound l permits L=1/(2 sqrt(l)).
A certified lower bound on sqrt(l) gives the implemented denominator.
When this denominator is unavailable, use |sqrt(x)-sqrt(y)| <= sqrt(|x-y|).
Every primitive call uses the declared certified primitive backend.
An unresolved primitive raises an arithmetic failure.

Affine propagation applies these rules in coordinate order.
It uses the revision 19 product and accumulator summaries.
It scans each changed matrix once per context and stage-code digest.
That scan is shared across records.
The affine bound reads no retained input values.

Induction over the tape proves every accepted error bound.
The final outward interval contains the requested finite stage factor.
A complete valid ancestor prefix is required.
Missing ancestors or different grids cause a binding error.
A numerical rejection does not imply that the actual decoder fails.

## Exact schedule correspondence

Preparation performs elementwise multiplication before addition.
It uses no fused operation or BLAS reduction.
Every reduction follows the declared coordinate order.
Attention preserves each causal prefix and head.
Its maximum shift precedes the certified exponential.
Its probability denominator uses the declared ordered sum.

GELU uses the declared division, erf, and multiplication sequence.
GELU-new uses the declared constant and ordered cubic expression.
Residual addition occurs at the same positions as the reference schedule.
The tests compare complete factors against the separate scalar decoder interface.

## Work and storage

`bound_stage` reads tape summaries and stored output factors.
It does not read token values.
It does not execute retained feature dot products.
It still reads the retained summaries and materializes output boxes.
This work is charged by explicit counters.
No claim treats that work as free.

The bound scans one scalar recurrence per recorded reduction coordinate.
Preparation groups token and output entries where possible.
Attention has separate groups for heads and causal lengths.
Thus tape size can grow with sequence length and head count.
This implementation makes no claim of constant cost per record.

Each scalar bound is rounded upward to binary64 after a node or affine coordinate.
Its rational representation therefore has at most 1,075 denominator bits.
Intermediate formulas have fixed algebraic degree in those bounded operands.
Their bit growth does not increase with tape length.
The largest finite bound and every outward conversion receive explicit checks.

Default limits permit 2,000,000 tape nodes and 4,096 tokens.
They permit 32,000,000 stored factor values and 256 MiB per serialized leaf.
The parser checks graph order, scalar encodings, array dimensions, and byte lengths.
It requires canonical reserialization.
Preparation aborts when its declared resource limit is exceeded.

The context contains request-local matrix changes.
The persistent state contains no request-local matrix change cache.
Surviving anchor leaves remain byte-identical after deletion.
A fresh retained-corpus run reconstructs those same leaves.
Exact model codes and identical surviving leaves therefore give identical canonical state.
The service proves that final composition separately.

## API

```python
context = prepare_context(decoder, target)
anchor = prepare_anchor(decoder, target, record, context=context)
raw = encode_anchor(anchor)
anchor = decode_anchor(raw)
box = bound_stage(decoder, target, anchor, prefix, stage_id,
                  context=context, diagnostics=metrics)
values = anchor_factor(anchor, stage_id)
```

`prefix` is the complete tuple of preceding `StageCodes` objects.
`AnchorBoundUnresolved` denotes a conservative numerical rejection.
`ValueError` denotes an invalid binding or malformed input.
The service must not convert binding failures into successful repair.

## Evidence boundary

Eight original provider tests passed under both declared primitive backends.
A separate fixture run changed the primitive backend before that verification.
The final suite contains nine provider tests under the MPFR backend.
The added test rejects a changed fixed bias.
Four separate adversarial review tests also passed under the MPFR backend.
They cover both activations, two head counts, and two decoder blocks.
They also cover changed prefixes, canonical state bytes, and rejected bounds.
They check that bound evaluation does not call the decoder or read tokens.
They verify shared matrix scans and bounded upward rounding.
These fixtures are software checks.
They are not empirical datasets or evidence of practical speed.

Useful bound width remains an empirical question.
A fixed nearest anchor can remain far from the retained-corpus model.
Even perfect perturbation analysis cannot make that model difference disappear.
The current implementation therefore retains a deterministic exact fallback.
