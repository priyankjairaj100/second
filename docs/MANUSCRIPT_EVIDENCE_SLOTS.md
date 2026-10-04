# Evidence specification for the prospective manuscript

Companion to `MANUSCRIPT_DRAFT.md`, 4 October 2026. This document defines how its unfinished result sentences and displays can be filled. It does not create an empirical protocol, change the frozen feasibility policy, authorize experiments, or certify that the required sources already exist. The current real-data evidence slots are **empty**. Software fixtures, historical chat statements, and recreated earlier results are ineligible.

## 1. Draft sentence bindings

| Marker | Exact sentence obligation | Required evidence and rejection rule |
| --- | --- | --- |
| A1 / S1 | Name the actually evaluated target, model/checkpoint, corpus, and complete workload. | Final real-source/target table T1 below; verified local hashes, source partition and root manifests, frozen configurations/inventories, supported runtime and finite execution. Candidate catalog metadata cannot fill this sentence. |
| A2 / I1 | State the principal complete-cost result, including denominator, comparator and uncertainty. | T2 primary request table plus T3 lifetime table; artifact-verified clean observations and planned failures. No speed wording if a required boundary, output contract, preparation, or eligible comparison is missing. |
| A3 / R3 | Explain whether changed-prefix certificates avoided actual retained feature work. | F2 complete group-level denominator and T4 cost/storage controls, from independently bound diagnostic replicates. Zero changed-ancestor denominator or capped/missing events supports an inconclusive mechanism statement. |
| R1 | Report ordinary model-only versus repair latency, alongside indexed comparison and full-state oracle. | T2 plus full failure appendix. A gain against direct full-state reconstruction alone cannot fill an ordinary-speed sentence. |
| R2 | Report preparation-inclusive savings or loss over the fixed ordered horizon. | T3 and F3; each system's original output preparation, every required request, final balance, incomplete horizons. Do not use the best observed crossing or a shared model-only zero preparation. |
| R4 | Report useful absolute NLP quality and the effect of calibration deletion. | T5 heldout/task table with base/original/retained outputs, exact model agreement, identical evaluation inputs and a prospectively selected application metric. Matching a poor oracle is not useful quality. |
| C1 | State the strongest conclusion justified jointly by exactness, mechanism, resources, quality and complete cost. | All applicable slots and the unresolved-obligation list. The conclusion must narrow when any central empirical condition fails; theoretical conditional guarantees may remain. |

Suggested result sentence forms are templates only; bracketed values must remain visibly unfilled until the evidence passes its checks:

- Positive conditional request result: “Across [eligible roots/requests] of [planned roots/requests], the conditional geometric mean complete-transaction ratio of model-only fresh to repair was [estimate, root interval]; [failure counts and reasons] remained outside that conditional ratio.”
- Negative request result: “Exact completed repairs did not establish a complete-transaction advantage over model-only fresh under [scope]; [measured cost category or unresolved evidence] limited the comparison.”
- Lifetime result: “At the fixed [H]-request horizon, complete repair lifetime was [lower/higher/incomplete] relative to independently prepared model-only fresh on [root counts]; [final balance distribution] includes preparation and state output.”
- Mechanism limitation: “The changed-ancestor mechanism was [not demonstrated/inconclusive] because [zero denominator, unavailable domain, complete replay, or incomplete diagnostics], despite [separately verified exactness if applicable].”

The final manuscript must not silently omit a negative branch of these alternatives.

## 2. Exact empirical display sources

All raw paths below are **path patterns**, not existing empirical artifacts. `REQUEST_OUT`, `SEQUENCE_OUT`, and inventory paths must point to a frozen real-data release. Every released derived table must bind the exact source files, inventory/protocol digests, source revision and analysis settings that produced it.

### T1 — Target, sources and supported domain

**Intended caption:** “Declared numerical target, source partitions, calibration workloads and supported execution conditions. Sizes are realized planned units; excluded or unsupported configurations remain listed.”

