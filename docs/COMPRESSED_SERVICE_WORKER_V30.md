# Registered compressed service worker V30

`scripts/run_compressed_service_v30.py` is a feasibility worker for the existing
fixed nearest-anchor target. It is not an original sequential-calibration
worker. The initial policy fixes forty-bit factor descriptors and block size
256. Model codes remain four-bit codes.
Every plan explicitly selects `decoder_backend: "scalar"` or `"ordered"`.
The prospective primary comparison uses ordered preparation and ordered
fallback, matching the optimized ordered baseline.

No empirical worker was launched while implementing this interface. Small
deterministic decoder fixtures exercise the complete output path. These are
software checks, not a synthetic empirical dataset or speed evidence.

## Methods and input capabilities

Every input entry is exactly `{"path": absolute_path, "sha256": digest}`.
Files are size-bounded and rehashed. Symbolic links are rejected.

| Method | Required inputs | Result |
|---|---|---|
| `convert_lossless` | `records`, `lossless_state`, `lossless_model`, `lossless_completion` | Original complete compressed state and unchanged complete model |
| `repair` | `records`, `config`, `weights`, `prior_state`, `compressed_preparation_completion`, `reference_completion` | Retained complete compressed state and verified exact model |
| `indexed_fresh` | Same as repair | Equally indexed retained reconstruction |

Completion inputs must identify the original
`campaign/attempts/trial/outputs/completion.json`. The worker reads and verifies
the surrounding original program, protocol, registration, attempt plan,
transaction, execution receipt, all receipt artifacts, all declared output
artifacts, and frozen source directory. This evidence closure is part of the
declared access policy. No historical file is rewritten.

The terminal verifier checks settled CPU, receipt identity, plan identity,
three identical terminal copies, the stdout terminal digest, and output hashes
and sizes. Named artifact fields from historical workers are adapted only
after original receipt checks. New outputs contain both `artifacts` and the
matching `model_artifact`/`state_artifact` named fields.

Repair's numerical service receives only the compressed state, checkpoint,
retained tokens, target, and registered budgets. It does not receive original
exact factors or the retained reference model as proposals. Evidence
verification does read reference artifacts. Those reads remain measured work.
Prefer the completed `model_only_fresh` reference when available; this avoids
reading a comparator's optional state during reference verification.
Generating the reference is experiment validation work. The numerical repair
service does not require it. Its earlier generation clock is retained in
`retained_reference_evidence`, and current validation reads stay inside the
request clock. Neither cost should silently disappear from experiment totals.

## Trusted conversion and compatibility

Conversion requires a complete original V30 lossless `direct_fresh`
preparation of the selected decoder family. It verifies original membership,
normalization, source tokens,
record-file hash, all 24 stage identities, target recipe, point policy,
complete model bytes, and canonical state.

The state passes through `fixed_lossless_state_v29.to_factor_state` and
`fixed_compressed_state_v26.from_factor_state`. Every original descriptor is
decoded again for the audit. Its binary64 bytes must match the decoded exact
factor. The new descriptor must retain the original source digest and correct
dimensions. Its decoded interval must contain every exact source value.
All factors are checked, including factors for sources later deleted.

Scalar plans require `fixed_factor_state.preparer_binding()` and the historical
`adaptive-complete-service-transaction-v30` preparation schema. Ordered plans
require `ordered_fixed_service_v30.ordered_preparer_binding()` and the
`ordered-complete-service-transaction-v30` schema. Ordered plans additionally
bind the original decoder implementation manifest and its digest. Conversion
preserves the existing preparer identity; it never relabels prepared factors.

Repair dispatches scalar states to `AdaptiveCompressedService` and ordered
states to `OrderedCompressedService`, respectively. Ordered fallback uses the
same ordered decoder and feature traversal as the optimized lossless/cold
baseline. Each service rejects the other family's prepared states. A matched
retained reference from the chosen family is required even when historical
and ordered model-code bytes happen to match.

Conversion and repair must use the same frozen worker source map. The original
lossless preparation and retained reference may use their earlier frozen maps;
their original registrations and complete evidence closures are verified.
The current decoder/service subsequently verifies compatibility with the
prepared state and target.

## Required plan fields

The controller supplies normal `source_sha256`, `protocol_sha256`, `output`,
and exact command admission. The worker accepts only `phase: "feasibility"`.
Every plan also supplies:

- `method`, `inputs`, sorted unique `record_ids` and `deleted_ids`.
- `original_token_count`, which remains the original count after deletion.
- `use_candidates: false`, `codec_bits: 40`, `block_size: 256`, and explicit
  `decoder_backend: "scalar"` or `"ordered"`.
