"""Small arithmetic and control fixtures; no empirical model evaluation."""
import copy
import math
from pathlib import Path
import tempfile
import unittest

import numpy as np

from scripts.run_quality_v30 import (LABELS, NumpyQualityDecoder, nearest_prefix,
    nll_from_logits, paired_summary, read_bound, select_records, validate_selection)
from src.run_store import digest
from tests.test_certified_transformer import small_decoder


def selection_fixture():
    prior = [f"wikitext2:validation:article-row-{i}" for i in range(12)]
    records = [dict(id=f"wikitext2:validation:article-row-{i}", tokens=[0] * 128,
                    body_sha256="a" * 64, document_id=f"wikitext2:validation:article-row-{i}")
               for i in range(24)]
    return {"confirmation": [{"id": "wikitext2:train:article-row-1"}],
            "evaluation": records}, {"excluded_from_future_confirmation_ids": prior}


class QualityV30Tests(unittest.TestCase):
    def test_numpy_matches_small_finite_program_both_activations(self):
        for activation in ("gelu", "gelu_new"):
            decoder, _ = small_decoder(activation)
            actual = NumpyQualityDecoder(decoder.base).logits([0, 1, 2])
            np.testing.assert_allclose(actual, decoder.logits([0, 1, 2]), rtol=0, atol=1e-12)

    def test_multihead_nonzero_bias_fixture_matches_finite_program(self):
        from src.transformer_backend import DecoderConfig, DeterministicDecoder
        from src.certified_transformer import CertifiedDecoder
        rng = np.random.default_rng(19)
        matrix = lambda a, b: (rng.integers(-4, 5, (a, b)) / 16).tolist()
        block = dict(qkv=matrix(12, 4), attn_out=matrix(4, 4),
                     mlp_up=matrix(6, 4), mlp_down=matrix(4, 6),
                     qkv_bias=[.125] * 12, attn_out_bias=[-.25] * 4,
                     mlp_up_bias=[.125] * 6, mlp_down_bias=[.0625] * 4,
                     norm1_scale=[.5, 1., 1.5, 2.], norm1_bias=[.125] * 4,
                     norm2_scale=[2., 1.5, 1., .5], norm2_bias=[-.125] * 4)
        base = DeterministicDecoder(DecoderConfig(5, 4, 2, 6, 2, 4, activation="gelu_new"),
            token_embeddings=matrix(5, 4), position_embeddings=matrix(4, 4),
            blocks=[block, block], lm_head=matrix(5, 4), lm_head_bias=[.125] * 5,
            final_norm_scale=[.5] * 4, final_norm_bias=[.125] * 4)
        decoder = CertifiedDecoder(base)
        np.testing.assert_allclose(NumpyQualityDecoder(base).logits([0, 2, 4]),
                                   decoder.logits([0, 2, 4]), rtol=0, atol=1e-12)

    def test_prefix_changes_weights_and_preserves_causality(self):
        decoder, _ = small_decoder()
        evaluator = NumpyQualityDecoder(decoder.base)
        first = decoder.stage_ids[0]
        changed = {first: np.asarray(decoder.base._float_weights[first], dtype=np.float64) * 0}
        reference = decoder.logits([0, 1, 2], {first: changed[first].astype(int).tolist()})
        actual = evaluator.logits([0, 1, 2], changed)
        np.testing.assert_allclose(actual, reference, rtol=0, atol=1e-12)
        np.testing.assert_allclose(evaluator.logits([0, 1], changed), actual[:2], rtol=0, atol=1e-12)

    def test_prefix_and_token_validation(self):
        decoder, _ = small_decoder()
        evaluator = NumpyQualityDecoder(decoder.base)
        for prefix in ({"unknown": np.zeros((1, 1))},
                       {decoder.stage_ids[0]: np.zeros((1, 1))}):
            with self.assertRaises(ValueError):
                evaluator.logits([0, 1], prefix)
        with self.assertRaises(ValueError):
            evaluator.logits([10, 1])

    def test_nll_uses_next_token_and_stable_logsum(self):
        logits = np.array([[1001., 1000.], [-1000., -999.], [0., 0.]])
        actual = nll_from_logits(logits, [0, 1, 0])
        self.assertAlmostEqual(actual, 2 * math.log1p(math.e), places=12)
        with self.assertRaises(ValueError):
            nll_from_logits(logits[:1], [0])
        with self.assertRaises(ValueError):
            nll_from_logits(logits, [0, 2, 0])

    def test_lower_midpoint_ties(self):
        from types import SimpleNamespace
        base = SimpleNamespace(_float_weights={"s": np.array([[-1.5, -.5, .5, 1.5, 2.0]])})
        stage = SimpleNamespace(stage_id="s", scale_values=(1.,), bits=2)
        np.testing.assert_array_equal(nearest_prefix(base, [stage])["s"], [[-2, -1, 0, 1, 1]])

    def test_selection_preserves_all_exclusions_and_reserve(self):
        pools, old = selection_fixture()
        chosen = select_records(pools, old)
        self.assertEqual(chosen[0]["id"], "wikitext2:validation:article-row-12")
        self.assertEqual(len(chosen), 8)
        pools["confirmation"].append({"id": chosen[0]["id"]})
        with self.assertRaises(ValueError):
            select_records(pools, old)

    def test_selection_rejects_short_and_duplicate_inventory(self):
        pools, old = selection_fixture()
        pools["evaluation"] = pools["evaluation"][:19]
        with self.assertRaises(ValueError):
            select_records(pools, old)
        pools, old = selection_fixture()
        pools["evaluation"][13] = copy.deepcopy(pools["evaluation"][12])
        with self.assertRaises(ValueError):
            select_records(pools, old)

    def test_changed_exclusion_metadata_fails(self):
        pools, old = selection_fixture()
        records = select_records(pools, old)
        reg = dict(records=records, prior_exclusions=sorted(old["excluded_from_future_confirmation_ids"]),
            excluded_from_future_confirmation_ids=sorted(old["excluded_from_future_confirmation_ids"] + [r["id"] for r in records]),
            confirmation=False, scientific_promotion=False, labels=list(LABELS), quality_order=[list(LABELS)] * 8)
        validate_selection(reg, pools, old)
        reg["excluded_from_future_confirmation_ids"].pop()
        with self.assertRaises(ValueError):
            validate_selection(reg, pools, old)

    def test_token_weighted_estimator_and_article_bootstrap(self):
        quality = {label: [dict(id="a", predictions=1, nll_sum=1.),
                           dict(id="b", predictions=3, nll_sum=3.)] for label in LABELS}
        quality["fixed_feature"] = [dict(id="a", predictions=1, nll_sum=2.),
                                    dict(id="b", predictions=3, nll_sum=3.)]
        result = paired_summary(quality, ["a", "b"], repetitions=200, seed=1)
        comparison = result["fixed_feature_comparisons"]["sequential"]
        self.assertEqual(comparison["token_weighted_mean_nll_difference"], .25)
        self.assertEqual(comparison["mean_article_nll_difference"], .5)
        self.assertEqual(comparison["paired_article_bootstrap_95_percentile_nll"], [0., 1.])
        self.assertEqual(result, paired_summary(quality, ["a", "b"], repetitions=200, seed=1))

    def test_incomplete_or_unmatched_quality_fails(self):
        quality = {label: [dict(id="a", predictions=1, nll_sum=1.)] for label in LABELS}
        quality["fixed_feature"][0]["predictions"] = 2
        with self.assertRaises(ValueError):
            paired_summary(quality, ["a"])
        quality["fixed_feature"] = []
        with self.assertRaises(ValueError):
            paired_summary(quality, ["a"])

    def test_bound_artifact_changes_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "artifact"
            path.write_bytes(b"original")
            entry = dict(path=str(path), bytes=8, sha256=digest(b"original"))
            self.assertEqual(read_bound(entry), b"original")
            path.write_bytes(b"different")
            with self.assertRaises(ValueError):
                read_bound(entry)


if __name__ == "__main__":
    unittest.main()
