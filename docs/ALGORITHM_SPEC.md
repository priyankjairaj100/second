# Implementable specification: transported exact sequential repair

Authoritative theory: `reports/theory_algorithm_revision.tex` and the corresponding PDF.
Revision 4 adds a compact aggregate service with complete fresh and repair operations.
It stores group matrices and fixed-size record bindings.
It preserves the exact sequential model target and canonical repeated deletion.
The numerical provider and checkpoint adapter have separate, explicit execution contracts.
Research experiments remain paused.
Read docs/REFERENCE_SERVICE.md, docs/AGGREGATE_SERVICE.md, and docs/VALIDATION.md for executable scope.

## 1. Chosen target

The primary output remains the sequential retained-data quantizer `Q_seq(W, R)`. The verification references do not replace its calibration inputs. They supply proposals and enclosures; acceptance must prove equality to the true sequential output.

The initial implementation contract fixes rational grids, coordinate order, tie-to-lower rounding, positive ridge, normalization, tokenization, per-record evaluation and a deterministic quantization DAG. Relative damping, activation ordering, fitted scales and dead-column rules require explicit extensions, not accidental inheritance from a package's defaults.

Oracle V uses finite feature-program outputs as exact dyadic numbers, exact moments and rational metric rounding. Oracle E denotes a distinct pinned finite Gram/Cholesky executable. Never compare against E and silently interpret its matches as a V certificate.

The committed state is `A(R) = (Q_seq(W,R), reference_index(R), retained_ids(R))`. The fresh constructor erases the actual sequential Grams and all transient calibration traces. An external retained-only data source supplies records/tokenized inputs to both fresh and repair, and access costs count. If raw records are part of the stored state, include their canonical retained-only representation explicitly.

## 2. Reference index

Fix a finite reference bank before observing deletable calibration data. Suitable examples are base weights W and deterministic weight-only quantized versions of W. A reference trained/calibrated on the deletable corpus is not independent, even if subsequently frozen.

For each reference, stage and stored group, keep exact reference Grams and intrinsic norm/domain summaries. Choose a fixed ID universe or deterministic retained-only structure. Fixed hash-prefix buckets plus canonical sorted ID maps are a simple specification; a dynamic insertion-order tree is not byte-canonical unless normalized at commit.

Typical intrinsic summaries:

- Token counts and sums of squared reference activation norms.
- Group maxima needed to bound individual attention/LN operations.
- Minimum reference centered RMS for local LayerNorm bounds, with a retained-only multiset/index supporting deletion of extrema.
- Exact reference Gram contributions at selected coarse groups.
- Corpus-independent reference/evaluator/grid manifests and record-content bindings.

Storage is explicitly budgeted. Storing every group's full Gram at every tree node costs `O(B N sum_l d_l^2)` values in the extreme. The default design uses a small fixed number of coarse groups; when a finer group's Gram is absent, recovering it is charged reference-side work. A scalar total Gram cannot reveal an absent record contribution.

## 3. Request and transaction

Input: current canonical state `A(S)`, unique valid deletion IDs F, removed-record content or authenticated intrinsic contributions, and retained-only access to `R=S\\F`.

1. Validate membership, uniqueness, content identities and the target manifest.
2. Subtract deleted intrinsic reference contributions exactly. Update retained maps, extrema and group summaries canonically in a pending transaction.
3. Begin exact baseline and/or transported repair using isolated transient arenas. Do not mutate the deployed artifact before a complete result is proved.
4. Commit only the exact retained model and the canonical index/maps. Dispose of all deleted entries, old calibrated traces and losing candidates. Charge serialization and disposal.

The repeated-request proof follows from intrinsic moment additivity and exact model equality. It does not depend on requests being random or non-adaptive.

## 4. Stage engine

```text
certified_prefix = fixed nonquantized roots
for stage in quantization_dependency_order:
    hold all certified ancestors immutable
    choose an available independent reference
    surrogate_gram = exact retained reference_gram(stage)
    unresolved_groups = retained partition
    retries_at_current_resolution = 0

    repeat:
        errors = propagate_sound_group_errors(certified_prefix, reference)
        enclosure = bound_true_metric(surrogate_gram, errors,
                                      exact_replayed_contributions,
                                      damping_and_branch_policy)
        if enclosure is known and positive:
            candidate = exact_or_validated_surrogate_quantization()
            proof = certify_all_candidate_cells(candidate, enclosure)
            if proof accepts and all target branches are resolved:
                accept stage into certified_prefix
                break

        if no unresolved group remains:
            stage_result = exact_target_quantization_from_replayed_gram()
            accept stage_result
            break

        if one bounded precision/tightening attempt is worthwhile:
            perform it; charge its work
        else:
            group = select_an_unresolved_group()
            exact_inputs = evaluate_under_certified_prefix(group)
            replace_that_group_reference_gram_with_target_gram()
            remove_group_uncertainty_and_mark_replayed()
            invalidate_current_candidate_and_all_tentative_descendants()
```

