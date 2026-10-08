"""Follow-up policy fixtures; no empirical model inference."""
import copy
import math
from pathlib import Path
import tempfile
import unittest

from scripts.run_followup_quality_v30 import (LABELS, ORIGINAL_IDS, POLICY, bound,
    summarize, validate_new_generation, validate_reused_articles, policy_for_mode,
    validate_sequential_generation, validate_sequential_implementation, verify_terminal_payload)
from src.run_store import canonical_json, digest


def generation_fixture():
    records = dict(records=[dict(id=rid, tokens=[1] * 128) for rid in ORIGINAL_IDS])
    model = dict(sha256="c" * 64, bytes=123)
    checkpoint = {"config.json": "a" * 64, "model.safetensors": "b" * 64}
    plan = dict(method="repair", source_sha256={"src/example.py": "d" * 64},
                original_token_count=256, record_ids=ORIGINAL_IDS[1:], deleted_ids=ORIGINAL_IDS[:1],
                inputs={"records": dict(sha256=digest(canonical_json(records)))})
    completion = dict(schema="adaptive-complete-service-transaction-v30", status="complete", method="repair",
        complete_model=True, complete_state=True, model_roundtrip_exact=True, state_roundtrip_canonical=True,
        use_candidates=False, confirmation=False, scientific_promotion=False,
        source_sha256=plan["source_sha256"], checkpoint_files_sha256=checkpoint,
        original_token_count=256, retained_token_count=128, original_record_lengths=[128, 128],
        retained_record_lengths=[128], original_record_ids=ORIGINAL_IDS,
        retained_record_ids=ORIGINAL_IDS[1:], committed_record_ids=ORIGINAL_IDS[1:], deleted_record_ids=ORIGINAL_IDS[:1],
        original_records_sha256=digest(canonical_json(records)), records_input_sha256=digest(canonical_json(records)),
        target_recipe=dict(original_token_count=256, bits=4),
        model_artifact=dict(file="model.bin", **model), stage_count=24,
        stage_ids=["s" + str(i) for i in range(24)], model_code_elements=42467328,
        fixed_target_sha256="e" * 64, base_target_sha256="f" * 64)
    return completion, plan, records, checkpoint, model


def article_fixture():
    records = [dict(id="article" + str(i), tokens=[1] * 128) for i in range(8)]
    excluded = ["article" + str(i) for i in range(20)]
    registration = dict(schema="matched-quality-registration-v30", records=records,
                        excluded_from_future_confirmation_ids=excluded)
    first = dict(status="complete", development_quality_gate_pass=True, historical_parity_pass=True,
                 confirmation=False, scientific_promotion=False, excluded_from_future_confirmation_ids=excluded,
                 quality={label: [dict(id=r["id"], predictions=127, nll_sum=127.) for r in records]
                          for label in ("full_precision", "nearest_rounding", "fixed_feature", "sequential")})
    pools = dict(evaluation=records, confirmation=[dict(id="reserved")])
    return registration, first, pools