**Rows:** every frozen primary configuration and predeclared control, with unsupported configurations visibly marked. **Columns:** model revision and local checkpoint digest; prepared corpus/pool and tokenizer digests; calibration records/tokens; original normalization and fixed ridge; grids and stage order; record boundaries; chart/family/tier/verifier; runtime contract; thread/affinity/worker limits; successful/aborted finite execution and reason.

**Required sources:** actual checkpoint/tokenizer/pool/document-boundary manifests; generated target manifest; source-bound run and sequence manifests; frozen measured inventory; saved root memberships; preflight and actual worker receipts. `configs/source_catalog_v1.json`, `configs/runtime_reference_v1.json` and `configs/protocol_v5.json` are planning/reference inputs only and cannot substitute for those realized artifacts.

**Verification:** reconstruct the declared target from the bound checkpoint; verify original token counts and fixed post-deletion normalization; demonstrate the declared document/record disjointness and required duplicate-content/token-sequence overlap checks across protected phase pools; confirm the source law and immutable selection before outcomes. Runtime identity does not establish identical physical hardware, load or OS caches. A parameter-count estimate does not establish memory fit.

### T2 — Exactness, failure and complete request cost

**Intended caption:** “Complete request transactions under the frozen primary inventory. Ratios condition on exact clean completion in every paired repetition; all planned outcomes remain in the denominator.”

**Rows:** configuration × phase × request family, plus the prespecified pooled primary stratum; retain controls separately. **Columns:** planned/attempted/exact/failed/missing requests and roots; failure types; complete per-method median durations; model-only/repair and indexed/repair ratios with root uncertainty; full-state oracle cost clearly labeled; state equality applicability; clean timing eligibility.

**Exact source chain:**

1. `calibration-measured-campaign-v1` inventory and final bound protocol.
2. `REQUEST_OUT/runs/RUN_ID/result.json` (`calibration-measured-comparison-v1`) and its immutable referenced tree.
3. `methods[METHOD].timing_receipt_path` and `timing_receipt_sha256`; child receipt, model/state references; observer/child instrumentation records and original observation identity.
4. `src.measured_analysis.load_measured_campaign_evidence(...)`, followed by `analyze_verified_evidence(...)` or `analyze_measured_campaign(...)`; export the returned `calibration-measured-analysis-v1` payload with its `evidence_sha256`, settings and all planned slots.

Use verified evidence `slots[*].methods[*].outcome`, `wall_ns`, `observed_wall_ns`, `exact_model` and applicable `exact_state`, not a manually edited convenience summary. The analysis rechecks complete accounting partitions and actual output artifacts. Observer bootstrap and measurement-manifest preparation precede the declared interval; final observer snapshot/receipt writes follow it. These exclusions must remain visible beside the complete declared-transaction label. It rejects reused original observers across planned repetitions. A completed worker or an equal hash string without the required verified source chain is insufficient. The current analyzer deliberately leaves empirical attainment false: source provenance and non-timing paper gates require additional evidence.

### T3 — Original preparation and fixed-horizon lifetime

**Intended caption:** “Attributable system costs over the complete ordered deletion horizon, including each system's original output preparation. Research oracle/equality/quality costs are shown separately, not added to one comparator alone.”

**Rows:** every planned root × sequence × repeat before aggregation, with a root-level presentation derived from those rows. **Columns:** original canonical preparation; original model-only preparation; repair, indexed and model-only request sums; complete lifetime; final model-only-minus-repair balance; failed/unstarted terms; separate oracle, quality and research orchestration costs where measured; stored state bytes.

**Exact source chain:** frozen `calibration-measured-sequence-campaign-v1`; `SEQUENCE_OUT/runs/RUN_ID/result.json` (`calibration-measured-sequence-v1`); `preparation.repair` and `preparation.model_only_fresh`; each `steps[i].methods` row and original observer; lineage/state commitments; `load_measured_sequence_evidence(...)` and `analyze_measured_sequences(...)`. Analysis must rederive preparation and every request from their observers, rather than trusting `lifetime` totals.

