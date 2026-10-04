# Frozen workload contract

Revision 6. Date: 4 October 2026.

This contract defines prospective requests and their immutable inventory.
It does not report empirical results.
Research experiments remain paused.
The tests use mathematical software fixtures.

## Inputs and record boundaries

Each prepared record needs one source document ID.
Each record needs fixed token offsets within that document.
Record construction must not combine text from different documents.
Deletion must not change the remaining chunks.
Deletion must not repack remaining tokens.
The tokenizer, normalization, BOS, EOS, positions, and masks need fixed rules.
The rules must precede request selection.
The prepared manifest must preserve the original record order.

The primary requests select prepared calibration records.
The first real workload should use at most one fixed chunk per source document.
This rule makes primary record counts equal source document counts.
If a workload contains several chunks, source document withdrawal must delete every associated chunk.
`expand_document_deletion` performs that complete expansion.
Do not describe a single selected chunk as complete source document withdrawal.

The workload module does not tokenize text.
It does not acquire a tokenizer or a corpus.
Actual tokenizer files, token hashes, and prepared records remain unavailable.
Those inputs remain a separate preparation gate.

## Phase pools and independent roots

`validate_phase_pools` checks source document IDs and normalized text hashes across three pools.
Those pools cover development, confirmation, and evaluation.
The same document ID or normalized text hash cannot cross pools.
Record IDs and prepared token hashes also cannot cross pools.
One document ID must retain one normalized text hash.
The producer must use one fixed normalization rule before computing these hashes.
This check cannot discover an undisclosed duplicate or a falsely declared source ID.

`sample_roots` samples subsets from a fixed, ordered phase pool.
It samples without replacement inside each root.
It uses a separate stream domain for each root.
Separate roots can share records.
Save the returned pool hash, seed, and complete root membership before testing methods.
Do not discard a root after observing its speed, acceptance, or quality.

The implementation uses a versioned SHA256 counter stream.
Rejection sampling avoids a modulo bias.
Fisher-Yates shuffling supplies subset samples.
Uniformity uses the ideal independent-stream model.
The implemented stream is deterministic pseudorandom computation.
It does not produce independent physical randomness.

## Original-state score preparation

`prepare_original_scores` reads the complete original state and its records.
It verifies every record content hash.
It evaluates each record at the original quantized ancestor prefix.
It includes transitive ancestors in dependency order.
It reconstructs each exact original Gram and the complete decision trace.
It checks the resulting codes against the stored original model.
A mismatch stops score preparation.
The function never calls deletion repair.
It never selects a request using repair outcomes.

For stage \(\ell\), define the original contribution and metric:

\[
C_{\ell j}=X_{\ell j}X_{\ell j}^{\mathsf T}/M_0,
\qquad H_\ell=\lambda_\ell I+\sum_j C_{\ell j}.
\]

The feature matrix uses the original quantized prefix.
It does not use a prefix from a deletion run.

The concentration score is the largest normalized stage energy:

\[
c_j=\max_\ell
\frac{\operatorname{tr}C_{\ell j}}
{\sum_k\operatorname{tr}C_{\ell k}}.
\]

A stage with zero total energy contributes zero.
Stage normalization prevents large feature dimensions from determining the score alone.
The rule measures original feature concentration.
It does not measure output quality or repair difficulty.

The exact leverage is

\[
e_{\ell j}=\operatorname{tr}(H_\ell^{-1}C_{\ell j}).
\]

The producer computes the inverse through exact triangular solves.
For decision \((a,i)\), let \(m_{\ell ai}\) denote its nearest finite cell boundary distance.
Let \(K_{\ell ai}^2=g_{\ell i}E_{\ell ai}\) use the original decision trace.
Define

\[
A_\ell=\max_{a,i}\frac{K_{\ell ai}^2}{m_{\ell ai}^2},
\qquad d_j=\max_\ell e_{\ell j}^2A_\ell.
\]

A decision with zero \(K^2\) contributes zero.
A singleton grid contributes zero because its cell has no finite boundary.
A zero margin with positive \(K^2\) gives infinite sensitivity.
A record with zero leverage contributes zero, including at infinite sensitivity.
The JSON representation uses the string `infinity`.
All finite values use reduced rational pairs.

The difficult score is a stress proxy.
It does not guarantee a changed code, failed certificate, or slow repair.
It has a direct connection to the original-prefix PSD deletion bound.
For total leverage \(\rho<1\), that bound has normalized squared radius

\[
\frac{\rho^2}{4(1-\rho)}A_\ell.
\]

The score retains its leverage and margin factors without the singular denominator.
The score cannot predict later feature changes after an earlier code changes.
No independence assumption between stages is required for its deterministic ranking.

The score artifact contains state, target, record, and producer hashes.
It also contains stage leverage values and margin sensitivity.
It records feature calls, factorizations, wall time, and CPU time.
Charge this complete work to workload preparation.
Do not amortize it silently into a later service advantage.
Save the score artifact beside the frozen workload.
Its hash alone does not reconstruct its contents.

