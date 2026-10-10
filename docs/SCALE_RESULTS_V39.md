# Real-data scale results and research decision: V39

Updated 10 October 2026, after workflow completion and metadata audit.

All seventeen method/size observations completed with identical exact stage codes.
The new primal solver improves the high-token case, but pooled Gram deletion remains the strongest large-retention control.
The result supports continued algorithm development, not a broad superiority or submission-readiness claim.

## Evidence and scope

- Workflow: https://github.com/priyankjairaj100/second/actions/runs/38023401448
- Trigger source: `30c2da3acb7e1d907d6e33d79dc2a1e7a0f75423`.
- Registration publication: `6cc05279e3e694f6700f7412508114afcc75fe24`.
- Final workflow evidence: `2881ca95793a0d0a97d76134633ae7a8f28c600d`.
- Results: `campaigns/ci_scale_v39/analysis.json` and the underlying attempts.
- Local audit: `validation/scale_metadata_audit_v40.json`.

The pinned DistilGPT2 checkpoint uses thirteen distinct real WikiText-2 development articles.
Each article contributes 128 tokens.
The original normalization remains 1,664 after deletion.
The three retained subsets are alternative requests from one original root.
They are not a successive deletion sequence or independent roots.
The target is fixed nearest-anchor calibration, distinct from sequential GPTQ.
Only the first complete QKV stage is evaluated: 2,304 rows, width 768, and 1,769,472 codes.
Each arm and size has one observation.
No quality evaluation or population inference is available here.
All sixty historical quality exclusions remain reserved from confirmation.

## Complete arm outcomes

Every row below has exact code agreement.
The 32-bit arm includes its failed certificate and registered fallback.

| Retained tokens | Arm | Elapsed seconds | Representation bytes | Replay fallback |
|---:|---|---:|---:|:---:|
| 128 | `cached_primal` | 14.760016 | 1,626,898 | No |
| 128 | `cached_token` | 1.493786 | 1,626,898 | No |
| 128 | `compressed_48` | 2.096019 | 1,554,233 | No |
| 128 | `gram_delete` | 99.786840 | 6,253,952 | No |
| 128 | `gram_fresh` | 22.182040 | 6,253,951 | No |
| 768 | `cached_primal` | 22.245019 | 5,071,731 | No |
| 768 | `cached_token` | 23.290473 | 5,071,731 | No |
| 768 | `compressed_32` | 56.414186 | 3,455,531 | Yes |
| 768 | `compressed_40` | 24.372360 | 4,045,355 | No |
| 768 | `compressed_48` | 24.361421 | 4,635,179 | No |
| 768 | `gram_delete` | 63.976924 | 6,255,266 | No |
| 768 | `gram_fresh` | 56.869621 | 6,255,265 | No |
| 1,536 | `cached_primal` | 31.323544 | 9,205,544 | No |
| 1,536 | `cached_token` | 86.450110 | 9,205,544 | No |
| 1,536 | `compressed_48` | 35.568671 | 8,332,316 | No |
| 1,536 | `gram_delete` | 22.674841 | 6,256,845 | No |
| 1,536 | `gram_fresh` | 98.466778 | 6,256,844 | No |

These payloads include retained descriptors or exact Grams, stage codes, and explicit metadata.
They exclude raw tokens, the shared checkpoint, and audit files.
They are not complete persistent service state.
A one-byte difference between Gram arms comes from metadata filename lengths.
Arm clocks include input loading, replay, accumulation, certification, diagnostics, and output.
Shared checkpoint construction, native builds, comparisons, and receipts are separately recorded.
Do not sum nested timing fields into their enclosing clocks.

## Findings

At 1,536 tokens, the primal solver is 2.759908 times faster than the token solver.
However, Gram deletion takes 22.674841 seconds versus the primal solver's 31.323544 seconds.
Gram deletion has 27.61% lower latency and 32.03% smaller payload than the cached primal arm.
It also dominates the 48-bit compressed arm in latency and payload.
An exact Gram control therefore cannot be omitted from the paper.

At 768 tokens, the 40-bit arm saves 20.2372% of payload against cached primal.
Its latency is 9.5632% higher.
This is a narrow development tradeoff, not a reliable complete-service benefit.
The 48-bit certificates accept at all three sizes without replay.
The 40-bit certificate also accepts at 768 tokens without replay.
The 32-bit certificate refuses at row 40, coordinate 424, with native status 3.
Its fallback regenerates six retained feature blocks and costs 31.454036 seconds.
The final result is exact, but the full arm takes 56.414186 seconds.
Neither the refusal nor its cost may be excluded.

## Accounting and audit

Preparation takes 140.189196 worker seconds and includes all thirteen source features and descriptor variants.
It spends 69.425049 seconds in the recorded exact Gram preparation field.
The model phase charges 877 of its 2,400 CPU-second allowance.
The separate data phase charges 5 of 122 seconds.
All five new workers have settled receipts; no new hold remains.
Software checks, setup, publication, and archive analysis sit outside those empirical ledgers.
Historical ledgers and unresolved historical holds remain unchanged.

CI compares actual code bytes and retained Gram archives before runner shutdown.
The local audit checks 164 published text files, source identities, receipts, ledgers, terminal copies, and ratios.
Seventy-seven derived binary artifacts are absent locally.
Their recorded CI comparisons cannot be independently repeated from hashes alone.
Do not describe the local metadata audit as a new numerical reproduction.

## Next decision

The Gram accumulator still uses Python integer loops.
A compiled exact integer implementation is necessary for a credible strongest-baseline comparison.
The cached primal arm also concatenates all retained features.
A blockwise version can remove that explicit total-token-dependent allocation.
V40 implements both improvements in a separate research directory.
Its new registration compares native Gram deletion, native fresh reconstruction, and cached or streamed feature routes.
Its compressed arm uses the exposed 40-bit development choice.
No cross-run V39/V40 timing ratio is a controlled treatment estimate.

If the stronger Gram baseline dominates, revise the method around that finding.
A cache-only speed claim would then lack defensible novelty.
The remaining opportunity is exact discrete code recovery with useful state, access, and lifetime tradeoffs.
That opportunity still requires complete-model validation, independent states, quality, and prospective confirmation.
The original sequential target still lacks a demonstrated full-model repair advantage.
