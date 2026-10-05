# Local empirical program: revision 11 handoff

Date: 5 October 2026.
The user now owns local execution. The assistant reviews returned evidence and helps improve algorithms.
This document specifies the program. It does not certify that execution prerequisites already pass.

## What we know

The theory supports exact repair under explicit premises, with conditional cost gains.
The current full-model implementation fails resource planning for DistilGPT2 and GPT-2.
The no-chart estimates are 23.01 GiB and 36.16 GiB under the reference planner.
These are heuristics, not measured peaks or model-only memory requirements.
Real first-block diagnostics matched 344,064 binary64 values across WikiText-2 and a bounded C4 prefix.
Their worker ratios were 4.471x and 4.509x. Each method had one observation per corpus.
Those results contain no quantization, repair, complete lifetime, or quality evidence.
Do not combine their timings with new hardware timings.

## Stage 0: reproduce software and declare the machine

Run LOCAL_LLM_START.md's setup commands. Keep the complete software test report.
Record CPU model, available RAM, disk space, OS, interpreter, dependencies, affinity, and thread settings.
The initialization tool records basic host properties. Add missing CPU details without recording account credentials.
Record free memory immediately before runs. The runtime contract alone does not prove comparable machine load.
Use separate output directories for each run. Commit source changes before freezing inventories.

The inherited feasibility allowance is 10,800 worker CPU seconds. Revision 10 charged 614 seconds.
The inherited remainder is 10,186 seconds, before any additional local work.
Never reset this allowance through a new directory or protocol hash.
A revised local policy can declare a different prospective budget and hardware envelope.
Record its new allowance, inherited spending, reason, and effective first run separately.
Keep the original failed resource gate visible. Never claim the revised policy passed the old policy.
Controller CPU and physical project-wide enforcement remain outside the current child ledger.

Deliver: runtime contract, hardware snapshot, dependency freeze, software report, and prospective local resource policy.
Exit: supported runtime and passing relevant software checks. No scientific claim follows.

## Stage 1: close implementation blockers

Complete these changes before launching a full campaign:

1. Replace eager Fraction parameter storage with bounded exact storage and lazy exact decoding.
2. Stream canonical hashing and serialization. Avoid duplicate whole-model JSON structures.
3. Bound exact Gram construction, factorization, intermediate integers, and old/new state coexistence.
4. Integrate the exact-order linear prototype into supported finite execution.
5. Preserve separate multiply/add operations, coordinate order, finite checks, and certified nonlinear primitives.
6. Keep proof jets on their supported exact path. Do not pass them through the finite-only prototype.
7. Give compatible changes equally to repair, indexed fresh, direct fresh, and model-only fresh.
8. Update conservative resource planning to match the new representation. Preserve documented excluded costs.
9. Add a real-source inventory builder using existing measured campaign APIs.
10. Bind scientific provenance into the feasibility bridge. Do not delete its unmet-provenance guard.
11. Integrate the complete-word LAMBADA scorer before using that task.

Verify altered arithmetic against the existing reference on small software fixtures.
Compare complete canonical bytes, every quantized code, and applicable state fields.
Include ties, cancellation, subnormals, finite overflow rejection, and replay fallback.
These checks are software tests, not synthetic empirical results.
If serialization changes, version the schema and prove semantic equivalence explicitly.
Do not weaken target checks merely to accommodate a faster representation.

Deliver: committed backend changes, test evidence, measured allocation diagnostics, and updated planning assumptions.
Exit: the revised implementation passes its software checks and conservative resource plan.
After Stage 2 acquisition, require a complete real-model preflight before Stage 3.
That preflight must fit the declared policy and produce valid finite outputs.
A planning pass alone does not establish actual admission.

## Stage 2: acquire and freeze real inputs

The existing acquisition script restores the archived diagnostic inputs:

```bash
python scripts/acquire_pilot_inputs.py
python scripts/prepare_wikitext_pilot.py \
  --data tmp/data/wikitext2 \
  --tokenizer tmp/models/distilgpt2/tokenizer.json \
  --output local_runs/first/wikitext-inputs
```

