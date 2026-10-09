"""Explicit V38 checkpoint import with frozen parsing and validation helpers.

This module downloads no files and executes no checkpoint code.
It requires a stable, trusted local directory during loading.
Its evaluator identity requires new preparation and a new registration.
"""
from __future__ import annotations
from contextlib import ExitStack
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from src import checkpoint_adapter as adapter
from src.checkpoint_adapter import (
    CheckpointError, LoadedCheckpoint, _integer, _child, _json, _config, _SafeFile, _digest,
)
from .portable_backend import PortableDeterministicDecoder


def load_portable_gpt2_checkpoint(directory: str | Path, *, max_parameter_elements: int = 200_000_000,
                         max_header_bytes: int = 16 * 1024 * 1024,
                         identity_encoding: str = "exact_json") -> LoadedCheckpoint:
    """Load config.json and local single-file or sharded safetensors weights.

    The returned decoder accepts unpadded token IDs and positions starting at
    zero. It disables dropout and uses no token types, cache, or custom masks.
    Checkpoint tensors retain immutable source bytes with exact values exposed
    on access. Downstream exact statistics can still require substantial memory.
    The element limit includes stored causal buffers. It is not a memory estimate.
    This function downloads nothing.
    """
    if identity_encoding not in ("exact_json", "binary64_tree_v2"):
        raise CheckpointError("unsupported parameter identity encoding")
    _integer(max_parameter_elements, "max_parameter_elements")
    _integer(max_header_bytes, "max_header_bytes")
    root = Path(directory).resolve()
    if not root.is_dir():
        raise CheckpointError("checkpoint directory does not exist")
    config_bytes = _child(root, "config.json").read_bytes()
    raw = _json(config_bytes)
    config, tied = _config(raw)
    single = (root / "model.safetensors").exists()
    sharded = (root / "model.safetensors.index.json").exists()
    if single == sharded:
        raise CheckpointError("provide exactly one single-file or sharded safetensors checkpoint")
    file_hashes = {"config.json": hashlib.sha256(config_bytes).hexdigest()}
    declared = None
    if sharded:
        index_bytes = _child(root, "model.safetensors.index.json").read_bytes()
        index = _json(index_bytes)
        if set(index) - {"metadata", "weight_map"}:
            raise CheckpointError("unsupported shard index fields")
        declared = index.get("weight_map")
        if not isinstance(declared, dict) or not declared or any(type(k) is not str or type(v) is not str for k, v in declared.items()):
            raise CheckpointError("invalid shard weight_map")
        filenames = sorted(set(declared.values()))
        if any(not filename.endswith(".safetensors") for filename in filenames):
            raise CheckpointError("all shard files must use .safetensors")
        file_hashes["model.safetensors.index.json"] = hashlib.sha256(index_bytes).hexdigest()
    else:
        filenames = ["model.safetensors"]
    with ExitStack() as stack:
        files = {name: _SafeFile(stack.enter_context(_child(root, name).open("rb")),
                                 max_header_bytes=max_header_bytes) for name in filenames}
        tensors = {}
        for filename, reader in files.items():
            file_hashes[filename] = reader.sha256
            for name in reader.tensors:
                if name in tensors:
                    raise CheckpointError(f"duplicate tensor across shards: {name}")
                if declared is not None and declared.get(name) != filename:
                    raise CheckpointError(f"tensor does not match shard index: {name}")
                tensors[name] = reader
        if declared is not None and set(tensors) != set(declared):
            raise CheckpointError("shard index has missing tensors")
        elements = sum(math.prod(reader.tensors[name].shape) for name, reader in tensors.items())
        if elements > max_parameter_elements:
            raise CheckpointError("checkpoint exceeds max_parameter_elements")
        prefix = "transformer." if "transformer.wte.weight" in tensors else ""
        expected: dict[str, tuple[int, ...]] = {}
        causal_buffers = {}
        d, f = config.model_width, config.feedforward_width
        expected[prefix + "wte.weight"] = (config.vocabulary_size, d)
        expected[prefix + "wpe.weight"] = (config.max_sequence_length, d)
        expected[prefix + "ln_f.weight"] = expected[prefix + "ln_f.bias"] = (d,)
        for i in range(config.block_count):
            pre = prefix + f"h.{i}."
            buffer_name = pre + "attn.bias"
            if buffer_name in tensors:
                expected[buffer_name] = (1, 1, config.max_sequence_length, config.max_sequence_length)
                causal_buffers[buffer_name] = tensors[buffer_name].validate_causal_mask(
                    buffer_name, config.max_sequence_length)
            for name in ("ln_1.weight", "ln_1.bias", "ln_2.weight", "ln_2.bias"):
                expected[pre + name] = (d,)
            for name, shape in (("attn.c_attn", (d, 3*d)), ("attn.c_proj", (d, d)),
                                ("mlp.c_fc", (d, f)), ("mlp.c_proj", (f, d))):
                expected[pre + name + ".weight"] = shape
                expected[pre + name + ".bias"] = (shape[1],)
        if "lm_head.weight" in tensors or not tied:
            expected["lm_head.weight"] = (config.vocabulary_size, d)
        if set(tensors) != set(expected):
            raise CheckpointError(f"tensor names differ: missing={sorted(set(expected)-set(tensors))}, unexpected={sorted(set(tensors)-set(expected))}")
        for name, shape in expected.items():
            if tensors[name].tensors[name].shape != shape:
                raise CheckpointError(f"wrong shape for {name}: expected {shape}")

        def tensor(name: str, transpose: bool = False) -> Any:
            values = tensors[name].compact_values(name)
            shape = expected[name]
            if len(shape) == 1:
                return values
            rows, cols = shape
            return values.matrix(rows, cols, transpose=transpose)

        embeddings = tensor(prefix + "wte.weight")
        head = tensor("lm_head.weight") if "lm_head.weight" in tensors else embeddings
        if tied:
            if head != embeddings:
                raise CheckpointError("tied lm_head.weight differs from token embeddings")
            head = embeddings
        blocks = []
        for i in range(config.block_count):
            pre = prefix + f"h.{i}."
            block = {}
            for dest, source in (("qkv", "attn.c_attn"), ("attn_out", "attn.c_proj"),
                                 ("mlp_up", "mlp.c_fc"), ("mlp_down", "mlp.c_proj")):
                block[dest] = tensor(pre + source + ".weight", True)
                block[dest + "_bias"] = tensor(pre + source + ".bias")
            for dest, source in (("norm1", "ln_1"), ("norm2", "ln_2")):
                block[dest + "_scale"] = tensor(pre + source + ".weight")
                block[dest + "_bias"] = tensor(pre + source + ".bias")
            blocks.append(block)
        decoder = PortableDeterministicDecoder(
            config, token_embeddings=embeddings, position_embeddings=tensor(prefix + "wpe.weight"),
            blocks=blocks, lm_head=head, final_norm_scale=tensor(prefix + "ln_f.weight"),
            final_norm_bias=tensor(prefix + "ln_f.bias"), identity_encoding=identity_encoding,
        )
        for filename, reader in files.items():
            if _digest(reader.handle) != reader.sha256:
                raise CheckpointError(f"checkpoint changed during loading: {filename}")
        provenance = {
            "schema": "local-gpt2-portable-safetensors-adapter-v38",
            "legacy_import_helpers_sha256": hashlib.sha256(Path(adapter.__file__).read_bytes()).hexdigest(),
            "historical_identity_compatibility": False, "files_sha256": file_hashes,
            "adapter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "source_dtype_counts": {dtype: sum(reader.tensors[name].dtype == dtype for name, reader in tensors.items())
                                    for dtype in sorted(_SafeFile.FORMATS)},
            "stored_parameter_elements": elements - len(causal_buffers) * config.max_sequence_length**2,
            "stored_tensor_elements": elements,
            "stored_causal_buffer_elements": len(causal_buffers) * config.max_sequence_length**2,
            "validated_causal_buffers": causal_buffers,
            "tied_word_embeddings": tied,
            "source_architectures": raw.get("architectures", ["GPT2LMHeadModel"]),
            "output_head_source": "stored lm_head.weight" if "lm_head.weight" in tensors else "declared tied token embeddings",
            "bare_gpt2_model_extension": raw.get("architectures") == ["GPT2Model"],
            "evaluator_id": decoder.evaluator_id,
            "contract": "architecture and parameter import; scalar binary64 decoder; not bitwise Hugging Face",
            "inputs": "unpadded token IDs; consecutive positions from zero; no token types, cache, or custom masks",
            "mode": "evaluation; dropout disabled",
        }
    if identity_encoding == "binary64_tree_v2":
        provenance["parameter_identity_encoding"] = identity_encoding
    return LoadedCheckpoint(decoder, json.dumps(provenance, sort_keys=True, separators=(",", ":")).encode())

