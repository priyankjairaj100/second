"""Local checkpoint format and mapping checks; no model or data downloads."""

import json
from pathlib import Path
import struct
import tempfile
import unittest

from src.checkpoint_adapter import CheckpointError, load_gpt2_checkpoint
from src.transformer_backend import DecoderConfig, DeterministicDecoder


def checkpoint_fixture(activation="gelu_new"):
    config = dict(model_type="gpt2", architectures=["GPT2LMHeadModel"], vocab_size=3,
                  n_embd=2, n_head=1, n_layer=1, n_positions=4, n_inner=3,
                  activation_function=activation, layer_norm_epsilon=1e-5)
    block = {
        "qkv": ((.375, .75), (-.25, 1), (.25, 1), (1, -.25), (1, -1), (.25, 1)),
        "qkv_bias": (.125, 0, -.125, 0, .25, 0),
        "attn_out": ((.25, .125), (-.125, .25)), "attn_out_bias": (.125, -.125),
        "mlp_up": ((1, .25), (-.25, 1), (.25, -.25)), "mlp_up_bias": (.125, 0, -.125),
        "mlp_down": ((.25, 0, .25), (0, .25, -.25)), "mlp_down_bias": (.125, -.125),
        "norm1_scale": (1, 1.125), "norm1_bias": (.125, -.125),
        "norm2_scale": (1.125, 1), "norm2_bias": (-.125, .125),
    }
    embeddings = ((1, 0), (0, 1), (1, -1))
    positions = ((0, 0), (.25, -.25), (-.25, .25), (.25, .25))
    weights = {"transformer.wte.weight": embeddings, "transformer.wpe.weight": positions,
               "transformer.ln_f.weight": (1, 1.125), "transformer.ln_f.bias": (.125, -.125)}
    for dest, source in (("qkv", "attn.c_attn"), ("attn_out", "attn.c_proj"),
                         ("mlp_up", "mlp.c_fc"), ("mlp_down", "mlp.c_proj")):
        weights["transformer.h.0." + source + ".weight"] = tuple(zip(*block[dest]))
        weights["transformer.h.0." + source + ".bias"] = block[dest + "_bias"]
    for dest, source in (("norm1", "ln_1"), ("norm2", "ln_2")):
        weights["transformer.h.0." + source + ".weight"] = block[dest + "_scale"]
        weights["transformer.h.0." + source + ".bias"] = block[dest + "_bias"]
    decoder = DeterministicDecoder(
        DecoderConfig(3, 2, 1, 3, 1, 4, activation=activation),
        token_embeddings=embeddings, position_embeddings=positions, blocks=[block], lm_head=embeddings,
        final_norm_scale=(1, 1.125), final_norm_bias=(.125, -.125),
    )
    return config, weights, decoder


def write_safe(path, weights, dtype="F32", mutate_header=None):
    header = {"__metadata__": {"format": "pt"}}
    data = bytearray()
    for name, tensor in sorted(weights.items()):
        if isinstance(tensor[0], (tuple, list)):
            shape = [len(tensor), len(tensor[0])]
            values = [x for row in tensor for x in row]
        else:
            shape = [len(tensor)]
            values = list(tensor)
        begin = len(data)
        for value in values:
            if dtype == "BF16":
                integer = struct.unpack("<I", struct.pack("<f", value))[0]
                data.extend(struct.pack("<H", integer >> 16))
            else:
                data.extend(struct.pack("<" + {"F16": "e", "F32": "f", "F64": "d"}[dtype], value))
        header[name] = {"dtype": dtype, "shape": shape, "data_offsets": [begin, len(data)]}
    if mutate_header:
        mutate_header(header)
    raw = json.dumps(header, separators=(",", ":")).encode()
    raw += b" " * (-len(raw) % 8)
    path.write_bytes(struct.pack("<Q", len(raw)) + raw + data)


def write_checkpoint(root, config, weights, **kwargs):
    (root / "config.json").write_text(json.dumps(config))
    write_safe(root / "model.safetensors", weights, **kwargs)