Repair/indexed fresh may share one indexed preparation observation because it represents the same original output requirement; count it once in each system total and disclose the correlation. Model-only preparation must be a separate positive complete original-model observation. It cannot use retained-only preparation, the full-state oracle, an absent term or zero. A failed/missing required term makes complete lifetime null; report observed consumed costs alongside that null, never as the completed lifetime. This sum is not elapsed wall time of the research validation harness.

### T4 — Storage, proof work and mechanism controls

**Intended caption:** “Complete costs and response-information tradeoffs for the declared state families and certificate controls. Rational-slot counts are theoretical; bytes, peaks and times are measured separately.”

**Rows:** compact response, full quadratic response, fixed-reference, identity-only/full replay, optional interval portfolio, and original-model Gram cache only where prospectively included. Never add an unmeasured favorable configuration after inspecting confirmation. **Columns:** state schema; rank/group counts; theoretical response/error slots; serialized index/model/metadata bytes; preparation and deleted extraction costs; exact arithmetic diagnostics; changed-prefix membership; proof attempts; retained target-feature evaluations; replayed groups; candidate/refactor attempts; complete request and lifetime costs.

**Sources:** actual plan/target/chart payloads; persisted complete state artifacts; child operation ledgers; matched diagnostic `StageAudit` and group records; observed worker RSS/CPU/artifact receipts; separate arithmetic endpoint audit if used. Theoretical slots come from `TARGET_CONTRACT.md` and the formulas in draft §3.2; they must appear in distinct columns from empirical memory. Transient rationals, old/new state coexistence and hidden integer temporaries are not implied by slot count or endpoint totals.

**Bridge:** `src.feasibility_archive.assemble_feasibility_evidence(policy, clean_verified, diagnostic_verified)` can derive supported group coverage and matching output evidence from loader-issued archives. Reject omission/saturation, unbound group membership, mismatched ancestor maps and missing actual feature counts. Some provider causes remain opaque; “unknown” cannot be plotted as zero cost or successful proof. The archive bridge consumes verified snapshots of the complete trusted protocol ledger and all regular files under supplied campaign output roots, including nontransaction files. Missing ledger, storage or diagnostic evidence remains explicit; this scope does not establish project/global resource use or physical disk allocation. Scientific workload provenance remains independently unestablished by those archives, so the bridge cannot currently issue an empirical promotion from them alone.

### T5 — Absolute and retained-oracle NLP quality

**Intended caption:** “Language-model quality under the declared numerical and inference contracts. Exact retained-oracle agreement and absolute application quality are separate outcomes.”

**Rows:** base fixed model, original calibrated model, retained model-only/direct outputs, repaired model; each relevant root/request with fixed aggregate rules. **Columns:** heldout corpus and token-count bindings; finite summed/mean NLL and perplexity when defined; retained-minus-base mean NLL; equality to the retained oracle; selected application metric with its frozen implementation, sample count and uncertainty; finite-evaluation failures.

**Sources:** dedicated `quality_evaluation` child/observer receipts and output artifact; actual heldout digest, evaluator identity, scored tokens and bound model/state references; `load_measured_sequence_evidence` or request evidence quality projections; independently bound application evaluation artifacts once implemented and frozen. The quality worker supports local diagnostic NLL only. A prospective task name is not a task result, and native-framework quality cannot be inferred from this evaluator.

The unchanged feasibility policy tests every root/request against mean-NLL increase `log(6/5)` with identical positive token counts. The rational threshold enclosure concerns saved finite observations only. It does not certify their underlying computation or population quality. Missing, nonfinite or mismatched metrics are inconclusive.

## 3. Figures and their derivations

