"""Software contract checks, not a synthetic empirical dataset or benchmark."""

from fractions import Fraction
import math
import unittest

from src.transformer_backend import DecoderConfig, DeterministicDecoder, FiniteTargetError


def decoder_fixture(block_count=1, head_count=1):
    """Small explicit arrays exercise the executable architecture contract."""
    quarter = Fraction(1, 4)
    blocks = [{
        "qkv": ((Fraction(3, 8), Fraction(3, 4)), (-quarter, 1), (quarter, 1), (1, -quarter),
                (1, -1), (quarter, 1)),
        "attn_out": ((quarter, 0), (0, quarter)),
        "mlp_up": ((1, quarter), (-quarter, 1), (quarter, -quarter)),
        "mlp_down": ((quarter, 0, quarter), (0, quarter, -quarter)),
    } for _ in range(block_count)]
    return DeterministicDecoder(
        DecoderConfig(3, 2, head_count, 3, block_count, 5),
        token_embeddings=((1, 0), (0, 1), (1, -1)),
        position_embeddings=((0, 0), (quarter, -quarter), (-quarter, quarter),
                             (quarter, quarter), (-quarter, -quarter)),
        blocks=blocks, lm_head=((1, 0), (0, 1), (1, -1)),
    )


class TransformerBackendTests(unittest.TestCase):
    def test_stage_dag_and_exact_feature_dimensions(self):
        backend = decoder_fixture(block_count=2)
        self.assertEqual(len(backend.stage_ids), 8)
        self.assertEqual(backend.dependencies(backend.stage_ids[0]), ())
        self.assertEqual(backend.dependencies(backend.stage_ids[-1]), backend.stage_ids[:-1])
        for stage in backend.stage_ids:
            features = backend.stage_features(stage, (0, 1))
            self.assertEqual(len(features), len(backend.stage_weights(stage)[0]))
            self.assertTrue(all(len(row) == 2 for row in features))
            for row in features:
                for value in row:
                    self.assertIsInstance(value, Fraction)
                    self.assertEqual(value.denominator & (value.denominator - 1), 0)

    def test_changed_qkv_affects_downstream_inputs(self):
        backend = decoder_fixture()
        first, second = backend.stage_ids[:2]
        zero = tuple(tuple(Fraction(0) for _ in row) for row in backend.stage_weights(first))
        prefix = {first: zero}
        self.assertEqual(backend.stage_features(first, (0, 1)), backend.stage_features(first, (0, 1), prefix))
        self.assertNotEqual(backend.stage_features(second, (0, 1)), backend.stage_features(second, (0, 1), prefix))
        self.assertTrue(backend.prefix_preserves_stage_inputs(first, prefix))
        self.assertFalse(backend.prefix_preserves_stage_inputs(second, prefix))
        self.assertTrue(backend.prefix_preserves_stage_inputs(second, {first: backend.stage_weights(first)}))

    def test_causal_prefix_and_full_logits(self):
        backend = decoder_fixture(block_count=2, head_count=2)
        longer = backend.logits((0, 1, 2))
        shorter = backend.logits((0, 1))
        self.assertEqual(shorter, longer[:2])
        self.assertEqual(longer, backend.logits((0, 1, 2)))
        self.assertTrue(all(len(row) == 3 and all(math.isfinite(x) for x in row) for row in longer))
        self.assertEqual(backend.exact_logits((0, 1)), tuple(tuple(Fraction.from_float(x) for x in row) for row in shorter))

    def test_generation_and_input_contracts(self):
        backend = decoder_fixture()
        output = backend.greedy_generate((0,), 2)
        self.assertEqual(len(output), 3)
        self.assertEqual(output, backend.greedy_generate((0,), 2))
        self.assertEqual(backend.decode_payload(backend.record_payload((0, 2))), (0, 2))
        for tokens in ((), (3,), (True,), (0,) * 6):
            with self.assertRaises(ValueError):
                backend.logits(tokens)
        with self.assertRaises(ValueError):
            backend.decode_payload(b'{"tokens":[0]}')
        with self.assertRaises(ValueError):
            backend.greedy_generate((0,), 5)
        with self.assertRaises(TypeError):
            stage = backend.stage_ids[0]
            backend.stage_features(stage, (0,), {stage: tuple(tuple(float(x) for x in row) for row in backend.stage_weights(stage))})

    def test_manifest_and_model_are_bound(self):
        backend = decoder_fixture()
        another = decoder_fixture()
        self.assertEqual(backend.evaluator_id, another.evaluator_id)
        manifest = backend.kernel_manifest
        manifest["config"]["model_width"] = 999
        self.assertEqual(backend.kernel_manifest["config"]["model_width"], 2)
        with self.assertRaises(AttributeError):
            backend.config = DecoderConfig(3, 4, 1, 3, 1, 5)
        with self.assertRaises(TypeError):
            backend.stage_weights(backend.stage_ids[0])[0][0] = Fraction(2)

    def test_nonfinite_target_errors_are_not_certificates(self):
        backend = decoder_fixture()
        first = backend.stage_ids[0]
        huge = Fraction(10) ** 308
        overflow = tuple((huge, -huge) for _ in range(6))
        with self.assertRaises(FiniteTargetError):
            backend.logits((0,), {first: overflow})
        with self.assertRaises(TypeError):
            backend.stage_features(first, (0,), {first: ((math.inf, 0),) * 6})

    def test_bad_architecture_component_is_rejected(self):
        with self.assertRaises(ValueError):
            DecoderConfig(3, 3, 2, 3, 1, 5)
        with self.assertRaises(ValueError):
            DecoderConfig(3, 2, 1, 3, 1, 5, layernorm_epsilon=0.0)

    def test_full_decoder_deletion_changes_first_stage_and_matches_fresh(self):
        from src.repair_service import Record

        backend = decoder_fixture()
        grid = (Fraction(-1), Fraction(0), Fraction(1))
        grids = {stage: (grid,) * len(backend.stage_weights(stage)[0]) for stage in backend.stage_ids}
        service = backend.make_repair_service(grids, ridge=1, normalization=1, group_count=2)
        records = tuple(Record(name, backend.record_payload((token,)))
                        for name, token in (("a", 0), ("b", 1), ("c", 2)))
        initial = service.fresh(records)
        before_bytes = initial.state.canonical_bytes()
        retained = {"a": records[0]}
        repaired = service.repair(initial.state, records[1:], retained.__getitem__)
        independent = service.fresh(retained.values())
        self.assertNotEqual(initial.state.model[0].codes, independent.state.model[0].codes)
        self.assertEqual(initial.state.canonical_bytes(), before_bytes)
        self.assertEqual(repaired.state.canonical_bytes(), independent.state.canonical_bytes())
        repaired_prefix = {stage.stage_id: stage.codes for stage in repaired.state.model}
        independent_prefix = {stage.stage_id: stage.codes for stage in independent.state.model}
        self.assertEqual(backend.exact_logits((0, 1), repaired_prefix), backend.exact_logits((0, 1), independent_prefix))
        self.assertEqual(repaired.stages[0].replayed_groups, ())
        self.assertTrue(any(stage.replayed_groups for stage in repaired.stages[1:]))

    def test_repeated_decoder_deletions_are_canonical_and_unknown_replays(self):
        from src.repair_service import Record

        backend = decoder_fixture()
        grid = (Fraction(-1), Fraction(0), Fraction(1))
        grids = {stage: (grid,) * len(backend.stage_weights(stage)[0]) for stage in backend.stage_ids}
        service = backend.make_repair_service(grids, ridge=1, normalization=1, group_count=2)
        records = tuple(Record(name, backend.record_payload((token,)))
                        for name, token in (("a", 0), ("b", 1), ("c", 2)))
        initial = service.fresh(records)
        first = service.repair(initial.state, (records[2],), {r.record_id: r for r in records[:2]}.__getitem__)
        second = service.repair(first.state, (records[1],), {"a": records[0]}.__getitem__)
        direct = service.repair(initial.state, records[1:], {"a": records[0]}.__getitem__)
        self.assertEqual(second.state.canonical_bytes(), direct.state.canonical_bytes())
        all_replay_service = backend.make_repair_service(grids, ridge=1, normalization=1, group_count=2,
                                                        structural_provider=False)
        fallback = all_replay_service.repair(initial.state, records[1:], {"a": records[0]}.__getitem__)
        self.assertEqual(fallback.state.canonical_bytes(), direct.state.canonical_bytes())
        self.assertTrue(all(stage.replayed_groups for stage in fallback.stages))


if __name__ == "__main__":
    unittest.main()
