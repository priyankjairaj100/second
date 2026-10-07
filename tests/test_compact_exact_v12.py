"""Storage and serialization checks use only small software fixtures."""

from dataclasses import FrozenInstanceError
from fractions import Fraction
import hashlib
import math
from pathlib import Path
import struct
import tempfile
import tracemalloc
import unittest

from src.checkpoint_adapter import load_gpt2_checkpoint
from src.compact_exact import CompactDyadicMatrix, CompactDyadicVector, exact_json_sha256, iter_exact_json
from src.transformer_backend import _json_bytes, _serial_exact
from tests.test_checkpoint_adapter import checkpoint_fixture, write_checkpoint


def packed(values, dtype):
    if dtype == "BF16":
        return b"".join(struct.pack("<H", struct.unpack("<I", struct.pack("<f", x))[0] >> 16) for x in values)
    return b"".join(struct.pack("<" + {"F16": "e", "F32": "f", "F64": "d"}[dtype], x) for x in values)


def parameters(decoder):
    return dict(token_embeddings=decoder._token_embeddings, position_embeddings=decoder._position_embeddings,
                blocks=decoder._blocks, lm_head=decoder._lm_head, lm_head_bias=decoder._lm_head_bias,
                final_norm_scale=decoder._final_norm_scale, final_norm_bias=decoder._final_norm_bias)


