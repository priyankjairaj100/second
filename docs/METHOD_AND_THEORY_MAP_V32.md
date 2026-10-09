# Method and theory map for continuation

This is a navigation aid, not a new proof or novelty assessment.
It identifies the implemented target and the strongest existing arguments.
Read the linked derivations before changing any numerical code.

## The target

The pretrained checkpoint stays fixed.
A base-only nearest-grid ancestor model produces each document's calibration features.
Those features do not depend on other calibration documents.
The target keeps its original normalization after deletion.
It also fixes ridge, grids, coordinate order, arithmetic semantics, and tie rules.

For retained sources R, each stage uses H(R) = lambda I + X(R)X(R)^T / nu.
Each successful finite feature value represents its exact dyadic rational.
The declared adaptive rounding recurrence determines the discrete weight codes.
Unsupported feature evaluation or unresolved certification causes refusal.

This target differs from sequential GPTQ calibration.
Earlier repaired weights do not change this target's surviving source features.
The original sequential implementation remains a separate, unsuccessful efficiency experiment.
No result removes information already present in the pretrained checkpoint.

## The implemented service

| Component | Current reference | Contract |
|---|---|---|
| Fixed source-local factors | `docs/FIXED_FACTOR_V22.md` | Unchanged retained features under source deletion |
| Lossless state and repair | `docs/FIXED_LOSSLESS_SERVICE_V29.md` | Exact stored factors, full model, canonical state under fixed policies |
| Ordered finite decoder | `docs/ORDERED_FINITE_DECODER_V30.md` | Shared feature execution for repair and cold controls |
| Adaptive compressed service | `docs/ADAPTIVE_COMPRESSED_V30.md` | Universal verification, refinement, charged replay, explicit refusal |
| Native box coefficients | `docs/NATIVE_BOX_COEFFICIENTS_V31.md` | Strict directed bounds for uncertain features |
| Integrated compressed policy | `docs/COMPRESSED_FOLLOWUP_V31.md` | 48-bit descriptors, four-bit model codes, unchanged point target |
| Recovery execution | `scripts/launch_independent_requests_v32.py` | Fresh runtime registration and complete retained-model comparisons |

V32 changes recovery and evidence handling only.
Its numerical source inventory must match the published V31 pilot exactly.
The recovered input helper does not retokenize selected sources.

## The theory package and its limits

| Result | Reference | What remains conditional |
|---|---|---|
| Exact compressed repair | `docs/ADAPTIVE_COMPRESSED_V30.md` | Trusted feature containment, accepted universal certificates, successful exact fallback |
| Canonical successor state | `docs/FIXED_LOSSLESS_SERVICE_V29.md` and compressed service contract | Fixed preparation, codec, provenance, and serialization policies |
| Sparse verification schedule | `docs/SPARSE_CERTIFICATE_V30.md` | Structural work accounting; no universal latency advantage |
| Primal residual certificate | `docs/PRIMAL_CERTIFICATE_V30.md` | Directed Gram bounds and verified residuals; proposals remain untrusted |
| Native coefficient verification | `docs/NATIVE_TOKEN_COEFFICIENTS_V30.md` and V31 native review | Strict arithmetic and supported runtime assumptions |
| Response information lower bound | `docs/RESPONSE_LOWER_BOUND_V29.md` | Declared finite access model and same-original-snapshot deletion responses |

The primal method uses width-based arrays instead of token-quadratic arrays.
Its structural work is O(d^2 T + d^3 + m d^2).
Its residual coefficient bound includes K_hh times the squared residual, divided by 4 beta.
The implementation also verifies an independent ridge-based bound.
These arguments establish sufficient correctness conditions, not the fastest backend in every case.

The response bound is ceil(log2(binomial(N, N/2))) archive bits without record probes.
Its probe extension bounds cumulative archive bits plus probes.
It is not a per-request lower bound for changing-state sequences.
It does not establish transformer realizability or practical speed.

Resource admission bounds specified schedules and explicit array allowances.
It does not guarantee total process memory fit, certificate success, or completion within the CPU limit.
The process controller supplies separate resource limits.
No approximate model is released after a failed exactness check.

## Positioning that the evidence can support

The candidate contribution concerns exact discrete calibration-code recovery from uncertain stored enclosures.
It combines useful storage reduction with conditional exactness and measured repair cost.
Frozen features, additive removal, cached factors, and interval arithmetic are established ingredients.
Their combination alone does not establish publication novelty.

Read `docs/NOVELTY_AUDIT_V30.md` for the existing source review.
It identifies QSS, MEDU, frozen-model ridge deletion, and executable certificate work as close references.
The detailed ExecCert comparison remains unfinished.
Search absence does not prove priority.

Read `docs/POOLED_GRAM_CONTROL_V30.md` before claiming baseline dominance.
Exact pooled Gram storage plus deleted-record replay remains an important unmeasured control.
Its access contract and exact accumulator storage must be explicit.
The current lossless indexed constructor is already a strong control with the same numerical algorithm.

The current positive experiments support a restricted storage and latency tradeoff.
They do not prove universal repair speed, quality superiority, or general sequential unlearning.
Use `docs/EMPIRICAL_STATUS_V32.md` and the actual receipt audits for numerical claims.
