# Revision 13 research decision

This revision separates three questions.

1. Can the complete model and retained state fit the worker limits?
2. Do repair and retained reconstruction return exactly the same artifacts?
3. Does repair avoid enough work to support the paper's efficiency claim?

The first question now has a positive real-model observation.
The second question has a complete diagnostic program.
The third question remains a separate scientific requirement.

## A precise state limitation

Let the canonical state contain exact retained factors at the current model prefix.
Let a certificate prove one code matrix throughout a non-singleton factor box.
Suppose two factors in that box have different canonical bytes.
The code certificate then cannot identify the required factor bytes.
Therefore, code constancy alone cannot establish that canonical state.
A valid implementation must recover the factors or use a different declared state family.

A one-coordinate example makes the distinction explicit.
Set the base weight to zero and use a grid containing zero.
Both feature factors Z=[1] and Z=[2] produce the exact code zero.
Their factor bytes differ, and their unregularized Grams are 1 and 4.
An assertion about that code therefore cannot identify either factor state.
This algebraic example is a proof example, not an empirical dataset.

This is an information distinction within the declared state contract.
It is not a universal lower bound on neural evaluation.
Additional side information could determine the exact factors.
A different canonical representation could also remove that particular requirement.

## The implemented identity cache

The compact identity cache requires identical ancestor prefixes before factor reuse.
Every other case invokes exact retained replay.
Thus, its changed-ancestor avoidance counter is identically zero by construction.
This holds on every dataset, regardless of observed timing variation.
It cannot meet the existing one-quarter avoidance requirement.
More repetitions cannot change that algorithmic fact.

When every retained stage input is replayed, both methods perform the same finite feature program.
They also solve the same exact quantization problems.
Repair additionally validates and commits its declared retained state.
This explains the absence of a deletion-specific computational shortcut on that path.
It does not prove a pointwise wall-clock inequality.
Cache state, allocation, and machine activity can alter individual clock readings.

## What the box certificate closes

The new certificate avoids dense input-coordinate Gram matrices.
It proves exact code constancy throughout a supplied factor box.
Its storage depends on token rank and output dimensions.
Its theorem includes feature uncertainty and numerical proposal errors.
It rejects unresolved cells rather than returning an approximate model.

The transformer box evaluator supplies sound finite feature bounds.
However, that evaluator currently traverses retained tokens.
The traversal remains part of the complete query cost.
Its use cannot establish source avoidance merely by changing the counter name.

## What a successful successor must add

One possible successor uses canonical anchors independent of deleted calibration records.
Each such anchor depends only on its surviving record and fixed base parameters.
It must construct useful changed-prefix bounds without full retained replay.
Another possibility reconstructs exact current factors through a cheaper transport algorithm.
Calibration-independent anchors are sufficient for the conditional design, not necessary for every valid design.
It must pass the same exactness, quality, storage, and preparation-inclusive cost requirements.
Every compatible baseline must receive common kernel and solver improvements.

The conditional anchor theorem appears in TOKEN_BOX_CERTIFICATE_V13.md.
The theorem does not establish a practical bound provider or useful acceptance rates.
These remain algorithmic research requirements.
A reliable full-model repair speedup must not be asserted before they pass.