The progress rule must eventually replay a new group. It may not loop forever trying to certify an exact tie. A missing transport proof or unsupported finite kernel returns `unknown`, not a guessed small tolerance. Unknown bounds lead to replay and the finite exact fallback.

Candidate changes at the current stage never change already certified ancestors. Any cached activation is keyed by the complete ancestor identity and is invalid after a relevant prefix change. Residual branches require all incoming boundary tensors, not just the primary hidden-state array.

## 5. Metric enclosure and decision proof

For retained true inputs X and proposal inputs Z, `Hbar = lambda I + ZZ^T/M0`. A sound bound on `E=X-Z` gives

`eta >= ||Hbar^(-1/2) (Htrue-Hbar) Hbar^(-1/2)|| <= 2 a0 e + e^2`,

where `a0=||Hbar^(-1/2) Z/sqrt(M0)|| <=1` and `e` bounds the whitened E norm. Coarse choice: `e <= ||E||_F/sqrt(M0 lambda)` when the right side is itself bounded.

More generally certify `a Hbar <= Htrue <= b Hbar`, with `0<a<=b`. For any forced row prefix, the conditional input displacement is at most

`chi K_i`, with `chi^2=(b-a)^2/(4ab)` and `K_i^2=g_i E_i`.

This shape bound ignores common metric scaling. Use certified spectral intervals rather than trace scores whenever feasible. Ordinary eigenvalue estimates without a rigorous residual/outward bound are not proofs.

`src/exact_core.py` implements the rational local inequality under supplied spectral premises. Its `accepted` field is CONDITIONAL: `spectral_premise_verified_by_module` is always false. A production driver must compose a valid transport/metric proof before treating it as a full certificate. A false but well-ordered pair (a,b) cannot be detected by that local function.

With relative damping, transport the retained trace term as well as the raw Gram. For `H=S+(zeta/d)tr(S)I`, include `(zeta/d)tr(Delta S)I`. Deleted-only subtraction is valid only while retained features are unchanged.

## 6. Adaptive uncertainty reduction

For an unresolved group G, obtain a bound `e_G` on its total Frobenius feature change. Its absolute Gram error is at most

`delta_G = (2 ||Z_G||_F e_G + e_G^2)/M0`.

Sum delta_G over unresolved groups; replayed groups contribute zero. This absolute bound decreases under replay while ancestors/reference remain fixed. Do not claim that a rewhitened bound or a reference switch is monotone.

Largest uncertainty per estimated cost is a selection heuristic. There is no optimality claim. Charge group ranking/index reads and each retry. A reference bank enlarges the union of available certificate routes but can increase actual service latency.

## 7. Optional sparse local repair

Once the true target factor B' is available, maintain sparse injections of code changes:

`v'_i = v_i + b_i + sum_{h<i} B'_{ih}(q'_h-q_h)`.

Use a proved interval for b_i. Emit the one cell containing the full interval; recompute only ambiguous target conditional inputs. Inject each actual changed code into later coordinates. Work is `O(pd+(s+r)d)` after factor/trace/envelope acquisition. This recurrence is implemented in src/sparse_repair.py. Target-factor provenance and external envelope soundness remain explicit premises; validation costs are charged separately.

It is invalid to use this exact-coordinate fallback when the target factor is unknown in transported repair. There the remedy is a tighter enclosure or record replay.

## 8. Scheduling and costs

Report disjoint categories: deleted reference work, retained target replay, reference replay, Gram work, factor work, rounding, validation, index/selection, state/erasure, artifact output, cancellation, and setup. Never add an outer timer to a nested timer.

The baseline gets identical reference/index access and implements identical state/output semantics. It can reuse any truly valid reference contribution. An unoptimized scan is not an information-theoretic comparator.

Weighted dovetail allocates work shares `1/(1+alpha)` and `alpha/(1+alpha)` to fresh and repair. The ideal branch-work bound is the minimum of `(1+alpha)B` and `(1+1/alpha)R`. Add common commit J, packet lag and losing-branch cancellation separately. Losing-branch cleanup is not common baseline work unless it was already prepaid in the comparable branch accounting.

The scheduler bounds regression; it does not prove a positive gain when every route does full work. A theoretical gain requires a certified bound on saved retained work exceeding all additional overhead. Preparation must also be amortized explicitly.

## 9. Required invariants before future execution

- A stage can be installed only after its own branches and all ancestor dependencies are certified.
- Every enclosure names its numerical target, prefix, reference, records, normalization, damping and grid policy.
- Every committed state equals the declared fresh retained constructor, including maps/extrema and serialization.
- Missing proofs cause abstention; midpoint ties trigger exact resolution.
- All fallback and cancellation costs remain in the service ledger.
- No speed, accuracy, privacy, novelty or coverage claim is inferred from passing a conditional local inequality.

The next integration must validate these invariants against an independent oracle before any research timing campaign. The user has not yet resumed experiments.


## 10. Revision 3: response moments and smaller Gram state

