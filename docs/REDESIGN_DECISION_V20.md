# Revision 20: decision after adverse feasibility results

Date: 8 October 2026.
Status: design review, updated with the registered revision 20 screen.
This note adds no research run beyond that archived screen.
It does not establish repair superiority or new literature priority.

## Decision

The current sequential target remains correct but lacks a useful repair mechanism.
The native kernel fixed substantial common arithmetic cost.
The remaining loss needs an algorithm change, not favorable timing selection.

The registered endpoint check found 252 unequal codes among 12,288 checked codes.
Stop symmetric anchor boxes containing both checked points for this root.
Do not build more scalar bounds that retain this same obstruction.
A shifted, correlated center can escape the obstruction.
Its useful cost remains unsupported.

The strongest alternative with a direct work guarantee changes the calibration target explicitly.
It uses fixed feature maps and exact additive moments.
An earlier derivation already specifies that alternative in `theory_revision/deletion_native.txt`.
Implementing that design would be a new research track, not successful repair of the old target.
Its immediate scientific gate is model quality.
Simple subtraction alone cannot supply a strong novelty claim.

## 1. What the adverse results establish

| Evidence | Supported finding | Unsupported extension |
|---|---|---|
| Revision 17 repair: 84.225 seconds | Current repair lost its cold comparison | Every repair algorithm must lose |
| Native cold reconstruction: 71.860 seconds | The shared kernel gives a strong baseline | One observation establishes reliable latency |
| 23 changed complete factors; none reusable | Whole-factor identity reuse failed on this root | Every structured feature update must fail |
| About 95 percent of candidate codes agree | Most checked proposals were correct | Checking them avoided the recurrence |
| Two records; one removed | The root tests a large deletion fraction | The result estimates small-request behavior |
| Current first-stage ancestor change | The identity stream eventually traverses every stage | Every possible decoder frontier has equal cost |

The separate 65.853-second complete-state observation also excludes a demonstrated current speed advantage.
Its timing does not imply that state construction has negative cost.
These runs differ in process conditions and numerical paths.

The coarse-grid quality failure and fine-grid improvement already caused a valid algorithm correction.
The finer target has only a small quality pilot.
The record does not support either a broad quality success or a broad quality failure.

## 2. A decisive obstruction for symmetric anchor boxes

Let `Q_j(Z)` be the exact quantizer at one fixed stage.
Fix its weights, grids, normalization, ridge, and coordinate order.
Let `Z_a` be its fixed-anchor features.
Let `Z_r` be its actual retained-prefix features.
Suppose a proposed box contains both matrices.

**Proposition.** If `Q_j(Z_a)` differs from `Q_j(Z_r)`, that box cannot certify one complete stage output.

**Proof.** A universal certificate must return the same output at every point in its box.
The two specified points require different outputs.
Therefore, no sound universal constant-output certificate can accept that box.

One unequal output row suffices.
The registered check used the first sixteen rows of `block.0000.attn_out`.
It found 252 unequal codes among 12,288 checked codes.
The first witness was output row zero, coordinate 148.
Its anchor code was `0x1.2b32680000000p-2`.
Its retained-prefix code was `0x1.c0cb9c0000000p-2`.
See `pilots/v20/attempt-002/outputs/progress.json` for the complete recorded result.
Such a subset can prove rejection.
It cannot provide complete-stage acceptance when all checked rows agree.
The check must use the same numerical target and row grids at both points.
Store the checked row indices and the first unequal code coordinate.
Store both feature bindings and both exact quantizer outputs.

This proposition concerns a box containing both points.
It does not reject a shifted enclosure that contains only the actual point.
It also does not reject a correlated admissible set that excludes the anchor point.
The anchor point might not represent an admissible current prefix at all.
Including it is an overapproximation chosen by the current provider.

This witness proves that tighter scalar radii cannot remove the obstruction while retaining both points.
Larger deletion-independent anchor caches do not address it automatically.
Changing the candidate code proposal cannot address it either.

