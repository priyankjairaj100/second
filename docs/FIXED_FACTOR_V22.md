# Minimal state for fixed-feature calibration

This change preserves the revision 21 numerical target.
It changes the persistent representation and its preparation method.
The legacy anchor backend remains the default.
Use `state_backend='factors'` to select the minimal backend.

## Stored information

The fixed-feature target requires exact retained feature matrices.
It does not require scalar summaries or affine perturbation summaries.
The minimal leaf therefore stores these fields:

- Record ID and ordered tokens.
- Every stage's exact token-major binary64 factor bytes.
- Complete factor dimensions and stage order.
- Original anchor target, decoder, provider, and nearest-anchor model bindings.
- A separate source binding for factor preparation.

The complete state adds the exact calibrated model and fixed-feature target digest.
It retains the logical family `fixed_anchor_calibration_v1`.
Its storage schema is `source_local_exact_factors_v1`.
Its distinct file magic selects the correct parser.

Factor arrays use immutable byte owners.
The format preserves signed-zero bytes.
The point quantizer still uses the same exact numerical target.

## Lightweight preparation

Fresh preparation uses the shared exact sequential decoder traversal.
It installs the fixed nearest-anchor matrix at every transition.
It records each stage input once.
It does not construct a scalar tape or affine summaries.

The anchor target and nearest-prefix bindings remain unchanged.
The preparer binding separately hashes the minimal codec and traversal source.
The service rejects a stale preparer binding.
This binding does not change the fixed-feature model target digest.

Trusted full anchor leaves can also be converted.
Conversion copies their exact factor bytes and validates complete stage membership.
It performs no model execution or quantization.
The conversion clock remains visible in the service diagnostics.
The service also retains the original external preparation receipt.
Conversion time is nested within prepared-leaf validation time.
Analysis must not add both clocks as independent costs.

## Exactness and deletion

The lightweight traversal follows the same finite feature schedule as anchor preparation.
It installs the same nearest-grid ancestor matrices.
Thus each retained factor equals the factor required by the fixed-feature target.
The complete point solver receives the same sorted factor matrices.
Its output model therefore stays unchanged.

Each minimal leaf depends only on its own record and fixed bindings.
Deleting records removes their complete leaves from the returned state.
Fresh construction and deletion retain identical leaves for every surviving record.
The model and canonical retained state therefore match.
This includes sequential deletion, combined deletion, no-op requests, and empty retention.

The trusted preparation premise remains necessary.
Hash checks do not authenticate a hostile replacement leaf.

## Comparators and costs

Both repair and indexed reconstruction use the same minimal state backend.
Both avoid transformer replay when their retained factors already exist.
The model-only control receives the same solver and finite traversal.
It creates no persistent leaves.

The minimal backend supplies no advantage over the matched indexed reconstruction control.
Its smaller state can reduce initial preparation, serialization, and storage costs.
Those costs require separate complete-transaction measurements.
Storage reduction alone does not prove a repair speedup.

## Parser and tests

The parser checks model, token, factor, and whole-file hashes.
It enforces bounded file size, header size, record count, token count, and factor values.
It rejects missing stages, duplicate records, wrong dimensions, and noncanonical ordering.
It also rejects nonfinite factors and inconsistent provenance.

Seven focused MPFR tests cover the minimal backend.
They compare full-anchor and lightweight factor bytes across two decoder blocks.
They compare native, reference, model-only, fresh, repair, and indexed outputs.
They check all deletion forms, parser limits, stale bindings, and signed-zero storage.

The archived state audit appears in `pilots/v22/factor-storage-audit.json`.
It converts existing bytes without running a model.
It checks every factor byte, every packed model code, and canonical roundtrip equality.
Its elapsed clock describes controller work only.
It is not a fresh, repair, or model-quality experiment.

Reproduce the audit with `python scripts/analyze_fixed_factor_v22.py`.
The script checks the trusted state hash, worker receipt, plan, and frozen source files.
It also checks the original model artifact and every retained factor byte.
Use `--save-state PATH` to save the converted binary separately.
The default command writes only the audit report.

The archived complete state occupies 54,107,392 bytes.
The minimal state occupies 26,326,066 bytes.
The reduction is 27,781,326 bytes, or about 51.3 percent.
All 24 factor blocks remain byte-identical.
All packed model codes also remain byte-identical.
