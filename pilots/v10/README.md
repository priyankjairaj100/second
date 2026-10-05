# Revision 10 pilot archive

Research resumed on 5 October 2026.
Read `../../docs/EMPIRICAL_PILOT_V10.md` before interpreting results.

The full-model resource plan rejected both primary model configurations.
The feature diagnostics use genuine DistilGPT2 weights and real text.
They evaluate first-block inputs without quantization.
They cannot establish model repair speed, quality, or lifetime.

`program.json` records every dataset and experiment decision.
`summary.json` contains verified diagnostic comparisons.
`*-worker` directories retain bounded worker receipts.
`phase-cpu-budget` preserves all four worker charges.
Feature directories contain complete binary64 outputs in little-endian order.
Each progress record specifies its token-major shape and content hash.
No checkpoint or downloaded source corpus is stored here.

The input acquisition recipe is:

```bash
python scripts/acquire_pilot_inputs.py
python scripts/prepare_wikitext_pilot.py --data tmp/data/wikitext2 --tokenizer tmp/models/distilgpt2/tokenizer.json --output pilots/v10/wikitext2
python scripts/prepare_reserve_pilots.py
```

`dependencies.json` records the observed package versions.
The network client requires `socksio` in this environment.
The acquisition script checks the frozen input hashes.
It downloads no executable model code.

The original execution order was:

```bash
python scripts/launch_pilot_v10.py wikitext2-scalar
python scripts/launch_pilot_v10.py wikitext2-accelerated
python scripts/launch_pilot_v10.py c4-accelerated
python scripts/launch_pilot_v10.py c4-scalar
python scripts/summarize_pilot_v10.py
```

These commands recover existing receipts when the original archive is present.
They do not create additional repetitions.
New measurements require new prospective plans and output locations.
New plans must share the remaining authorized CPU allowance.
Do not delete the existing ledger or restart its allowance.
All original plans bind absolute paths and source hashes.
Relocation requires explicit new path bindings.

The source-only resource checks used `inspect_local_config`.
They tested `none`, `stage-rtn`, `grid-box`, and `coordinate` chart modes.
Each plan used `TargetRecipe(original_token_count=32, group_count=1)`.
Default chart limits and the six-GiB budget remained unchanged.

Run the new software checks with:

```bash
python -m unittest tests.test_pilot_inputs_v10 -v
```

The NumPy kernel remains a diagnostic prototype.
The LAMBADA scorer also remains outside the production runner.
Production integration and full-model validation remain open.