## 3. Correct the comparison requirement

A comparator with identical inputs, persistent state, and allowed operations can execute repair itself.
Therefore, repair cannot have an exclusive computational advantage over that entire comparator class.
This follows by assigning the comparator the same program.
It is not a lower bound on either program's runtime.

An equally indexed implementation remains essential for checking the stated access model.
A tie with that implementation is expected when both invoke the same algorithm.
Do not make strict superiority over an identical program a scientific acceptance gate.

Instead, declare concrete baselines and their information:

1. Optimized replay from retained documents, with the shared native kernel.
2. Warm replay with the previous model, when that improves the common algorithm.
3. Reconstruction using retained immutable feature leaves.
4. Repair using canonical aggregates and available deleted contributions.

Give each baseline every compatible optimization.
If a baseline can use the same aggregate update, include that optimized baseline too.
Report the resulting tie as access equivalence.
Claim a measured benefit for the indexed service over replay, if the complete costs support it.
Do not claim that an API name creates algorithmic novelty.

The revision 17 loss against optimized cold replay remains an actual feasibility failure.
Changing the comparison language does not repair that result.

## 4. Ranked algorithm choices

### Rank 1: fixed-feature calibration, with an explicit new target

This route has the strongest direct saving in retained feature work.
Its quality and novelty remain open.

Fix corpus-independent feature maps `X_j` before the deletable corpus is observed.
Keep the current dyadic grids and certified rounding kernel where compatible.
Define each stage metric by

\[
H(S)=\lambda I+M_0^{-1}\sum_{j\in S}X_jX_j^\top.
\]

The stage quantizer uses this metric and fixed base weights.
Upstream emitted codes do not change the feature maps.
Different stages can therefore change codes without invalidating another stage's calibration features.

Store canonical exact aggregate moments and retained membership.
Obtain a removed record's contribution before erasure, or retain its source-local contribution.
Apply

\[
H(S\setminus F)=H(S)-M_0^{-1}\sum_{j\in F}X_jX_j^\top.
\]

Exact dyadic accumulation makes this equality independent of deletion order.
A deterministic certified quantizer then gives the same model as fresh retained construction.
Repeated deletion produces the same canonical state.
Floating subtraction alone does not prove that state guarantee.

For the mathematical work comparison, use the same dense quantizer for both methods.
This isolates feature and moment savings without requiring stable old codes.
However, dense factorization can lose badly when calibration has few tokens.
The current native solver uses token-space factors.
It cannot consume a dense aggregate without an additional implementation.

The cheapest implementation screen should therefore start with cached fixed feature leaves and the existing native solver.
This first implementation saves retained forward work, but still reads every retained feature leaf.
Its equally indexed comparator must obtain the same saving.
It does not yet establish removed-side-only moment repair.
Promote aggregate downdates only if their complete verified solver cost beats that stronger cached-factor control.

Let `f` include fixed feature evaluation and moment accumulation per record.
Let `G` include complete factorization, quantization, verification, and shared output work.
Let `D` include additional repair state costs.
For `n` retained records and `k` removed records, the declared work is

\[
C_{\rm fresh}=nf+G,\qquad
C_{\rm repair}\le kf+G+D.
\]

Thus, repair saves work when `(n-k)f>D`.
This guarantee does not require unchanged codes or positive rounding margins.
It concerns the stated algorithm and work charges, not every indexed comparator.
If both methods receive fixed feature leaves, replace `f` with their actual moment-construction cost.
Charge exact-number storage and arithmetic costs explicitly.
Charge preparation across the deletion sequence.

**Gate.** Freeze one teacher-feature target before further evaluation.
Compare its retained-model quality with the current sequential target and nearest rounding on development data.
Keep the bit budget, grids, evaluation records, and deployment runtime matched.
Set the permitted quality loss before reading those outcomes.
Use calibration reconstruction loss only as a diagnostic.
It does not replace held-out language quality.
Stop this track if quality fails the stated requirement.