class CompactExactTests(unittest.TestCase):
    def test_dtype_values_transpose_slicing_and_negative_zero(self):
        values = (0.0, -0.0, 1.5, -2.25, 0.125, 65504.0)
        expected = tuple(Fraction.from_float(x) for x in values)
        for dtype in ("F16", "BF16", "F32", "F64"):
            with self.subTest(dtype=dtype):
                data = packed(values, dtype)
                compact = CompactDyadicVector.from_bytes(data, dtype)
                # BF16 rounds the last source value down in this fixture.
                decoded = expected if dtype != "BF16" else expected[:-1] + (Fraction(65280),)
                self.assertEqual(compact, decoded)
                self.assertEqual(decoded, compact)
                self.assertEqual(compact[::-2], decoded[::-2])
                self.assertEqual(tuple(compact[0:0]), ())
                self.assertEqual(compact[-1], decoded[-1])
                self.assertEqual(struct.pack("<d", compact.floats()[1]), struct.pack("<d", 0.0))
                matrix = compact.matrix(2, 3)
                transposed = compact.matrix(2, 3, transpose=True)
                self.assertEqual(matrix, (decoded[:3], decoded[3:]))
                self.assertEqual(transposed, tuple(zip(decoded[:3], decoded[3:])))
                self.assertEqual(transposed[::-1], tuple(reversed(tuple(transposed))))
                self.assertIs(matrix._storage.data, data)
                self.assertIs(transposed._storage, matrix._storage)
                self.assertEqual(matrix.storage_bytes, len(data))
                with self.assertRaises(IndexError):
                    _ = compact[len(compact)]
                with self.assertRaises(IndexError):
                    _ = matrix[-3]

    def test_binary64_extremes_are_exact(self):
        values = (float.fromhex("0x0.0000000000001p-1022"),
                  float.fromhex("-0x1.fffffffffffffp1023"),
                  float.fromhex("0x1.0000000000001p0"))
        compact = CompactDyadicVector.from_bytes(packed(values, "F64"), "F64")
        self.assertEqual(tuple(compact), tuple(Fraction.from_float(x) for x in values))
        self.assertEqual(tuple(compact.floats()), values)
        self.assertEqual(b"".join(iter_exact_json(compact)), _json_bytes(_serial_exact(tuple(compact))))

    def test_immutability_and_invalid_storage(self):
        compact = CompactDyadicVector.from_bytes(packed((1.0, 2.0), "F32"), "F32")
        with self.assertRaises(FrozenInstanceError):
            compact._offset = 1
        with self.assertRaises(FrozenInstanceError):
            compact._storage.data = b""
        with self.assertRaises(TypeError):
            compact[0] = Fraction(2)
        with self.assertRaises(TypeError):
            CompactDyadicVector.from_bytes(bytearray(b"\0" * 4), "F32")
        for dtype in ("F16", "BF16", "F32", "F64"):
            for value in (float("nan"), float("inf"), -float("inf")):
                with self.subTest(dtype=dtype, value=value), self.assertRaisesRegex(ValueError, "nonfinite"):
                    CompactDyadicVector.from_bytes(packed((value,), dtype), dtype)
        with self.assertRaises(ValueError):
            CompactDyadicVector.from_bytes(b"\0", "F32")
        with self.assertRaises(ValueError):
            compact.matrix(1, 3)
        with self.assertRaises(ValueError):
            CompactDyadicVector.from_bytes(b"", "I32")

    def test_streamed_json_matches_old_bytes_with_nested_values(self):
        compact = CompactDyadicVector.from_bytes(packed((-.125, 0., 1.5, 2.25), "F64"), "F64")
        payload = {"z": [compact.matrix(2, 2, transpose=True), Fraction(1, 3), True, None],
                   "unicode": "α\n雪", 2: "overwritten", "2": "retained", "a": -0.0}
        old_bytes = _json_bytes(_serial_exact(payload))
        self.assertEqual(b"".join(iter_exact_json(payload)), old_bytes)
        for buffer_bytes in (1, 2, 17, 65536):
            self.assertEqual(exact_json_sha256(payload, buffer_bytes=buffer_bytes), hashlib.sha256(old_bytes).hexdigest())
        with self.assertRaises(ValueError):
            exact_json_sha256(payload, buffer_bytes=0)
        with self.assertRaises(ValueError):
            exact_json_sha256(float("nan"))

    def test_no_tensor_sized_python_object_graph_during_hash(self):
        # This tests allocation behavior, not a research dataset or runtime gain.
        data = struct.pack("<f", 0.125) * 12000
        tracemalloc.start()
        try:
            compact = CompactDyadicVector.from_bytes(data, "F32")
            exact_json_sha256(compact)
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        self.assertLess(peak, 512 * 1024)
        self.assertIs(compact._storage.data, data)

    def test_decoder_retains_compact_storage_and_canonical_hash(self):
        config, weights, expected = checkpoint_fixture()
        old_digest = hashlib.sha256(_json_bytes(_serial_exact(parameters(expected)))).hexdigest()
        for dtype in ("F16", "BF16", "F32", "F64"):
            with self.subTest(dtype=dtype), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                weights["lm_head.weight"] = weights["transformer.wte.weight"]
                write_checkpoint(root, config, weights, dtype=dtype)
                loaded = load_gpt2_checkpoint(root).decoder
                self.assertIsInstance(loaded._token_embeddings, CompactDyadicMatrix)
                self.assertIs(loaded._lm_head, loaded._token_embeddings)
                self.assertEqual(loaded.kernel_manifest["parameters_sha256"], old_digest)
                self.assertEqual(loaded.evaluator_id, expected.evaluator_id)
                for stage in loaded.stage_ids:
                    self.assertIsInstance(loaded.stage_weights(stage), CompactDyadicMatrix)
                    self.assertIs(loaded._float_weights[stage].exact, loaded.stage_weights(stage))
                first, second = loaded.stage_ids[:2]
                prefix = {first: loaded.stage_weights(first)}
                self.assertTrue(loaded.prefix_preserves_stage_inputs(second, prefix))
                self.assertEqual(loaded.stage_features(second, (0, 1), prefix), expected.stage_features(second, (0, 1)))
                self.assertEqual(loaded.logits((0, 1)), expected.logits((0, 1)))

    def test_compact_and_tuple_targets_and_job_hashes_match(self):
        from src.certified_transformer import CertifiedDecoder
        from src.target_manifest import TargetRecipe, build_target
        from src.streamed_rationals import rational_json_sha256
        config, weights, expected = checkpoint_fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_checkpoint(root, config, weights)
            compact = load_gpt2_checkpoint(root).decoder
            for bits in (2, 4, 8):
                recipe = TargetRecipe(6, bits=bits)
                eager_target = build_target(CertifiedDecoder(expected), recipe)
                compact_target = build_target(CertifiedDecoder(compact), recipe)
                self.assertEqual(compact_target.payload(), eager_target.payload())
                self.assertEqual(compact_target.digest, eager_target.digest)
                compact_job = compact_target.make_job("unicode-α-reference")
                eager_job = eager_target.make_job("unicode-α-reference")
                self.assertEqual(compact_job.manifest_bytes, eager_job.manifest_bytes)
                self.assertEqual(compact_job.manifest_digest, hashlib.sha256(eager_job.manifest_bytes).hexdigest())
                self.assertEqual(compact_job.manifest_digest, eager_job.manifest_digest)
                for stage in compact_target.stages:
                    self.assertIs(stage.weights, compact.stage_weights(stage.stage_id))
                    pairs = [[[x.numerator, x.denominator] for x in row] for row in stage.weights]
                    self.assertEqual(rational_json_sha256(stage.weights), hashlib.sha256(_json_bytes(pairs)).hexdigest())

    def test_each_dtype_subnormal_float_array_is_exact(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest("NumPy is optional for compact exact storage")
        for dtype, tiny in (("F16", 2.0**-24), ("BF16", 2.0**-133),
                            ("F32", 2.0**-149), ("F64", 2.0**-1074)):
            vector = CompactDyadicVector.from_bytes(packed((tiny, -tiny), dtype), dtype)
            self.assertEqual(tuple(vector), (Fraction.from_float(tiny), -Fraction.from_float(tiny)))
            self.assertEqual(vector.float_array().tobytes(), np.array([tiny, -tiny], dtype=np.float64).tobytes())

    def test_finite_only_plan_requires_no_weight_files(self):
        import json
        from src.compact_preflight import inspect_compact_forward_config
        from src.resource_preflight import ResourcePlanError
        from src.target_manifest import TargetRecipe
        config, _, _ = checkpoint_fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config.json").write_text(json.dumps(config))
            result = inspect_compact_forward_config(root, TargetRecipe(6), max_record_tokens=3)
            result.require_allowed()
            self.assertEqual(result.planning_bytes, sum(dict(result.components_bytes).values()))
            self.assertFalse(result.payload()["authorizes_quantization_or_repair"])
            self.assertFalse(result.payload()["memory_bound_proved"])
            self.assertEqual(result.memory_budget_bytes, 6 * 2**30)
            self.assertEqual(result.source_parameter_elements_upper, 73)
            self.assertEqual(result.quantized_parameter_elements, 28)
            self.assertEqual(result.grid_entries, 144)
            denied = inspect_compact_forward_config(root, TargetRecipe(6), max_record_tokens=5, memory_budget_bytes=1)
            self.assertEqual(denied.rejected_limits, ("max_record_tokens", "planning_bytes"))
            with self.assertRaises(ResourcePlanError):
                denied.require_allowed()
            grids = inspect_compact_forward_config(root, TargetRecipe(6, max_grid_entries=1), max_record_tokens=1)
            self.assertIn("grid_entries", grids.rejected_limits)
            with self.assertRaises(ValueError):
                inspect_compact_forward_config(root, TargetRecipe(6), max_record_tokens=True)

    def test_optional_numpy_views_match_fraction_roundtrip(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest("NumPy is optional for compact exact storage")
        values = (0.0, -0.0, 1.5, -2.25, 0.125, 256.0)
        for dtype in ("F16", "BF16", "F32", "F64"):
            with self.subTest(dtype=dtype):
                vector = CompactDyadicVector.from_bytes(packed(values, dtype), dtype)
                for view in (vector, vector[::-2], vector[0:0], vector.matrix(2, 3),
                             vector.matrix(2, 3, transpose=True), vector.matrix(2, 3)[::-1],
                             vector.matrix(2, 3)[:0]):
                    array = view.float_array()
                    self.assertEqual(array.dtype, np.dtype("float64"))
                    self.assertFalse(array.flags.writeable)
                    expected = np.asarray([[float(x) for x in row] for row in view]
                                          if isinstance(view, CompactDyadicMatrix) else [float(x) for x in view])
                    if len(view):
                        self.assertEqual(array.tobytes(), expected.tobytes())
                    self.assertFalse(np.any((array == 0) & np.signbit(array)))


if __name__ == "__main__":
    unittest.main()
