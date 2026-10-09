# Pooled-Gram component pilot: complete

Updated 9 October 2026.

The full C4 program remains blocked exactly as recorded in `ACTIVE_SESSION_V34.md`.
The current environment still lacks the required neural decoder runtime interfaces.
No historical worker is retried or reclassified.

A new bounded component implements the missing exact pooled-Gram control.
It operates on preserved real WikiText feature words, not regenerated neural features.
It tests four complete rows of the first QKV stage, with width 768 and original normalization 256.
No synthetic empirical dataset is used.

The registered program is `campaigns/pooled_gram_component_v35/program.json`.
Its SHA-256 is `a676d214813f1bd47d55f5bf3629a768826a85b3368a7169309f07e0173fd5fa`.
Its separate CPU allowance is 900 seconds, with one 880-second worker and a complete 882-second reservation.
All prior ledgers remain bound and unchanged.
Registration formed no Gram and computed no new quantized codes.
The protocol was published at `451574d0c0938fec666c4b68b92da51218088af4` before execution.
The worker completed successfully and charged 38 CPU seconds.
Its three code arrays match all 3,072 archived reference decisions.
The repaired and independently rebuilt retained Gram bytes match exactly.
Pooled deletion took 14.830470 seconds; retained Gram reconstruction took 14.180701 seconds.
The cached-token arm took 0.501197 seconds.
Original Gram preparation cost 7.557861 seconds.
The retained exact Gram occupies 5,020,445 bytes; the retained feature descriptor occupies 688,713 bytes.
These are component representations, not complete deployed model states.

The pilot compares exact pooled deletion, independent retained-Gram reconstruction, and the existing cached-feature token solver.
It checks exact retained Gram bytes and all 3,072 codes against the historical reference.
Native compilation and common inputs are reported separately from arm times.
Each arm includes its own needed feature decoding.
Timing is a single fixed-order component observation, with no statistical reliability or complete-model claim.

Read `EXACT_GRAM_BASELINE_V35.md` for mathematical premises and scope.
Read `GRAM_REVIEW_V35.md` for independent review.
Fifteen accumulator, thirteen direct-solver, nine protocol, and five capsule fixtures pass.
Original numerical files under `src` and historical `run_` workers remain unchanged.

The 1,873,584-byte real-data capsule is `data/gram_v35/wikitext-firststage.json`.
Its SHA-256 is `59bf847f2765fc788a93fe53374aa91e7853d2981a18d46b1084d0807cf6c775`.
It preserves exact feature descriptor bytes, four weight rows, and previously observed reference codes.
The archival reader does not substitute historical machine facts or claim current neural re-execution.

The known chat attempt is complete. Do not execute it again.
Read `campaigns/pooled_gram_component_v35/analysis.json` and the immutable completion record.
A separate full-first-stage protocol is being prepared to test all 2,304 rows and shared coefficient costs.
It will have its own registration and allowance.

Do not retry an existing attempt. Inspect actual receipts and status first.
Use process-output waits only while the timed worker runs.

For a fresh local component reproduction, use `LOCAL_GRAM_PILOT_V35.md`.
The broader research program and ACL submission remain incomplete.

The immutable V35 status command compares the historical ledger path inventory exactly.
After a later phase adds a ledger, use the append-only V35 result audit for historical interpretation.
An additional ledger is not itself a change to V35 measurements; all originally bound ledgers must still match.