These commands download public pinned files. They execute no remote model code.
The first command downloads DistilGPT2 weights and only GPT-2's configuration.
Complete GPT-2 weights need a separate pinned download before that model's experiments.
The reserve-input script now requires a fresh output directory:

```bash
python scripts/prepare_reserve_pilots.py --output local_runs/first/reserve-inputs
```

It reproduces bounded-prefix C4 and LAMBADA input checks. It does not prepare the four-shard confirmation frame.
Do not run `launch_pilot_v10.py` for new observations. It reopens archived paths and budgets.

| Input | Frozen source revision | Role |
| --- | --- | --- |
| distilbert/distilgpt2 | 2290a62682d06624634c1f46a6ad5be0f47f38aa | First complete-model implementation and primary candidate |
| openai-community/gpt2 | 607a30d783dfa663caf39e06633721c8d4cfcd7e | Second-model replication after admission |
| Salesforce/wikitext | b08601e04326c79dfdd32d625aee71d232d685c3 | WikiText-2 raw calibration and heldout language quality |
| allenai/c4 | 1588ec454efa1a09f29cd18ddd04fe05fc8653a2 | Independent corpus replication |
| EleutherAI/lambada_openai | 900124bf3b8235c6daf21033af9948b3f07346c4 | External complete-word evaluation only |

Preserve document boundaries, token offset zero, no BOS/EOS, and no post-deletion repacking.
Keep the original normalization M0 after every deletion.
Hash raw files, document identities, normalized content, prepared token records, and tokenizer files.
Check duplicate document IDs, normalized text, and token sequences across protected phases.
Source revisions alone do not validate locally prepared inputs.

WikiText has 500 development, 110 confirmation, and 60 evaluation articles under the existing parser.
Reproduce these counts or explain discrepancies before proceeding.
Within the evaluation pool, prospectively assign the first 20 hash-ordered articles to development quality.
Assign the remaining 40 to final quality. This new split must be committed before model outcomes.
Use two, eight, and sixteen development evaluation articles for preflight, feasibility, and development respectively.
Use lengths 16, 32, and 64 respectively. Final quality uses all 40 articles at length 128.
Score next-token likelihood within each record. Exclude each record's first token from the denominator.
Do not tune with final evaluation data.

The archived C4 input is only a two-MiB compressed prefix from English shard zero.
It supports diagnostic claims about that frame only.
For broader replication, prospectively acquire complete pinned English training shards 00000 through 00003.
Assign shards 00000–00001 to development, 00002 to confirmation, and 00003 to evaluation.
Hash complete files and parse complete JSON records. Filter length and duplicates before root sampling.
Order the evaluation pool using a committed hash salt before outcomes.
Reserve its first 20 eligible documents for development quality and its next 40 for final quality.
Use the same quality counts and lengths as WikiText for matched cost comparisons.
This four-shard design remains conditional on the declared frame, not all C4 or independent web domains.
If storage prevents acquisition, freeze a narrower frame and narrow claims before running.
Do not switch frames after observing performance.

Draw root subsets independently from fixed ordered phase pools, using separate committed random streams.
Sampling is without replacement within each root. Different roots may overlap within a phase.
Inference then conditions on that finite pool and the independent subset-draw design.
Do not describe overlapping roots as disjoint documents or population-wide independent domains.
Twelve disjoint roots of 64 records cannot fit the existing 110-article WikiText confirmation pool.
Any disjoint-root design requires new acquisition or revised sample sizes before confirmation.

Keep the sixteen inspected LAMBADA examples excluded from final evaluation.
Split context at the final ASCII space. Include the leading space in the answer.
Verify tokenizer boundary equality and score every answer token.
For accuracy, generate greedily without feeding gold answer tokens.
Compare the complete target continuation under a frozen EOS and tie policy.
Teacher-forced token accuracy equals complete greedy accuracy only when every preceding prediction also matches.
Report whole-answer log likelihood separately. Never substitute last-token accuracy.
Resolve source-license documentation before redistribution. Keep complete raw corpora outside Git.