| Figure | Exact content and derivation | Interpretation boundary |
| --- | --- | --- |
| F1 — Method schematic | Original/counterfactual quantization DAG; highlight new certified ancestors; intrinsic retained moments → covariance enclosure → code certificate or retained replay → canonical commit. Draw from Algorithm 1 and theorem assumptions, not observed frequencies. | Conceptual diagram only. Label unavailable proof as replay and target-evaluation failure as abort. Do not depict all stages accepting or the old prefix staying fixed. |
| F2 — Changed-prefix mechanism and cost | For each frozen root/request, plot all eligible nonempty retained stage groups against actual retained target-feature evaluation outcome. Add separately measured proof/replay cost or a companion complete-time panel; include unknown/truncated categories and full denominator. | Counts come only from complete matched diagnostic replicas. Acceptance fraction is not cost-weighted avoided work and cannot instantiate equation (8) by itself. Use identical axes/control scopes and retain roots with no demonstrated changed-prefix mechanism. |
| F3 — Preparation debt and complete horizon | From T3's original observers compute `P_R-P_F` at step zero and `D_k=P_R-P_F-sum_{h<=k}(F_h-R_h)` after each planned request. Plot each root and the fixed final horizon; stop at missing required observations and show the reason. | Negative debt means strict attributable lifetime gain at that prefix. An early crossing is not permanent break-even. No extrapolation beyond the frozen horizon without explicitly stated assumptions; no interpolation through failures. |

Generate eventual publication plots from checked machine-readable evidence using standard plotting tools, with source hashes and plotting code recorded. At present F1 can be authored as a conceptual diagram; F2/F3 have no empirical data and must not contain fabricated curves. The current draft does not include stand-in plots.

## 4. Mathematical claim-to-proof map

The main draft changes presentation and numbering, not the numerical target or theorem assumptions.

| Draft result | Existing mathematical source | Required scope and implementation match |
| --- | --- | --- |
| Equation (3), finite response bound | `PUBLICATION_THEORY.md` T1; `reports/theory_algorithm_revision.tex` Sections 18, 22 and 25; `theory_revision/response_moments.txt`. | Ideal map differentiated; actual finite error separately enclosed; all mixed derivatives and domain/residual premises included. Automatic affine provider requires zero residual. |
| Proposition 1, compact enclosure and replay invariant | Publication T2–T3; report Section 21; `theory_revision/linear_gram_response.txt` L1–L16. | Positive-semidefinite omitted Gram and trace bound; fixed positive ridge; exact retained sums; sound outward norm contraction; finite error included. Compact method does not recover missing quadratic matrices. |
| Lemma 2, forced-prefix displacement | Publication T4; report Section 2; `NOVELTY_AUDIT.md` classical reduction. | Same forced preceding code prefix; positive valid relative spectral endpoints; classical constant with no general priority claim; squared exact cell checks. |
| Interval option | Publication T4b; `ALGORITHM_ADVANCE_V7.md` R1–R5. | Valid entry enclosure, fixed ridge, completed interval arithmetic; same-candidate monotonicity only. It is neither a universal faster verifier nor an implemented multi-domain bank. |
| Theorem 3, sequential model and canonical state | Publication T5–T6; report Sections 1, 17, 19 and 24. | Trusted intrinsic state, record-local target, sound accepted premises, checked deletion, topological induction and canonical serialization. Completion additionally requires successful necessary partial-evaluator calls, finite resources and replay progress. |
| Corollary 4, conditional zero replay | Publication implementation-matched compact condition; `linear_gram_response.txt` §11. | Every stage under the newly certified prefix; positive-energy normalized margin; `beta+delta<=lambda/2` and `beta+2delta<lambda*tau`; finite/domain/zero-energy tie conditions. Small deletion size alone supplies none of these. |
| Storage distinction | `TARGET_CONTRACT.md`; publication §5; report Sections 20–21. | Implemented full-matrix rational-slot formulas are not packed symmetric storage, bits or bytes. Quadratic means full Gram polynomial of an affine feature response, not a second-order Taylor transformer. |
| Equation (8), conditional complete work | Publication T7; report Sections 9, 20 and 24. | Positive avoidable work and repair cost, nonnegative budgets, demonstrated common work, every excess charged; not an empirical or distributional speed guarantee. |
| Equation (9), attributable lifetime | `FEASIBILITY_DECISION.md` exact lifetime identity; `MEASURED_SEQUENCE.md`; `BASELINES.md`. | Each system's own original output, complete fixed horizon, no double counting, symmetry of separately reported research costs, incomplete lifetime remains null. |

