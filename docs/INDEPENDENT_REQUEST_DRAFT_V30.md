# Prospective independent-request development pilot

This draft adds one WikiText root and one bounded-C4 root.
Each root contains two distinct sources with 128 tokens each.
Both single-source deletions are evaluated separately from the same original prepared state.
Every retained target keeps original normalization 256.
The mathematical target remains fixed nearest-anchor calibration on DistilGPT2.

No model inference, registration, or empirical worker ran while preparing this draft.
Only cached-source verification, tokenization, metadata checks, and software fixtures ran.
Preparation used 2.951239194 CPU seconds, outside empirical worker accounting.

## Preconditions

Do not register this pilot until all three earlier gates pass:

1. The ordered complete-service campaign finishes with exact models and settled transaction receipts.
2. The ordered compressed128 pilot passes its registered exactness, storage, and timing guards.
3. Matched follow-up quality passes its sequential128 primary gate and fixed16 safety gate.

The controller must bind every prerequisite to its final evidence closure before registration.
Failures remain evidence and cannot be replaced by another selected root.
Neither a passing prerequisite nor this draft promises a positive speed result.

## Deterministic selection

The selector ranks each eligible identifier by SHA-256 of:

```text
independent-requests-v30:<corpus>:<identifier>
```

Corpus names are `wikitext` and `c4`.
Selection reads earlier plans and input audits, without inspecting model outcomes.
It binds 88 earlier selection and plan files and excludes their designated identifiers.
Together with preserved quality exclusions, this removes 52 previously designated documents.

WikiText candidates come exclusively from the established 500-document development pool.
The 110-document training confirmation reserve remains unused.
The selector verifies all three historical pool hashes and the tokenizer hash.
The twenty existing quality exclusions remain unchanged.
The four newly selected training documents receive separate prospective development exclusions.

C4 uses 2,278 complete records from a cached two-MiB compressed prefix of English training shard zero.
The acquisition revision is `1588ec454efa1a09f29cd18ddd04fe05fc8653a2`.
The selector decompresses the cached prefix and verifies the complete JSON records exactly.
It reproduces the historical eligible-pool hash across all 1,678 eligible documents.
This checks tokenization, normalized-document deduplication, and the minimum length rule.
Tokenization adds no BOS or EOS and takes the first 128 tokens without repacking.

C4 selection excludes earlier designated C4 candidates.
It also rejects prepared-token duplicates against all WikiText pools and prior designated C4 chunks.
Selected C4 documents must have distinct document hashes, token hashes, and URL hashes.
This bounded frame does not support corpus-wide sampling or population generalization.

| Root | Source identifiers |
|---|---|
| WikiText | `wikitext2:train:article-row-17380`, `wikitext2:train:article-row-22925` |
| Bounded C4 | `c4:en:shard0:line2172`, `c4:en:shard0:line683` |

Lexicographic source order defines deletion indices zero and one.
The compressed control always evaluates deletion zero for each root.
This choice precedes every new model outcome.

## Measurements

Each root has five primary transactions:

1. Complete original ordered preparation with both sources.
2. Ordered repair and model-only cold reconstruction after deletion zero.
3. Ordered repair and model-only cold reconstruction after deletion one.

Each deletion starts from the same original state.
The two requests are alternative branches, rather than a sequential deletion chain.
Complete canonical model bytes must match within each repair/cold pair.
Both methods use identical checkpoints, grids, normalization, feature arithmetic, and point-solver budgets.
Cold reconstruction receives only retained tokens and the checkpoint.
Repair receives the corresponding original state and preparation evidence.

Method order is balanced prospectively:

| Root | Delete zero | Delete one |
|---|---|---|
| WikiText | Repair, cold | Cold, repair |
| Bounded C4 | Cold, repair | Repair, cold |

Two further transactions provide the selected compressed control:

1. Convert the original lossless state into forty-bit descriptors with block size 256.
2. Repair the preselected deletion zero and verify against its completed model-only cold reference.

Compressed conversion and repair must share frozen sources.
They use the ordered decoder, disable prior-model candidates, and preserve original normalization 256.
Copy the successful compressed128 certificate and point budgets exactly before registration.
Do not tune those budgets using either new root.
The draft deliberately leaves their evidence binding unresolved until that prerequisite finishes.
It therefore cannot be passed directly to an existing execution launcher.

## Budgets and timing scope

| Transaction type | Transactions per root | CPU ceiling each | Wall ceiling each |
|---|---:|---:|---:|
| Original lossless preparation | 1 | 450 s | 600 s |
| Lossless repair | 2 | 180 s | 240 s |
| Model-only cold reconstruction | 2 | 300 s | 400 s |
| Compressed conversion | 1 | 120 s | 180 s |
| Selected compressed repair | 1 | 300 s | 420 s |

One root requires at most 1,844 seconds of complete CPU reservations, including controller reservation margins.
The proposed phase ceiling is 1,900 CPU seconds per root, or 3,800 across both separate phases.
These are abort ceilings, not predicted runtimes or authorization to launch.
Use one CPU, one thread, six GiB address-space limits, and separate complete process receipts.
The measured earlier ordered preparation took about 310 seconds; the 450-second ceiling supplies limited headroom.
Preparation can still fail or exhaust that ceiling on another document pair.
No automatic retry, source replacement, or allowance pooling is permitted.

Measure complete controller transactions, including loading, verification, serialization, and output rereads.
Report every individual latency and cold/repair ratio.
Report complete lossless and compressed state bytes, including models, indices, and framing.
Report certificate acceptance, fallback, neural traversals, and unresolved work separately.
Preserve failed, adverse, and unstarted rows.

Original preparation and compressed conversion remain charged setup costs.
The main table reports both setup and request costs without subtracting nested clocks.
This small pilot omits per-root original model-only preparation.
It therefore cannot establish lifetime break-even or isolated caching overhead.

## Interpretation and remaining expansion

The design provides four different deletion requests across two disjoint development roots.
Requests sharing a root remain correlated.
There is only one root per corpus and one timing pair per deletion.
Report root-level summaries descriptively; do not calculate a population confidence interval from four requests.
The bounded C4 result would add cross-corpus development evidence, not independent-domain confirmation.
This pilot adds neither model diversity nor new language-quality measurements.

If correctness and practical costs justify expansion, preregister more roots and repeated randomized timing blocks.
Use untouched documents for a later, separately frozen quality program.
Keep the original sequential-target failure and all fixed-target limitations explicit.

## Files and reproduction

The new preparer is `scripts/prepare_independent_requests_v30.py`.
Seven software fixtures verify selection, exclusions, source reconstruction, token rules, and paired scheduling.

The draft directory contains:

- `selection.json`: provenance, hashes, historical exclusions, selected document metadata, and preprocessing cost.
- `wikitext-records.json`: the two selected 128-token WikiText inputs.
- `c4-records.json`: the two selected 128-token C4 inputs.
- `specification.json`: contingent gates, primary plans, compressed templates, and resource ceilings.

All source texts remain outside the repository.
The draft contains only short token prefixes, metadata hashes, and reproducible selection rules.
The preparer refuses to overwrite an existing draft.

```bash
python -m unittest tests.test_independent_requests_v30
python scripts/prepare_independent_requests_v30.py --output /absolute/new/draft-directory
```

Neither command registers an empirical phase or evaluates a model.
