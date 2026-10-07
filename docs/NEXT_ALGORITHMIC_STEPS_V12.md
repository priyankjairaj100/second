# Algorithm changes motivated by revision 12

Row scaling has now been implemented and tested on a tiny diagnostic.
Its ratio improved from 8.102 to 1.315, which remains above the 1.20 screen.
State and transport changes below remain proposals, not demonstrated fixes or novelty claims.
The existing poor-quality and resource observations remain part of the record.
Large experiments must stay blocked until the replacement passes fresh pilots.

## 1. Test fixed output-row scaling

The current grids share an input-column scale across all output rows.
Packed QKV rows can have different weight magnitudes.
The first block's value codes are approximately 92 percent zero in both observed quantized models.
This motivates a grid-allocation control; it does not establish a causal explanation.

For output row r, choose a positive power-of-two scale a_r using base weights only.
Normalize that row as w'_r=w_r/a_r.
Quantize normalized rows on a shared fixed integer codebook, then install q_r=a_r q'_r.
The scales remain fixed after every deletion.
This defines a different, explicitly versioned quantizer target.
It must not replace the current target retrospectively.

### Exact equivalence for the proposed target

Let L be the same reverse-LDL feedback coefficients for a supplied exact feature metric.
The normalized decision input satisfies

v'_i=w_i/a_r+sum_{h<i} L_ih(w_h/a_r-q'_h).

Assuming earlier installed codes satisfy q_h=a_r q'_h, this equals v_i/a_r.
Positive scaling preserves code order and lower-code ties.
Induction proves equivalence to directly using the scaled row-specific codebook.
The identity applies separately to each output row.

The token-space coefficient solver depends on features and the metric, not output-row scales.
It therefore supports this reparameterization without changing its coefficient identity.
Certified decisions must still use exact representable inputs and the declared rounding rules.
Power-of-two conversion needs explicit overflow, underflow, and representability checks.
Exact grid-code restoration must precede downstream calibration evaluation.
The complete sequential model changes and must be requantized.

### Prospective pilot

Compare current column grids and fixed output-row grids at the same bit budget.
Add nearest-rounding controls to separate grid effects from calibration feedback.
Use identical base weights, real records, token counts, normalization, and resource limits.
Give every compatible baseline the same row-scaling implementation.
Bind every scale, codebook, source version, and output encoding.
Retain all failed quality and exactness outcomes.
The existing two validation IDs are development diagnostics and remain excluded from confirmation.

This is a conventional quantization control, not the paper's novelty claim.
It must not be promoted merely because it improves one tiny pilot.

## 2. Replace the committed state encoding

The specified dense rational-pair state cannot fit the current single-file cap.
See V12_REPAIR_INTEGRATION_AUDIT.md for the 523.125 MiB lower bound and its assumptions.
Changing the finite kernel cannot resolve that encoding obstruction.

A new family can encode grid indices compactly and bind fixed scale metadata separately.
A factor representation can store exact binary64 feature factors in deterministic record-and-token order.
Its represented Gram remains exact, but its storage grows with retained token count.
This changes the aggregate-only storage contract and requires a revised cost theorem.

Deletion must preserve canonical factor ordering and purge removed record factors.
Fresh retained construction and repair must commit identical declared state bytes.
Repeated deletion must agree with combined deletion.
Every comparator must receive the same compatible representation and solver.
Packing and output verification belong inside complete transaction costs.

## 3. Preserve the hard scientific requirement

A compact factor cache alone does not establish changed-ancestor feature avoidance.
It can reuse unchanged prefixes and replay changed prefixes.
The intended paper additionally needs a sound, efficient feature-transport certificate.
Current scalar rational proof jets and dense verification have no successful complete-model admission.
A compact interval or structured response implementation needs independent arithmetic validation.

Only after complete state and transport work passes should the four-method feasibility pilot resume.
That pilot must meet unchanged correctness, quality, coverage, resource, and preparation-inclusive cost requirements.
No revision 12 observation proves reliable full-model repair speedup.