Deliver: pinned input manifests, disjoint phase audits, root memberships, and source-frame statements.
Exit: complete provenance, token checks, and adequate eligible pools. Missing provenance keeps promotion blocked.

## Stage 3: pilot every experiment cell

The table specifies the required empirical matrix.
Run each applicable cell on each corpus and model before expanding that cell.
The initial model is DistilGPT2. GPT-2 repeats the admitted program as a secondary replication.
LAMBADA evaluates models calibrated on both corpora. It is not a calibration corpus here.

| ID | Experiment | Pilot evidence | Expansion evidence |
| --- | --- | --- | --- |
| E01 | Input integrity | Counts, boundaries, duplicates, token alignment | Frozen complete pools and roots |
| E02 | Full-model exactness | Every stage code versus direct fresh | Zero mismatches across every planned request |
| E03 | Changed-ancestor mechanism | Actual ancestor changes and retained feature evaluations | Complete group denominator and certificate/replay decomposition |
| E04 | Four-method request cost | One complete paired transaction per method | Four counterbalanced repeats, root uncertainty, all failures |
| E05 | Three-request lifetime | Preparation plus three disjoint deletions | Same horizon, all costs, final state and combined-delete agreement |
| E06 | Heldout quality | Base, original quantized, retained fresh, repair | Identical evaluation tokens and finite quality at every request |
| E07 | Mechanism ablations | Each ablation admits and preserves its declared target | Paired mechanism, cost, storage, and quality comparisons |
| E08 | Robustness | Each request, precision, and size setting passes its own pilot | Development grid and declared secondary confirmation cells |
| E09 | Resource scaling | Measured memory, bytes, factorization, serialization | Calibration-size and group/rank tradeoffs with complete costs |
| E10 | External NLP task | Sixteen development LAMBADA examples, complete-word evaluator | Remaining eligible examples, paired repair/fresh agreement |

The default pilot uses one root, two calibration records, sixteen tokens, and one timing repeat.
For six distinct request patterns, use at least eight records. Tiny patterns can otherwise coincide.
For a three-request pilot, use eight records and three disjoint singleton deletions.
Tiny pilots diagnose bugs and cost structure. They cannot establish reliable speedup.

Apply four labels: pass, loss, blocked, or invalid.
A pass requires the experiment's own correctness and interpretation checks.
A loss is valid negative evidence. Preserve it and inspect the dominant cost.
A blocked cell lacks required execution or evidence. An invalid cell has a bug or mismatched contract.
Do not report a win merely because a kernel improved.
Do not automatically discard valid losing robustness settings.
Only expand costly efficacy cells after their parent feasibility gate passes.

## Stage 4: unchanged feasibility decision

Use `configs/feasibility_gates_v1.json` unless a prospective successor explicitly replaces its resource envelope.
Keep successor results distinct. Preserve unchanged scientific thresholds unless justified before outcomes.
Run two real roots, eight calibration records, 32 tokens, and three sequential requests per root.
Use the four methods: model_only_fresh, repair, indexed_fresh, and direct_fresh.
Use one repeat for this engineering gate. Freeze method order before execution.

Every root must satisfy all conditions:

- Zero code mismatches and applicable canonical-state mismatches.
- No missing or failed required requests.
- Required finite evaluations complete under declared resource limits.
- Changed-ancestor retained-group feature avoidance reaches at least one quarter.
- Retained fresh/base perplexity ratio stays at most 1.2 for every request.
- Complete repair lifetime beats model_only_fresh lifetime over three requests.
- Provenance, quality, diagnostic, and budget evidence bind to the same workload.

Coverage counts every nonempty retained group under actually changed transitive ancestors across every request.
Count only groups resolved without retained target-feature evaluation.
A source-cache hit alone does not qualify. A zero denominator means mechanism not demonstrated.
Quality uses equal positive token counts and finite NLL differences at most log(1.2).
The original resource policy caps each worker at 900 seconds and 6 GiB address space/RSS.
It caps files at 512 MiB, preparation at 900 seconds, and complete lifetime at 3,600 seconds.
A tie or loss against indexed fresh prohibits deletion-exclusive solver claims.
Passing permits development. It does not establish reliable population speedup.

