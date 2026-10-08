# Maintained pooled-Gram control: scope and pilot judgment

This is a required control for broad fixed-feature efficiency claims.
It is not required to state the narrower observed comparison against model-only cold reconstruction.
The existing metric-sufficiency and canonical moment-state results already cover its mathematical target.
No complete fixed-target implementation or empirical comparison currently covers this maintained-state baseline.

For each stage, store the exact pooled Gram and retained membership.
At deletion, subtract exact deleted contributions and preserve the original normalization.
Deleted-record replay can supply those contributions before erasure.
Otherwise, a request needs stored source contributions or another sufficient access mechanism.
An identity-only request cannot generally recover deleted contributions from one pooled Gram.

## Concrete feasibility

The archived target has eighteen width-768 stages and six width-3072 stages.
Their packed symmetric Grams contain 33,636,096 entries in total.
One binary64 word per entry would occupy 269,088,768 bytes before metadata.
This is an illustrative representation count, not an exact accumulator size or compression lower bound.
Exact accumulators can require more bits; compression can reduce stored bytes.

Straight symmetric accumulation over 256 original tokens requires 8,610,840,576 scalar product contributions.
Deleting 128 tokens requires 4,305,420,288 such contributions, plus feature replay and model solving.
These counts follow from archived dimensions; they are not measured runtimes.

The current primal implementation cannot serve as an immediate full-model Gram-only solver under the registered limits.
Even with zero feature-token storage, a width-3072 down-projection requests 36,238,811,136 structural work units.
Its explicit array estimate is 3,210,166,272 bytes.
The current limits are six billion work units and 512 MiB per point stage.
Both limits reject this route before execution.
These are implementation limitations, not impossibility results for pooled-Gram methods.

## Bounded useful next pilot

A first-stage component pilot is feasible after dedicated implementation and review.
Use the existing real 256-token feature archive and retain the full width 768.
Evaluate four complete output rows, preserving every coordinate and the original grid.
Do not crop feature coordinates, which would change the target.

The original packed Gram needs 75,595,776 exact product contributions.
First admit actual accumulator bit widths, temporary storage, and operation limits from the saved feature words.
Implement canonical exact accumulation and a reviewed direct-Gram certificate entry point.
Existing coefficient and row verification can supply components, but the current public API requires feature arrays.

Compare original-minus-deleted moments with independently accumulated retained moments exactly.
Then require all complete row codes to match the existing retained reference.
Charge preparation, decoding, exact accumulation, serialization, solving, verification, and output separately.
Cached archive features exclude neural replay, so this pilot cannot establish complete service latency.
Any complete follow-up must additionally charge deleted-only feature replay and the new canonical state contract.

The recommendation is to retain this control as a submission requirement for broad efficiency positioning.
Do not expand the current full-model campaign into an unreviewed Gram implementation.
A bounded component pilot can resolve its practical promise before a separately admitted full service.
Neither current factor-storage counts nor cold speedups establish superiority over this control.
