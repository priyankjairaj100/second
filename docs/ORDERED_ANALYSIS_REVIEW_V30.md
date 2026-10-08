# Independent ordered analysis review

The completed ordered-service audit reproduces from its archived evidence.
No error affects its reported timings, output agreement, or phase accounting.

| File | Reviewed SHA256 |
|---|---|
| `scripts/analyze_ordered_service_v30.py` | `d6f0229d8375f320e1debc53cdb8f1aa8fc109b4eedb16ae7964f23fdf9ce07e` |
| `tests/test_ordered_service_analysis_v30.py` | `d1ad8e95402f5b59132c2229a990a5f6a605b24e5634690a45cf84f4af4bee34` |
| `campaigns/ordered_service_v30/audit.json` | `56318bd9458043c716a7379dc8166cb84b40d80499e6e23eb7c90a97c84ca4c1` |

## Verified scope

The source review checked registration, late-bound inputs, frozen worker sources, external references, and command identities.
All nine registered trials must appear exactly once.
Each settled receipt must correspond to one phase debit.
The final ledger must contain exactly those receipts and no unresolved reservation.

Original and retained ordered models match their respective scalar reference artifacts.
Within the ordered phase, methods with matching retained membership also match complete model bytes.
Stateful methods with matching membership match state bytes.
These checks do not compare historical and ordered provenance-bearing state bytes.

The feature audit recomputes all 48 saved descriptor comparisons without neural evaluation.
It verifies binary64 feature words and canonical descriptors across both original records and all 24 stages.
The source manifest binds the current reconstruction of that earlier report.

Complete controller clocks supply all latency ratios.
Nested worker and service clocks receive no additional weight.
The preparation comparison uses the same original corpus and optimized model target.
The lifetime illustration explicitly repeats one request from the same original state.
It makes no claim about an evolving deletion sequence.

## Independent verification

Fifteen common and ordered analyzer fixtures passed in a reported 0.176 seconds.
An independent read-only replay then reconstructed the completed audit.
Every field matched except the two clocks for analysis itself.
The replay consumed 16.611763491 CPU seconds and did not alter the worker ledger.

The replay confirmed these recorded results:

- Nine completed trials and 1,323 charged worker CPU seconds.
- Three timing pairs with a geometric mean cold/repair ratio of 2.0387524009663163.
- All three observed pairs favor repair on the same deletion request.
- Complete model agreement across all 24 stages and 42,467,328 codes.
- A measured preparation increment of 22.695266794 seconds.

These observations remain development evidence from one model, corpus, and deletion request.
They do not establish population superiority, a changing-state lifetime benefit, or language-quality superiority.

## Helper edge case corrected after the archived audit

The generic timing helper has one edge case outside the archived measurements.
Negative preparation overhead and nonpositive request savings produce no reported strict break-even count.
However, zero repetitions already satisfy its displayed inequality when preparation overhead is negative.
The archived preparation overhead and request savings are positive, so its reported result remains correct.

The current helper now returns zero whenever preparation already satisfies the strict inequality.
This first successful count does not imply that the advantage persists as requests accumulate.
A new fixture covers zero savings, negative savings, later losses, and equality at zero overhead.
Sixteen common and ordered fixtures passed in a reported 0.184 seconds after this correction.

The corrected analyzer hash is `39c531122590163800a567516d401d438d7214b4c8ba3c8cbf2a95bd06ec6b84`.
The corrected test hash is `115b2f1d69c0699dd79f2741dfc466054f508303945058c570db9418441a2d5e`.
The original analyzer remains preserved under `campaigns/ordered_service_v30/analysis-source-snapshots/`, named by its reviewed SHA256.
The immutable audit and all original transaction evidence remain unchanged.

No model inference, empirical trial, or immutable audit edit occurred during this review.
