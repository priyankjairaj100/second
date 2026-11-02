# Next-checkpoint admission: planning checklist

Prepared 11 October 2026 from a read-only inspection of the current source.
This document is not a registration, resource admission, checkpoint selection,
numerical result, or authorization to run.

Expansion remains conditional on a useful V54 complete-model tradeoff surviving
the strong controls. Read `docs/RESEARCH_DECISION_V41.md` and
`docs/CLAIM_BOUNDARIES_V41.md`. Both final V54 audits remain required.
If the tradeoff fails, reconsider the representation or direction first.
Do not weaken or remove a control to obtain a favorable comparison.

## Identity and geometry

- Select and bind an immutable checkpoint revision, every weight/config file,
  tokenizer identity, and permitted access. No second supported checkpoint was
  found in this checkout, including ignored files. Only
  `tmp/models/distilgpt2/{config.json,model.safetensors}` was present.
- Check the actual config and tensor inventory against
  `src/checkpoint_adapter.py:_config` and `load_gpt2_checkpoint`. The importer
  supports a restricted GPT-2 family and single-file or sharded safetensors.
  Unsupported attention/config options or the existing stored-element limit
  may reject another checkpoint. Compatibility has not been established.
- Derive every stage ID, shape, code count, and packed extent from the new
  admitted target. Do not copy the DistilGPT2 constants: 24 stages,
  42,467,328 codes, or 21,233,664 packed model bytes.
- Bind calibration-source selection, tokenizer mapping, provenance,
  original normalization, grids, ridge, coordinate order, lower ties, and
  fixed nearest-grid anchor before numerical execution. Reusing the current
  adaptive C4 root does not make it independent confirmation.

## Additive implementation and state checks

- Implement a fresh version without editing frozen V53--V56 sources or
  their dependencies. `research_v53/service.py` binds DistilGPT2 hashes,
  thirteen sources, normalization 1664, 24 stages, and the width-768 Gram rule.
  `research_v54/campaign.py` and `worker.py` also bind checkpoint paths and
  the current data/program. `research_v53/resource_review.py` uses a historical
  DistilGPT2 target rather than a new checkpoint's geometry.
- Specify representation routing and state semantics explicitly.
  `research_v53/state.py:_mode` fixes hybrid Grams at widths at most 768;
  parser and serializer limits are not whole-process memory proofs.
  A changed schema or routing rule needs its own version and checks.
- Require complete model and canonical successor-state equality against fresh
  retained-input reconstruction after the declared successive deletions.
  Check code extent, target identity, retained membership/provenance, trust,
  descriptor containment, and actual bytes. Hash agreement alone does not
  establish independently constructed state.
- Preserve matched cached, cold, hybrid, and compressed controls. Give every
  compatible control the same numerical optimizations and declared access.
  Account for checkpoint, preparation, loading, replay, certificates, fallback,
  serialization, successor state, and disposal. Preserve failures and refusals.

## Quality and CPU/GPU boundaries

- Build a new quality wrapper around admitted complete models.
  `research_v55/sequential.py` iterates the declared target, but V55's campaign,
  worker, diagnostic, and audit bind the exact V54 program, DistilGPT2 geometry,
  retained inputs, and historical losses. Those losses cannot establish parity
  for a different checkpoint. Establish appropriate new control references.
- Preserve all 60 historical article exclusions. The existing eight diagnostic
  articles remain exposed. Define any untouched evaluation separately before
  access; do not recast development quality as confirmation. Preserve valid
  adverse outcomes independently of scheduler or audit success.
- Keep exact feature construction and calibration on the admitted CPU runtime.
  GPU likelihood transfer requires a new CPU parameter-word export and binding:
  `research_v56/campaign.py` requires the old V47 export hashes, and its worker
  requires 24 stages. `research_v47/snapshot.py` has geometry-driven archive
  machinery, but that does not admit a new export or prove evaluator parity.
  Register actual-model CPU/GPU parity separately from exact calibration.

## Admission still to resolve

- Review actual checkpoint/feature residency, temporary arrays, all-stage
  solver/fallback work, descriptor/state limits, serialization copies, and
  total storage before proposing CPU, wall, memory, or file ceilings.
- Run appropriate software and runtime checks on pinned Linux before a new
  numerical registration. Bind a clean source commit, literal commands,
  immutable inputs, fresh one-use paths, and separate charged budgets.
- Current resource ceilings and stage-count extrapolation do not establish
  completion or timing. Local storage is constrained; plan acquisition and
  archive placement before downloading checkpoint or parameter exports.

No new budget, ETA, launch command, or empirical registration is specified here.
