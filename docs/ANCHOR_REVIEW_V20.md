# Revision 20 numerical and service review

Status: numerical and service review completed under the stated premises.
This review uses the same project team.
It is not an external review or proof-assistant verification.
No research experiment belongs to this review.

## Required numerical premises

The finite target uses binary64 with round-to-nearest and gradual underflow.
Each affine input coordinate uses separate multiplication and addition.
The nonlinear path must preserve the target's operation order.
All primitive calls must use the declared correctly rounded backend.
Every intermediate must remain finite.

An error bound concerns numerical values.
It does not establish signed-zero byte identity.
The state must store fixed anchor bytes or separately establish current factor bytes.

The zero-error shortcut is valid for numerical values under identical finite operations.
Division still needs a denominator domain that excludes zero.
Every square-root domain must remain nonnegative.
Every bound conversion must round upward or reject the result.
An upward adjacent value can overflow at the largest finite binary64 value.
That case must reject the bound.

## Required state premises

Anchor preparation must use a fixed model without calibration-dependent ancestor weights.
The implementation selects nearest codes from fixed base weights and target grids.
Its target metadata retains the declared original normalization.
Thus independence concerns calibration values, conditional on that frozen target metadata.
Each record must bind its complete token sequence.
Each trace must bind the decoder, primitive backend, and trace construction version.
Serialized traces need shape, node, reference, and finite-value checks.
Hashes detect corruption and mismatches.
Hashes do not prove that an untrusted trace was computed correctly.

Deleting records must restrict the fixed trace set.
Fresh construction on retained records must create the same canonical trace bytes.
The new state family must remain distinct from current-prefix factor storage.
Numerical boxes must not replace exact factors in that older family.

## Required cost accounting

Charge complete anchor preparation once in the declared lifetime comparison.
Charge stored traces, summaries, and outputs as auxiliary storage.
Charge parsing, validation, matrix scans, bound propagation, and box construction for each request.
Charge rejected certificates before charging their fallback work.
Charge repeated stage visits when exact fallback cannot resume from an earlier frontier.
The strongest fresh comparator receives every compatible shared kernel improvement.
Single timing observations cannot establish a reliable speed advantage.

## Findings and fixes

The reviewed formulas establish conservative errors under their stated finite arithmetic premises.
No numerical counterexample appeared in this review.
This conclusion assumes trusted prepared leaves and trusted request contexts.
It does not validate fabricated summaries or mutated context objects.

The provider preserves the scalar calibration schedule.
The review checked normalization, attention, both activations, projections, and residual placement.
It also checked the final stopping point.
The provider stops before the final projection output and language-model head.
It therefore covers complete calibration features, rather than complete prediction outputs.

The review found three integration issues.
The initial experiment caller supplied a mapping instead of the required complete code tuple.
The caller now uses the required representation.
The initial service replaced earlier records' work counters with later records' counters.
The service now stores each record's counters and sums them.
Singleton boxes initially used the reference solver even when the service selected the native solver.
Singleton boxes now use the same selected point solver as exact replay.

The review also found an unnecessary square-root primitive call.
The provider removed that call before experiment admission.
The revised affine recurrence initially omitted the earlier fixed-bias hash check.
Trusted preparation still supplied the correct bias under the declared premises.
The provider restored explicit bias shape, finiteness, and hash checks before experiment admission.
This fix also rejects an accidental mixed-summary call.

The state family correctly separates fixed anchor bytes from current-prefix factor bytes.
It stores exact packed model codes and fixed source-local leaves.
It does not persist approximate transported factors as exact current factors.
The service counts all stages traversed during later exact replay.
Therefore an earlier accepted box cannot falsely count a later traversed stage as avoided work.