class FollowupQualityV30Tests(unittest.TestCase):
    def test_valid_generation_contract(self):
        c, p, r, checkpoint, model = generation_fixture()
        validate_new_generation(c, p, r, checkpoint_hashes=checkpoint, model_binding=model)

    def test_generation_rejects_incomplete_state_and_wrong_method(self):
        for key, value in (("complete_model", False), ("state_roundtrip_canonical", False),
                           ("method", "direct_fresh"), ("confirmation", True),
                           ("stage_count", 23), ("model_code_elements", 123)):
            c, p, r, checkpoint, model = generation_fixture()
            c[key] = value
            with self.assertRaises(ValueError):
                validate_new_generation(c, p, r, checkpoint_hashes=checkpoint, model_binding=model)

    def test_generation_rejects_wrong_normalization_or_retained_tokens(self):
        for key, value in (("original_token_count", 32), ("retained_token_count", 16),
                           ("retained_record_lengths", [16]), ("original_record_lengths", [16, 16])):
            c, p, r, checkpoint, model = generation_fixture()
            c[key] = value
            with self.assertRaises(ValueError):
                validate_new_generation(c, p, r, checkpoint_hashes=checkpoint, model_binding=model)

    def test_generation_rejects_foreign_source_checkpoint_or_model(self):
        c, p, r, checkpoint, model = generation_fixture()
        for change in (dict(source_sha256={}), dict(checkpoint_files_sha256={}),
                       dict(model_artifact=dict(file="model.bin", bytes=123, sha256="f" * 64))):
            with self.assertRaises(ValueError):
                validate_new_generation(dict(c, **change), p, r, checkpoint_hashes=checkpoint, model_binding=model)

    def test_generation_rejects_record_mutation(self):
        c, p, r, checkpoint, model = generation_fixture()
        r["records"][0]["tokens"][0] = 2
        with self.assertRaises(ValueError):
            validate_new_generation(c, p, r, checkpoint_hashes=checkpoint, model_binding=model)

    def test_reuses_all_eight_articles_and_twenty_exclusions(self):
        reg, first, pools = article_fixture()
        self.assertEqual(validate_reused_articles(reg, first, pools), reg["records"])
        changed = copy.deepcopy(reg)
        changed["excluded_from_future_confirmation_ids"].pop()
        with self.assertRaises(ValueError):
            validate_reused_articles(changed, first, pools)

    def test_rejects_new_article_token_changes_and_reserve_access(self):
        reg, first, pools = article_fixture()
        for variant in ("duplicate", "token", "reserve"):
            reg2, first2, pools2 = copy.deepcopy((reg, first, pools))
            if variant == "duplicate":
                reg2["records"][1] = copy.deepcopy(reg2["records"][0])
            elif variant == "token":
                reg2["records"][0]["tokens"][0] = 3
                # Fixture shared storage must become independent for this check.
                pools2 = copy.deepcopy(pools)
            else:
                pools2["confirmation"].append(dict(id=reg2["records"][0]["id"]))
            with self.assertRaises(ValueError):
                validate_reused_articles(reg2, first2, pools2)

    def test_primary_gate_and_unmatched_scope(self):
        reg, _, _ = article_fixture()
        quality = {label: [dict(id=r["id"], predictions=127, nll_sum=127.) for r in reg["records"]]
                   for label in LABELS}
        quality["fixed128"] = [dict(id=r["id"], predictions=127, nll_sum=127. * (1 + math.log(1.02)))
                               for r in reg["records"]]
        result = summarize(quality, reg["records"])
        self.assertTrue(result["development_safety_gate_pass"])
        self.assertAlmostEqual(result["fixed128_comparisons"]["fixed16"]["perplexity_ratio"], 1.02)
        self.assertIn("unmatched secondary", result["fixed128_comparisons"]["sequential16"]["comparison_scope"])
        self.assertEqual(POLICY["primary_control"], "fixed16")
        self.assertFalse(POLICY["sequential128_available"])

    def test_secondary_win_cannot_rescue_primary_failure(self):
        reg, _, _ = article_fixture()
        quality = {label: [dict(id=r["id"], predictions=127, nll_sum=127.) for r in reg["records"]]
                   for label in LABELS}
        for row in quality["fixed128"]:
            row["nll_sum"] *= 1 + math.log(1.10)
        for row in quality["sequential16"]:
            row["nll_sum"] *= 2
        result = summarize(quality, reg["records"])
        self.assertFalse(result["development_safety_gate_pass"])
        self.assertLess(result["fixed128_comparisons"]["sequential16"]["perplexity_ratio"], 1)

    def test_incomplete_model_article_table_fails(self):
        reg, _, _ = article_fixture()
        quality = {label: [dict(id=r["id"], predictions=127, nll_sum=127.) for r in reg["records"]]
                   for label in LABELS}
        quality["fixed128"].pop()
        with self.assertRaises(ValueError):
            summarize(quality, reg["records"])

    def test_late_bound_descriptor_supports_missing_size(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "model"
            path.write_bytes(b"fixture")
            entry = dict(path=str(path), sha256=digest(b"fixture"))
            self.assertEqual(bound(entry), b"fixture")
            self.assertEqual(bound(dict(entry, bytes=7)), b"fixture")
            with self.assertRaises(ValueError):
                bound(dict(entry, bytes=8))
            path.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                bound(entry)

    def test_prospective_mode_selects_primary_without_changing_safety_control(self):
        self.assertEqual(policy_for_mode(False), POLICY)
        matched = policy_for_mode(True)
        self.assertEqual(matched["primary_control"], "sequential128")
        self.assertEqual(matched["safety_control"], "fixed16")
        with self.assertRaises(ValueError):
            policy_for_mode("yes")

    def test_matched_sequential_validation_and_target_mismatch(self):
        fixed, fixed_plan, records, checkpoint, model = generation_fixture()
        plan = dict(fixed_plan, method="model_only_fresh", inputs=dict(fixed_plan["inputs"], config={}, weights={}))
        seq = dict(fixed, schema="sequential-quality-comparison-v30", method="model_only_fresh",
                   comparison_role="sequential_quality", complete_state=False,
                   sequential_target_sha256=fixed["base_target_sha256"])
        validate_sequential_generation(seq, plan, records, checkpoint_hashes=checkpoint,
                                       model_binding=model, fixed_completion=fixed)
        for key, value in (("retained_token_count", 16), ("original_token_count", 32),
                           ("sequential_target_sha256", "d" * 64), ("target_recipe", {}),
                           ("comparison_role", "fixed_quality"), ("complete_state", True)):
            with self.assertRaises(ValueError):
                validate_sequential_generation(dict(seq, **{key:value}), plan, records,
                    checkpoint_hashes=checkpoint, model_binding=model, fixed_completion=fixed)

    def test_matched_primary_requires_six_complete_models(self):
        reg, _, _ = article_fixture()
        quality = {label: [dict(id=r["id"], predictions=127, nll_sum=127.) for r in reg["records"]]
                   for label in LABELS}
        with self.assertRaises(ValueError):
            summarize(quality, reg["records"], matched=True)
        quality["sequential128"] = copy.deepcopy(quality["sequential16"])
        result = summarize(quality, reg["records"], matched=True)
        self.assertTrue(result["matched_quality_gate_pass"])
        self.assertIn("prospectively chosen primary", result["fixed128_comparisons"]["sequential128"]["comparison_scope"])
        with self.assertRaises(ValueError):
            summarize(quality, reg["records"], matched=False)

    def test_named_service_adapter_preserves_original_terminal_bytes(self):
        original = dict(schema="adaptive-complete-service-transaction-v30", status="complete",
                        complete_state=True, model_artifact=dict(file="model.bin", bytes=1, sha256="a" * 64),
                        state_artifact=dict(file="state.bin", bytes=2, sha256="b" * 64))
        verified = dict(original, artifacts=dict(model=original["model_artifact"], state=original["state_artifact"]),
            artifact_manifest_source="verified named model_artifact/state_artifact fields; original bytes unchanged")
        self.assertEqual(verify_terminal_payload(canonical_json(original), verified), original)
        self.assertEqual(verify_terminal_payload(canonical_json(original), original), original)

    def test_ordered_implementation_requires_artifact_identity_and_source_bindings(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            names = ('ordered_finite_decoder_v30.py', 'ordered_attention_v30.py')
            for name in names:
                (root/name).write_bytes(b'software fixture source')
            manifest = dict(schema='ordered-equivalent-finite-decoder-v30', global_mutation=False,
                source_sha256={name:digest((root/name).read_bytes()) for name in names})
            raw = canonical_json(manifest)
            result = dict(implementation='ordered-finite-decoder-v30', target_identity_matches_scalar_reference=True,
                implementation_manifest=manifest, implementation_manifest_sha256=digest(raw),
                artifacts=dict(implementation=dict(file='implementation.json', bytes=len(raw), sha256=digest(raw))))
            self.assertEqual(validate_sequential_implementation(result, policy_for_mode(True), raw, root), digest(raw))
            for change in (dict(target_identity_matches_scalar_reference=False), dict(artifacts={}),
                           dict(implementation='scalar-decoder'), dict(implementation_manifest_sha256='f'*64)):
                with self.assertRaises(ValueError):
                    validate_sequential_implementation(dict(result, **change), policy_for_mode(True), raw, root)
            (root/names[0]).write_bytes(b'changed source')
            with self.assertRaisesRegex(ValueError, 'source differs'):
                validate_sequential_implementation(result, policy_for_mode(True), raw, root)

    def test_adapter_cannot_change_original_fields_or_inject_other_fields(self):
        original = dict(schema="adaptive-complete-service-transaction-v30", status="complete", complete_state=False,
                        model_artifact=dict(file="model.bin", bytes=1, sha256="a" * 64))
        for verified in (dict(original, status="failed"), dict(original, unexpected=True),
                         dict(original, artifacts={}, artifact_manifest_source="invalid")):
            with self.assertRaises(ValueError):
                verify_terminal_payload(canonical_json(original), verified)


if __name__ == "__main__":
    unittest.main()