## Primary request laws

Let \(N\) denote the original root size.
Define \(k_s=\lceil N/16\rceil\) and \(k_l=\lceil N/4\rceil\).
Every request below starts from the original committed state.
Selection returns IDs in original record order.

| Request | Fixed law |
| --- | --- |
| Uniform singleton | Select one ID uniformly. |
| Uniform small | Select a uniform subset of size \(k_s\). |
| Uniform large | Select a uniform subset of size \(k_l\). |
| Contiguous | Select the start uniformly from \(0,\ldots,N-k_s\). |
| Concentrated | Select the largest \(k_s\) concentration scores. |
| Difficult | Select the largest \(k_s\) difficult scores. |

Concentration and difficult ties use ascending record ID order.
Infinite difficult scores precede every finite score.
Each uniform selector uses a distinct stream domain.
The six requests can overlap.
Overlapping requests remain separate original-state resets.
They are not separate independent statistical roots.

## Repeated deletion and correctness controls

A separate uniform permutation defines three disjoint small deletion batches.
Batch \(t\) contains permutation positions \((t-1)k_s,\ldots,tk_s-1\).
Every batch size uses the original \(N\).
Each step must start from the preceding committed state.
Compare each result against complete fresh construction on the remaining records.
Compare the final result against the combined deletion from the original state.

Roots with \(3k_s>N\) cannot supply this sequence.
The generated workload marks those sequences blocked.
The current comparison runner also lacks a previous-state sequence interface.
The workload records that separate implementation blocker.
An independently reset cumulative deletion does not satisfy this sequence contract.

Empty deletion and complete deletion are separate correctness controls.
They do not enter the primary latency average.
The current runner rejects complete deletion.
The workload records that blocker instead of dropping the request.
The service can support an empty retained corpus under its separate target contract.
That service capability does not complete the experiment interface.

## Documented source withdrawal

This extension requires real source metadata.
Each record must map to one documented source ID.
Hash the complete mapping before selection.
Let \(S\) contain sources with at least one record and at least one remaining record after withdrawal.
Sort \(S\) by source ID.
Select one source uniformly using its separate stream domain.
Delete every root record assigned to the selected source.

`source_withdrawal_request` implements this law.
It verifies the mapping hash and complete record membership.
It rejects a root without an eligible source.
The producer must document the meaning and origin of source IDs.
The function cannot establish that semantic provenance.
Do not manufacture source labels to create this extension.
The extension remains blocked for corpora without the required metadata.

## Method order and statistical units

The first repeat uses a seeded permutation of the three primary methods.
The next repeats use cyclic rotations.
Each block of three repeats places each method once in each position.
The next block reverses orientation before applying rotations.
Six repeats therefore cover all six method permutations.
Partial blocks retain their fixed prospective order.
They do not guarantee exact position balance.

The order uses only seed, root ID, request ID, and repeat index.
It cannot depend on timing or completion.
Timing repeats remain measurements of the same request.
Analysis must first reduce repeats within requests.
It must resample independent roots when estimating an interval.

## Inventory and circular hashes

`build_campaign` records the complete supplied run sequence.
Every entry binds request membership, metadata, target digest, and method order.
It also embeds the complete run manifest.
The embedded manifest clears only `protocol.sha256`.
Every other manifest field contributes to its binding hash.

This rule removes the inventory and protocol hash cycle.
Use this order:

1. Construct the workload and all run manifests.
2. Build the campaign with `protocol.sha256` cleared in its embedded manifests.
3. Save the campaign as exact `canonical_json` bytes.
4. Insert the campaign hash into the final protocol.
5. Insert the final protocol hash into external run manifests.
6. Verify each external manifest against its inventory binding.

The executor must also verify the final raw protocol hash.
Changing a target, deletion, path, method, or configuration changes the manifest binding.
The inventory includes hashes for every source module and both execution scripts.
The executor compares this complete source set before dispatch.
These hashes provide integrity under trusted storage.
They do not authenticate hostile storage.

`validate_campaign` checks each entry and rejects duplicate identities or paths.
It checks repeat numbering and deterministic method orders.
It rejects unsupported sequence or complete-deletion requests as runnable entries.
It binds embedded workloads to their canonical hash.
Campaign execution separately checks the complete confirmation matrix against the frozen protocol.
The inventory builder alone does not infer missing configurations or root counts.

`analysis_plan` resolves the final protocol hash after freezing.
Its default output contains only primary requests.
Controls and extension groups require a separate plan.
The plan preserves service mode to prevent mixed ablation estimates.

## Completion boundary

The selector equations, edge cases, tie rules, and sequence laws are implemented.
The source-withdrawal law is implemented for documented metadata.
The inventory constructor, binding rules, and analysis projection are implemented.
Their tests do not establish an empirical benefit.

The real prepared source pools and score artifacts remain unavailable.
No real calibration roots or final execution inventory have been created.
No confirmation request was observed or selected.
Actual source preparation, sequence execution, and complete-deletion execution remain open.
