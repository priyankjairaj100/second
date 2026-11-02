# Focused literature update and contribution boundary

SECOND V43 — FOCUSED PRIMARY-SOURCE NOVELTY / CLAIM REVIEW
Checked 10 October 2026. Read-only review; no repository or campaign edits.

Conclusion
The defensible candidate is a specialized certificate and evidence representation for exact adaptive calibration-code recovery from lossy feature enclosures, together with a precisely specified canonical successor-state contract. Quantization stability, verifier-gated release, fallback retraining, frozen representations, exact sufficient-statistic deletion, and compression for unlearning are already prior art. A successful complete-model pilot with slower compression and a modest storage saving establishes feasibility and a tradeoff, not acceleration, general superiority, useful language quality, or ACL readiness.

Project scope checked
Read docs/CLAIM_BOUNDARIES_V41.md, EXACT_FUN_RETRIEVAL_V41.md, CLOSEST_WORK_UPDATE_V39.md, NOVELTY_AUDIT_V29/V30.md, METHOD_AND_THEORY_MAP_V32.md, ADAPTIVE_COMPRESSED_V30.md, RESPONSE_LOWER_BOUND_V29.md, and the related-work/claim portions of reports/theory_algorithm_revision.tex. V41 boundaries are the operative empirical scope: fixed pretrained checkpoint; deterministic source-local anchor features; fixed grids/order/ridge/original normalization; binary64 values interpreted as dyadics; lower-code ties. This removes calibration-membership influence for that declared constructor. It does not remove pretraining knowledge or reproduce unspecified floating-point/sequential GPTQ.

The historical theory manuscript's section 16 still describes changed-ancestor sequential repair as the defensible contribution. That prose cannot describe a fixed-anchor V43 result without a rewrite. The V29 counting lower bound has an explicit response-separating family, fixed original snapshots and access assumptions; it is not a transformer realization, sequential shrinking-state lower bound, latency theorem, or storage-optimality result. Treat it as supporting conditional theory, not automatic novelty.

1. Exact-Fun full-proof retrieval CLOSED (primary author version recovered)
Conference version: Xiong, Li, Li, Cai, ICDM 2023, pp. 1439–1444:
https://par.nsf.gov/servlets/purl/10525207
https://doi.org/10.1109/ICDM58522.2023.00188
The current author PDF URL returns 404. Its public author-repository history contains the complete 11-page version, recovered and read including Theorem 2, pp. 6–7, Eqs. (29)–(32):
https://github.com/zuobinxiong/zuobinxiong.github.io/blob/300a0672be8d265ddebf20d6e69f790456a1bd81/assets/pdf/ExactFedUnlearning.pdf
Raw:
https://raw.githubusercontent.com/zuobinxiong/zuobinxiong.github.io/300a0672be8d265ddebf20d6e69f790456a1bd81/assets/pdf/ExactFedUnlearning.pdf
SHA256 ae3b7b1d6cabe8e5efda303068224493805c62204e5e235cdfa3c6b1630c54ae (790466 bytes).

Exact-Fun changes training to Q-FL, stores historical models, corrects deleted gradients, compares recomputed quantized parameters, and retrains from the first affected round. Thus discrete stability plus conditional retraining is established prior work. Its Theorem 2 proof assumes uniform within-cell position and independent coordinates; the overlap calculation also uses a uniform perturbation model. A displacement bound alone does not imply that probability formula. Do not use it as a distribution-free fallback-rate prediction. The distinction to pursue is universal certification over an archive's uncertainty set for the declared adaptive quantizer, which can produce changed codes; not the general idea that rounding can hide a deletion. Reading the proof does not validate every implementation, aggregation, or experimental exactness claim in Exact-Fun.

2. Earlier direct overlap: Ginart et al., NeurIPS 2019
Making AI Forget You: Data Deletion in Machine Learning, section 4.1 and Appendix B/C:
https://papers.nips.cc/paper_files/paper/2019/file/cb79f8fa58b91d3af6c9c991f63962d3-Paper.pdf
Quantized k-means saves metadata, verifies whether deletion changes the quantized centroids, updates metadata if stable, and otherwise retrains. It analyzes expected deletion cost under randomized lattices. This predates Exact-Fun and is essential citation support against any first-use claim for quantization-enabled exact deletion, stability verification, or unchanged outputs with updated persistent metadata.

3. ExecCert: broader overlap than a residual-check baseline
Zhao, Wang, Chang, He, From Mathematical to Executable Certificates for Machine Unlearning, v1:
https://arxiv.org/html/2610.02268v1
Read main sections 3–5 and numerical/lifecycle appendices. ExecCert separates candidate generation, release contract and verifier; handles executable residual/inverse-defect certificates, exact-reference transfer, guarded updates/rebuild, decision agreement, and full lifecycle comparisons. Section 4.4 explicitly discusses finite output formats/codebooks, so saying it ignores finite precision or discrete outputs would be wrong. Its ridge-relative and fixed-readout tolerances differ from certifying every adaptive weight-code decision over uncertain calibration evidence. That is a specialization, not proof that its general release framework cannot express our contract. A novel claim must identify the new verifier/evidence mathematics and useful capability; merely adding interval arithmetic or a canonical state digest is insufficient.

4. Other relevant primary sources, freshly verified
QSS: Tavory et al., Exact Unlearning via Quantized Sufficient Statistics, v1 (5 Oct 2026):
https://arxiv.org/html/2610.07197v1
Frozen schema plus additive content, exact reconstruction, explicit label/instance distinction, and full rebuild costs are prior work. It changes the predictor to local quantized-region corrections; our target is adaptive weight quantization under a fixed calibration constructor. Both require an honest definition of what information is removed.