The final focused log reports 42 passing software tests.
The log is `pilots/v20/software-tests.txt`.
This is not a complete project test-suite run.
Four tests in `tests/test_anchor_review_v20.py` target numerical edge cases.
They include 16 scalar operation cases with explicit finite endpoints.
They also test denominator rejection, square-root rejection, overflow rejection, and signed-zero semantics.
These numerical review tests use the MPFR primitive backend.
The complete provider fixtures compare calibration factors with the separate scalar decoder interface.
The complete service fixtures compare exact models and canonical state bytes.
These fixtures do not provide real-data acceptance or speed evidence.

## Two-point obstruction for centered boxes

Fix the stage weights, grids, ridge, normalization, factor order, and exact quantizer schedule.
Write the resulting deterministic row quantizer as $Q$.
Let $Z_0$ be the stored anchor factor.
Let $Z_1$ be the exact retained factor under the verified target prefix.
Suppose the exact outputs differ:

\[
Q(Z_0)\ne Q(Z_1).
\]

Then no set containing both factors admits one constant exact quantizer output.
Otherwise that constant would equal both displayed outputs, which is a contradiction.
One differing coordinate in a fixed output-row subset suffices.
The row scales and row independence must remain unchanged during that subset comparison.

Every symmetric interval centered at $Z_0$ contains $Z_0$.
Every valid such interval must also contain $Z_1$.
A verified differing-output witness therefore rules out constant-code certification over every such interval.
This conclusion includes the tightest valid symmetric interval.
Reducing conservative rounding terms cannot remove this obstruction.
The implication also holds when a provider rejects before producing its interval.

This is a conditional theorem, independent of whether the registered screen finds a witness.
The screen must use certified endpoint codes before applying the theorem.
The theorem does not rule out shifted centers, correlated domains, different anchors, or exact refinement.
It does not establish a general lower bound for deletion repair.

## Concrete alternative after a centered-box rejection

A shifted affine center can remove a large deterministic weight-change term from the uncertainty radius.
It needs stored fixed-anchor inputs and affine outputs.
For a target matrix $W'=W_0+\Delta W$, consider

\[
C=Y_0+\Delta W X_0+W'\Delta X_{\mathrm{approx}}.
\]

Here $Y_0$ is the stored finite anchor output.
The center is a proposal, not an algebraically identical finite target execution.
A separate certificate must cover the target's ordered rounding and the residual input change.
That residual contributes a bound for $W'(\Delta X-\Delta X_{\mathrm{approx}})$.
Sparse matrix changes or a low-rank input correction can reduce the center's computation.
Dense input corrections generally recover the original affine cost.
Later transformer blocks can produce such dense corrections.

This alternative therefore needs a prospective correction-cost and residual-bound screen.
It must charge the additional anchor output storage and its preparation.
It must compare against the same optimized reconstruction kernels.
The current implementation does not provide this alternative.
This review establishes neither its useful acceptance nor its complete-model speed.

## Reviewed source hashes

These hashes identify the final reviewed files before the registered screen began.

| File | SHA-256 |
|---|---|
| `src/anchor_transformer.py` | `2684520ff962d80f36c9c3da60f20dfeb89d0fc2e8fc288a04d370694433828a` |
| `src/anchor_affine.py` | `4fb7c9fbb3e21995a649dd1c14c7dfd539316998f5327ef5234262759c72c289` |
| `src/anchor_service.py` | `bb9de01e7180f93e669332883b573045bda11770acbd515714dfa3b229d5acd7` |
| `src/anchor_state.py` | `d0138b6cb45c6aeedb6ac5502ddb14136adddea266ec2647da02a198eb00ae7c` |
| `tests/test_anchor_review_v20.py` | `8ad3886d463b1798199809932622538bd2ce6ad281b148e7347257465806efc6` |
| `tests/test_anchor_transformer_v20.py` | `8853010c41847fa1970ddb08373c63cc58c71369cdd1b181af149eef034bf000` |
| `tests/test_anchor_service_v20.py` | `9344faf38def4e25d9b8e9f7f360cd611c7cc76f3b332d1520688e4d054c42b8` |
