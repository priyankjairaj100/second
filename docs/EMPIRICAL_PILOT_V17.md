# Revision 17: faster exact arithmetic, without a repair advantage

Date: 7 October 2026.
This report separates shared implementation gains from deletion-specific gains.
All seven registered workers completed.
No confirmation experiment ran.

## Result

A native ball certificate replaces expensive directed tensor scans.
The kernel preserves the exact dyadic target and uses the existing certified fallback.
Both reconstruction and repair receive this improvement.
Twelve stage comparisons matched their exact references.
Six complete transactions matched the corresponding revision 15 model.
Original and retained canonical states also matched their references byte-for-byte.

The native cold solver improved stage median time by 7.39x on WikiText and 8.25x on bounded C4.
These ratios compare three native observations against one reference observation per corpus.
The matched complete reconstruction improved from 194.774 seconds to 71.860 seconds, a 2.710x ratio.
This is one observation per implementation, not a population estimate.

Repair took 84.225 seconds.
Native cold reconstruction took 71.860 seconds.
Native reconstruction with complete state took 65.853 seconds in its separate observation.
Repair therefore has no demonstrated advantage over optimized reconstruction.
The faster complete-state observation does not prove state construction has negative cost.
Run order, process variation, and nested work differ across these single observations.

## Complete transaction record

Each root contains two WikiText records with sixteen tokens per record.
Deletion removes the first sorted record, leaving one record.
The model is pinned DistilGPT2.
The target uses four-bit dyadic row grids with twenty-four significant bits.
Original normalization remains 32, and ridge remains 0.01.
The model contains 24 projection stages and 42,467,328 code values.

| Attempt | Transaction | Solver | Worker seconds | Charged CPU seconds |
|---|---|---|---:|---:|
| 002 | Original complete state | Native | 116.720 | 117 |
| 003 | Retained repair | Native | 84.225 | 85 |
| 004 | Retained cold model only | Native | 71.860 | 72 |
| 005 | Retained cold model only | Reference | 194.774 | 195 |
| 006 | Retained warm model only | Native | 86.100 | 86 |
| 007 | Retained complete state | Native | 65.853 | 66 |

The warm control receives the same original model codes, without original calibration factors.
Repair was 2.18 percent faster than this warm control in these observations.
This small difference does not establish reliable superiority.
The cold control was faster than both candidate-based methods.
Candidate decoding and checking can add work.

Worker time includes startup, loading, first compilation, service execution, and output serialization.
It excludes controller work and source snapshot preparation.
Operating-system cache and other machine activity were uncontrolled.
Nested diagnostic clocks overlap and must not be summed with their enclosing clocks.
These observations do not establish complete deployment latency or preparation-inclusive lifetime gains.

## Stage screen

Attempt 001 uses frozen WikiText and bounded C4 inputs.
The C4 input is a bounded shard prefix, not the declared final sampling frame.
Each retained calibration has sixteen tokens.
Three alternating cold and warm observations ran per corpus.
All twelve comparisons matched the reference, without fallback rows.

| Corpus | Reference seconds | Native cold median | Native warm median |
|---|---:|---:|---:|
| WikiText | 6.362007 | 0.860820 | 0.891097 |
| Bounded C4 | 5.571126 | 0.675632 | 0.742235 |

The screen charged 65 CPU seconds.
Warm candidates did not improve either corpus median.
No stage timing supports a complete-model or population claim by itself.

## Algorithm and proof

Read NATIVE_BALL_PROOF_V17.md and NATIVE_BALL_REVIEW_V17.md.
The native loop maintains a rounded residual accumulator and conservative error bounds.
Bounds include subtraction, products, accumulated sums, coefficient uncertainty, and underflow.
Unsupported arithmetic or uncertain decisions prevent native acceptance.
Unresolved rows enter one existing certified solver call.
Exact and refinement budgets therefore remain global.
The compiler disables fast arithmetic and fused contraction.
The proof assumes the documented binary64 runtime premises.
The independent review found no defect under these premises.
It is not proof-assistant verification.

Candidate codes only change the first cell checked.
They do not avoid the accumulator or dot-product work.
Repair matched 40,498,834 of 42,467,328 proposed codes during candidate checking.
High candidate agreement therefore does not imply high computation avoidance.

## Remaining algorithmic obstruction

Read section 7 of BLOCK_LOW_RANK_DESIGN_V17.md.
The current cache binds each factor to its complete ancestor-code prefix.
A changed early stage invalidates all later factor entries.
The first cache miss starts feature execution from the beginning.
The final factor therefore requires a complete retained feature traversal.

Repair executed 24 neural stage-record pairs and read one cached factor.
Cold reconstruction executed the same 24 neural pairs without that cache read.
Repair avoided zero changed-ancestor pairs.
The operation-count theorem applies to this service implementation.
It is not a universal lower bound on repair or wall time.
A shared arithmetic improvement cannot alone remove this obstruction.

A useful successor must avoid retained feature work or other substantial work beyond compatible reconstruction.
A resumable frontier alone saves only the unchanged prefix.
The observed first-stage change gives that prefix no useful depth.
Exact changed-prefix transport or a useful alternative canonical state remains necessary for the proposed feature-saving route.
Block low-rank updates remain a separate design, without implementation or timing evidence.
Do not expand the present identity route merely to seek favorable timing noise.

## Exactness and reproducibility

The target digest is `1e254f573e2cc8249c7aff653940f6c267d28ef40bc8ec950691b02dc215bc13`.
The retained model digest is `25a5a1ace3884a2d1b291ba8299a61e41b437e215ce6ea3457634479fecae302`.
The original state occupies 30,467,831 bytes.
The retained state occupies 26,330,225 bytes.
The read-only analyzer checked actual output bytes before this checkpoint.
Large binaries remain ignored and must be regenerated after a fresh clone.
Without those binaries, the analyzer explicitly reports digest-only artifact verification.

Use a new output path:

```bash
python scripts/analyze_native_complete_v17.py --output /tmp/v17-analysis.json
```

Plans, frozen programs, source snapshots, receipts, and all outcomes remain archived.
The final focused regression passed 32 tests.
It covered native certificates, service integration, prior services, compact state, grids, and inherited budgets.
This was not a full-suite rerun.
The first test command could not run because pytest was unavailable.
The archived unittest command then passed.

## Budget and scientific status

This revision charged 686 CPU seconds.
The inherited total is 10,509 CPU seconds.
The unchanged 10,800-second allowance has 291 seconds remaining.
All empirical workers are settled.
Software tests and controller work remain separate overhead.
No paid cloud job ran.

No new quality records were evaluated.
The earlier positive quality pilot still contains four articles and sixty predictions.
All ten earlier evaluated article exclusions remain active.
The two-root feasibility sequence and forty scientific cells remain unpromoted.
Larger quality, repeated deletion, lifetime gains, and independent confirmation remain open.
The project is not ready for a paper claiming reliable repair superiority.
