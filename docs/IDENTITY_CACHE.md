# Original quantized-model feature cache

Revision 7 implements the original-model identity baseline in `src/identity_cache.py`.
This baseline uses exact installed code equality for every relevant transitive ancestor.
This condition is sufficient for finite feature equality under the declared deterministic evaluator.
It can reject other cases where finite features happen to agree.

The baseline differs from revision 6's base-reference identity control.
It compares the previous quantized model with the repaired quantized prefix.
It never substitutes base weights for the previous model.

## Target and optional state interface

`IdentityCacheService(job, evaluator)` uses the existing `JobSpec` and exact quantization kernel.
It preserves grids, ridge, normalization, order, ties, record-local features, and the declared dependency graph.
It changes the optional stored state interface.
It does not claim byte equality with aggregate-response state.

For retained set R, write the complete sequential model as Q(R).
The cache stores each raw Gram under that model's relevant ancestors:

\[
G_\ell(R)=\sum_{j\in R}
X_{\ell j}(Q(R)_{\operatorname{anc}(\ell)})
X_{\ell j}(Q(R)_{\operatorname{anc}(\ell)})^\top.
\]

The cache contains the model, sorted record IDs and content hashes, and one raw Gram per stage.
Each Gram binds its exact ancestor prefix digest.
It contains no record payloads, per-record Grams, or historical cache entries.
The service manifest binds its source files and the complete job manifest.
The evaluator identity and dependency declaration remain trusted premises.

The returned state is a canonical function of the retained records under this fixed service.
Exact arithmetic makes summation order irrelevant.
Sorted membership fixes the remaining serialization order.

## Repair algorithm

First, validate the trusted cache digest, source bindings, dimensions, grids, and stored prefix bindings.
Then validate every supplied deleted payload against its committed content hash.
Process stages in their declared dependency order.

1. Form the stage's new ancestor prefix from already repaired outputs.
2. Compare every transitive ancestor against the cached model.
3. If ancestors agree, subtract the deleted records' exact contributions from the cached raw Gram.
4. Otherwise, evaluate retained records under the new prefix and construct their exact raw Gram.
5. Quantize the stage through the unchanged exact kernel.
6. Store the new raw Gram and its new prefix binding.

An empty retained set produces zero raw Grams without feature evaluation.
Its model still follows the fixed ridge, grids, and exact target kernel.
An empty request requires no feature evaluation or retained source access.
It still pays cache validation, factorization, rounding, and output costs.

The implementation uses one global Gram per stage.
It does not implement group-selective invariance or hidden-state checkpoint reuse.
Changed stages read retained records again.
The source provider may cache independently, but its full cost remains part of the execution contract.

## Exactness and repeated requests

Assume the incoming cache came from the declared service or an authenticated store.
Assume the feature evaluator is deterministic and depends only on declared ancestors and its own record.
Assume all required evaluations and exact arithmetic complete.

At a stage with matching ancestors, determinism gives identical old and new per-record features.
Exact subtraction therefore produces the retained target Gram.
At a changed stage, retained replay produces that same Gram directly.
The exact target kernel consequently emits the retained target stage output.
Topological induction establishes equality for the complete model and every stored Gram.

The refreshed cache equals direct construction on the retained set.
The next request therefore compares against the current quantized model.
It does not reuse stale original-model Grams after earlier changes.
Repeated, reordered, and combined deletions reach identical canonical bytes when their final retained sets agree.

These claims concern the declared exact-statistic target.
They do not imply equality with native Hugging Face execution or historical floating quantization.

## API and fair comparison

The core API is:

```python
service = IdentityCacheService(job, evaluator)
original = service.fresh(records)
repaired = service.repair(
    original.state, deleted_records, retained_source,
    expected_digest=trusted_original_digest,
)
indexed = service.indexed_fresh(
    original.state, deleted_records, retained_source,
    expected_digest=trusted_original_digest,
)
loaded = service.load_state(encoded_cache, expected_digest=trusted_original_digest)
```

`indexed_fresh` receives the same valid cache, old model, deleted payloads, and retained source.
It executes the identical repair solver.
This comparator prevents a false deletion-exclusive solver advantage.
Only access to a valid existing cache distinguishes both methods from uncached direct construction.

The runner adapter has the existing three-method service interface:

```python
adapter = IdentityCacheRunnerAdapter(service)
```

It supports `fresh`, `load_state`, `repair`, `prepare_index`, and `indexed_fresh`.
The modes `certified` and `identity_only` select the same original-model identity algorithm.
`full_replay` forces retained evaluation at each nonempty stage.
`fixed_reference` is unsupported and raises an error.

