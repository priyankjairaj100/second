# Research decision after strengthening the Gram control

Updated 9 October 2026. The direction warrants targeted continuation, but the
paper is not ready for an ACL submission. The strongest evidence still concerns
one small model and a very small calibration workload.

## What this continuation resolved

The missing exact pooled-Gram control now exists and has been tested on a
complete first QKV stage. V35 checked four rows. V36 checked all 2,304 rows and
revealed avoidable generic interval-kernel overhead. V37 removed that asymmetry
by giving the Gram path the same native ball row kernel as the cached-feature
control, with a reviewed exact interval fallback for unresolved rows.

Every V36 and V37 arm matched all 1,769,472 archived reference decisions.
Repaired and independently rebuilt exact Gram bytes also matched.
All outcomes, including the slower original implementation, remain preserved.
These are development measurements on previously exposed real WikiText records.

| V37 complete first-stage arm | Seconds |
|---|---:|
| Pooled-Gram deletion and reconstruction | 17.724627 |
| Fresh retained-Gram construction and reconstruction | 17.158287 |
| Lossless feature decode and token reconstruction | 1.216621 |

The within-run deletion/cache ratio is 14.5687.
All three arms used the identical native row source and binary.
No row required fallback. Thus the cache advantage in this observation survives
removal of the identified row-kernel mismatch.
The measured Gram row time fell from 48.889642 seconds in V36 to 2.567298 seconds
in V37. These are separate development runs, not a randomized causal timing study.

The remaining Gram cost includes 9.266046 seconds for shared coefficients,
1.394124 seconds for exact Gram enclosures, and 3.887054 seconds for deleted-source
Gram accumulation. The cached-token coefficient calculation took 0.503930 seconds.
Retained token count is 128, while feature width is 768. These dimensions favor
token-space computation and representation. They do not establish the ranking
when retained tokens greatly exceed width.

The Gram archive occupies 5,020,445 bytes and the feature descriptor 688,713 bytes.
Adding the same 884,736-byte stage code payload gives 5,905,181 and 1,573,449 bytes.
These are payload sums, not complete canonical service-state implementations.
The Gram arm also requires deleted feature access before erasure.
It does not solve arbitrary identity-only deletion from a pooled matrix alone.

## What remains established only narrowly

Earlier complete-model WikiText experiments verified all 24 stages and
42,467,328 codes. Their two lossless repair/cold ratios were 1.8685 and 1.7883,
on two alternative deletions from one original state. The descriptive geometric
mean is 1.8279. One cold trial has a declared independently reviewed recovery.
There is no population latency interval or broad reliability guarantee.

The positive target uses fixed nearest-anchor features, preserving original
normalization. It differs from sequential GPTQ-style calibration.
The original sequential-target repair still lacks a complete-model speed advantage.
The new stage control does not change that conclusion.

Compressed repair remains a storage–latency tradeoff. In the later WikiText root,
it took 133.959649 seconds versus 76.827684 seconds for lossless repair on the same
request. It saved 5.5763% of service state, or about 0.70% including the common base
checkpoint. One rejected stage certificate caused eight retained neural traversals.
The new Gram result does not establish compressed superiority over lossless caching.

The candidate methods contribution remains certified exact discrete-code recovery
from uncertain compressed archives, with bounded fallback. Caching, fixed features,
additive moments, and reuse of the native ball kernel are supporting techniques.
This continuation introduces no claim that those techniques are novel.
The theory does not imply unconditional wall-time speedup or pretraining erasure.

## Next investment gates

These are research priorities, not retrospectively registered success thresholds.
Freeze actual thresholds before observing a future workload.

1. Restore a genuinely supported neural runtime, then register fresh C4 preparation
   and paired reconstruction. The historical failed campaign cannot be resumed by
   inventing old runtime facts. `RUNTIME_PORTABILITY_PLAN_V37.md` specifies what a new
   backend would require; no such backend is implemented or validated yet.
2. Test a materially larger real calibration workload, with token counts spanning
   the feature width. Compare complete services, matched source access, explicit
   state storage, and preparation costs. Use a reviewed dimension-appropriate
   Gram/factor control rather than extrapolating this low-token stage result.
3. Determine whether compressed certification offers a useful complete-state
   storage–latency frontier against the lossless cache. Charge fallback, conversion,
   and successive deletion-state maintenance. A favorable cold-only comparison
   cannot answer this stronger question.
4. Expand to another model and independent requests only after those mechanisms
   survive their pilots. Freeze the method before prospective confirmation and
   keep all 60 exposed quality articles excluded.
5. Complete the direct closest-work comparison and bind every final paper claim
   to audited measurements or explicitly conditional theorems.

The new control closes a concrete baseline-quality objection for one stage.
It does not close full-model Gram comparison, C4, larger calibration scale,
independent confirmation, complete lifetime costs, or publication novelty.
The appropriate decision is bounded continuation, not a claim that the full
empirical program or theory-and-experiment package is finalized.
