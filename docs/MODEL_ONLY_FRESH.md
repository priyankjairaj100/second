# Fresh model output without a deletion index

Revision 8 adds the conventional output contract as an explicit control.
The complete target remains `V_cert`.
Only the retained quantized model is returned.
No response index, Gram cache, deletion metadata, or chart is constructed.
This output cannot support another deletion without additional preparation.

## Why this control is necessary

The existing `direct_fresh` method constructs both the retained model and canonical deletion state.
It remains the independent oracle for complete state equality.
Its cost includes response extraction or cache construction.
That extra output is unnecessary for ordinary one-time requantization.
A gain against that oracle alone cannot establish faster model-only requantization.

The new control skips response extraction and persistent cache construction.
It evaluates retained features under every newly constructed ancestor prefix.
It builds each exact Gram, applies the fixed normalization and ridge, and executes the exact quantizer.
Temporary Grams are discarded after use.
All original stages and codes remain part of the output.

The control uses the same certified finite evaluator and exact quantizer as the main target.
It provides an independent full replay control flow.
It is not an independently implemented numerical library.

## Equality contract

`src/model_fresh.py` exports `fresh_model` and `target_model_bytes`.
The canonical model encoding includes the common target digest and every stage's exact codes.
It excludes each service family's state digest.
Family-specific model artifact hashes can differ even when their codes agree.
Use the common target encoding for comparisons across families.

For each stage, exact retained feature evaluation produces the target Gram.
The exact quantizer then produces the target stage output.
Induction through dependencies establishes the complete model.
Empty retained input produces the fixed ridge-only target.
The original normalization remains unchanged.
A necessary finite-evaluator failure aborts construction.

## Local execution

```bash
python scripts/run_model_fresh.py run.json --output model-only-result
```

The CLI accepts the existing local run manifest.
It validates the checkpoint, calibration input, source code, target, and protocol bindings.
It skips heldout input loading because this output contract does not request evaluation.
It skips chart construction and deletion state construction.
It retains a conservative rank-zero resource plan under the declared resource limits.
This plan can overestimate the baseline's storage.
It cannot establish measured memory fit.

The calibration manifest still contains original records.
The CLI reads that manifest and removes the declared records before feature evaluation.
This file layout imposes a real parsing cost.
The control does not represent every possible optimized requantization implementation.

The output contains `model.json`, its manifest, and a durable result receipt.
The receipt declares `output_contract="model_only"`.
Repeated invocation verifies saved artifacts before returning the original receipt.
It must not report cached receipt reuse as a new fresh latency measurement.
Use the measured process wrapper for the complete child transaction.
Internal telemetry remains diagnostic.
Research feasibility and development require a live CPU admission record for the exact measured command.
The measured wrapper creates that record under the protocol budget.
Standalone confirmation remains blocked until a frozen inventory includes this control.
Research remains paused.

## Comparison rules

| Claim | Required comparison |
| --- | --- |
| Same model after deletion | Common target digest and all stage codes |
| Same complete live state | Within-family retained `direct_fresh` oracle |
| Faster ordinary requantization | Model-only fresh under the same complete measured boundary |
| Cheaper maintenance of deletion state | Equally indexed fresh with the same valid information |
| Better lifetime cost | Original preparation plus every request, output, verification, and required state cost |

Never charge response preparation only to the ordinary requantization control.
Never remove index maintenance from the repair lifetime.
Keep model-only, canonical-state, comparison, and sequence clocks separate.
Real speed, quality, and resource feasibility remain unmeasured.
