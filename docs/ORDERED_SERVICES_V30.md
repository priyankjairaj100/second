# Explicit ordered services, revision 30

## Scope

The new services use explicit ordered neural execution for fixed-feature calibration.
They preserve the fixed-feature target, exact model codes, and canonical storage formats.
They record a new preparation identity because different source code prepares the factors.

These services do not implement repair for the original sequential calibration target.
They do not establish a measured full-model speedup.
The focused checks below are software fixtures, not empirical datasets.

Historical source files remain unchanged.
No global function replacement selects the new implementation.

## Interfaces

```python
from src.ordered_finite_decoder_v30 import OrderedFiniteDecoder
from src.ordered_fixed_service_v30 import (
    OrderedFixedAnchorService,
    ordered_preparer_binding,
    prepare_ordered_leaf,
)
from src.ordered_lossless_service_v30 import OrderedLosslessService

decoder = OrderedFiniteDecoder(base_decoder, primitive_backend="mpfr_enclosure")
exact = OrderedFixedAnchorService(decoder, base_target)
lossless = OrderedLosslessService(decoder, base_target)

prepared = lossless.run(records, method="direct_fresh")
repaired = lossless.repair(prepared.state, deleted_ids)
indexed = lossless.indexed_fresh(prepared.state, deleted_ids)
cold = lossless.run(retained_records, method="model_only_fresh")
```

Both constructors accept `solver_backend`, `progress`, `coefficient_budget`, and `max_point_work_units`.
Point routes are `auto`, `token`, and `primal`.
The default cumulative point allowance is 48 billion structural work units.
The default coefficient allowance comes from `AdaptiveBudget`.

The exact service also accepts `state_backend="factors"` and `use_candidates=False`.
Other state backends and model candidates are rejected.
Both services require an actual `OrderedFiniteDecoder` and four-bit target grids.

Both `run` interfaces support these methods:

| Method | Neural preparation | Successor state |
| --- | --- | --- |
| `direct_fresh` | All retained records | Canonical exact or lossless state |
| `model_only_fresh` | All retained records | None |
| `repair` | Reuse retained prepared factors | Canonical exact or lossless state |
| `indexed_fresh` | Reuse retained prepared factors | Canonical exact or lossless state |

Repair and indexed reconstruction share their numerical algorithm.
Separate observations are required before comparing their measured times.

`OrderedFixedAnchorService.run_prepared` accepts exact `FixedFactorLeaf` objects and an explicit external preparation receipt.
The receipt contains `source`, `artifact_sha256`, and nonnegative `elapsed_ns` fields.
The service records that provenance; it does not verify an external elapsed timer.
Old anchor objects are never silently converted into ordered preparation.

## Mathematical target and implementation identity

`OrderedFiniteDecoder` preserves the reference evaluator identity and target kernel manifest.
Its separate `implementation_manifest` identifies the actual ordered decoder, attention, and primitive sources.
The service records this manifest in every successful receipt.

Preparation feeds fixed nearest-grid ancestor matrices into `ordered_sequential_features`.
The generator name describes traversal order; it does not change this fixed-feature target into sequential calibration.

`ordered_preparer_binding()` hashes a distinct schema and the actual preparation dependencies:

```text
ordered_fixed_service_v30.py
ordered_finite_decoder_v30.py
ordered_attention_v30.py
fixed_factor_state.py
anchor_transformer.py
ordered_finite.py
finite_primitives.py
certified_intervals.py
certified_transformer.py
transformer_backend.py
```

The existing exact and lossless formats accept this new, internally consistent binding.
Ordered states therefore differ from historical states even when every factor and model bit agrees.
This difference records actual preparation provenance.

Historical preparer states are rejected before lossless decoding.
Full deletion still validates the preparer, decoder, provider, and anchor bindings.
The prepared-leaf route validates the same provenance through the exact state envelope.
Within the new preparation family, fresh, repaired, and indexed successor states are canonical.

Preparation manifests depend on source bytes.
Freeze all bound sources before registering workers or creating reusable states.
Never relabel a historical artifact with the new preparation identity.

## Correctness argument

The ordered decoder establishes the same finite neural values under its documented numerical premises.
Consequently, feeding identical fixed ancestor matrices produces identical factor values.
The shared adaptive point solver certifies the same exact rowwise quantization target.
It uses identical target weights, scales, ridge, and original normalization.

Deleting complete source records removes their factors.
Reconstruction concatenates surviving factors in canonical record order.
Its exact features therefore equal fresh ordered preparation on those surviving records.
The same certified point solver produces the same complete model codes.
Canonical state assembly produces the same successor state within the ordered preparation family.

This argument requires valid prepared factors and the ordered decoder's numerical premises.
Hashes identify prepared content; hashes alone do not prove numerical preparation correctness.
No result here proves useful speed, general transformer support, or equivalence to a different quantizer.

## Resource admission and refusal

Every stage receives an allocation-free point route assessment before context construction or neural preparation.
The service sums selected stage allowances before admitting the complete request.
The lossless wrapper performs this admission before retained descriptor decoding.
The underlying exact service repeats admission before its own work.

Selected point routes use the shared bounded adaptive dispatcher.
Numerical uncertainty raises `LowRankUnresolved` without a partial model result.
Failure receipts retain the request allowance, completed stages, nested diagnostics, and observed elapsed time.
The lossless wrapper also retains performed decoding and receipt work.

Structural work units are engineering allowances, not measured operations or CPU time.
The workspace assessment does not certify whole-process resident memory.
These services do not impose a separate cumulative neural-work cap.
Empirical workers must retain independent process, time, and memory controls.

## Timing and storage accounting

The exact in-memory timer includes admission, context, preparation, point solving, and state construction.
The lossless timer additionally includes retained descriptor decoding and lossless state assembly.
Constructors, external parsing, input loading, and serialized output remain outside those timers.
Complete worker receipts must charge these external operations separately.

Lossless repair reuses surviving canonical descriptor payloads.
The in-request service does not decode deleted descriptors.
The existing canonical input parser can decode all supplied descriptors, including deleted records.
That parser cost remains part of complete transaction accounting.

Indexed preparation is a lifetime cost.
Request diagnostics neither repeat nor credit that external cost.
Original-corpus model-only preparation must accompany stateful preparation for a fair lifetime comparison.

The current adaptive compressed service expects historical preparation identities.
It cannot consume these ordered states without an explicit new integration.

## Verification

Command:

```bash
python -m unittest tests.test_ordered_services_v30 -v
```

Fifteen focused tests passed on 8 October 2026.
They cover two-block finite decoder fixtures and all three point routes.

The checks compare every factor byte and complete model digest against historical reference preparation.
They also check fresh, model-only, repair, indexed, empty deletion, and complete deletion behavior.
Further checks cover deletion histories, exact/lossless parsing, provenance rejection, malformed input, and disabled model candidates.
Resource checks ensure admission precedes preparation, traversal, and retained descriptor decoding.
Failure checks verify nested diagnostics without partial output.
Global attention and traversal functions remain unchanged.

These tests do not replace prospective full-model identity gates on real calibration records.
No empirical worker was executed while implementing these services.