MEDU: Lang, Helvitz, Shlezinger, Memory-Efficient Distributed Unlearning, v1:
https://arxiv.org/abs/2505.03388
Lossy stored updates with a bound on distance to retraining already address the storage/unlearning tradeoff. Our proposed separation is exact discrete recovery, conditional on certification, from a lossy evidence representation. Do not claim the first compressed archive for unlearning.

QEBVerif: Zhang, Song, Sun, v2 / CAV 2023:
https://arxiv.org/abs/2212.02781v2
Differential reachability bounds and MILP fallback verify quantization-error properties across input regions. Universal set-based verification and a fast conservative verifier with stronger fallback are established patterns. Our claimed property concerns the calibration algorithm's produced codes under uncertain calibration matrices, rather than inference-output error of an already quantized network.

GPTQ / related quantization theory:
https://arxiv.org/abs/2210.17323
https://github.com/IST-DASLab/GPTQ-Babai
https://arxiv.org/abs/2508.04853v2
https://arxiv.org/abs/2504.02692
These cover second-order adaptive rounding, nearest-plane geometry, quantitative OPTQ/Qronos error bounds, and asymmetric calibration. Do not claim the recurrence, lattice interpretation, anchoring, or ordinary rounding margins as new. The proposed theorem must explain how uncertainty propagates through the entire adaptive decision sequence while preserving fixed saturation and tie rules.

Additional recent warning against broad bitwise-equivalence novelty:
Xie et al., Beyond Accuracy: Prefix-Invariant Realizations of Low-Precision Fast Matrix Multiplication, v1:
https://arxiv.org/abs/2609.39816v1
It certifies bitwise equality to a prescribed int8 operator so realization choice affects cost rather than predictions. Different operator/problem, but exact output invariance across alternative numerical implementations is not unique to this project.

5. What could remain a contribution (candidate, not priority established)
A precise theorem: for every calibration feature matrix in the authenticated archive enclosure, the declared ordered quantization recurrence yields the same complete code array; the implementation either returns that array with its fixed target identity, or refuses. Soundness must cover enclosure construction, positive ridge, coefficient verification, adaptive-prefix induction, saturation/ties, finite arithmetic premises, complete stage extent, and atomic publication. A certificate is informative only if it sometimes avoids reconstructing exact retained features; record accepted compressed stages, certified widths, fallback counts and all fallback access.

A second contract concerns canonical persistent state, not just code agreement. The state must be independently reconstructed from retained inputs under the same schema, and exercise successor requests. Equality of a digest computed by the same serializer is a serialization check, not independent arithmetic correctness. Target metadata, membership, source identities and canonical payloads require explicit scope; transient caches may differ if intentionally excluded. Incremental state and fresh state should be compared using separate construction paths. Do not describe a fresh rebuild after every request as proof of a fast incremental state-update algorithm.

A system result could map where uncertain compressed features, lossless features, and exact Gram representations are preferable, using the same compatible solver improvements for each comparator. Token-space versus feature-space algebra is standard; integrating it fairly is necessary engineering, not sufficient novelty.

6. Conditional paper claim if full-model codes AND state agree, compression is slower
Suggested wording after validating receipts:
"We study exact calibration-membership updates for a fixed-anchor quantization constructor. Our service certifies complete adaptive weight codes from compressed feature enclosures or falls back to exact retained-source reconstruction, and checks canonical successor state against an independent reconstruction. On the reported workloads, compression reduces the declared retained-evidence footprint while increasing update latency. The results characterize an exactness-preserving storage–latency tradeoff and the regimes where lossless or Gram representations are preferable."

For the three-record / 96-token pilot, append: "This is a bounded complete-model feasibility pilot; it does not establish a useful calibration scale, language-quality advantage, lifetime saving, or population-level performance estimate."

Report literal component and total bytes. Shared checkpoints/anchors, packed deployed codes, tokens or retrieval access, indexes, exact replay sources, successor state, and duplicated artifacts can dwarf the feature saving. If the compressed arm retains a lossless feature cache for fallback, charge it; if it regenerates features from tokens, charge those tokens/access and replay. A modest component saving is not a corresponding reduction in total persistent service storage. Exact equality preserves the declared reference's quality; it does not show that reference matches standard GPTQ or a useful full-precision model.

7. Evidence needed before a strong ACL submission claim
First finish the frozen pilot and independent state/order/refusal checks without tuning its gates. Then prospectively evaluate useful retained sizes, multiple deletion sequences and models, untouched language data, and quality against standard quantization targets. Include strong lossless compression controls, hybrid/native Gram controls, cold and indexed reconstruction with matched access, full preparation/request/fallback lifetime costs, and repeated randomized timing. Seek a real memory-constrained feasibility region or substantial end-to-end storage benefit rather than optimizing a weak baseline to produce speedup. If compression remains dominated, present the negative cost result honestly; an exactness artifact alone at tiny calibration scale is weak evidence for a strong ACL paper. No literature search establishes absence of prior art, and no acceptance guarantee follows.

Retrieval notes
Primary web sources above were checked live. Exact-Fun's NSF PDF and the author's historical full PDF were downloaded only to projectless work/; proof pages 6–7 were rendered and visually inspected. Full author proof retrieval resolves the V41 accessibility gap, but the recovered file is a pinned historical author version, not a claim that it is the latest revision. Focused review only, not an exhaustive survey. No pilot results are asserted here.