**Novelty limit.** Fixed features, quadratic reconstruction, and matrix subtraction are established ingredients.
The repository's earlier audit also identified asymmetric calibration methods.
A strong paper needs a useful quality--storage--repair result beyond those ingredients.
No current result establishes that contribution.

### Rank 2: shifted corrections that preserve the sequential target

Replace the symmetric anchor box with

\[
Z_r\in \widehat Z(\Delta Q)+[-R(\Delta Q),R(\Delta Q)].
\]

The predictor `Z_hat` includes signed changes from the actual repaired ancestor codes.
Its enclosure need not contain the original anchor features.
This removes the specific obstruction in Section 2.
It does not guarantee a sufficiently narrow enclosure.

At an affine node, retain the signed term `DeltaW X_a` instead of replacing it with its magnitude.
Propagate input corrections and correlations through the remaining graph.
Charge sparse products or low-rank products when their actual representation permits them.
Dense code changes do not imply a useful rank bound.
Attention can increase the rank of a low-rank input change.
The existing `theory_revision/changed_prefix.txt` supplies that structural counterexample.

The finite target also needs the separate rounding remainder at every node.
Real identities such as `Y'=Y+DeltaW X` do not preserve arbitrary floating reduction schedules.
A Jacobian proposal alone cannot certify the finite target.
The existing response-moment modules are useful components, not a proved cheap complete predictor.

**Gate.** First compute a static cost ceiling from archived shapes and changed-code counts.
Reject implementations whose predictor already performs the full dense retained traversal.
Then require a verified shifted enclosure that excludes the anchor witness and contains the actual retained features.
Observed containment can expose a bug; it cannot replace the enclosure proof.
Only then admit a bounded real-data certificate screen.

This route preserves the main counterfactual.
It has the highest remaining implementation risk under the current allowance.
Another generic Lipschitz bound is not a new mechanism.

### Rank 3: fixed block entrances

Reset calibration to fixed teacher features at each declared block entrance.
Keep sequential calibration within each block.
This defines a target between stagewise fixed features and full sequential calibration.

Changes cannot cross calibration block entrances.
They can still force retained replay throughout every block interior.
A one-stage block has the additive guarantee above.
A full-model block recovers the propagation problem.
Neither quality nor speed is universally monotone in block length.

**Gate.** Consider this only if stagewise fixed features fail the frozen quality gate.
Use one predetermined block partition.
Do not search many partitions using confirmation data.
Charge all within-block replay and cached entrance storage.

Block reconstruction alone is not a sufficient novelty claim.
The earlier deletion-native note already records the relevant background.

## 5. Rejected shortcuts

- More repetitions cannot remove the identity service's complete traversal.
- Smaller deletion fractions cannot reduce fixed verification work in the current native kernel.
- Smaller deletions also cannot remove a nearest-anchor mismatch caused by calibration itself.
- Partial-row acceptance does not save shared feature generation when another row needs that same feature matrix.
- Early accepted stages do not save traversal if later fallback starts from the model input.
- Temporary old traces need preparation and deletion semantics before reuse can support a lifetime claim.
- A calibrated anchor cannot become source-independent merely because its weights are frozen.
- Approximate repair needs an explicitly different guarantee and an independently checked quality criterion.

These conclusions reject shortcuts, not all variants of the broader methods.

## 6. Immediate disposition

Preserve all previous outcomes and the unchanged CPU allowance.
The endpoint check has completed and rejects the symmetric-box branch for this root.
The provider also rejected its first changed-stage bound because its primitive result bound overflowed.
That numerical rejection is separate from the exact two-point obstruction.
Do not convert this rejection witness into a general transformer impossibility claim.

Revision 21 now implements the first route under a distinct fixed-feature target.
The fixed-feature route offers the clearer work theorem.
The shifted route preserves the stronger existing target.
Neither route currently has sufficient empirical evidence for paper completion.

The project can still produce a positive result.
The present evidence cannot promise that result or its publication value.
A narrower tested claim is preferable to a broad unsupported claim.
