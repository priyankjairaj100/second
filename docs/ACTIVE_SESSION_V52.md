# Active continuation V52 — precision diagnostic terminal

Updated 11 October 2026. This supersedes V51's running status. Both Slurm 13276 and 13291 are terminal. Read this checkpoint before historical launch instructions. No research job from this continuation remains active and no scheduled monitor was created.

## Verified V51 outcome

Slurm 13276 failed its complete gate when 40-bit compressed features could not be certified. The exact-input arms succeeded: all 2,359,296 codes in the 768-by3072 stage match by actual complete packed bytes. They also match the preserved V45 SHA commitment; historical V45 code bytes were unavailable. Original normalization 1664, ridge 1/100, dyadic24 four-bit grids, lower ties, all 13 known C4 records and the fixed nearest-anchor target remain unchanged.

Optimized versus historical point solve/write times were 609.961 and 1162.054 seconds in fixed order; both certified 768 rows with no interval fallback. This engineering observation has uncontrolled cache/order effects and is not a randomized or full-model speedup result.

The 40-bit descriptors used 26,887,374 bytes versus 35,177,196 lossless bytes (23.57% fewer feature bytes). However, the ball pass certified 79 rows; 689 required interval fallback, which refused at subset row 41, original stage row 43, coordinate 1591 (zero based). Maximum coefficient radius was 1.3443e-6 versus 5.0180e-9 for the successful point arms. This is certificate insufficiency, not proof of incorrect true-source codes or impossibility. No complete compressed output was released.

All four V51 charges are settled: preparation 430, optimized point 609, historical point 1158, compressed refusal 637 CPU seconds; total 2834. The complete 81 MiB artifact archive is copied locally. All 346 frozen sources, sealed receipts, complete declared binaries and CPU debits were checked. Terminal metadata is in `campaigns/csis_wide_stage_v51_terminal`; the earlier launch snapshot remains separate and unchanged. Audits: `validation/v51_terminal_audit.json` and `validation/v52_v51_point_pair_audit.json`.

## V52 precision diagnostic

The 48-bit stage passed: all 2,359,296 codes match both V51 point outputs by actual complete bytes. Its feature descriptors occupy 31,999,182 bytes, 9.03% below the original lossless descriptors. Encoding/containment took 61.775s; solve/write took 629.885s; whole-worker time was 691.676s. The ball pass certified 761 rows, with 7 rows handled by the required interval fallback.

The fresh worker charged 690 CPU seconds in its separate 1202-second phase, within the fixed 1200 CPU/1800 wall worker limits, 16 GiB address-space cap and one CPU/thread. The previous 430 CPU neural preparation charge is explicitly reused, not hidden or reported as new execution. V51's 2834 CPU total stays preserved. Slurm software job 13290 passed all 4 new checks; numerical job 13291 has terminal state COMPLETED. No retry, threshold relaxation, new corpus root or quality article was used.

The 48-bit setting was chosen after seeing V51's 40-bit refusal. This is adaptive development on the same stage and sources, not untouched confirmation. Only the already-supported codec precision changed; block size 256, source words, dispatcher, verifier, original target and optimized kernel stayed fixed. Source binding: 358 files and 101 prior/check artifacts. Full postrun audit: `validation/v52_terminal_audit.json`. Terminal metadata: `campaigns/csis_precision48_v52`; numerical artifacts remain in the fresh local and cluster run directories and are omitted from Git and the user ZIP.

Frozen numerical source: `6b70d703a716cef744f49ba1c55add3a691c3267`.
Program SHA-256: `f22f6667500b4205107929bd4607c00730ed4df61db1ac13f7f87137a5838ec0`.
Directory: `/nfs_home/users/poonam/second-20261010/local_runs/precision48-v52-20261011-a`.

The audit rehashes actual artifacts and verifies sealed execution under the declared trust model; it does not independently repeat numerical inference or authenticate a hostile machine. Feature-descriptor storage is not full model/state/deployment storage. Prepared-input solve time is not cold-replay or deletion-service latency. V51 remains a failed 40-bit gate regardless of V52's outcome.

## Next decision

Review a new canonical state representation with an explicit precision policy and shared optimized kernels before any full-model registration. The old compressed40 state validator must continue rejecting 48-bit descriptors.

Static inspection confirms `research_v43/state.py` fixes compressed40 to 40 bits and block 256 and forbids silent representation changes during deletion. A 48-bit integration must have an explicit new representation/schema and tested canonical retained-state comparisons; it cannot be relabeled compressed40. Preserve this historical validator and all frozen experiment sources.

No full-model recovery is registered. A later experiment must prospectively bind all 24 stages, matched control access, explicit fallback costs, complete changing-state bytes, independent fresh retained comparisons and new bounded resource limits. One stage's timing cannot establish or be multiplied into a claimed full-model runtime. Retain V43's latency loss to the equally indexed cache, V45's CPU-limit failure, both representation outcomes and all 60 historical quality exclusions.

For an ACL paper, useful-scale full-model quality, a second checkpoint, stronger codec baselines, certificate/replay ablations, repeated randomized roots/deletions, untouched quality and a defensible novelty contribution remain required. This diagnostic supplies neither confirmation nor paper readiness.

## Manuscript and environment

The existing editor master is `outputs/second-research-draft.tex`, with repository snapshot `reports/manuscript_v52.tex`. It records verified wide-stage evidence and the compressed refusal; the built-in compiler succeeded. Visual layout remains unverified. No replacement document, separate PDF or new editor tab was created.

Cluster access and the exact CPU environment remain available. GPU likelihood parity from V47 and the local 78-array parameter backup remain verified historical evidence; GPU feature generation has not replaced the exact CPU feature target. Check current account resources before new work and preserve unrelated jobs. If SSH fails, stop bounded retries and keep remote status unknown; do not infer or duplicate work.
