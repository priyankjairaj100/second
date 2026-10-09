# Explicit V38 decoder construction

This implementation creates a new evaluator identity.
It requires new preparation and a new experiment registration.
It does not resume the failed historical C4 attempt.

## Construction paths

`research_v38/portable_backend.py` supplies these classes:

- `PortableDeterministicDecoder` validates parameters and uses a new runtime manifest.
- `PortableOrderedDecoder` uses the frozen ordered arithmetic helpers.
- `PortableFinitePrefix` stores an immutable installed prefix.

`research_v38/portable_checkpoint.py` supplies `load_portable_gpt2_checkpoint`.
The loader retains the frozen checkpoint parsing helpers.
It rejects unsupported tensors, configurations, shapes, and parameter counts.
It constructs the new decoder directly.
It does not replace the historical constructor.

The historical constructors hardcode their manifest functions.
The V38 classes therefore copy their initialization logic into separate files.
The copied logic retains parameter validation, conversion, shapes, and parameter hashes.
The loader retains the original tensor mapping and checkpoint validation rules.
The V38 manifests bind both the new construction source and the reused source.

No production code replaces historical globals.
No production code creates false proc files.
No caller can supply a historical manifest as live evidence.

## Runtime contract

The collector obtains current hardware and library evidence.
Construction fails when required evidence is unavailable.
The supported collector requires one allowed CPU in the current affinity set.

The base decoder checks current evidence before and after each evaluation.
These checks cover inherited logits, exact logits, stage features, and generation.
The structural prefix check also validates the runtime.

The ordered decoder checks current evidence before and after each evaluation.
The generator checks every advancement.
The generator restores primitive scope before each yield.
The prepared prefix applies the same checks to logits.

Checks prevent a result from returning after a detected runtime change.
They do not detect a temporary change that starts and ends between checks.
The caller must preserve the runtime throughout each evaluation.
The collector assumes trusted, stable library files.
File hashes do not attest every mapped memory byte.

The legacy automatic jet service remains unsupported through the V38 convenience method.
That method raises an explicit error.
New workers must construct reviewed services directly.
External historical providers are outside this module's supported construction paths.

## Arithmetic claim

The ordered evaluator reuses the frozen V30 arithmetic functions.
The primitive evaluator reuses the frozen directed MPFR functions.
V38 changes construction and runtime evidence.
It does not change coordinate order, primitive rounding, activation formulas, or attention order.

The conditional target remains the declared finite computation.
Successful software fixtures compare every output bit against the frozen scalar arithmetic.
Such agreement does not establish historical evaluator identity equality.
It does not establish equal refusal behavior, completion domains, or resource costs.

The new identity binds a different runtime schema.
Historical targets and prepared states remain incompatible.
New comparisons require the same fresh preparation and current runtime.
Any runtime check cost belongs in the new complete request cost.

## Validation scope

`tests/test_portable_backend_v38.py` contains small software fixtures.
Successful construction uses live runtime evidence.
Failure fixtures inject errors only into the new collector interface.
They do not count as hardware observations.

The fixtures cover both activation formulas, multiple heads, multiple blocks, and changed prefixes.
They compare features, logits, and generator outputs against the frozen scalar arithmetic.
They cover runtime changes before evaluation and after evaluation.
They cover runtime changes between generator yields.
They cover prepared prefixes and inherited generation.
They verify new identities and unchanged historical globals.
They check checkpoint values and import refusals.

These fixtures are not empirical datasets.
They provide no model-scale speed or quality evidence.
A separate review must assess the collector and the execution controller.
A compatible host must compare old and new live observations.
Real-data comparisons require prospective registration after these gates pass.

## Recorded fixture results

The initial invocation passed thirteen cases.
The remaining case refused after the collector source changed during evaluation.
The post-evaluation check detected a different runtime identity.
The collector agent then held its source fixed.
The affected case passed in a targeted rerun.

All fourteen distinct cases have passing results.
No single invocation passed the entire suite.
The initial invocation took 65.566 seconds.
The targeted rerun took 41.033 seconds.
These times describe software validation, not empirical latency.
`validation/portable_backend_v38.json` preserves both outcomes.
