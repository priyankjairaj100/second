"""Explicit parameter identity checks on small software fixtures."""
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.checkpoint_adapter import CheckpointError, load_gpt2_checkpoint
from src.compact_exact import CompactDyadicVector
from src.parameter_identity import binary64_parameter_sha256, binary64_parameter_tree
from src.transformer_backend import DeterministicDecoder
from tests.test_checkpoint_adapter import checkpoint_fixture, write_checkpoint
from tests.test_compact_exact_v12 import packed, parameters


def clone(decoder, **overrides):
    config = overrides.pop("config", decoder.config)
    return DeterministicDecoder(config, **dict(parameters(decoder), **overrides))


class ParameterIdentityTests(unittest.TestCase):
    def test_fast_mode_is_explicit_and_preserves_all_outputs(self):
        config, weights, expected = checkpoint_fixture()
        fast_expected = clone(expected, identity_encoding="binary64_tree_v2")
        for dtype in ("F16", "BF16", "F32", "F64"):
            with self.subTest(dtype=dtype), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                write_checkpoint(root, config, weights, dtype=dtype)
                default = load_gpt2_checkpoint(root)
                with patch("src.transformer_backend.exact_json_sha256", side_effect=AssertionError("slow hash selected")):
                    fast = load_gpt2_checkpoint(root, identity_encoding="binary64_tree_v2")
                self.assertEqual(default.decoder.evaluator_id, expected.evaluator_id)
                self.assertEqual(fast.decoder.evaluator_id, fast_expected.evaluator_id)
                self.assertNotEqual(fast.decoder.evaluator_id, default.decoder.evaluator_id)
                self.assertEqual(fast.decoder.identity_encoding, "binary64_tree_v2")
                self.assertEqual(fast.provenance["parameter_identity_encoding"], "binary64_tree_v2")
                self.assertNotIn("parameter_identity_encoding", default.provenance)
                self.assertNotIn("parameters_identity_encoding", default.decoder.kernel_manifest)
                self.assertEqual(fast.decoder.kernel_manifest["parameters_identity_encoding"], "binary64_tree_v2")
                for stage in expected.stage_ids:
                    self.assertEqual(fast.decoder.stage_weights(stage), expected.stage_weights(stage))
                    self.assertEqual(fast.decoder.stage_features(stage, (0, 1)), expected.stage_features(stage, (0, 1)))
                self.assertEqual(fast.decoder.logits((0, 1)), expected.logits((0, 1)))

    def test_every_parameter_group_changes_identity(self):
        _, _, base = checkpoint_fixture()
        source = parameters(base)
        original = binary64_parameter_sha256(source)
        for key in source:
            changed = dict(source)
            if key == "blocks":
                blocks = [dict(block) for block in source[key]]
                for block_key, values in blocks[0].items():
                    block = dict(blocks[0])
                    if isinstance(values[0], tuple):
                        block[block_key] = ((values[0][0] + 1,) + values[0][1:],) + values[1:]
                    else:
                        block[block_key] = (values[0] + 1,) + values[1:]
                    changed[key] = (block,)
                    with self.subTest(key=key, block_key=block_key):
                        self.assertNotEqual(binary64_parameter_sha256(changed), original)
            elif isinstance(source[key][0], tuple):
                values = source[key]
                changed[key] = ((values[0][0] + 1,) + values[0][1:],) + values[1:]
                with self.subTest(key=key):
                    self.assertNotEqual(binary64_parameter_sha256(changed), original)
            else:
                changed[key] = (source[key][0] + 1,) + source[key][1:]
                with self.subTest(key=key):
                    self.assertNotEqual(binary64_parameter_sha256(changed), original)

    def test_tree_keys_shapes_and_structure_are_bound(self):
        values = (Fraction(1), Fraction(2), Fraction(3), Fraction(4))
        hashes = {binary64_parameter_sha256(value) for value in (
            {"a": values}, {"b": values}, {"a": (values,)},
            {"a": (values[:2], values[2:])}, {"a": values, "b": values},
            ({"a": values},), {"a": tuple(reversed(values))},
        )}
        self.assertEqual(len(hashes), 7)
        self.assertEqual(binary64_parameter_sha256({"a": values, "b": values}),
                         binary64_parameter_sha256({"b": values, "a": values}))
        with self.assertRaises(TypeError):
            binary64_parameter_sha256({1: values})

    def test_compact_typed_values_match_exact_tree_with_signed_zero(self):
        for dtype in ("F16", "BF16", "F32", "F64"):
            vector = CompactDyadicVector.from_bytes(packed((-0.0, 0.5, -1.0, 2.0), dtype), dtype)
            matrix = vector.matrix(2, 2, transpose=True)
            self.assertEqual(binary64_parameter_tree(vector), binary64_parameter_tree(tuple(vector)))
            self.assertEqual(binary64_parameter_tree(matrix), binary64_parameter_tree(tuple(tuple(row) for row in matrix)))
            self.assertEqual(binary64_parameter_tree(vector)["shape"], [4])
            self.assertEqual(binary64_parameter_tree(matrix)["shape"], [2, 2])

    def test_fast_mode_rejects_general_rationals_without_rounding(self):
        _, _, base = checkpoint_fixture()
        changed_bias = (Fraction(1, 3), Fraction(0), Fraction(0))
        slow = clone(base, lm_head_bias=changed_bias)
        self.assertEqual(slow._lm_head_bias, changed_bias)
        with self.assertRaisesRegex(ValueError, "exact parameter"):
            clone(base, lm_head_bias=changed_bias, identity_encoding="binary64_tree_v2")
        with self.assertRaises(ValueError):
            clone(base, identity_encoding="unsupported")
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(CheckpointError):
            load_gpt2_checkpoint(directory, identity_encoding="unsupported")

    def test_config_remains_bound_separately(self):
        _, _, base = checkpoint_fixture()
        first = clone(base, identity_encoding="binary64_tree_v2")
        second = clone(base, config=replace(base.config, activation="gelu"), identity_encoding="binary64_tree_v2")
        self.assertEqual(first.kernel_manifest["parameters_sha256"], second.kernel_manifest["parameters_sha256"])
        self.assertNotEqual(first.evaluator_id, second.evaluator_id)


if __name__ == "__main__":
    unittest.main()