The paper supplement should carry detailed finite-primitive and matrix proofs, the full state interface and serialization assumptions, and the storage/query obstructions with their oracle models. Software tests check implementations; they do not replace proofs or instantiate real-model hypotheses. The stronger ideal whitened quadratic-radius theorem remains supplementary and must not be attributed to the default quadratic implementation.

## 5. Falsification and manuscript decisions

These are interpretation rules for the existing protocol and fixed feasibility policy, not new thresholds or execution authorization.

| Observed or unresolved condition | Required paper action |
| --- | --- |
| Any false successful code/state certificate or counterfactual mismatch | Stop interpreting latency for that method version; retain the failure, repair the defect, and prospectively revise/revalidate before further claims. |
| Required finite evaluator or real checkpoint cannot complete within declared resources | No completed full-model empirical claim. Report the supported smaller domain or a theory/reference implementation limitation; do not label aborts as successful replay. |
| No actual changed-ancestor groups, or incomplete group denominator | Withhold changed-prefix avoidance evidence. Identity-cache reuse does not substitute for the stated mechanism. |
| Certificates reduce feature evaluations but complete repair is slower | Report feature avoidance and the complete slowdown. Inspect proof/index/output costs; do not replace the primary endpoint with a favorable kernel time. |
| Repair beats full-state fresh but fails to beat model-only fresh | Withhold ordinary-requantization speed claim. The result concerns a different state-building comparator. |
| Repair ties or loses to equally indexed fresh | No deletion-exclusive solving advantage. Shared solver benefits and interface overhead must be described directly. |
| Request speed improves but preparation debt remains unpaid at the fixed horizon | Report no lifetime gain at that horizon. An assumed future crossing is an explicitly conditional projection, not a result. |
| Retained-oracle agreement is exact but absolute quality is poor or no relevant task is evaluated | Do not claim useful NLP relevance; report target fidelity separately and retain the application limitation. |
| Some planned methods/roots fail or are missing | Preserve all outcomes. Conditional ratios may be reported with their denominator, but no reliable-speed claim from a favorable surviving subset. |
| Diagnostic instrument caps, opaque causes or unmatched code/state outputs | Treat the affected mechanism quantity as unknown/inconclusive; never impute zero work or map a capped sample to the whole workload. |
| Lower confirmatory speed interval is not strictly above the frozen 1.05 threshold, or precision/provenance is unresolved | No reliable population-speed statement. Report the observed conditional interval and unresolved assumptions. |
| Updated prior art directly matches the proposed contribution | Narrow or revise the contribution and attribution before submission. Existing non-discovery is not proof of novelty. |

## 6. Release and citation obligations

Before replacing an evidence marker, save the final raw and derived artifacts, frozen inventory/protocol/source/runtime digests, analysis command/settings, complete planned denominators and failure records, and the exact figure/table derivation. Freeze the interpretation against those artifacts. A successful script return or a prospective protocol field cannot substitute for verified evidence.

`MANUSCRIPT_DRAFT.md` R1–R10 are local labels mapped from `NOVELTY_AUDIT.md` and the existing report. They are not a finalized bibliography. Recheck the current primary literature, exact titles/authors/versions and contribution boundary before submission; archive that audit. In particular, attribute matrix geometry, summation-form deletion, polynomial sufficient statistics, whole-algorithm sketches, neural Taylor verification and state/history semantics. Do not claim to introduce those ingredients.

The current draft is substantial writing preparation. The real-source selection, practical theorem regime, empirical evidence, current literature audit, ACL formatting/length, authorship, ethics/disclosure text and final submission checks remain open. This document and the draft do not close K01 or K02.
