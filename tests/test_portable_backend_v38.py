"""Small software fixtures for V38 construction and finite arithmetic.

Successful construction uses live runtime evidence. Failure tests inject errors.
These fixtures are not empirical datasets or model-scale benchmarks.
"""
from fractions import Fraction as Q
import hashlib
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import src.transformer_backend as tb
import src.certified_transformer as ct
import src.finite_primitives as fp
import src.ordered_finite_decoder_v30 as ordered
from src.ordered_finite import FiniteWeights
from src.certified_transformer import _Finite, _StageWeights
from src.checkpoint_adapter import CheckpointError
from tests.test_checkpoint_adapter import write_checkpoint
from research_v38.portable_backend import (
    PortableDeterministicDecoder, PortableOrderedDecoder, PortableFinitePrefix,
    portable_primitive_manifest, portable_sequential_features,
)
from research_v38.portable_checkpoint import load_portable_gpt2_checkpoint


def fixture_arguments(activation="gelu_new", blocks=1, heads=1):
    block = {
        "qkv": ((.375, .75), (-.25, 1), (.25, 1), (1, -.25), (1, -1), (.25, 1)),
        "qkv_bias": (.125, 0, -.125, 0, .25, 0),
        "attn_out": ((.25, .125), (-.125, .25)), "attn_out_bias": (.125, -.125),
        "mlp_up": ((1, .25), (-.25, 1), (.25, -.25)), "mlp_up_bias": (.125, 0, -.125),
        "mlp_down": ((.25, 0, .25), (0, .25, -.25)), "mlp_down_bias": (.125, -.125),
        "norm1_scale": (1, 1.125), "norm1_bias": (.125, -.125),
        "norm2_scale": (1.125, 1), "norm2_bias": (-.125, .125),
    }
    return dict(
        config=tb.DecoderConfig(3, 2, heads, 3, blocks, 4, activation=activation),
        token_embeddings=((1, 0), (0, 1), (1, -1)),
        position_embeddings=((0, 0), (.25, -.25), (-.25, .25), (.25, .25)),
        blocks=[dict(block) for _ in range(blocks)],
        lm_head=((1, 0), (0, 1), (1, -1)),
        final_norm_scale=(1, 1.125), final_norm_bias=(.125, -.125),
    )


def fixture(**kwargs):
    return PortableOrderedDecoder(PortableDeterministicDecoder(**fixture_arguments(**kwargs)))


def binary(values):
    return tuple(tuple(struct.pack(">d", float(value)) for value in row) for row in values)


def scalar_reference(decoder, tokens, prefix=None, stop=None):
    """Run unchanged scalar arithmetic without any legacy manifest constructor."""
    base = decoder.base
    installed = base._prefix(prefix)
    weights = _StageWeights(base.stage_ids, lambda stage: FiniteWeights(
        installed.get(stage, base._float_weights[stage])))
    with fp.primitive_scope(decoder.primitive_backend):
        return ct._execute(base, base._tokens(tokens), weights, lambda x: _Finite(float(x)), stop)


def checkpoint_arguments():
    args = fixture_arguments()
    config = dict(model_type="gpt2", architectures=["GPT2LMHeadModel"], vocab_size=3,
                  n_embd=2, n_head=1, n_layer=1, n_positions=4, n_inner=3,
                  activation_function="gelu_new", layer_norm_epsilon=1e-5)
    weights = {
        "transformer.wte.weight": args["token_embeddings"],
        "transformer.wpe.weight": args["position_embeddings"],
        "transformer.ln_f.weight": args["final_norm_scale"],
        "transformer.ln_f.bias": args["final_norm_bias"],
    }
    block = args["blocks"][0]
    for dest, source in (("qkv", "attn.c_attn"), ("attn_out", "attn.c_proj"),
                         ("mlp_up", "mlp.c_fc"), ("mlp_down", "mlp.c_proj")):
        weights["transformer.h.0." + source + ".weight"] = tuple(zip(*block[dest]))
        weights["transformer.h.0." + source + ".bias"] = block[dest + "_bias"]
    for dest, source in (("norm1", "ln_1"), ("norm2", "ln_2")):
        weights["transformer.h.0." + source + ".weight"] = block[dest + "_scale"]
        weights["transformer.h.0." + source + ".bias"] = block[dest + "_bias"]
    return config, weights


class PortableBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_affinity = os.sched_getaffinity(0)
        os.sched_setaffinity(0, {min(cls.original_affinity)})

    @classmethod
    def tearDownClass(cls):
        os.sched_setaffinity(0, cls.original_affinity)

    def test_live_manifest_and_evaluator_are_new_and_immutable(self):
        decoder = fixture()
        self.assertTrue(decoder.evaluator_id.startswith("portable-certified-decoder-v38:"))
        self.assertTrue(decoder.base.evaluator_id.startswith("portable-decoder-v38:"))
        self.assertFalse(decoder.kernel_manifest["historical_identity_compatibility"])
        self.assertFalse(decoder.implementation_manifest["global_mutation"])
        changed = decoder.kernel_manifest
        changed["base_parameters"].clear()
        self.assertTrue(decoder.kernel_manifest["base_parameters"])
        with self.assertRaises(AttributeError):
            decoder.base = decoder.base
        self.assertEqual(decoder.evaluator_id, fixture().evaluator_id)

    def test_all_features_and_logits_match_scalar_operations(self):
        for activation in ("gelu", "gelu_new"):
            decoder = fixture(activation=activation, blocks=2, heads=2)
            first = decoder.stage_ids[0]
            changed = {first: tuple(tuple(value / 2 for value in row)
                                    for row in decoder.stage_weights(first))}
            for prefix in (None, changed):
                for stage in decoder.stage_ids:
                    reference = scalar_reference(decoder, (0, 1, 2), prefix, stage)
                    expected = tuple(tuple(Q.from_float(row[k].value) for row in reference)
                                     for k in range(len(reference[0])))
                    self.assertEqual(expected, decoder.stage_features(stage, (0, 1, 2), prefix))
                expected = [[v.value for v in row] for row in scalar_reference(decoder, (0, 1, 2), prefix)]
                self.assertEqual(binary(expected), binary(decoder.logits((0, 1, 2), prefix)))

    def test_each_generator_step_matches_independent_scalar_restart(self):
        decoder = fixture(blocks=2, heads=2)
        stream = decoder.sequential_features((0, 1, 2))
        prefix = {}
        current = next(stream)
        for index, stage in enumerate(decoder.stage_ids):
            expected = scalar_reference(decoder, (0, 1, 2), prefix, stage)
            self.assertEqual(current[0], stage)
            self.assertEqual(binary(current[1]), binary([[v.value for v in row] for row in expected]))
            weights = tuple(tuple(value / (index + 2) for value in row) for row in decoder.stage_weights(stage))
            prefix[stage] = weights
            if index + 1 < len(decoder.stage_ids):
                current = stream.send(weights)
            else:
                with self.assertRaises(StopIteration):
                    stream.send(weights)

    def test_generator_refuses_changed_runtime_after_suspension(self):
        decoder = fixture()
        with fp.primitive_scope("rational"):
            stream = decoder.sequential_features((0, 1))
            stage, _ = next(stream)
            self.assertEqual(fp._BACKEND.get(), "rational")
            with patch("research_v38.portable_backend.assert_runtime_unchanged",
                       side_effect=RuntimeError("changed runtime")):
                with self.assertRaisesRegex(RuntimeError, "changed runtime"):
                    stream.send(decoder.stage_weights(stage))
            self.assertEqual(fp._BACKEND.get(), "rational")

    def test_prepared_prefix_copies_weights_and_checks_runtime(self):
        decoder = fixture()
        first = decoder.stage_ids[0]
        prefix = {first: decoder.stage_weights(first)}
        prepared = decoder.prepare_prefix(prefix)
        prefix.clear()
        self.assertEqual(binary(prepared.logits((0, 1))), binary(decoder.logits((0, 1))))
        with self.assertRaises(TypeError):
            prepared.installed[first] = ()
        with patch("research_v38.portable_backend.assert_runtime_unchanged",
                   side_effect=RuntimeError("changed runtime")):
            with self.assertRaisesRegex(RuntimeError, "changed runtime"):
                prepared.logits((0, 1))

    def test_runtime_change_after_evaluation_prevents_return(self):
        decoder = fixture()
        with patch("research_v38.portable_backend.assert_runtime_unchanged",
                   side_effect=[None, None, RuntimeError("changed during evaluation")]):
            with self.assertRaisesRegex(RuntimeError, "changed during evaluation"):
                decoder.logits((0, 1))

    def test_base_inherited_public_evaluation_paths_check_runtime(self):
        base = fixture().base
        calls = (
            lambda: base.logits((0,)),
            lambda: base.exact_logits((0,)),
            lambda: base.stage_features(base.stage_ids[0], (0,)),
            lambda: base.greedy_generate((0,), 1),
            lambda: base.prefix_preserves_stage_inputs(base.stage_ids[0], None),
        )
        with patch("research_v38.portable_backend.assert_runtime_unchanged",
                   side_effect=RuntimeError("changed runtime")):
            for call in calls:
                with self.assertRaisesRegex(RuntimeError, "changed runtime"):
                    call()

    def test_construction_refuses_missing_runtime_evidence(self):
        with patch("research_v38.portable_backend.collect_runtime",
                   side_effect=RuntimeError("live evidence unavailable")):
            with self.assertRaisesRegex(RuntimeError, "live evidence unavailable"):
                PortableDeterministicDecoder(**fixture_arguments())
            with self.assertRaisesRegex(RuntimeError, "live evidence unavailable"):
                portable_primitive_manifest("mpfr_enclosure")

    def test_construction_does_not_change_legacy_globals(self):
        before = (tb.DeterministicDecoder, tb._runtime_manifest, ct.CertifiedDecoder,
                  fp.primitive_manifest, ordered.OrderedFiniteDecoder, ordered._execute_ordered)
        fixture().logits((0, 1))
        after = (tb.DeterministicDecoder, tb._runtime_manifest, ct.CertifiedDecoder,
                 fp.primitive_manifest, ordered.OrderedFiniteDecoder, ordered._execute_ordered)
        self.assertEqual(before, after)

    def test_implementation_binds_reused_sources(self):
        manifest = fixture().implementation_manifest
        for name, digest in manifest["reused_source_sha256"].items():
            self.assertEqual(hashlib.sha256(Path(tb.__file__).with_name(name).read_bytes()).hexdigest(), digest)

    def test_new_checkpoint_loader_preserves_values_and_has_new_provenance(self):
        config, weights = checkpoint_arguments()
        expected = fixture()
        for dtype in ("F16", "BF16", "F32", "F64"):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                write_checkpoint(root, config, weights, dtype=dtype)
                loaded = load_portable_gpt2_checkpoint(root)
                decoder = PortableOrderedDecoder(loaded.decoder)
                for stage in decoder.stage_ids:
                    self.assertEqual(expected.stage_weights(stage), decoder.stage_weights(stage))
                self.assertEqual(binary(expected.logits((0, 1))), binary(decoder.logits((0, 1))))
                self.assertEqual(loaded.provenance["schema"], "local-gpt2-portable-safetensors-adapter-v38")
                self.assertFalse(loaded.provenance["historical_identity_compatibility"])

    def test_checkpoint_import_rejects_unknown_config_and_tensor_names(self):
        config, weights = checkpoint_arguments()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_checkpoint(root, dict(config, new_architecture=True), weights)
            with self.assertRaises(CheckpointError):
                load_portable_gpt2_checkpoint(root)
            write_checkpoint(root, config, dict(weights, unexpected=(0,)))
            with self.assertRaises(CheckpointError):
                load_portable_gpt2_checkpoint(root)
            write_checkpoint(root, config, weights)
            with self.assertRaises(CheckpointError):
                load_portable_gpt2_checkpoint(root, max_parameter_elements=1)

    def test_binary_parameter_identity_is_explicit_and_stable(self):
        args = fixture_arguments()
        first = PortableDeterministicDecoder(**args, identity_encoding="binary64_tree_v2")
        second = PortableDeterministicDecoder(**args, identity_encoding="binary64_tree_v2")
        self.assertEqual(first.evaluator_id, second.evaluator_id)
        self.assertEqual(first.kernel_manifest["parameters_identity_encoding"], "binary64_tree_v2")
        self.assertNotEqual(first.evaluator_id, PortableDeterministicDecoder(**args).evaluator_id)
        config, weights = checkpoint_arguments()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_checkpoint(root, config, weights)
            loaded = load_portable_gpt2_checkpoint(root, identity_encoding="binary64_tree_v2")
            self.assertEqual(loaded.decoder.evaluator_id, first.evaluator_id)
            self.assertEqual(loaded.provenance["parameter_identity_encoding"], "binary64_tree_v2")

    def test_foreign_types_and_unsupported_primitive_fail(self):
        with self.assertRaises(TypeError):
            PortableOrderedDecoder(object())
        with self.assertRaises(TypeError):
            PortableFinitePrefix(object())
        with self.assertRaises(TypeError):
            next(portable_sequential_features(object(), (0,)))
        with self.assertRaises(ValueError):
            portable_primitive_manifest("unknown")
        decoder = fixture()
        with self.assertRaises(ValueError):
            decoder.prepare_prefix({"unknown": ()})
        with self.assertRaisesRegex(NotImplementedError, "explicit service construction"):
            decoder.make_repair_service()


if __name__ == "__main__":
    unittest.main()
