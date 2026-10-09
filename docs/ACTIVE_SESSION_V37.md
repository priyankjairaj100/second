# Shared-kernel complete-stage Gram comparison

Updated 9 October 2026. This checkpoint supersedes older execution-status notes.

V36 completed and independently verified all 1,769,472 first-QKV code decisions
in three arms. Pooled-Gram deletion took 65.995601 seconds, fresh Gram reconstruction
61.257673 seconds, and cached-feature reconstruction 1.299832 seconds.
The registered phase charged 139 CPU seconds. Its source, protocol, and results
are preserved at GitHub commit `9ff391899307b2384b7e708cf203430e90dd69b4`.

The audit found avoidable work in the generic interval row verifier used by the
Gram solver. Native row verification alone took 48.889642 seconds.
The large observed gap is not a comparison against an optimal Gram method.
V37 gives the direct-Gram path the existing faster certified ball row kernel.

The new adapter keeps the exact accumulator and coefficient enclosures unchanged.
An identity-feature representation gives the same direct-Gram rounding recurrence.
A rigorously rounded Euclidean coefficient-error bound supplies the ball certificate.
Any unresolved ball rows receive the original interval verifier with shared coefficients.
Every fallback cost is included. Unresolved final output is refused, never approximated.

Current state: reviewed, registered, and unstarted.
Program SHA-256: `7c4fd95b6645a20adc7b4c1b84f20cc7d354348c4b4061f7ac8e76e887ec29da`.
All 19 focused software fixtures pass. Read `GRAM_BALL_REVIEW_V37.md`.
The next action is protocol publication followed by the one registered execution.
The new controller is `scripts/launch_gram_ball_stage_v37.py`.
Its campaign is `campaigns/pooled_gram_ball_stage_v37`.
It reuses the committed V36 full-stage capsule. No new data selection occurs.
The original normalization, ridge, source records, grids, and complete row extent stay fixed.
Read `LOCAL_GRAM_BALL_STAGE_V37.md` for fresh local reproduction.

This is adaptive algorithm development after inspecting V36 diagnostics.
It needs its own reviewed protocol, registration, and GitHub checkpoint before execution.
There is one attempt under a separate 900-second CPU phase and 880-second worker cap.
Previous ledgers and all V35/V36 numerical files remain immutable.
Do not retry historical attempts or turn refusals into completed-time speed ratios.

The full-model C4 program remains blocked by unavailable required runtime interfaces.
Its failed repair and four unstarted trials are not scientific losses or completed experiments.
Do not invent runtime facts or silently weaken an existing runtime contract.
Read `ACTIVE_SESSION_V34.md` for the preserved incident and compatible local path.

The broader research program remains incomplete. Exact full-model WikiText agreement
and narrow repair speed observations are established for fixed nearest-anchor features.
They do not apply to the original sequential target, whose measured repair still loses.
The compressed archive method currently offers a storage–latency tradeoff and does not
dominate the lossless cache. Its strongest candidate contribution is certified exact
discrete-code recovery from uncertain archived features.

Larger calibration workloads, full-model Gram comparisons, additional models,
changing-state lifetime costs, prospective confirmation, and the final novelty comparison
remain open. The paper is not submission-ready.