Read theory_revision/response_moments.txt and theory_revision/linear_gram_response.txt. Fix the reference/directions/extractor/domain independently of the removable corpus. Intrinsic jets define Z(a)=Z0+sum a_t Zt. Exact quadratic response moments yield a candidate Gram, and squared intrinsic remainder descriptors yield a bound including mixed curvature, residual drift, jet error and the actual finite evaluator. The new certified prefix determines query coefficients; no old calibrated anchor is committed.

The low-storage alternative stores constant and linear Gram matrices plus the scalar tangent Gram. With beta=trace(DeltaZ DeltaZ^T)/M0, the omitted term is between zero and beta I. A shifted raw surrogate Slin+beta I is PSD. The true metric discrepancy lies between -(beta+delta)I and delta I, allowing asymmetric scales (1-(beta+delta)/lambda, 1+delta/lambda). Each replay replaces the selected shifted proposal and removes both of its signed uncertainty budgets. This retains second-order local error while reducing O(r² d²) coefficient storage to O(r d²+r²).

The standalone moment modules use aggregate totals.
The original response adapter stores individual moment payloads in canonical descriptors.
It rebuilds group totals on each request.
That historical path scans `O(N)` descriptors and can store `O(N r² d²)` matrix entries.
Revision 4 implements a separate compact state schema.
The original adapter remains available for correctness comparisons.

The original decoder adapter proves identity of relevant finite ancestor weights.
Its built-in shortcut returns UNKNOWN for other prefixes.
The separate certified decoder supplies automatic response evidence for its supported finite program and parameter chart.
Generic response callbacks still require an explicit proof contract.
Neither interface certifies arbitrary external floating kernels.

No universal advantage over equally indexed fresh construction is claimed. Both comparators must access the same response summaries; setup, index update, projection, factorization, proof, serialization, erasure and all replay count.


## 11. Revision 4: compact aggregate state and transaction

`src/aggregate_response_service.py` implements `AggregateRepairService`.
Its declared state is

`A_agg(R) = (Q_seq(W,R), aggregate_moments(R), record_bindings(R), group_membership(R))`.

The model target remains `Q_seq(W,R)`.
The new logical state differs from the original descriptor-based service state.
The fresh constructor builds intrinsic aggregates and independently evaluates every target stage.
The repair constructor must reproduce every committed state component.

Record bindings contain IDs, content digests, group IDs, contribution digests, and availability flags.
No individual matrix payload or source content remains in committed state.
Group statistics contain constant Grams, linear responses, scalar tangent Grams, and scalar error moments.
For each stage and group, storage uses `O(r d² + r²)` rational entries.
Record bindings use `O(N L)` metadata.
Group membership uses `O(N)` IDs.
Rational bit lengths and model output storage require separate accounting.

The extractor and its parameter directions are fixed before the deletable corpus.
A contribution digest binds the exact response and error payloads.
Deleted source content must be supplied before erasure.
The service regenerates deleted contributions under the fixed extractor.
It checks content and contribution digests before exact subtraction.
A changed contribution or availability marker aborts the transaction.

An unavailable contribution increments a group counter.
A group with unavailable evidence cannot certify through its response proposal.
It must use retained replay.
Deleting all unavailable contributions can restore certification eligibility.
Unsupported stages follow the same replay rule.

The proposal query receives group aggregates and the new certified prefix.
It receives no retained record sequence or individual descriptor.
Its contraction cost depends on group dimensions and response rank.
It does not depend on the number of records within that group.
The service checks the query binding and chart radius.
It checks positive semidefiniteness of the shifted proposal exactly.

The proposal preserves the raw signed enclosure

`-(beta + delta) I <= true_raw_Gram - proposal_raw_Gram <= delta I`.

The engine sums unresolved negative and positive radii separately.
It divides them by the fixed normalization and ridge when constructing relative scales.
Replay replaces the selected proposal with the exact target Gram.
It removes both uncertainty radii for that group.
The exact Gram stays in the candidate metric.
Every failed iteration replays another group.
Finite input therefore reaches exact fallback when certification cannot succeed.

The state manifest binds the aggregate schema and fixed extraction contracts.
Target prefixes retain the original job manifest.
This separates a new state interface from the unchanged model target.
Fresh construction and successful repair produce identical canonical bytes for the same retained records.
Repeated and reordered deletions preserve that equality.
No old calibrated anchor, individual descriptor, or proof history remains in the committed result.

The input object remains immutable throughout the transaction.
The guarantee concerns committed logical state only.
It does not erase caller copies, old snapshots, process memory, or external source records.
The service assumes trusted construction or authenticated state storage.
Digest checks alone do not authenticate hostile state replacements.

The implementation still validates, filters, and rebuilds record metadata.
These steps require `O(N L)` work.
Canonical serialization also writes the complete retained state.
The ledger reports these costs separately from aggregate contraction and retained replay.
Callbacks must not hide individual record payloads in persistent caches.
Fixed model and chart caches require separate storage accounting.

The compact state closes the earlier individual-payload storage limitation.
It does not establish a complete-service speedup.
An equally indexed fresh solver can use the same group statistics.
Future empirical comparisons must measure full service cost and all failed certificates.
