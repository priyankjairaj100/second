"""Load local GPT-2 safetensors into the project's scalar finite decoder.

This adapter maps architecture and parameter values. It does not reproduce
Hugging Face's floating-point kernels. It downloads and executes no code.
The caller supplies a stable, trusted local directory during loading.
"""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import struct
from typing import Any, BinaryIO, Mapping

from .transformer_backend import DecoderConfig, DeterministicDecoder


class CheckpointError(ValueError):
    """The checkpoint violates the supported import contract."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out = {}
    for key, value in pairs:
        if key in out:
            raise CheckpointError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _json(data: bytes) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise CheckpointError(f"nonfinite JSON constant: {value}")
    try:
        value = json.loads(data, object_pairs_hook=_unique_object,
                           parse_constant=reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CheckpointError("invalid JSON") from exc
    if not isinstance(value, dict):
        raise CheckpointError("JSON root must be an object")
    return value


def _integer(value: Any, name: str, minimum: int = 1) -> int:
    if type(value) is not int or value < minimum:
        raise CheckpointError(f"{name} must be an integer >= {minimum}")
    return value


def _boolean(config: Mapping[str, Any], key: str, default: bool) -> bool:
    value = config.get(key, default)
    if type(value) is not bool:
        raise CheckpointError(f"{key} must be bool")
    return value


def _child(root: Path, filename: str) -> Path:
    # Deliberately exclude paths and symlinks that leave the given directory.
    if type(filename) is not str or Path(filename).name != filename or filename in ("", ".", ".."):
        raise CheckpointError("checkpoint files must use plain relative filenames")
    path = (root / filename).resolve()
    if path.parent != root:
        raise CheckpointError("checkpoint file escapes the supplied directory")
    if not path.is_file():
        raise CheckpointError(f"missing checkpoint file: {filename}")
    return path


def _digest(handle: BinaryIO) -> str:
    handle.seek(0)
    digest = hashlib.sha256()
    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class _Tensor:
    shape: tuple[int, ...]
    dtype: str
    begin: int
    end: int


class _SafeFile:
    """A strict reader for the four supported floating-point storage types."""

    FORMATS = {"F16": (2, "e"), "BF16": (2, "H"), "F32": (4, "f"), "F64": (8, "d")}

    def __init__(self, handle: BinaryIO, *, max_header_bytes: int) -> None:
        self.handle = handle
        handle.seek(0, 2)
        size = handle.tell()
        handle.seek(0)
        prefix = handle.read(8)
        if len(prefix) != 8:
            raise CheckpointError("truncated safetensors prefix")
        length = struct.unpack("<Q", prefix)[0]
        if not 2 <= length <= max_header_bytes or 8 + length > size:
            raise CheckpointError("invalid or excessive safetensors header length")
        header_bytes = handle.read(length)
        if not header_bytes.startswith(b"{"):
            raise CheckpointError("safetensors header must start with '{'")
        header = _json(header_bytes)
        self.data_offset = 8 + length
        self.tensors = {}
        spans = []
        for name, entry in header.items():
            if name == "__metadata__":
                if not isinstance(entry, dict) or any(type(k) is not str or type(v) is not str for k, v in entry.items()):
                    raise CheckpointError("safetensors metadata must map strings to strings")
                continue
            if type(name) is not str or not name or not isinstance(entry, dict):
                raise CheckpointError("invalid tensor entry")
            if set(entry) != {"dtype", "shape", "data_offsets"}:
                raise CheckpointError(f"unexpected tensor metadata: {name}")
            dtype = entry["dtype"]
            if type(dtype) is not str or dtype not in self.FORMATS:
                raise CheckpointError(f"unsupported storage dtype for {name}: {dtype}")
            shape = entry["shape"]
            offsets = entry["data_offsets"]
            if not isinstance(shape, list) or any(type(x) is not int or x < 0 for x in shape):
                raise CheckpointError(f"invalid tensor shape: {name}")
            if not isinstance(offsets, list) or len(offsets) != 2 or any(type(x) is not int or x < 0 for x in offsets):
                raise CheckpointError(f"invalid tensor offsets: {name}")
            begin, end = offsets
            if end < begin or end > size - self.data_offset:
                raise CheckpointError(f"tensor offsets exceed file: {name}")
            if end - begin != math.prod(shape) * self.FORMATS[dtype][0]:
                raise CheckpointError(f"tensor shape and byte length differ: {name}")
            self.tensors[name] = _Tensor(tuple(shape), dtype, begin, end)
            if end > begin:
                spans.append((begin, end))
        previous = 0
        for begin, end in sorted(spans):
            if begin != previous:
                raise CheckpointError("tensor data contains overlaps or gaps")
            previous = end
        if previous != size - self.data_offset:
            raise CheckpointError("unclaimed trailing tensor bytes")
        self.sha256 = _digest(handle)

    def values(self, name: str) -> tuple[float, ...]:
        tensor = self.tensors[name]
        self.handle.seek(self.data_offset + tensor.begin)
        data = self.handle.read(tensor.end - tensor.begin)
        if len(data) != tensor.end - tensor.begin:
            raise CheckpointError("checkpoint changed during loading")
        values = struct.iter_unpack("<" + self.FORMATS[tensor.dtype][1], data)
        if tensor.dtype == "BF16":
            result = tuple(struct.unpack("<f", struct.pack("<I", value[0] << 16))[0] for value in values)
        else:
            result = tuple(float(value[0]) for value in values)
        if any(not math.isfinite(value) for value in result):
            raise CheckpointError(f"nonfinite tensor value: {name}")
        return result


# GPT2Config fields without an architectural effect in this import contract.
# Unknown fields fail closed instead of silently changing model semantics.
_METADATA_FIELDS = {
    "_name_or_path", "_commit_hash", "transformers_version", "architectures",
    "torch_dtype", "dtype", "initializer_range", "n_ctx", "use_cache",
    "resid_pdrop", "embd_pdrop", "attn_pdrop", "bos_token_id", "eos_token_id", "pad_token_id",
    "return_dict", "output_hidden_states", "output_attentions", "torchscript",
    "use_bfloat16", "tf_legacy_loss", "tie_encoder_decoder", "chunk_size_feed_forward",
    "is_decoder", "is_encoder_decoder", "cross_attention_hidden_size",
    "finetuning_task", "id2label", "label2id", "num_labels", "_num_labels", "task_specific_params", "problem_type",
    "summary_type", "summary_use_proj", "summary_activation", "summary_proj_to_labels", "summary_first_dropout",
    "max_length", "min_length", "do_sample", "early_stopping", "num_beams", "num_beam_groups",
    "diversity_penalty", "temperature", "top_k", "top_p", "typical_p", "repetition_penalty",
    "length_penalty", "no_repeat_ngram_size", "encoder_no_repeat_ngram_size", "bad_words_ids",
    "num_return_sequences", "output_scores", "return_dict_in_generate", "forced_bos_token_id",
    "forced_eos_token_id", "remove_invalid_values", "exponential_decay_length_penalty",
    "suppress_tokens", "begin_suppress_tokens", "decoder_start_token_id", "sep_token_id",
    "tokenizer_class", "prefix", "_attn_implementation", "_attn_implementation_autoset",
}
_MODEL_FIELDS = {
    "model_type", "vocab_size", "n_positions", "n_embd", "n_layer", "n_head", "n_inner",
    "activation_function", "layer_norm_epsilon", "scale_attn_weights", "scale_attn_by_inverse_layer_idx",
    "reorder_and_upcast_attn", "add_cross_attention", "pruned_heads", "tie_word_embeddings",
}


def _config(raw: Mapping[str, Any]) -> tuple[DecoderConfig, bool]:
    unknown = set(raw) - _MODEL_FIELDS - _METADATA_FIELDS
    if unknown:
        raise CheckpointError(f"unsupported config fields: {sorted(unknown)}")
    if raw.get("model_type") != "gpt2":
        raise CheckpointError("only model_type='gpt2' is supported")
    architectures = raw.get("architectures", ["GPT2LMHeadModel"])
    if architectures not in (["GPT2LMHeadModel"], ["GPT2Model"]):
        raise CheckpointError("unsupported GPT-2 model architecture")
    if not _boolean(raw, "scale_attn_weights", True):
        raise CheckpointError("unscaled attention is unsupported")
    for key in ("scale_attn_by_inverse_layer_idx", "reorder_and_upcast_attn", "add_cross_attention",
                "is_encoder_decoder", "tie_encoder_decoder"):
        if _boolean(raw, key, False):
            raise CheckpointError(f"{key}=True is unsupported")
    if raw.get("pruned_heads", {}) != {}:
        raise CheckpointError("pruned heads are unsupported")
    if raw.get("cross_attention_hidden_size") is not None:
        raise CheckpointError("cross-attention width is unsupported")
    for key in ("resid_pdrop", "embd_pdrop", "attn_pdrop"):
        value = raw.get(key, 0.1)
        if type(value) not in (float, int) or not math.isfinite(value) or not 0 <= value <= 1:
            raise CheckpointError(f"invalid {key}")
    activation = raw.get("activation_function", "gelu_new")
    if activation not in ("gelu", "gelu_new"):
        raise CheckpointError("only gelu and gelu_new activations are supported")
    d = _integer(raw.get("n_embd"), "n_embd")
    epsilon = raw.get("layer_norm_epsilon", 1e-5)
    if type(epsilon) not in (float, int) or not math.isfinite(epsilon) or epsilon <= 0:
        raise CheckpointError("invalid layer_norm_epsilon")
    try:
        result = DecoderConfig(
            vocabulary_size=_integer(raw.get("vocab_size"), "vocab_size"), model_width=d,
            head_count=_integer(raw.get("n_head"), "n_head"),
            feedforward_width=_integer(raw.get("n_inner") if raw.get("n_inner") is not None else 4 * d, "n_inner"),
            block_count=_integer(raw.get("n_layer"), "n_layer"),
            max_sequence_length=_integer(raw.get("n_positions"), "n_positions"),
            layernorm_epsilon=float(epsilon), activation=activation,
        )
    except ValueError as exc:
        raise CheckpointError(str(exc)) from exc
    return result, _boolean(raw, "tie_word_embeddings", True)


@dataclass(frozen=True)
class LoadedCheckpoint:
    decoder: DeterministicDecoder
    provenance_json: bytes

    @property
    def provenance(self) -> dict[str, Any]:
        """Return a copy of the recorded source and numerical contract."""
        return _json(self.provenance_json)


def load_gpt2_checkpoint(directory: str | Path, *, max_parameter_elements: int = 200_000_000,
                         max_header_bytes: int = 16 * 1024 * 1024) -> LoadedCheckpoint:
    """Load config.json and local single-file or sharded safetensors weights.

    The returned decoder accepts unpadded token IDs and positions starting at
    zero. It disables dropout and uses no token types, cache, or custom masks.
    The exact scalar decoder stores Python objects eagerly. Its memory cost is
    much larger than the checkpoint size. The element limit is not a memory
    estimate. Checkpoints and tokenizers are never downloaded by this function.
    """
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
        d, f = config.model_width, config.feedforward_width
        expected[prefix + "wte.weight"] = (config.vocabulary_size, d)
        expected[prefix + "wpe.weight"] = (config.max_sequence_length, d)
        expected[prefix + "ln_f.weight"] = expected[prefix + "ln_f.bias"] = (d,)
        for i in range(config.block_count):
            pre = prefix + f"h.{i}."
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
            values = tensors[name].values(name)
            shape = expected[name]
            if len(shape) == 1:
                return values
            rows, cols = shape
            if transpose:
                return tuple(tuple(values[i*cols+j] for i in range(rows)) for j in range(cols))
            return tuple(values[i*cols:(i+1)*cols] for i in range(rows))

        embeddings = tensor(prefix + "wte.weight")
        head = tensor("lm_head.weight") if "lm_head.weight" in tensors else embeddings
        if tied and head != embeddings:
            raise CheckpointError("tied lm_head.weight differs from token embeddings")
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
        decoder = DeterministicDecoder(
            config, token_embeddings=embeddings, position_embeddings=tensor(prefix + "wpe.weight"),
            blocks=blocks, lm_head=head, final_norm_scale=tensor(prefix + "ln_f.weight"),
            final_norm_bias=tensor(prefix + "ln_f.bias"),
        )
        for filename, reader in files.items():
            if _digest(reader.handle) != reader.sha256:
                raise CheckpointError(f"checkpoint changed during loading: {filename}")
        provenance = {
            "schema": "local-gpt2-safetensors-adapter-v1", "files_sha256": file_hashes,
            "adapter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "source_dtype_counts": {dtype: sum(reader.tensors[name].dtype == dtype for name, reader in tensors.items())
                                    for dtype in sorted(_SafeFile.FORMATS)},
            "stored_parameter_elements": elements, "tied_word_embeddings": tied,
            "source_architectures": raw.get("architectures", ["GPT2LMHeadModel"]),
            "output_head_source": "stored lm_head.weight" if "lm_head.weight" in tensors else "declared tied token embeddings",
            "bare_gpt2_model_extension": raw.get("architectures") == ["GPT2Model"],
            "evaluator_id": decoder.evaluator_id,
            "contract": "architecture and parameter import; scalar binary64 decoder; not bitwise Hugging Face",
            "inputs": "unpadded token IDs; consecutive positions from zero; no token types, cache, or custom masks",
            "mode": "evaluation; dropout disabled",
        }
    return LoadedCheckpoint(decoder, json.dumps(provenance, sort_keys=True, separators=(",", ":")).encode())


__all__ = ["CheckpointError", "LoadedCheckpoint", "load_gpt2_checkpoint"]