- `expected_target`, the complete fixed-target digest.
- `solver_backend`: `auto`, `token`, or `primal`.
- `solver_budget`: exactly `max_workspace_bytes`, `max_work_units`, and
  `max_refinement_coordinates`.
- `certificate_backend`: `auto`, `sparse`, or `primal`.
- `sparse_budget`: exactly `max_workspace_bytes`, `max_work_units`,
  `max_preconditioned_coordinates`, and `max_rounds`.
- `max_point_work_units`, `max_certificate_work_units`, and
  `max_neural_stage_record_pairs` as explicit request caps.
- `max_certificate_workspace_bytes`, a positive cap no larger than 1 GiB.
  Ordered requests may set it independently of the unchanged point workspace.
  Scalar requests must set it equal to the point workspace. Conversion and
  repair must bind the same certificate workspace cap.

Repair/indexed plans additionally supply `checkpoint`, containing the bound
`config.json` and `model.safetensors`. Optional `expected_model_sha256` and
`expected_state_sha256` add gates. The verified retained reference model is
always compared byte-for-byte, regardless of those optional fields.

Conversion includes every original record, deletes none, and requires a zero
neural cap. For the existing prepare-128 artifact, original normalization is
256 tokens: two records of 128 tokens each. A one-record retained request has
128 tokens. Its point policy must match original preparation, including the
96,000,000,000 cumulative point-work cap and original per-stage policy.

The target recipe is fixed to four-bit, one-group calibration with ridge
`[1,100]`, maximum grid entries 1,000,000, and the original normalization count.
Changing these parameters is a different registered target.

## Bounded numerical work and failure evidence

All stages undergo cumulative point-fallback admission before compressed state
parsing or service execution. This conservative preflight requires a feasible
complete fallback schedule even if certificates later avoid it.
The service additionally enforces cumulative point work, cumulative certificate
work, sparse refinement limits, and neural stage-record traversal limits.
For ordered certificates, the effective sparse workspace also respects
`sparse_budget.max_workspace_bytes`. The prospective 128-token pilot sets both
certificate limits to 1 GiB while preserving the matched point limit of
512 MiB. Its earlier 512 MiB certificate draft would have refused all twelve
MLP stages before attempting numerical certification. The revised shape
audit admits all 24 stages; it does not guarantee certificate acceptance.

No rational solver or unbounded numerical fallback is exposed by this worker.
Unresolved results or refused work produce failure progress and no completed
model receipt. Both `diagnostics` and `service_diagnostics`, plus any admission
receipt, are preserved on failures. Structural work limits are not guaranteed
wall-time or whole-process RSS bounds; the outer registered execution limits
still apply.

Full deletion is supported. The complete original normalization remains
unchanged, the successor source collection becomes empty, and its model must
match the corresponding retained reference.

## Cost boundary and lifetime accounting

The main latency is the outer complete transaction, including process startup,
all verification, checkpoint/state loading, certificate and fallback work,
serialization, output rereads, terminal commits, and exit. Worker and service
clocks are nested diagnostics and must not be added to that total.

The worker records original lossless preparation as
`external_lossless_preparation`, including its verified controller and worker
clocks. Conversion additionally records factor decoding, encoding, containment
audit, state parsing, and its own full transaction. Repair records conversion
as `external_compressed_conversion`. A lifetime comparison charges original
preparation **plus** conversion **plus** request transactions. Original
preparation is not free because it predates this campaign.

All historical evidence-closure reads and reference verification occur inside
the current transaction. Their overhead can affect comparisons with older
workers. Preserve the complete clock and disclose the different validation
work. A speed claim requires matched end-to-end boundaries or a clearly
conservative comparison; subtracting verification from one method would not
establish a fair speedup.

State storage is the complete serialized output artifact, including model,
descriptors, index, and framing. Base checkpoint parameters remain required
outside that artifact. Audit archives remain on disk and should be disclosed
separately from the deployed service state.

## Verification

Run software checks with:

```sh
python -m unittest tests.test_compressed_service_worker_v30 -v
```

The fixtures cover immutable codec/budget policy, exact input capabilities,
normalization and full deletion, preparation/reference drift, every-factor
containment, wrong model/preparer/source rejection, historical source and
receipt checks, conversion, repair, equally indexed reconstruction, matching
retained model bytes, matching canonical successor states, and admission
failure before service construction. Both scalar and ordered paths are
exercised. Ordered fixtures also force complete point fallback and neural-cap
refusal, preserving measured failure diagnostics without committing a model.

An independent service author reviewed the worker's API, containment boundary,
fallback caps, and complete timing scope without finding a blocker. A read-only
check also verified the existing prepare-128 closure, including all 142 frozen
sources. Its original completion digest is
`8068161b81adea38581035f691e09a3b026d62795f932be962fb082b1631eb12`.
No actual archive conversion or new model request was executed for these checks.