Stop mismatches immediately. Fix the implementation and invalidate affected results without deleting them.
For resource failure, optimize the measured bottleneck or narrow the declared supported setting.
For poor coverage, diagnose domain rejection, conditioning, margins, and bound looseness.
For lifetime loss, inspect preparation, proof work, replay, hashing, state output, and exact factorization.
Do not improve ratios by excluding inconvenient cost categories.

## Stage 5: development and algorithm selection

Use four roots, 32 calibration records, 64 tokens, and four counterbalanced timing repeats.
Use disjoint development and confirmation pools. Freeze each development batch before launch.
Use four-bit quantization, ridge 1/100, and one group as the initial admission candidate.
These are proposed starting settings, not a selected final configuration.
Keep the fixed target contract, grid construction, stage order, and lower-code ties.

For each root, construct these six independent-reset deletion requests from original state:

1. Uniform singleton.
2. Uniform ceil(N/16).
3. Uniform ceil(N/4).
4. Contiguous ceil(N/16), with a random original-order start.
5. Concentrated ceil(N/16), using original feature-energy scores.
6. Difficult ceil(N/16), using original leverage/margin scores.

Use `src/request_workload.py` for score definitions and sampling.
Score before deletion outcomes. Charge score preparation separately and consistently.
Run a separate ordered sequence of three disjoint ceil(N/16) batches.
Compare its final codes and applicable state with combined deletion.
Keep empty/full deletion and repeat-deletion semantics as separate correctness controls.
Source withdrawal remains conditional on a genuine source mapping. Do not invent labels for this experiment.

Run ablations sequentially, with a pilot for each setting:

- Certified response versus full_replay, fixed_reference, and identity_only service modes.
- Identity-cache family with its supported no-chart configuration.
- Linear versus quadratic Gram tier for the same affine feature surrogate.
- Spectral versus spectral_or_interval verification.
- Stage-RTN versus grid-box charts; coordinate charts only after admission.
- Groups 1, 2, and 4, then chart-rank caps 8, 16, and 32 where supported.

Do not run an unbounded Cartesian product.
Change one factor from the declared development reference, then test justified interactions separately.
Quadratic means the Gram of an affine response. It does not mean second-order transformer features.
Compare canonical states only within compatible family/tier contracts.
Compare common target codes across families sharing the numerical target.

For robustness, use bits 3, 4, and 8; calibration sizes 8, 32, and 64; lengths 32, 64, and 128.
Vary one factor around the development reference. Pilot each new setting first.
List unsupported cases and resource failures explicitly.
Track preparation, service, lifetime, retained passes, state bytes, peak RSS, and arithmetic costs.
Use diagnostic clones for cost attribution. Do not mix their clocks with clean measurements.

Choose one primary configuration using development results only.
Prefer complete exactness, useful quality, changed-ancestor avoidance, and preparation-inclusive gains together.
Lock the algorithm before confirmation. A positive isolated latency ratio is insufficient.

## Stage 6: freeze confirmation

The planning default is twelve roots, 64 calibration records, 128 tokens, and four repeats.
Twelve roots are not a power justification.
Estimate between-root variability from development. Choose precision and root count before confirmation outcomes.
Use independent root streams within the declared finite pool. Report that conditional inference scope.
Freeze one primary model/corpus/configuration/comparator and one primary complete-cost estimand.
The preferred primary estimand is three-request preparation-inclusive lifetime against model_only_fresh.
Treat single-request ratios, indexed comparisons, C4 replication, and GPT-2 replication as secondary unless preregistered otherwise.
Bind the analyzer's primary selection to that choice. Do not infer multiple primary wins from separate tables.