The adapter exposes `family="identity_cache"` and `service_family="identity_cache"`.
Its normalized `response_tier="linear"` and `verifier_policy="spectral"` fields satisfy shared runner metadata conventions.
Those defaults do not invoke linear response or a spectral decision certificate in this family.

The transient prepared index includes the original cache and deleted source payloads.
It is not the returned retained-only cache.
Discard it after use.
Its solver still needs the old model because that model defines its cached features.

| Operation | Work charged | Work deferred |
| --- | --- | --- |
| `fresh` | Source hashing, all sequential feature evaluations, Gram construction, target solves, cache serialization | External checkpoint load, durable output, runtime memory accounting |
| `prepare_index` | Trusted-origin digest lookup, cache serialization/hash, structural validation, source hashing, transient input packaging | All prefix-dependent extraction, subtraction, replay, and target solves |
| `repair` | Cache validation, deleted source binding, deleted extraction on identity stages, retained replay otherwise, every target solve, refreshed cache | Durable output and caller archive management |
| `indexed_fresh` | The same solver work as `repair`, plus prior preparation when reported end to end | Durable output and caller archive management |
| `load_state` | Bounded parsing, canonical encoding validation, trusted digest verification, cache validation | Feature recomputation; trusted origin makes it unnecessary |
| Runner commit | Canonical state/model serialization, artifact hashes, atomic writes, file and directory synchronization | Final run-result commit remains a distinct boundary |

Preparation validation and hashing add overhead to the split indexed interface.
That overhead cannot justify a scientific speed claim for repair.
The core solver ledgers match when both methods receive the same inputs and mode.

## Storage and cost accounting

The live Gram cache stores \(\sum_\ell d_\ell^2\) exact rational slots.
It also stores the full model, record metadata, and stage prefix hashes.
Rational numerator and denominator sizes can grow.
The ledger reports those integer bit totals separately from slot counts.
Canonical byte counts measure serialized content, not resident memory.

The implementation records setup feature calls, deleted feature calls, retained reads, replay calls, and target solves.
It records Gram arithmetic, validation calls, source bytes, state bytes, slot counts, and integer sizes.
It refreshes and serializes the complete optional state after every request.
Telemetry records exclusive extraction, Gram, factorization, validation, serialization, and source-access spans.
Instrumentation adds overhead.

The adapter separately records its extra input/output serialization and hashing.
Its trusted-origin registry stores digest capabilities within the process.
The registry keeps at most 16 digests by default, with a configurable minimum capacity of two.
Least-recently-used entries expire when this limit is reached.
An expired state requires trusted loading before reuse.
The registry size appears in its ledger.
It is outside returned canonical live state and must be included in runtime memory measurements.
The research runner already retains historical states outside the live-state deletion guarantee.

Input and output caches can coexist during a transaction.
Evaluator intermediates, rational temporaries, and serialized buffers also require memory.
Use enforced process limits and measured resident memory to assess feasibility.
Logical slot counts do not prove a total memory bound.

There is no universal speedup guarantee.
Changed ancestors can force almost every retained forward pass.
Validation, exact solves, refreshed state, and output can dominate even when feature reuse succeeds.
Any speed claim must include preparation amortization and equal-information indexed comparison.

## Authentication and failure boundaries

The core requires an externally trusted expected cache digest for every repair.
A changed cache fails before retained source access when checked against that digest.
A digest chosen by an attacker does not authenticate the cache.
Structural and PSD checks cannot prove that arbitrary stored statistics came from the corpus.

The runner adapter accepts origins established through fresh construction or trusted loading.
It rejects unregistered cache digests.
The source provider must return the requested ID with the committed content hash.
Invalid payloads, malformed caches, or necessary evaluator failures abort without replacing the input state.
Immutable input states remain unchanged.
Logical omission does not erase caller copies or archived artifacts.

## Correctness evidence

`tests/test_identity_cache_v7.py` covers unchanged ancestors without retained reads, changed ancestors, and transitive dependency changes.
It covers independent DAG branches, repeated and reordered deletion, full deletion, and empty requests.
It checks canonical reload, parser limits, forged caches, malformed prefixes, payload failures, and input immutability.
It checks equal-information indexed solving, forced replay, detailed costs, telemetry, and existing-runner integration.
It also compares model outputs against the independent aggregate service target.
These fixtures are software correctness checks.
They are not dataset experiments or speed measurements.
