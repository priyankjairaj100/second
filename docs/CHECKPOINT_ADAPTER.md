# Local GPT-2 checkpoint adapter

`src/checkpoint_adapter.py` imports local GPT-2 weights into the deterministic decoder.
It supports the standard GPT-2 architecture and its default `gelu_new` activation.
It also supports the `gelu` activation.

This adapter defines a new finite execution target.
It does not reproduce Hugging Face kernels or their floating-point outputs.
The existing target V still treats the resulting finite features as exact dyadic values.

## Supported files and mapping

The loader requires `config.json` and one weight layout:

- A single `model.safetensors` file.
- A `model.safetensors.index.json` file with local safetensors shards.

The loader uses only Python's standard library.
It accepts F16, BF16, F32, and F64 tensor storage.
Conversion to binary64 preserves each finite stored value.
The decoder then applies its declared rational and finite conversion rules.

| Checkpoint component | Decoder component | Mapping |
| --- | --- | --- |
| `wte.weight` | Token embeddings | Keep row order |
| `wpe.weight` | Position embeddings | Keep row order |
| `attn.c_attn.weight` | Fused QKV matrix | Transpose input-by-output storage |
| `attn.c_proj.weight` | Attention output matrix | Transpose input-by-output storage |
| `mlp.c_fc.weight` | MLP up matrix | Transpose input-by-output storage |
| `mlp.c_proj.weight` | MLP down matrix | Transpose input-by-output storage |
| `ln_1`, `ln_2`, `ln_f` | LayerNorm parameters | Copy scales, biases, and epsilon |
| Projection biases | Projection biases | Keep coordinate order |
| `lm_head.weight` | Fixed output head | Copy, or use declared tied embeddings |

Names can include the standard `transformer.` prefix.
The adapter validates every tensor name and shape before decoding parameter values.
It rejects conflicting tied embeddings.
An untied head must have its own tensor.
An import marked `GPT2Model` receives the declared output head for this project's language-model interface.
This head extends the original bare decoder.
The provenance records this extension explicitly.

## Input and architecture contract

The decoder accepts one unpadded token sequence per record.
Positions start at zero and increase by one.
Attention uses the causal mask and square-root head scaling.
The decoder disables dropout.
It does not accept token types, custom masks, cached keys, or cached values.
Tokenization remains outside the adapter.
The experiment manifest must record the tokenizer and tokenized input policy separately.

The adapter rejects cross-attention, pruned heads, inverse-layer attention scaling, and reordered attention.
It rejects unsupported activations and unknown configuration fields.
It rejects unknown tensors, including legacy attention buffers.
It supports ordinary evaluation metadata without interpreting generation settings.
It does not execute remote code or load pickle files.

## Usage

```python
from src.checkpoint_adapter import load_gpt2_checkpoint

loaded = load_gpt2_checkpoint("/absolute/path/to/local/gpt2")
decoder = loaded.decoder
provenance = loaded.provenance

# These token IDs must come from the declared tokenizer.
features = decoder.stage_features(decoder.stage_ids[0], (42, 17))
logits = decoder.logits((42, 17))
```

The returned decoder supports the same repair interface as a directly constructed decoder.
A separate certified wrapper can define another numerical target explicitly.
The adapter does not silently replace either numerical target.

## Provenance and resource costs

The provenance records hashes for the configuration, weight files, adapter, and decoder contract.
It records stored tensor types and the parameter count.
The decoder contract includes the architecture, parameters, source, and runtime identity.
The loader checks each weight file again after construction.
The caller must keep the supplied directory stable during loading.
These checks do not authenticate hostile storage.

The loader reads each weight file twice for hashes.
It also reads the tensor data for conversion.
These reads belong in setup costs.

The decoder stores Python tuples, exact rational values, and finite values eagerly.
Its memory cost can greatly exceed the checkpoint size.
The default limit permits 200 million stored elements.
This limit prevents larger imports by default.
It does not guarantee that a permitted import fits available memory.
This reference implementation is not an efficient GPU loader.

## Validation completed

Twelve software tests passed during this revision.
They cover all four storage types, both activations, shards, tied heads, mapping, provenance, and invalid inputs.
The mapping tests compare all stage features and final logits against a separately assembled decoder.
These tests use explicit small arrays for software verification.
They are not a dataset study or a pretrained-model experiment.

No pretrained checkpoint was downloaded or evaluated during this revision.
No comparison with Hugging Face outputs was run.
Such a comparison would assess architecture mapping, not establish bitwise equality between different numerical targets.

## Primary source inspection

The implementation follows these official sources, inspected on 4 October 2026:

- [GPT-2 implementation, Transformers v4.57.1](https://github.com/huggingface/transformers/blob/v4.57.1/src/transformers/models/gpt2/modeling_gpt2.py).
- [GPT-2 configuration, Transformers v4.57.1](https://github.com/huggingface/transformers/blob/v4.57.1/src/transformers/models/gpt2/configuration_gpt2.py).
- [Conv1D implementation, Transformers v4.57.1](https://github.com/huggingface/transformers/blob/v4.57.1/src/transformers/pytorch_utils.py).
- [Activation definitions](https://github.com/huggingface/transformers/blob/main/src/transformers/activations.py).
- [Safetensors file format](https://github.com/safetensors/safetensors#format).

The inspected GPT-2 implementation uses sequential pre-LayerNorm residual blocks and fused QKV projections.
Its default configuration selects `gelu_new`.
The finite scalar schedule remains the project's own declared contract.