class CheckpointAdapterTests(unittest.TestCase):
    def test_all_supported_dtypes_map_architecture_and_values(self):
        config, weights, expected = checkpoint_fixture()
        for dtype in ("F16", "BF16", "F32", "F64"):
            with self.subTest(dtype=dtype), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                write_checkpoint(root, config, weights, dtype=dtype)
                loaded = load_gpt2_checkpoint(root)
                for stage in expected.stage_ids:
                    self.assertEqual(loaded.decoder.stage_weights(stage), expected.stage_weights(stage))
                    self.assertEqual(loaded.decoder.stage_features(stage, (0, 1, 2)),
                                     expected.stage_features(stage, (0, 1, 2)))
                self.assertEqual(loaded.decoder.logits((0, 1, 2)), expected.logits((0, 1, 2)))
                self.assertEqual(loaded.provenance["source_dtype_counts"][dtype], len(weights))

    def test_default_activation_is_gelu_new_and_not_erf(self):
        config, weights, tanh_decoder = checkpoint_fixture()
        _, _, erf_decoder = checkpoint_fixture("gelu")
        del config["activation_function"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_checkpoint(root, config, weights)
            loaded = load_gpt2_checkpoint(root)
            self.assertEqual(loaded.decoder.config.activation, "gelu_new")
            self.assertEqual(loaded.decoder.logits((0, 1)), tanh_decoder.logits((0, 1)))
            self.assertNotEqual(loaded.decoder.logits((0, 1)), erf_decoder.logits((0, 1)))

    def test_explicit_erf_activation(self):
        config, weights, expected = checkpoint_fixture("gelu")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_checkpoint(root, config, weights)
            loaded = load_gpt2_checkpoint(root)
            self.assertEqual(loaded.decoder.logits((0, 1)), expected.logits((0, 1)))
            self.assertFalse(loaded.provenance["bare_gpt2_model_extension"])

    def test_distilgpt2_label_metadata_preserves_language_model(self):
        # The official DistilGPT2 config uses this historical metadata key.
        config, weights, expected = checkpoint_fixture()
        config.update(_num_labels=1, id2label={"0": "LABEL_0"}, label2id={"LABEL_0": 0})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_checkpoint(root, config, weights)
            loaded = load_gpt2_checkpoint(root)
            self.assertEqual(loaded.decoder.logits((0, 1)), expected.logits((0, 1)))

    def test_sharded_checkpoint_matches_single_checkpoint(self):
        config, weights, expected = checkpoint_fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config.json").write_text(json.dumps(config))
            names = sorted(weights)
            halves = (names[:8], names[8:])
            weight_map = {}
            for i, names in enumerate(halves):
                name = f"model-{i}.safetensors"
                write_safe(root / name, {key: weights[key] for key in names})
                weight_map.update({key: name for key in names})
            (root / "model.safetensors.index.json").write_text(json.dumps({"weight_map": weight_map}))
            loaded = load_gpt2_checkpoint(root)
            self.assertEqual(loaded.decoder.logits((0, 1)), expected.logits((0, 1)))
            self.assertEqual(len(loaded.provenance["files_sha256"]), 4)
            weight_map[names[0]] = "../foreign.safetensors"
            (root / "model.safetensors.index.json").write_text(json.dumps({"weight_map": weight_map}))
            with self.assertRaises(CheckpointError):
                load_gpt2_checkpoint(root)

    def test_bare_gpt2_model_names_are_supported(self):
        config, weights, expected = checkpoint_fixture()
        config["architectures"] = ["GPT2Model"]
        weights = {key.removeprefix("transformer."): value for key, value in weights.items()}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_checkpoint(root, config, weights)
            loaded = load_gpt2_checkpoint(root)
            self.assertEqual(loaded.decoder.logits((0, 1)), expected.logits((0, 1)))
            self.assertTrue(loaded.provenance["bare_gpt2_model_extension"])

    def test_tied_head_must_match_and_untied_head_must_exist(self):
        config, weights, expected = checkpoint_fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            weights["lm_head.weight"] = weights["transformer.wte.weight"]
            write_checkpoint(root, config, weights)
            self.assertEqual(load_gpt2_checkpoint(root).decoder.logits((0, 1)), expected.logits((0, 1)))
            weights["lm_head.weight"] = ((0, 0), (0, 0), (0, 0))
            write_checkpoint(root, config, weights)
            with self.assertRaisesRegex(CheckpointError, "tied"):
                load_gpt2_checkpoint(root)
            config["tie_word_embeddings"] = False
            write_checkpoint(root, config, weights)
            self.assertEqual(load_gpt2_checkpoint(root).decoder.logits((0, 1)), ((0, 0, 0), (0, 0, 0)))
            del weights["lm_head.weight"]
            write_checkpoint(root, config, weights)
            with self.assertRaisesRegex(CheckpointError, "missing"):
                load_gpt2_checkpoint(root)

    def test_unsupported_config_features_fail_closed(self):
        config, weights, _ = checkpoint_fixture()
        cases = {"activation_function": "relu", "scale_attn_weights": False,
                 "scale_attn_by_inverse_layer_idx": True, "reorder_and_upcast_attn": True,
                 "add_cross_attention": True, "pruned_heads": {"0": [0]}, "new_architecture_flag": True,
                 "model_type": "gpt_neox", "n_head": True, "layer_norm_epsilon": 0}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for key, value in cases.items():
                with self.subTest(key=key):
                    bad = dict(config, **{key: value})
                    write_checkpoint(root, bad, weights)
                    with self.assertRaises(CheckpointError):
                        load_gpt2_checkpoint(root)

    def test_missing_unexpected_and_wrong_shape_tensors_fail_closed(self):
        config, weights, _ = checkpoint_fixture()
        bad_cases = []
        missing = dict(weights)
        del missing["transformer.ln_f.bias"]
        bad_cases.append(missing)
        bad_cases.append(dict(weights, unexpected=(0,)))
        shape = dict(weights)
        shape["transformer.h.0.attn.c_attn.weight"] = tuple(zip(*shape["transformer.h.0.attn.c_attn.weight"]))
        bad_cases.append(shape)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for bad in bad_cases:
                write_checkpoint(root, config, bad)
                with self.assertRaises(CheckpointError):
                    load_gpt2_checkpoint(root)

    def test_nonfinite_values_fail_closed(self):
        config, weights, _ = checkpoint_fixture()
        weights["transformer.ln_f.bias"] = (float("nan"), 0)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_checkpoint(root, config, weights)
            with self.assertRaisesRegex(CheckpointError, "nonfinite"):
                load_gpt2_checkpoint(root)

    def test_duplicate_json_keys_fail_closed(self):
        config, weights, _ = checkpoint_fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_checkpoint(root, config, weights)
            data = (root / "config.json").read_text()
            (root / "config.json").write_text('{"model_type":"gpt2",' + data[1:])
            with self.assertRaisesRegex(CheckpointError, "duplicate"):
                load_gpt2_checkpoint(root)
            write_checkpoint(root, config, weights)
            (root / "model.safetensors").write_bytes(struct.pack("<Q", 32) + b'{"a":{},"a":{}}' + b" " * 17)
            with self.assertRaises(CheckpointError):
                load_gpt2_checkpoint(root)

    def test_offsets_header_and_element_limits_fail_closed(self):
        config, weights, _ = checkpoint_fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_checkpoint(root, config, weights)
            with self.assertRaisesRegex(CheckpointError, "elements"):
                load_gpt2_checkpoint(root, max_parameter_elements=1)
            with self.assertRaisesRegex(CheckpointError, "header"):
                load_gpt2_checkpoint(root, max_header_bytes=2)
            def overlap(header):
                names = sorted(set(header) - {"__metadata__"})
                entry = header[names[1]]
                entry["data_offsets"] = [0, entry["data_offsets"][1] - entry["data_offsets"][0]]
            write_checkpoint(root, config, weights, mutate_header=overlap)
            with self.assertRaisesRegex(CheckpointError, "overlaps"):
                load_gpt2_checkpoint(root)

    def test_provenance_is_stable_and_returns_copies(self):
        config, weights, _ = checkpoint_fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_checkpoint(root, config, weights)
            loaded = load_gpt2_checkpoint(root)
            self.assertEqual(loaded.provenance_json, load_gpt2_checkpoint(root).provenance_json)
            altered = loaded.provenance
            altered["files_sha256"].clear()
            self.assertEqual(len(loaded.provenance["files_sha256"]), 2)
            self.assertIn("not bitwise Hugging Face", loaded.provenance["contract"])


if __name__ == "__main__":
    unittest.main()