Freeze source commit, runtime, hardware, resource policy, inputs, roots, requests, quality set, orders, and complete inventory.
Freeze bootstrap settings, exclusion rules, failure handling, and the minimum speedup threshold.
Commit the freeze before executing any confirmation leaf.
Fill every blocked protocol field from real artifacts. Do not clear fields without evidence.
Local protocol creation must bind local paths and runtime. Archived absolute paths are not portable manifests.

Run all planned confirmation cells. Never stop when an interval first becomes favorable.
A bug requiring code changes invalidates affected confirmation. Preserve it and register a fresh study.
Do not tune on those observations or reuse their heldout status.

## Stage 7: analyze and return evidence

For each request, take method medians across all planned valid paired repeats.
Average request log ratios within roots. Weight roots equally.
For lifetime, include each system's preparation once and every request exactly once.
Bootstrap roots, not layers, tokens, requests, or repeated timings.
Use 2,000 draws, seed 20261004, and a 95% interval unless prospectively revised.
A reliable primary speed claim requires the lower interval bound strictly above 1.05.
It also requires all planned exact clean completions and every applicable scientific gate.
An interval crossing one is inconclusive. A complete measured loss remains a result.

Keep ordinary model_only_fresh as the main speed comparator.
Give indexed_fresh the same valid summaries, caches, and solver improvements.
Use direct_fresh as the independent full-state oracle.
Never present a gain against unnecessary index reconstruction as faster ordinary requantization.

The transaction clock includes loading, required validation, service, verification, state maintenance, serialization, commitments, and cleanup.
Observer bootstrap and final observer receipt remain outside its declared boundary.
Research oracle comparisons, external lineage, and quality run separately.
Do not charge those costs selectively to a comparator.
Report research overhead separately when available. OS caches remain uncontrolled unless a new policy specifies otherwise.

Return every planned row, including failures, losses, and unstarted cells.
For each row, include source/runtime/input hashes, target/configuration, roots, requests, and original observation identities.
Include exactness, coverage numerator/denominator, quality token counts, finite NLLs, complete timings, RSS, bytes, and budget settlement.
Provide diagnostic explanations with supporting receipts. Mark unknown causes explicitly.
Use `scripts/local_handoff.py pack` and the generated report template.
The bundle is a review index, not a replacement for immutable raw archives.

## Existing execution commands

A local inventory builder must create the referenced files first.
These filenames describe the expected local layout; they are not shipped empirical inventories.

```bash
python scripts/run_measured_campaign.py local_runs/first/request-inventory.json \
  --output local_runs/first/request-results --validate-only
python scripts/run_measured_campaign.py local_runs/first/request-inventory.json \
  --output local_runs/first/request-results
python scripts/run_measured_sequence.py local_runs/first/sequence-inventory.json \
  --campaign --output local_runs/first/sequence-results --validate-only
python scripts/run_measured_sequence.py local_runs/first/sequence-inventory.json \
  --campaign --output local_runs/first/sequence-results
python scripts/summarize_measured.py local_runs/first/request-inventory.json \
  local_runs/first/request-results > local_runs/first/request-analysis.json
python scripts/summarize_measured.py local_runs/first/sequence-inventory.json \
  local_runs/first/sequence-results --sequence > local_runs/first/sequence-analysis.json
```

Use `build_measured_plan`, `build_measured_campaign`, and `build_measured_sequence_campaign` in their corresponding source modules.
Follow software tests for schema construction only. Their fixture inputs are not empirical sources.
Resolve the inventory/protocol/manifest hashing cycle using the existing normalization contract.
Run `evaluate_feasibility.py` with clean and diagnostic sequence evidence after provenance integration.
Its zero exit status means report creation, not scientific promotion.

## Paper deliverables

Populate the ten evidence slots only from verified archives.
Deliver target/source settings, exactness/failures, request costs, lifetime costs, mechanism, storage, and language-quality tables.
Add scaling figures and a complete negative-results appendix.
State the strongest jointly supported claim. Narrow the paper if complete-model speedup remains unsupported.
A world-class empirical program requires honest failure analysis, not a predetermined positive result.
