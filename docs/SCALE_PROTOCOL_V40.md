# Prospective native and streamed control pilot

Registration design date: 10 October 2026, after V39 completed.
V39 results motivated this development follow-up.
This is not independent confirmation.
No V40 empirical result existed when this protocol was written.

## Question

Does native exact accumulation strengthen the pooled-Gram control without changing a single archive byte?
Does blockwise certification preserve exact codes while avoiding the concatenated feature matrix?
Does the observed 40-bit storage tradeoff survive that implementation change and the larger retained set?

Reuse V39's pinned model, tokenizer, parquet, article partition, and deterministic selection rule.
Publish a fresh selection before model work.
Use the same thirteen real articles and 1,664 original tokens.
Retain six or twelve records: 768 or 1,536 tokens.
Keep normalization 1,664, ridge 1/100, and the four-bit base-only grids.
Evaluate the same complete first QKV stage and all 1,769,472 codes.
The target remains fixed nearest-anchor calibration.

## Preparation

Generate each source's first-stage features independently.
Create lossless and 40-bit source descriptors.
Verify exact roundtrips and true containment.
Compute each source Gram through both native integers and the original Python reference.
Require complete canonical archive byte equality for every source.
Pool the trusted native results through the unchanged exact algebra.
Record native, reference, comparison, feature, and codec costs separately.
Their nested timing fields must not be added to the enclosing preparation clock.
Original complete-model quantization remains outside this stage pilot.

## Registered arms

Each retained size runs these six arms in a fixed hash-seeded order:

1. `gram_delete_python`: original exact Gram plus deleted-feature replay and Python exact accumulation.
2. `gram_delete_native`: the same access and certificate, with native exact accumulation.
3. `gram_fresh_native`: retained-feature replay and native exact accumulation.
4. `cached_primal`: lossless decoding, concatenation, and the V39 feature-space certificate.
5. `streamed_primal`: lossless decoding and the new blockwise certificate.
6. `streamed_compressed_40`: 40-bit boxes and blockwise certification.

A declared numerical refusal in the compressed arm triggers fresh retained-feature replay and blockwise point certification.
Charge the failed certificate, replay, and point fallback to that arm.
Other scientific refusals remain visible without a partial result.
Unknown runtime, allocation, compiler, or integrity errors stop dependent work.
There are twelve registered observations and no outcome-based repetition.

Every completed arm must produce identical actual packed code bytes.
All three retained Gram archives must also match exactly.
Record actual comparisons before the temporary runner ends.
There is one observation per arm and size.
Do not claim reliable population superiority or use a cross-run timing ratio against V39.

Each arm clock includes loading, replay, accumulation, certification, diagnostics, and output.
Shared checkpoint construction and native builds are separately recorded.
Comparisons and receipts remain outside arm clocks.
Representation payloads exclude raw token inputs, the common checkpoint, and audit files.
They are not complete persistent service state.

## Resources and preservation

Use one standard public `ubuntu-24.04` runner, one CPU, one numerical thread, and a 6-GiB process limit.
The data phase has a separate 122-second CPU allowance.
Its worker limit is 120 seconds.
The model phase has a separate 1,700-second allowance.
Preparation has a 240-second limit.
Each request has a 700-second limit.
The complete model reservations total 1,646 seconds, including controller reservation slack.
The workflow wall limit is 60 minutes.
Allowances are not observed usage.
Setup, fixtures, publication, and audits remain outside empirical ledgers and must be disclosed.

Use a new one-use claim, registration, runtime identity, prefix, and ledgers.
Publish the registration, selected data, preparation, and each settled request before dependent work.
No paid compute, cache storage, artifact upload, force-push, or automatic retry is authorized.
Never rewrite V39 evidence or reuse its unused allowance.
If settlements are lost, hold the full affected phase allowance without inventing observed CPU use.
Git receives text evidence and binary hashes.
Derived binary files remain on the temporary runner.

## Interpretation gate

Report the strengthened baseline even if it defeats the proposed cache or compression path.
Report the 40-bit result even if fallback erases its earlier benefit.
Successful stage checks permit planning a complete-model experiment.
They do not establish complete-model speed, canonical successor states, lifetime benefits, quality, or ACL readiness.
